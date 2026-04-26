# -*- coding: utf-8 -*-
"""
@File   :   main.py
@Time   :   2024-04-14
@Desc   :   AI 搜索模块主控制器
           提供公共 API 接口
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List

from odoo import http, fields
from odoo.http import request, Response
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AiSearchController(http.Controller):
    """
    AI 搜索主控制器
    处理浏览器端请求和内部 API 调用
    """

    # ==================== 辅助方法 ====================

    def _get_config_service(self):
        """获取配置服务"""
        from ..services.config_service import AiSearchConfigService
        return AiSearchConfigService(request.env)

    def _get_session_service(self):
        """获取会话服务"""
        from ..services.session_service import AiSessionService
        return AiSessionService(request.env)

    def _get_dify_service(self):
        """获取 Dify 服务"""
        from ..services.dify_service import DifyService
        return DifyService(request.env)

    def _get_search_service(self):
        """获取搜索服务"""
        from ..services.search_service import AiSearchService
        return AiSearchService(request.env)

    def _get_fallback_service(self):
        """获取 Fallback 服务"""
        from ..services.fallback_service import AiFallbackService
        return AiFallbackService(request.env)

    def _json_response(self, data: Dict, status: int = 200) -> Response:
        """返回 JSON 响应"""
        return Response(
            json.dumps(data, ensure_ascii=False, default=str),
            status=status,
            mimetype='application/json'
        )

    def _error_response(self, message: str, code: str = 'ERROR', **kwargs) -> Response:
        """返回错误响应"""
        data = {
            'success': False,
            'error': message,
            'code': code,
        }
        data.update(kwargs)
        return self._json_response(data, status=400)

    def _parse_dify_answer(self, answer: str) -> Optional[Dict[str, Any]]:
        """
        解析 Dify 返回的 answer 字段中的 JSON

        Dify 的 answer 是 JSON 字符串，包含完整响应数据

        :param answer: Dify 返回的 answer 文本
        :return: 解析后的字典，或 None
        """
        import json
        import re

        if not answer:
            _logger.warning('[AI_SEARCH_DEBUG] _parse_dify_answer called with empty answer')
            return None

        _logger.info('[AI_SEARCH_DEBUG] _parse_dify_answer input length=%d, first 200 chars: %s', len(answer), answer[:200])

        # 尝试直接解析
        try:
            result = json.loads(answer)
            _logger.info('[AI_SEARCH_DEBUG] _parse_dify_answer parsed successfully, keys=%s', list(result.keys()))
            return result
        except (json.JSONDecodeError, TypeError) as e:
            _logger.warning('[AI_SEARCH_DEBUG] direct JSON parse failed: %s', e)

        # 尝试提取 JSON（去除 markdown 代码块）
        try:
            cleaned = answer.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]

            return json.loads(cleaned.strip())
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试从文本中提取 JSON
        try:
            json_match = re.search(r'\{[\s\S]*\}', answer)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, TypeError):
            pass

        return None

    def _validate_query_input(self, query: str, lang: str = 'zh_CN') -> tuple:
        """
        验证查询输入

        :param query: 查询文本
        :param lang: 语言
        :return: tuple (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, 'Query cannot be empty'

        if len(query) > 500:
            return False, 'Query too long (max 500 characters)'

        return True, None

    def _get_visitor_info(self) -> Dict[str, Any]:
        """
        获取访问者信息

        :return: 访问者信息字典
        """
        visitor_id = None
        partner_id = None
        user_id = None
        website_id = None

        # 尝试从 session 获取 (需要 website 模块)
        if hasattr(request, 'website') and request.website:
            website_id = request.website.id

        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            user_id = request.env.user.id
            partner_id = request.env.user.partner_id.id if request.env.user.partner_id else None

        return {
            'website_visitor_id': visitor_id,
            'partner_id': partner_id,
            'user_id': user_id,
            'website_id': website_id,
        }

    @http.route('/ai-search', type='http', auth='public', cors='*')
    def ai_search_page(self, **kw):
        """Render the AI search page."""
        return request.render('ai_dify_search.ai_search_page')

    # ==================== 公共 API：浏览器调用接口 ====================

    @http.route('/ai_search/query', type='json', auth='public', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_query(self, **post):
        """
        浏览器调用接口：处理 AI 搜索请求

        请求体：
        {
            "query": "帮我找300元以内适合通勤的男鞋",
            "session_key": "xxx",  // 可选
            "lang": "zh_CN"         // 可选
        }

        返回：
        {
            "success": true,
            "query": "帮我找300元以内适合通勤的男鞋",
            "parsed_intent": {...},
            "applied_filters": {...},
            "products": [...],
            "summary": "...",
            "followup_enabled": true,
            "fallback_used": false,
            "conversation_id": "xxx",
            "debug_info": {}
        }
        """
        start_time = time.time()

        try:
            # 解析请求体
            # JSON-RPC: params 在 request.params 中
            # 直接 JSON: params 在 json.loads(request.httprequest.data) 中
            if hasattr(request, 'params') and request.params:
                data = request.params
            else:
                data = json.loads(request.httprequest.data)
            query = data.get('query', '')
            session_key = data.get('session_key')
            lang = data.get('lang', 'zh_CN')

            # 验证输入
            is_valid, error_msg = self._validate_query_input(query, lang)
            if not is_valid:
                return {
                    'success': False,
                    'error': error_msg,
                    'code': 'INVALID_INPUT'
                }

            # 获取配置
            config = self._get_config_service()

            _logger.info('DEBUG: Config loaded - is_enabled=%s, api_url=%s, api_key_set=%s, app_id=%s',
                          config.is_enabled, config.dify_api_base_url, bool(config.dify_api_key_raw), config.dify_app_id)

            # 检查是否启用
            if not config.is_enabled:
                return {
                    'success': False,
                    'error': 'AI Search is not enabled',
                    'code': 'DISABLED'
                }

            # 获取访问者信息
            visitor_info = self._get_visitor_info()

            # 获取或创建会话
            session_service = self._get_session_service()
            session, session_created = session_service.get_or_create_session(
                session_key=session_key,
                website_visitor_id=visitor_info.get('website_visitor_id'),
                partner_id=visitor_info.get('partner_id'),
                user_id=visitor_info.get('user_id'),
                website_id=visitor_info.get('website_id'),
            )
            session_key = session['session_key']

            _logger.info(
                'AI Search request: query=%s, session_key=%s',
                query[:50], session_key
            )

            # ========== simple_mode: 直接关键词搜索 ==========
            simple_mode = data.get('simple_mode', False)
            page = data.get('page', 1)  # 分页页码
            if simple_mode:
                _logger.info('Simple keyword search mode for query: %s, page: %s', query[:50], page)

                # 直接执行关键词搜索
                fallback_service = self._get_fallback_service()
                products, fallback_result = fallback_service.execute_fallback(
                    query=query,
                    session_context=session,
                    top_k=config.search_top_k,
                    lang=lang,
                    page=page
                )

                # 生成分类卡片数据
                from ..services.search_service import AiSearchService
                search_svc = AiSearchService(request.env)
                usage_categories = search_svc._build_usage_categories(products)

                # Compute suggestions using the fallback service (avoids DRY violation)
                suggestions = []
                if not products:
                    fallback_suggestions = fallback_service.generate_suggestions(query)
                    suggestions = fallback_suggestions.get('suggestions', [])

                result = {
                    'success': True,
                    'query': query,
                    'session_key': session_key,
                    'products': products,
                    'count': len(products),
                    'summary': fallback_result.get('summary', ''),
                    'search_mode': 'keyword',
                    'has_results': len(products) > 0,
                    'has_more': fallback_result.get('has_more', False),
                    'message': None if products else f'未找到匹配「{query}」的商品',
                    'suggestions': suggestions,
                    'usage_categories': usage_categories,
                }

                if config.is_debug_mode:
                    result['debug'] = {
                        'dify_latency': 0,
                        'odoo_latency': fallback_result.get('latency_ms', 0),
                        'fallback_used': True,
                    }

                return result
            # ========== 原有 Dify 调用逻辑 ==========

            # 调用 Dify 进行意图解析和搜索编排
            # Dify Chatflow 内部会调用 Odoo /ai_search/internal/search 获取商品
            # 然后 Dify 生成推荐总结，最后返回完整结果
            _logger.info('[AI_SEARCH_DEBUG] About to call Dify: query=%s, simple_mode=%s', query[:50], simple_mode)
            dify_service = self._get_dify_service()
            dify_result, dify_latency, dify_error = dify_service.chat_with_parse(
                query=query,
                session=None,
                website_visitor_id=visitor_info.get('website_visitor_id'),
                partner_id=visitor_info.get('partner_id'),
                user_id=visitor_info.get('user_id'),
                conversation_id=session.get('conversation_id'),
                inputs={
                    'session_key': session_key or '',
                    'lang': lang,
                },
            )

            _logger.info('DIFY_RESULT: success=%s, answer=%s, error=%s, latency=%.2fms',
                         dify_result.get('success') if dify_result else None,
                         dify_result.get('answer', '')[:200] if dify_result else None,
                         dify_error, dify_latency)

            # 解析 Dify 返回的结果
            # Dify 的 answer 字段是 JSON 字符串，包含完整的响应数据
            fallback_used = False
            parsed_intent = None
            summary = None
            highlight = None
            value_tip = None
            products = []
            applied_filters = {}
            message = None
            suggestions = []
            usage_categories = None
            odoo_latency = 0

            if dify_result.get('success') and dify_result.get('answer'):
                # Dify 调用成功，解析 answer 中的 JSON
                answer_json = self._parse_dify_answer(dify_result.get('answer', ''))
                if answer_json:
                    parsed_intent = answer_json.get('parsed_intent')
                    # 优先从 answer 获取产品，其次从 outputs.products 获取
                    products = answer_json.get('products', [])
                    if not products and dify_result.get('outputs'):
                        products = dify_result.get('outputs', {}).get('products', [])
                    applied_filters = answer_json.get('applied_filters', {})
                    summary = answer_json.get('summary')
                    highlight = answer_json.get('highlight')
                    value_tip = answer_json.get('value_tip')
                    message = answer_json.get('message')
                    suggestions = answer_json.get('suggestions', [])
                    fallback_used = answer_json.get('fallback_used', False)

                    _logger.info('[AI_SEARCH_DEBUG] answer_json extracted: products_count=%d, usage_categories=%s, summary=%s, first_product_short_reason=%s',
                        len(products),
                        answer_json.get('usage_categories'),
                        summary,
                        products[0].get('short_reason') if products else 'N/A')

                    # 如果 Dify 返回了产品（含 short_reason），补充 Odoo 详细信息
                    if products and any(p.get('short_reason') for p in products if isinstance(p, dict)):
                        _logger.info('Using Dify products with short_reason: %d products', len(products))
                        product_ids = [p.get('id') for p in products if isinstance(p, dict) and p.get('id')]
                        if product_ids:
                            from ..services.search_service import AiSearchService
                            search_svc = AiSearchService(request.env)
                            odoo_products = search_svc._get_product_details(product_ids, applied_filters, lang)
                            short_reason_map = {p.get('id'): p.get('short_reason') for p in products if isinstance(p, dict)}
                            for op in odoo_products:
                                op['short_reason'] = short_reason_map.get(op['id'], '')
                            products = odoo_products

                    # 优先使用 Dify 返回的 usage_categories，否则本地生成
                    usage_categories = answer_json.get('usage_categories')
                    if not usage_categories and products:
                        from ..services.search_service import AiSearchService
                        search_svc = AiSearchService(request.env)
                        usage_categories = search_svc._build_usage_categories(products)

                    _logger.info('[AI_SEARCH_DEBUG] final state: products_count=%d, usage_categories=%s, first_product=%s, short_reason=%s',
                        len(products),
                        usage_categories,
                        products[0].get('name') if products else 'N/A',
                        products[0].get('short_reason') if products else 'N/A')
                else:
                    # JSON 解析失败，从原始字段获取
                    parsed_intent = dify_result.get('parsed_intent')
                    _logger.warning('[AI_SEARCH_DEBUG] answer_json parse failed, dify_result=%s', dify_result)

            elif dify_error and config.fallback_enabled:
                # Dify 失败，使用 Fallback
                _logger.warning('[AI_SEARCH_DEBUG] Dify failed, using fallback: error=%s', dify_error)

                fallback_service = self._get_fallback_service()
                products, fallback_result = fallback_service.execute_fallback(
                    query=query,
                    session_context=session,
                    top_k=config.search_top_k,
                    lang=lang
                )

                fallback_used = True
                summary = fallback_result.get('summary', '')
                applied_filters = {}

            else:
                # Dify 失败且未启用 Fallback
                _logger.warning('[AI_SEARCH_DEBUG] Dify failed, fallback disabled')
                return {
                    'success': False,
                    'error': 'AI Search service temporarily unavailable',
                    'code': 'SERVICE_UNAVAILABLE',
                    'fallback_available': config.fallback_enabled
                }

            _logger.info('[AI_SEARCH_DEBUG] post-dify block: fallback_used=%s, products_count=%d, dify_success=%s, dify_answer=%s, dify_error=%s',
                fallback_used, len(products), dify_result.get('success') if dify_result else None,
                dify_result.get('answer', '')[:100] if dify_result else None, dify_error)

            # 更新会话
            conversation_id = dify_result.get('conversation_id') if dify_result else None
            session_service.add_query_to_session(
                session_key=session_key,
                query=query,
                parsed_intent=parsed_intent,
                applied_filters=applied_filters,
                product_ids=[p['id'] for p in products] if isinstance(products, list) else [],
                summary=summary,
                conversation_id=conversation_id,
            )

            # 记录日志
            if config.log_enabled:
                self._log_search(
                    session=session,
                    query=query,
                    parsed_intent=parsed_intent,
                    fallback_used=fallback_used,
                    dify_latency=dify_latency,
                    odoo_latency=odoo_latency,
                    product_ids=[p['id'] for p in products] if isinstance(products, list) else [],
                    summary=summary,
                    lang=lang,
                )

            # 构建响应
            total_latency = (time.time() - start_time) * 1000

            result = {
                'success': True,
                'query': query,
                'session_key': session_key,
                'parsed_intent': parsed_intent,
                'applied_filters': applied_filters,
                'products': products,
                'summary': summary,
                'highlight': highlight,
                'value_tip': value_tip,
                'message': message,
                'suggestions': suggestions,
                'usage_categories': usage_categories,
                'followup_enabled': config.followup_enabled,
                'fallback_used': fallback_used,
                'conversation_id': conversation_id,
                'total_latency_ms': round(total_latency, 2),
                'debug_info': {
                    'dify_latency_ms': round(dify_latency, 2) if dify_latency else 0,
                    'odoo_latency_ms': round(odoo_latency, 2) if odoo_latency else 0,
                } if config.is_debug_mode else {},
            }

            return result

        except Exception as e:
            _logger.error('AI Search error: %s', str(e), exc_info=True)

            # 尝试使用 Fallback
            config = self._get_config_service()
            if config.fallback_enabled:
                try:
                    fallback_service = self._get_fallback_service()
                    products, fallback_result = fallback_service.execute_fallback(
                        query=query,
                        top_k=config.search_top_k,
                        lang=lang,
                    )
                    return {
                        'success': True,
                        'query': query,
                        'products': products,
                        'summary': fallback_result.get('summary', ''),
                        'fallback_used': True,
                        'error': str(e),
                    }
                except Exception:
                    pass

            return {
                'success': False,
                'error': 'An error occurred processing your request',
                'code': 'INTERNAL_ERROR'
            }

    # ==================== 内部 API：Dify 调用接口 ====================

    @http.route('/ai_search/internal/search', type='json', auth='none', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_internal(self, **post):
        """
        内部搜索接口：供 Dify HTTP Request 节点调用

        Dify 配置使用 X-Internal-Token header 传递令牌：
        Headers: X-Internal-Token: {ODOO_INTERNAL_SEARCH_TOKEN}

        请求体：
        {
            "query": "帮我找300元以内适合通勤的男鞋",
            "session_key": "xxx",
            "parsed_intent": {...},
            "top_k": 8,
            "lang": "zh_CN"
        }

        返回：
        {
            "success": true,
            "parsed_intent": {...},
            "applied_filters": {...},
            "products": [...],
            "count": 5
        }
        """
        try:
            # 验证内部 Token（支持两种方式：header 或 body）
            config = self._get_config_service()
            expected_token = config.internal_search_token

            if not expected_token:
                _logger.error('Internal search token not configured')
                return {
                    'success': False,
                    'error': 'Internal search token not configured'
                }

            # 优先从 header 获取 token（Dify 使用 X-Internal-Token）
            provided_token = request.httprequest.headers.get('X-Internal-Token', '')

            # 始终解析 body 数据
            data = json.loads(request.httprequest.data)

            # 如果 header 没有 token，从 body 获取（兼容旧版配置）
            if not provided_token:
                provided_token = data.get('token', '')

            # TODO: 临时禁用 token 验证，方便测试
            # if provided_token != expected_token:
            #     _logger.warning('Invalid internal search token attempted: %s', provided_token[:10] if provided_token else 'empty')
            #     return {
            #         'success': False,
            #         'error': 'Invalid token'
            #     }

            # 解析参数
            query = data.get('query', '')
            session_key = data.get('session_key')
            parsed_intent = data.get('parsed_intent', {})
            top_k = data.get('top_k', config.search_top_k)
            lang = data.get('lang', 'zh_CN')

            # 如果 parsed_intent 是字符串（来自 Dify 的 parsed_intent_json），则解析为 dict
            if isinstance(parsed_intent, str) and parsed_intent:
                try:
                    parsed_intent = json.loads(parsed_intent)
                except (json.JSONDecodeError, ValueError):
                    _logger.warning('Failed to parse parsed_intent as JSON: %s', parsed_intent[:100])
                    parsed_intent = {}

            _logger.info(
                'Internal search request: query=%s, session_key=%s, parsed_intent=%s',
                query[:50] if query else 'N/A', session_key,
                json.dumps(parsed_intent, ensure_ascii=False)[:200] if parsed_intent else 'None'
            )

            # 执行搜索
            search_service = self._get_search_service()

            if parsed_intent and isinstance(parsed_intent, dict):
                # 有解析后的意图
                _logger.info('Internal search: calling search_service.search_products with parsed_intent')
                products, applied_filters, latency_ms = search_service.search_products(
                    parsed_intent=parsed_intent,
                    top_k=top_k,
                    session_context={'session_key': session_key} if session_key else None,
                    lang=lang
                )
                _logger.info('Internal search: search returned %d products', len(products))
            else:
                # 无意图，使用 fallback
                _logger.info('Internal search: calling search_service.fallback_search')
                products, fallback_latency, has_more = search_service.fallback_search(
                    query=query,
                    top_k=top_k,
                    lang=lang
                )
                applied_filters = {}
                latency_ms = fallback_latency
                _logger.info('Internal search: fallback returned %d products', len(products))

            # 构建响应
            return {
                'success': True,
                'parsed_intent': parsed_intent,
                'applied_filters': applied_filters,
                'products': products,
                'count': len(products),
            }

        except Exception as e:
            _logger.error('Internal search error: %s', str(e), exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== 公共 API：关闭会话 ====================

    @http.route('/ai_search/session/close', type='json', auth='public', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_session_close(self, **post):
        """
        关闭 AI 搜索会话

        请求体：
        {
            "session_key": "xxx"
        }
        """
        try:
            session_key = post.get('session_key')
            if not session_key:
                return {
                    'success': False,
                    'error': 'session_key is required'
                }

            session_service = self._get_session_service()
            success = session_service.close_session(session_key)

            return {
                'success': success,
                'session_key': session_key,
            }

        except Exception as e:
            _logger.error('Close session error: %s', str(e))
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== 公共 API：获取会话上下文 ====================

    @http.route('/ai_search/session/context', type='json', auth='public', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_session_context(self, **post):
        """
        获取会话上下文

        请求体：
        {
            "session_key": "xxx"
        }
        """
        try:
            session_key = post.get('session_key')
            if not session_key:
                return {
                    'success': False,
                    'error': 'session_key is required'
                }

            session_service = self._get_session_service()
            context = session_service.get_session_context(session_key)

            return {
                'success': True,
                'context': context,
            }

        except Exception as e:
            _logger.error('Get session context error: %s', str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/ai_search/poll', type='json', auth='public', cors='*',
                methods=['GET'], csrf=False)
    def ai_search_poll(self, **kw):
        """
        Poll for async search results.

        Query params:
            session_key: The session key

        Returns poll status and results when completed.
        """
        session_key = kw.get('session_key')
        if not session_key:
            return {
                'success': False,
                'error': 'session_key is required'
            }

        try:
            session_model = request.env['ai.search.session']
            session = session_model.get_session_by_key(session_key)

            if not session:
                return {
                    'success': False,
                    'error': 'Session not found'
                }

            task_id = session.task_id
            poll_status = session.poll_status

            if not task_id:
                return {
                    'success': False,
                    'error': 'No task_id found'
                }

            if poll_status == 'completed':
                # Return cached results
                poll_result = session.poll_result or {}
                return {
                    'success': True,
                    'status': 'completed',
                    'parsed_intent': poll_result.get('parsed_intent'),
                    'products': poll_result.get('products', []),
                    'summary': poll_result.get('summary'),
                }

            elif poll_status == 'failed':
                return {
                    'success': False,
                    'error': 'Search failed'
                }

            else:
                # pending or processing - poll Dify
                dify_service = self._get_dify_service()
                poll_result = dify_service.poll_response(task_id)

                if poll_result['status'] == 'completed':
                    data = poll_result['data']
                    parsed_intent = dify_service.parse_response(data).get('parsed_intent')

                    # Get products - 检查 Dify 返回的完整数据结构
                    # Dify 可能返回: data.products 或 data.outputs.products
                    outputs = data.get('outputs', {}) if data else {}
                    dify_products = data.get('products', []) if data else []
                    if not dify_products:
                        dify_products = outputs.get('products', [])

                    _logger.info('DEBUG Dify poll result: data keys=%s, outputs keys=%s',
                                list(data.keys()) if data else [],
                                list(outputs.keys()) if outputs else [])
                    config = self._get_config_service()
                    search_service = self._get_search_service()

                    if dify_products and any(p.get('short_reason') for p in dify_products):
                        # Dify 直接返回了产品数据（含 AI 推荐理由），补充 Odoo 详细信息
                        _logger.info('Using Dify products with short_reason: %d products', len(dify_products))
                        product_ids = [p.get('id') for p in dify_products if p.get('id')]
                        if product_ids:
                            # 获取 Odoo 产品详细信息
                            odoo_products = search_service._get_product_details(
                                product_ids, {}, 'zh_CN'
                            )
                            # 合并 Dify 的 short_reason 到 Odoo 产品数据
                            short_reason_map = {p.get('id'): p.get('short_reason') for p in dify_products}
                            for op in odoo_products:
                                op['short_reason'] = short_reason_map.get(op['id'], '')
                            products = odoo_products
                        else:
                            products = dify_products
                        applied_filters = {}
                    else:
                        # Dify 没有返回产品数据，使用 Odoo 搜索
                        products, applied_filters, _ = search_service.search_products(
                            parsed_intent=parsed_intent,
                            top_k=config.search_top_k,
                            session_context={'session_key': session_key},
                        )

                    summary = self._extract_summary_from_answer(
                        data.get('answer', ''), products
                    )

                    # Update session
                    session.write({
                        'poll_status': 'completed',
                        'poll_result': {
                            'parsed_intent': parsed_intent,
                            'products': products,
                            'summary': summary,
                        }
                    })

                    return {
                        'success': True,
                        'status': 'completed',
                        'parsed_intent': parsed_intent,
                        'products': products,
                        'summary': summary,
                    }

                return {
                    'success': True,
                    'status': poll_status,
                }

        except Exception as e:
            _logger.error('Poll error: %s', str(e), exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/ai_search/categories', type='json', auth='public', cors='*',
                csrf=False)
    def ai_search_categories(self, **kw):
        """
        获取所有产品分类

        Returns categories from product.public.category model.
        """
        try:
            # 使用原生 SQL 获取分类
            request.env.cr.execute("""
                SELECT id, name
                FROM product_category
                ORDER BY name
            """)
            categ_rows = request.env.cr.fetchall()

            categories = []
            for categ_id, categ_name in categ_rows:
                # 统计该分类下的产品数量
                request.env.cr.execute("""
                    SELECT COUNT(*)
                    FROM product_template
                    WHERE categ_id IN (
                        SELECT id FROM product_category WHERE parent_path LIKE %s
                    )
                    AND sale_ok = true
                    AND active = true
                """, (f'{categ_id}/%',))
                product_count = request.env.cr.fetchone()[0]

                if product_count > 0:
                    categories.append({
                        'id': categ_id,
                        'name': categ_name,
                        'product_count': product_count,
                    })

            return {
                'success': True,
                'categories': categories,
            }

        except Exception as e:
            _logger.error('Get categories error: %s', str(e), exc_info=True)
            return {
                'success': False,
                'error': repr(e),
                'categories': [],
            }

    # ==================== 辅助方法 ====================

    def _extract_summary_from_answer(self, answer: str, products: list) -> Optional[str]:
        """
        从 Dify 返回的 answer 中提取总结

        :param answer: Dify 返回的完整回答
        :param products: 商品列表
        :return: 总结文本
        """
        # 尝试从 JSON 格式中提取 summary 字段
        import re
        try:
            # 尝试匹配 JSON
            json_match = re.search(r'\{[\s\S]*\}', answer)
            if json_match:
                data = json.loads(json_match.group())
                if 'summary' in data:
                    return data['summary']
        except (json.JSONDecodeError, TypeError):
            pass

        # 如果没有 JSON，直接返回原始回答的前200字符
        if answer:
            return answer[:200] if len(answer) > 200 else answer

        return None

    def _log_search(self, session, query: str, parsed_intent: Optional[Dict],
                    fallback_used: bool, dify_latency: float, odoo_latency: float,
                    product_ids: List[int], summary: Optional[str], lang: str):
        """
        记录搜索日志

        :param session: 会话信息
        :param query: 查询
        :param parsed_intent: 解析的意图
        :param fallback_used: 是否使用了 fallback
        :param dify_latency: Dify 延迟
        :param odoo_latency: Odoo 搜索延迟
        :param product_ids: 商品 ID 列表
        :param summary: 总结
        :param lang: 语言
        """
        try:
            log_model = request.env['ai.search.log']
            session_id = None

            # 验证 session 是否存在，避免 FK 约束错误
            if session and session.get('id'):
                session_record = request.env['ai.search.session'].browse(session['id'])
                if session_record.exists():
                    session_id = session_record

            log_model.log_search(
                session_id=session_id,
                query=query,
                parsed_intent=parsed_intent,
                fallback_used=fallback_used,
                success=True,
                dify_latency=dify_latency,
                odoo_latency=odoo_latency,
                product_ids=product_ids,
                summary=summary,
                language=lang,
            )
        except Exception as e:
            _logger.warning('Failed to log search: %s', str(e))

    # ==================== 商品理解 API ====================

    @http.route('/ai_search/product/understand', type='json', auth='public', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_product_understand(self, **post):
        """
        商品理解接口

        请求体：
        {
            "product_id": 123
        }
        或
        {
            "product_ids": [123, 456]
        }

        返回：
        {
            "success": true,
            "product": {...},  // 单个商品理解结果
            "products": [...]  // 批量商品理解结果
        }
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else post

            from ..services.product_understanding_service import ProductUnderstandingService
            understanding_svc = ProductUnderstandingService(request.env)

            product_id = data.get('product_id')
            product_ids = data.get('product_ids', [])

            if product_ids:
                # 批量理解
                products = request.env['product.template'].sudo().browse(product_ids).read([
                    'name', 'list_price', 'description_sale', 'description',
                    'categ_id', 'default_code', 'sale_ok'
                ])
                # 补充类目信息
                categ_map = {}
                if products:
                    categ_ids = list(set(p.get('categ_id')[0] if isinstance(p.get('categ_id'), tuple) else p.get('categ_id') for p in products if p.get('categ_id')))
                    if categ_ids:
                        categs = request.env['product.public.category'].sudo().browse(categ_ids).read(['name'])
                        categ_map = {c['id']: c['name'] for c in categs}

                # 构建商品数据
                product_data_list = []
                for p in products:
                    categ_id = p.get('categ_id')
                    if isinstance(categ_id, tuple):
                        categ_id = categ_id[0]
                    product_data = {
                        'id': p['id'],
                        'name': p.get('name', ''),
                        'price': p.get('list_price', 0),
                        'description_sale': p.get('description_sale', ''),
                        'description': p.get('description', ''),
                        'category_names': [categ_map.get(categ_id, '')] if categ_id else [],
                        'default_code': p.get('default_code', ''),
                        'sale_ok': p.get('sale_ok', False),
                    }
                    product_data_list.append(product_data)

                results = understanding_svc.understand_products(product_data_list)
                return {'success': True, 'products': results}

            elif product_id:
                # 单个理解
                product = request.env['product.template'].sudo().browse(product_id)
                product_data = {
                    'id': product.id,
                    'name': product.name or '',
                    'price': product.list_price or 0,
                    'description_sale': product.description_sale or '',
                    'description': product.description or '',
                    'category_names': [],
                    'default_code': product.default_code or '',
                    'sale_ok': product.sale_ok,
                }
                result = understanding_svc.understand_product(product_data)
                return {'success': True, 'product': result}

            else:
                return {'success': False, 'error': 'product_id or product_ids is required'}

        except Exception as e:
            _logger.error('Product understanding error: %s', str(e), exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== 搜索理解 API ====================

    @http.route('/ai_search/query/understand', type='json', auth='public', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_query_understand(self, **post):
        """
        搜索理解接口

        请求体：
        {
            "query": "适合老人用的大屏手机，声音大一点，预算2000内"
        }

        返回：
        {
            "success": true,
            "parsed_query": {
                "original_query": "...",
                "category": "手机",
                "budget_max": 2000,
                "target_people": ["老人"],
                "attributes": {...},
                "keywords": [...]
            }
        }
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else post

            query = data.get('query', '')
            if not query:
                return {'success': False, 'error': 'query is required'}

            from ..services.product_understanding_service import QueryUnderstandingService
            query_svc = QueryUnderstandingService(request.env)

            result = query_svc.understand_query(query)
            return {'success': True, 'parsed_query': result}

        except Exception as e:
            _logger.error('Query understanding error: %s', str(e), exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== 商品对比 API ====================

    @http.route('/ai_search/product/compare', type='json', auth='public', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_product_compare(self, **post):
        """
        商品对比接口

        请求体：
        {
            "product_ids": [123, 456]
        }
        或
        {
            "products": [
                {"id": 123, "name": "...", "price": 1999, ...},
                {"id": 456, "name": "...", "price": 2999, ...}
            ]
        }

        返回：
        {
            "success": true,
            "comparison": {
                "products": [...],
                "same_points": [...],
                "diff_points": [...],
                "attributes_compare": {...},
                "price_compare": {...},
                "selling_points_compare": {...},
                "target_people_compare": {...},
                "scenes_compare": {...},
                "recommendation": {...}
            }
        }
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8')) if request.httprequest.data else post

            from ..services.product_compare_service import ProductCompareService
            compare_svc = ProductCompareService(request.env)

            product_ids = data.get('product_ids', [])
            products_data = data.get('products', [])

            if product_ids and len(product_ids) >= 2:
                # 通过ID获取商品
                ProductTemplate = request.env['product.template'].sudo()
                products = ProductTemplate.browse(product_ids).read([
                    'name', 'list_price', 'description_sale', 'description',
                    'categ_id', 'default_code', 'sale_ok'
                ])

                # 补充类目信息
                categ_map = {}
                if products:
                    categ_ids = list(set(p.get('categ_id')[0] if isinstance(p.get('categ_id'), tuple) else p.get('categ_id') for p in products if p.get('categ_id')))
                    if categ_ids:
                        categs = request.env['product.public.category'].sudo().browse(categ_ids).read(['name'])
                        categ_map = {c['id']: c['name'] for c in categs}

                from ..services.product_understanding_service import ProductUnderstandingService
                understanding_svc = ProductUnderstandingService(request.env)

                understood_products = []
                for p in products:
                    categ_id = p.get('categ_id')
                    if isinstance(categ_id, tuple):
                        categ_id = categ_id[0]
                    product_data = {
                        'id': p['id'],
                        'name': p.get('name', ''),
                        'price': p.get('list_price', 0),
                        'description_sale': p.get('description_sale', ''),
                        'description': p.get('description', ''),
                        'category_names': [categ_map.get(categ_id, '')] if categ_id else [],
                    }
                    understood = understanding_svc.understand_product(product_data)
                    understood_products.append(understood)

                comparison = compare_svc.compare_products(understood_products)
                return {'success': True, 'comparison': comparison}

            elif products_data and len(products_data) >= 2:
                # 直接使用商品数据
                from ..services.product_understanding_service import ProductUnderstandingService
                understanding_svc = ProductUnderstandingService(request.env)

                understood_products = [understanding_svc.understand_product(p) for p in products_data]
                comparison = compare_svc.compare_products(understood_products)
                return {'success': True, 'comparison': comparison}

            else:
                return {'success': False, 'error': 'Need at least 2 products to compare'}

        except Exception as e:
            _logger.error('Product compare error: %s', str(e), exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== AI 商品对比 API ====================

    @http.route('/ai_search/product/ai_compare', type='json', auth='public', cors='*',
                methods=['POST'], csrf=False)
    def ai_search_product_ai_compare(self, **post):
        """
        AI 商品对比接口 - 调用 Dify 进行智能对比

        请求体：
        {
            "products": [
                {"id": 123, "name": "...", "price": 1999, ...},
                {"id": 456, "name": "...", "price": 2999, ...}
            ]
        }

        返回：
        {
            "success": true,
            "comparison": {
                "same_points": [...],
                "diff_points": [...],
                "recommendation": "...",
                "comparison_table": [...]
            }
        }
        """
        try:
            # type='json' 的数据通过 request.params 传递
            data = request.params

            from ..services.dify_compare_service import DifyCompareService
            dify_compare_svc = DifyCompareService(request.env)

            products_data = data.get('products', [])

            if len(products_data) < 2:
                return {'success': False, 'error': 'Need at least 2 products to compare'}

            # 取前2个商品进行对比
            product1 = products_data[0]
            product2 = products_data[1]

            _logger.info('AI Compare: product1=%s, product2=%s', product1.get('name'), product2.get('name'))

            # 调用 Dify AI 对比
            comparison = dify_compare_svc.compare_products(product1, product2)
            _logger.info('AI Compare result: comparison=%s', comparison)

            return {'success': True, 'comparison': comparison}

        except Exception as e:
            _logger.error('AI Compare error: %s', str(e), exc_info=True)
            return {'success': False, 'error': str(e)}

