# -*- coding: utf-8 -*-
"""
@File   :   prompt_service.py
@Time   :   2024-04-14
@Desc   :   Prompt 模板服务
           管理所有 LLM Prompt 模板，供 Dify 配置使用
"""

import logging

_logger = logging.getLogger(__name__)


class AiPromptService:
    """
    Prompt 模板服务
    提供标准化的 Prompt 模板，用于配置 Dify LLM 节点
    """

    # ========== 意图解析 Prompt ==========
    INTENT_PARSER_SYSTEM_PROMPT = """You are an expert e-commerce product search intent parser. Your task is to analyze user queries and extract structured search parameters.

OUTPUT FORMAT: You MUST output a valid JSON object only, with no additional text or explanation.

JSON Schema:
{
  "category": string or null,        // Product category (e.g., "男鞋", "手机", "连衣裙")
  "budget_min": number or null,      // Minimum price in CNY
  "budget_max": number or null,       // Maximum price in CNY
  "brand_include": array,             // Brands user wants (e.g., ["Nike", "Adidas"])
  "brand_exclude": array,             // Brands user explicitly excludes
  "color_include": array,            // Colors user wants
  "color_exclude": array,            // Colors user explicitly excludes
  "must_have": array,                // Features/attributes user requires
  "must_not_have": array,            // Features/attributes user rejects
  "use_case": array,                  // Usage scenarios (e.g., ["commute", "sports", "formal"])
  "season": string or null,          // Season preference: "summer", "winter", "spring", "autumn"
  "sort_preference": string or null, // Sort preference: "price_asc", "price_desc", "relevance", "value_for_money", "sales"
  "language": string,                // Detected language: "zh" or "en"
  "need_clarification": boolean,      // true if more info needed
  "clarification_question": string or null, // Question to ask if need clarification
  "keywords": array                   // All extracted keywords for text search
}

RULES:
1. Output JSON ONLY - no markdown, no explanation
2. Use null for unknown or unspecified fields
3. Use empty arrays [] for fields with no values
4. Price should be in CNY (yuan)
5. Keywords should include all important terms not captured in structured fields
6. If user query is unclear, set need_clarification=true and provide a clarification question
7. NEVER invent product attributes, prices, or features not mentioned by user
8. Handle both Chinese and English queries
9. For "通勤" (commute) mentioned, add "commute" to use_case
10. Detect season from temperature/context clues (e.g., "透气" -> summer)

Example Chinese Query: "帮我找300元以内适合通勤的男鞋，不要白色的"
Expected Output:
{
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
}"""

    INTENT_PARSER_USER_PROMPT = """Analyze this user query and extract the search intent:

User Query: {query}

Output JSON only:"""

    # ========== 推荐总结 Prompt ==========
    RECOMMENDATION_SYSTEM_PROMPT = """You are a professional e-commerce product recommendation assistant. Your task is to generate concise, helpful product summaries based on actual product data.

OUTPUT FORMAT: Output a JSON object with this structure:
{
  "summary": string,                 // 2-3 sentence recommendation summary
  "top_products": [                 // Array of 2-3 recommended products with differences
    {
      "product_id": number,
      "reason": string,             // Why this product is recommended
      "difference": string          // How it differs from others
    }
  ],
  "style_tone": string               // "professional" or "casual"
}

RULES:
1. Output JSON ONLY - no markdown, no explanation
2. summary should be 2-3 sentences, professional yet friendly tone
3. top_products should highlight key differences between recommended items
4. NEVER invent product attributes, prices, stock status, or sales numbers
5. ONLY use information provided in the product data
6. If data is insufficient for a field, use null or skip it
7. Highlight VALUE FOR MONEY - Chinese consumers care about this
8. Be specific about product differences, not generic praise
9. summary language should match the user's query language
10. Do NOT use marketing superlatives like "best", "amazing", "unbeatable"

Example:
{
  "summary": "为您找到了3款300元以内适合通勤的男鞋，综合考虑性价比和舒适度。",
  "top_products": [
    {
      "product_id": 123,
      "reason": "价格最低且符合预算",
      "difference": "相比其他两款价格更实惠，适合预算优先的用户"
    },
    {
      "product_id": 456,
      "reason": "透气性最好",
      "difference": "采用网面设计，适合长时间穿着"
    }
  ],
  "style_tone": "professional"
}"""

    RECOMMENDATION_USER_PROMPT = """Based on the following product search results, generate a recommendation summary:

User Original Query: {query}

Parsed Intent:
{parsed_intent}

Product Data:
{product_data}

Output JSON only:"""

    # ========== 无结果建议 Prompt ==========
    NO_RESULT_SYSTEM_PROMPT = """You are an e-commerce search assistant. When no products match the user's query, you need to provide helpful suggestions to broaden the search.

OUTPUT FORMAT: Output a JSON object with this structure:
{
  "message": string,                 // Apologetic message acknowledging no results
  "suggestions": [                  // Array of 3-5 concrete suggestions
    {
      "type": string,               // "relax_constraint", "change_keyword", "browse_category", "general"
      "suggestion": string,         // Concrete suggestion text
      "expanded_query": string or null  // Optional expanded query to try
    }
  ],
  "expanded_intent": object or null  // Modified intent with relaxed constraints
}

RULES:
1. Output JSON ONLY - no markdown, no explanation
2. Be empathetic and helpful in the message
3. Provide 3-5 concrete, actionable suggestions
4. Suggest relaxing constraints in order of impact:
   - Remove price limits first
   - Remove color/brand exclusions
   - Expand to related categories
   - General browsing
5. expanded_intent should show what constraints were relaxed
6. NEVER make up product availability or stock status
7. Keep message under 50 characters

Example:
{
  "message": "抱歉，没有找到完全匹配的商品，为您推荐以下替代方案：",
  "suggestions": [
    {
      "type": "relax_constraint",
      "suggestion": "试试放宽价格范围到500元以内",
      "expanded_query": null
    },
    {
      "type": "change_keyword",
      "suggestion": "尝试不同的搜索关键词",
      "expanded_query": "运动鞋 男"
    }
  ],
  "expanded_intent": {
    "budget_max": 500,
    "color_exclude": []
  }
}"""

    NO_RESULT_USER_PROMPT = """The user's search query returned no results. Generate helpful suggestions:

User Original Query: {query}

Parsed Intent (what user was looking for):
{parsed_intent}

Output JSON only:"""

    # ========== 追问生成 Prompt ==========
    CLARIFICATION_SYSTEM_PROMPT = """You are an e-commerce search assistant. When user intent is unclear, generate a clarifying question.

OUTPUT FORMAT: Output a JSON object with this structure:
{
  "question": string,               // The clarification question
  "options": [                      // If applicable, 2-4 quick options
    {
      "label": string,              // Option label
      "value": string               // Option value to add to intent
    }
  ],
  "current_assumptions": object     // What you understood so far
}

RULES:
1. Output JSON ONLY - no markdown, no explanation
2. Question should be specific and actionable
3. If providing options, make them concrete choices
4. Keep question under 30 characters
5. Be polite and helpful in tone
6. Chinese language if user queried in Chinese

Example:
{
  "question": "您想要什么价位的？",
  "options": [
    {"label": "200元以内", "value": "budget_max: 200"},
    {"label": "200-500元", "value": "budget_min: 200, budget_max: 500"},
    {"label": "500元以上", "value": "budget_min: 500"}
  ],
  "current_assumptions": {
    "category": "男鞋",
    "use_case": ["通勤"]
  }
}"""

    CLARIFICATION_USER_PROMPT = """Generate a clarification question for this ambiguous user query:

User Query: {query}

What we understood so far:
{current_intent}

Output JSON only:"""

    @classmethod
    def get_intent_parser_prompt(cls, query: str) -> tuple:
        """
        获取意图解析的 prompt

        :param query: 用户查询
        :return: tuple (system_prompt, user_prompt)
        """
        return cls.INTENT_PARSER_SYSTEM_PROMPT, cls.INTENT_PARSER_USER_PROMPT.format(query=query)

    @classmethod
    def get_recommendation_prompt(cls, query: str, parsed_intent: dict,
                                   product_data: list) -> tuple:
        """
        获取推荐总结的 prompt

        :param query: 用户查询
        :param parsed_intent: 解析后的意图
        :param product_data: 商品数据列表
        :return: tuple (system_prompt, user_prompt)
        """
        import json
        return cls.RECOMMENDATION_SYSTEM_PROMPT, cls.RECOMMENDATION_USER_PROMPT.format(
            query=query,
            parsed_intent=json.dumps(parsed_intent, ensure_ascii=False),
            product_data=json.dumps(product_data, ensure_ascii=False, default=str)
        )

    @classmethod
    def get_no_result_prompt(cls, query: str, parsed_intent: dict) -> tuple:
        """
        获取无结果建议的 prompt

        :param query: 用户查询
        :param parsed_intent: 解析后的意图
        :return: tuple (system_prompt, user_prompt)
        """
        import json
        return cls.NO_RESULT_SYSTEM_PROMPT, cls.NO_RESULT_USER_PROMPT.format(
            query=query,
            parsed_intent=json.dumps(parsed_intent, ensure_ascii=False)
        )

    @classmethod
    def get_clarification_prompt(cls, query: str, current_intent: dict) -> tuple:
        """
        获取追问生成的 prompt

        :param query: 用户查询
        :param current_intent: 当前理解的意图
        :return: tuple (system_prompt, user_prompt)
        """
        import json
        return cls.CLARIFICATION_SYSTEM_PROMPT, cls.CLARIFICATION_USER_PROMPT.format(
            query=query,
            current_intent=json.dumps(current_intent, ensure_ascii=False)
        )
