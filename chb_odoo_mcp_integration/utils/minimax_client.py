# -*- coding: utf-8 -*-
# author: chb
import json
import logging
from openai import OpenAI
from .config import (
    DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL_NAME,
    MINIMAX_API_KEY, MINIMAX_API_URL, MINIMAX_MODEL_NAME,
    CURRENT_PROVIDER
)
from .function_tools import get_function_schema

_logger = logging.getLogger(__name__)


# 模型提供商枚举
class LLMProvider:
    DEEPSEEK = "deepseek"
    MINIMAX = "minimax"


class LLMChatClient:
    def __init__(self, provider=None):
        """
        初始化 LLM 客户端
        provider: LLMProvider.DEEPSEEK 或 LLMProvider.MINIMAX，默认为配置中的 CURRENT_PROVIDER
        """
        self.provider = provider or CURRENT_PROVIDER
        self._init_client()
        self.messages = [{"role": "system", "content": "You are a helpful assistant"}]

    def _init_client(self):
        """根据 provider 初始化对应的客户端"""
        if self.provider == LLMProvider.MINIMAX:
            self.client = OpenAI(
                api_key=MINIMAX_API_KEY,
                base_url=MINIMAX_API_URL
            )
            self.model = MINIMAX_MODEL_NAME
            _logger.info(f"MCP 初始化: 使用 MiniMax, 模型: {self.model}")
        else:
            # 默认使用 DeepSeek
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_URL
            )
            self.model = DEEPSEEK_MODEL_NAME
            _logger.info(f"MCP 初始化: 使用 DeepSeek, 模型: {self.model}")

    def switch_provider(self, provider):
        """
        切换模型提供商
        provider: LLMProvider.DEEPSEEK 或 LLMProvider.MINIMAX
        """
        self.provider = provider
        self._init_client()
        # 切换时重置对话历史
        self.messages = [{"role": "system", "content": "You are a helpful assistant"}]

    def chat(self, user_input: str):
        _logger.info(f"==================== LLM 调用开始 ====================")
        _logger.info(f"用户输入: {user_input}")

        # 每次只发送当前用户输入，不累积历史
        messages = [{"role": "system", "content": "You are a helpful assistant. 只回答用户当前的问题，不要复述对话历史。"}, {"role": "user", "content": user_input}]

        _logger.info(f"发送消息给 AI: {json.dumps(messages, ensure_ascii=False, indent=2)}")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=get_function_schema(),
            tool_choice="auto"
        )

        message = response.choices[0].message
        _logger.info(f"AI 响应: {json.dumps(message.model_dump(), ensure_ascii=False, indent=2) if hasattr(message, 'model_dump') else str(message)}")

        if message.tool_calls:
            _logger.info(f"AI 触发工具调用，共 {len(message.tool_calls)} 个工具调用")
            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                _logger.info(f"工具调用详情 - 函数名: {fn_name}, 参数: {json.dumps(fn_args, ensure_ascii=False)}")

                # 延迟导入，避免循环依赖
                from .function_handler import handle_function_call
                result = handle_function_call(fn_name, fn_args)

                _logger.info(f"工具返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": json.dumps(result)
                }

                messages.append(message.model_dump())
                messages.append(tool_response)

                _logger.info(f"进行第二次 LLM 调用，获取最终回复")

                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                final_reply = final_response.choices[0].message.content
                _logger.info(f"最终回复: {final_reply}")

                _logger.info(f"==================== LLM 调用结束 ====================\n")
                return final_reply
        else:
            reply = message.content
            _logger.info(f"AI 直接回复（无工具调用）: {reply}")
            _logger.info(f"==================== LLM 调用结束 ====================\n")
            return reply

    def reset_conversation(self):
        """重置对话历史"""
        _logger.info("重置对话历史")
        self.messages = [{"role": "system", "content": "You are a helpful assistant"}]
