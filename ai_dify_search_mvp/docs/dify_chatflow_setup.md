# Dify Chatflow 配置指南

本文档说明如何在 Dify 中配置 AI 搜索 Chatflow。

## 前提条件

1. 已有 Dify 账号或自部署 Dify 服务
2. 创建 Chatflow 类型的应用

## Chatflow 结构

```
Start → LLM (意图解析) → HTTP Request → LLM (总结生成) → Answer
```

## 节点配置

### 1. Start 节点

设置输入变量：
- `query`: 用户消息
- `session_key`: 会话标识
- `lang`: 语言代码

### 2. LLM 节点（意图解析）

System Prompt:
```
你是一个商品搜索意图解析助手。用户的输入是中文商品查询。

请解析用户的查询，提取以下信息：
- category: 商品类别
- budget_min: 最低预算（如有）
- budget_max: 最高预算（如有）
- keywords: 关键词列表

请以JSON格式输出，例如：
{"category": "手机", "budget_max": 3000, "keywords": ["手机", "5G"]}

如果无法解析出某个字段，请忽略该字段。
```

### 3. HTTP Request 节点

配置调用 Odoo 内部搜索接口：

```
URL: https://your-odoo-domain.com/ai_search_mvp/internal/search
Method: POST
Headers:
  Content-Type: application/json
  X-Internal-Token: {{internal_token}}
Body:
  {
    "query": {{query}},
    "session_key": {{session_key}},
    "parsed_intent": {{parsed_intent}},
    "top_k": 8,
    "lang": {{lang}}
  }
```

### 4. LLM 节点（总结生成）

System Prompt:
```
你是一个商品推荐助手。用户正在搜索商品。

已找到的商品信息：
{{products}}

请根据用户的原始查询和商品列表，生成一段简短的推荐总结（50字以内）。

格式要求：
- 开头使用"为您找到"
- 提及商品数量和主要特征
- 语言简洁亲切

例如："为您找到5款2000-3000元的5G手机，推荐关注续航和拍照性能。"
```

### 5. Answer 节点

直接输出 LLM 总结内容。

## Dify 配置检查清单

- [ ] Start 节点配置了 query, session_key, lang 变量
- [ ] LLM 意图解析节点正确配置了 System Prompt
- [ ] HTTP Request 节点配置了正确的 Odoo URL
- [ ] HTTP Request 节点的 Header 包含 X-Internal-Token
- [ ] LLM 总结生成节点正确配置了输入变量
- [ ] 测试 Chatflow 是否能正常调用

## 常见问题

### Q: HTTP Request 节点调用失败
检查：
1. Odoo 服务是否可访问
2. internal_token 是否正确配置
3. 防火墙是否允许 HTTP 请求

### Q: LLM 解析的 intent 格式不对
检查：
1. System Prompt 是否清晰
2. 是否有 JSON 输出示例
3. LLM 模型是否支持 JSON 输出
