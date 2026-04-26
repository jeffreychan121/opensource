# Odoo AI Search API 接口契约

本文档定义了 AI Dify Search 模块的 API 接口规范。

## 概览

| 接口 | 路径 | 用途 | 认证 |
|------|------|------|------|
| 公共查询 | POST /ai_search/query | 浏览器调用 | 无需认证（网站用户） |
| 内部搜索 | POST /ai_search/internal/search | Dify 调用 | Token 认证 |
| 关闭会话 | POST /ai_search/session/close | 关闭会话 | 无需认证 |
| 会话上下文 | POST /ai_search/session/context | 获取上下文 | 无需认证 |

---

## 1. 公共查询接口

### POST /ai_search/query

浏览器调用的主接口，用于发起 AI 商品搜索。

**认证方式**：无（public auth）

**CORS**：支持跨域

**请求头**：
```
Content-Type: application/json
```

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户自然语言查询，最大 500 字符 |
| session_key | string | 否 | 会话标识，不传则创建新会话 |
| lang | string | 否 | 语言代码，默认 "zh_CN" |

**请求示例**：

```json
{
    "query": "帮我找300元以内适合通勤的男鞋",
    "session_key": "abc123xyz",
    "lang": "zh_CN"
}
```

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 请求是否成功 |
| query | string | 原始查询 |
| session_key | string | 会话标识 |
| parsed_intent | object | Dify 解析的意图 |
| applied_filters | object | 实际应用的过滤条件 |
| products | array | 商品列表 |
| summary | string | AI 推荐总结 |
| followup_enabled | boolean | 是否支持追问 |
| fallback_used | boolean | 是否使用了降级搜索 |
| conversation_id | string | Dify 会话 ID |
| total_latency_ms | number | 总延迟（毫秒） |
| debug_info | object | 调试信息（仅调试模式） |
| error | string | 错误信息（失败时） |
| code | string | 错误码（失败时） |

**响应示例（成功）**：

```json
{
    "success": true,
    "query": "帮我找300元以内适合通勤的男鞋",
    "session_key": "abc123xyz",
    "parsed_intent": {
        "category": "男鞋",
        "budget_min": null,
        "budget_max": 300,
        "brand_include": [],
        "brand_exclude": [],
        "color_include": [],
        "color_exclude": ["白色"],
        "must_have": ["通勤"],
        "must_not_have": [],
        "use_case": ["commute"],
        "season": null,
        "sort_preference": null,
        "language": "zh",
        "need_clarification": false,
        "clarification_question": null,
        "keywords": ["男鞋", "通勤", "300元以内"]
    },
    "applied_filters": {
        "budget_max": 300,
        "color_exclude": ["白色"]
    },
    "products": [
        {
            "id": 10,
            "name": "轻量通勤运动鞋",
            "default_code": "SPT-001",
            "price": 269.0,
            "currency": "CNY",
            "url": "/shop/product/10",
            "image_url": "/web/image/product.template/10/image_512",
            "category_names": ["男鞋", "运动鞋"],
            "attributes": ["黑色", "轻量", "透气"],
            "brand": "XYZ",
            "short_description": "适合日常通勤的轻量鞋款"
        }
    ],
    "summary": "为您找到了3款300元以内适合通勤的男鞋，综合考虑性价比和透气性。",
    "followup_enabled": true,
    "fallback_used": false,
    "conversation_id": "conv_abc123",
    "total_latency_ms": 1250.5
}
```

**响应示例（失败）**：

```json
{
    "success": false,
    "error": "AI Search service temporarily unavailable",
    "code": "SERVICE_UNAVAILABLE",
    "fallback_available": true
}
```

**错误码**：

| 错误码 | 说明 |
|--------|------|
| INVALID_INPUT | 输入参数无效 |
| DISABLED | AI 搜索未启用 |
| SERVICE_UNAVAILABLE | 服务不可用 |
| INTERNAL_ERROR | 内部错误 |

---

## 2. 内部搜索接口

### POST /ai_search/internal/search

供 Dify HTTP Request 节点调用的内部接口。

**认证方式**：Token 认证

**请求头**：
```
Content-Type: application/json
```

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| token | string | 是 | 内部搜索 Token |
| query | string | 是 | 用户查询 |
| session_key | string | 否 | 会话标识 |
| parsed_intent | object | 否 | 解析后的意图 |
| top_k | integer | 否 | 返回数量，默认 8 |
| lang | string | 否 | 语言代码 |

**请求示例**：

```json
{
    "token": "my_internal_token_123",
    "query": "帮我找300元以内适合通勤的男鞋",
    "session_key": "abc123xyz",
    "parsed_intent": {
        "category": "男鞋",
        "budget_max": 300,
        "use_case": ["通勤"]
    },
    "top_k": 8,
    "lang": "zh_CN"
}
```

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 请求是否成功 |
| parsed_intent | object | 解析的意图 |
| applied_filters | object | 应用的过滤条件 |
| products | array | 商品列表 |
| count | integer | 商品数量 |

**响应示例**：

```json
{
    "success": true,
    "parsed_intent": {
        "category": "男鞋",
        "budget_max": 300,
        "use_case": ["通勤"]
    },
    "applied_filters": {
        "budget_max": 300,
        "website_published": true,
        "sale_ok": true
    },
    "products": [
        {
            "id": 10,
            "name": "轻量通勤运动鞋",
            "default_code": "SPT-001",
            "price": 269.0,
            "currency": "CNY",
            "url": "/shop/product/10",
            "image_url": "/web/image/product.template/10/image_512",
            "category_names": ["男鞋", "运动鞋"],
            "attributes": ["黑色", "轻量", "透气"],
            "brand": "XYZ",
            "short_description": "适合日常通勤的轻量鞋款"
        }
    ],
    "count": 1
}
```

**HTTP 状态码**：

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 参数错误 |
| 401 | Token 无效 |
| 500 | 服务器错误 |

---

## 3. 关闭会话接口

### POST /ai_search/session/close

关闭指定的搜索会话。

**认证方式**：无

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_key | string | 是 | 要关闭的会话标识 |

**响应示例**：

```json
{
    "success": true,
    "session_key": "abc123xyz"
}
```

---

## 4. 获取会话上下文接口

### POST /ai_search/session/context

获取指定会话的上下文信息。

**认证方式**：无

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_key | string | 是 | 会话标识 |

**响应示例**：

```json
{
    "success": true,
    "context": {
        "session_key": "abc123xyz",
        "conversation_id": "conv_abc123",
        "last_query": "300元以内的男鞋",
        "last_parsed_intent": {
            "budget_max": 300,
            "category": "男鞋"
        },
        "last_applied_filters": {
            "budget_max": 300
        },
        "last_product_ids": [10, 11, 12],
        "query_count": 2
    }
}
```

---

## 5. Dify 与 Odoo 的通信流程

### 流程图

```
Browser                    Odoo                     Dify
   │                        │                        │
   │  POST /ai_search/query │                        │
   │───────────────────────▶│                        │
   │                        │                        │
   │                        │  POST /chat-messages   │
   │                        │───────────────────────▶│
   │                        │                        │
   │                        │    (LLM Intent Parse)  │
   │                        │◀───────────────────────│
   │                        │                        │
   │                        │ POST /ai_search/       │
   │                        │     internal/search    │
   │                        │───────────────────────▶│
   │                        │                        │
   │                        │    (Product Search)    │
   │                        │◀───────────────────────│
   │                        │                        │
   │                        │   (LLM Summary Gen)    │
   │                        │                        │
   │                        │◀───────────────────────│
   │  {results}             │                        │
   │◀───────────────────────│                        │
```

### Dify 调用 Odoo 内部接口示例

**Dify HTTP Request 节点配置**：

```json
{
    "method": "POST",
    "url": "https://your-odoo.com/ai_search/internal/search",
    "headers": {
        "Content-Type": "application/json"
    },
    "body": {
        "token": "{{internal_token}}",
        "query": "{{query}}",
        "session_key": "{{session_key}}",
        "parsed_intent": {{parsed_intent}},
        "top_k": 8,
        "lang": "{{lang}}"
    }
}
```

---

## 6. 数据类型定义

### Product 对象

```typescript
interface Product {
    id: number;                    // 商品 ID
    name: string;                  // 商品名称
    default_code: string;          // 商品编码
    price: number;                 // 价格
    currency: string;              // 货币代码
    url: string;                   // 商品页面 URL
    image_url: string;             // 图片 URL
    category_names: string[];      // 类别名称列表
    attributes: string[];          // 属性值列表
    brand: string | null;          // 品牌
    short_description: string;     // 简短描述
    description: string;           // 详细描述
    description_sale: string;      // 销售描述
    website_published: boolean;    // 是否发布
    sale_ok: boolean;              // 是否可售
}
```

### ParsedIntent 对象

```typescript
interface ParsedIntent {
    category: string | null;           // 商品类别
    budget_min: number | null;         // 最低价格
    budget_max: number | null;         // 最高价格
    brand_include: string[];           // 包含的品牌
    brand_exclude: string[];           // 排除的品牌
    color_include: string[];           // 包含的颜色
    color_exclude: string[];           // 排除的颜色
    must_have: string[];               // 必须有的属性
    must_not_have: string[];           // 不能有的属性
    use_case: string[];                // 使用场景
    season: string | null;             // 季节
    sort_preference: string | null;    // 排序偏好
    language: string;                  // 语言
    need_clarification: boolean;       // 是否需要追问
    clarification_question: string | null; // 追问问题
    keywords: string[];                // 关键词
}
```

---

## 7. 错误处理

### 错误响应格式

```json
{
    "success": false,
    "error": "错误描述信息",
    "code": "ERROR_CODE",
    "details": {}
}
```

### 常见错误

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| INVALID_INPUT | 400 | 请求参数无效 |
| INVALID_TOKEN | 401 | 内部搜索 Token 无效 |
| DISABLED | 400 | AI 搜索功能未启用 |
| SERVICE_UNAVAILABLE | 503 | Dify 服务不可用且未启用 Fallback |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 8. 安全注意事项

1. **Token 保护**：内部搜索 Token 不要暴露给浏览器
2. **输入验证**：Odoo 会对 query 参数进行长度和格式验证
3. **CORS 配置**：公共接口已配置 CORS，仅允许必要域名
4. **敏感信息**：日志会脱敏处理，不会记录完整的 API Key
5. **权限控制**：内部接口需要验证 Token，公共接口无需认证
