# Dify Chatflow 配置指南

本文档详细说明如何在 Dify 中创建 Chatflow 以支持 AI 商品搜索功能。

---

## 一、Dify 应用创建步骤

### 1.1 创建 Chatflow 应用

1. 登录 Dify，点击「创建应用」
2. 选择应用类型：**Chatflow**
3. 填写应用信息：
   - 应用名称：`AI商品搜索`
   - 应用描述：`Odoo电商AI智能商品搜索助手`
4. 点击「创建」

### 1.2 获取 API Key 和 App ID

创建完成后，在应用页面获取：
- **API Key**：用于 Odoo 认证
- **App ID**：标识应用身份

---

## 二、Chatflow 节点配置

### 2.1 整体架构

```
[Start] → [LLM: 意图解析] → [HTTP Request: 调用Odoo搜索] → [LLM: 生成总结] → [Answer]
                                        ↓
                                  [无结果分支]
                                        ↓
                              [LLM: 生成建议] → [Answer]
```

### 2.2 Start 节点配置

**用途**：接收来自 Odoo 的用户查询

点击 Start 节点，配置输入变量：

| 变量名 | 类型 | 说明 | 来源 |
|--------|------|------|------|
| `query` | String | 用户自然语言查询 | Odoo 传入 |
| `session_key` | String | 会话标识 | Odoo 传入 |
| `conversation_id` | String | Dify 会话ID | Dify 自动生成 |
| `lang` | String | 语言代码 | Odoo 传入，固定值 `zh_CN` |

**Response Mode**：选择 `Blocking`（阻塞模式，等待完整执行后返回）

---

### 2.3 LLM 节点：意图解析

**用途**：将用户自然语言解析为结构化搜索条件

**模型选择**（按推荐优先级）：
1. GPT-4 Turbo（效果最好，速度较慢）
2. GPT-3.5 Turbo（效果不错，速度快）
3. Claude 3 Sonnet（平衡之选）

#### System Prompt：

```
你是一个专业的电商商品搜索意图解析专家。你的任务是将用户的自然语言查询解析为结构化的搜索参数。

【输出格式】
你必须且只能输出一个有效的 JSON 对象，不要包含任何其他文字或解释。

【JSON 结构】
{
  "category": string or null,      // 商品品类（如："男鞋"、"手机"、"连衣裙"）
  "budget_min": number or null,    // 最低价格（人民币元）
  "budget_max": number or null,    // 最高价格（人民币元）
  "brand_include": array,          // 用户想要的品牌列表（如：["Nike", "Adidas"]）
  "brand_exclude": array,          // 用户明确排除的品牌
  "color_include": array,          // 用户想要的颜色
  "color_exclude": array,          // 用户明确排除的颜色
  "must_have": array,              // 用户要求的必须特征（如：["防滑"、"防水"）
  "must_not_have": array,          // 用户明确不想要的特征
  "use_case": array,               // 使用场景（如：["通勤"、"运动"、"正式场合"）
  "season": string or null,         // 季节偏好："spring"、"summer"、"autumn"、"winter"
  "sort_preference": string or null,// 排序偏好："price_asc"、"price_desc"、"relevance"、"sales"
  "language": string,               // 检测到的语言："zh" 或 "en"
  "need_clarification": boolean,    // 是否需要追问
  "clarification_question": string or null,  // 需要追问的问题
  "keywords": array                // 用于文本搜索的所有关键词
}

【规则】
1. 只输出 JSON，不要 markdown 包裹
2. 未知或未指定的字段使用 null
3. 无值的数组使用 []
4. 价格单位是人民币元（CNY）
5. 关键词应包含所有未被结构化字段捕获的重要词汇
6. 如果用户表达模糊，设置 need_clarification=true
7. 绝对不要捏造用户未提及的产品属性、价格或特征
8. 同时支持中文和英文查询
9. 用户提到"通勤"时，自动添加到 use_case
10. 根据温度或语境线索推断季节

【示例】

输入："帮我找300元以内适合通勤的黑色男鞋，不要白色的"
输出：{
  "category": "男鞋",
  "budget_min": null,
  "budget_max": 300,
  "brand_include": [],
  "brand_exclude": [],
  "color_include": ["黑色"],
  "color_exclude": ["白色"],
  "must_have": ["通勤"],
  "must_not_have": [],
  "use_case": ["通勤"],
  "season": null,
  "sort_preference": null,
  "language": "zh",
  "need_clarification": false,
  "clarification_question": null,
  "keywords": ["男鞋", "通勤", "黑色"]
}
```

#### User Prompt：

```
分析以下用户查询，提取搜索意图：

用户查询：{{query}}

只输出 JSON：
```

---

### 2.4 HTTP Request 节点：调用 Odoo 搜索

**用途**：调用 Odoo 内部搜索接口获取真实商品数据

#### 节点配置：

| 配置项 | 值 |
|--------|-----|
| Method | `POST` |
| URL | `{你的Odoo域名}/ai_search/internal/search` |

#### Headers：

```
Content-Type: application/json
```

#### Body：

```json
{
  "token": "{internal_search_token}",
  "query": "{{query}}",
  "session_key": "{{session_key}}",
  "parsed_intent": {{ parsed_intent }},
  "top_k": 8,
  "lang": "{{lang}}"
}
```

#### 输出变量映射：

| Dify 变量名 | 来源 |
|-------------|------|
| `search_success` | 响应中的 `success` 字段 |
| `search_products` | 响应中的 `products` 数组 |
| `search_count` | 响应中的 `count` 或 `products.length` |
| `search_parsed_intent` | 响应中返回的解析意图 |
| `search_applied_filters` | 响应中的 `applied_filters` 对象 |

---

### 2.5 条件分支节点：判断是否有结果

**用途**：根据搜索结果数量决定后续流程

#### 条件配置：

```javascript
{{ search_count }} > 0
```

#### 两个分支：
1. **Yes（True）**：转到「LLM: 生成推荐总结」
2. **No（False）**：转到「LLM: 无结果建议」

---

### 2.6 LLM 节点：生成推荐总结（有结果时）

**用途**：基于搜索结果生成 AI 推荐理由和总结

#### System Prompt：

```
你是一个专业的电商商品推荐助手。你的任务是根据真实的商品数据生成简洁、有用的产品推荐总结。

【输出格式】
输出一个 JSON 对象：

{
  "summary": string,      // 2-3 句话的推荐总结
  "highlight": string,     // 本次搜索的核心亮点（1句话）
  "value_tip": string      // 性价比提示（1句话）
}

【规则】
1. 只输出 JSON，不要任何其他文字
2. summary 应该是 2-3 句话，专业但友好的语气
3. 绝对不要使用真实数据中没有的信息
4. 突出性价比 - 中国消费者非常看重这个
5. 要具体说明产品之间的差异，不要泛泛而谈
6. 语言必须与用户查询语言一致（中文或英文）
7. 不要使用极限词汇（如"最便宜"、"绝对首选"）
8. 如果数据不足以生成某字段，使用 null

【示例】

输入商品数据：
- 商品A：Nike运动鞋，299元，黑色，防滑耐磨
- 商品B：Adidas运动鞋，359元，蓝色，透气轻便
- 商品C：安踏运动鞋，199元，白色，适合学生

输出：
{
  "summary": "为你找到3款适合通勤的运动鞋。Nike这款299元性价比突出，黑色设计稳重百搭；Adidas更贵但透气性更好；安踏作为国产品牌，199元的价格对学生很友好。",
  "highlight": "Nike 299元款兼具性价比和通勤实用性",
  "value_tip": "安踏199元起，适合预算有限的学生群体"
}
```

#### User Prompt：

```
根据以下商品搜索结果，生成推荐总结：

用户原始查询：{{query}}

解析的搜索意图：
{{ parsed_intent }}

商品数据：
{{ search_products }}

只输出 JSON：
```

---

### 2.7 LLM 节点：生成无结果建议

**用途**：当没有商品匹配时，提供智能建议

#### System Prompt：

```
你是一个电商搜索助手。当用户的搜索没有匹配商品时，你需要提供有帮助的建议。

【输出格式】
输出一个 JSON 对象：

{
  "message": string,      // 道歉和理解用户需求的表述
  "suggestions": [         // 3-5 个具体建议
    {
      "type": string,      // 建议类型
      "suggestion": string, // 具体的建议文本
      "action": string     // 建议用户采取的行动
    }
  ]
}

【建议类型】
- "relax_constraint"：放宽某个搜索条件
- "change_keyword"：换用不同的关键词
- "browse_category"：浏览相关品类
- "general"：一般性建议

【规则】
1. 只输出 JSON，不要任何其他文字
2. 语气要同理心，理解用户需求
3. 提供 3-5 个具体、可操作的建议
4. 按影响程度从大到小排序建议
5. 绝对不要捏造商品是否存在

【示例】

输入：用户搜索"5000元以内的苹果手机"

输出：
{
  "message": "抱歉，目前没有5000元以内的苹果手机，苹果产品定位高端，价格通常在5000元以上。",
  "suggestions": [
    {
      "type": "relax_constraint",
      "suggestion": "可以考虑略微提高预算到5500元左右，能买到iPhone 13或iPhone SE",
      "action": "重新搜索"
    },
    {
      "type": "change_keyword",
      "suggestion": "如果喜欢苹果系统但预算有限，可以考虑二手或官翻机",
      "action": "浏览二手手机"
    },
    {
      "type": "browse_category",
      "suggestion": "小米、华为等国产品牌在5000元内有很好的选择，性价比很高",
      "action": "浏览安卓手机"
    }
  ]
}
```

#### User Prompt：

```
用户的搜索查询没有返回任何结果。请生成帮助性建议：

用户原始查询：{{query}}

解析的搜索意图：
{{ parsed_intent }}

只输出 JSON：
```

---

### 2.8 Answer 节点：返回结果

**用途**：将最终结果返回给 Odoo

#### 输出内容：

```json
{
  "success": true,
  "query": "{{query}}",
  "conversation_id": "{{conversation_id}}",
  "parsed_intent": {{ parsed_intent }},
  "products": {{ search_products }},
  "count": {{ search_count }},
  "summary": {{ summary }},
  "has_results": {{ search_count }} > 0,
  "suggestions": {{ suggestions }}
}
```

**注意**：确保开启「JSON 输出模式」

---

## 三、Odoo 端配置

### 3.1 配置参数对照表

| Odoo 配置项 | Dify 对应值 |
|-------------|-------------|
| `dify_api_base_url` | `https://api.dify.ai/v1`（或你的自部署地址） |
| `dify_api_key` | Dify 应用页面的 API Key |
| `dify_app_id` | Dify 应用页面的 App ID |
| `internal_search_token` | HTTP Request 节点中的 token 值（需一致） |

### 3.2 配置步骤

1. 进入 Odoo：**设置 → AI 智能搜索 → Dify 设置**
2. 填写以下必填项：
   - ✅ 启用 AI 搜索
   - ✅ Dify API 地址
   - ✅ Dify API Key
   - ✅ Dify 应用 ID
   - ✅ 内部搜索令牌（与 Dify 中保持一致）
3. 点击「保存」

### 3.3 测试验证

保存配置后，在 Odoo 前端测试：
1. 进入 **AI 智能搜索** 页面
2. 输入测试查询，如："300元以内的男鞋"
3. 查看是否返回商品结果

---

## 四、常见问题排查

### Q1: 搜索返回"AI服务暂时不可用"

可能原因：
- Dify API Key 配置错误
- Dify 应用未发布
- 网络连接问题

排查步骤：
1. 确认 Dify 应用状态为「已发布」
2. 在 Dify 中测试 API 是否正常
3. 检查 Odoo 配置的 API 地址和 Key

### Q2: 意图解析不准确

解决方案：
1. 在 Dify 中调整 LLM 节点的系统提示词
2. 尝试使用更强的模型（如 GPT-4）
3. 添加更多示例到提示词中

### Q3: 商品数据不完整

确认 Odoo 商品数据包含：
- 商品名称（name）
- 商品描述（description_sale）
- 商品价格（list_price）
- 商品图片（image_128）

### Q4: 搜索响应慢

优化建议：
1. 降低 `search_top_k` 值
2. 减少 Dify LLM 调用次数
3. 开启搜索缓存
4. 检查 Odoo 数据库查询性能

---

## 五、进阶配置

### 5.1 多轮对话配置

在 Start 节点中，`conversation_id` 用于维护多轮对话：

1. 首次调用：不传 `conversation_id`，Dify 返回新的
2. 后续调用：传入上次返回的 `conversation_id`
3. Dify 自动维护对话历史上下文

### 5.2 Streaming 模式（高级）

如需实时流式响应：

1. 在 Dify Start 节点选择 `Streaming` 模式
2. Odoo 端需要使用 WebSocket 或 SSE 接收
3. 当前模块默认使用 Blocking 模式

### 5.3 自定义意图字段

如需扩展解析的意图结构：

1. 修改 Dify LLM 的 JSON Schema
2. 修改 Odoo 端 `parsed_intent` 的处理逻辑
3. 更新 `ranking_service.py` 中的排序逻辑

---

## 六、完整配置检查清单

| 序号 | 检查项 | 状态 |
|------|--------|------|
| 1 | Dify 应用已创建并发布 | ⬜ |
| 2 | Dify API Key 已获取 | ⬜ |
| 3 | Chatflow 节点已配置 | ⬜ |
| 4 | HTTP Request 节点 URL 正确 | ⬜ |
| 5 | internal_search_token 两端一致 | ⬜ |
| 6 | Odoo 配置页面填写正确 | ⬜ |
| 7 | AI 搜索功能已启用 | ⬜ |
| 8 | 前端测试搜索功能正常 | ⬜ |
