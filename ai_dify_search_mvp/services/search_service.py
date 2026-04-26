# -*- coding: utf-8 -*-
"""
@File   : search_service.py
@Time   : 2026-04-21
@Desc   : Odoo 商品搜索服务（MVP简化版）
"""

import logging
import time
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from odoo import models, fields, api, SUPERUSER_ID
from odoo.osv.expression import AND, OR

_logger = logging.getLogger(__name__)


class AiSearchMvpService:
    """
    Odoo 商品搜索服务
    负责根据解析后的意图执行真实的商品检索
    """

    def __init__(self, env):
        self.env = env
        self._config_service = None

    @property
    def config_service(self):
        """懒加载配置服务"""
        if self._config_service is None:
            from .config_service import AiSearchMvpConfigService
            self._config_service = AiSearchMvpConfigService(self.env)
        return self._config_service

    def search_products(self, parsed_intent: Dict[str, Any],
                        top_k: Optional[int] = None,
                        lang: str = 'zh_CN') -> Tuple[List[Dict[str, Any]], Dict[str, Any], float]:
        """
        根据解析后的意图搜索商品

        :param parsed_intent: Dify 解析出的意图 JSON
        :param top_k: 返回商品数量限制
        :param lang: 语言代码
        :return: tuple (products, applied_filters, latency_ms)
        """
        start_time = time.time()

        if top_k is None:
            top_k = self.config_service.search_top_k

        domain, applied_filters = self._build_search_domain(parsed_intent, lang)
        _logger.info('Searching products with domain: %s, top_k=%d', domain, top_k)

        product_ids = self._execute_search(domain, top_k, parsed_intent)
        products = self._get_product_details(product_ids, lang)

        latency_ms = (time.time() - start_time) * 1000
        _logger.info('Product search completed: found=%d, latency=%.2fms', len(products), latency_ms)

        return products, applied_filters, latency_ms

    def _build_search_domain(self, intent: Dict[str, Any],
                              lang: str = 'zh_CN') -> Tuple[List, Dict]:
        """
        根据意图构建搜索域
        """
        domain = []
        applied_filters = {}

        domain.append(('sale_ok', '=', True))
        domain.append(('active', '=', True))
        applied_filters['sale_ok'] = True

        budget_min = intent.get('budget_min')
        budget_max = intent.get('budget_max')

        if budget_max is not None and budget_max > 0:
            domain.append(('list_price', '<=', budget_max))
            applied_filters['budget_max'] = budget_max

        if budget_min is not None and budget_min > 0:
            domain.append(('list_price', '>=', budget_min))
            applied_filters['budget_min'] = budget_min

        category = intent.get('category')
        if category:
            categ_ids = self._find_category(category)
            if categ_ids:
                domain.append(('categ_id', 'child_of', categ_ids))
                applied_filters['category'] = category

        keywords = intent.get('keywords', [])
        if keywords:
            applied_filters['keywords'] = keywords
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append(('name', 'ilike', kw))
                keyword_conditions.append(('description_sale', 'ilike', kw))
            keyword_domain = ['|'] * (len(keyword_conditions) - 1) + keyword_conditions if len(keyword_conditions) > 1 else keyword_conditions
            domain = AND([domain, keyword_domain])

        return domain, applied_filters

    def _execute_search(self, domain: List, top_k: int,
                        intent: Dict[str, Any]) -> List[int]:
        """执行商品搜索"""
        keywords = intent.get('keywords', [])
        search_term = keywords[0] if keywords else ''

        if search_term:
            sql = """
                SELECT id FROM product_template
                WHERE sale_ok = true
                  AND active = true
                  AND (
                      COALESCE(name->>'zh_CN', name->>'en_US', '') ILIKE %s
                      OR COALESCE(default_code, '') ILIKE %s
                      OR COALESCE(description_sale->>'zh_CN', description_sale->>'en_US', '') ILIKE %s
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
        else:
            products = self.env['product.template'].sudo().search(
                domain, limit=top_k * 3, order='id DESC'
            )
            product_ids = products.ids

        if not product_ids and domain:
            fallback_domain = self._build_keyword_fallback_domain(intent)
            if fallback_domain:
                products = self.env['product.template'].sudo().search(
                    fallback_domain, limit=top_k * 3, order='id DESC'
                )
                product_ids = products.ids

        return product_ids[:top_k]

    def _build_keyword_fallback_domain(self, intent: Dict[str, Any]) -> List:
        """构建仅使用关键词的降级搜索域"""
        domain = []
        domain.append(('sale_ok', '=', True))
        domain.append(('active', '=', True))

        keywords = intent.get('keywords', [])
        if not keywords:
            category = intent.get('category')
            if category:
                keywords = [category]

        if keywords:
            keyword_domain = ['|', '|',
                ('name', 'ilike', keywords[0]),
                ('default_code', 'ilike', keywords[0]),
                ('description_sale', 'ilike', keywords[0])
            ]
            domain = AND([domain, keyword_domain])

        return domain

    def _find_category(self, category_name: str) -> List[int]:
        """查找匹配的类目"""
        if not category_name:
            return []

        try:
            categs = self.env['product.public.category'].search([
                '|',
                ('name', 'ilike', category_name),
                ('name', 'ilike', category_name.replace(' ', ''))
            ], limit=10)
            return categs.ids
        except Exception:
            return []

    def _get_product_details(self, product_ids: List[int],
                               lang: str = 'zh_CN') -> List[Dict[str, Any]]:
        """获取商品详细信息"""
        if not product_ids:
            return []

        lang_key = 'zh_CN' if lang == 'zh_CN' else 'en_US'
        products = self.env['product.template'].with_context(lang=lang_key).sudo().browse(product_ids)

        result = []
        for product in products:
            image_url = ''
            if product.image_512:
                image_url = '/web/image/product.template/%d/image_512' % product.id

            name = product.name or ''
            description_sale = product.description_sale or ''
            if isinstance(product.name, dict):
                name = product.name.get(lang_key, product.name.get('en_US', ''))
            if isinstance(product.description_sale, dict):
                description_sale = description_sale.get(lang_key, description_sale.get('en_US', ''))

            short_description = description_sale or ''
            if len(short_description) > 100:
                short_description = short_description[:100] + '...'

            # Convert CNY to USD (approximate rate 1 USD = 7.2 CNY)
            price_cny = product.list_price or 0
            price_usd = round(price_cny / 7.2, 2)

            result.append({
                'id': product.id,
                'name': name,
                'default_code': product.default_code or '',
                'price': price_usd,
                'currency': 'USD',
                'url': '/shop/product/%s' % product.id,
                'image_url': image_url,
                'short_description': short_description,
                'description_sale': description_sale,
                'sale_ok': product.sale_ok,
            })

        return result

    def fallback_search(self, query: str, top_k: Optional[int] = None,
                       lang: str = 'zh_CN',
                       page: int = 1) -> Tuple[List[Dict[str, Any]], float, bool]:
        """
        本地 Fallback 搜索
        """
        start_time = time.time()

        if top_k is None:
            top_k = self.config_service.search_top_k

        intent = self._simple_intent_parse(query)
        keywords = intent.get('keywords', [])
        search_term = keywords[0] if keywords else query
        lang_key = 'zh_CN' if lang == 'zh_CN' else 'en_US'
        offset = (page - 1) * top_k

        try:
            self.env.cr.execute("ROLLBACK")
        except Exception:
            pass

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
        has_more = (offset + len(product_ids)) < total_count

        try:
            self.env.cr.execute("COMMIT")
        except Exception:
            pass

        products = self._get_product_details(product_ids, lang)
        latency_ms = (time.time() - start_time) * 1000

        return products, latency_ms, has_more

    def _simple_intent_parse(self, query: str) -> Dict[str, Any]:
        """简单的本地意图解析"""
        intent = {
            'category': None,
            'budget_min': None,
            'budget_max': None,
            'keywords': [],
        }

        query_lower = query.lower()

        budget_max_match = re.search(r'(\d+)\s*(元|块)?\s*(以内|以下|不超过|低于)', query)
        if budget_max_match:
            intent['budget_max'] = float(budget_max_match.group(1))

        range_match = re.search(r'(\d+)\s*-\s*(\d+)\s*(元|块)?', query)
        if range_match:
            intent['budget_min'] = float(range_match.group(1))
            intent['budget_max'] = float(range_match.group(2))

        remaining = re.sub(r'\d+\s*元以内|\d+\s*元以下|\d+\s*-\s*\d+\s*元?', '', query)
        remaining = re.sub(r'[^\w\s]', ' ', remaining)
        words = [w.strip() for w in remaining.split() if len(w.strip()) > 1]

        stop_words = ['帮我', '给我', '找一下', '推荐', '有没有', '想要', '需要', '看看']
        intent['keywords'] = [w for w in words if w not in stop_words] or [query]

        return intent