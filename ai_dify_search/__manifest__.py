# -*- coding: utf-8 -*-
{
    'name': "YZL-AI Dify 智能搜索",
    'summary': "基于 Dify Chatflow 的 AI 商品搜索导购模块",
    'description': """
        YZL-AI Dify 智能搜索模块
        ========================
        支持自然语言商品搜索、Dify AI 编排、Odoo 真实商品检索、智能推荐总结。

        功能特性：
        - 自然语言 query 解析
        - 多轮对话上下文记忆
        - AI 推荐理由生成
        - 无结果时智能放宽建议
        - Dify 不可用时自动降级到本地搜索
        - 会话管理与日志记录
    """,
    'author': "YZL",
    'website': "https://www.yzl.co.zw/",
    'category': 'YZL/YZL',
    'version': '0.2',
    'depends': [
        'base',
        'web',
        'product',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/ai_search_menu.xml',
        'views/ai_dify_config_views.xml',
        'data/ir_cron_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_dify_search/static/src/js/ai_search_mock_data.js',
            'ai_dify_search/static/src/js/ai_search_page.js',
            'ai_dify_search/static/src/xml/ai_search_page.xml',
            'ai_dify_search/static/src/css/ai_search.css'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
