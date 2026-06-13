/** @odoo-module **/

import { Component, useState, onWillStart, useRef, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";


// ═══════════════════════════════════════════════════════════════════════════════
// ArticleTreeItem — recursive sidebar node
// ═══════════════════════════════════════════════════════════════════════════════

class ArticleTreeItem extends Component {
    static template = "knowledge_dnd.ArticleTreeItem";
    static props = {
        node: Object,
        depth: { type: Number, optional: true },
        tree: Object,       // shared reactive state { selectedId, expanded, children }
        onSelect: Function,
        onPlus: Function,
        onExpand: Function,
    };

    get depth() { return this.props.depth || 0; }
    get isSelected() { return this.props.tree.selectedId === this.props.node.id; }
    get isExpanded() { return !!this.props.tree.expanded[this.props.node.id]; }
    get hasChildIds() { return this.props.node.child_ids && this.props.node.child_ids.length > 0; }
    get children() { return this.props.tree.children[this.props.node.id] || []; }

    async onExpandClick(ev) {
        ev.stopPropagation();
        await this.props.onExpand(this.props.node.id);
    }

    onSelectClick() {
        this.props.onSelect(this.props.node);
    }

    onPlusClick(ev) {
        ev.stopPropagation();
        this.props.onPlus(this.props.node);
    }
}
ArticleTreeItem.components = { ArticleTreeItem };


// ═══════════════════════════════════════════════════════════════════════════════
// KnowledgeApp — main client action
// ═══════════════════════════════════════════════════════════════════════════════

export class KnowledgeApp extends Component {
    static template = "knowledge_dnd.KnowledgeApp";
    static components = { ArticleTreeItem };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        // Shared sidebar tree state — reactive, passed to ArticleTreeItem as prop
        this.tree = useState({
            selectedId: null,
            expanded: {},   // { [articleId]: true | false }
            children: {},   // { [parentId]: [child nodes] }
        });

        this.state = useState({
            loading: false,
            article: null,      // full selected article data
            favorites: [],
            workspace: [],
            private: [],
            showList: true,
            allArticles: [],
            searchQuery: "",
            showCategoryMenu: false,
            showMoreMenu: false,
            showTrash: false,
            trashedArticles: [],
        });

        // Multi-select state for article list and trash view
        this.selection = useState({
            articleIds: [],
            trashIds: [],
        });

        // DOM refs for contenteditable title and innerHTML body
        this.titleRef = useRef("title");
        this.bodyRef  = useRef("body");

        // Sync body HTML only when switching to a different article (not on every body save)
        useEffect(() => {
            if (this.bodyRef.el) {
                this.bodyRef.el.innerHTML = this.state.article?.body || "";
            }
        }, () => [this.state.article?.id]);

        // Sync title text when selected article changes
        useEffect(() => {
            if (this.titleRef.el && this.state.article) {
                this.titleRef.el.textContent = this.state.article.name;
            }
        }, () => [this.state.article?.id]);

        onWillStart(() => this.loadSidebar());
    }

    // ── Data loading ──────────────────────────────────────────────────────────

    async loadSidebar() {
        const roots = await this.orm.searchRead(
            "knowledge.article",
            [["parent_id", "=", false], ["trashed", "=", false]],
            ["id", "name", "icon", "category", "is_favorite", "child_ids", "sequence"],
            { order: "sequence, name", limit: 300 },
        );
        this.state.favorites = roots.filter(a => a.is_favorite);
        this.state.workspace = roots.filter(a => a.category === "workspace");
        this.state.private   = roots.filter(a => a.category === "private");

        this.state.allArticles = await this.orm.searchRead(
            "knowledge.article",
            [["trashed", "=", false]],
            ["id", "name", "icon", "category", "parent_id", "author_id", "create_date", "is_favorite"],
            { order: "sequence, name", limit: 500 },
        );
    }

    async loadChildren(parentId) {
        // If already loaded, just toggle expand
        if (this.tree.children[parentId]) {
            this.tree.expanded[parentId] = !this.tree.expanded[parentId];
            return;
        }
        const children = await this.orm.searchRead(
            "knowledge.article",
            [["parent_id", "=", parentId], ["trashed", "=", false]],
            ["id", "name", "icon", "category", "is_favorite", "child_ids", "sequence"],
            { order: "sequence, name" },
        );
        this.tree.children[parentId] = children;
        this.tree.expanded[parentId] = true;
    }

    async _forceReloadChildren(parentId) {
        const children = await this.orm.searchRead(
            "knowledge.article",
            [["parent_id", "=", parentId], ["trashed", "=", false]],
            ["id", "name", "icon", "category", "is_favorite", "child_ids", "sequence"],
            { order: "sequence, name" },
        );
        this.tree.children[parentId] = children;
        this.tree.expanded[parentId] = true;
    }

    // ── Selection ─────────────────────────────────────────────────────────────

    async selectArticle(node) {
        this.tree.selectedId = node.id;
        this.state.showList = false;
        this.state.loading = true;
        const [full] = await this.orm.read(
            "knowledge.article",
            [node.id],
            ["id", "name", "icon", "body", "category", "author_id", "write_date", "is_favorite", "parent_id"],
        );
        this.state.article = full;
        this.state.loading = false;
    }

    goHome() {
        this.tree.selectedId = null;
        this.state.showList = true;
        this.state.article = null;
    }

    // ── Create article — inline, stays within KnowledgeApp ───────────────────

    async createRootArticle() {
        const [id] = await this.orm.create("knowledge.article", [{
            name: "Untitled",
            category: "private",
        }]);
        await this.loadSidebar();
        await this.selectArticle({ id });
        this._focusTitle();
    }

    async createCategoryArticle(category) {
        const [id] = await this.orm.create("knowledge.article", [{
            name: "Untitled",
            category: category,
        }]);
        await this.loadSidebar();
        await this.selectArticle({ id });
        this._focusTitle();
    }

    async changeCategory(newCategory) {
        if (!this.state.article) return;
        await this.orm.write("knowledge.article", [this.state.article.id], { category: newCategory });
        this.state.article = { ...this.state.article, category: newCategory };
        this.state.showCategoryMenu = false;
        await this.loadSidebar();
    }

    toggleCategoryMenu(ev) {
        if (ev) ev.stopPropagation();
        this.state.showCategoryMenu = !this.state.showCategoryMenu;
    }

    closeCategoryMenu() {
        this.state.showCategoryMenu = false;
    }

    // ── More options menu ─────────────────────────────────────────────────────

    toggleMoreMenu(ev) {
        if (ev) ev.stopPropagation();
        this.state.showMoreMenu = !this.state.showMoreMenu;
    }

    closeMoreMenu() {
        this.state.showMoreMenu = false;
    }

    async sendToTrash() {
        if (!this.state.article) return;
        await this.orm.call("knowledge.article", "action_send_to_trash", [[this.state.article.id]]);
        this.state.showMoreMenu = false;
        this.goHome();
        await this.loadSidebar();
    }

    // ── Trash view ────────────────────────────────────────────────────────────

    async openTrash() {
        this.state.showTrash = true;
        this.state.showList = false;
        this.state.article = null;
        this.tree.selectedId = null;
        await this._loadTrashedArticles();
    }

    async _loadTrashedArticles() {
        this.state.trashedArticles = await this.orm.searchRead(
            "knowledge.article",
            [["trashed", "=", true]],
            ["id", "name", "icon", "category", "author_id", "create_date", "parent_id", "is_favorite"],
            { order: "create_date desc", limit: 200, context: { active_test: false } },
        );
    }

    async restoreFromTrash(articleId) {
        await this.orm.call(
            "knowledge.article", "action_restore_from_trash", [[articleId]],
            { context: { active_test: false } },
        );
        await this._loadTrashedArticles();
        await this.loadSidebar();
    }

    async permanentDelete(articleId) {
        if (!window.confirm("Permanently delete this article? This cannot be undone.")) return;
        await this.orm.call(
            "knowledge.article", "action_permanent_delete", [[articleId]],
            { context: { active_test: false } },
        );
        await this._loadTrashedArticles();
    }

    closeTrash() {
        this.state.showTrash = false;
        this.state.showList = true;
    }

    async createChildArticle(parentNode) {
        const [id] = await this.orm.create("knowledge.article", [{
            name: "Untitled",
            parent_id: parentNode.id,
            category: parentNode.category,
        }]);
        // Force-reload children of parent so the new article appears expanded
        await this._forceReloadChildren(parentNode.id);
        await this.loadSidebar();
        await this.selectArticle({ id });
        this._focusTitle();
    }

    _focusTitle() {
        setTimeout(() => {
            const el = this.titleRef.el;
            if (!el) return;
            el.focus();
            try {
                const range = document.createRange();
                range.selectNodeContents(el);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
            } catch (_e) {}
        }, 80);
    }

    // ── Favorite toggle ───────────────────────────────────────────────────────

    async toggleFavorite() {
        if (!this.state.article) return;
        await this.orm.call("knowledge.article", "action_toggle_favorite", [[this.state.article.id]]);
        this.state.article = { ...this.state.article, is_favorite: !this.state.article.is_favorite };
        await this.loadSidebar();
    }

    // ── Inline title editing ──────────────────────────────────────────────────

    async saveTitle(ev) {
        const newName = ev.target.textContent.trim();
        if (!newName || newName === this.state.article.name) return;
        await this.orm.write("knowledge.article", [this.state.article.id], { name: newName });
        this.state.article = { ...this.state.article, name: newName };
        await this.loadSidebar();
    }

    onTitleKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            ev.target.blur();
        }
    }

    // ── Body editing ──────────────────────────────────────────────────────────

    onBodyInput() {
        // Auto-save 1.5s after user stops typing
        if (this._saveTimer) clearTimeout(this._saveTimer);
        this._saveTimer = setTimeout(() => this._flushBodySave(), 1500);
    }

    async saveBody() {
        if (this._saveTimer) {
            clearTimeout(this._saveTimer);
            this._saveTimer = null;
        }
        await this._flushBodySave();
    }

    async _flushBodySave() {
        const el = this.bodyRef.el;
        if (!el || !this.state.article) return;
        const body = el.innerHTML;
        if (body === (this.state.article.body || "")) return;
        await this.orm.write("knowledge.article", [this.state.article.id], { body });
        // Update locally without touching the DOM (avoid resetting caret position)
        this.state.article = { ...this.state.article, body };
    }

    // ── List helpers ──────────────────────────────────────────────────────────

    get filteredArticles() {
        const q = this.state.searchQuery.toLowerCase().trim();
        if (!q) return this.state.allArticles;
        return this.state.allArticles.filter(a => a.name.toLowerCase().includes(q));
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        try {
            return new Date(dateStr).toLocaleDateString(undefined, {
                day: "2-digit", month: "short", year: "numeric",
            });
        } catch {
            return dateStr;
        }
    }

    formatDateTime(dateStr) {
        if (!dateStr) return "";
        try {
            return new Date(dateStr).toLocaleDateString(undefined, {
                month: "short", day: "numeric",
                hour: "numeric", minute: "2-digit",
            });
        } catch {
            return dateStr;
        }
    }

    get articleIcon() {
        return this.state.article?.icon || "📄";
    }

    // ── Article list selection ────────────────────────────────────────────────

    get selectedArticleCount() { return this.selection.articleIds.length; }

    get allArticlesSelected() {
        const all = this.filteredArticles;
        return all.length > 0 && all.every(a => this.selection.articleIds.includes(a.id));
    }

    toggleArticleSelection(ev, id) {
        ev.stopPropagation();
        const idx = this.selection.articleIds.indexOf(id);
        if (idx >= 0) {
            this.selection.articleIds.splice(idx, 1);
        } else {
            this.selection.articleIds.push(id);
        }
    }

    toggleAllArticles(ev) {
        ev.stopPropagation();
        if (this.allArticlesSelected) {
            this.selection.articleIds = [];
        } else {
            this.selection.articleIds = this.filteredArticles.map(a => a.id);
        }
    }

    clearArticleSelection() {
        this.selection.articleIds = [];
    }

    async sendSelectedToTrash() {
        const ids = this.selection.articleIds.slice();
        if (!ids.length) return;
        await this.orm.call("knowledge.article", "action_send_to_trash", [ids]);
        this.selection.articleIds = [];
        await this.loadSidebar();
    }

    // ── Trash view selection ──────────────────────────────────────────────────

    get selectedTrashCount() { return this.selection.trashIds.length; }

    get allTrashSelected() {
        const all = this.state.trashedArticles;
        return all.length > 0 && all.every(a => this.selection.trashIds.includes(a.id));
    }

    toggleTrashSelection(ev, id) {
        ev.stopPropagation();
        const idx = this.selection.trashIds.indexOf(id);
        if (idx >= 0) {
            this.selection.trashIds.splice(idx, 1);
        } else {
            this.selection.trashIds.push(id);
        }
    }

    toggleAllTrash(ev) {
        ev.stopPropagation();
        if (this.allTrashSelected) {
            this.selection.trashIds = [];
        } else {
            this.selection.trashIds = this.state.trashedArticles.map(a => a.id);
        }
    }

    clearTrashSelection() {
        this.selection.trashIds = [];
    }

    async restoreSelectedFromTrash() {
        const ids = this.selection.trashIds.slice();
        if (!ids.length) return;
        await this.orm.call(
            "knowledge.article", "action_restore_from_trash", [ids],
            { context: { active_test: false } },
        );
        this.selection.trashIds = [];
        await this._loadTrashedArticles();
        await this.loadSidebar();
    }

    async deleteSelectedPermanently() {
        const ids = this.selection.trashIds.slice();
        if (!ids.length) return;
        if (!window.confirm(`Permanently delete ${ids.length} article(s)? This cannot be undone.`)) return;
        await this.orm.call(
            "knowledge.article", "action_permanent_delete", [ids],
            { context: { active_test: false } },
        );
        this.selection.trashIds = [];
        await this._loadTrashedArticles();
    }
}

registry.category("actions").add("knowledge_dnd.main", KnowledgeApp);
