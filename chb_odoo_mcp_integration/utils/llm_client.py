# -*- coding: utf-8 -*-
# author: chb

import json
from openai import OpenAI
from .config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, MODEL_NAME
from .function_tools import get_function_schema
from .function_handler import handle_function_call


class LLMChatClient:
    def __init__(self):
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)
        self.messages = [{"role": "system", "content": "You are a helpful assistant"}]

    def chat(self, user_input: str):
        self.messages.append({"role": "user", "content": user_input})

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=self.messages,
            tools=get_function_schema(),
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                result = handle_function_call(fn_name, fn_args)

                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": json.dumps(result)
                }

                self.messages.append(message.model_dump())
                self.messages.append(tool_response)

                final_response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=self.messages
                )
                final_reply = final_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_reply})
                return final_reply
        else:
            reply = message.content
            self.messages.append({"role": "assistant", "content": reply})
            return reply
