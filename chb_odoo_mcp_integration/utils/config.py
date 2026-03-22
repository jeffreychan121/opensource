# -*- coding: utf-8 -*-
# author: chb

# ============================================
# 模型提供商配置
# ============================================
# 当前使用的提供商: "deepseek" 或 "minimax"
CURRENT_PROVIDER = "minimax"  # 修改这里切换模型

# DeepSeek 配置
DEEPSEEK_API_KEY = "sk-7bfb1041b45f40ca8faec3a6a62e2e88"
DEEPSEEK_API_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL_NAME = "deepseek-chat"

# MiniMax 配置
MINIMAX_API_KEY = "sk-cp-4U5kB2EsperK6298rijeKHfO865C1MPoRkRpn0ow7_JWLWw_9yQtcEydYFGqz6GRGo17Ob-hLpg5HlgUzjoua-rIavqH4l-W_DPtVQTOkst3T63BjU8rnh8"
MINIMAX_API_URL = "https://api.minimaxi.com/v1"
MINIMAX_MODEL_NAME = "MiniMax-M2.5"

# 兼容旧版本
MODEL_NAME = DEEPSEEK_MODEL_NAME

# Odoo 配置
BASE_URL = "http://localhost:8070"
API_KEY = "guyaxin"