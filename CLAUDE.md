# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a monorepo containing multiple independent projects under `/Users/chan/Henson/odoo/opensource/`:

- `chb_odoo_mcp_integration/` - Odoo 17 MCP integration module
- `stock-monitor/` - Stock monitoring system (Node.js fullstack)
- `dashboard/` - Dashboard project
- `docs/` - Documentation

## Common Commands

### Odoo MCP Integration Module

```bash
# Start Odoo
/Users/chan/Henson/odoo/venv310/bin/python odoo-bin -c /Users/chan/Henson/odoo/debian/odoo.conf -d odoo17

# Stop Odoo
lsof -i :8069 | grep LISTEN | awk '{print $2}' | head -1 | xargs kill

# Upgrade module
/Users/chan/Henson/odoo/venv310/bin/python odoo-bin -c odoo.conf -u chb_odoo_mcp_integration --stop-after-init

# Test MCP endpoint
curl -X POST http://localhost:8069/mcp/call -H "Content-Type: application/json" -d '{"function":"get_product_stock","args":{"product_sku":"1273"}}'
```

### Stock Monitor

```bash
cd stock-monitor/server && npm install && npm run dev
cd stock-monitor/client && npm install && npm run dev
```

## Odoo MCP Module Architecture

The `chb_odoo_mcp_integration` module exposes Odoo ERP functions as MCP tools:

- **Controller**: `controllers/mcp_gateway.py` handles `/mcp/call` endpoint
- **Available functions**: get_product_stock, create_sales_order, create_sales_order_auto, search_products, get_customer_info, create_customer, get_order_status, cancel_order, get_delivery_status
- **Entry point**: `controllers/__init__.py` must import the controller module

## Bug Investigation Workflow

When troubleshooting Odoo issues:
1. Check logs: `tail -100 /Users/chan/Henson/odoo/log/odoo17.log`
2. Test the specific endpoint with curl
3. Identify root cause by examining module imports and routing
4. Fix and restart Odoo
5. Verify the fix with another curl call
6. Commit and push to remote

## Commit Format

```
[ADD]模块名:新增功能
[IMP]模块名:修改内容
[FIX]模块名:解决的问题
```

Push to remote after commit:
```bash
git push
```