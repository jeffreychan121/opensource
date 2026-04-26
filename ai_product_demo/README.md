# AI Product Demo - 演示商品数据模块

## 模块概述

本模块为 AI 商品搜索和商品对比演示提供测试用的商品数据。

## 模块结构

```
ai_product_demo/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── product_demo.py           # 演示模型扩展
├── services/
│   ├── __init__.py
│   └── product_understanding_service.py  # 商品理解服务
└── data/
    ├── product_category_init.xml       # 品牌和分类初始化
    ├── product_demo_data.xml           # 演示商品数据（80个）
    ├── search_cases.json               # 搜索案例（42条）
    ├── compare_cases.json              # 对比案例（22条）
    └── dialogue_cases.json             # 导购对话案例（18组）
```

## 数据内容

### 产品分类 (4个)
- 手机/数码 (demo_phone)
- 蓝牙耳机/音频 (demo_earphone)
- 笔记本/办公 (demo_laptop)
- 家电/小家电 (demo_appliance)

### 品牌数据 (20个)

**手机品牌 (6个)**
- 小米、华为、苹果、三星、vivo、OPPO

**耳机品牌 (5个)**
- 索尼、BOSE、苹果(音频)、华为音频、漫步者、森海塞尔

**笔记本品牌 (6个)**
- 联想、戴尔、华为、苹果、华硕、惠普

**家电品牌 (5个)**
- 美的、格力、飞利浦、戴森、德尔玛、小米(家电)

### 商品数据 (80个)

| 类别 | 商品数量 |
|------|----------|
| 手机/数码 | 20个 |
| 蓝牙耳机/音频 | 20个 |
| 笔记本/办公 | 20个 |
| 家电/小家电 | 20个 |
| **总计** | **80个** |

## 自定义字段说明

### x_scenario_tags - 场景标签
逗号分隔的场景标签，用于描述商品适用场景。

示例值：
- `商务,拍照,游戏,日常使用`
- `降噪,音乐,通勤`
- `游戏,性价比,日常使用`

### x_selling_point - 核心卖点
一句话描述商品的核心竞争优势。

示例值：
- `徕卡影像+骁龙8 Gen3高性能组合`
- `A17 Pro+钛金属旗舰iPhone`
- `顶级降噪+优秀音质通勤神器`

### x_target_people - 目标人群
商品的目标购买人群。

示例值：
- `追求旗舰性能的用户,摄影爱好者`
- `商务人士,科技爱好者`
- `学生党,预算有限用户`

## 商品理解层

### ProductUnderstandingService

商品理解服务将 Odoo 商品转换为 AI 可理解的结构化对象。

#### 核心方法

**get_product_understanding(product)**
获取单个商品的理解对象，返回结构如下：
```python
{
    'id': product.id,
    'name': '小米14 Pro 5G智能手机',
    'sku': 'DEMO-PHONE-001',
    'brand': '小米',
    'category': '手机/数码',
    'price': 4999.00,
    'description': '小米14 Pro，骁龙8 Gen3处理器...',
    'selling_point': '徕卡影像+骁龙8 Gen3高性能组合',
    'target_people': '追求旗舰性能的用户,摄影爱好者',
    'scenes': ['商务', '拍照', '游戏', '日常使用'],
    'weight': 0.21,
    'attributes': {'颜色': ['黑色', '白色'], '内存': ['12GB', '16GB']},
    'searchable_text': '小米14 Pro 5G智能手机 DEMO-PHONE-001...',
    'compare_features': {'price': 4999.00, 'weight': 0.21, 'brand': '小米'},
    'recommendation_tags': ['徕卡影像+骁龙8 Gen3高性能组合', '追求旗舰性能的用户', '摄影爱好者', '商务', '拍照', '游戏', '日常使用']
}
```

**get_products_understanding(products)**
批量获取商品理解列表。

**search_products_for_understanding(query, category, brand, min_price, max_price, scenes, limit)**
基于理解字段搜索商品。

**get_similar_products(product_id, limit)**
获取相似商品。

### 使用示例

```python
from odoo import api
from ..services.product_understanding_service import ProductUnderstandingService

class MyAI Service:
    @api.model
    def search_products(self, query, category=None):
        service = ProductUnderstandingService(self.env)
        return service.search_products_for_understanding(
            query=query,
            category=category,
            limit=50
        )
```

## 案例文件说明

### search_cases.json - 搜索案例（42条）

覆盖多种搜索场景：

| 类型 | 示例 | 说明 |
|------|------|------|
| 模糊搜索 | "打游戏快的手机" | 自然语言描述需求 |
| 场景搜索 | "商务人士用什么手机" | 场景化需求 |
| 人群搜索 | "学生党性价比手机" | 目标人群需求 |
| 参数搜索 | "骁龙8 Gen3手机" | 具体参数需求 |
| 预算搜索 | "3000-5000元手机" | 价格范围需求 |
| 反向排除 | "不要苹果，要国产" | 排除性需求 |

每条案例包含：
- `id`: 案例ID
- `raw_query`: 用户原始查询
- `inferred_category`: 推断的分类
- `inferred_filters`: 推断的筛选条件
- `inferred_target_people`: 推断的目标人群
- `inferred_scenes`: 推断的场景
- `expected_followup_questions`: 期望的追问
- `expected_product_templates`: 期望返回的商品SKU
- `expected_domain`: 期望的Odoo搜索域

### compare_cases.json - 对比案例（22条）

覆盖多种对比场景：

| 类型 | 示例 | 说明 |
|------|------|------|
| 同类不同价位 | iPhone 15 vs iPhone 15 Pro | 定位差异 |
| 同类不同卖点 | 小米拍照 vs 华为拍照 | 特色差异 |
| 同类不同场景 | 商务手机 vs 游戏手机 | 场景差异 |
| 人群导向型 | 学生党手机 vs 商务人士手机 | 人群差异 |

每条案例包含：
- `id`: 案例ID
- `products_to_compare`: 要对比的商品SKU列表
- `compare_dimensions`: 对比维度
- `expected_structured_summary`: 期望的结构化对比摘要
- `better_for_people`: 适合人群
- `better_for_scenes`: 适合场景

### dialogue_cases.json - 导购对话案例（18组）

覆盖多种导购场景：

| 类别 | 案例数 |
|------|--------|
| 手机 | 6组 |
| 蓝牙耳机 | 3组 |
| 笔记本 | 3组 |
| 空调 | 2组 |
| 小家电 | 3组 |
| 综合场景 | 1组 |

每组案例包含：
- `id`: 案例ID
- `category`: 商品类别
- `user_turns`: 用户多轮对话
- `system_should_ask`: 系统应追问的问题
- `structure_after_each_turn`: 每轮对话后的结构化理解
- `candidate_products`: 候选商品SKU列表
- `final_recommendation_reason`: 最终推荐理由

## 安装与加载

### 安装命令

```bash
# 方式1: 使用 odoo-bin
./venv310/bin/python odoo-bin -c debian/odoo.conf -d odoo17 -i ai_product_demo --stop-after-init

# 方式2: 升级模块
./venv310/bin/python odoo-bin -c debian/odoo.conf -d odoo17 -u ai_product_demo --stop-after-init
```

### 验证数据

安装后可通过以下方式验证：

1. **Odoo界面**: 访问 产品 > 产品，找到标记为 `DEMO-*` 的商品
2. **数据库查询**:
   ```sql
   -- 验证商品数量
   SELECT c.name as category, COUNT(*) as product_count
   FROM product_template p
   JOIN product_category c ON p.categ_id = c.id
   WHERE p.default_code LIKE 'DEMO-%'
   GROUP BY c.name;

   -- 验证商品理解字段
   SELECT name, x_scenario_tags, x_selling_point, x_target_people
   FROM product_template
   WHERE default_code LIKE 'DEMO-%'
   LIMIT 5;
   ```

3. **Python验证**:
   ```python
   from odoo import api
   from ai_product_demo.services.product_understanding_service import ProductUnderstandingService

   @api.model
   def test_product_understanding(self):
       service = ProductUnderstandingService(self.env)
       products = self.env['product.template'].search([
           ('default_code', '=', 'DEMO-PHONE-001')
       ], limit=1)
       if products:
           understanding = service.get_product_understanding(products)
           print(understanding)
   ```

## 使用场景

1. **AI搜索演示**: 用于测试商品搜索和推荐功能
2. **商品对比**: 提供多品牌、多价位的商品对比数据
3. **导购场景**: 模拟真实导购对话的测试数据
4. **数据看板**: 用于数据分析展示的商品基础数据
5. **商品理解**: 通过 ProductUnderstandingService 转换为结构化数据

## 注意事项

1. 本模块为演示用途，数据为虚构，仅供测试
2. 安装前请确保 `product` 和 `product_extension` 模块已安装
3. `x_scenario_tags`、`x_selling_point`、`x_target_people` 字段需要有对应的自定义字段支持
4. JSON案例文件在模块升级时会重新加载

## 扩展建议

如需扩展更多演示数据，可考虑：

1. **添加更多商品类别**: 如 相机/摄影、智能手表/穿戴、配件等
2. **添加属性线**: 为商品添加颜色、内存等属性变体
3. **添加标签**: 创建 `product_tag` 数据并关联商品
4. **添加图片**: 为商品添加演示图片
5. **扩展案例**: 在JSON文件中添加更多搜索、对比、对话案例

## 更新日志

- **v1.0** (2024-04-19): 初始版本，包含80个演示商品
- **v1.1** (2024-04-19): 新增商品理解服务层和案例数据
  - 添加 `services/product_understanding_service.py`
  - 添加 `data/search_cases.json`（42条搜索案例）
  - 添加 `data/compare_cases.json`（22条对比案例）
  - 添加 `data/dialogue_cases.json`（18组导购案例）
