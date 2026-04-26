# -*- coding: utf-8 -*-
"""
@File   : test_ai_dify_search_mvp.py
@Time   : 2026-04-21
@Desc   : AI 搜索 MVP 单元测试
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock


class TestAiSearchMvpConfigService(unittest.TestCase):
    """测试配置服务"""

    def test_config_service_default_values(self):
        """测试默认配置值"""
        from ai_dify_search_mvp.services.config_service import AiSearchMvpConfigService

        mock_env = Mock()
        mock_config = Mock()
        mock_config.enable_ai_search = False
        mock_config.dify_api_base_url = 'https://api.dify.ai/v1'
        mock_config.dify_api_key = ''
        mock_config.dify_app_id = ''
        mock_config.dify_timeout = 30
        mock_config.internal_token = ''
        mock_config.search_top_k = 8
        mock_config.enable_fallback = True
        mock_config.enable_logging = True
        mock_config.debug_mode = False

        with patch.object(Mock, '_get_config', return_value=mock_config):
            service = AiSearchMvpConfigService(mock_env)
            self.assertEqual(service.dify_timeout, 30)
            self.assertEqual(service.search_top_k, 8)
            self.assertTrue(service.fallback_enabled)


class TestDifyServiceResponseParsing(unittest.TestCase):
    """测试 Dify 响应解析"""

    def test_parse_response_with_valid_json(self):
        """测试解析包含有效 JSON 的响应"""
        from ai_dify_search_mvp.services.dify_service import DifyService

        mock_env = Mock()
        service = DifyService(mock_env)

        response = {
            'answer': '{"category": "手机", "budget_max": 3000, "keywords": ["手机", "5G"]}',
            'conversation_id': 'conv_123',
        }

        result = service.parse_response(response)

        self.assertTrue(result['success'])
        self.assertEqual(result['parsed_intent']['category'], '手机')
        self.assertEqual(result['parsed_intent']['budget_max'], 3000)

    def test_parse_response_missing_answer(self):
        """测试解析缺少 answer 字段的响应"""
        from ai_dify_search_mvp.services.dify_service import DifyService, DifyServiceError

        mock_env = Mock()
        service = DifyService(mock_env)

        response = {'conversation_id': 'conv_123'}

        with self.assertRaises(DifyServiceError):
            service.parse_response(response)


class TestSearchServiceIntentParse(unittest.TestCase):
    """测试搜索服务的意图解析"""

    def test_simple_intent_parse_budget_max(self):
        """测试解析最高预算"""
        from ai_dify_search_mvp.services.search_service import AiSearchMvpService

        mock_env = Mock()
        service = AiSearchMvpService(mock_env)

        result = service._simple_intent_parse('300元以内的手机')

        self.assertEqual(result['budget_max'], 300.0)
        self.assertIn('手机', result['keywords'])

    def test_simple_intent_parse_budget_range(self):
        """测试解析价格区间"""
        from ai_dify_search_mvp.services.search_service import AiSearchMvpService

        mock_env = Mock()
        service = AiSearchMvpService(mock_env)

        result = service._simple_intent_parse('2000-3000元的手机')

        self.assertEqual(result['budget_min'], 2000.0)
        self.assertEqual(result['budget_max'], 3000.0)


class TestFallbackService(unittest.TestCase):
    """测试降级服务"""

    def test_fallback_service_available(self):
        """测试降级服务可用性检查"""
        from ai_dify_search_mvp.services.fallback_service import AiSearchMvpFallbackService

        mock_env = Mock()

        with patch.object(
            AiSearchMvpFallbackService,
            'config_service',
            new_callable=lambda: property(lambda self: Mock(fallback_enabled=True)))
        ):
            service = AiSearchMvpFallbackService(mock_env)
            self.assertTrue(service.is_available())


if __name__ == '__main__':
    unittest.main()
