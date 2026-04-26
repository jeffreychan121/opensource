# -*- coding: utf-8 -*-
"""
@File   :   session_service.py
@Time   :   2024-04-14
@Desc   :   会话管理服务
"""

import logging
from typing import Optional, Tuple, Dict, Any

from odoo import fields

_logger = logging.getLogger(__name__)


class AiSessionService:
    """
    AI 搜索会话服务
    负责会话的创建、更新、查询等操作
    """

    def __init__(self, env):
        """
        初始化会话服务

        :param env: Odoo environment
        """
        self.env = env
        self._config_service = None

    @property
    def config_service(self):
        """懒加载配置服务"""
        if self._config_service is None:
            from .config_service import AiSearchConfigService
            self._config_service = AiSearchConfigService(self.env)
        return self._config_service

    def get_or_create_session(self, session_key: Optional[str] = None,
                               website_visitor_id: Optional[str] = None,
                               partner_id: Optional[int] = None,
                               user_id: Optional[int] = None,
                               website_id: Optional[int] = None) -> Tuple[Dict[str, Any], bool]:
        """
        获取或创建搜索会话

        :param session_key: 传入的 session key
        :param website_visitor_id: 网站访问者 ID
        :param partner_id: 合作伙伴 ID
        :param user_id: 用户 ID
        :param website_id: 网站 ID
        :return: tuple (session_dict, created)
        """
        session_model = self.env['ai.search.session'].sudo()

        if session_key:
            # 尝试查找现有会话
            session = session_model.get_session_by_key(session_key)
            if session:
                _logger.debug('Found existing session: %s', session_key)
                return self._session_to_dict(session), False

        # 创建新会话
        session, created = session_model.get_or_create_session(
            session_key=session_key,
            website_visitor_id=website_visitor_id,
            partner_id=partner_id,
            user_id=user_id,
            website_id=website_id,
        )

        _logger.info('Created new session: %s', session.session_key)
        return self._session_to_dict(session), created

    def update_session(self, session_key: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        更新会话信息

        :param session_key: 会话 key
        :param kwargs: 要更新的字段
        :return: 更新后的 session dict 或 None
        """
        session_model = self.env['ai.search.session'].sudo()
        session = session_model.get_session_by_key(session_key)

        if not session:
            _logger.warning('Session not found for update: %s', session_key)
            return None

        # 处理特殊字段
        if 'parsed_intent' in kwargs:
            kwargs['last_parsed_intent'] = kwargs.pop('parsed_intent')

        if 'applied_filters' in kwargs:
            kwargs['last_applied_filters'] = kwargs.pop('applied_filters')

        if 'product_ids' in kwargs:
            kwargs['last_product_ids'] = kwargs.pop('product_ids')

        if 'summary' in kwargs:
            kwargs['last_summary'] = kwargs.pop('summary')

        if 'conversation_id' in kwargs:
            kwargs['conversation_id'] = kwargs.pop('conversation_id')

        session.write(kwargs)

        _logger.debug('Updated session: %s', session_key)
        return self._session_to_dict(session)

    def add_query_to_session(self, session_key: str, query: str,
                              parsed_intent: Optional[Dict] = None,
                              applied_filters: Optional[Dict] = None,
                              product_ids: Optional[list] = None,
                              summary: Optional[str] = None,
                              conversation_id: Optional[str] = None) -> bool:
        """
        向会话添加查询记录

        :param session_key: 会话 key
        :param query: 用户查询
        :param parsed_intent: 解析的意图
        :param applied_filters: 应用的过滤条件
        :param product_ids: 返回的商品 ID
        :param summary: AI 总结
        :param conversation_id: Dify 会话 ID
        :return: 是否成功
        """
        session_model = self.env['ai.search.session'].sudo()
        session = session_model.get_session_by_key(session_key)

        if not session:
            _logger.warning('Session not found for adding query: %s', session_key)
            return False

        session.add_query(
            query=query,
            parsed_intent=parsed_intent,
            applied_filters=applied_filters,
            product_ids=product_ids,
            summary=summary,
            conversation_id=conversation_id,
        )

        _logger.info('Added query to session: %s, query: %s', session_key, query[:50])
        return True

    def close_session(self, session_key: str) -> bool:
        """
        关闭会话

        :param session_key: 会话 key
        :return: 是否成功
        """
        session_model = self.env['ai.search.session'].sudo()
        session = session_model.get_session_by_key(session_key)

        if not session:
            return False

        session.close_session()
        _logger.info('Closed session: %s', session_key)
        return True

    def get_session_context(self, session_key: str) -> Dict[str, Any]:
        """
        获取会话上下文用于传递到搜索服务

        :param session_key: 会话 key
        :return: 上下文字典
        """
        session_model = self.env['ai.search.session'].sudo()
        session = session_model.get_session_by_key(session_key)

        if not session:
            return {}

        return {
            'session_key': session.session_key,
            'conversation_id': session.conversation_id,
            'last_query': session.last_query,
            'last_parsed_intent': session.last_parsed_intent,
            'last_applied_filters': session.last_applied_filters,
            'last_product_ids': session.last_product_ids,
            'query_count': session.query_count,
            'query_history': session.query_history or [],
        }

    def _session_to_dict(self, session) -> Dict[str, Any]:
        """
        将 session record 转换为字典

        :param session: ai.search.session record
        :return: session 字典
        """
        return {
            'id': session.id,
            'session_key': session.session_key,
            'conversation_id': session.conversation_id,
            'last_query': session.last_query,
            'last_parsed_intent': session.last_parsed_intent,
            'last_applied_filters': session.last_applied_filters,
            'last_product_ids': session.last_product_ids,
            'last_summary': session.last_summary,
            'query_count': session.query_count,
            'query_history': session.query_history or [],
            'active': session.active,
            'state': session.state,
            'create_date': session.create_date.isoformat() if session.create_date else None,
            'last_query_date': session.last_query_date.isoformat() if session.last_query_date else None,
            'expire_date': session.expire_date.isoformat() if session.expire_date else None,
        }

    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        :return: 清理的会话数量
        """
        session_model = self.env['ai.search.session'].sudo()
        before_count = session_model.search_count([('state', '=', 'active')])
        session_model.cleanup_expired_sessions()
        after_count = session_model.search_count([('state', '=', 'active')])
        cleaned = before_count - after_count
        _logger.info('Cleaned up %d expired sessions', cleaned)
        return cleaned
