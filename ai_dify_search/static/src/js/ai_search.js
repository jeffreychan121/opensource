/**
 * AI Dify Search - Frontend JavaScript
 * @odoo-module ai_dify_search.ai_search
 */

(function () {
    'use strict';

    /**
     * AI Search Component
     * 负责与 Odoo 后端通信并管理 UI 状态
     */
    var AiSearch = {
        // 状态
        state: {
            sessionKey: null,
            conversationId: null,
            isLoading: false,
            lastQuery: null,
            lastResult: null,
            followupEnabled: true,
        },

        // DOM 元素引用
        elements: {
            container: '#ai_search_container',
            input: '#ai_search_input',
            submitBtn: '#ai_search_submit',
            clearBtn: '#ai_search_clear',
            loading: '#ai_search_loading',
            results: '#ai_search_results',
            chips: '#ai_search_chips',
            summary: '#ai_search_summary',
            products: '#ai_search_products',
            refineBox: '#ai_search_refine_box',
            refineInput: '#ai_search_refine_input',
            refineSubmit: '#ai_search_refine_submit',
            error: '#ai_search_error',
        },

        /**
         * 初始化
         */
        init: function () {
            var self = this;

            // 绑定事件
            $(this.elements.submitBtn).on('click', function (e) {
                e.preventDefault();
                self.handleSearch();
            });

            $(this.elements.clearBtn).on('click', function (e) {
                e.preventDefault();
                self.handleClear();
            });

            $(this.elements.refineSubmit).on('click', function (e) {
                e.preventDefault();
                self.handleRefine();
            });

            // 回车键搜索
            $(this.elements.input).on('keypress', function (e) {
                if (e.which === 13) {
                    e.preventDefault();
                    self.handleSearch();
                }
            });

            // 回车键追问
            $(this.elements.refineInput).on('keypress', function (e) {
                if (e.which === 13) {
                    e.preventDefault();
                    self.handleRefine();
                }
            });

            // 初始化 session
            this.loadSession();

            console.log('AI Search initialized');
        },

        /**
         * 加载或创建 session
         */
        loadSession: function () {
            // 从 localStorage 获取 session key
            var stored = localStorage.getItem('ai_search_session');
            if (stored) {
                try {
                    var session = JSON.parse(stored);
                    this.state.sessionKey = session.session_key;
                    this.state.conversationId = session.conversation_id;
                } catch (e) {
                    console.warn('Invalid stored session');
                }
            }
        },

        /**
         * 保存 session
         */
        saveSession: function (sessionKey, conversationId) {
            this.state.sessionKey = sessionKey;
            this.state.conversationId = conversationId;
            localStorage.setItem('ai_search_session', JSON.stringify({
                session_key: sessionKey,
                conversation_id: conversationId,
            }));
        },

        /**
         * 处理搜索请求
         */
        handleSearch: function () {
            var query = $(this.elements.input).val().trim();
            if (!query) {
                this.showError('请输入搜索内容');
                return;
            }

            if (this.state.isLoading) {
                return;
            }

            this.executeSearch(query);
        },

        /**
         * 执行搜索
         */
        executeSearch: function (query) {
            var self = this;
            this.state.isLoading = true;
            this.state.lastQuery = query;

            // 显示 loading
            this.showLoading(true);
            this.hideError();
            this.hideResults();

            var postData = {
                query: query,
                lang: this.getLang(),
            };

            if (this.state.sessionKey) {
                postData.session_key = this.state.sessionKey;
            }

            $.ajax({
                url: '/ai_search/query',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(postData),
                timeout: 60000, // 60 秒超时
            })
            .done(function (response) {
                self.handleSearchResponse(response);
            })
            .fail(function (xhr, status, error) {
                self.handleSearchError(xhr, status, error);
            })
            .always(function () {
                self.state.isLoading = false;
                self.showLoading(false);
            });
        },

        /**
         * 处理搜索响应
         */
        handleSearchResponse: function (response) {
            if (!response.success) {
                this.showError(response.error || '搜索失败，请重试');
                return;
            }

            // 保存 session
            if (response.session_key) {
                this.saveSession(response.session_key, response.conversation_id);
            }

            // 更新状态
            this.state.lastResult = response;
            this.state.followupEnabled = response.followup_enabled !== false;

            // 显示结果
            this.showResults(response);
        },

        /**
         * 处理搜索错误
         */
        handleSearchError: function (xhr, status, error) {
            var message = '网络错误，请检查连接后重试';
            if (status === 'timeout') {
                message = '请求超时，请稍后重试';
            } else if (xhr.responseJSON && xhr.responseJSON.error) {
                message = xhr.responseJSON.error;
            }
            this.showError(message);
        },

        /**
         * 显示结果
         */
        showResults: function (response) {
            var self = this;

            // 隐藏原始商品列表
            if ($('#products_grid').length) {
                $('#products_grid').hide();
            }

            // 显示结果区域
            $(this.elements.results).show();

            // 显示清除按钮
            $(this.elements.clearBtn).show();

            // 渲染意图 chips
            this.renderChips(response.parsed_intent);

            // 渲染总结
            this.renderSummary(response.summary, response.fallback_used);

            // 渲染商品列表
            this.renderProducts(response.products);

            // 显示/隐藏追问框
            if (this.state.followupEnabled && !response.fallback_used) {
                $(this.elements.refineBox).show();
                $(this.elements.refineInput).val('').focus();
            } else {
                $(this.elements.refineBox).hide();
            }
        },

        /**
         * 渲染意图 chips
         */
        renderChips: function (parsedIntent) {
            var html = '';
            var self = this;

            if (!parsedIntent) {
                $(this.elements.chips).html('').hide();
                return;
            }

            $(this.elements.chips).show();

            // 价格
            if (parsedIntent.budget_min || parsedIntent.budget_max) {
                var priceText = '';
                if (parsedIntent.budget_min && parsedIntent.budget_max) {
                    priceText = parsedIntent.budget_min + ' - ' + parsedIntent.budget_max + '元';
                } else if (parsedIntent.budget_max) {
                    priceText = parsedIntent.budget_max + '元以内';
                } else if (parsedIntent.budget_min) {
                    priceText = parsedIntent.budget_min + '元以上';
                }
                html += '<span class="ai_search_chip badge bg-success me-1">✓ ' + priceText + '</span>';
            }

            // 包含的颜色
            if (parsedIntent.color_include && parsedIntent.color_include.length) {
                parsedIntent.color_include.forEach(function (color) {
                    html += '<span class="ai_search_chip badge bg-success me-1">✓ ' + color + '</span>';
                });
            }

            // 排除的颜色
            if (parsedIntent.color_exclude && parsedIntent.color_exclude.length) {
                parsedIntent.color_exclude.forEach(function (color) {
                    html += '<span class="ai_search_chip badge bg-danger me-1">✗ ' + color + '</span>';
                });
            }

            // 品牌
            if (parsedIntent.brand_include && parsedIntent.brand_include.length) {
                parsedIntent.brand_include.forEach(function (brand) {
                    html += '<span class="ai_search_chip badge bg-success me-1">✓ ' + brand + '</span>';
                });
            }

            if (parsedIntent.brand_exclude && parsedIntent.brand_exclude.length) {
                parsedIntent.brand_exclude.forEach(function (brand) {
                    html += '<span class="ai_search_chip badge bg-danger me-1">✗ ' + brand + '</span>';
                });
            }

            // 必须有
            if (parsedIntent.must_have && parsedIntent.must_have.length) {
                parsedIntent.must_have.forEach(function (item) {
                    html += '<span class="ai_search_chip badge bg-info me-1">' + item + '</span>';
                });
            }

            // 场景
            if (parsedIntent.use_case && parsedIntent.use_case.length) {
                parsedIntent.use_case.forEach(function (use) {
                    html += '<span class="ai_search_chip badge bg-secondary me-1">' + use + '</span>';
                });
            }

            // 季节
            if (parsedIntent.season) {
                html += '<span class="ai_search_chip badge bg-warning me-1">' + parsedIntent.season + '</span>';
            }

            // 关键词
            if (parsedIntent.keywords && parsedIntent.keywords.length) {
                parsedIntent.keywords.slice(0, 3).forEach(function (kw) {
                    if (kw.length < 20) {
                        html += '<span class="ai_search_chip badge bg-light text-dark me-1">' + kw + '</span>';
                    }
                });
            }

            $(this.elements.chips).html(html);
        },

        /**
         * 渲染总结
         */
        renderSummary: function (summary, fallbackUsed) {
            if (!summary) {
                $(this.elements.summary).hide();
                return;
            }

            $(this.elements.summary).show();

            var alertClass = fallbackUsed ? 'alert-warning' : 'alert-info';
            $(this.elements.summary).attr('class', 'ai_search_summary alert ' + alertClass);
            $(this.elements.summary).html(summary);
        },

        /**
         * 渲染商品列表
         */
        renderProducts: function (products) {
            var html = '';

            if (!products || products.length === 0) {
                html = '<div class="alert alert-warning">未找到匹配的商品，请尝试其他关键词</div>';
            } else {
                html = '<div class="row">';
                var self = this;

                products.forEach(function (product) {
                    html += self.renderProductCard(product);
                });

                html += '</div>';
            }

            $(this.elements.products).html(html);
        },

        /**
         * 渲染单个商品卡片
         */
        renderProductCard: function (product) {
            var imageUrl = product.image_url || '/website_sale/static/src/img/plhdr.gif';
            var shortDesc = product.short_description || '';
            if (shortDesc.length > 80) {
                shortDesc = shortDesc.substring(0, 80) + '...';
            }

            var attrs = product.attributes || [];
            var categories = product.category_names || [];
            var price = product.price || 0;

            var badges = '';
            categories.forEach(function (cat) {
                badges += '<span class="badge bg-secondary me-1">' + _.escape(cat) + '</span>';
            });
            attrs.forEach(function (attr) {
                badges += '<span class="badge bg-light text-dark border me-1">' + _.escape(attr) + '</span>';
            });

            return '<div class="col-12 col-md-6 mb-3">' +
                '<div class="card ai_search_product_card h-100">' +
                '<div class="row g-0">' +
                '<div class="col-4">' +
                '<img src="' + imageUrl + '" class="img-fluid rounded-start" alt="' + _.escape(product.name) + '"' +
                'onerror="this.src=\'/website_sale/static/src/img/plhdr.gif\'"/>' +
                '</div>' +
                '<div class="col-8">' +
                '<div class="card-body">' +
                '<h5 class="card-title">' +
                '<a href="' + (product.url || '#') + '">' + _.escape(product.name) + '</a>' +
                '</h5>' +
                '<p class="card-text text-muted small">' + _.escape(shortDesc) + '</p>' +
                '<div class="mb-2">' + badges + '</div>' +
                '<p class="card-text">' +
                '<strong class="text-danger h5">' + price.toFixed(2) + (product.currency === 'CNY' ? '元' : '') + '</strong>' +
                '</p>' +
                '</div>' +
                '</div>' +
                '</div>' +
                '</div>' +
                '</div>';
        },

        /**
         * 处理追问
         */
        handleRefine: function () {
            var query = $(this.elements.refineInput).val().trim();
            if (!query) {
                return;
            }

            // 将追问追加到原始查询
            var fullQuery = this.state.lastQuery + '，' + query;
            this.executeSearch(fullQuery);
        },

        /**
         * 清除搜索
         */
        handleClear: function () {
            // 清除状态
            this.state.lastQuery = null;
            this.state.lastResult = null;
            this.state.sessionKey = null;
            this.state.conversationId = null;

            // 清除存储
            localStorage.removeItem('ai_search_session');

            // 清除输入
            $(this.elements.input).val('');
            $(this.elements.clearBtn).hide();

            // 隐藏结果区域
            this.hideResults();

            // 显示原始商品列表
            if ($('#products_grid').length) {
                $('#products_grid').show();
            }
        },

        /**
         * 显示/隐藏 loading
         */
        showLoading: function (show) {
            if (show) {
                $(this.elements.loading).show();
                $(this.elements.submitBtn).prop('disabled', true);
            } else {
                $(this.elements.loading).hide();
                $(this.elements.submitBtn).prop('disabled', false);
            }
        },

        /**
         * 显示结果区域
         */
        showResults: function () {
            $(this.elements.results).show();
        },

        /**
         * 隐藏结果区域
         */
        hideResults: function () {
            $(this.elements.results).hide();
            $(this.elements.chips).html('').hide();
            $(this.elements.summary).html('').hide();
            $(this.elements.products).html('');
            $(this.elements.refineBox).hide();
        },

        /**
         * 显示错误
         */
        showError: function (message) {
            $(this.elements.error).text(message).show();
        },

        /**
         * 隐藏错误
         */
        hideError: function () {
            $(this.elements.error).hide();
        },

        /**
         * 获取当前语言
         */
        getLang: function () {
            // 从 DOM 或页面获取语言设置
            var lang = 'zh_CN';
            var container = $(this.elements.container);
            if (container.data('lang')) {
                lang = container.data('lang');
            }
            return lang;
        },
    };

    // 页面加载完成后初始化
    $(document).ready(function () {
        // 延迟初始化，确保 DOM 完全加载
        setTimeout(function () {
            AiSearch.init();
        }, 100);
    });

    // 暴露到全局
    window.AiSearch = AiSearch;

})();
