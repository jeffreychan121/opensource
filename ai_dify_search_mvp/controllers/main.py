# -*- coding: utf-8 -*-
"""
@File   : main.py
@Time   : 2026-04-21
@Desc   : AI 搜索 MVP 主控制器
"""

import json
import logging
import time
from typing import Dict, Any, Optional

from odoo import http, fields
from odoo.http import request, Response
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AiSearchMvpController(http.Controller):

    def _get_config_service(self):
        from ..services.config_service import AiSearchMvpConfigService
        return AiSearchMvpConfigService(request.env)

    def _get_session_service(self):
        from ..services.session_service import AiSearchMvpSessionService
        return AiSearchMvpSessionService(request.env)

    def _get_dify_service(self):
        from ..services.dify_service import DifyService
        return DifyService(request.env)

    def _get_search_service(self):
        from ..services.search_service import AiSearchMvpService
        return AiSearchMvpService(request.env)

    def _get_fallback_service(self):
        from ..services.fallback_service import AiSearchMvpFallbackService
        return AiSearchMvpFallbackService(request.env)

    def _json_response(self, data: Dict, status: int = 200) -> Response:
        return Response(
            json.dumps(data, ensure_ascii=False, default=str),
            status=status,
            content_type='application/json'
        )

    def _write_log(self, query: str, session_key: str,
                   parsed_intent: Optional[Dict],
                   product_ids: list,
                   fallback_used: bool,
                   success: bool,
                   error_message: Optional[str],
                   dify_latency_ms: float,
                   search_latency_ms: float,
                   total_latency_ms: float):
        """写入搜索日志"""
        try:
            config_service = self._get_config_service()
            if not config_service.log_enabled:
                return

            self.env['ai.search.mvp.log'].sudo().create({
                'query': query,
                'session_key': session_key,
                'parsed_intent': json.dumps(parsed_intent, ensure_ascii=False) if parsed_intent else None,
                'product_ids': json.dumps(product_ids, ensure_ascii=False) if product_ids else None,
                'fallback_used': fallback_used,
                'success': success,
                'error_message': error_message,
                'dify_latency_ms': dify_latency_ms,
                'search_latency_ms': search_latency_ms,
                'total_latency_ms': total_latency_ms,
            })
        except Exception as e:
            _logger.error('Failed to write log: %s', str(e))

    @http.route('/ai-search-mvp', type='http', auth='user', website=True)
    def ai_search_page(self, **kw):
        """渲染 AI 搜索页面"""
        return request.render('ai_dify_search_mvp.ai_search_mvp_page')

    @http.route('/ai_search_mvp/query', type='json', auth='public', cors='*', csrf=False)
    def query(self, **post):
        """
        浏览器主搜索入口

        POST /ai_search_mvp/query
        Body: {query, session_key?, lang?}
        """
        start_time = time.time()

        query_text = post.get('query', '')
        session_key = post.get('session_key')
        lang = post.get('lang', 'zh_CN')

        if not query_text or len(query_text) > 500:
            return {
                'success': False,
                'error': 'Invalid query',
                'code': 'INVALID_INPUT',
            }

        config_service = self._get_config_service()
        if not config_service.is_enabled:
            return {
                'success': False,
                'error': 'AI Search is not enabled',
                'code': 'DISABLED',
            }

        session_service = self._get_session_service()
        session = session_service.get_or_create_session(session_key)
        session_key = session.session_key

        dify_service = self._get_dify_service()
        search_service = self._get_search_service()

        dify_latency_ms = 0
        search_latency_ms = 0
        parsed_intent = None
        products = []
        summary = ''
        fallback_used = False
        error_message = None
        conversation_id = None

        try:
            inputs = {
                'session_key': session_key,
                'lang': lang,
            }

            dify_result, dify_latency, err = dify_service.chat_with_parse(
                query=query_text,
                conversation_id=session.conversation_id,
                user_id=f'odoo_user_{request.env.user.id}' if request.env.user.id else None,
                inputs=inputs,
            )

            dify_latency_ms = dify_latency

            if err:
                if config_service.fallback_enabled:
                    fallback_service = self._get_fallback_service()
                    products, fb_result = fallback_service.execute_fallback(
                        query=query_text,
                        top_k=config_service.search_top_k,
                        lang=lang,
                    )
                    summary = fb_result.get('summary', '')
                    fallback_used = True
                    search_latency_ms = fb_result.get('latency_ms', 0)
                else:
                    error_message = err
            else:
                parsed_intent = dify_result.get('parsed_intent')
                summary = dify_result.get('answer', '')
                conversation_id = dify_result.get('conversation_id')

                if parsed_intent:
                    products, applied_filters, search_latency_ms = search_service.search_products(
                        parsed_intent=parsed_intent,
                        top_k=config_service.search_top_k,
                        lang=lang,
                    )

        except Exception as e:
            _logger.error('Search error: %s', str(e), exc_info=True)
            error_message = str(e)

            if config_service.fallback_enabled:
                fallback_service = self._get_fallback_service()
                products, fb_result = fallback_service.execute_fallback(
                    query=query_text,
                    top_k=config_service.search_top_k,
                    lang=lang,
                )
                summary = fb_result.get('summary', '')
                fallback_used = True
                search_latency_ms = fb_result.get('latency_ms', 0)
                error_message = None

        total_latency_ms = (time.time() - start_time) * 1000

        product_ids = [p['id'] for p in products]
        success = error_message is None and len(products) > 0

        if parsed_intent and conversation_id:
            session_service.update_session(
                session_key,
                last_query=query_text,
                last_parsed_intent=json.dumps(parsed_intent, ensure_ascii=False),
                last_product_ids=json.dumps(product_ids, ensure_ascii=False),
                conversation_id=conversation_id,
            )

        self._write_log(
            query=query_text,
            session_key=session_key,
            parsed_intent=parsed_intent,
            product_ids=product_ids,
            fallback_used=fallback_used,
            success=success,
            error_message=error_message,
            dify_latency_ms=dify_latency_ms,
            search_latency_ms=search_latency_ms,
            total_latency_ms=total_latency_ms,
        )

        result = {
            'success': success,
            'query': query_text,
            'session_key': session_key,
            'parsed_intent': parsed_intent or {},
            'products': products,
            'summary': summary,
            'fallback_used': fallback_used,
            'total_latency_ms': total_latency_ms,
        }

        if error_message:
            result['error'] = error_message
            result['code'] = 'SERVICE_UNAVAILABLE'

        if config_service.debug_mode:
            result['debug_info'] = {
                'dify_latency_ms': dify_latency_ms,
                'search_latency_ms': search_latency_ms,
                'parsed_intent_raw': parsed_intent,
            }

        return result

    @http.route('/ai_search_mvp/internal/search', type='json', auth='public', cors='*', csrf=False)
    def internal_search(self, **post):
        """
        内部搜索接口（Dify 调用）

        POST /ai_search_mvp/internal/search
        Header: X-Internal-Token: <token>
        Body: {query, session_key?, parsed_intent?, top_k?, lang?}
        """
        token = request.httprequest.headers.get('X-Internal-Token')
        config_service = self._get_config_service()

        if not token or token != config_service.internal_token:
            return self._json_response({
                'success': False,
                'error': 'Invalid or missing token',
                'code': 'INVALID_TOKEN',
            }, status=401)

        query_text = post.get('query', '')
        parsed_intent = post.get('parsed_intent', {})
        top_k = post.get('top_k', config_service.search_top_k)
        lang = post.get('lang', 'zh_CN')

        if not query_text:
            return {
                'success': False,
                'error': 'Query is required',
                'code': 'INVALID_INPUT',
            }

        search_service = self._get_search_service()

        try:
            products, applied_filters, latency_ms = search_service.search_products(
                parsed_intent=parsed_intent,
                top_k=top_k,
                lang=lang,
            )

            return {
                'success': True,
                'parsed_intent': parsed_intent,
                'applied_filters': applied_filters,
                'products': products,
                'count': len(products),
                'latency_ms': latency_ms,
            }

        except Exception as e:
            _logger.error('Internal search error: %s', str(e), exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR',
            }
