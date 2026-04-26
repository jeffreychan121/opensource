/** @odoo-module **/
import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AiSearchMvpPage extends Component {
    static template = "ai_dify_search_mvp.AiSearchMvpPage";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            query: "",
            aiMode: true,  // true = AI mode (Dify), false = simple keyword search
            isLoading: false,
            hasSearched: false,
            products: [],
            summary: "",
            parsedIntent: {},
            fallbackUsed: false,
            error: null,
            sessionKey: null,
            chips: [],
        });

        this.searchInputRef = useRef("searchInput");
    }

    onSearchKeypress(ev) {
        if (ev.key === "Enter") {
            this.onSearch();
        }
    }

    async onSearch() {
        const query = this.searchInputRef.el?.value || this.state.query;
        if (!query.trim()) {
            return;
        }

        this.state.isLoading = true;
        this.state.error = null;

        try {
            const result = await this.rpc("/ai_search_mvp/query", {
                query: query,
                session_key: this.state.sessionKey,
                lang: "zh_CN",
                simple_mode: !this.state.aiMode,  // Backend uses simple_mode flag (inverted)
            });

            if (result.success) {
                this.state.products = result.products || [];
                this.state.summary = result.summary || "";
                this.state.parsedIntent = result.parsed_intent || {};
                this.state.fallbackUsed = result.fallback_used || false;
                this.state.sessionKey = result.session_key;
                this.state.hasSearched = true;
                this.state.chips = this.buildChips(result.parsed_intent);
            } else {
                this.state.error = result.error || "Search failed";
                this.state.hasSearched = true;
            }
        } catch (e) {
            this.state.error = "Request failed: " + (e.message || String(e));
            this.state.hasSearched = true;
        } finally {
            this.state.isLoading = false;
        }
    }

    toggleAiMode() {
        this.state.aiMode = !this.state.aiMode;
    }

    getAiToggleClass() {
        return this.state.aiMode ? "toggle-switch active" : "toggle-switch";
    }

    buildChips(parsedIntent) {
        const chips = [];
        if (!parsedIntent) return chips;

        if (parsedIntent.category) {
            chips.push({ label: parsedIntent.category, type: "category" });
        }
        if (parsedIntent.budget_max) {
            chips.push({ label: `Budget ≤${parsedIntent.budget_max}`, type: "budget" });
        }
        if (parsedIntent.budget_min) {
            chips.push({ label: `Budget ≥${parsedIntent.budget_min}`, type: "budget" });
        }
        if (parsedIntent.keywords && parsedIntent.keywords.length > 0) {
            parsedIntent.keywords.forEach(kw => {
                chips.push({ label: kw, type: "keyword" });
            });
        }
        return chips;
    }

    formatPrice(price) {
        if (!price) return "0";
        return parseFloat(price).toFixed(2);
    }

    getChipClass(chip) {
        const classes = {
            category: "chip-category",
            budget: "chip-budget",
            keyword: "chip-keyword",
        };
        return classes[chip.type] || "chip-default";
    }
}

registry.category("actions").add("ai_dify_search_mvp_page", AiSearchMvpPage);
