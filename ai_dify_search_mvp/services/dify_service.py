# -*- coding: utf-8 -*-
"""
@File   : dify_service.py
@Time   : 2026-04-21
@Desc   : Dify API 调用服务
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Tuple

import requests

from odoo import _

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
    封装与 Dify Chatflow 的交互
    """

    ERROR_TIMEOUT = 'DIFY_TIMEOUT'
    ERROR_NETWORK = 'DIFY_NETWORK_ERROR'
    ERROR_AUTH = 'DIFY_AUTH_ERROR'
    ERROR_RESPONSE = 'DIFY_RESPONSE_ERROR'
    ERROR_PARSE = 'DIFY_PARSE_ERROR'
    ERROR_APP = 'DIFY_APP_ERROR'

    def __init__(self, env):
        self.env = env
        self._config_service = None

    @property
    def config_service(self):
        """懒加载配置服务"""
        if self._config_service is None:
            from .config_service import AiSearchMvpConfigService
            self._config_service = AiSearchMvpConfigService(self.env)
        return self._config_service

    def _get_base_url(self):
        return self.config_service.dify_api_base_url.rstrip('/')

    def _get_headers(self):
        return self.config_service.get_dify_headers()

    def _get_timeout(self):
        return self.config_service.dify_timeout

    def chat(self, query: str,
             conversation_id: Optional[str] = None,
             user_id: Optional[str] = None,
             inputs: Optional[Dict] = None) -> Tuple[Dict[str, Any], float]:
        """
        调用 Dify Chatflow API（blocking 模式）

        :param query: 用户查询文本
        :param conversation_id: 会话 ID（用于多轮对话）
        :param user_id: 用户标识
        :param inputs: 额外的输入参数
        :return: tuple (result_dict, latency_ms)
        """
        start_time = time.time()

        url = f'{self._get_base_url()}/chat-messages'
        headers = self._get_headers()
        timeout = self._get_timeout()

        data = {
            'query': query,
            'user': user_id or 'odoo_user_anonymous',
            'response_mode': 'blocking',
        }

        if conversation_id:
            data['conversation_id'] = conversation_id

        data['inputs'] = inputs if inputs else {}

        _logger.info('Calling Dify API: query=%s', query[:50])

        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=timeout
            )
            latency_ms = (time.time() - start_time) * 1000

        except requests.exceptions.Timeout:
            _logger.error('Dify API timeout')
            raise DifyServiceError(
                _('Dify API request timeout'),
                code=self.ERROR_TIMEOUT,
            )

        except requests.exceptions.ConnectionError as e:
            _logger.error('Dify API connection error: %s', str(e))
            raise DifyServiceError(
                _('Failed to connect to Dify API'),
                code=self.ERROR_NETWORK,
            )

        except requests.exceptions.RequestException as e:
            _logger.error('Dify API request error: %s', str(e))
            raise DifyServiceError(
                _('Dify API request failed'),
                code=self.ERROR_NETWORK,
            )

        if response.status_code == 401:
            _logger.error('Dify API authentication failed')
            raise DifyServiceError(
                _('Dify API authentication failed'),
                code=self.ERROR_AUTH
            )

        if response.status_code != 200:
            _logger.error('Dify API error: status=%d', response.status_code)
            raise DifyServiceError(
                _('Dify API returned error status: %d') % response.status_code,
                code=self.ERROR_APP,
            )

        try:
            result = response.json()
        except json.JSONDecodeError as e:
            _logger.error('Failed to parse Dify response')
            raise DifyServiceError(
                _('Failed to parse Dify API response'),
                code=self.ERROR_PARSE,
            )

        _logger.info('Dify API response received: latency=%.2fms', latency_ms)
        return result, latency_ms

    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 Dify 返回的响应

        :param response: Dify API 返回的原始响应
        :return: 解析后的结构化数据
        """
        try:
            if 'answer' not in response:
                raise DifyServiceError(
                    _('Dify response missing "answer" field'),
                    code=self.ERROR_RESPONSE,
                )

            answer = response.get('answer', '')
            conversation_id = response.get('conversation_id')

            parsed_intent = None
            if answer:
                parsed_intent = self._extract_json_from_answer(answer)

            return {
                'success': True,
                'answer': answer,
                'parsed_intent': parsed_intent,
                'conversation_id': conversation_id,
            }

        except DifyServiceError:
            raise
        except Exception as e:
            _logger.error('Error parsing Dify response: %s', str(e))
            raise DifyServiceError(
                _('Error parsing Dify response'),
                code=self.ERROR_PARSE,
            )

    def _extract_json_from_answer(self, answer: str) -> Optional[Dict[str, Any]]:
        """从 answer 中提取 JSON"""
        import re

        patterns = [
            r'\{[^{}]*\}',
            r'\{[\s\S]*?"[\w]+"[\s\S]*?\}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, answer)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and (
                        'category' in parsed or
                        'keywords' in parsed or
                        'intent' in parsed
                    ):
                        return parsed
                except (json.JSONDecodeError, TypeError):
                    continue

        try:
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

    def chat_with_parse(self, query: str,
                       conversation_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       inputs: Optional[Dict] = None) -> Tuple[Dict[str, Any], float, Optional[str]]:
        """
        调用 Dify 并自动解析响应

        :return: tuple (parsed_result, latency_ms, error_message)
        """
        error_message = None

        try:
            raw_response, latency_ms = self.chat(
                query=query,
                conversation_id=conversation_id,
                user_id=user_id,
                inputs=inputs,
            )

            result = self.parse_response(raw_response)
            return result, latency_ms, None

        except DifyServiceError as e:
            error_message = str(e)
            _logger.warning('Dify service error: %s', e)
            return {
                'success': False,
                'error': error_message,
                'error_code': e.code,
            }, 0, error_message

        except Exception as e:
            error_message = _('Unexpected error: %s') % str(e)
            _logger.error('Unexpected Dify service error: %s', str(e))
            return {
                'success': False,
                'error': error_message,
                'error_code': 'UNKNOWN_ERROR',
            }, 0, error_message