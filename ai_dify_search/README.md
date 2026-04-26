# AI Dify Search - Odoo 17 智能搜索模块

基于 Dify Chatflow 的 AI 商品搜索导购模块，支持自然语言商品搜索、多轮对话上下文记忆、智能推荐总结。

## 功能特性

- **自然语言搜索**：用户输入如"300元以内适合通勤的男鞋"，系统自动解析并搜索
- **多轮对话**：支持追问"不要白色的"、"更便宜一点"等
- **意图解析**：Dify LLM 解析用户查询为结构化 JSON
- **智能总结**：AI 生成推荐理由和商品差异说明
- **自动降级**：Dify 不可用时自动切换到本地搜索
- **会话管理**：支持跨请求的会话上下文
- **日志记录**：完整的搜索日志用于分析

## 系统架构

```
Browser
    │
    ▼
Odoo /ai_search/query (公共接口)
    │
    ├──▶ Dify Chatflow API (AI 编排)
    │         │
    │         ├──▶ LLM: 意图解析
    │         │
    │         ├──▶ HTTP Request: 调用 Odoo 内部搜索
    │         │         │
    │         │         └──▶ Odoo /ai_search/internal/search
    │         │                   │
    │         └──▶ LLM: 生成总结
    │
    └──▶ Fallback (Dify 不可用时)
              │
              └──▶ 本地搜索 + 简单意图解析
```

## 安装步骤

### 1. 安装模块

```bash
# 进入 Odoo 目录
cd /Users/chan/Henson/odoo

# 升级自定义模块
./venv310/bin/python odoo-bin -c debian/odoo.conf -u ai_dify_search --stop-after-init
```

或者在 Odoo Apps 界面搜索 `ai_dify_search` 进行安装。

### 2. 配置模块

1. 进入 **设置 > 网站 > AI Dify 搜索 > 设置**
2. 启用 AI 搜索
3. 配置 Dify API 信息：
   - API Base URL: `https://api.dify.ai/v1`
   - API Key: 您的 Dify API Key
   - App ID: 您的 Dify Chatflow App ID
4. 配置内部接口 Token（用于 Dify 调用 Odoo）
5. 设置其他参数（超时、返回数量等）
6. 保存设置

### 3. 配置 Dify

请参考 `docs/dify_chatflow_setup.md` 创建 Dify Chatflow。

### 4. 在 /shop 页面使用

安装并配置完成后，在 `/shop` 页面顶部会显示 AI 搜索框。

## 配置说明

### 基本配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 启用 AI 搜索 | 是否启用功能 | False |
| Dify API Base URL | Dify API 地址 | https://api.dify.ai/v1 |
| Dify API Key | API 认证密钥 | - |
| Dify App ID | Chatflow 应用 ID | - |
| Dify 超时 | API 调用超时（秒） | 30 |
| 内部接口 Token | Dify 调用 Odoo 的认证 Token | - |
| 默认返回数量 | 搜索返回商品数量 | 8 |
| 会话过期时间 | 搜索会话有效期（小时） | 24 |

### 功能开关

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 启用 Fallback | Dify 失败时使用本地搜索 | True |
| 允许追问 | 是否允许用户追问 | True |
| 启用日志 | 记录搜索日志 | True |
| 调试模式 | 显示详细调试信息 | False |

### 向量搜索（可选）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 启用向量搜索 | 需要 pgvector 扩展 | False |
| 向量搜索限制 | 向量搜索返回数量 | 20 |

## 目录结构

```
ai_dify_search/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── data/
│   └── ir_cron_data.xml
├── models/
│   ├── __init__.py
│   ├── res_config_settings.py
│   ├── ai_search_session.py
│   └── ai_search_log.py
├── services/
│   ├── __init__.py
│   ├── config_service.py
│   ├── dify_service.py
│   ├── search_service.py
│   ├── ranking_service.py
│   ├── session_service.py
│   ├── fallback_service.py
│   └── prompt_service.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── views/
│   ├── res_config_settings_views.xml
│   ├── ai_search_log_views.xml
│   ├── ai_search_menu.xml
│   └── website_templates.xml
├── static/
│   └── src/
│       ├── js/
│       │   └── ai_search.js
│       ├── xml/
│       │   └── ai_search_templates.xml
│       └── scss/
│           └── ai_search.scss
├── tests/
│   ├── __init__.py
│   └── test_ai_dify_search.py
└── docs/
    ├── dify_chatflow_setup.md
    └── api_contract.md
```

## API 接口

### 公共接口

#### POST /ai_search/query
浏览器调用的主接口

```json
// Request
{
    "query": "帮我找300元以内适合通勤的男鞋",
    "session_key": "xxx",
    "lang": "zh_CN"
}

// Response
{
    "success": true,
    "query": "帮我找300元以内适合通勤的男鞋",
    "parsed_intent": {...},
    "applied_filters": {...},
    "products": [...],
    "summary": "...",
    "followup_enabled": true,
    "fallback_used": false,
    "conversation_id": "xxx"
}
```

### 内部接口

#### POST /ai_search/internal/search
Dify HTTP Request 节点调用的接口

```json
// Request
{
    "token": "internal_token",
    "query": "...",
    "parsed_intent": {...},
    "top_k": 8
}

// Response
{
    "success": true,
    "products": [...],
    "count": 5
}
```

详细接口文档请参考 `docs/api_contract.md`

## 升级注意事项

### v0.1 -> v0.2 计划

- 支持更多属性过滤
- 添加向量搜索增强
- 支持多语言
- 添加搜索建议 autocomplete

## 常见问题

### Q: Dify API 调用失败怎么办？

A: 系统会自动降级到本地搜索，确保用户仍能搜索商品。可以在日志中查看具体错误。

### Q: 如何查看搜索日志？

A: 进入 **设置 > 网站 > AI Search > Search Logs**

### Q: 如何关闭 AI 搜索？

A: 在配置页面关闭"启用 AI 搜索"即可。

## License

LGPL-3
