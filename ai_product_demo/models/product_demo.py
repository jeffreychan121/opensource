# -*- coding: utf-8 -*-
"""
AI Product Demo - 演示商品模型扩展

本模块用于扩展 product.template 添加演示用字段。
如果 yzl_field_model 模块已提供 x_scenario_tags 等字段，则本文件可为空。
"""

from odoo import models, fields, api


class ProductDemo(models.Model):
    """
    演示商品扩展模型

    添加 AI 商品搜索和商品对比所需的演示字段：
    - x_scenario_tags: 场景标签（逗号分隔）
    - x_selling_point: 核心卖点
    - x_target_people: 目标人群
    """
    _name = 'product.template'
    _inherit = 'product.template'

    # AI 商品理解字段
    x_scenario_tags = fields.Char(
        string='场景标签',
        help='逗号分隔的场景标签，如：商务,拍照,游戏'
    )
    x_selling_point = fields.Char(
        string='核心卖点',
        help='一句话描述商品核心卖点'
    )
    x_target_people = fields.Char(
        string='目标人群',
        help='目标购买人群，如：学生党,商务人士'
    )

    def get_demo_product_data(self):
        """
        获取演示商品数据的公共方法
        用于 AI 服务获取演示数据进行搜索和对比演示
        """
        return self.search_read(
            [('sale_ok', '=', True), ('active', '=', True)],
            [
                'name', 'default_code', 'categ_id', 'list_price',
                'standard_price', 'description_sale', 'brand_id',
                'weight', 'volume', 'x_scenario_tags', 'x_selling_point',
                'x_target_people', 'product_tag_ids'
            ],
            limit=100
        )
