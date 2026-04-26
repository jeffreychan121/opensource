# -*- coding: utf-8 -*-
"""
@File   :   fallback_service.py
@Time   :   2024-04-14
@Desc   :   Fallback 降级服务
"""

import logging
from typing import Dict, Any, Tuple, Optional, List

from odoo import _

_logger = logging.getLogger(__name__)


class AiFallbackService:
    """
    Fallback 降级服务
    当 Dify 服务不可用时，提供本地搜索能力
    """

    def __init__(self, env):
        """
        初始化 Fallback 服务

        :param env: Odoo environment
        """
        self.env = env
        self._search_service = None
        self._config_service = None

    @property
    def config_service(self):
        """懒加载配置服务"""
        if self._config_service is None:
            from .config_service import AiSearchConfigService
            self._config_service = AiSearchConfigService(self.env)
        return self._config_service

    @property
    def search_service(self):
        """懒加载搜索服务"""
        if self._search_service is None:
            from .search_service import AiSearchService
            self._search_service = AiSearchService(self.env)
        return self._search_service

    def is_available(self) -> bool:
        """
        检查 Fallback 是否可用

        :return: 是否可用
        """
        return self.config_service.fallback_enabled

    def execute_fallback(self, query: str, session_context: Optional[Dict] = None,
                          top_k: Optional[int] = None,
                          lang: str = 'zh_CN',
                          page: int = 1) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行 Fallback 搜索

        :param query: 用户查询
        :param session_context: 会话上下文
        :param top_k: 返回数量
        :param lang: 语言
        :param page: 页码（从1开始）
        :return: tuple (products, result_info)
        """
        _logger.info('Executing fallback search for query: %s, page: %s', query[:50], page)

        try:
            # 使用搜索服务的 fallback 方法
            products, latency_ms, has_more = self.search_service.fallback_search(
                query=query,
                top_k=top_k,
                lang=lang,
                page=page
            )

            # 生成简单的总结
            summary = self._generate_simple_summary(products, query)

            result_info = {
                'success': True,
                'fallback_used': True,
                'summary': summary,
                'latency_ms': latency_ms,
                'product_count': len(products),
                'has_more': has_more,
            }

            return products, result_info

        except Exception as e:
            _logger.error('Fallback search error: %s', str(e), exc_info=True)

            result_info = {
                'success': False,
                'fallback_used': True,
                'error': str(e),
                'products': [],
                'product_count': 0,
            }

            return [], result_info

    def _generate_simple_summary(self, products: List[Dict[str, Any]],
                                  query: str) -> str:
        """
        生成简单的总结（Fallback 模式）

        :param products: 商品列表
        :param query: 用户查询
        :return: 总结文本
        """
        if not products:
            return _('No products found matching your search. Please try different keywords.')

        count = len(products)

        if count == 1:
            return _('Found 1 product matching your search.')
        else:
            return _('Found %d products matching your search.') % count

    def generate_suggestions(self, query: str, failed_intent: Optional[Dict] = None) -> Dict[str, Any]:
        """
        当 Fallback 也没有结果时，生成建议

        :param query: 用户查询
        :param failed_intent: 失败的意图（如果有）
        :return: 建议字典
        """
        suggestions = {
            'suggestions': [],
            'expanded_query': None,
            'alternative_queries': [],
        }

        # 基于查询词生成替代查询
        if failed_intent:
            keywords = failed_intent.get('keywords', [])

            # 尝试放宽条件
            if failed_intent.get('budget_max'):
                suggestions['alternative_queries'].append(
                    _('Try increasing your budget or removing price limit')
                )

            if failed_intent.get('color_exclude'):
                suggestions['alternative_queries'].append(
                    _('Try removing color restrictions')
                )

            if keywords:
                # 简化的替代查询
                suggestions['alternative_queries'].extend(keywords[:2])

        # 通用建议
        suggestions['suggestions'] = [
            _('Try more general keywords'),
            _('Check your spelling'),
            _('Try a different category'),
            _('Remove some filters'),
        ]

        return suggestions
