# -*- coding: utf-8 -*-
"""
@File   : session_service.py
@Time   : 2026-04-21
@Desc   : 会话管理服务
"""

import logging
import json
import uuid
from typing import Optional

_logger = logging.getLogger(__name__)


class AiSearchMvpSessionService:
    """
    会话管理服务
    """

    def __init__(self, env):
        self.env = env

    def get_or_create_session(self, session_key: Optional[str] = None):
        """获取或创建会话"""
        if not session_key:
            session_key = str(uuid.uuid4())

        session = self.env['ai.search.mvp.session'].sudo().search(
            [('session_key', '=', session_key)], limit=1
        )

        if not session:
            session = self.env['ai.search.mvp.session'].sudo().create({
                'session_key': session_key,
                'active': True,
            })

        return session

    def update_session(self, session_key: str, **vals):
        """更新会话"""
        session = self.env['ai.search.mvp.session'].sudo().search(
            [('session_key', '=', session_key)], limit=1
        )

        if session:
            session.write(vals)

        return session

    def close_session(self, session_key: str):
        """关闭会话"""
        session = self.env['ai.search.mvp.session'].sudo().search(
            [('session_key', '=', session_key)], limit=1
        )

        if session:
            session.write({'active': False})

        return True

    def get_session(self, session_key: str):
        """获取会话"""
        return self.env['ai.search.mvp.session'].sudo().search(
            [('session_key', '=', session_key)], limit=1
        )