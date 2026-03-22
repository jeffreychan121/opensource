# -*- coding: utf-8 -*-
# author: chb
"""
Odoo MCP Function Tools - 定义所有可用的函数工具
"""

def get_function_schema():
    """
    返回 MCP 函数工具的 schema 定义
    AI 模型会根据这些定义来选择调用哪个函数
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_sales_summary",
                "description": "获取指定时间段的销售订单汇总，包括销售总额、订单数量等信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "开始日期，格式为YYYY-MM-DD"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "结束日期，格式为YYYY-MM-DD"
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_sales_order",
                "description": "根据产品货号和数量创建销售订单",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_sku": {"type": "string", "description": "产品货号"},
                        "quantity": {"type": "number", "description": "购买数量"},
                        "partner_id": {"type": "integer", "description": "可选，客户ID"},
                        "partner_name": {"type": "string", "description": "可选，客户名称"},
                        "unit_price": {"type": "number", "description": "可选，自定义单价"},
                        "notes": {"type": "string", "description": "可选，订单备注"}
                    },
                    "required": ["product_sku", "quantity"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_product_stock",
                "description": "查询指定产品的库存和价格信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_sku": {"type": "string", "description": "产品货号"}
                    },
                    "required": ["product_sku"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "搜索产品，支持按货号、名称、类别搜索",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "搜索关键词"},
                        "category": {"type": "string", "description": "可选，产品类别"},
                        "limit": {"type": "integer", "description": "可选，返回数量限制，默认20"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_customer_info",
                "description": "查询客户信息及销售订单历史",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "partner_id": {"type": "integer", "description": "客户ID"},
                        "partner_name": {"type": "string", "description": "客户名称"},
                        "phone": {"type": "string", "description": "客户电话"},
                        "email": {"type": "string", "description": "客户邮箱"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_customer",
                "description": "创建新客户",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "客户名称"},
                        "email": {"type": "string", "description": "客户邮箱"},
                        "phone": {"type": "string", "description": "客户电话"},
                        "street": {"type": "string", "description": "街道地址"},
                        "city": {"type": "string", "description": "城市"},
                        "country": {"type": "string", "description": "国家"}
                    },
                    "required": ["name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "查询销售订单的状态和详细信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "integer", "description": "订单ID"},
                        "order_name": {"type": "string", "description": "订单编号"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_order",
                "description": "取消销售订单",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "integer", "description": "订单ID"},
                        "order_name": {"type": "string", "description": "订单编号"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_product_pricelist",
                "description": "获取产品的价格表价格",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_sku": {"type": "string", "description": "产品货号"},
                        "partner_id": {"type": "integer", "description": "可选，客户ID"},
                        "quantity": {"type": "number", "description": "可选，购买数量"}
                    },
                    "required": ["product_sku"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_delivery_status",
                "description": "查询销售订单的交货状态",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "integer", "description": "订单ID"},
                        "order_name": {"type": "string", "description": "订单编号"}
                    }
                }
            }
        }
    ]
