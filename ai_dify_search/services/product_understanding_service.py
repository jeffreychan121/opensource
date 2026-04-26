# -*- coding: utf-8 -*-
"""
@File   :   product_understanding_service.py
@Time   :   2024-04-18
@Desc   :   商品理解服务
            将商品原始数据结构化为统一商品知识对象
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

_logger = logging.getLogger(__name__)


class ProductUnderstandingService:
    """
    商品理解服务

    负责从商品原始数据中提取结构化信息：
    - 品牌识别
    - 类目标准化
    - 参数归一化
    - 卖点提取
    - 人群标签
    - 场景标签
    """

    # ==================== 品牌同义词映射 ====================
    # 英文名 → 中文名
    BRAND_ALIASES = {
        'apple': 'Apple',
        'iphone': 'Apple',
        'mi': '小米',
        'xiaomi': '小米',
        'redmi': 'Redmi',
        'huawei': '华为',
        'honor': '荣耀',
        'samsung': '三星',
        'oppo': 'OPPO',
        'vivo': 'vivo',
        'oneplus': '一加',
        'realme': '真我',
        'iqoo': 'iQOO',
        'midea': '美的',
        'gree': '格力',
        'haier': '海尔',
        ' TCL': 'TCL',
        'sony': '索尼',
        'lg': 'LG',
        'dell': '戴尔',
        'hp': '惠普',
        'lenovo': '联想',
        'asus': '华硕',
        'acer': '宏碁',
        'microsoft': '微软',
        'google': '谷歌',
        'amazon': '亚马逊',
        'nvidia': '英伟达',
        'amd': 'AMD',
        'intel': '英特尔',
    }

    # 品牌中文名 → 英文名
    BRAND_TO_EN = {v.lower(): k for k, v in BRAND_ALIASES.items()}
    for cn, en in [
        ('苹果', 'apple'), ('小米', 'xiaomi'), ('华为', 'huawei'),
        ('荣耀', 'honor'), ('三星', 'samsung'), ('OPPO', 'oppo'),
        ('vivo', 'vivo'), ('一加', 'oneplus'), ('真我', 'realme'),
        ('iQOO', 'iqoo'), ('美的', 'midea'), ('格力', 'gree'),
        ('海尔', 'haier'), ('TCL', 'tcl'), ('索尼', 'sony'),
        ('戴尔', 'dell'), ('惠普', 'hp'), ('联想', 'lenovo'),
        ('华硕', 'asus'), ('宏碁', 'acer'),
    ]:
        BRAND_TO_EN[cn] = en

    # ==================== 类目层级映射 ====================
    # 简化版类目层级
    CATEGORY_HIERARCHY = {
        '手机': ['智能手机', '功能机', '老人机'],
        '电脑': ['笔记本电脑', '台式电脑', '平板电脑', '一体机'],
        '家电': ['冰箱', '洗衣机', '空调', '电视', '热水器', '油烟机'],
        '数码': ['相机', '摄像机', '耳机', '音箱', '智能手表', '手环'],
        '汽车用品': ['行车记录仪', '车载充电器', '车衣', '脚垫', '座垫'],
    }

    # ==================== 参数归一化规则 ====================
    # 单位映射
    UNIT_MAPPINGS = {
        '英寸': 'inch',
        '寸': 'inch',
        'inch': 'inch',
        'inches': 'inch',
        '毫安时': 'mAh',
        'mah': 'mAh',
        'miliampere hour': 'mAh',
        'GB': 'GB',
        'gb': 'GB',
        'TB': 'TB',
        'tb': 'TB',
        'G': 'GB',
        'g': 'GB',
    }

    # ==================== 卖点关键词 ====================
    SELLING_POINT_PATTERNS = {
        '续航': ['续航', '电池', '待机', '充电快', '大容量电池'],
        '拍照': ['拍照', '摄影', '像素', '摄像头', '美颜', '夜景', '防抖'],
        '性能': ['流畅', '高速', '旗舰', '处理器', 'CPU', 'GPU', '跑分'],
        '屏幕': ['屏幕', '显示屏', '刷新率', '护眼', '高清', 'OLED', 'LCD'],
        '外观': ['轻薄', '时尚', '颜值', '手感', '重量', '厚度'],
        '系统': ['系统', 'IOS', 'Android', '鸿蒙', 'MIUI', 'EMUI'],
        '音质': ['音质', '音响', '扬声器', 'HiFi', '音频'],
        '散热': ['散热', '制冷', '变频', '静音'],
        '容量': ['大容量', '小体积', '迷你', '省空间'],
        '智能': ['智能', 'AI', '人工智能', '自动', '互联'],
    }

    # ==================== 人群标签关键词 ====================
    TARGET_PEOPLE_PATTERNS = {
        '老人': ['老人', '老年人', '爸妈', '父母', '大字体', '大声音'],
        '学生': ['学生', '大学生', '考研', '上网课', '学习'],
        '商务': ['商务', '办公', '出差', '会议', '便携'],
        '游戏': ['游戏', '电竞', '玩家', '开黑', '手游'],
        '女性': ['女生', '女性', '自拍', '美颜', '轻便'],
        '男性': ['男生', '男性', '游戏', '科技感'],
        '家庭': ['家庭', '一家三口', '有孩子', '全家'],
        '租房': ['租房', '独居', '小户型', '省空间'],
        '司机': ['司机', '车主', '驾驶', '车载'],
        '运动': ['运动', '跑步', '健身', '骑行', '户外'],
    }

    # ==================== 场景标签关键词 ====================
    SCENE_PATTERNS = {
        '日常使用': ['日常', '通勤', '居家', '休息', '放松'],
        '办公学习': ['办公', '学习', '上网课', '写论文', '工作'],
        '拍照摄影': ['拍照', '摄影', '自拍', '短视频', '直播'],
        '游戏娱乐': ['游戏', '电竞', '看电影', '追剧', '听音乐'],
        '运动健身': ['跑步', '健身', '运动', '骑行', '户外'],
        '差旅出行': ['出差', '旅行', '旅游', '便携', '轻便'],
        '送礼': ['送礼', '礼物', '生日', '节日', '纪念日'],
        '家居生活': ['家居', '收纳', '清洁', '厨房', '卧室'],
        '驾驶出行': ['驾驶', '车载', '导航', '行车', '停车'],
        '商务办公': ['商务', '会议', '谈判', '签约', '接待'],
    }

    def __init__(self, env):
        """
        初始化商品理解服务

        :param env: Odoo environment
        """
        self.env = env

    def understand_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将商品原始数据转换为结构化的商品理解对象

        :param product_data: 商品原始数据（如 search_service 返回的格式）
        :return: 结构化的商品理解对象
        """
        result = {
            'product_id': product_data.get('id'),
            'title': product_data.get('name', ''),
            'brand': self._extract_brand(product_data),
            'category_path': self._extract_category_path(product_data),
            'attributes': self._extract_attributes(product_data),
            'selling_points': self._extract_selling_points(product_data),
            'target_people': self._extract_target_people(product_data),
            'scenes': self._extract_scenes(product_data),
            'price_range': self._extract_price_range(product_data),
            'tags': self._extract_tags(product_data),
            'searchable_text': self._build_searchable_text(product_data),
            'compare_features': self._build_compare_features(product_data),
        }
        return result

    def understand_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量理解商品

        :param products: 商品列表
        :return: 理解后的商品列表
        """
        return [self.understand_product(p) for p in products]

    def _extract_brand(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        提取品牌信息

        :param product: 商品数据
        :return: 品牌信息字典或None
        """
        name = product.get('name', '')
        description = product.get('description_sale', '') + product.get('description', '')
        category_names = product.get('category_names', [])

        # 合并所有文本
        text = ' '.join([name, description] + category_names)

        # 先检查全名匹配（更长的词优先）
        brand_mappings = [
            ('apple', 'Apple'),
            ('iphone', 'Apple'),
            ('小米', '小米'),
            ('mi', '小米'),
            ('xiaomi', '小米'),
            ('redmi', 'Redmi'),
            ('huawei', '华为'),
            ('honor', '荣耀'),
            ('samsung', '三星'),
            ('oppo', 'OPPO'),
            ('vivo', 'vivo'),
            ('oneplus', '一加'),
            ('realme', '真我'),
            ('iqoo', 'iQOO'),
            ('midea', '美的'),
            ('gree', '格力'),
            ('haier', '海尔'),
            ('tcl', 'TCL'),
            ('sony', '索尼'),
            ('lg', 'LG'),
            ('dell', '戴尔'),
            ('hp', '惠普'),
            ('lenovo', '联想'),
            ('华硕', '华硕'),
            ('asus', '华硕'),
            ('宏碁', '宏碁'),
            ('acer', '宏碁'),
            ('microsoft', '微软'),
            ('google', '谷歌'),
            ('联想', '联想'),
        ]

        # 按名称长度降序排列，确保长名称优先匹配
        brand_mappings.sort(key=lambda x: len(x[0]), reverse=True)

        text_lower = text.lower()
        for alias, brand_name in brand_mappings:
            if alias in text_lower:
                return {
                    'name': brand_name,
                    'original': alias if alias != brand_name.lower() else None,
                }

        return None

    def _extract_category_path(self, product: Dict[str, Any]) -> List[str]:
        """
        提取类目路径

        :param product: 商品数据
        :return: 类目路径列表
        """
        category_names = product.get('category_names', [])
        if category_names:
            return category_names

        # 如果没有类目，尝试从名称推断
        name = product.get('name', '')
        for main_cat, sub_cats in self.CATEGORY_HIERARCHY.items():
            for sub_cat in sub_cats:
                if sub_cat in name:
                    return [main_cat, sub_cat]
        return []

    def _extract_attributes(self, product: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        提取商品属性/规格

        :param product: 商品数据
        :return: 属性列表
        """
        attributes = product.get('attributes', [])
        if attributes:
            return attributes

        # 尝试从名称和描述中提取参数
        name = product.get('name', '')
        description = product.get('description_sale', '')
        text = ' '.join([name, description])

        extracted = []

        # 屏幕尺寸
        screen_pattern = r'(\d+\.?\d*)\s*[英寸寸]\s*["]?'
        match = re.search(screen_pattern, text)
        if match:
            extracted.append({
                'name': '屏幕尺寸',
                'value': f"{match.group(1)}英寸",
                'raw': match.group(0),
            })

        # 电池容量
        battery_pattern = r'(\d{3,5})\s*[mM][aA][hH]'
        match = re.search(battery_pattern, text)
        if match:
            extracted.append({
                'name': '电池容量',
                'value': f"{match.group(1)}mAh",
                'raw': match.group(0),
            })

        # 存储 - 匹配 "数字GB/TB存储" 或 "数字GB/TB 存储"
        storage_pattern = r'(\d+)\s*(GB|TB)\s*(?:存储|ROM|硬盘|空间)'
        match = re.search(storage_pattern, text, re.IGNORECASE)
        if match:
            extracted.append({
                'name': '存储',
                'value': f"{match.group(1)}{match.group(2).upper()}",
                'raw': match.group(0),
            })

        # 内存 - 匹配 "数字GB内存" 或 "数字GB 内存" 或 "数字GB/RAM"
        ram_pattern = r'(\d+)\s*GB\s*(?:内存|RAM)?'
        # 检查是否有内存相关词
        has_ram_context = any(ind in text for ind in ['内存', 'RAM', '运行内存'])
        if has_ram_context:
            match = re.search(ram_pattern, text, re.IGNORECASE)
            if match:
                extracted.append({
                    'name': '运行内存',
                    'value': f"{match.group(1)}GB",
                    'raw': match.group(0),
                })

        # 像素
        pixel_pattern = r'(\d+)\s*[万兆]?像素'
        match = re.search(pixel_pattern, text)
        if match:
            extracted.append({
                'name': '像素',
                'value': match.group(0),
                'raw': match.group(0),
            })

        return extracted

    def _extract_selling_points(self, product: Dict[str, Any]) -> List[str]:
        """
        提取卖点

        :param product: 商品数据
        :return: 卖点列表
        """
        name = product.get('name', '')
        description = product.get('description_sale', '')
        text = ' '.join([name, description])

        selling_points = []

        for point_type, keywords in self.SELLING_POINT_PATTERNS.items():
            for keyword in keywords:
                if keyword in text and point_type not in selling_points:
                    selling_points.append(point_type)
                    break

        return selling_points

    def _extract_target_people(self, product: Dict[str, Any]) -> List[str]:
        """
        提取目标人群

        :param product: 商品数据
        :return: 人群标签列表
        """
        name = product.get('name', '')
        description = product.get('description_sale', '')
        text = ' '.join([name, description])

        target_people = []

        for people_type, keywords in self.TARGET_PEOPLE_PATTERNS.items():
            for keyword in keywords:
                if keyword in text and people_type not in target_people:
                    target_people.append(people_type)
                    break

        return target_people

    def _extract_scenes(self, product: Dict[str, Any]) -> List[str]:
        """
        提取使用场景

        :param product: 商品数据
        :return: 场景列表
        """
        name = product.get('name', '')
        description = product.get('description_sale', '')
        scenario_tags = product.get('scenario_tags', [])
        text = ' '.join([name, description] + scenario_tags)

        scenes = []

        for scene_type, keywords in self.SCENE_PATTERNS.items():
            for keyword in keywords:
                if keyword in text and scene_type not in scenes:
                    scenes.append(scene_type)
                    break

        return scenes

    def _extract_price_range(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        提取价格区间

        :param product: 商品数据
        :return: 价格区间信息
        """
        price = product.get('price', 0)
        if not price:
            return None

        return {
            'min': price,
            'max': price,
            'currency': product.get('currency', 'CNY'),
        }

    def _extract_tags(self, product: Dict[str, Any]) -> List[str]:
        """
        提取标签

        :param product: 商品数据
        :return: 标签列表
        """
        tags = set()

        # 来自类目
        tags.update(product.get('category_names', []))

        # 来自场景标签
        tags.update(product.get('scenario_tags', []))

        # 来自卖点
        tags.update(self._extract_selling_points(product))

        # 来自人群
        tags.update(self._extract_target_people(product))

        # 来自场景
        tags.update(self._extract_scenes(product))

        return list(tags)

    def _build_searchable_text(self, product: Dict[str, Any]) -> str:
        """
        构建可搜索文本

        :param product: 商品数据
        :return: 合并的可搜索文本
        """
        parts = [
            product.get('name', ''),
            product.get('short_description', ''),
            ' '.join(product.get('category_names', [])),
            ' '.join(product.get('scenario_tags', [])),
        ]

        brand = self._extract_brand(product)
        if brand:
            parts.append(brand['name'])

        return ' '.join(parts)

    def _build_compare_features(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建对比特征

        :param product: 商品数据
        :return: 用于对比的特征字典
        """
        attributes = {attr['name']: attr['value'] for attr in self._extract_attributes(product)}

        return {
            'brand': self._extract_brand(product),
            'price': product.get('price'),
            'attributes': attributes,
            'selling_points': self._extract_selling_points(product),
            'target_people': self._extract_target_people(product),
            'scenes': self._extract_scenes(product),
        }


class QueryUnderstandingService:
    """
    搜索理解服务

    负责将用户自然语言搜索转换为结构化查询条件
    """

    # ==================== 预算关键词 ====================
    BUDGET_PATTERNS = [
        (r'预算\s*(\d+)\s*以?[内外]?', 'max', '元'),
        (r'(\d+)\s*元\s*以?[内外]?', 'max', '元'),
        (r'(\d+)\s*以?[内外]?\s*元', 'max', '元'),
        (r'不超过\s*(\d+)\s*元?', 'max', '元'),
        (r'(\d+)元以内', 'max', '元'),
        (r'(\d+)元以下', 'max', '元'),
        (r'大概\s*(\d+)', 'approx', '元'),
        (r'左右\s*(\d+)', 'approx', '元'),
    ]

    # ==================== 类目关键词 ====================
    CATEGORY_KEYWORDS = {
        '手机': ['手机', '智能手机', '电话'],
        '电脑': ['电脑', '笔记本', '笔记本电脑', '平板', '台式机'],
        '冰箱': ['冰箱', '冷柜', '冰柜'],
        '洗衣机': ['洗衣机', '洗衣烘干'],
        '空调': ['空调', '变频空调', '挂机', '柜机'],
        '电视': ['电视', '电视机', '智能电视'],
        '耳机': ['耳机', '蓝牙耳机', '无线耳机', '降噪耳机', '头戴式耳机'],
        '音箱': ['音箱', '音响', '蓝牙音箱'],
        '手表': ['手表', '智能手表', '运动手表'],
        '相机': ['相机', '数码相机', '单反', '微单'],
        '打印机': ['打印机', '激光打印机', '喷墨打印机'],
        '路由器': ['路由器', 'WiFi', '无线'],
    }

    # ==================== 人群关键词 ====================
    PEOPLE_KEYWORDS = {
        '老人': ['老人', '老年人', '爸妈', '父母', '长辈'],
        '学生': ['学生', '大学生', '考研', '上网课'],
        '儿童': ['儿童', '小孩', '孩子', '小朋友'],
        '商务': ['商务', '办公', '出差', '商务人士'],
        '游戏': ['游戏', '电竞', '玩家', ' gamers'],
        '女性': ['女生', '女性', '女士'],
        '男性': ['男生', '男性', '男士'],
        '家庭': ['家庭', '一家三口', '有孩子'],
        '租房': ['租房', '独居', '小户型'],
        '送礼': ['送礼', '礼物', '生日礼物'],
    }

    # ==================== 场景关键词 ====================
    SCENE_KEYWORDS = {
        '日常使用': ['日常', '通勤', '居家', '每天用'],
        '办公学习': ['办公', '学习', '上网课', '写论文'],
        '拍照摄影': ['拍照', '摄影', '自拍', '短视频'],
        '游戏娱乐': ['游戏', '电竞', '看电影', '追剧'],
        '运动健身': ['跑步', '健身', '运动', '骑行'],
        '差旅出行': ['出差', '旅行', '旅游', '便携'],
        '送礼': ['送礼', '礼物', '生日', '节日'],
        '家居': ['家居', '收纳', '清洁'],
        '驾驶': ['驾驶', '车载', '开车'],
    }

    # ==================== 属性关键词 ====================
    ATTRIBUTE_KEYWORDS = {
        '屏幕尺寸': [r'(\d+\.?\d*)\s*寸', r'(\d+\.?\d*)\s*英寸', r'(\d+\.?\d*)["]'],
        '电池容量': [r'(\d{3,5})\s*mAh', r'(\d+\.?\d*)\s*安时'],
        '存储': [r'(\d+)\s*GB', r'(\d+)\s*G\s*(?:内存|存储)'],
        '内存': [r'(\d+)\s*GB\s*(?:内存|RAM)'],
        '像素': [r'(\d+)\s*万像素', r'(\d+)\s*像素'],
        '刷新率': [r'(\d+)\s*Hz', r'(\d+)\s*赫兹'],
        '重量': [r'(\d+\.?\d*)\s*kg', r'(\d+\.?\d*)\s*克'],
        '颜色': ['黑色', '白色', '银色', '金色', '蓝色', '绿色', '红色', '粉色'],
    }

    # ==================== 排序偏好关键词 ====================
    SORT_PREFERENCE_KEYWORDS = {
        '价格': ['便宜', '实惠', '性价比', '划算', '省钱'],
        '销量': ['销量', '热销', '爆款', '爆火'],
        '评价': ['好评', '评价高', '口碑'],
        '新品': ['新品', '最新', '新款'],
        '综合': ['综合', '推荐'],
    }

    def __init__(self, env):
        """
        初始化搜索理解服务

        :param env: Odoo environment
        """
        self.env = env

    def understand_query(self, query: str) -> Dict[str, Any]:
        """
        将用户搜索词转换为结构化查询对象

        :param query: 用户搜索词
        :return: 结构化查询对象
        """
        query = query.strip()
        text = query.lower()

        result = {
            'original_query': query,
            'category': self._extract_category(text, query),
            'brand': None,
            'budget_min': None,
            'budget_max': None,
            'attributes': {},
            'target_people': [],
            'scenes': [],
            'sort_preference': None,
            'must_have': [],
            'must_not_have': [],
            'keywords': [],
        }

        # 提取预算
        budget_min, budget_max = self._extract_budget(text)
        result['budget_min'] = budget_min
        result['budget_max'] = budget_max

        # 提取人群
        result['target_people'] = self._extract_people(text)

        # 提取场景
        result['scenes'] = self._extract_scenes(text)

        # 提取属性
        result['attributes'] = self._extract_attributes(text)

        # 提取排序偏好
        result['sort_preference'] = self._extract_sort_preference(text)

        # 提取否定条件
        result['must_not_have'] = self._extract_negations(text)

        # 构建关键词
        result['keywords'] = self._build_keywords(query, result)

        return result

    def _extract_category(self, text: str, original_query: str) -> Optional[str]:
        """提取类目"""
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return None

    def _extract_budget(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """提取预算范围"""
        budget_min = None
        budget_max = None

        for pattern, budget_type, unit in self.BUDGET_PATTERNS:
            match = re.search(pattern, text)
            if match:
                amount = float(match.group(1))
                if budget_type == 'max':
                    budget_max = amount
                elif budget_type == 'min':
                    budget_min = amount
                elif budget_type == 'approx':
                    budget_min = amount * 0.8
                    budget_max = amount * 1.2
                break

        return budget_min, budget_max

    def _extract_people(self, text: str) -> List[str]:
        """提取目标人群"""
        people = []
        for people_type, keywords in self.PEOPLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text and people_type not in people:
                    people.append(people_type)
                    break
        return people

    def _extract_scenes(self, text: str) -> List[str]:
        """提取使用场景"""
        scenes = []
        for scene_type, keywords in self.SCENE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text and scene_type not in scenes:
                    scenes.append(scene_type)
                    break
        return scenes

    def _extract_attributes(self, text: str) -> Dict[str, Any]:
        """提取属性条件"""
        attributes = {}

        for attr_name, patterns in self.ATTRIBUTE_KEYWORDS.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    attributes[attr_name] = match.group(0)
                    break

        return attributes

    def _extract_sort_preference(self, text: str) -> Optional[str]:
        """提取排序偏好"""
        for pref, keywords in self.SORT_PREFERENCE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return pref
        return None

    def _extract_negations(self, text: str) -> List[str]:
        """提取否定条件"""
        negations = []

        negation_words = ['不要', '不要', '不用', '拒绝', '不含']
        for neg_word in negation_words:
            if neg_word in text:
                # 提取否定词后面的内容
                idx = text.find(neg_word)
                remaining = text[idx + len(neg_word):]
                # 简单取前几个词作为否定内容
                words = remaining.split()[:3]
                negations.extend(words)

        return negations

    def _build_keywords(self, query: str, parsed: Dict[str, Any]) -> List[str]:
        """构建关键词列表"""
        keywords = []

        # 原查询分词
        stop_words = {'的', '了', '和', '或', '在', '是', '有', '个', '一', '些', '吗', '呢', '吧'}
        words = [w for w in query if w not in stop_words]

        # 添加类目
        if parsed['category']:
            keywords.append(parsed['category'])

        # 添加属性值
        for attr_value in parsed['attributes'].values():
            if attr_value:
                keywords.append(str(attr_value))

        # 添加人群
        keywords.extend(parsed['target_people'])

        # 添加场景
        keywords.extend(parsed['scenes'])

        return list(set(keywords))
