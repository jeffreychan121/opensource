# -*- coding: utf-8 -*-
"""
@File   :   ranking_service.py
@Time   :   2024-04-14
@Desc   :   商品搜索结果排序服务
"""

import logging
from typing import List, Dict, Any

from odoo import models

_logger = logging.getLogger(__name__)


class AiRankingService:
    """
    搜索结果排序服务
    负责对搜索结果进行重排，综合考虑多个因素
    """

    def __init__(self, env):
        """
        初始化排序服务

        :param env: Odoo environment
        """
        self.env = env

    def reorder_by_text_match(self, products: models.BaseModel,
                              keywords: List[str]) -> models.BaseModel:
        """
        根据文本匹配度重排商品

        :param products: product.template recordset
        :param keywords: 关键词列表
        :return: 重新排序的 recordset
        """
        if not products or not keywords:
            return products

        # 计算每个商品的匹配得分
        scored_products = []
        for product in products:
            score = self._calculate_text_score(product, keywords)
            scored_products.append((product.id, score))

        # 按得分降序排序
        scored_products.sort(key=lambda x: x[1], reverse=True)

        # 根据排序后的 ID 重新排序
        sorted_ids = [pid for pid, score in scored_products]
        return products.sorted(key=lambda p: sorted_ids.index(p.id) if p.id in sorted_ids else 999)

    def _calculate_text_score(self, product: models.BaseModel,
                                keywords: List[str]) -> float:
        """
        计算单个商品的文本匹配得分

        :param product: 商品记录
        :param keywords: 关键词列表
        :return: 匹配得分 (0-100)
        """
        score = 0.0

        # 收集所有文本字段
        text_fields = [
            product.name or '',
            product.default_code or '',
            product.description_sale or '',
            product.description or '',
        ]

        # 获取属性值文本
        attribute_texts = []
        for line in product.attribute_line_ids:
            attribute_texts.append(line.attribute_id.name or '')
            attribute_texts.extend([v.name or '' for v in line.value_ids])
        text_fields.extend(attribute_texts)

        # 获取类别文本
        if product.categ_id:
            text_fields.append(product.categ_id.name or '')

        # 获取品牌文本
        if hasattr(product, 'product_brand_id') and product.product_brand_id:
            text_fields.append(product.product_brand_id.name or '')

        all_text = ' '.join(text_fields).lower()
        keywords_lower = [k.lower() for k in keywords]

        # 精确匹配关键词
        for keyword in keywords_lower:
            if keyword in all_text:
                score += 10

                # 计算密度（关键词出现次数 / 总词数）
                count = all_text.count(keyword)
                score += min(count * 2, 10)  # 最多额外加 10 分

                # 关键词在名称中出现权重更高
                if keyword in (product.name or '').lower():
                    score += 15

                # 关键词在描述中出现
                if keyword in (product.description_sale or '').lower():
                    score += 5

        # 名称精确匹配（不区分大小写）
        for keyword in keywords_lower:
            if (product.name or '').lower() == keyword:
                score += 30

        return score

    def rerank(self, products: List[Dict[str, Any]],
               intent: Dict[str, Any],
               vector_similarity: Dict[int, float] = None) -> List[Dict[str, Any]]:
        """
        综合重排商品列表

        :param products: 商品字典列表
        :param intent: 解析后的搜索意图
        :param vector_similarity: 商品 ID 到向量相似度的映射
        :return: 重排后的商品列表
        """
        if not products:
            return products

        scored_products = []

        for product in products:
            score = self._calculate_comprehensive_score(
                product, intent, vector_similarity
            )
            scored_products.append((product, score))

        # 按综合得分降序
        scored_products.sort(key=lambda x: x[1], reverse=True)

        return [p for p, score in scored_products]

    def _calculate_comprehensive_score(self, product: Dict[str, Any],
                                        intent: Dict[str, Any],
                                        vector_similarity: Dict[int, float] = None) -> float:
        """
        计算商品的综合排序得分

        :param product: 商品信息字典
        :param intent: 搜索意图
        :param vector_similarity: 向量相似度（可选）
        :return: 综合得分
        """
        score = 0.0

        # ========== 1. 强约束满足度 (40分) ==========
        constraint_score = self._evaluate_constraint_satisfaction(product, intent)
        score += constraint_score * 40

        # ========== 2. 文本匹配度 (30分) ==========
        text_score = self._evaluate_text_match(product, intent)
        score += text_score * 30

        # ========== 3. 向量相似度 (如果有) (20分) ==========
        if vector_similarity and product['id'] in vector_similarity:
            similarity = vector_similarity[product['id']]
            score += similarity * 20

        # ========== 4. 业务权重 (10分) ==========
        business_score = self._evaluate_business_factors(product)
        score += business_score * 10

        return score

    def _evaluate_constraint_satisfaction(self, product: Dict[str, Any],
                                           intent: Dict[str, Any]) -> float:
        """
        评估商品满足强约束的程度

        :param product: 商品信息
        :param intent: 搜索意图
        :return: 得分 (0-1)
        """
        score = 1.0

        # 检查价格约束
        budget_max = intent.get('budget_max')
        budget_min = intent.get('budget_min')
        price = product.get('price', 0)

        if budget_max and price > budget_max:
            return 0.0  # 超出预算
        if budget_min and price < budget_min:
            score *= 0.5  # 低于最低预算

        # 检查排除属性
        color_exclude = intent.get('color_exclude', [])
        attributes = product.get('attributes', [])
        for color in color_exclude:
            if any(color.lower() in attr.lower() for attr in attributes):
                return 0.0

        # 检查必须包含的属性
        must_have = intent.get('must_have', [])
        if must_have:
            matched = sum(1 for attr in must_have
                         if any(attr.lower() in a.lower() for a in attributes))
            score *= (matched / len(must_have)) if must_have else 0

        return max(0.0, min(1.0, score))

    def _evaluate_text_match(self, product: Dict[str, Any],
                             intent: Dict[str, Any]) -> float:
        """
        评估文本匹配程度

        :param product: 商品信息
        :param intent: 搜索意图
        :return: 得分 (0-1)
        """
        keywords = intent.get('keywords', [])
        if not keywords:
            return 0.5  # 无关键词时给中等分

        score = 0.0
        matched = 0

        # 检查各文本字段
        text_fields = [
            product.get('name', ''),
            product.get('default_code', ''),
            product.get('description_sale', ''),
            product.get('brand', ''),
        ]
        text_fields.extend(product.get('attributes', []))
        text_fields.extend(product.get('category_names', []))

        all_text = ' '.join(text_fields).lower()
        keywords_lower = [k.lower() for k in keywords]

        for keyword in keywords_lower:
            if keyword in all_text:
                matched += 1

        if keywords:
            score = matched / len(keywords)

        return max(0.0, min(1.0, score))

    def _evaluate_business_factors(self, product: Dict[str, Any]) -> float:
        """
        评估业务因素

        :param product: 商品信息
        :return: 得分 (0-1)
        """
        score = 0.5  # 基础分

        # 可销售状态
        if product.get('sale_ok'):
            score += 0.2

        # 有图片
        if product.get('image_url') and '/plhdr.gif' not in product.get('image_url', ''):
            score += 0.1

        return min(1.0, score)
