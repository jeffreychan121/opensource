# -*- coding: utf-8 -*-
"""
@File   : ai_search_mvp_log.py
@Time   : 2026-04-21
@Desc   : AI 搜索 MVP 日志模型
"""

from odoo import models, fields


class AiSearchMvpLog(models.Model):
    """
    AI 搜索日志
    """
    _name = 'ai.search.mvp.log'
    _description = 'AI 搜索日志'
    _order = 'create_date desc'

    query = fields.Text(
        string='用户查询',
        required=True,
    )

    session_key = fields.Char(
        string='会话标识',
        index=True,
    )

    parsed_intent = fields.Text(
        string='解析意图',
        help='JSON 格式的解析意图',
    )

    product_ids = fields.Text(
        string='商品 IDs',
        help='JSON 格式的商品 ID 列表',
    )

    fallback_used = fields.Boolean(
        string='使用 Fallback',
        default=False,
    )

    success = fields.Boolean(
        string='成功',
        default=True,
    )

    error_message = fields.Text(
        string='错误信息',
    )

    dify_latency_ms = fields.Float(
        string='Dify 延迟（毫秒）',
    )

    search_latency_ms = fields.Float(
        string='搜索延迟（毫秒）',
    )

    total_latency_ms = fields.Float(
        string='总延迟（毫秒）',
    )

    create_date = fields.Datetime(
        string='创建时间',
        readonly=True,
    )