# -*- coding: utf-8 -*-
{
    'name': 'YZL-AI Dify 智能搜索 MVP',
    'summary': '基于 Dify Chatflow 的 AI 商品搜索 MVP 模块（最小闭环）',
    'version': '0.1',
    'depends': ['base', 'web', 'product', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_search_mvp_config_views.xml',
        'views/ai_search_mvp_menu.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_dify_search_mvp/static/src/js/ai_search_mvp_page.js',
            'ai_dify_search_mvp/static/src/xml/ai_search_mvp_page.xml',
            'ai_dify_search_mvp/static/src/css/ai_search_mvp.css',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
