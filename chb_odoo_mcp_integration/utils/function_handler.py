# -*- coding: utf-8 -*-
# author: chb
"""
Odoo MCP Function Handler - 处理函数调用
通过 HTTP 调用 Odoo MCP 接口
"""
import logging
import json

_logger = logging.getLogger(__name__)

# 从 config 导入配置
try:
    from .config import BASE_URL
except ImportError:
    BASE_URL = "http://localhost:8069"


def handle_function_call(name: str, arguments: dict):
    """
    处理函数调用
    通过 HTTP 调用 Odoo MCP 接口
    """
    import requests

    url = f"{BASE_URL}/mcp/call"

    payload = {
        "function": name,
        "args": arguments
    }

    _logger.info(f"==================== MCP 调用开始 ====================")
    _logger.info(f"函数名称: {name}")
    _logger.info(f"传递参数: {json.dumps(arguments, ensure_ascii=False, indent=2)}")

    try:
        response = requests.post(url, json=payload, timeout=30)
        _logger.info(f"HTTP 响应状态码: {response.status_code}")

        response.raise_for_status()
        result = response.json()

        # Odoo 返回的是 JSON-RPC 格式，实际数据在 result 字段中
        rpc_result = result.get("result", result)

        _logger.info(f"原始响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

        if rpc_result.get("ok"):
            data = rpc_result.get("data", {})
            _logger.info(f"函数执行成功，返回数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            _logger.info(f"==================== MCP 调用结束 ====================\n")
            return data
        else:
            error = rpc_result.get("error", {})
            error_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            _logger.error(f"函数执行失败: {error_msg}")
            _logger.info(f"==================== MCP 调用结束 ====================\n")
            return {"error": error_msg}

    except requests.RequestException as e:
        _logger.error(f"HTTP 请求失败: {str(e)}")
        _logger.info(f"==================== MCP 调用结束 ====================\n")
        return {"error": f"请求失败: {str(e)}"}
    except json.JSONDecodeError as e:
        _logger.error(f"JSON 解析失败: {str(e)}")
        _logger.info(f"==================== MCP 调用结束 ====================\n")
        return {"error": f"响应解析失败: {str(e)}"}
    except Exception as e:
        _logger.exception(f"未知错误: {str(e)}")
        _logger.info(f"==================== MCP 调用结束 ====================\n")
        return {"error": f"未知错误: {str(e)}"}
