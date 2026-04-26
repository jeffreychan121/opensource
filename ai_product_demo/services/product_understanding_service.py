# -*- coding: utf-8 -*-
"""
商品理解服务 - 将 Odoo 商品转换为 AI 可理解的结构化对象
"""

from typing import Dict, List, Any, Optional


class ProductUnderstandingService:
    """
    商品理解层

    从 product.template 读取真实字段，转换为：
    - brand: 品牌
    - category: 类别
    - key_attributes: 关键属性
    - selling_points: 卖点
    - target_people: 目标人群
    - scenes: 使用场景
    - searchable_text: 可搜索文本
    - compare_features: 对比特征
    - recommendation_tags: 推荐标签
    """

    def __init__(self, env):
        self.env = env

    def get_product_understanding(self, product) -> Dict[str, Any]:
        """
        获取单个商品的理解对象

        Args:
            product: product.template 记录

        Returns:
            Dict: 商品理解结构化对象
        """
        return {
            'id': product.id,
            'name': product.name,
            'sku': product.default_code,
            'brand': product.brand_id.name if product.brand_id else None,
            'category': product.categ_id.name if product.categ_id else None,
            'price': product.list_price,
            'description': product.description_sale or '',
            'selling_point': product.x_selling_point or '',
            'target_people': product.x_target_people or '',
            'scenes': self._parse_scenes(product.x_scenario_tags),
            'weight': product.weight,
            'attributes': self._extract_attributes(product),
            'searchable_text': self._build_searchable_text(product),
            'compare_features': self._build_compare_features(product),
            'recommendation_tags': self._build_recommendation_tags(product),
        }

    def _parse_scenes(self, scenario_tags: str) -> List[str]:
        """解析场景标签"""
        if not scenario_tags:
            return []
        return [s.strip() for s in scenario_tags.split(',') if s.strip()]

    def _extract_attributes(self, product) -> Dict[str, str]:
        """提取商品属性"""
        attrs = {}
        if hasattr(product, 'attribute_line_ids'):
            for line in product.attribute_line_ids:
                attr_name = line.attribute_id.name
                values = [v.name for v in line.value_ids]
                if values:
                    attrs[attr_name] = values
        return attrs

    def _build_searchable_text(self, product) -> str:
        """构建可搜索文本"""
        parts = [
            product.name or '',
            product.default_code or '',
            product.description_sale or '',
            product.brand_id.name if product.brand_id else '',
            product.categ_id.name if product.categ_id else '',
            product.x_scenario_tags or '',
            product.x_selling_point or '',
            product.x_target_people or '',
        ]
        return ' '.join(filter(None, parts))

    def _build_compare_features(self, product) -> Dict[str, Any]:
        """构建对比特征"""
        return {
            'price': product.list_price,
            'weight': product.weight,
            'brand': product.brand_id.name if product.brand_id else None,
        }

    def _build_recommendation_tags(self, product) -> List[str]:
        """构建推荐标签"""
        tags = []
        if product.x_selling_point:
            tags.append(product.x_selling_point)
        if product.x_target_people:
            tags.extend([t.strip() for t in product.x_target_people.split(',')])
        if product.x_scenario_tags:
            tags.extend(self._parse_scenes(product.x_scenario_tags))
        return list(set(tags))

    def get_products_understanding(self, products) -> List[Dict[str, Any]]:
        """批量获取商品理解"""
        return [self.get_product_understanding(p) for p in products]

    def search_products_for_understanding(
        self,
        query: str = None,
        category: str = None,
        brand: str = None,
        min_price: float = None,
        max_price: float = None,
        scenes: List[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        基于理解字段搜索商品

        Args:
            query: 搜索关键词
            category: 分类名称
            brand: 品牌名称
            min_price: 最低价格
            max_price: 最高价格
            scenes: 场景标签列表
            limit: 返回数量限制

        Returns:
            List[Dict]: 商品理解对象列表
        """
        domain = [('sale_ok', '=', True), ('active', '=', True)]

        if query:
            domain.append(('name', 'ilike', f'%{query}%'))
        if category:
            domain.append(('categ_id.name', 'ilike', f'%{category}%'))
        if brand:
            domain.append(('brand_id.name', 'ilike', f'%{brand}%'))
        if min_price is not None:
            domain.append(('list_price', '>=', min_price))
        if max_price is not None:
            domain.append(('list_price', '<=', max_price))

        products = self.env['product.template'].search_read(
            domain,
            [
                'name', 'default_code', 'categ_id', 'list_price', 'brand_id',
                'description_sale', 'x_scenario_tags', 'x_selling_point',
                'x_target_people', 'weight', 'attribute_line_ids'
            ],
            limit=limit
        )

        # 转换为理解对象
        result = []
        for p in products:
            product = self.env['product.template'].browse(p['id'])
            result.append(self.get_product_understanding(product))

        # 如果有场景过滤
        if scenes:
            result = [r for r in result if any(s in r['scenes'] for s in scenes)]

        return result

    def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """根据SKU获取商品理解"""
        product = self.env['product.template'].search([
            ('default_code', '=', sku)
        ], limit=1)
        if product:
            return self.get_product_understanding(product)
        return None

    def get_products_by_category(self, category_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """根据分类获取商品理解列表"""
        products = self.env['product.template'].search([
            ('categ_id.name', 'ilike', f'%{category_name}%'),
            ('sale_ok', '=', True),
            ('active', '=', True)
        ], limit=limit)

        return self.get_products_understanding(products)

    def get_products_by_brand(self, brand_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """根据品牌获取商品理解列表"""
        products = self.env['product.template'].search([
            ('brand_id.name', 'ilike', f'%{brand_name}%'),
            ('sale_ok', '=', True),
            ('active', '=', True)
        ], limit=limit)

        return self.get_products_understanding(products)

    def get_similar_products(self, product_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """获取相似商品（基于分类和场景标签）"""
        product = self.env['product.template'].browse(product_id)
        if not product:
            return []

        # 基于分类和场景找相似商品
        scenes = self._parse_scenes(product.x_scenario_tags)
        domain = [
            ('sale_ok', '=', True),
            ('active', '=', True),
            ('categ_id', '=', product.categ_id.id),
            ('id', '!=', product_id)
        ]

        products = self.env['product.template'].search(domain, limit=limit * 2)

        # 计算相似度并排序
        similarities = []
        for p in products:
            p_scenes = set(self._parse_scenes(p.x_scenario_tags))
            common_scenes = len(set(scenes) & p_scenes) if scenes else 0
            similarities.append((common_scenes, p))

        similarities.sort(key=lambda x: x[0], reverse=True)
        similar_products = [p for _, p in similarities[:limit]]

        return self.get_products_understanding(similar_products)
