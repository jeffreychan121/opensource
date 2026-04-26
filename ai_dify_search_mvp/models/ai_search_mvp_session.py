# -*- coding: utf-8 -*-
"""
@File   : ai_search_mvp_session.py
@Time   : 2026-04-21
@Desc   : AI 搜索 MVP 会话模型
"""

from odoo import models, fields


class AiSearchMvpSession(models.Model):
    """
    AI 搜索会话管理
    """
    _name = 'ai.search.mvp.session'
    _description = 'AI 搜索会话'
    _rec_name = 'session_key'

    session_key = fields.Char(
        string='会话标识',
        required=True,
        index=True,
    )

    conversation_id = fields.Char(
        string='Dify 会话 ID',
        help='Dify 返回的会话 ID，用于多轮对话',
    )

    last_query = fields.Text(
        string='最后查询',
    )

    last_parsed_intent = fields.Text(
        string='最后解析意图',
        help='JSON 格式的最后解析意图',
    )

    last_product_ids = fields.Text(
        string='最后商品 IDs',
        help='JSON 格式的最后返回商品 IDs',
    )

    active = fields.Boolean(
        string='激活',
        default=True,
        help='会话是否激活',
    )

    create_date = fields.Datetime(
        string='创建时间',
        readonly=True,
    )

    write_date = fields.Datetime(
        string='更新时间',
        readonly=True,
    )