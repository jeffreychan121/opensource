# AI Dify Search MVP API 接口契约

## 概览

| 接口 | 路径 | 用途 | 认证 |
|------|------|------|------|
| 公共查询 | POST /ai_search_mvp/query | 浏览器调用 | 无需认证 |
| 内部搜索 | POST /ai_search_mvp/internal/search | Dify 调用 | Header Token |

---

## 1. 公共查询接口

### POST /ai_search_mvp/query

**认证方式**: 无（public auth）

**CORS**: 支持跨域

**请求头**:
```
Content-Type: application/json
```

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户自然语言查询，最大 500 字符 |
| session_key | string | 否 | 会话标识，不传则创建新会话 |
| lang | string | 否 | 语言代码，默认 "zh_CN" |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 请求是否成功 |
| query | string | 原始查询 |
| session_key | string | 会话标识 |
| parsed_intent | object | Dify 解析的意图 |
| products | array | 商品列表 |
| summary | string | AI 推荐总结 |
| fallback_used | boolean | 是否使用了降级搜索 |
| total_latency_ms | number | 总延迟（毫秒） |
| error | string | 错误信息（失败时） |
| code | string | 错误码（失败时） |

**响应示例（成功）**:

```json
{
    "success": true,
    "query": "300元以内的男鞋",
    "session_key": "abc123",
    "parsed_intent": {
        "category": "男鞋",
        "budget_max": 300,
        "keywords": ["男鞋"]
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
            "short_description": "适合日常通勤的轻量鞋款"
        }
    ],
    "summary": "为您找到3款300元以内的男鞋，综合考虑性价比。",
    "fallback_used": false,
    "total_latency_ms": 1250.5
}
```

**错误码**:

| 错误码 | 说明 |
|--------|------|
| INVALID_INPUT | 输入参数无效 |
| DISABLED | AI 搜索未启用 |
| SERVICE_UNAVAILABLE | 服务不可用 |

---

## 2. 内部搜索接口

### POST /ai_search_mvp/internal/search

**用途**: 供 Dify HTTP Request 节点调用

**认证**: Header `X-Internal-Token: <token>`

**请求头**:
```
Content-Type: application/json
X-Internal-Token: your_internal_token
```

**请求体**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户查询 |
| session_key | string | 否 | 会话标识 |
| parsed_intent | object | 否 | 解析后的意图 |
| top_k | integer | 否 | 返回数量，默认 8 |
| lang | string | 否 | 语言代码 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 请求是否成功 |
| parsed_intent | object | 解析的意图 |
| products | array | 商品列表 |
| count | integer | 商品数量 |
| latency_ms | number | 延迟（毫秒） |

**HTTP 状态码**:

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 参数错误 |
| 401 | Token 无效 |
| 500 | 服务器错误 |
