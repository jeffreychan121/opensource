# -*- coding: utf-8 -*-
"""
@File   :   dify_compare_service.py
@Time   :   2024-04-25
@Desc   :   Dify AI 商品对比服务
            调用 Dify Compare Workflow 进行商品 AI 对比
"""

import json
import logging
import time
import requests
from typing import Dict, Any, List, Optional

_logger = logging.getLogger(__name__)


class DifyCompareService:
    """
    Dify AI 商品对比服务

    调用 Dify Compare Workflow，输入两个商品信息，返回 AI 对比结果。
    """

    def __init__(self, env):
        """
        初始化 Dify 对比服务

        :param env: Odoo environment
        """
        self.env = env
        self._config_service = None

    @property
    def config_service(self):
        if self._config_service is None:
            from .config_service import AiSearchConfigService
            self._config_service = AiSearchConfigService(self.env)
        return self._config_service

    def _get_base_url(self) -> str:
        base_url = self.config_service.dify_compare_api_base_url
        return base_url.rstrip('/') if base_url else 'https://api.dify.ai/v1'

    def _get_api_key(self) -> str:
        return self.config_service.dify_compare_api_key or ''

    def compare_products(self, product1: Dict[str, Any], product2: Dict[str, Any]) -> Dict[str, Any]:
        """
        对比两个商品

        :param product1: 商品1数据 {'name': '', 'price': 0, 'description': '', 'specs': ''}
        :param product2: 商品2数据
        :return: 对比结果 {'same_points': [], 'diff_points': [], 'recommendation': '', 'comparison_table': []}
        """
        try:
            # 构造 Dify Workflow 输入
            product1_text = self._format_product_text(product1)
            product2_text = self._format_product_text(product2)

            # 调用 Dify
            result = self._call_dify_workflow(product1_text, product2_text)

            if result.get('success'):
                parsed = self._parse_dify_result(result)
                parsed['products'] = [
                    {'id': product1.get('id'), 'name': product1.get('name'), 'price': product1.get('price'), 'image_url': product1.get('image_url', '')},
                    {'id': product2.get('id'), 'name': product2.get('name'), 'price': product2.get('price'), 'image_url': product2.get('image_url', '')},
                ]
                parsed['attributes_compare'] = {
                    'has_comparison': bool(parsed.get('comparison_table')),
                    'attributes': {}
                }
                return parsed
            else:
                _logger.error("Dify compare failed: %s", result.get('error'))
                return self._fallback_compare(product1, product2)

        except Exception as e:
            _logger.error("Compare error: %s", str(e), exc_info=True)
            return self._fallback_compare(product1, product2)

    def _format_product_text(self, product: Dict[str, Any]) -> str:
        """格式化商品信息为文本"""
        lines = []
        if product.get('name'):
            lines.append(f"商品名称: {product['name']}")
        if product.get('price'):
            lines.append(f"价格: ¥{product['price']}")
        if product.get('description'):
            lines.append(f"描述: {product['description']}")
        if product.get('compare_selling_points'):
            lines.append(f"卖点: {product['compare_selling_points']}")
        if product.get('compare_target_people'):
            lines.append(f"适用人群: {product['compare_target_people']}")
        if product.get('compare_scenes'):
            lines.append(f"适用场景: {product['compare_scenes']}")
        if product.get('compare_highlights'):
            lines.append(f"产品亮点: {product['compare_highlights']}")
        if product.get('compare_warranty'):
            lines.append(f"保修信息: {product['compare_warranty']}")
        if product.get('compare_attributes'):
            try:
                attrs = json.loads(product['compare_attributes'])
                if isinstance(attrs, list):
                    attr_str = ', '.join([f"{a.get('name')}:{a.get('value')}" for a in attrs if isinstance(a, dict)])
                    if attr_str:
                        lines.append(f"规格参数: {attr_str}")
            except:
                pass
        if product.get('specs'):
            lines.append(f"详细规格: {product['specs']}")
        return '\n'.join(lines) if lines else product.get('name', '')

    def _call_dify_workflow(self, product1_text: str, product2_text: str) -> Dict[str, Any]:
        """
        调用 Dify Compare Workflow

        :param product1_text: 商品1文本
        :param product2_text: 商品2文本
        :return: Dify 返回结果
        """
        base_url = self._get_base_url()
        api_key = self._get_api_key()
        masked_key = api_key[:4] + '****' + api_key[-4:] if len(api_key) > 8 else '****'
        _logger.info("Dify API call: base_url=%s, api_key=%s", base_url, masked_key)

        if not api_key:
            _logger.warning("Dify API key not configured")
            return {'success': False, 'error': 'API key not configured'}

        # Dify Chatflow API endpoint (与 dify_service.py 保持一致)
        url = f"{base_url}/chat-messages"

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # 构造 prompt
        prompt = f"""请对比以下两个商品，输出JSON格式的对比结果：

商品1:
{product1_text}

商品2:
{product2_text}

【输出格式】严格输出以下JSON（不要包含其他文字）：
{{
  "same_points": ["相同点1", "相同点2"],
  "diff_points": ["差异点1", "差异点2"],
  "recommendation": "选购建议",
  "comparison_table": [
    {{"attr": "属性名", "p1": "商品1的值", "p2": "商品2的值"}}
  ]
}}

【注意事项】
1. same_points 和 diff_points 各列出2-4条
2. comparison_table 列出5-8个关键对比属性
3. recommendation 要针对不同用户场景给出具体建议
4. 只输出JSON格式，不要其他内容"""

        payload = {
            'inputs': {
                'product1': product1_text,
                'product2': product2_text,
            },
            'query': prompt,
            'response_mode': 'blocking',
            'conversation_id': '',
            'user': 'odoo-compare'
        }

        _logger.info("Calling Dify compare workflow for 2 products")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            _logger.info("Dify API response status: %s, body: %s", response.status_code, response.text[:1000] if response.text else 'empty')
            if not response.ok:
                _logger.error("Dify API error: status=%s, response=%s", response.status_code, response.text)
                return {'success': False, 'error': f'Dify API error: {response.status_code}'}
            result = response.json()

            # 解析 Dify 响应
            if 'answer' in result:
                return {'success': True, 'answer': result['answer']}
            else:
                return {'success': False, 'error': 'Invalid Dify response'}

        except requests.exceptions.Timeout:
            _logger.error("Dify API timeout")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            _logger.error("Dify API error: %s", str(e))
            return {'success': False, 'error': str(e)}
        except Exception as e:
            _logger.error("Unexpected error: %s", str(e))
            return {'success': False, 'error': str(e)}

    def _parse_dify_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 Dify 返回结果

        :param result: {'success': True, 'answer': 'json string'}
        :return: 结构化对比结果
        """
        try:
            answer = result.get('answer', '')
            if not answer:
                return self._empty_result()

            # 提取 JSON（可能在 ```json ``` 块中）
            json_str = answer
            if '```json' in answer:
                start = answer.find('```json') + 7
                end = answer.find('```', start)
                json_str = answer[start:end].strip()
            elif '```' in answer:
                start = answer.find('```') + 3
                end = answer.find('```', start)
                json_str = answer[start:end].strip()

            # 解析 JSON
            parsed = json.loads(json_str)

            return {
                'success': True,
                'same_points': parsed.get('same_points', []),
                'diff_points': parsed.get('diff_points', []),
                'recommendation': parsed.get('recommendation', ''),
                'comparison_table': parsed.get('comparison_table', []),
            }

        except json.JSONDecodeError as e:
            _logger.warning("Failed to parse Dify JSON: %s, answer: %s", e, result.get('answer', '')[:500])
            return self._empty_result()
        except Exception as e:
            _logger.error("Failed to parse Dify result: %s", e)
            return self._empty_result()

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'success': True,
            'products': [],
            'same_points': ['暂未获取到相同点信息'],
            'diff_points': ['暂未获取到差异点信息'],
            'recommendation': '暂无对比建议',
            'comparison_table': [],
            'attributes_compare': {
                'has_comparison': False,
                'attributes': {}
            }
        }

    def _fallback_compare(self, product1: Dict[str, Any], product2: Dict[str, Any]) -> Dict[str, Any]:
        """
        降级对比：当 Dify 不可用时使用规则对比

        :param product1: 商品1
        :param product2: 商品2
        :return: 基于规则的简单对比结果
        """
        _logger.info("Using fallback rule-based comparison")

        same_points = []
        diff_points = []

        # 品牌对比
        name1 = product1.get('name', '')
        name2 = product2.get('name', '')
        if name1.split()[0] == name2.split()[0] if name1 and name2 else False:
            same_points.append("品牌相同")
        elif name1 and name2:
            diff_points.append(f"品牌不同 ({name1.split()[0]} vs {name2.split()[0]})")

        # 价格对比
        price1 = product1.get('price', 0)
        price2 = product2.get('price', 0)
        if price1 and price2:
            if abs(price1 - price2) / max(price1, price2) < 0.1:
                same_points.append("价格相近")
            else:
                diff_points.append(f"价格差异大 (¥{price1} vs ¥{price2})")

        # 卖点对比
        sp1 = product1.get('compare_selling_points', '')
        sp2 = product2.get('compare_selling_points', '')
        if sp1 and sp2:
            common = set(sp1.split(',')) & set(sp2.split(','))
            if common:
                same_points.extend([f"共同卖点: {c.strip()}" for c in common if c.strip()])

        # 适用人群对比
        tp1 = product1.get('compare_target_people', '')
        tp2 = product2.get('compare_target_people', '')
        if tp1 and tp2:
            common = set(tp1.split(',')) & set(tp2.split(','))
            if common:
                same_points.extend([f"共同人群: {c.strip()}" for c in common if c.strip()])

        return {
            'success': True,
            'products': [
                {'id': product1.get('id'), 'name': product1.get('name'), 'price': price1, 'image_url': product1.get('image_url', '')},
                {'id': product2.get('id'), 'name': product2.get('name'), 'price': price2, 'image_url': product2.get('image_url', '')},
            ],
            'same_points': same_points if same_points else ['暂无共同特征'],
            'diff_points': diff_points if diff_points else ['暂无明显差异'],
            'recommendation': f"商品1 ¥{price1}，商品2 ¥{price2}，请根据需求选择",
            'comparison_table': [
                {'attr': '价格', 'p1': f'¥{price1}', 'p2': f'¥{price2}'},
                {'attr': '名称', 'p1': name1[:20] if name1 else '-', 'p2': name2[:20] if name2 else '-'},
            ],
            'attributes_compare': {
                'has_comparison': True,
                'attributes': {
                    '价格': {product1.get('id'): f'¥{price1}', product2.get('id'): f'¥{price2}'},
                    '名称': {product1.get('id'): name1[:20] if name1 else '-', product2.get('id'): name2[:20] if name2 else '-'},
                }
            }
        }
