# -*- coding: utf-8 -*-
"""
@File   :   ai_dify_config.py
@Time   :   2024-04-15
@Desc   :   Dify 配置模型
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class AiDifyConfig(models.Model):
    """
    Dify 配置表
    存储 AI 商品搜索的 Dify 连接配置
    """
    _name = 'ai.dify.config'
    _description = 'Dify 配置'
    _rec_name = 'name'

    # ==================== 基本信息 ====================
    name = fields.Char(
        string='配置名称',
        default='默认配置',
        required=True,
        help='配置的唯一标识名称'
    )

    # ==================== Dify API 配置 ====================
    dify_api_base_url = fields.Char(
        string='Dify API 地址',
        default='https://api.dify.ai/v1',
        required=True,
        help='''Dify 平台的 API 接口地址。
        - SaaS 版：https://api.dify.ai/v1
        - 自部署：请填写你的 Dify 服务器地址
        注意：必须以 /v1 结尾'''
    )

    dify_api_key = fields.Char(
        string='Dify API Key',
        default='',
        help='''Dify 应用的 API Key，用于认证。
        获取方式：Dify 首页 -> 应用 -> API Key'''
    )

    dify_app_id = fields.Char(
        string='Dify 应用 ID',
        default='',
        help='''Dify Chatflow 应用的 ID。
        获取方式：Dify 首页 -> 应用 -> 复制 App ID'''
    )

    dify_compare_api_key = fields.Char(
        string='AI对比 API Key',
        default='',
        help='''AI对比 Dify 应用的 API Key。
        获取方式：Dify 首页 -> 应用 -> API Key'''
    )

    dify_compare_app_id = fields.Char(
        string='AI对比应用 ID',
        default='',
        help='''AI对比 Chatflow 应用的 ID。
        获取方式：Dify 首页 -> 应用 -> 复制 App ID'''
    )

    dify_compare_base_url = fields.Char(
        string='AI对比 API 地址',
        default='',
        help='''AI对比 Dify 应用的 API 地址。
        如果与 AI 搜索应用相同，可以留空'''
    )

    dify_user_prefix = fields.Char(
        string='用户标识前缀',
        default='odoo_user_',
        help='''生成 Dify 用户标识的前缀。
        例如：odoo_user_ + 用户ID = odoo_user_123'''
    )

    dify_timeout = fields.Integer(
        string='API 超时时间（秒）',
        default=30,
        help='''调用 Dify API 的最大等待时间。
        建议值：30-60秒'''
    )

    # ==================== 内部搜索配置 ====================
    internal_search_token = fields.Char(
        string='内部搜索令牌',
        default='',
        help='''用于 Dify 调用 Odoo 内部搜索接口的令牌。
        设置步骤：
        1. 在此处填写一个随机字符串（如：sk-ai-search-2024）
        2. 在 Dify 的 HTTP Request 节点中使用相同的值'''
    )

    # ==================== 搜索参数 ====================
    search_top_k = fields.Integer(
        string='默认返回商品数量',
        default=8,
        help='''AI 搜索默认返回的商品数量。
        建议值：8-20'''
    )

    # ==================== 向量搜索配置 ====================
    vector_search_enabled = fields.Boolean(
        string='启用向量搜索（pgvector）',
        default=False,
        help='''启用基于商品描述的语义搜索功能。
        前提条件：
        - Odoo 数据库已安装 pgvector 扩展
        - 商品已有描述文本'''
    )

    vector_search_limit = fields.Integer(
        string='向量搜索返回数量',
        default=20,
        help='''向量搜索的最大返回数量。
        建议值：20-50'''
    )

    # ==================== 功能开关 ====================
    ai_search_enabled = fields.Boolean(
        string='启用 AI 智能搜索',
        default=False,
        help='开启后，用户可以在网站前端使用 AI 智能搜索功能。'
    )

    ai_search_log_enabled = fields.Boolean(
        string='启用搜索日志',
        default=True,
        help='''记录所有搜索查询和响应，用于分析和优化。'''
    )

    fallback_enabled = fields.Boolean(
        string='Dify 失败时启用本地搜索',
        default=True,
        help='''当 Dify AI 服务不可用时，自动降级到本地关键词搜索。
        建议保持开启。'''
    )

    followup_enabled = fields.Boolean(
        string='启用追问功能',
        default=True,
        help='''允许用户在搜索结果基础上继续追问或细化需求。'''
    )

    # ==================== 缓存与性能 ====================
    search_cache_ttl = fields.Integer(
        string='搜索缓存时间（秒）',
        default=300,
        help='''相同查询的缓存有效期。
        建议值：300秒（5分钟）'''
    )

    # ==================== 调试配置 ====================
    debug_mode = fields.Boolean(
        string='调试模式',
        default=False,
        help='''开启后，搜索结果会包含详细的调试信息。
        仅用于排查问题，生产环境请关闭。'''
    )

    # ==================== Session 配置 ====================
    session_expire_hours = fields.Integer(
        string='会话有效期（小时）',
        default=24,
        help='''AI 搜索会话的过期时间。
        建议值：24-72小时'''
    )

    # ==================== 约束验证 ====================
    @api.constrains('dify_timeout')
    def _check_dify_timeout(self):
        for record in self:
            if record.dify_timeout and record.dify_timeout < 5:
                raise ValidationError('Dify 超时时间最少为 5 秒。')

    @api.constrains('search_top_k')
    def _check_search_top_k(self):
        for record in self:
            if record.search_top_k and (record.search_top_k < 1 or record.search_top_k > 100):
                raise ValidationError('返回商品数量必须在 1-100 之间。')

    @api.constrains('session_expire_hours')
    def _check_session_expire_hours(self):
        for record in self:
            if record.session_expire_hours and record.session_expire_hours < 1:
                raise ValidationError('会话有效期最少为 1 小时。')

    # ==================== 单例模式 ====================
    @api.model
    def get_active_config(self):
        """
        获取当前激活的配置（单例模式）
        如果不存在配置记录，则创建一个默认配置
        """
        # 使用 sudo() 以便 public 用户访问配置
        config = self.sudo().search([], limit=1)
        if not config:
            config = self.sudo().create({
                'name': '默认配置',
            })
        return config.sudo()

    # ==================== 写入处理 ====================
    def write(self, vals):
        """写入配置"""
        return super().write(vals)
