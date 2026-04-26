# -*- coding: utf-8 -*-
"""
@File   : config_service.py
@Time   : 2026-04-21
@Desc   : AI 搜索 MVP 配置服务
"""

import logging

_logger = logging.getLogger(__name__)


class AiSearchMvpConfigService:
    """
    配置服务
    从 ai.search.mvp.config 模型读取配置
    """

    def __init__(self, env):
        self.env = env

    def _get_config(self):
        """获取配置记录（单例）"""
        return self.env['ai.search.mvp.config'].sudo().get_active_config()

    def _get_field_value(self, field_name, default=None):
        """安全获取字段值"""
        config = self._get_config()
        value = getattr(config, field_name, None)
        if value is None:
            return default
        return value

    @property
    def is_enabled(self):
        """是否启用 AI 搜索"""
        return self._get_field_value('enable_ai_search', False)

    @property
    def dify_api_base_url(self):
        """Dify API 基础 URL"""
        value = self._get_field_value('dify_api_base_url')
        return value if value else 'https://api.dify.ai/v1'

    @property
    def dify_api_key_raw(self):
        """获取原始 Dify API Key（仅内部使用）"""
        return self._get_field_value('dify_api_key') or ''

    @property
    def dify_api_key(self):
        """Dify API Key（脱敏后返回）"""
        key = self.dify_api_key_raw
        if key and len(key) > 8:
            return key[:4] + '****' + key[-4:]
        return key

    @property
    def dify_app_id(self):
        """Dify App ID"""
        return self._get_field_value('dify_app_id') or ''

    @property
    def dify_timeout(self):
        """Dify API 超时时间（秒）"""
        return self._get_field_value('dify_timeout') or 30

    @property
    def internal_token(self):
        """内部搜索接口 Token"""
        return self._get_field_value('internal_token') or ''

    @property
    def search_top_k(self):
        """默认返回商品数量"""
        return self._get_field_value('search_top_k') or 8

    @property
    def fallback_enabled(self):
        """是否启用 Fallback"""
        return self._get_field_value('enable_fallback', True)

    @property
    def log_enabled(self):
        """是否启用日志记录"""
        return self._get_field_value('enable_logging', True)

    @property
    def debug_mode(self):
        """是否开启调试模式"""
        return self._get_field_value('debug_mode', False)

    def get_dify_headers(self):
        """获取调用 Dify API 所需的请求头"""
        return {
            'Authorization': f'Bearer {self.dify_api_key_raw}',
            'Content-Type': 'application/json',
        }

    def validate_config(self):
        """验证配置是否完整有效"""
        if not self.is_enabled:
            return False, 'AI Search is not enabled'
        if not self.dify_api_base_url:
            return False, 'Dify API Base URL is not configured'
        if not self.dify_api_key_raw:
            return False, 'Dify API Key is not configured'
        if not self.dify_app_id:
            return False, 'Dify App ID is not configured'
        return True, None
