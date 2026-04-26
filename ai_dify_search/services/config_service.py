# -*- coding: utf-8 -*-
"""
@File   :   config_service.py
@Time   :   2024-04-14
@Desc   :   AI 搜索模块配置服务
"""

import logging

_logger = logging.getLogger(__name__)


class AiSearchConfigService:
    """
    配置服务
    统一管理 AI 搜索模块的所有配置参数
    从 ai.dify.config 数据库表读取
    """

    def __init__(self, env):
        """
        初始化配置服务

        :param env: Odoo environment
        """
        self.env = env

    def _get_config(self):
        """获取配置记录（单例）"""
        return self.env['ai.dify.config'].sudo().get_active_config()

    def _get_field_value(self, field_name, default=None):
        """安全获取字段值"""
        config = self._get_config()
        value = getattr(config, field_name, None)
        if value is None:
            return default
        return value

    # ==================== 开关配置 ====================

    @property
    def is_enabled(self):
        """是否启用 AI 搜索"""
        return self._get_field_value('ai_search_enabled', False)

    @property
    def is_debug_mode(self):
        """是否开启调试模式"""
        return self._get_field_value('debug_mode', False)

    # ==================== Dify 配置 ====================

    @property
    def dify_api_base_url(self):
        """Dify API 基础 URL"""
        value = self._get_field_value('dify_api_base_url')
        return value if value else 'https://api.dify.ai/v1'

    @property
    def dify_api_key(self):
        """Dify API Key（脱敏后返回）"""
        key = self.dify_api_key_raw
        if key and len(key) > 8:
            return key[:4] + '****' + key[-4:]
        return key

    @property
    def dify_api_key_raw(self):
        """获取原始 Dify API Key（仅内部使用）"""
        return self._get_field_value('dify_api_key') or ''

    @property
    def dify_app_id(self):
        """Dify App ID"""
        return self._get_field_value('dify_app_id') or ''

    @property
    def dify_compare_api_base_url(self):
        """AI对比 Dify API 基础 URL"""
        value = self._get_field_value('dify_compare_api_base_url')
        return value if value else self.dify_api_base_url  # 默认为 AI 搜索的 URL

    @property
    def dify_compare_api_key(self):
        """AI对比 Dify API Key"""
        return self._get_field_value('dify_compare_api_key') or ''

    @property
    def dify_compare_app_id(self):
        """AI对比 Dify App ID"""
        return self._get_field_value('dify_compare_app_id') or ''

    @property
    def dify_user_prefix(self):
        """Dify 用户标识前缀"""
        value = self._get_field_value('dify_user_prefix')
        return value if value else 'odoo_user_'

    @property
    def dify_timeout(self):
        """Dify API 超时时间（秒）"""
        return self._get_field_value('dify_timeout') or 30

    # ==================== 内部搜索配置 ====================

    @property
    def internal_search_token(self):
        """内部搜索接口 Token"""
        return self._get_field_value('internal_search_token') or ''

    # ==================== 搜索参数 ====================

    @property
    def search_top_k(self):
        """默认返回商品数量"""
        return self._get_field_value('search_top_k') or 8

    @property
    def session_expire_hours(self):
        """会话过期时间（小时）"""
        return self._get_field_value('session_expire_hours') or 24

    # ==================== 向量搜索配置 ====================

    @property
    def vector_search_enabled(self):
        """是否启用向量搜索"""
        return self._get_field_value('vector_search_enabled', False)

    @property
    def vector_search_limit(self):
        """向量搜索返回数量限制"""
        return self._get_field_value('vector_search_limit') or 20

    # ==================== 功能开关 ====================

    @property
    def log_enabled(self):
        """是否启用日志记录"""
        return self._get_field_value('ai_search_log_enabled', True)

    @property
    def fallback_enabled(self):
        """是否启用 Fallback"""
        return self._get_field_value('fallback_enabled', True)

    @property
    def followup_enabled(self):
        """是否启用追问功能"""
        return self._get_field_value('followup_enabled', True)

    @property
    def search_cache_ttl(self):
        """搜索缓存 TTL（秒）"""
        return self._get_field_value('search_cache_ttl') or 300

    # ==================== 便捷方法 ====================

    def get_dify_headers(self):
        """
        获取调用 Dify API 所需的请求头

        :return: dict of headers
        """
        return {
            'Authorization': f'Bearer {self.dify_api_key_raw}',
            'Content-Type': 'application/json',
        }

    def validate_config(self):
        """
        验证配置是否完整有效

        :return: tuple (is_valid, error_message)
        """
        if not self.is_enabled:
            return False, 'AI Search is not enabled'

        if not self.dify_api_base_url:
            return False, 'Dify API Base URL is not configured'

        if not self.dify_api_key_raw:
            return False, 'Dify API Key is not configured'

        if not self.dify_app_id:
            return False, 'Dify App ID is not configured'

        return True, None

    def get_all_config(self):
        """
        获取所有配置（用于调试页面展示）

        :return: dict of all configuration values
        """
        return {
            'enabled': self.is_enabled,
            'debug_mode': self.is_debug_mode,
            'dify_api_base_url': self.dify_api_base_url,
            'dify_api_key': self.dify_api_key,  # 脱敏
            'dify_app_id': self.dify_app_id,
            'dify_user_prefix': self.dify_user_prefix,
            'dify_timeout': self.dify_timeout,
            'internal_search_token_set': bool(self.internal_search_token),
            'search_top_k': self.search_top_k,
            'session_expire_hours': self.session_expire_hours,
            'vector_search_enabled': self.vector_search_enabled,
            'vector_search_limit': self.vector_search_limit,
            'log_enabled': self.log_enabled,
            'fallback_enabled': self.fallback_enabled,
            'followup_enabled': self.followup_enabled,
            'search_cache_ttl': self.search_cache_ttl,
        }
