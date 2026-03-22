# -*- coding: utf-8 -*-
# author: chb
from odoo import http
from odoo.http import request
import uuid
import time


class MCPCatewayController(http.Controller):
    """
    MCP 统一入口：/mcp/call
    """

    @http.route('/mcp/call', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def mcp_call(self, **kwargs):
        payload = request.httprequest.get_json() or {}
        fn_name = payload.get("function")
        args = payload.get("args") or payload

        if not fn_name:
            fn_name = self._guess_function(args)

        audit_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"

        dispatch = {
            "get_sales_summary": self._fn_get_sales_summary,
            "create_sales_order": self._fn_create_sales_order,
            "create_sales_order_auto": self._fn_create_sales_order_auto,
            "get_product_stock": self._fn_get_product_stock,
            "search_products": self._fn_search_products,
            "create_product": self._fn_create_product,
            "get_customer_info": self._fn_get_customer_info,
            "create_customer": self._fn_create_customer,
            "get_order_status": self._fn_get_order_status,
            "cancel_order": self._fn_cancel_order,
            "get_product_pricelist": self._fn_get_product_pricelist,
            "get_delivery_status": self._fn_get_delivery_status,
        }

        if fn_name not in dispatch:
            return self._err("NOT_FOUND",
                             f"unknown function '{fn_name}'. "
                             f"allowed: {', '.join(dispatch.keys())}",
                             audit_id, fn_name)

        ok, msg = self._validate(fn_name, args)
        if not ok:
            return self._err("VALIDATION", msg, audit_id, fn_name)

        try:
            data = dispatch[fn_name](args)
            return {"ok": True, "function": fn_name, "data": data, "audit_id": audit_id}
        except Exception as e:
            return self._err("BUSINESS", str(e), audit_id, fn_name)

    def _guess_function(self, args: dict) -> str:
        if all(k in args for k in ("start_date", "end_date")):
            return "get_sales_summary"
        if "product_sku" in args and "quantity" in args:
            return "create_sales_order"
        if "product_sku" in args:
            return "get_product_stock"
        if "keyword" in args:
            return "search_products"
        if "partner_name" in args or "phone" in args or "email" in args:
            return "get_customer_info"
        if "name" in args and not args.get("product_sku") and not args.get("order_id"):
            return "create_customer"
        if "order_id" in args or "order_name" in args:
            return "get_order_status"
        return "unknown"

    def _validate(self, fn_name: str, args: dict):
        if fn_name == "get_sales_summary":
            if not args.get("start_date") or not args.get("end_date"):
                return False, "required: start_date, end_date (YYYY-MM-DD)"
            return True, ""
        if fn_name == "create_sales_order":
            if not args.get("product_sku"):
                return False, "required: product_sku"
            if "quantity" not in args:
                return False, "required: quantity"
            try:
                float(args.get("quantity"))
            except Exception:
                return False, "quantity must be a number"
            return True, ""
        if fn_name == "create_sales_order_auto":
            # 无则创建：客户和产品都可以自动创建
            return True, ""
        if fn_name == "get_product_stock":
            if not args.get("product_sku"):
                return False, "required: product_sku"
            return True, ""
        if fn_name == "search_products":
            if not args.get("keyword") and not args.get("category"):
                return False, "required: keyword or category"
            return True, ""
        if fn_name == "create_product":
            if not args.get("name"):
                return False, "required: name"
            return True, ""
        if fn_name == "get_customer_info":
            if not args.get("partner_id") and not args.get("partner_name") and not args.get("phone") and not args.get("email"):
                return False, "required: partner_id or partner_name or phone or email"
            return True, ""
        if fn_name == "create_customer":
            if not args.get("name"):
                return False, "required: name"
            return True, ""
        if fn_name == "get_order_status":
            if not args.get("order_id") and not args.get("order_name"):
                return False, "required: order_id or order_name"
            return True, ""
        if fn_name == "cancel_order":
            if not args.get("order_id") and not args.get("order_name"):
                return False, "required: order_id or order_name"
            return True, ""
        if fn_name == "get_product_pricelist":
            if not args.get("product_sku"):
                return False, "required: product_sku"
            return True, ""
        if fn_name == "get_delivery_status":
            if not args.get("order_id") and not args.get("order_name"):
                return False, "required: order_id or order_name"
            return True, ""
        return False, "unknown function"

    def _err(self, code: str, message: str, audit_id: str, fn_name: str = None):
        return {"ok": False, "function": fn_name, "error": {"code": code, "message": message}, "audit_id": audit_id}

    # ========== 销售相关函数 ==========

    def _fn_get_sales_summary(self, args: dict):
        start = args.get("start_date")
        end = args.get("end_date")
        recs = request.env['sale.order'].sudo().search_read(
            [('date_order', '>=', start), ('date_order', '<=', end)],
            ['amount_total', 'state']
        )
        total_sales = sum(r['amount_total'] for r in recs)
        order_count = len(recs)
        delivered_count = len([r for r in recs if r.get('state') == 'done'])
        return {
            "start_date": start,
            "end_date": end,
            "total_sales": total_sales,
            "order_count": order_count,
            "delivered_count": delivered_count,
            "currency": "CNY"
        }

    def _fn_create_sales_order(self, args: dict):
        sku = args.get("product_sku")
        qty = float(args.get("quantity", 1.0))
        partner_id = args.get("partner_id")
        partner_name = args.get("partner_name")
        unit_price = args.get("unit_price")
        notes = args.get("notes")

        # 使用 ilike 支持模糊匹配（不区分大小写）
        product = request.env['product.product'].sudo().search([('default_code', 'ilike', sku)], limit=1)
        if not product:
            raise ValueError(f"未找到货号 {sku} 的产品")

        # 查找或创建客户
        partner = None
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(int(partner_id))
        elif partner_name:
            partner = request.env['res.partner'].sudo().search([('name', 'ilike', partner_name)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({'name': partner_name})

        if not partner:
            partner = request.env['res.partner'].sudo().search([], limit=1)
        if not partner:
            raise ValueError("未找到可用的客户")

        # 创建订单行
        order_line_vals = {
            'product_id': product.id,
            'product_uom_qty': qty,
        }
        if unit_price:
            order_line_vals['price_unit'] = float(unit_price)

        order_vals = {
            'partner_id': partner.id,
            'order_line': [(0, 0, order_line_vals)],
        }
        if notes:
            order_vals['note'] = notes

        order = request.env['sale.order'].sudo().create(order_vals)
        return {
            "order_id": order.id,
            "order_name": order.name,
            "partner": partner.name,
            "product": product.name,
            "quantity": qty,
            "message": f"销售订单已创建: {order.name}"
        }

    def _fn_create_sales_order_auto(self, args: dict):
        """
        自动创建销售订单：客户不存在则创建，产品不存在则创建，支持多产品
        参数:
        - partner_name: 客户名称（可选，不提供则随机生成）
        - products: 产品列表，每项包含 name, sku, quantity, unit_price（可选）
          示例: [{"name": "产品A", "sku": "SKU001", "quantity": 2}, ...]
        - notes: 订单备注（可选）
        """
        import random

        partner_name = args.get("partner_name")
        products_data = args.get("products")
        notes = args.get("notes")

        # 处理产品数据
        if not products_data:
            # 默认创建2个随机产品
            products_data = [
                {
                    "name": f"自动产品{random.randint(1000, 9999)}",
                    "sku": f"AUTO{random.randint(100, 999)}",
                    "quantity": random.randint(1, 5),
                    "unit_price": round(random.uniform(10, 500), 2)
                },
                {
                    "name": f"自动产品{random.randint(1000, 9999)}",
                    "sku": f"AUTO{random.randint(100, 999)}",
                    "quantity": random.randint(1, 5),
                    "unit_price": round(random.uniform(10, 500), 2)
                }
            ]

        # 处理客户
        if not partner_name:
            partner_name = f"自动客户{random.randint(1000, 9999)}"

        # 查找或创建客户
        partner = request.env['res.partner'].sudo().search([('name', 'ilike', partner_name)], limit=1)
        if not partner:
            partner = request.env['res.partner'].sudo().create({'name': partner_name})

        # 处理产品：查找或创建
        order_lines = []
        product_names = []
        for i, prod in enumerate(products_data):
            prod_name = prod.get("name")
            prod_sku = prod.get("sku")
            prod_qty = float(prod.get("quantity", 1))
            prod_price = prod.get("unit_price")

            # 查找产品
            product = None
            if prod_sku:
                product = request.env['product.product'].sudo().search([('default_code', 'ilike', prod_sku)], limit=1)
            if not product and prod_name:
                product = request.env['product.product'].sudo().search([('name', 'ilike', prod_name)], limit=1)

            # 产品不存在则创建
            if not product:
                product_vals = {
                    'name': prod_name,
                    'type': 'consu',
                    'list_price': prod_price or 100.0,
                    'standard_price': (prod_price or 100.0) * 0.7,
                }
                if prod_sku:
                    product_vals['default_code'] = prod_sku
                product = request.env['product.product'].sudo().create(product_vals)

            order_line_vals = {
                'product_id': product.id,
                'product_uom_qty': prod_qty,
            }
            if prod_price:
                order_line_vals['price_unit'] = float(prod_price)

            order_lines.append((0, 0, order_line_vals))
            product_names.append(f"{product.name} x {prod_qty}")

        # 创建订单
        order_vals = {
            'partner_id': partner.id,
            'order_line': order_lines,
        }
        if notes:
            order_vals['note'] = notes

        order = request.env['sale.order'].sudo().create(order_vals)

        return {
            "order_id": order.id,
            "order_name": order.name,
            "partner": partner.name,
            "products": product_names,
            "amount_total": order.amount_total,
            "message": f"销售订单已创建: {order.name}"
        }

    def _fn_get_order_status(self, args: dict):
        order_id = args.get("order_id")
        order_name = args.get("order_name")

        domain = []
        if order_id:
            domain.append(('id', '=', int(order_id)))
        if order_name:
            domain.append(('name', 'ilike', order_name))

        order = request.env['sale.order'].sudo().search(domain, limit=1)
        if not order:
            raise ValueError("未找到订单")

        return {
            "order_id": order.id,
            "order_name": order.name,
            "partner": order.partner_id.name,
            "date_order": str(order.date_order),
            "state": order.state,
            "amount_total": order.amount_total,
            "order_lines": [
                {
                    "product": line.product_id.name,
                    "quantity": line.product_uom_qty,
                    "price_unit": line.price_unit,
                    "subtotal": line.price_subtotal,
                }
                for line in order.order_line
            ]
        }

    def _fn_cancel_order(self, args: dict):
        order_id = args.get("order_id")
        order_name = args.get("order_name")

        domain = []
        if order_id:
            domain.append(('id', '=', int(order_id)))
        if order_name:
            domain.append(('name', 'ilike', order_name))

        order = request.env['sale.order'].sudo().search(domain, limit=1)
        if not order:
            raise ValueError("未找到订单")

        if order.state in ['done', 'cancel']:
            raise ValueError(f"订单状态为 {order.state}，无法取消")

        order.action_cancel()
        return {
            "order_id": order.id,
            "order_name": order.name,
            "state": order.state,
            "message": f"订单 {order.name} 已取消"
        }

    # ========== 产品相关函数 ==========

    def _fn_get_product_stock(self, args: dict):
        sku = args.get("product_sku")
        # 不使用 sudo()，使用当前用户的公司上下文
        product = request.env['product.product'].sudo().search([('default_code', 'ilike', sku)], limit=1)
        if not product:
            raise ValueError(f"未找到该货号的产品: {sku}")

        # 获取当前用户公司
        current_company = request.env.company
        company_name = current_company.name
        currency = current_company.currency_id.name

        # 获取库存信息（按当前公司）
        template = product.product_tmpl_id

        # 使用 stock.quant 获取公司特定的库存
        quants = request.env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id.usage', '=', 'internal'),
            '|',
            ('company_id', '=', current_company.id),
            ('company_id', '=', False)
        ])
        # 按公司过滤
        qty_available = sum(q.quantity for q in quants if q.company_id.id == current_company.id or not q.company_id)

        # 获取价格（按当前公司）
        price = product.with_context(
            force_company=current_company.id
        ).list_price

        return {
            "sku": sku,
            "product_name": product.name,
            "company": company_name,
            "currency": currency,
            "qty_available": qty_available,
            "virtual_available": template.virtual_available if hasattr(template, 'virtual_available') else 0,
            "incoming_qty": template.incoming_qty if hasattr(template, 'incoming_qty') else 0,
            "outgoing_qty": template.outgoing_qty if hasattr(template, 'outgoing_qty') else 0,
            "price": price,
            "standard_price": product.standard_price,
        }

    def _fn_search_products(self, args: dict):
        keyword = args.get("keyword", "")
        category = args.get("category")
        limit = args.get("limit", 20)

        # 获取当前用户公司
        current_company = request.env.company

        domain = []
        if keyword:
            domain.append('|')
            domain.append(('default_code', 'ilike', keyword))
            domain.append(('name', 'ilike', keyword))
        if category:
            domain.append(('categ_id.name', 'ilike', category))

        # 不使用 sudo()，按当前公司查询
        products = request.env['product.product'].sudo().search(domain, limit=limit)

        def get_qty(p):
            # 使用 stock.quant 获取公司特定库存
            quants = request.env['stock.quant'].sudo().search([
                ('product_id', '=', p.id),
                ('location_id.usage', '=', 'internal'),
                '|',
                ('company_id', '=', current_company.id),
                ('company_id', '=', False)
            ])
            return sum(q.quantity for q in quants if q.company_id.id == current_company.id or not q.company_id)

        return {
            "count": len(products),
            "products": [
                {
                    "id": p.id,
                    "sku": p.default_code,
                    "name": p.name,
                    "qty_available": get_qty(p),
                    "list_price": p.list_price,
                    "category": p.categ_id.name if p.categ_id else "",
                }
                for p in products
            ]
        }

    def _fn_create_product(self, args: dict):
        name = args.get("name")
        sku = args.get("sku") or args.get("default_code")
        list_price = args.get("list_price") or args.get("price") or 0.0
        standard_price = args.get("standard_price") or args.get("cost") or 0.0
        category = args.get("category")
        type_ = args.get("type") or "product"

        # 查找或创建产品分类
        categ_id = None
        if category:
            categ_id = request.env['product.category'].sudo().search(
                [('name', 'ilike', category)], limit=1
            )
            if not categ_id:
                categ_id = request.env['product.category'].sudo().create({'name': category})

        # 创建产品
        product_vals = {
            'name': name,
            'type': type_,
            'list_price': float(list_price),
            'standard_price': float(standard_price),
        }
        if sku:
            product_vals['default_code'] = sku
        if categ_id:
            product_vals['categ_id'] = categ_id.id

        product = request.env['product.product'].sudo().create(product_vals)

        return {
            "product_id": product.id,
            "sku": product.default_code,
            "name": product.name,
            "list_price": product.list_price,
            "message": f"产品已创建: {product.name}"
        }

    def _fn_get_product_pricelist(self, args: dict):
        product_sku = args.get("product_sku")
        partner_id = args.get("partner_id")
        quantity = float(args.get("quantity", 1))

        # 获取当前用户公司
        current_company = request.env.company

        product = request.env['product.product'].sudo().search([('default_code', 'ilike', product_sku)], limit=1)
        if not product:
            raise ValueError(f"未找到货号为 {product_sku} 的产品")

        partner = None
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(int(partner_id))

        price = product.with_context(
            force_company=current_company.id,
            partner=partner.id if partner else None,
            quantity=quantity
        ).list_price

        return {
            "product_sku": product_sku,
            "product_name": product.name,
            "unit_price": price,
            "quantity": quantity,
            "total_price": price * quantity,
        }

    # ========== 客户相关函数 ==========

    def _fn_get_customer_info(self, args: dict):
        partner_id = args.get("partner_id")
        partner_name = args.get("partner_name")
        phone = args.get("phone")
        email = args.get("email")

        domain = []
        if partner_id:
            domain.append(('id', '=', int(partner_id)))
        if partner_name:
            domain.append(('name', 'ilike', partner_name))
        if phone:
            domain.append(('phone', 'ilike', phone))
        if email:
            domain.append(('email', 'ilike', email))

        if not domain:
            raise ValueError("请提供客户ID、名称、电话或邮箱")

        partner = request.env['res.partner'].sudo().search(domain, limit=1)
        if not partner:
            raise ValueError("未找到客户")

        orders = request.env['sale.order'].sudo().search(
            [('partner_id', '=', partner.id)], limit=10, order='date_order desc'
        )

        return {
            "partner_id": partner.id,
            "name": partner.name,
            "email": partner.email,
            "phone": partner.phone,
            "street": partner.street or "",
            "city": partner.city or "",
            "country": partner.country_id.name if partner.country_id else "",
            "total_orders": len(orders),
            "recent_orders": [
                {
                    "order_id": o.id,
                    "order_name": o.name,
                    "date": str(o.date_order),
                    "amount": o.amount_total,
                    "state": o.state,
                }
                for o in orders
            ]
        }

    def _fn_create_customer(self, args: dict):
        name = args.get("name")
        email = args.get("email")
        phone = args.get("phone")
        street = args.get("street")
        city = args.get("city")
        country = args.get("country")

        if not name:
            raise ValueError("请提供客户名称")

        # 查找国家
        country_id = None
        if country:
            country_id = request.env['res.country'].sudo().search(
                [('name', 'ilike', country)], limit=1
            ).id

        partner_vals = {
            'name': name,
            'email': email,
            'phone': phone,
            'street': street,
            'city': city,
        }
        if country_id:
            partner_vals['country_id'] = country_id

        partner = request.env['res.partner'].sudo().create(partner_vals)

        return {
            "partner_id": partner.id,
            "name": partner.name,
            "message": f"客户已创建: {partner.name}"
        }

    # ========== 交货相关函数 ==========

    def _fn_get_delivery_status(self, args: dict):
        order_id = args.get("order_id")
        order_name = args.get("order_name")

        domain = []
        if order_id:
            domain.append(('id', '=', int(order_id)))
        if order_name:
            domain.append(('name', 'ilike', order_name))

        order = request.env['sale.order'].sudo().search(domain, limit=1)
        if not order:
            raise ValueError("未找到订单")

        pickings = request.env['stock.picking'].sudo().search(
            [('sale_id', '=', order.id)]
        )

        return {
            "order_id": order.id,
            "order_name": order.name,
            "delivery_count": len(pickings),
            "deliveries": [
                {
                    "picking_id": p.id,
                    "name": p.name,
                    "state": p.state,
                    "scheduled_date": str(p.scheduled_date) if p.scheduled_date else "",
                }
                for p in pickings
            ]
        }
