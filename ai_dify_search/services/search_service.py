# -*- coding: utf-8 -*-
"""
@File   :   search_service.py
@Time   :   2024-04-14
@Desc   :   Odoo 商品搜索服务
"""

import logging
import time
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from odoo import models, fields, api, SUPERUSER_ID
from odoo.osv.expression import AND, OR

_logger = logging.getLogger(__name__)


class AiSearchService:
    """
    Odoo 商品搜索服务
    负责根据解析后的意图执行真实的商品检索
    """

    # category → scenario_tags 映射表
    # key: category_names 中的值（支持大小写不敏感匹配）
    # value: 中文场景标签列表
    CATEGORY_SCENARIO_TAGS = {
        # 园林灌溉
        'filter': ['园林灌溉', '水处理系统'],
        'irrigation': ['园林灌溉', '农业灌溉'],
        'sprinkler': ['园林灌溉', '农业灌溉'],
        # 园艺
        'garden': ['家庭园艺', '农业机械'],
        'lawn': ['家庭园艺', '草坪维护'],
        'mower': ['家庭园艺', '草坪维护'],
        # 矿山/工程
        'mining': ['矿山设备', '工程器械'],
        'excavator': ['工程器械', '矿山设备'],
        'bulldozer': ['工程器械', '土方工程'],
        # 管道
        'pe pipe': ['管道工程', '灌溉系统'],
        'pipe': ['管道工程', '水利工程'],
        'plumbing': ['管道工程', '给排水'],
        # 农机
        'tractor': ['农业机械', '拖拉机配件'],
        'harvester': ['农业机械', '收割设备'],
        'agricultural': ['农业机械', '农业生产'],
        'farm': ['农业生产', '农业机械'],
        # 发动机/燃油系统
        'engine': ['发动机', '动力系统'],
        'fuel': ['燃油系统', '发动机'],
        'injection': ['燃油喷射', '发动机'],
        'injector': ['燃油喷射', '发动机喷油器'],
        'pump': ['泵送设备', '液压系统'],
        # 车辆
        'automotive': ['汽车配件', '车辆维修'],
        'car': ['汽车配件', '车辆维修'],
        'truck': ['卡车配件', '商用车'],
        'vehicle': ['汽车配件', '车辆维修'],
        # 通用
        'all': ['通用配件', '多场景应用'],
        'parts': ['机械配件', '维修替换'],
        'accessory': ['配件', '辅助设备'],
    }

    def __init__(self, env):
        """
        初始化搜索服务

        :param env: Odoo environment
        """
        self.env = env
        self._config_service = None
        self._ranking_service = None
        self._product_understanding = None

    @property
    def config_service(self):
        """懒加载配置服务"""
        if self._config_service is None:
            from .config_service import AiSearchConfigService
            self._config_service = AiSearchConfigService(self.env)
        return self._config_service

    @property
    def ranking_service(self):
        """懒加载排名服务"""
        if self._ranking_service is None:
            from .ranking_service import AiRankingService
            self._ranking_service = AiRankingService(self.env)
        return self._ranking_service

    @property
    def product_understanding(self):
        """懒加载商品理解服务"""
        if self._product_understanding is None:
            from .product_understanding_service import ProductUnderstandingService
            self._product_understanding = ProductUnderstandingService(self.env)
        return self._product_understanding

    def search_products(self, parsed_intent: Dict[str, Any],
                        top_k: Optional[int] = None,
                        session_context: Optional[Dict] = None,
                        lang: str = 'zh_CN') -> Tuple[List[Dict[str, Any]], Dict[str, Any], float]:
        """
        根据解析后的意图搜索商品

        :param parsed_intent: Dify 解析出的意图 JSON
        :param top_k: 返回商品数量限制
        :param session_context: 会话上下文（用于多轮对话优化）
        :param lang: 语言代码
        :return: tuple (products, applied_filters, latency_ms)
        """
        start_time = time.time()

        # 获取配置
        if top_k is None:
            top_k = self.config_service.search_top_k

        # 构建搜索域
        domain, applied_filters = self._build_search_domain(
            parsed_intent, session_context, lang
        )

        _logger.info('Searching products with domain: %s, top_k=%d', domain, top_k)
        _logger.info('DEBUG: intent keywords = %s', parsed_intent.get('keywords', []))

        # 执行搜索
        product_ids = self._execute_search(domain, top_k, parsed_intent)

        # 获取商品详细信息
        products = self._get_product_details(
            product_ids, applied_filters, lang
        )

        latency_ms = (time.time() - start_time) * 1000

        _logger.info(
            'Product search completed: domain=%s, found=%d, latency=%.2fms',
            domain, len(products), latency_ms
        )

        return products, applied_filters, latency_ms

    def _build_search_domain(self, intent: Dict[str, Any],
                              session_context: Optional[Dict] = None,
                              lang: str = 'zh_CN') -> Tuple[List, Dict]:
        """
        根据意图构建搜索域

        :param intent: 解析后的意图
        :param session_context: 会话上下文
        :param lang: 语言
        :return: tuple (domain, applied_filters)
        """
        domain = []
        applied_filters = {}

        # ========== 第一层：基础业务过滤 ==========

        # 必须满足：可销售
        domain.append(('sale_ok', '=', True))

        # 排除未激活的商品
        domain.append(('active', '=', True))

        applied_filters['sale_ok'] = True

        # ========== 第二层：价格区间 ==========

        budget_min = intent.get('budget_min')
        budget_max = intent.get('budget_max')

        if budget_max is not None and budget_max > 0:
            domain.append(('list_price', '<=', budget_max))
            applied_filters['budget_max'] = budget_max

        if budget_min is not None and budget_min > 0:
            domain.append(('list_price', '>=', budget_min))
            applied_filters['budget_min'] = budget_min

        # ========== 第三层：类目过滤 ==========

        category = intent.get('category')
        if category:
            # 尝试查找匹配的类目
            categ_ids = self._find_category(category, lang)
            if categ_ids:
                # 使用子类别搜索
                domain.append(('categ_id', 'child_of', categ_ids))
                applied_filters['category'] = category

        # ========== 第四层：品牌过滤 ==========

        brand_include = intent.get('brand_include', [])
        brand_exclude = intent.get('brand_exclude', [])

        if brand_include:
            brand_ids = self._find_brands(brand_include)
            if brand_ids:
                domain.append(('product_brand_id', 'in', brand_ids))
                applied_filters['brand_include'] = brand_include

        if brand_exclude:
            brand_ids = self._find_brands(brand_exclude)
            if brand_ids:
                domain.append(('product_brand_id', 'not in', brand_ids))
                applied_filters['brand_exclude'] = brand_exclude

        # ========== 第五层：属性过滤（颜色等） ==========

        color_include = intent.get('color_include', [])
        color_exclude = intent.get('color_exclude', [])

        if color_exclude:
            # 排除指定颜色
            color_ids = self._find_attribute_values('color', color_exclude)
            if color_ids:
                # 商品不应有这些颜色属性
                exclude_domain = [('attribute_line_ids.attribute_id.name', 'ilike', 'color')]
                for color_name in color_exclude:
                    exclude_domain = OR([
                        exclude_domain,
                        [('attribute_line_ids.value_ids.name', 'ilike', color_name)]
                    ])
                domain = AND([domain, exclude_domain])
                applied_filters['color_exclude'] = color_exclude

        # ========== 第六层：关键词文本匹配 ==========

        keywords = intent.get('keywords', [])

        # 如果有 must_have 属性要求
        must_have = intent.get('must_have', [])
        if must_have:
            for attr in must_have:
                # 尝试匹配属性值
                attr_ids = self._find_attribute_values(None, [attr])
                if attr_ids:
                    for attr_id in attr_ids:
                        domain = AND([domain, [
                            ('attribute_line_ids.value_ids', 'in', attr_id)
                        ]])
            applied_filters['must_have'] = must_have

        # 收集所有用于文本匹配的内容
        text_conditions = []
        if keywords:
            text_conditions.extend(keywords)
        if intent.get('use_case'):
            text_conditions.extend(intent.get('use_case'))
        if intent.get('season'):
            text_conditions.append(intent.get('season'))

        if text_conditions:
            applied_filters['keywords'] = text_conditions
            # 添加关键词搜索条件：匹配名称或描述
            keyword_conditions = []
            for kw in text_conditions:
                keyword_conditions.append(('name', 'ilike', kw))
                keyword_conditions.append(('description_sale', 'ilike', kw))
            keyword_domain = ['|'] + keyword_conditions if len(keyword_conditions) > 1 else keyword_conditions
            domain = AND([domain, keyword_domain])

        return domain, applied_filters

    def _build_keyword_fallback_domain(self, intent: Dict[str, Any]) -> List:
        """
        构建仅使用关键词的降级搜索域（当类目等过滤无结果时使用）

        :param intent: 解析后的意图
        :return: 仅包含关键词的搜索域
        """
        domain = []

        # 必须满足：可销售且已激活
        domain.append(('sale_ok', '=', True))
        domain.append(('active', '=', True))

        keywords = intent.get('keywords', [])
        if not keywords:
            # 如果没有关键词，尝试使用类目名作为关键词
            category = intent.get('category')
            if category:
                keywords = [category]

        if keywords:
            # 搜索 name, default_code, description_sale
            keyword_domain = ['|', '|',
                ('name', 'ilike', keywords[0]),
                ('default_code', 'ilike', keywords[0]),
                ('description_sale', 'ilike', keywords[0])
            ]
            for kw in keywords[1:]:
                keyword_domain = OR([keyword_domain, [('name', 'ilike', kw)]])
                keyword_domain = OR([keyword_domain, [('default_code', 'ilike', kw)]])
                keyword_domain = OR([keyword_domain, [('description_sale', 'ilike', kw)]])

            domain = AND([domain, keyword_domain])

        return domain

    def _execute_search(self, domain: List, top_k: int,
                        intent: Dict[str, Any]) -> List[int]:
        """
        执行商品搜索

        :param domain: 搜索域
        :param top_k: 返回数量
        :param intent: 意图（用于文本匹配排序）
        :return: 商品 ID 列表
        """
        _logger.info('DEBUG _execute_search: domain=%s, top_k=%d', domain, top_k)

        # 使用 SQL 搜索以正确处理 JSON 翻译字段
        lang_key = 'zh_CN'
        keywords = intent.get('keywords', []) if intent else []
        search_term = keywords[0] if keywords else ''

        # 如果 domain 包含关键词条件，提取搜索词
        if not search_term and domain:
            for clause in domain:
                if isinstance(clause, tuple) and len(clause) == 3:
                    if clause[0] == 'name' and 'ilike' in str(clause[2]):
                        search_term = clause[2] if isinstance(clause[2], str) else ''
                    elif clause[0] == 'description_sale' and 'ilike' in str(clause[2]):
                        search_term = clause[2] if isinstance(clause[2], str) else ''

        # 构建 SQL 查询
        if search_term:
            sql = """
                SELECT id FROM product_template
                WHERE sale_ok = true
                  AND active = true
                  AND (
                      COALESCE(name->>'zh_CN', name->>'en_US', name->>'en_US', '') ILIKE %s
                      OR COALESCE(default_code, '') ILIKE %s
                      OR COALESCE(description_sale->>'zh_CN', description_sale->>'en_US', description_sale->>'en_US', '') ILIKE %s
                  )
                ORDER BY id DESC
                LIMIT %s
            """
            try:
                self.env.cr.execute("ROLLBACK")
            except Exception:
                pass
            self.env.cr.execute(sql, [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', top_k * 3])
            results = self.env.cr.fetchall()
            product_ids = [r[0] for r in results]
            _logger.info('DEBUG _execute_search: SQL search returned %d products for term: %s', len(product_ids), search_term)
            products = self.env['product.template'].sudo().browse(product_ids) if product_ids else self.env['product.template'].sudo()
        else:
            # 无关键词时使用 ORM（处理其他过滤条件如价格、类目等）
            product_model = self.env['product.template'].sudo()
            products = product_model.search(
                domain,
                limit=top_k * 3,
                order='id DESC'
            )
            _logger.info('DEBUG _execute_search: ORM search returned %d products', len(products))

        # ========== 降级搜索：当类目/过滤条件无结果时，回退到关键词搜索 ==========
        if not products and domain:
            _logger.info('Full domain search returned no results, falling back to keyword search')
            fallback_domain = self._build_keyword_fallback_domain(intent)
            _logger.info('DEBUG fallback_domain: %s', fallback_domain)
            if fallback_domain:
                products = self.env['product.template'].sudo().search(
                    fallback_domain,
                    limit=top_k * 3,
                    order='id DESC'
                )
                _logger.info('Fallback search returned %d products', len(products))

        # 如果有向量搜索能力且启用，尝试向量搜索
        if self.config_service.vector_search_enabled:
            vector_results = self._vector_search(intent, top_k)
            if vector_results:
                # 合并结果
                products = self._merge_search_results(
                    products.ids, vector_results, intent
                )

        # 文本相关性排序
        keywords = intent.get('keywords', [])
        if keywords and products:
            products = self.ranking_service.reorder_by_text_match(
                products, keywords
            )

        # 返回 top_k
        return products.ids[:top_k]

    def _vector_search(self, intent: Dict[str, Any], limit: int) -> List[int]:
        """
        向量搜索（如果可用）

        :param intent: 意图
        :param limit: 返回数量
        :return: 商品 ID 列表，如果没有启用或不可用则返回空
        """
        # 检查 pgvector 是否可用
        if not self._check_pgvector_available():
            _logger.debug('pgvector not available, skipping vector search')
            return []

        try:
            # 获取文本用于 embedding
            keywords = intent.get('keywords', [])
            query_text = ' '.join(keywords) if keywords else intent.get('category', '')

            if not query_text:
                return []

            # 注意：这里需要商品已经有 embedding
            # 简化实现，假设使用现有的 ir.config_parameter 配置
            embedding_model = self.env['product.embedding']
            vector_limit = self.config_service.vector_search_limit

            # 使用简化相似度搜索
            products = embedding_model.search([], limit=vector_limit)

            # 返回 product IDs（这里需要根据实际 embedding 表结构调整）
            return []

        except Exception as e:
            _logger.warning('Vector search error: %s', str(e))
            return []

    def _check_pgvector_available(self) -> bool:
        """检查 pgvector 是否可用"""
        try:
            self.env.cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return bool(self.env.cr.fetchone())
        except Exception:
            return False

    def _merge_search_results(self, base_ids: List[int],
                               vector_ids: List[int],
                               intent: Dict[str, Any]) -> List[int]:
        """
        合并基础搜索和向量搜索结果

        :param base_ids: 基础搜索的商品 ID
        :param vector_ids: 向量搜索的商品 ID
        :param intent: 意图
        :return: 合并后的 ID 列表
        """
        seen = set()
        result = []

        # 优先保留基础搜索结果
        for pid in base_ids:
            if pid not in seen:
                result.append(pid)
                seen.add(pid)

        # 添加向量搜索结果
        for pid in vector_ids:
            if pid not in seen:
                result.append(pid)
                seen.add(pid)

        return result

    def _resize_image_url(self, image_url: str, height: int, width: int) -> str:
        """
        动态调整图片尺寸

        :param image_url:原始图片URL
        :param height: 目标高度
        :param width: 目标宽度
        :return: 调整后的图片URL
        """
        if not image_url or 'x-oss-process=' not in image_url:
            return image_url

        # 替换现有的 resize 参数
        import re
        # 匹配 resize,h_XYZ,w_XYZ 模式
        pattern = r'resize,h_\d+,w_\d+'
        replacement = f'resize,h_{height},w_{width}'
        return re.sub(pattern, replacement, image_url)

    def _get_product_details(self, product_ids: List[int],
                               applied_filters: Dict,
                               lang: str = 'zh_CN') -> List[Dict[str, Any]]:
        """
        获取商品详细信息用于前端展示

        :param product_ids: 商品 ID 列表
        :param applied_filters: 应用的过滤条件
        :param lang: 语言
        :return: 商品详情列表
        """
        if not product_ids:
            return []

        lang_key = 'zh_CN' if lang == 'zh_CN' else 'en_US'

        # 使用 sudo() + 指定 lang context 获取商品记录
        products = self.env['product.template'].with_context(lang=lang_key).sudo().browse(product_ids)

        result = []
        # 获取产品ID列表用于SQL查询分类
        product_ids = [p.id for p in products]

        # 预先用SQL查询每个产品的分类名称
        category_map = {}
        if product_ids:
            self.env.cr.execute("""
                SELECT pt.id, pc.name
                FROM product_template pt
                LEFT JOIN product_category pc ON pt.categ_id = pc.id
                WHERE pt.id IN %s
            """, [tuple(product_ids)])
            category_map = {row[0]: row[1] for row in self.env.cr.fetchall()}

        for product in products:
            # 获取图片 URL - 优先使用 external_card_image_url (h_400, product_image_hub)
            # 其次 external_thumbnail_image_url (h_100) - 动态调整尺寸
            # 最后使用标准 image_512
            external_card = getattr(product, 'external_card_image_url', None) or ''
            if external_card:
                image_url = external_card
            elif getattr(product, 'external_thumbnail_image_url', None):
                # 动态调整缩略图尺寸到卡片所需尺寸 (h_400,w_400)
                thumb_url = product.external_thumbnail_image_url
                image_url = self._resize_image_url(thumb_url, 400, 400)
            elif product.image_512:
                image_url = '/web/image/product.template/%d/image_512' % product.id
            else:
                image_url = ''

            # 获取类别名称 - 使用SQL查询的结果（获取产品实际分配的分类）
            category_names = []
            cat_name = category_map.get(product.id)
            if cat_name:
                category_names = [cat_name]

            # 直接获取已翻译的字段值（with_context 已设置语言）
            name = product.name or ''
            description_sale = product.description_sale or ''
            description = product.description or ''

            # 如果字段返回的是 JSON dict，手动提取翻译
            if isinstance(product.name, dict):
                name = product.name.get(lang_key, product.name.get('en_US', ''))
            if isinstance(product.description_sale, dict):
                description_sale = product.description_sale.get(lang_key, product.description_sale.get('en_US', ''))
            if isinstance(product.description, dict):
                description = product.description.get(lang_key, product.description.get('en_US', ''))

            # 组合简短描述
            short_description = description_sale or description or ''
            if len(short_description) > 100:
                short_description = short_description[:100] + '...'

            # 从 category_names 映射到 scenario_tags（大小写不敏感模糊匹配）
            scenario_tags = []
            for cat in category_names:
                cat_lower = cat.lower()
                tags = []
                # 优先精确匹配
                if cat_lower in self.CATEGORY_SCENARIO_TAGS:
                    tags = self.CATEGORY_SCENARIO_TAGS[cat_lower]
                else:
                    # 模糊匹配：检查 category name 是否包含映射表中的 key
                    for key, value in self.CATEGORY_SCENARIO_TAGS.items():
                        if key in cat_lower or cat_lower in key:
                            tags = value
                            break
                scenario_tags.extend(tags)
            scenario_tags = list(set(scenario_tags))  # 去重

            # 构建基础商品数据
            # 直接使用价格（系统使用美元）
            price = product.list_price or 0

            base_product = {
                'id': product.id,
                'name': name,
                'default_code': product.default_code or '',
                'price': price,
                'currency': 'USD',
                'url': '/shop/product/%s' % product.id,
                'image_url': image_url,
                'category_names': category_names,
                'scenario_tags': scenario_tags,
                'short_description': short_description,
                'description': description,
                'description_sale': description_sale,
                'sale_ok': product.sale_ok,
                # 产品对比字段
                'compare_selling_points': product.compare_selling_points or '',
                'compare_target_people': product.compare_target_people or '',
                'compare_scenes': product.compare_scenes or '',
                'compare_attributes': product.compare_attributes or '[]',
                'compare_highlights': product.compare_highlights or '',
                'compare_warranty': product.compare_warranty or '',
            }

            # 使用商品理解服务提取结构化信息
            try:
                understood = self.product_understanding.understand_product(base_product)
                # 合并理解结果到基础数据
                base_product.update({
                    'brand': understood.get('brand'),
                    'attributes': understood.get('attributes', []),
                    'selling_points': understood.get('selling_points', []),
                    'target_people': understood.get('target_people', []),
                    'scenes': understood.get('scenes', []),
                    'tags': understood.get('tags', []),
                    'searchable_text': understood.get('searchable_text', ''),
                    'compare_features': understood.get('compare_features', {}),
                })
            except Exception as e:
                _logger.warning('Product understanding failed for product %s: %s', product.id, e)
                base_product.update({
                    'brand': None,
                    'attributes': [],
                    'selling_points': [],
                    'target_people': [],
                    'scenes': [],
                    'tags': [],
                    'searchable_text': name,
                    'compare_features': {},
                })

            result.append(base_product)

        return result

    def _find_category(self, category_name: str, lang: str) -> List[int]:
        """
        查找匹配的类目

        :param category_name: 类目名称
        :param lang: 语言
        :return: 类目 ID 列表
        """
        if not category_name:
            return []

        try:
            # 搜索类目
            categs = self.env['product.public.category'].search([
                '|',
                ('name', 'ilike', category_name),
                ('name', 'ilike', category_name.replace(' ', ''))
            ], limit=10)
            return categs.ids
        except Exception:
            return []

    def _find_brands(self, brand_names: List[str]) -> List[int]:
        """
        查找匹配的品牌

        :param brand_names: 品牌名称列表
        :return: 品牌 ID 列表
        """
        if not brand_names:
            return []

        # 查找品牌模型（如果有）
        if hasattr(self.env, 'product.brand'):
            brands = self.env['product.brand'].search([
                '|',
                ('name', 'in', brand_names),
                ('name', 'ilike', brand_names[0] if brand_names else '')
            ], limit=10)
            return brands.ids

        # 尝试使用 x_brand 字段
        brand_field_exists = self._check_field_exists('product.template', 'x_brand')
        if brand_field_exists:
            domain = ['|'] * (len(brand_names) - 1) if len(brand_names) > 1 else []
            for name in brand_names:
                domain = OR([domain, [('x_brand', 'ilike', name)]])
            products = self.env['product.template'].search(domain, limit=100)
            return products.mapped('x_brand').ids

        return []

    def _find_attribute_values(self, attribute_type: Optional[str],
                                values: List[str]) -> List[int]:
        """
        查找匹配的属性值

        :param attribute_type: 属性类型（如 'color'）
        :param values: 属性值名称列表
        :return: 属性值 ID 列表
        """
        if not values:
            return []

        domain = []
        for val in values:
            domain = OR([domain, [('name', 'ilike', val)]])

        attr_value_model = self.env['product.attribute.value']
        values_found = attr_value_model.search(domain, limit=50)

        return values_found.ids

    def _check_field_exists(self, model_name: str, field_name: str) -> bool:
        """
        检查字段是否存在

        :param model_name: 模型名
        :param field_name: 字段名
        :return: 是否存在
        """
        try:
            model = self.env[model_name]
            return field_name in model._fields
        except Exception:
            return False

    def fallback_search(self, query: str, top_k: Optional[int] = None,
                        lang: str = 'zh_CN',
                        page: int = 1) -> Tuple[List[Dict[str, Any]], float, bool]:
        """
        本地 Fallback 搜索
        当 Dify 不可用时使用本地简化意图提取 + 搜索

        :param query: 用户原始查询
        :param top_k: 返回数量
        :param lang: 语言
        :param page: 页码（从1开始）
        :return: tuple (products, latency_ms, has_more)
        """
        start_time = time.time()

        if top_k is None:
            top_k = self.config_service.search_top_k

        # 简单的本地意图提取
        intent = self._simple_intent_parse(query)
        keywords = intent.get('keywords', [])
        _logger.info('DEBUG fallback: query=%s, intent_keywords=%s, page=%s', query, keywords, page)

        # 使用原生 SQL 搜索（ORM 无法正确处理 JSON 翻译字段的 ilike）
        search_term = keywords[0] if keywords else query
        lang_key = 'zh_CN' if lang == 'zh_CN' else 'en_US'

        # 计算偏移量
        offset = (page - 1) * top_k

        try:
            # 先清理可能失败的事务状态
            self.env.cr.execute("ROLLBACK")
        except Exception:
            pass

        # 执行搜索 SQL - 显式处理 JSON 翻译字段
        # 先查询总数
        count_sql = """
            SELECT COUNT(id) FROM product_template
            WHERE sale_ok = true
              AND active = true
              AND (
                  COALESCE(name->>'zh_CN', name->>'en_US', '') ILIKE %s
                  OR COALESCE(default_code, '') ILIKE %s
                  OR COALESCE(description_sale->>'zh_CN', description_sale->>'en_US', '') ILIKE %s
              )
        """
        self.env.cr.execute(count_sql, [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
        total_count = self.env.cr.fetchone()[0]

        # 执行分页搜索 SQL
        self.env.cr.execute("""
            SELECT id FROM product_template
            WHERE sale_ok = true
              AND active = true
              AND (
                  COALESCE(name->>'zh_CN', name->>'en_US', '') ILIKE %s
                  OR COALESCE(default_code, '') ILIKE %s
                  OR COALESCE(description_sale->>'zh_CN', description_sale->>'en_US', '') ILIKE %s
              )
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', top_k, offset])

        product_ids = [row[0] for row in self.env.cr.fetchall()]
        _logger.info('DEBUG fallback: found %d products via SQL (page=%s, offset=%s, total=%s)', len(product_ids), page, offset, total_count)

        # 判断是否还有更多
        has_more = (offset + len(product_ids)) < total_count

        # 提交事务以清除状态
        try:
            self.env.cr.execute("COMMIT")
        except Exception:
            pass

        # 获取商品详情
        product_details = self._get_product_details(product_ids, {}, lang)

        total_latency = (time.time() - start_time) * 1000

        return product_details, total_latency, has_more

    def _simple_intent_parse(self, query: str) -> Dict[str, Any]:
        """
        简单的本地意图解析
        使用正则表达式提取基本搜索条件

        :param query: 用户查询
        :return: 简化的意图字典
        """
        intent = {
            'category': None,
            'budget_min': None,
            'budget_max': None,
            'brand_include': [],
            'brand_exclude': [],
            'color_include': [],
            'color_exclude': [],
            'must_have': [],
            'must_not_have': [],
            'use_case': [],
            'season': None,
            'sort_preference': None,
            'language': 'zh',
            'need_clarification': False,
            'clarification_question': None,
            'keywords': [],
        }

        query_lower = query.lower()
        keywords = []

        # ========== 价格提取 ==========
        # 匹配 "300元以内", "300以下", "不超过300"
        budget_max_match = re.search(r'(\d+)\s*(元|块)?\s*(以内|以下|不超过|低于|少于|不到)', query)
        if budget_max_match:
            intent['budget_max'] = float(budget_max_match.group(1))
            keywords.append(query[:budget_max_match.start()].strip())

        # 匹配 "300元以上", "300以上", "至少300"
        budget_min_match = re.search(r'(\d+)\s*(元|块)?\s*(以上|以上|超过|高于|多于)', query)
        if budget_min_match:
            intent['budget_min'] = float(budget_min_match.group(1))

        # 匹配 "300-500元" 价格区间
        range_match = re.search(r'(\d+)\s*-\s*(\d+)\s*(元|块)?', query)
        if range_match:
            intent['budget_min'] = float(range_match.group(1))
            intent['budget_max'] = float(range_match.group(2))

        # 匹配单独的数字（可能是价格）
        if not intent['budget_max'] and not intent['budget_min']:
            single_price_match = re.search(r'^(\d{2,4})\s*(元|块)?$', query.strip())
            if single_price_match:
                intent['budget_max'] = float(single_price_match.group(1))

        # ========== 排除词处理 ==========
        # "不要白色", "不要 Nike"
        exclude_match = re.search(r'不要\s*([^\s,，]+)', query)
        if exclude_match:
            exclude_item = exclude_match.group(1)
            # 检查是否是颜色词
            color_words = ['白色', '黑色', '红色', '蓝色', '绿色', '黄色', '粉色', '灰色', '棕色']
            if exclude_item in color_words:
                intent['color_exclude'].append(exclude_item)
            else:
                intent['must_not_have'].append(exclude_item)

        # ========== 场景/用途 ==========
        use_case_map = {
            '通勤': ['通勤', '上班', '日常'],
            '运动': ['运动', '跑步', '健身'],
            '休闲': ['休闲', '居家'],
            '正式': ['正式', '商务'],
        }
        for case, synonyms in use_case_map.items():
            if any(s in query_lower for s in synonyms):
                intent['use_case'].append(case)
                break

        # ========== 季节 ==========
        season_map = {
            'summer': ['夏天', '夏季', '透气', '凉快'],
            'winter': ['冬天', '冬季', '保暖'],
            'spring': ['春天', '春季'],
            'autumn': ['秋天', '秋季'],
        }
        for season, synonyms in season_map.items():
            if any(s in query_lower for s in synonyms):
                intent['season'] = season
                break

        # ========== 关键词收集 ==========
        # 移除已识别的模式后，剩余的作为关键词
        remaining = query
        for pattern in [r'\d+\s*元以内', r'\d+\s*元以下', r'不要\s*\S+',
                         r'\d+\s*-\s*\d+\s*元?', r'[上下左右前后]?\s*不要']:
            remaining = re.sub(pattern, '', remaining)

        # 清理并分词
        remaining = re.sub(r'[^\w\s]', ' ', remaining)
        words = [w.strip() for w in remaining.split() if len(w.strip()) > 1]

        # 过滤停用词
        stop_words = ['帮我', '给我', '找一下', '推荐', '有没有', '想要', '需要', '看看']
        keywords.extend([w for w in words if w not in stop_words])

        intent['keywords'] = keywords if keywords else [query]

        return intent

    def _build_usage_categories(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据产品列表生成分类卡片数据

        :param products: 产品列表
        :return: usage_categories 列表
        """
        if not products:
            return []

        # 按 category_names 分组
        category_groups = {}
        for product in products:
            category_names = product.get('category_names', [])
            if category_names:
                cat_name = category_names[0]
            else:
                cat_name = '其他'

            if cat_name not in category_groups:
                category_groups[cat_name] = []
            category_groups[cat_name].append(product)

        # 为每个分类生成卡片数据
        usage_categories = []
        icon_map = {
            'VEHICLE PARTS': '🚗',
            '汽车': '🚗',
            'TRACTOR PARTS': '🚜',
            '拖拉机': '🚜',
            'FORKLIFT PARTS': '🚜',
            '叉车': '🚜',
            'MINING EQUIPMENT PARTS': '⛏️',
            '矿山': '⛏️',
            'GENERATOR PARTS': '⚡',
            '发电机': '⚡',
            '船用': '🚤',
            'MARINE': '🚤',
            'All': '📦',
            '其他': '📦',
        }

        description_map = {
            'VEHICLE PARTS': '适用于各类汽车动力系统更换与维修，广泛用于乘用车、商用车等公路交通工具。',
            '汽车': '适用于各类汽车动力系统更换与维修，广泛用于乘用车、商用车等公路交通工具。',
            'TRACTOR PARTS': '专为大扭矩农业机械设计，适合犁地、播种、收割等农田作业环境。',
            '拖拉机': '专为大扭矩农业机械设计，适合犁地、播种、收割等农田作业环境。',
            'FORKLIFT PARTS': '专为物流搬运设计，适合仓库、港口、工厂等物料搬运场景。',
            '叉车': '专为物流搬运设计，适合仓库、港口、工厂等物料搬运场景。',
            'MINING EQUIPMENT PARTS': '专为矿业设备设计，适合矿山开采、巷道掘进等严苛环境。',
            '矿山': '专为矿业设备设计，适合矿山开采、巷道掘进等严苛环境。',
            'GENERATOR PARTS': '适用于各类发电设备，为建筑工程、矿山、工厂提供备用或主用电源。',
            '发电机': '适用于各类发电设备，为建筑工程、矿山、工厂提供备用或主用电源。',
            'All': '通用类别商品，应用范围广泛。',
            '其他': '通用类别商品，应用范围广泛。',
        }

        for cat_name, cat_products in category_groups.items():
            # 确定图标
            icon = '📦'
            for key, emo in icon_map.items():
                if key.upper() in cat_name.upper():
                    icon = emo
                    break

            # 确定描述
            description = description_map.get(cat_name, f'共 {len(cat_products)} 件相关商品，品质优良，应用广泛。')

            usage_categories.append({
                'name': cat_name,
                'icon': icon,
                'description': description,
                'product_count': len(cat_products),
            })

        # 按商品数量排序
        usage_categories.sort(key=lambda x: x['product_count'], reverse=True)

        return usage_categories
