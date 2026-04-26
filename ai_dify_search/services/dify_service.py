# -*- coding: utf-8 -*-
"""
@File   :   dify_service.py
@Time   :   2024-04-14
@Desc   :   Dify API 调用服务
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Tuple

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DifyServiceError(Exception):
    """Dify 服务异常"""
    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class DifyService:
    """
    Dify API 调用服务
    封装与 Dify Chatflow 的所有交互
    """

    # 错误码定义
    ERROR_TIMEOUT = 'DIFY_TIMEOUT'
    ERROR_NETWORK = 'DIFY_NETWORK_ERROR'
    ERROR_AUTH = 'DIFY_AUTH_ERROR'
    ERROR_RESPONSE = 'DIFY_RESPONSE_ERROR'
    ERROR_PARSE = 'DIFY_PARSE_ERROR'
    ERROR_APP = 'DIFY_APP_ERROR'

    def __init__(self, env):
        """
        初始化 Dify 服务

        :param env: Odoo environment
        """
        self.env = env
        self.config = None
        self._config_service = None

    @property
    def config_service(self):
        """懒加载配置服务"""
        if self._config_service is None:
            from .config_service import AiSearchConfigService
            self._config_service = AiSearchConfigService(self.env)
        return self._config_service

    def _get_base_url(self):
        """获取 Dify API 基础 URL"""
        return self.config_service.dify_api_base_url.rstrip('/')

    def _get_headers(self):
        """获取请求头"""
        return self.config_service.get_dify_headers()

    def _get_timeout(self):
        """获取超时时间"""
        return self.config_service.dify_timeout

    def _generate_user_id(self, session=None, website_visitor_id=None,
                          partner_id=None, user_id=None):
        """
        生成 Dify 用户标识

        :param session: AI 搜索会话
        :param website_visitor_id: 网站访问者 ID
        :param partner_id: 合作伙伴 ID
        :param user_id: 用户 ID
        :return: 用户标识字符串
        """
        prefix = self.config_service.dify_user_prefix
        if partner_id:
            return f'{prefix}partner_{partner_id}'
        elif user_id:
            return f'{prefix}user_{user_id}'
        elif website_visitor_id:
            return f'{prefix}visitor_{website_visitor_id}'
        elif session:
            if session.partner_id:
                return f'{prefix}partner_{session.partner_id.id}'
            elif session.user_id:
                return f'{prefix}user_{session.user_id.id}'
            elif session.website_visitor_id:
                return f'{prefix}visitor_{session.website_visitor_id}'
        return f'{prefix}anonymous'

    def chat(self, query: str, query_type: str = 'chatflow',
             conversation_id: Optional[str] = None,
             session=None, website_visitor_id: Optional[str] = None,
             partner_id: Optional[int] = None,
             user_id: Optional[int] = None,
             inputs: Optional[Dict] = None,
             response_mode: str = 'blocking') -> Tuple[Dict[str, Any], float]:
        """
        调用 Dify Chatflow API（blocking 模式）

        :param query: 用户查询文本
        :param query_type: 查询类型，'chatflow' 或 'agent'
        :param conversation_id: 会话 ID（用于多轮对话）
        :param session: AI 搜索会话对象
        :param website_visitor_id: 网站访问者 ID
        :param partner_id: 合作伙伴 ID
        :param user_id: 用户 ID
        :param inputs: 额外的输入参数
        :param response_mode: 响应模式，'blocking' 或 'streaming'
        :return: tuple (result_dict, latency_ms)
        :raises DifyServiceError: 调用失败时抛出
        """
        start_time = time.time()

        # 生成用户标识
        user_id_str = self._generate_user_id(
            session=session,
            website_visitor_id=website_visitor_id,
            partner_id=partner_id,
            user_id=user_id
        )

        # 构建请求 URL
        app_id = self.config_service.dify_app_id
        url = f'{self._get_base_url()}/chat-messages'

        # 构建请求数据
        data = {
            'query': query,
            'user': user_id_str,
            'response_mode': response_mode,
        }

        # 添加会话 ID（用于多轮对话）
        if conversation_id:
            data['conversation_id'] = conversation_id

        # 添加额外输入（Dify 要求 inputs 必须存在，即使为空）
        data['inputs'] = inputs if inputs else {}

        headers = self._get_headers()
        timeout = self._get_timeout()

        _logger.info(
            'Calling Dify API: app_id=%s, user=%s, conversation_id=%s, query=%s',
            app_id, user_id_str, conversation_id, query[:50]
        )

        try:
            _logger.info('DIFY_API_CALL: URL=%s, Headers=%s, Data=%s', url, headers, data)
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=timeout
            )
            latency_ms = (time.time() - start_time) * 1000
            _logger.info('DIFY_API_RESPONSE: Status=%d, Body=%s', response.status_code, response.text[:500] if response.text else 'empty')

        except requests.exceptions.Timeout:
            _logger.error('Dify API timeout: timeout=%ds, query=%s', timeout, query[:50])
            raise DifyServiceError(
                _('Dify API request timeout'),
                code=self.ERROR_TIMEOUT,
                details={'timeout': timeout}
            )

        except requests.exceptions.ConnectionError as e:
            _logger.error('Dify API connection error: %s', str(e))
            raise DifyServiceError(
                _('Failed to connect to Dify API'),
                code=self.ERROR_NETWORK,
                details={'error': str(e)}
            )

        except requests.exceptions.RequestException as e:
            _logger.error('Dify API request error: %s', str(e))
            raise DifyServiceError(
                _('Dify API request failed'),
                code=self.ERROR_NETWORK,
                details={'error': str(e)}
            )

        # 检查响应状态码
        if response.status_code == 401:
            _logger.error('Dify API authentication failed')
            raise DifyServiceError(
                _('Dify API authentication failed'),
                code=self.ERROR_AUTH
            )

        if response.status_code != 200:
            _logger.error('Dify API error: status=%d, body=%s',
                         response.status_code, response.text[:500])
            raise DifyServiceError(
                _('Dify API returned error status: %d') % response.status_code,
                code=self.ERROR_APP,
                details={'status': response.status_code, 'body': response.text[:500]}
            )

        # 解析响应
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            _logger.error('Failed to parse Dify response: %s, body=%s',
                         str(e), response.text[:500])
            raise DifyServiceError(
                _('Failed to parse Dify API response'),
                code=self.ERROR_PARSE,
                details={'error': str(e), 'body': response.text[:500]}
            )

        _logger.info(
            'Dify API response received: latency=%.2fms, conversation_id=%s',
            latency_ms, result.get('conversation_id', 'N/A')
        )

        return result, latency_ms

    def chat_async(self, query: str, query_type: str = 'chatflow',
                   conversation_id: Optional[str] = None,
                   session=None, website_visitor_id: Optional[str] = None,
                   partner_id: Optional[int] = None,
                   user_id: Optional[int] = None,
                   inputs: Optional[Dict] = None) -> Tuple[str, float]:
        """
        Start async chat (non-blocking) and return task_id.

        :return: tuple (task_id, latency_ms)
        :raises DifyServiceError: if call fails
        """
        start_time = time.time()

        user_id_str = self._generate_user_id(
            session=session,
            website_visitor_id=website_visitor_id,
            partner_id=partner_id,
            user_id=user_id
        )

        app_id = self.config_service.dify_app_id
        url = f'{self._get_base_url()}/chat-messages'

        data = {
            'query': query,
            'user': user_id_str,
            'response_mode': 'blocking',
            'inputs': inputs or {},
        }

        if conversation_id:
            data['conversation_id'] = conversation_id

        headers = self._get_headers()
        timeout = self._get_timeout()

        try:
            response = requests.post(
                url, headers=headers, json=data, timeout=timeout
            )
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code != 200:
                raise DifyServiceError(
                    f'Dify API error: {response.status_code}',
                    code=self.ERROR_APP
                )

            result = response.json()
            task_id = result.get('task_id') or result.get('conversation_id')

            return task_id, latency_ms

        except requests.exceptions.Timeout:
            raise DifyServiceError(
                _('Dify API request timeout'),
                code=self.ERROR_TIMEOUT
            )
        except Exception as e:
            raise DifyServiceError(
                str(e),
                code=self.ERROR_NETWORK
            )

    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 Dify 返回的响应

        :param response: Dify API 返回的原始响应
        :return: 解析后的结构化数据
        :raises DifyServiceError: 解析失败时抛出
        """
        try:
            # 检查响应结构
            if 'answer' not in response:
                raise DifyServiceError(
                    _('Dify response missing "answer" field'),
                    code=self.ERROR_RESPONSE,
                    details={'keys': list(response.keys())}
                )

            # 提取关键字段
            answer = response.get('answer', '')
            conversation_id = response.get('conversation_id')
            request_id = response.get('conversation_id')  # Dify 使用 conversation_id 作为请求标识

            # 尝试解析 answer 中的 JSON
            parsed_intent = None
            if answer:
                # 尝试从 answer 中提取 JSON
                parsed_intent = self._extract_json_from_answer(answer)

            # 构建标准返回结构
            result = {
                'success': True,
                'answer': answer,
                'parsed_intent': parsed_intent,
                'conversation_id': conversation_id,
                'request_id': request_id,
                'raw_response': response if self.config_service.is_debug_mode else None,
            }

            # 提取元数据（如果有）
            if 'metadata' in response:
                result['metadata'] = response.get('metadata')

            # 提取 token 使用情况（如果有）
            if 'token_usage' in response:
                result['token_usage'] = response.get('token_usage')

            return result

        except DifyServiceError:
            raise
        except Exception as e:
            _logger.error('Error parsing Dify response: %s', str(e))
            raise DifyServiceError(
                _('Error parsing Dify response'),
                code=self.ERROR_PARSE,
                details={'error': str(e)}
            )

    def poll_response(self, task_id: str) -> Dict[str, Any]:
        """
        Poll Dify for task result.

        :param task_id: The task ID returned by chat_async
        :return: dict with status and result
        """
        url = f'{self._get_base_url()}/chat-messages/{task_id}/stop'

        headers = self._get_headers()

        try:
            # First try to get the response
            get_url = f'{self._get_base_url()}/chat-messages/{task_id}'
            response = requests.get(get_url, headers=headers, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return {
                    'status': 'completed',
                    'data': result
                }
            elif response.status_code == 404:
                return {
                    'status': 'not_found',
                    'data': None
                }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}'
                }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def _extract_json_from_answer(self, answer: str) -> Optional[Dict[str, Any]]:
        """
        从 Dify LLM 返回的文本中提取 JSON

        :param answer: LLM 返回的文本
        :return: 解析后的 JSON 对象，或 None
        """
        import re

        # 尝试多种 JSON 提取模式
        patterns = [
            r'\{[^{}]*\}',  # 简单单层 JSON
            r'\{[\s\S]*?"[\w]+"[\s\S]*?\}',  # 含嵌套的 JSON
        ]

        for pattern in patterns:
            matches = re.findall(pattern, answer)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    # 验证是有效的 intent 结构
                    if isinstance(parsed, dict) and (
                        'category' in parsed or
                        'keywords' in parsed or
                        'intent' in parsed
                    ):
                        return parsed
                except (json.JSONDecodeError, TypeError):
                    continue

        # 如果没找到有效的 JSON，尝试直接解析
        try:
            # 去除 markdown 代码块标记
            cleaned = answer.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]

            parsed = json.loads(cleaned.strip())
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        return None

    def chat_with_parse(self, query: str, session=None,
                        website_visitor_id: Optional[str] = None,
                        partner_id: Optional[int] = None,
                        user_id: Optional[int] = None,
                        conversation_id: Optional[str] = None,
                        inputs: Optional[Dict] = None) -> Tuple[Dict[str, Any], float, Optional[str]]:
        """
        调用 Dify 并自动解析响应

        :param query: 用户查询
        :param session: 搜索会话
        :param website_visitor_id: 网站访问者 ID
        :param partner_id: 合作伙伴 ID
        :param user_id: 用户 ID
        :param conversation_id: Dify 会话 ID
        :param inputs: 额外输入参数
        :return: tuple (parsed_result, latency_ms, error_message)
        """
        error_message = None

        try:
            # 调用 Dify
            raw_response, latency_ms = self.chat(
                query=query,
                session=session,
                website_visitor_id=website_visitor_id,
                partner_id=partner_id,
                user_id=user_id,
                conversation_id=conversation_id,
                inputs=inputs,
                response_mode='blocking'
            )

            # 解析响应
            result = self.parse_response(raw_response)

            return result, latency_ms, None

        except DifyServiceError as e:
            error_message = str(e)
            _logger.warning('Dify service error: %s, code=%s', e, e.code)
            return {
                'success': False,
                'error': error_message,
                'error_code': e.code,
            }, 0, error_message

        except Exception as e:
            error_message = _('Unexpected error: %s') % str(e)
            _logger.error('Unexpected Dify service error: %s', str(e), exc_info=True)
            return {
                'success': False,
                'error': error_message,
                'error_code': 'UNKNOWN_ERROR',
            }, 0, error_message
