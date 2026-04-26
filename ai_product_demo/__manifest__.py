# -*- coding: utf-8 -*-
{
    'name': 'AI Product Demo - 演示商品数据',
    'version': '1.0',
    'category': 'YZL/YZL',
    'summary': 'AI 商品搜索演示用商品数据',
    'description': '''
        AI 商品搜索和商品对比演示用数据
        - 演示商品（手机、耳机、笔记本等）
        - 商品理解数据
        - 搜索/对比/导购案例
    ''',
    'author': 'YZL',
    'depends': ['product', 'product_extension', 'yzl_field_model'],
    'data': [
        'data/product_category_init.xml',
        'data/product_demo_data.xml',
    ],
    'installable': True,
    'application': True,
}
