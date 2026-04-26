# -*- coding: utf-8 -*-
"""
@File   :   ai_search_session.py
@Time   :   2024-04-14
@Desc   :   AI 搜索会话管理
"""

import logging
import secrets
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AiSearchSession(models.Model):
    """
    AI 搜索会话表
    用于管理用户与 AI 搜索的多轮对话上下文
    """
    _name = 'ai.search.session'
    _description = 'AI Search Session'
    _order = 'write_date DESC'

    # ==================== 会话标识 ====================
    session_key = fields.Char(
        string='Session Key',
        required=True,
        index=True,
        default=lambda self: secrets.token_urlsafe(32),
        help='Unique identifier for the search session'
    )

    # ==================== 用户信息 ====================
    website_visitor_id = fields.Char(
        string='Website Visitor ID',
        index=True,
        help='Website visitor identifier from session'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        index=True,
        help='Logged-in partner if available'
    )

    user_id = fields.Many2one(
        'res.users',
        string='User',
        index=True,
        help='Odoo user who initiated the search'
    )

    website_id = fields.Many2one(
        'website',
        string='Website',
        index=True,
        help='Website where the search was initiated'
    )

    # ==================== 对话上下文 ====================
    conversation_id = fields.Char(
        string='Dify Conversation ID',
        index=True,
        help='Conversation ID returned by Dify for multi-turn chat'
    )

    last_query = fields.Text(
        string='Last Query',
        help='The most recent user query in this session'
    )

    last_parsed_intent = fields.Json(
        string='Last Parsed Intent',
        help='JSON object representing the parsed search intent'
    )

    last_applied_filters = fields.Json(
        string='Last Applied Filters',
        help='Filters that were actually applied to the last search'
    )

    last_product_ids = fields.Json(
        string='Last Product IDs',
        help='List of product IDs returned in the last search'
    )

    last_summary = fields.Text(
        string='Last AI Summary',
        help='AI-generated summary from the last search'
    )

    # ==================== 交互统计 ====================
    query_count = fields.Integer(
        string='Query Count',
        default=0,
        help='Number of queries in this session'
    )

    query_history = fields.Json(
        string='Query History',
        default=list,
        help='List of previous queries with timestamps'
    )

    # ==================== 状态 ====================
    active = fields.Boolean(
        string='Active',
        default=True,
        index=True,
        help='Whether this session is still active'
    )

    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('closed', 'Closed'),
    ], string='State', default='active', index=True)

    # ==================== 时间戳 ====================
    create_date = fields.Datetime(
        string='Created',
        index=True,
        readonly=True
    )

    write_date = fields.Datetime(
        string='Last Updated',
        index=True,
        readonly=True
    )

    last_query_date = fields.Datetime(
        string='Last Query Time',
        help='Timestamp of the last query in this session'
    )

    expire_date = fields.Datetime(
        string='Expire Date',
        compute='_compute_expire_date',
        store=True,
        index=True,
        help='When this session will expire'
    )

    # ==================== 计算字段 ====================
    @api.depends('last_query_date')
    def _compute_expire_date(self):
        """根据最后查询时间和配置的过期时长计算过期时间"""
        ICP = self.env['ir.config_parameter'].sudo()
        expire_hours = int(ICP.get_param('ai_dify_search.session_expire_hours', 24))
        for record in self:
            if record.last_query_date:
                record.expire_date = record.last_query_date + timedelta(hours=expire_hours)
            else:
                record.expire_date = fields.Datetime.now() + timedelta(hours=expire_hours)

    # ==================== 约束 ====================
    _sql_constraints = [
        ('session_key_unique', 'UNIQUE(session_key)', 'Session key must be unique!')
    ]

    # ==================== Async Polling ====================
    task_id = fields.Char(
        string='Dify Task ID',
        index=True,
        help='Task ID for async polling'
    )

    poll_status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Poll Status', default='pending')

    poll_result = fields.Json(
        string='Poll Result',
        help='Cached poll result when completed'
    )

    # ==================== CRUD ====================
    @api.model_create_multi
    def create(self, vals_list):
        """创建会话时初始化相关字段"""
        for vals in vals_list:
            if 'last_query_date' not in vals:
                vals['last_query_date'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        """更新会话时刷新过期时间"""
        res = super().write(vals)
        if 'last_query_date' in vals:
            self._compute_expire_date()
        return res

    # ==================== 业务方法 ====================
    def add_query(self, query, parsed_intent=None, applied_filters=None,
                  product_ids=None, summary=None, conversation_id=None):
        """
        向会话添加一条查询记录

        :param query: 用户输入的查询文本
        :param parsed_intent: 解析后的意图 JSON
        :param applied_filters: 实际应用的过滤条件
        :param product_ids: 返回的商品 ID 列表
        :param summary: AI 生成的总结
        :param conversation_id: Dify 返回的会话 ID
        :return: True
        """
        self.ensure_one()

        # 更新历史记录
        history = self.query_history or []
        history.append({
            'query': query,
            'timestamp': fields.Datetime.now().isoformat(),
            'parsed_intent': parsed_intent,
        })
        # 保留最近 20 条历史
        history = history[-20:]

        # 构建更新值
        update_vals = {
            'last_query': query,
            'last_parsed_intent': parsed_intent,
            'last_applied_filters': applied_filters,
            'last_product_ids': product_ids,
            'last_summary': summary,
            'query_count': self.query_count + 1,
            'query_history': history,
            'last_query_date': fields.Datetime.now(),
            'active': True,
            'state': 'active',
        }

        # 更新 conversation_id（如果 Dify 返回了新的）
        if conversation_id:
            update_vals['conversation_id'] = conversation_id

        self.write(update_vals)
        return True

    def close_session(self):
        """关闭当前会话"""
        self.write({
            'active': False,
            'state': 'closed'
        })
        return True

    @api.model
    def get_or_create_session(self, session_key=None, website_visitor_id=None,
                              partner_id=None, user_id=None, website_id=None):
        """
        获取或创建一个搜索会话

        :param session_key: 传入的 session key，如果为空则创建新的
        :param website_visitor_id: 网站访问者 ID
        :param partner_id: 合作伙伴 ID
        :param user_id: 用户 ID
        :param website_id: 网站 ID
        :return: tuple(session, created)
        """
        session = None
        created = False

        if session_key:
            session = self.sudo().search([
                ('session_key', '=', session_key),
                ('active', '=', True),
                ('state', '=', 'active'),
            ], limit=1)

        if not session:
            # 创建新会话 (使用 sudo 以便 public 用户创建会话)
            session = self.sudo().create({
                'session_key': session_key or secrets.token_urlsafe(32),
                'website_visitor_id': website_visitor_id,
                'partner_id': partner_id,
                'user_id': user_id,
                'website_id': website_id,
            })
            created = True

        return session, created

    @api.model
    def cleanup_expired_sessions(self):
        """
        清理过期的会话
        由定时任务调用
        """
        now = fields.Datetime.now()
        expired_sessions = self.search([
            ('expire_date', '<', now),
            ('state', '=', 'active'),
        ])
        if expired_sessions:
            expired_sessions.write({'state': 'expired', 'active': False})
            _logger.info('Cleaned up %d expired AI search sessions', len(expired_sessions))
        return True

    @api.model
    def get_session_by_key(self, session_key):
        """
        根据 key 获取活跃会话

        :param session_key: 会话 key
        :return: session recordset
        """
        return self.sudo().search([
            ('session_key', '=', session_key),
            ('active', '=', True),
            ('state', '=', 'active'),
        ], limit=1)

    def update_poll_status(self, task_id, status, result=None):
        """Update async polling status"""
        self.write({
            'task_id': task_id,
            'poll_status': status,
            'poll_result': result,
        })
        return True
