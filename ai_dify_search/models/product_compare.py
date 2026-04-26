# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductCompare(models.Model):
    _inherit = "product.template"

    # ===== 产品对比字段 =====
    # 卖点（逗号分隔，如 "省油30%,动力强劲"）
    compare_selling_points = fields.Char(string='Compare Selling Points')
    # 适用人群（逗号分隔，如 "商用钓鱼,户外作业"）
    compare_target_people = fields.Char(string='Compare Target People')
    # 适用场景（逗号分隔，如 "海洋作业,淡水钓鱼"）
    compare_scenes = fields.Char(string='Compare Scenes')
    # 规格参数（JSON格式，如 [{"name":"马力","value":"200HP"}]）
    compare_attributes = fields.Text(string='Compare Attributes')
    # 产品亮点（如 "潜艇级钢材,耐腐蚀"）
    compare_highlights = fields.Char(string='Compare Highlights')
    # 保修信息（如 "2年质保,全国联保"）
    compare_warranty = fields.Char(string='Compare Warranty')
