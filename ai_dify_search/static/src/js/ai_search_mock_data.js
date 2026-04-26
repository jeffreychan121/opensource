/** @odoo-module **/
/**
 * Mock Product Data for AI Shopping Search
 *
 * This file contains mock data for demonstration purposes.
 * To integrate with real backend:
 * 1. Replace the mock data functions with actual RPC calls to your API
 * 2. Update the product type definition to match your backend schema
 * 3. The state management and UI logic remain the same
 */

/**
 * @typedef {Object} ProductSpec
 * @property {string} label - Display label for the spec
 * @property {string} value - Spec value
 */

/**
 * @typedef {Object} Product
 * @property {number} id - Unique product ID
 * @property {string} name - Product name
 * @property {string} subtitle - Short product description/bullets
 * @property {string} image - Product image URL
 * @property {number} price - Current price
 * @property {number|null} originalPrice - Original price (for discount display)
 * @property {string[]} tags - Product tags/categories
 * @property {string} category - Primary category
 * @property {string} usageType - Usage type (船用动力引擎, 机械动力核心, 硬核机械模型)
 * @property {string} shortReason - AI recommendation reason
 * @property {ProductSpec[]} specs - Product specifications for comparison
 * @property {string} deliveryText - Delivery info text
 * @property {string} shopName - Shop name
 * @property {boolean} isNew - Whether product is marked as new
 */

// Mock product images - using placeholder service
const PRODUCT_IMAGES = {
    engine1: 'https://picsum.photos/seed/engine1/400/400',
    engine2: 'https://picsum.photos/seed/engine2/400/400',
    engine3: 'https://picsum.photos/seed/engine3/400/400',
    engine4: 'https://picsum.photos/seed/engine4/400/400',
    engine5: 'https://picsum.photos/seed/engine5/400/400',
    engine6: 'https://picsum.photos/seed/engine6/400/400',
    model1: 'https://picsum.photos/seed/model1/400/400',
    model2: 'https://picsum.photos/seed/model2/400/400',
    model3: 'https://picsum.photos/seed/model3/400/400',
    model4: 'https://picsum.photos/seed/model4/400/400',
    model5: 'https://picsum.photos/seed/model5/400/400',
    model6: 'https://picsum.photos/seed/model6/400/400',
};

/**
 * @type {Product[]}
 * Mock product catalog with 12 products across 3 usage categories
 */
export const MOCK_PRODUCTS = [
    // === 船用动力引擎 (Marine Power Engines) ===
    {
        id: 1,
        name: 'XY-200船用舷外发动机 200匹马力',
        subtitle: '高效节能，适合钓鱼艇/橡皮艇',
        image: PRODUCT_IMAGES.engine1,
        price: 15800,
        originalPrice: 18900,
        tags: ['船用', '200匹', '四冲程'],
        category: '船用动力引擎',
        usageType: '船用动力引擎',
        shortReason: '200匹马力强劲输出，四冲程省油30%，适合商用钓鱼',
        specs: [
            { label: '马力', value: '200HP' },
            { label: '冲程', value: '四冲程' },
            { label: '重量', value: '156kg' },
            { label: '油箱', value: '24L' },
            { label: '启动', value: '电启动' },
        ],
        deliveryText: '同城隔日达',
        shopName: '海洋动力装备专营店',
        isNew: true,
    },
    {
        id: 2,
        name: 'YM-150舷内机 船用柴油发动机',
        subtitle: '稳定性强，适合游艇/公务艇',
        image: PRODUCT_IMAGES.engine2,
        price: 28500,
        originalPrice: null,
        tags: ['船用', '舷内机', '柴油'],
        category: '船用动力引擎',
        usageType: '船用动力引擎',
        shortReason: '舷内设计更稳定，柴油动力续航500海里',
        specs: [
            { label: '马力', value: '150HP' },
            { label: '燃料', value: '柴油' },
            { label: '重量', value: '280kg' },
            { label: '续航', value: '500海里' },
            { label: '噪音', value: '65dB' },
        ],
        deliveryText: '专业安装服务',
        shopName: '船舶动力专家',
        isNew: false,
    },
    {
        id: 3,
        name: 'XC-80便携式船外机 80匹',
        subtitle: '轻便易携带，适合小舟/橡皮艇',
        image: PRODUCT_IMAGES.engine3,
        price: 4200,
        originalPrice: 4800,
        tags: ['船用', '便携', '80匹'],
        category: '船用动力引擎',
        usageType: '船用动力引擎',
        shortReason: '仅28kg超轻设计，单人可安装，野外作业首选',
        specs: [
            { label: '马力', value: '80HP' },
            { label: '重量', value: '28kg' },
            { label: '冲程', value: '二冲程' },
            { label: '油箱', value: '12L' },
            { label: '便携性', value: '可折叠' },
        ],
        deliveryText: '全国包邮',
        shopName: '户外动力装备店',
        isNew: false,
    },
    {
        id: 4,
        name: 'HD-300军工级船用推进系统',
        subtitle: '军用标准，超强耐用性',
        image: PRODUCT_IMAGES.engine4,
        price: 52000,
        originalPrice: null,
        tags: ['船用', '军用级', '300匹'],
        category: '船用动力引擎',
        usageType: '船用动力引擎',
        shortReason: '采用潜艇级钢材，耐腐蚀10年不生锈',
        specs: [
            { label: '马力', value: '300HP' },
            { label: '材质', value: '潜艇钢' },
            { label: '寿命', value: '20年' },
            { label: '保修', value: '5年' },
            { label: '认证', value: '军标' },
        ],
        deliveryText: '定制生产 30天',
        shopName: '国防动力装备',
        isNew: true,
    },

    // === 机械动力核心 (Mechanical Power Core) ===
    {
        id: 5,
        name: 'GM-500涡轮增压器 机械增压套装',
        subtitle: '提升动力30%，适用于各类发动机',
        image: PRODUCT_IMAGES.engine5,
        price: 8900,
        originalPrice: 10800,
        tags: ['机械增压', '涡轮', '通用'],
        category: '机械动力核心',
        usageType: '机械动力核心',
        shortReason: '机械增压无延迟，动力响应提升30%',
        specs: [
            { label: '增压比', value: '1.8:1' },
            { label: '适用', value: '2.0-4.0L' },
            { label: '材质', value: '钛合金' },
            { label: '最高转速', value: '80000rpm' },
            { label: '安装', value: '原位替换' },
        ],
        deliveryText: '支持定制',
        shopName: '高性能动力改装',
        isNew: false,
    },
    {
        id: 6,
        name: 'CVT-800无级变速器 工业级',
        subtitle: '平滑传动，适用于农机/工程机械',
        image: PRODUCT_IMAGES.engine6,
        price: 12500,
        originalPrice: null,
        tags: ['CVT', '无级变速', '工业'],
        category: '机械动力核心',
        usageType: '机械动力核心',
        shortReason: 'CVT无级变速，燃油效率提升25%',
        specs: [
            { label: '扭矩', value: '800Nm' },
            { label: '传动效率', value: '92%' },
            { label: '速比范围', value: '0-6:1' },
            { label: '适用功率', value: '50-150HP' },
            { label: '防护等级', value: 'IP67' },
        ],
        deliveryText: '上门安装',
        shopName: '工业传动专家',
        isNew: true,
    },
    {
        id: 7,
        name: 'PS-200动力转向系统',
        subtitle: '液压助力，转向轻盈',
        image: PRODUCT_IMAGES.engine1,
        price: 6800,
        originalPrice: 7500,
        tags: ['转向系统', '液压助力', '改装'],
        category: '机械动力核心',
        usageType: '机械动力核心',
        shortReason: '液压助力转向，原车无损安装',
        specs: [
            { label: '助力类型', value: '液压' },
            { label: '工作压力', value: '12MPa' },
            { label: '转向比', value: '14:1' },
            { label: '兼容车型', value: ' универсал' },
            { label: '安装难度', value: '简单' },
        ],
        deliveryText: '视频指导安装',
        shopName: '汽车动力升级',
        isNew: false,
    },
    {
        id: 8,
        name: 'GB-1200重型齿轮箱 工业减速机',
        subtitle: '直角输出，大扭矩传输',
        image: PRODUCT_IMAGES.engine2,
        price: 15800,
        originalPrice: null,
        tags: ['齿轮箱', '减速机', '重型'],
        category: '机械动力核心',
        usageType: '机械动力核心',
        shortReason: 'RV减速机精度，承载能力提升40%',
        specs: [
            { label: '减速比', value: '1:100' },
            { label: '输出扭矩', value: '1200Nm' },
            { label: '传动效率', value: '95%' },
            { label: '背隙', value: '<3弧分' },
            { label: '润滑方式', value: '永久润滑' },
        ],
        deliveryText: '专业技术支持',
        shopName: '精密传动制造',
        isNew: false,
    },

    // === 硬核机械模型 (Hardcore Mechanical Models) ===
    {
        id: 9,
        name: 'HM-1:12航空发动机模型',
        subtitle: '全金属仿真，可拆解组装',
        image: PRODUCT_IMAGES.model1,
        price: 2800,
        originalPrice: 3200,
        tags: ['航模', '金属', '仿真'],
        category: '硬核机械模型',
        usageType: '硬核机械模型',
        shortReason: '300+精密零件，真实还原发动机结构',
        specs: [
            { label: '比例', value: '1:12' },
            { label: '零件数', value: '320个' },
            { label: '材质', value: '铝合金+铜' },
            { label: '尺寸', value: '25x15x18cm' },
            { label: '功能', value: '可运行' },
        ],
        deliveryText: '京东快递',
        shopName: '精密模型工坊',
        isNew: true,
    },
    {
        id: 10,
        name: 'HM-2:16柴油机透明模型',
        subtitle: '透明外壳，观察内部结构',
        image: PRODUCT_IMAGES.model2,
        price: 1680,
        originalPrice: null,
        tags: ['航模', '透明', '教学'],
        category: '硬核机械模型',
        usageType: '硬核机械模型',
        shortReason: '透明PC外壳，教学展示首选',
        specs: [
            { label: '比例', value: '1:16' },
            { label: '零件数', value: '180个' },
            { label: '外壳', value: '透明PC' },
            { label: '尺寸', value: '30x12x18cm' },
            { label: '适用', value: '教学演示' },
        ],
        deliveryText: '次日达',
        shopName: '教育装备商城',
        isNew: false,
    },
    {
        id: 11,
        name: 'HM-3V12超跑发动机动态模型',
        subtitle: '还原V12声浪，可遥控启动',
        image: PRODUCT_IMAGES.model3,
        price: 5800,
        originalPrice: 6800,
        tags: ['超跑', 'V12', '动态'],
        category: '硬核机械模型',
        usageType: '硬核机械模型',
        shortReason: '声浪模拟系统，真实V12发动机音效',
        specs: [
            { label: '比例', value: '1:8' },
            { label: '气缸', value: 'V12' },
            { label: '声浪', value: '真实录音' },
            { label: '遥控距离', value: '50m' },
            { label: '电池', value: '7.4V 2000mAh' },
        ],
        deliveryText: '限时特惠',
        shopName: '超级车模收藏',
        isNew: true,
    },
    {
        id: 12,
        name: 'HM-4蒸汽机古董复刻版',
        subtitle: '手工打造，还原工业革命',
        image: PRODUCT_IMAGES.model4,
        price: 4200,
        originalPrice: null,
        tags: ['古董复刻', '蒸汽机', '收藏'],
        category: '硬核机械模型',
        usageType: '硬核机械模型',
        shortReason: '匠人手工打造，限 量88台',
        specs: [
            { label: '原型', value: '瓦特蒸汽机' },
            { label: '材质', value: '黄铜+实木' },
            { label: '工艺', value: '纯手工' },
            { label: '产量', value: '限量88台' },
            { label: '证书', value: '收藏证书' },
        ],
        deliveryText: '顺丰保价',
        shopName: '古董机械收藏馆',
        isNew: false,
    },
];

/**
 * Usage categories for the guide cards
 * @type {Array<{id: string, name: string, icon: string, description: string}>}
 */
export const USAGE_CATEGORIES = [
    {
        id: '船用动力引擎',
        name: '船用动力引擎',
        icon: '🚤',
        description: '舷外机、舷内机、推进系统',
    },
    {
        id: '机械动力核心',
        name: '机械动力核心',
        icon: '⚙️',
        description: '涡轮增压器、变速器、转向系统',
    },
    {
        id: '硬核机械模型',
        name: '硬核机械模型',
        icon: '🔧',
        description: '航模发动机、透明教学模型',
    },
];

/**
 * Search hot words / suggestions
 * @type {string[]}
 */
export const SEARCH_SUGGESTIONS = [
    '发动机', '舷外机', '涡轮增压器', '机械模型',
    '变速器', '船用动力', '减速机', '航模'
];

/**
 * Simulated API search function
 * In production, replace this with actual RPC call to backend
 *
 * @param {string} query - Search query
 * @param {string|null} usageType - Filter by usage type (or null for all)
 * @returns {Promise<{products: Product[], total: number}>}
 */
export async function mockSearchProducts(query, usageType = null) {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 400));

    let results = [...MOCK_PRODUCTS];

    // Filter by usage type if specified
    if (usageType && usageType !== 'all') {
        results = results.filter(p => p.usageType === usageType);
    }

    // Filter by search query if specified
    if (query && query.trim()) {
        const q = query.toLowerCase().trim();
        results = results.filter(p =>
            p.name.toLowerCase().includes(q) ||
            p.subtitle.toLowerCase().includes(q) ||
            p.tags.some(tag => tag.toLowerCase().includes(q)) ||
            p.category.toLowerCase().includes(q)
        );
    }

    return {
        products: results,
        total: results.length,
    };
}

/**
 * Get category counts for tab display
 *
 * @param {Product[]} products - List of products
 * @returns {Array<{name: string, count: number}>}
 */
export function getCategoryCounts(products) {
    const counts = {};

    products.forEach(p => {
        if (p.category) {
            counts[p.category] = (counts[p.category] || 0) + 1;
        }
    });

    return Object.entries(counts)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
}
