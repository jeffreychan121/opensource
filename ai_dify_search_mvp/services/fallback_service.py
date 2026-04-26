# -*- coding: utf-8 -*-
"""
@File   : fallback_service.py
@Time   : 2026-04-21
@Desc   : Fallback 降级服务
"""

import logging
from typing import Dict, Any, Tuple, Optional, List

from odoo import _

_logger = logging.getLogger(__name__)


class AiSearchMvpFallbackService:
    """
    Fallback 降级服务
    """

    def __init__(self, env):
        self.env = env
        self._search_service = None
        self._config_service = None

    @property
    def config_service(self):
        if self._config_service is None:
            from .config_service import AiSearchMvpConfigService
            self._config_service = AiSearchMvpConfigService(self.env)
        return self._config_service

    @property
    def search_service(self):
        if self._search_service is None:
            from .search_service import AiSearchMvpService
            self._search_service = AiSearchMvpService(self.env)
        return self._search_service

    def is_available(self) -> bool:
        """检查 Fallback 是否可用"""
        return self.config_service.fallback_enabled

    def execute_fallback(self, query: str,
                         top_k: Optional[int] = None,
                         lang: str = 'zh_CN') -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        执行 Fallback 搜索
        """
        _logger.info('Executing fallback search for query: %s', query[:50])

        try:
            products, latency_ms, has_more = self.search_service.fallback_search(
                query=query,
                top_k=top_k,
                lang=lang,
            )

            summary = _('AI 服务暂时不可用，已为你返回基础搜索结果。')

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
            _logger.error('Fallback search error: %s', str(e))

            result_info = {
                'success': False,
                'fallback_used': True,
                'error': str(e),
                'product_count': 0,
            }

            return [], result_info