/** @odoo-module **/
import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * AI Shopping Search Page Component
 *
 * Connects to real Dify backend API via /ai_search/query endpoint.
 * Supports both AI mode (Dify) and simple keyword search mode.
 *
 * API Response format:
 * {
 *   success: boolean,
 *   products: [{id, name, price, image_url, category_names, short_description, ...}],
 *   summary: "AI recommendation text",
 *   parsed_intent: {...},
 *   has_more: boolean,
 *   session_key: "xxx"
 * }
 */
export class AiSearchPage extends Component {
    static template = "ai_dify_search.AiSearchPage";

    // Usage categories for guide cards
    USAGE_CATEGORIES = [
        { id: '船用动力引擎', name: '船用动力引擎', icon: '🚤', description: '舷外机、舷内机、推进系统' },
        { id: '机械动力核心', name: '机械动力核心', icon: '⚙️', description: '涡轮增压器、变速器、转向系统' },
        { id: '硬核机械模型', name: '硬核机械模型', icon: '🔧', description: '航模发动机、透明教学模型' },
    ];

    // Search suggestions
    SEARCH_SUGGESTIONS = ['发动机', '舷外机', '涡轮增压器', '机械模型', '变速器', '船用动力', '减速机', '航模'];

    setup() {
        this.rpc = useService("rpc");

        /**
         * Main component state
         */
        this.state = useState({
            // Search state
            query: "",
            isLoading: false,
            aiMode: false,          // true = AI mode (Dify), false = simple keyword search
            hasSearched: false,

            // Products state
            allProducts: [],
            filteredProducts: [],
            categories: [],        // Category tabs data (from search results)
            availableCategories: [], // All available categories from backend
            activeCategory: "all",  // Currently selected category
            activeUsageType: null,  // Currently selected usage type

            // Comparison state
            selectedProducts: [],
            showCompareModal: false,
            compareBarCollapsed: false,  // Compare bar collapsed state

            // UI state
            error: null,
            emptyMessage: null,  // Separate message for "no results" (different from errors)
            usageCategories: [], // AI 解析出的分类卡片数据
            suggestions: [],     // AI 搜索建议（需要澄清时）
            aiResponse: '',     // AI 回答内容（支持流式）
            isStreaming: false,  // 是否正在流式输出
            // Compare state
            aiCompareResult: null,  // AI 对比结果
            isComparing: false,     // 是否正在调用对比 API
            compareError: null,     // 对比错误信息
        });

        // Refs
        this.searchInputRef = useRef("searchInput");

        // Initialize - load categories on mount
        onMounted(() => {
            console.log("AiSearchPage mounted");
            this._loadCategories();
        });
    }

    // ==================== Initialization ====================

    /**
     * Load all available categories from backend
     * @private
     */
    async _loadCategories() {
        try {
            const result = await this.rpc('/ai_search/categories', {});
            if (result.success && result.categories) {
                this.state.availableCategories = result.categories;
            }
        } catch (e) {
            console.error("Failed to load categories:", e);
        }
    }

    /**
     * Handle category tab click - search by category if not searched yet
     * @param {string} categoryName - Category name or 'all'
     */
    onCategoryTabClick(categoryName) {
        this.state.activeCategory = categoryName;

        // If already searched, filter locally
        if (this.state.hasSearched) {
            this._applyFilters();
        }
    }

    /**
     * Handle category pill click from available categories
     * Triggers search with the category name
     * @param {Object} category - Category object with id and name
     */
    onCategoryPillClick(category) {
        this.state.query = category.name;
        this.state.activeCategory = category.name;
        this.onSearch();
    }

    /**
     * Apply filters to products based on active category and usage type
     * @private
     */
    _applyFilters() {
        let baseProducts = [...this.state.allProducts];

        // Apply usage type filter
        if (this.state.activeUsageType) {
            baseProducts = baseProducts.filter(p => p.usageType === this.state.activeUsageType);
        }

        // Apply category filter
        if (this.state.activeCategory && this.state.activeCategory !== "all") {
            baseProducts = baseProducts.filter(p => p.category === this.state.activeCategory);
        }

        this.state.filteredProducts = baseProducts;
    }

    // ==================== Initialization ====================

    // ==================== Search ====================

    /**
     * Handle search action
     * Calls real backend API
     */
    async onSearch() {
        const query = this.state.query.trim();
        if (!query) {
            this.state.error = '请输入搜索关键词';
            return;
        }

        this.state.isLoading = true;
        this.state.error = null;

        try {
            await this._searchWithBackend(query, null, this.state.aiMode);
        } catch (e) {
            this.state.error = "搜索失败，请稍后重试";
            console.error("Search error:", e);
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Internal search method - calls backend API
     * @param {string} query - Search query
     * @param {string|null} usageType - Usage type filter
     * @param {boolean} aiMode - Use AI (Dify) or simple mode
     * @private
     */
    async _searchWithBackend(query, usageType, aiMode) {
        try {
            const result = await this.rpc('/ai_search/query', {
                query: query,
                lang: 'zh_CN',
                simple_mode: !aiMode,  // Backend uses simple_mode flag (inverted)
                page: 1,
            });

            if (result.success) {
                // Transform backend product format to frontend format
                const products = this._transformProducts(result.products || []);

                // 处理 AI 回答（支持 summary 字段和流式输出）
                if (result.summary) {
                    this.state.aiResponse = result.summary;
                } else if (result.ai_response) {
                    this.state.aiResponse = result.ai_response;
                } else {
                    this.state.aiResponse = '';
                }
                this.state.isStreaming = false;

                // 解析 usage_categories
                if (result.usage_categories && result.usage_categories.length > 0) {
                    this.state.usageCategories = result.usage_categories;
                } else {
                    this.state.usageCategories = [];
                }

                // Handle empty results - show message if available
                if (products.length === 0) {
                    this.state.emptyMessage = result.message || result.suggestions?.[0]?.suggestion || '未找到匹配的商品';
                    this.state.suggestions = result.suggestions || [];
                    this.state.error = null;
                    this.state.allProducts = [];
                    this.state.filteredProducts = [];
                    this.state.categories = [];
                    this.state.hasSearched = true;
                } else {
                    this.state.suggestions = [];  // Clear suggestions when there are results
                    this.state.allProducts = products;
                    this.state.filteredProducts = products;
                    this.state.categories = this._buildCategories(products);
                    this.state.activeCategory = "all";
                    this.state.error = null;
                }

                this.state.hasSearched = true;

                console.log("Search completed:", {
                    query,
                    aiMode,
                    productCount: products.length,
                    categories: this.state.categories,
                    hasMore: result.has_more,
                });
            } else {
                this.state.error = result.error || '搜索服务暂时不可用';
                // Try fallback with empty query to show products
                if (!query) {
                    this.state.allProducts = [];
                    this.state.filteredProducts = [];
                    this.state.categories = [];
                    this.state.hasSearched = true;
                }
            }
        } catch (e) {
            console.error("Backend API error:", e);
            this.state.error = '网络错误，请检查连接';

            // Fallback: show empty state
            this.state.allProducts = [];
            this.state.filteredProducts = [];
            this.state.categories = [];
            this.state.hasSearched = true;
        }
    }

    /**
     * Transform backend product format to frontend format
     * @param {Array} backendProducts - Products from backend
     * @returns {Array} - Frontend product format
     * @private
     */
    _transformProducts(backendProducts) {
        return backendProducts.map(p => ({
            id: p.id,
            name: p.name || 'Unnamed Product',
            subtitle: p.short_description || p.description_sale || '',
            image: p.image_url || '',
            price: p.price || 0,
            currency: p.currency || 'USD',
            originalPrice: null,  // Backend doesn't provide original price
            sku: p.default_code || '',  // SKU (product code)
            tags: p.category_names || [],  // Use category_names as tags
            // 使用后端返回的实际类别名称
            category: p.category_names && p.category_names.length > 0
                ? p.category_names[0]
                : 'Other',
            usageType: p.category_names && p.category_names.length > 0
                ? p.category_names[0]
                : 'Other',
            shortReason: p.short_reason || '',  // AI 推荐理由
            // 产品对比字段
            compareSellingPoints: p.compare_selling_points || '',
            compareTargetPeople: p.compare_target_people || '',
            compareScenes: p.compare_scenes || '',
            compareAttributes: p.compare_attributes || '[]',
            compareHighlights: p.compare_highlights || '',
            compareWarranty: p.compare_warranty || '',
            specs: [],  // Backend doesn't provide specs in list view
            deliveryText: p.sale_ok ? 'In Stock' : 'Out of Stock',
            shopName: 'Store',
            isNew: false,
        }));
    }

    /**
     * Infer usage type from category names
     * @param {Array} categoryNames - Category names from backend
     * @returns {string} - Usage type
     * @private
     */
    _inferUsageType(categoryNames, productName = '') {
        // 优先使用传入的 productName，否则使用 categoryNames
        const text = productName || categoryNames.join('');

        if (text.includes('船用') || text.includes('发动机') || text.includes('动力')) {
            return '船用动力引擎';
        }
        if (text.includes('机械') || text.includes('涡轮') || text.includes('变速') || text.includes('传动')) {
            return '机械动力核心';
        }
        if (text.includes('模型') || text.includes('航模') || text.includes('教学') || text.includes('透明')) {
            return '硬核机械模型';
        }

        return '其他';
    }

    /**
     * Build categories from products for tab display
     * @param {Array} products - Product list
     * @returns {Array} - Category counts
     * @private
     */
    _buildCategories(products) {
        const counts = {};

        products.forEach(p => {
            const cat = p.usageType || '其他';
            counts[cat] = (counts[cat] || 0) + 1;
        });

        return Object.entries(counts)
            .map(([name, count]) => ({ name, count }))
            .sort((a, b) => b.count - a.count);
    }

    /**
     * Handle Enter key in search input
     * @param {KeyboardEvent} e
     */
    onSearchKeypress(e) {
        if (e.key === "Enter") {
            this.onSearch();
        }
    }

    /**
     * Handle search suggestion click
     * @param {string} suggestion
     */
    onSuggestionClick(suggestion) {
        this.state.query = suggestion;
        // 只填充 input，不自动搜索，让用户确认后手动搜索
    }

    /**
     * Handle AI suggestion click - use action text as search query
     * @param {Object} suggestion - {type, suggestion, action}
     */
    onAiSuggestionClick(suggestion) {
        if (suggestion.type === 'change_keyword' && suggestion.action) {
            // Extract keyword from action like "将关键词替换为'引擎'后重新搜索"
            const match = suggestion.action.match(/'([^']+)'/);
            if (match && match[1]) {
                this.state.query = match[1];
                return;
            }
        }
        // Fallback: use suggestion text as query
        this.state.query = suggestion.suggestion;
    }

    // ==================== Usage Cards ====================

    /**
     * Handle usage card click
     * Filters products by usage type
     * @param {string} usageType
     */
    onUsageCardClick(usageType) {
        // Toggle if already selected
        if (this.state.activeUsageType === usageType) {
            this.state.activeUsageType = null;
        } else {
            this.state.activeUsageType = usageType;
        }

        // Filter products
        this._applyUsageTypeFilter();
    }

    /**
     * Apply usage type filter to products
     * @private
     */
    _applyUsageTypeFilter() {
        if (!this.state.activeUsageType) {
            // No filter - show all
            this.state.filteredProducts = [...this.state.allProducts];
            // Reset category tab to all
            this.state.activeCategory = "all";
        } else {
            this.state.filteredProducts = this.state.allProducts.filter(
                p => p.usageType === this.state.activeUsageType
            );
            // Also set activeCategory so the category tab shows this as selected
            this.state.activeCategory = this.state.activeUsageType;
        }
    }

    /**
     * Check if a usage card is active
     * @param {string} usageType
     * @returns {boolean}
     */
    isUsageCardActive(usageType) {
        return this.state.activeUsageType === usageType;
    }

    // ==================== Category Tabs ====================

    /**
     * Handle category tab click
     * @param {string} categoryName - 'all' or specific category name
     */
    onCategoryTabClick(categoryName) {
        this.state.activeCategory = categoryName;

        // First apply usage type filter
        let baseProducts = this.state.activeUsageType
            ? this.state.allProducts.filter(p => p.usageType === this.state.activeUsageType)
            : [...this.state.allProducts];

        // Then apply category filter
        if (categoryName === "all") {
            this.state.filteredProducts = baseProducts;
        } else {
            this.state.filteredProducts = baseProducts.filter(p => p.category === categoryName);
        }
    }

    /**
     * Check if a tab is active
     * @param {string} tabName
     * @returns {boolean}
     */
    isTabActive(tabName) {
        return this.state.activeCategory === tabName;
    }

    /**
     * Get total product count
     * @returns {number}
     */
    getTotalCount() {
        if (this.state.activeUsageType) {
            return this.state.allProducts.filter(p => p.usageType === this.state.activeUsageType).length;
        }
        return this.state.allProducts.length;
    }

    // ==================== Product Selection ====================

    /**
     * Toggle product selection for comparison
     * @param {Object} product
     * @param {Event} e - Click event
     */
    toggleProductSelection(product, e) {
        if (e) {
            e.stopPropagation();
        }

        const selected = this.state.selectedProducts;
        const index = selected.findIndex(p => p.id === product.id);

        if (index !== -1) {
            // Already selected - remove it
            selected.splice(index, 1);
        } else {
            // Not selected - add if under limit
            if (selected.length >= 2) {
                console.log("Maximum 2 products can be selected for comparison");
                return;
            }
            selected.push(product);
        }

        // Trigger reactivity
        this.state.selectedProducts = [...selected];
    }

    /**
     * Check if a product is selected
     * @param {number} productId
     * @returns {boolean}
     */
    isProductSelected(productId) {
        return this.state.selectedProducts.some(p => p.id === productId);
    }

    /**
     * Remove a product from comparison
     * @param {number} productId
     */
    removeFromComparison(productId) {
        this.state.selectedProducts = this.state.selectedProducts.filter(
            p => p.id !== productId
        );
    }

    // ==================== Compare Bar ====================

    /**
     * Get comparison slots
     * @returns {Array}
     */
    getCompareSlots() {
        const slots = [];
        for (let i = 0; i < 2; i++) {
            slots.push(this.state.selectedProducts[i] || null);
        }
        return slots;
    }

    /**
     * Check if compare bar should be visible
     * @returns {boolean}
     */
    isCompareBarVisible() {
        return this.state.hasSearched && this.state.filteredProducts.length > 0;
    }

    /**
     * Check if compare bar is collapsed
     * @returns {boolean}
     */
    isCompareBarCollapsed() {
        return this.state.compareBarCollapsed;
    }

    /**
     * Toggle compare bar collapsed state
     */
    toggleCompareBar() {
        this.state.compareBarCollapsed = !this.state.compareBarCollapsed;
    }

    /**
     * Check if compare button should be enabled
     * @returns {boolean}
     */
    canCompare() {
        return this.state.selectedProducts.length === 2;
    }

    /**
     * Get remaining selection count
     * @returns {number}
     */
    getRemainingSlots() {
        return 2 - this.state.selectedProducts.length;
    }

    /**
     * Clear all selected products
     */
    clearComparison() {
        this.state.selectedProducts = [];
        this.state.compareBarCollapsed = false;
    }

    /**
     * Submit comparison - opens modal first, then async AI call
     */
    async submitComparison() {
        if (!this.canCompare()) {
            return;
        }

        console.log("Starting AI comparison for:", this.state.selectedProducts);

        // Reset states
        this.state.isComparing = true;
        this.state.compareError = null;
        this.state.aiCompareResult = null;

        // Open modal immediately to show parameter comparison
        this.state.showCompareModal = true;

        // Async AI call
        this._fetchAiRecommendation();
    }

    /**
     * Fetch AI recommendation asynchronously
     */
    async _fetchAiRecommendation() {
        try {
            const result = await this.rpc('/ai_search/product/ai_compare', {
                products: this.state.selectedProducts.map(p => ({
                    id: p.id,
                    name: p.name,
                    price: p.price,
                    short_description: p.subtitle || '',
                    compare_selling_points: p.compareSellingPoints || '',
                    compare_target_people: p.compareTargetPeople || '',
                    compare_scenes: p.compareScenes || '',
                    compare_attributes: p.compareAttributes || '[]',
                    compare_highlights: p.compareHighlights || '',
                    compare_warranty: p.compareWarranty || '',
                })),
            });

            if (result.success && result.comparison) {
                console.log("AI comparison result:", result.comparison);
                this.state.aiCompareResult = result.comparison;
            } else {
                this.state.compareError = result.error || '对比分析失败';
            }
        } catch (e) {
            console.error("Compare API error:", e);
            this.state.compareError = '网络错误，请重试';
        } finally {
            this.state.isComparing = false;
        }
    }

    /**
     * Open compare modal
     */
    openCompareModal() {
        if (this.canCompare()) {
            this.state.showCompareModal = true;
        }
    }

    /**
     * Close compare modal
     */
    closeCompareModal() {
        this.state.showCompareModal = false;
    }

    /**
     * Get AI comparison result for template
     * @returns {Object|null}
     */
    getAiCompareResult() {
        return this.state.aiCompareResult;
    }

    /**
     * Check if comparing is in progress
     * @returns {boolean}
     */
    isComparing() {
        return this.state.isComparing;
    }

    /**
     * Get compare error
     * @returns {string|null}
     */
    getCompareError() {
        return this.state.compareError;
    }

    // ==================== Helpers ====================

    /**
     * Toggle AI search mode
     */
    toggleAiMode() {
        this.state.aiMode = !this.state.aiMode;
    }

    /**
     * Get AI toggle class
     * @returns {string}
     */
    getAiToggleClass() {
        return this.state.aiMode ? "toggle-switch active" : "toggle-switch";
    }

    /**
     * Format price for display
     * @param {number} price
     * @returns {string}
     */
    formatPrice(price) {
        if (!price) return '0';
        return price.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    /**
     * Parse JSON string safely
     * @param {string} jsonStr
     * @returns {Array}
     */
    parseJson(jsonStr) {
        if (!jsonStr) return [];
        try {
            return JSON.parse(jsonStr);
        } catch (e) {
            console.warn("JSON parse error:", e);
            return [];
        }
    }

    /**
     * Get category count
     * @param {string} categoryName
     * @returns {number}
     */
    getCategoryCount(categoryName) {
        const cat = this.state.categories.find(c => c.name === categoryName);
        return cat ? cat.count : 0;
    }
}

registry.category("actions").add("ai_dify_search_page", AiSearchPage);
