# -*- coding: utf-8 -*-
# author: chb

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


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

    @http.route('/mcp/test_bot', type='json', auth='public', methods=['POST'], csrf=False)
    def test_bot(self, **kwargs):
        """测试端点：手动触发 bot 回复到指定 channel"""
        json_args = request.httprequest.get_json()
        channel_id = json_args.get('channel_id')
        message = json_args.get('message', 'Hello')

        if not channel_id:
            return {"error": "缺少 channel_id"}

        try:
            channel = request.env['mail.channel'].sudo().browse(int(channel_id))
            if not channel.exists():
                return {"error": "Channel 不存在"}

            odoo_bot = request.env.ref("base.partner_root1")
            odoo_partner = odoo_bot.partner_id

            # 直接发送消息
            channel.with_context(mcp_bot_post=True).message_post(
                body=f"<p>测试回复: {message}</p>",
                author_id=odoo_partner.id,
                email_add_signature=False,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            return {"ok": True, "message": "已发送测试消息"}
        except Exception as e:
            _logger.error(f"Test bot error: {e}")
            return {"error": str(e)}