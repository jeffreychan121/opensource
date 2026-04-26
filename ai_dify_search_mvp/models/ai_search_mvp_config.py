# -*- coding: utf-8 -*-
"""
@File   : ai_search_mvp_config.py
@Time   : 2026-04-21
@Desc   : AI 搜索 MVP 配置模型
"""

import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AiSearchMvpConfig(models.Model):
    """
    AI 搜索 MVP 配置表
    单例模式，所有配置存放在一条记录中
    """
    _name = 'ai.search.mvp.config'
    _description = 'AI 搜索 MVP 配置'
    _rec_name = 'name'

    name = fields.Char(
        string='配置名称',
        default='默认配置',
        required=True,
    )

    enable_ai_search = fields.Boolean(
        string='启用 AI 搜索',
        default=False,
        help='开启后用户可以使用 AI 智能搜索功能',
    )

    dify_api_base_url = fields.Char(
        string='Dify API 地址',
        default='https://api.dify.ai/v1',
        required=True,
        help='Dify 平台的 API 接口地址',
    )

    dify_api_key = fields.Char(
        string='Dify API Key',
        default='',
        help='Dify 应用的 API Key，用于认证',
    )

    dify_app_id = fields.Char(
        string='Dify App ID',
        default='',
        help='Dify Chatflow 应用的 ID',
    )

    dify_timeout = fields.Integer(
        string='API 超时时间（秒）',
        default=30,
        help='调用 Dify API 的最大等待时间',
    )

    internal_token = fields.Char(
        string='内部搜索令牌',
        default='',
        help='用于 Dify 调用 Odoo 内部搜索接口的令牌',
    )

    search_top_k = fields.Integer(
        string='默认返回商品数量',
        default=8,
        help='AI 搜索默认返回的商品数量',
    )

    enable_fallback = fields.Boolean(
        string='启用 Fallback',
        default=True,
        help='当 Dify 服务不可用时，自动降级到本地搜索',
    )

    enable_logging = fields.Boolean(
        string='启用搜索日志',
        default=True,
        help='记录所有搜索查询和响应',
    )

    debug_mode = fields.Boolean(
        string='调试模式',
        default=False,
        help='开启后搜索结果会包含详细调试信息',
    )

    @api.constrains('dify_timeout')
    def _check_dify_timeout(self):
        for record in self:
            if record.dify_timeout and record.dify_timeout < 5:
                raise ValidationError('Dify 超时时间最少为 5 秒')

    @api.constrains('search_top_k')
    def _check_search_top_k(self):
        for record in self:
            if record.search_top_k and (record.search_top_k < 1 or record.search_top_k > 100):
                raise ValidationError('返回商品数量必须在 1-100 之间')

    @api.model
    def get_active_config(self):
        """
        获取当前激活的配置（单例模式）
        """
        config = self.sudo().search([], limit=1)
        if not config:
            config = self.sudo().create({'name': '默认配置'})
        return config.sudo()
