# -*- coding: utf-8 -*-
# author: chb

from odoo import http
from odoo.http import request
import json


class MCPController(http.Controller):

    @http.route('/mcp/sales/summary', methods=["GET", "POST"], type="json", auth="public", cors="*")
    def get_sales_summary(self, **kwargs):
        json_args = request.httprequest.get_json()
        start = json_args.get("start_date")
        end = json_args.get("end_date")
        total = request.env['sale.order'].sudo().search_read(
            [('date_order', '>=', start), ('date_order', '<=', end)],
            ['amount_total']
        )
        total_sales = sum([t['amount_total'] for t in total])
        return {
            "start_date": start,
            "end_date": end,
            "total_sales": total_sales
        }

    @http.route('/mcp/sales/create_order', methods=["GET", "POST"], type="json", auth="public", cors="*")
    def create_order(self, **kwargs):
        json_args = request.httprequest.get_json()
        sku = json_args.get("product_sku")
        qty = float(json_args.get("quantity", 1.0))

        product = request.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
        if not product:
            return {"error": f"未找到货号 {sku} 的产品"}

        partner = request.env['res.partner'].sudo().search([], limit=1)
        order = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty
            })]
        })
        return {"order_id": order.id, "message": f"销售订单已创建，ID: {order.name}"}

    @http.route('/mcp/product_stock', type='json', auth='public', methods=['POST'], csrf=False)
    def get_product_stock(self, **kwargs):
        json_args = request.httprequest.get_json()
        sku = json_args.get("product_sku")
        if not sku:
            return {"error": "缺少参数: sku"}
        request.update_env(user=1, su=True)

        product = request.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
        if not product:
            return {"error": "未找到该货号的产品"}

        qty_available = product.qty_available

        return {
            "sku": sku,
            "product_name": product.name,
            "qty_available": qty_available,
            "price": product.list_price
        }