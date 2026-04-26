# -*- coding: utf-8 -*-
"""
@File   :   product_compare_service.py
@Time   :   2024-04-18
@Desc   :   商品对比服务
            支持对多个商品进行结构化对比
"""

import logging
from typing import Dict, Any, List, Optional
from collections import Counter

_logger = logging.getLogger(__name__)


class ProductCompareService:
    """
    商品对比服务

    负责对比多个商品的结构化差异，输出：
    - 相同点
    - 差异点
    - 核心参数对比
    - 卖点对比
    - 适用人群对比
    - 适用场景对比
    - 总结建议
    """

    def __init__(self, env):
        """
        初始化商品对比服务

        :param env: Odoo environment
        """
        self.env = env

    def compare_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        对比多个商品

        :param products: 商品理解后的数据列表（需要包含 compare_features）
        :return: 对比结果
        """
        if not products:
            return {'error': 'No products to compare'}

        if len(products) < 2:
            return {'error': 'Need at least 2 products to compare'}

        result = {
            'products': [self._summarize_product(p) for p in products],
            'same_points': self._find_same_points(products),
            'diff_points': self._find_diff_points(products),
            'attributes_compare': self._compare_attributes(products),
            'price_compare': self._compare_prices(products),
            'selling_points_compare': self._compare_selling_points(products),
            'target_people_compare': self._compare_target_people(products),
            'scenes_compare': self._compare_scenes(products),
            'recommendation': self._generate_recommendation(products),
        }

        return result

    def compare_by_ids(self, product_ids: List[int]) -> Dict[str, Any]:
        """
        根据商品ID对比

        :param product_ids: 商品ID列表
        :return: 对比结果
        """
        ProductTemplate = self.env['product.template']

        products = ProductTemplate.sudo().browse(product_ids).read([
            'name', 'list_price', 'description_sale',
            'categ_id', 'product_brand_id'
        ])

        return self.compare_products(products)

    def _summarize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """生成商品摘要"""
        return {
            'id': product.get('product_id') or product.get('id'),
            'name': product.get('name') or product.get('title', ''),
            'price': product.get('price'),
            'brand': self._get_brand_name(product),
            'category': self._get_category_name(product),
        }

    def _get_brand_name(self, product: Dict[str, Any]) -> Optional[str]:
        """获取品牌名"""
        brand = product.get('brand')
        if isinstance(brand, dict):
            return brand.get('name')
        return brand

    def _get_category_name(self, product: Dict[str, Any]) -> Optional[str]:
        """获取类目名"""
        category_path = product.get('category_path') or product.get('category_names', [])
        if category_path:
            return category_path[0] if isinstance(category_path, list) else str(category_path)
        return None

    def _find_same_points(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """找相同点"""
        same_points = []

        # 提取所有特征
        brands = [self._get_brand_name(p) for p in products]
        categories = [self._get_category_name(p) for p in products]

        # 品牌相同
        if len(set(brands)) == 1 and brands[0]:
            same_points.append({
                'type': 'brand',
                'value': brands[0],
                'description': f'都是 {brands[0]} 品牌',
            })

        # 类目相同
        if len(set(categories)) == 1 and categories[0]:
            same_points.append({
                'type': 'category',
                'value': categories[0],
                'description': f'都属于 {categories[0]} 类目',
            })

        # 卖点相同
        all_sp = [set(p.get('selling_points', []) or []) for p in products]
        if all_sp:
            common_sp = set.intersection(*all_sp) if all([all_sp]) else set()
            if common_sp:
                same_points.append({
                    'type': 'selling_points',
                    'value': list(common_sp),
                    'description': f'共同卖点: {", ".join(common_sp)}',
                })

        return same_points

    def _find_diff_points(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """找差异点"""
        diff_points = []

        # 价格差异
        prices = [p.get('price') or 0 for p in products]
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            if max_price > min_price * 1.1:  # 差异超过10%
                diff_points.append({
                    'type': 'price',
                    'description': f'价格跨度 {min_price:.0f}元 ~ {max_price:.0f}元',
                    'details': [
                        {'product_id': p.get('id'), 'price': p.get('price')}
                        for p in products
                    ]
                })

        # 卖点差异
        all_sp = [set(p.get('selling_points', []) or []) for p in products]
        if all_sp:
            all_unique_sp = set.union(*all_sp)
            common_sp = set.intersection(*all_sp) if all([all_sp]) else set()
            unique_sp = all_unique_sp - common_sp
            if unique_sp:
                diff_points.append({
                    'type': 'selling_points',
                    'description': '各有特色卖点',
                    'details': [
                        {
                            'product_id': p.get('id'),
                            'unique_points': list(set(p.get('selling_points', []) or []) - common_sp)
                        }
                        for p in products
                    ]
                })

        return diff_points

    def _compare_attributes(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对比属性"""
        all_attributes = []
        for p in products:
            attrs = p.get('attributes', []) or []
            if isinstance(attrs, list):
                attr_dict = {a.get('name'): a.get('value') for a in attrs if isinstance(a, dict)}
                all_attributes.append(attr_dict)
            elif isinstance(attrs, dict):
                all_attributes.append(attrs)
            else:
                all_attributes.append({})

        # 找出所有属性名
        all_attr_names = set()
        for attrs in all_attributes:
            all_attr_names.update(attrs.keys())

        if not all_attr_names:
            return {'has_comparison': False}

        compare_result = {'has_comparison': True, 'attributes': {}}

        for attr_name in sorted(all_attr_names):
            values = [attrs.get(attr_name) for attrs in all_attributes]
            unique_values = set(v for v in values if v)

            if len(unique_values) > 1:
                compare_result['attributes'][attr_name] = {
                    'values': [
                        {'product_id': p.get('id'), 'value': v}
                        for p, v in zip(products, values)
                    ],
                    'is_different': True,
                }
            else:
                compare_result['attributes'][attr_name] = {
                    'values': [{'product_id': p.get('id'), 'value': values[0]}],
                    'is_different': False,
                }

        return compare_result

    def _compare_prices(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对比价格"""
        prices = [(p.get('id'), p.get('price', 0)) for p in products]
        prices_sorted = sorted(prices, key=lambda x: x[1])

        return {
            'range': {
                'min': prices_sorted[0][1],
                'max': prices_sorted[-1][1],
            },
            'cheapest': {
                'product_id': prices_sorted[0][0],
                'price': prices_sorted[0][1],
            },
            'most_expensive': {
                'product_id': prices_sorted[-1][0],
                'price': prices_sorted[-1][1],
            },
        }

    def _compare_selling_points(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对比卖点"""
        all_sp = [p.get('selling_points', []) or [] for p in products]

        return {
            'all': [sp for sp_list in all_sp for sp in sp_list],
            'common': list(set.intersection(*[set(sp) for sp in all_sp if sp])) if all_sp else [],
            'unique': [
                {
                    'product_id': p.get('id'),
                    'unique_points': list(set(p.get('selling_points', []) or []) - set.intersection(*[set(sp) for sp in all_sp if sp]))
                }
                if all_sp else {'product_id': p.get('id'), 'unique_points': []}
                for p in products
            ],
        }

    def _compare_target_people(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对比目标人群"""
        all_people = [set(p.get('target_people', []) or []) for p in products]

        return {
            'all': list(set.union(*all_people)) if all_people else [],
            'common': list(set.intersection(*all_people)) if all_people else [],
            'by_product': [
                {'product_id': p.get('product_id') or p.get('id'), 'target_people': list(set(p.get('target_people', []) or []))}
                for p in products
            ],
        }

    def _compare_scenes(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对比使用场景"""
        all_scenes = [set(p.get('scenes', []) or []) for p in products]

        return {
            'all': list(set.union(*all_scenes)) if all_scenes else [],
            'common': list(set.intersection(*all_scenes)) if all_scenes else [],
            'by_product': [
                {'product_id': p.get('id'), 'scenes': list(set(p.get('scenes', []) or []))}
                for p in products
            ],
        }

    def _generate_recommendation(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成推荐建议"""
        recommendation = {
            'summary': '',
            'for_different_needs': [],
        }

        if not products:
            return recommendation

        # 按人群分组推荐
        people_products = {}
        for p in products:
            for people in (p.get('target_people', []) or []):
                if people not in people_products:
                    people_products[people] = []
                people_products[people].append(p)

        for people, prods in people_products.items():
            if len(prods) >= 2:
                recommendation['for_different_needs'].append({
                    'people': people,
                    'suggested_product': prods[0].get('id') if prods else None,
                    'reason': f'适合{people}使用',
                })

        # 生成综合建议
        if len(products) == 2:
            p1, p2 = products[0], products[1]
            price1 = p1.get('price', 0)
            price2 = p2.get('price', 0)

            recommendation['summary'] = self._generate_summary(p1, p2)

        return recommendation

    def _generate_summary(self, p1: Dict[str, Any], p2: Dict[str, Any]) -> str:
        """生成对比总结"""
        summaries = []

        # 价格对比
        price1 = p1.get('price', 0)
        price2 = p2.get('price', 0)

        if price1 < price2:
            summaries.append(f'{p1.get("name", "商品1")}价格更亲民')
        elif price2 < price1:
            summaries.append(f'{p2.get("name", "商品2")}价格更亲民')

        # 品牌对比
        brand1 = self._get_brand_name(p1)
        brand2 = self._get_brand_name(p2)
        if brand1 and brand2 and brand1 != brand2:
            summaries.append(f'两者分别为{brand1}和{brand2}品牌')

        # 场景对比
        scenes1 = set(p1.get('scenes', []) or [])
        scenes2 = set(p2.get('scenes', []) or [])
        common_scenes = scenes1 & scenes2
        if common_scenes:
            summaries.append(f'共同适合: {", ".join(common_scenes)}')

        return '; '.join(summaries) if summaries else '两款商品各有特色'
