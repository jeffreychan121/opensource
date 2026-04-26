# -*- coding: utf-8 -*-
"""
@File   :   test_ai_dify_search.py
@Time   :   2024-04-14
@Desc   :   AI Dify 搜索模块单元测试
"""

import json
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, TransactionCase

_logger = logging.getLogger(__name__)


class TestAiSearchConfig(common.TransactionCase):
    """测试配置服务"""

    def setUp(self):
        super().setUp()
        self.config_service = self.env['ir.config_parameter'].sudo()

    def test_config_parameters(self):
        """测试配置参数读写"""
        ICP = self.config_service

        # 测试写入和读取
        ICP.set_param('ai_dify_search.enabled', 'True')
        self.assertEqual(ICP.get_param('ai_dify_search.enabled'), 'True')

        ICP.set_param('ai_dify_search.dify_timeout', '30')
        self.assertEqual(ICP.get_param('ai_dify_search.dify_timeout'), '30')

        ICP.set_param('ai_dify_search.search_top_k', '8')
        self.assertEqual(ICP.get_param('ai_dify_search.search_top_k'), '8')

    def test_config_defaults(self):
        """测试配置默认值"""
        ICP = self.config_service

        # 清除已有配置
        ICP.set_param('ai_dify_search.dify_api_base_url', False)
        ICP.set_param('ai_dify_search.dify_timeout', False)

        # 读取默认值
        self.assertEqual(
            ICP.get_param('ai_dify_search.dify_api_base_url', 'https://api.dify.ai/v1'),
            'https://api.dify.ai/v1'
        )
        self.assertEqual(
            int(ICP.get_param('ai_dify_search.dify_timeout', '30')),
            30
        )


class TestAiSearchSession(common.TransactionCase):
    """测试会话服务"""

    def setUp(self):
        super().setUp()
        self.session_model = self.env['ai.search.session']

    def test_session_creation(self):
        """测试会话创建"""
        session = self.session_model.create({
            'website_visitor_id': 'test_visitor_123',
        })

        self.assertTrue(session.session_key)
        self.assertTrue(session.active)
        self.assertEqual(session.state, 'active')
        self.assertEqual(session.query_count, 0)

    def test_session_unique_key(self):
        """测试会话 Key 唯一性"""
        session1 = self.session_model.create({
            'session_key': 'unique_key_123',
        })

        # 尝试创建相同 key 的会话应该失败
        with self.assertRaises(Exception):
            self.session_model.create({
                'session_key': 'unique_key_123',
            })

    def test_add_query(self):
        """测试添加查询记录"""
        session = self.session_model.create({})

        session.add_query(
            query='帮我找300元以内的男鞋',
            parsed_intent={'budget_max': 300, 'category': '男鞋'},
            applied_filters={'budget_max': 300},
            product_ids=[1, 2, 3],
            summary='找到3款合适的商品'
        )

        self.assertEqual(session.last_query, '帮我找300元以内的男鞋')
        self.assertEqual(session.last_parsed_intent, {'budget_max': 300, 'category': '男鞋'})
        self.assertEqual(session.last_product_ids, [1, 2, 3])
        self.assertEqual(session.query_count, 1)

    def test_add_multiple_queries(self):
        """测试添加多条查询"""
        session = self.session_model.create({})

        for i in range(3):
            session.add_query(
                query=f'查询{i}',
                parsed_intent={'query': i},
            )

        self.assertEqual(session.query_count, 3)
        # 检查历史记录
        history = session.query_history or []
        self.assertEqual(len(history), 3)

    def test_close_session(self):
        """测试关闭会话"""
        session = self.session_model.create({})
        self.assertTrue(session.active)

        session.close_session()

        self.assertFalse(session.active)
        self.assertEqual(session.state, 'closed')

    def test_get_or_create_session(self):
        """测试获取或创建会话"""
        # 第一次获取 - 应该创建
        session1, created1 = self.session_model.get_or_create_session(
            session_key='test_key_456'
        )
        self.assertTrue(created1)
        self.assertEqual(session1.session_key, 'test_key_456')

        # 第二次获取相同 key - 应该返回现有
        session2, created2 = self.session_model.get_or_create_session(
            session_key='test_key_456'
        )
        self.assertFalse(created2)
        self.assertEqual(session2.id, session1.id)

    def test_cleanup_expired_sessions(self):
        """测试清理过期会话"""
        # 创建一个会话并手动设置过期时间
        session = self.session_model.create({
            'session_key': 'expired_session'
        })

        # 手动设置最后查询时间为过去
        expired_time = fields.Datetime.now() - timedelta(hours=48)
        session.write({
            'last_query_date': expired_time
        })

        # 执行清理
        self.session_model.cleanup_expired_sessions()

        # 验证会话已过期
        session.invalidate_recordset()
        self.assertEqual(session.state, 'expired')
        self.assertFalse(session.active)


class TestAiSearchLog(common.TransactionCase):
    """测试日志服务"""

    def setUp(self):
        super().setUp()
        self.log_model = self.env['ai.search.log']
        self.session_model = self.env['ai.search.session']

    def test_log_creation(self):
        """测试日志创建"""
        log = self.log_model.create({
            'query': '测试查询',
            'language': 'zh_CN',
        })

        self.assertTrue(log.query_hash)
        self.assertTrue(log.create_date)
        self.assertEqual(log.success, True)
        self.assertEqual(log.fallback_used, False)

    def test_log_search(self):
        """测试 log_search 便捷方法"""
        session = self.session_model.create({})

        log = self.log_model.log_search(
            session_id=session,
            query='300元以内的男鞋',
            parsed_intent={'budget_max': 300},
            fallback_used=False,
            success=True,
            dify_latency=100.0,
            odoo_latency=50.0,
            product_ids=[1, 2, 3],
            summary='找到3款商品',
            language='zh_CN'
        )

        self.assertEqual(log.query, '300元以内的男鞋')
        self.assertEqual(log.product_count, 3)
        self.assertEqual(log.total_latency, 150.0)
        self.assertEqual(log.intent_source, 'dify')

    def test_log_with_fallback(self):
        """测试 Fallback 日志"""
        log = self.log_model.log_search(
            query='测试查询',
            parsed_intent={},
            fallback_used=True,
            success=True,
            dify_latency=0.0,
            odoo_latency=30.0,
            product_ids=[1, 2],
        )

        self.assertEqual(log.intent_source, 'fallback')
        self.assertTrue(log.fallback_used)

    def test_log_failure(self):
        """测试失败日志"""
        log = self.log_model.log_search(
            query='测试查询',
            fallback_used=False,
            success=False,
            error_message='Dify API timeout',
            error_code='DIFY_TIMEOUT',
        )

        self.assertFalse(log.success)
        self.assertEqual(log.error_code, 'DIFY_TIMEOUT')

    def test_set_latency(self):
        """测试设置延迟"""
        log = self.log_model.create({'query': '测试'})

        log.set_latency(dify_latency=200.0, odoo_latency=80.0)

        self.assertEqual(log.dify_latency, 200.0)
        self.assertEqual(log.odoo_search_latency, 80.0)
        self.assertEqual(log.total_latency, 280.0)

    def test_write_result(self):
        """测试写入结果"""
        log = self.log_model.create({'query': '测试'})

        log.write_result(
            product_ids=[10, 20, 30],
            summary='测试总结',
            success=True
        )

        self.assertEqual(log.product_count, 3)
        self.assertEqual(log.summary, '测试总结')


class TestFallbackService(common.TransactionCase):
    """测试 Fallback 服务"""

    def setUp(self):
        super().setUp()

    def test_fallback_available(self):
        """测试 Fallback 可用性检查"""
        from odoo.addons.ai_dify_search.services.fallback_service import AiFallbackService

        service = AiFallbackService(self.env)

        # 检查方法存在
        self.assertTrue(hasattr(service, 'is_available'))
        self.assertTrue(hasattr(service, 'execute_fallback'))
        self.assertTrue(hasattr(service, 'generate_suggestions'))


class TestSearchService(common.TransactionCase):
    """测试搜索服务"""

    def setUp(self):
        super().setUp()

    def test_simple_intent_parse(self):
        """测试简单意图解析"""
        from odoo.addons.ai_dify_search.services.search_service import AiSearchService

        service = AiSearchService(self.env)

        # 测试价格提取
        intent = service._simple_intent_parse('300元以内的男鞋')
        self.assertEqual(intent['budget_max'], 300)
        self.assertIn('男鞋', intent['keywords'])

        # 测试排除词
        intent = service._simple_intent_parse('不要白色的鞋子')
        self.assertIn('白色', intent['color_exclude'])

        # 测试场景
        intent = service._simple_intent_parse('适合通勤的鞋子')
        self.assertIn('通勤', intent['use_case'])


class TestDifyService(common.TransactionCase):
    """测试 Dify 服务"""

    def setUp(self):
        super().setUp()

    def test_dify_service_creation(self):
        """测试 Dify 服务创建"""
        from odoo.addons.ai_dify_search.services.dify_service import DifyService

        service = DifyService(self.env)
        self.assertIsNotNone(service)

    def test_extract_json_from_answer(self):
        """测试从回答中提取 JSON"""
        from odoo.addons.ai_dify_search.services.dify_service import DifyService

        service = DifyService(self.env)

        # 测试标准 JSON
        answer = '{"category": "男鞋", "budget_max": 300}'
        result = service._extract_json_from_answer(answer)
        self.assertEqual(result['category'], '男鞋')
        self.assertEqual(result['budget_max'], 300)

    def test_generate_user_id(self):
        """测试用户 ID 生成"""
        from odoo.addons.ai_dify_search.services.dify_service import DifyService

        service = DifyService(self.env)

        # 设置配置
        self.env['ir.config_parameter'].sudo().set_param(
            'ai_dify_search.dify_user_prefix', 'test_user_'
        )

        user_id = service._generate_user_id(
            partner_id=123
        )
        self.assertEqual(user_id, 'test_user_partner_123')

        user_id = service._generate_user_id(
            user_id=456
        )
        self.assertEqual(user_id, 'test_user_user_456')


class TestPromptService(common.TransactionCase):
    """测试 Prompt 服务"""

    def test_prompt_templates_exist(self):
        """测试 Prompt 模板存在"""
        from odoo.addons.ai_dify_search.services.prompt_service import AiPromptService

        self.assertTrue(AiPromptService.INTENT_PARSER_SYSTEM_PROMPT)
        self.assertTrue(AiPromptService.INTENT_PARSER_USER_PROMPT)
        self.assertTrue(AiPromptService.RECOMMENDATION_SYSTEM_PROMPT)
        self.assertTrue(AiPromptService.NO_RESULT_SYSTEM_PROMPT)

    def test_get_intent_parser_prompt(self):
        """测试获取意图解析 Prompt"""
        from odoo.addons.ai_dify_search.services.prompt_service import AiPromptService

        system, user = AiPromptService.get_intent_parser_prompt('测试查询')

        self.assertIn('JSON', system)
        self.assertIn('测试查询', user)


class TestAiSearchController(common.HttpCase):
    """测试 AI 搜索控制器"""

    def setUp(self):
        super().setUp()
        # 启用 AI 搜索
        self.env['ir.config_parameter'].sudo().set_param('ai_dify_search.enabled', 'True')
        self.env['ir.config_parameter'].sudo().set_param('ai_dify_search.fallback_enabled', 'True')

    def test_query_endpoint_exists(self):
        """测试查询接口存在"""
        response = self.url_open(
            '/ai_search/query',
            data=json.dumps({'query': '测试'}),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        # 应该能收到响应（可能失败但不应该是 404）
        self.assertNotEqual(response.status_code, 404)

    def test_internal_search_requires_token(self):
        """测试内部搜索需要 Token"""
        response = self.url_open(
            '/ai_search/internal/search',
            data=json.dumps({
                'token': 'wrong_token',
                'query': '测试'
            }),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        # 无效 token 应该返回 401
        self.assertEqual(response.status_code, 401)

    def test_session_close(self):
        """测试关闭会话接口"""
        # 创建测试会话
        session = self.env['ai.search.session'].create({
            'session_key': 'test_close_session'
        })

        response = self.url_open(
            '/ai_search/session/close',
            data=json.dumps({'session_key': 'test_close_session'}),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        # 验证响应格式
        result = response.json()
        self.assertIn('success', result)


# 运行测试的辅助类
class TestRunner:
    """测试运行器辅助类"""

    @staticmethod
    def run_tests():
        """运行所有测试（供调试用）"""
        import unittest
        suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)
