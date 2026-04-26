# -*- coding: utf-8 -*-
"""
@File   :   ai_search_log.py
@Time   :   2024-04-14
@Desc   :   AI 搜索日志记录
"""

import logging
import json
import hashlib

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AiSearchLog(models.Model):
    """
    AI 搜索日志表
    记录每次搜索请求的详细信息，用于分析和问题排查
    """
    _name = 'ai.search.log'
    _description = 'AI Search Log'
    _order = 'create_date DESC'

    # ==================== 请求信息 ====================
    session_id = fields.Many2one(
        'ai.search.session',
        string='Session',
        index=True,
        ondelete='set null'
    )

    session_key = fields.Char(
        string='Session Key',
        index=True,
        help='Session key for quick lookup'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=0,
        help='Query sequence number within the session'
    )

    # ==================== 查询内容 ====================
    query = fields.Text(
        string='User Query',
        help='Original user query text'
    )

    query_hash = fields.Char(
        string='Query Hash',
        index=True,
        help='Hash of query for deduplication'
    )

    language = fields.Char(
        string='Language',
        default='zh_CN',
        help='Detected language of the query'
    )

    # ==================== 解析结果 ====================
    parsed_intent = fields.Json(
        string='Parsed Intent',
        help='Intent parsed by Dify or local fallback'
    )

    intent_source = fields.Selection([
        ('dify', 'Dify'),
        ('fallback', 'Local Fallback'),
    ], string='Intent Source', default='dify')

    # ==================== Dify 请求信息 ====================
    dify_request_id = fields.Char(
        string='Dify Request ID',
        index=True,
        help='Request ID returned by Dify API'
    )

    dify_conversation_id = fields.Char(
        string='Dify Conversation ID',
        index=True,
        help='Conversation ID used in Dify'
    )

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

    dify_latency = fields.Float(
        string='Dify Latency (ms)',
        default=0.0,
        help='Time taken by Dify API call in milliseconds'
    )

    # ==================== Odoo 搜索信息 ====================
    odoo_search_latency = fields.Float(
        string='Odoo Search Latency (ms)',
        default=0.0,
        help='Time taken by Odoo internal search in milliseconds'
    )

    applied_filters = fields.Json(
        string='Applied Filters',
        help='Filters actually applied to the search'
    )

    # ==================== 返回结果 ====================
    product_ids = fields.Json(
        string='Returned Product IDs',
        help='List of product IDs returned'
    )

    product_count = fields.Integer(
        string='Product Count',
        default=0,
        help='Number of products returned'
    )

    summary = fields.Text(
        string='AI Summary',
        help='AI-generated summary or recommendation text'
    )

    # ==================== 状态标记 ====================
    fallback_used = fields.Boolean(
        string='Fallback Used',
        default=False,
        index=True,
        help='Whether local fallback was used instead of Dify'
    )

    success = fields.Boolean(
        string='Success',
        default=True,
        index=True,
        help='Whether the request was successful'
    )

    error_message = fields.Text(
        string='Error Message',
        help='Error message if the request failed'
    )

    error_code = fields.Char(
        string='Error Code',
        index=True,
        help='Error code for categorization'
    )

    # ==================== 性能标记 ====================
    total_latency = fields.Float(
        string='Total Latency (ms)',
        default=0.0,
        help='Total time for the entire request'
    )

    # ==================== 调试信息 ====================
    debug_info = fields.Json(
        string='Debug Info',
        help='Additional debug information (not shown to users)'
    )

    # ==================== 时间戳 ====================
    create_date = fields.Datetime(
        string='Created',
        index=True,
        readonly=True
    )

    # ==================== 计算和约束 ====================
    @api.onchange('query')
    def _onchange_query(self):
        """当 query 变化时更新 hash 值"""
        if self.query:
            self.query_hash = hashlib.md5(self.query.encode('utf-8')).hexdigest()[:16]

    _sql_constraints = [
        ('query_hash_session_unique', 'UNIQUE(query_hash, session_id)',
         'Duplicate query in same session!')
    ]

    # ==================== CRUD ====================
    @api.model_create_multi
    def create(self, vals_list):
        """创建日志时设置默认值"""
        for vals in vals_list:
            if 'query' in vals and 'query_hash' not in vals:
                vals['query_hash'] = hashlib.md5(
                    vals['query'].encode('utf-8')
                ).hexdigest()[:16]
        return super().create(vals_list)

    # ==================== 业务方法 ====================
    def write_result(self, product_ids, summary=None, success=True,
                     error_message=None, error_code=None, debug_info=None):
        """
        更新日志结果

        :param product_ids: 返回的商品 ID 列表
        :param summary: AI 生成的总结
        :param success: 是否成功
        :param error_message: 错误信息
        :param error_code: 错误码
        :param debug_info: 调试信息
        :return: True
        """
        self.ensure_one()
        update_vals = {
            'product_ids': product_ids,
            'product_count': len(product_ids) if product_ids else 0,
            'summary': summary,
            'success': success,
            'error_message': error_message,
            'error_code': error_code,
        }
        if debug_info:
            update_vals['debug_info'] = debug_info
        self.write(update_vals)
        return True

    def set_latency(self, dify_latency=0.0, odoo_latency=0.0):
        """
        设置延迟信息

        :param dify_latency: Dify 调用延迟（毫秒）
        :param odoo_latency: Odoo 搜索延迟（毫秒）
        :return: True
        """
        self.write({
            'dify_latency': dify_latency,
            'odoo_search_latency': odoo_latency,
            'total_latency': dify_latency + odoo_latency,
        })
        return True

    @api.model
    def cleanup_old_logs(self, days=30):
        """
        清理旧日志
        由定时任务调用

        :param days: 保留多少天的日志
        """
        cutoff_date = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        old_logs = self.search([
            ('create_date', '<', cutoff_date)
        ])
        count = len(old_logs)
        if old_logs:
            old_logs.unlink()
            _logger.info('Cleaned up %d old AI search log entries', count)
        return True

    @api.model
    def log_search(self, session_id, query, parsed_intent=None,
                   fallback_used=False, success=True, error_message=None,
                   dify_latency=0.0, odoo_latency=0.0, product_ids=None,
                   summary=None, language='zh_CN', debug_info=None):
        """
        便捷方法：记录一次搜索

        :param session_id: 会话 ID
        :param query: 用户查询
        :param parsed_intent: 解析的意图
        :param fallback_used: 是否使用了 fallback
        :param success: 是否成功
        :param error_message: 错误信息
        :param dify_latency: Dify 延迟
        :param odoo_latency: Odoo 搜索延迟
        :param product_ids: 返回的商品 ID
        :param summary: AI 总结
        :param language: 语言
        :param debug_info: 调试信息
        :return: log record
        """
        # 获取 sequence 编号
        sequence = 0
        if session_id:
            last_log = self.search([
                ('session_id', '=', session_id.id)
            ], order='sequence DESC', limit=1)
            sequence = (last_log.sequence or 0) + 1

        vals = {
            'session_id': session_id.id if session_id else False,
            'session_key': session_id.session_key if session_id else None,
            'sequence': sequence,
            'query': query,
            'query_hash': hashlib.md5(query.encode('utf-8')).hexdigest()[:16],
            'language': language,
            'parsed_intent': parsed_intent,
            'intent_source': 'fallback' if fallback_used else 'dify',
            'fallback_used': fallback_used,
            'success': success,
            'error_message': error_message,
            'dify_latency': dify_latency,
            'odoo_search_latency': odoo_latency,
            'total_latency': dify_latency + odoo_latency,
            'product_ids': product_ids,
            'product_count': len(product_ids) if product_ids else 0,
            'summary': summary,
            'debug_info': debug_info,
        }

        log = self.create(vals)
        return log

    @api.model
    def get_recent_logs(self, limit=100, session_key=None):
        """
        获取最近的日志

        :param limit: 返回数量限制
        :param session_key: 可选的 session key 过滤
        :return: log recordset
        """
        domain = []
        if session_key:
            domain.append(('session_key', '=', session_key))
        return self.search(domain, order='create_date DESC', limit=limit)

    @api.model
    def get_statistics(self, days=7):
        """
        获取搜索统计数据

        :param days: 统计天数
        :return: dict with statistics
        """
        cutoff_date = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        logs = self.search([('create_date', '>=', cutoff_date)])

        return {
            'total_searches': len(logs),
            'successful_searches': len(logs.filtered(lambda l: l.success)),
            'failed_searches': len(logs.filtered(lambda l: not l.success)),
            'fallback_usage': len(logs.filtered(lambda l: l.fallback_used)),
            'avg_total_latency': sum(logs.mapped('total_latency')) / len(logs) if logs else 0,
            'avg_dify_latency': sum(logs.mapped('dify_latency')) / len(logs) if logs else 0,
            'avg_odoo_latency': sum(logs.mapped('odoo_search_latency')) / len(logs) if logs else 0,
            'avg_products_returned': sum(logs.mapped('product_count')) / len(logs) if logs else 0,
        }
