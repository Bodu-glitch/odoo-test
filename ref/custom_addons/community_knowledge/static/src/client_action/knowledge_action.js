import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, markup, onWillStart, useRef, useState } from "@odoo/owl";

const ARTICLE_FIELDS = [
    "name",
    "complete_name",
    "body",
    "parent_id",
    "child_ids",
    "access_mode",
    "favorite_user_ids",
    "owner_id",
    "write_date",
];

export class CommunityKnowledgeAction extends Component {
    static template = "community_knowledge.KnowledgeAction";
    static props = { ...standardActionServiceProps };
    static path = "knowledge";
    static displayName = "Knowledge";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.editorRef = useRef("editor");

        this.state = useState({
            articles: [],
            currentId: false,
            query: "",
            saving: false,
        });

        onWillStart(async () => {
            await this.loadArticles();
        });
    }

    async loadArticles(preferredId) {
        const articles = await this.orm.searchRead(
            "community.knowledge.article",
            [["active", "=", true]],
            ARTICLE_FIELDS,
            { order: "sequence, complete_name, id" }
        );
        this.state.articles = articles;
        if (preferredId && articles.some((article) => article.id === preferredId)) {
            this.state.currentId = preferredId;
        } else if (!this.currentArticle && articles.length) {
            this.state.currentId = articles[0].id;
        } else if (!articles.length) {
            this.state.currentId = false;
        }
    }

    get currentArticle() {
        return this.state.articles.find((article) => article.id === this.state.currentId);
    }

    get currentBody() {
        return markup(this.currentArticle?.body || "<p><br></p>");
    }

    get filteredArticles() {
        const query = this.state.query.trim().toLowerCase();
        if (!query) {
            return this.state.articles;
        }
        return this.state.articles.filter((article) =>
            `${article.name || ""} ${article.complete_name || ""}`.toLowerCase().includes(query)
        );
    }

    get favoriteArticles() {
        return this.filteredArticles.filter((article) => article.favorite_user_ids.length);
    }

    get workspaceArticles() {
        return this.filteredArticles.filter((article) => article.access_mode === "internal");
    }

    get privateArticles() {
        return this.filteredArticles.filter((article) => article.access_mode === "private");
    }

    selectArticle(article) {
        this.state.currentId = article.id;
    }

    onSearch(ev) {
        this.state.query = ev.target.value;
    }

    async createArticle() {
        const [articleId] = await this.orm.create("community.knowledge.article", [
            {
                name: "Untitled",
                access_mode: "internal",
                body: "<h1>Untitled</h1><p>Start writing...</p>",
            },
        ]);
        await this.loadArticles(articleId);
    }

    async saveTitle(ev) {
        const article = this.currentArticle;
        const name = ev.target.value.trim() || "Untitled";
        if (!article || article.name === name) {
            return;
        }
        await this.saveArticle({ name });
    }

    async saveBody() {
        const article = this.currentArticle;
        const editor = this.editorRef.el;
        if (!article || !editor) {
            return;
        }
        const body = editor.innerHTML;
        if ((article.body || "") === body) {
            return;
        }
        await this.saveArticle({ body });
    }

    async saveArticle(values) {
        const article = this.currentArticle;
        if (!article) {
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.write("community.knowledge.article", [article.id], values);
            Object.assign(article, values);
        } catch (error) {
            this.notification.add(error?.data?.message || "Could not save article.", {
                type: "danger",
            });
            await this.loadArticles(article.id);
        } finally {
            this.state.saving = false;
        }
    }

    async toggleFavorite() {
        const article = this.currentArticle;
        if (!article) {
            return;
        }
        await this.orm.call("community.knowledge.article", "action_toggle_favorite", [[article.id]]);
        await this.loadArticles(article.id);
    }

    openArticles() {
        this.actionService.doAction("community_knowledge.action_community_knowledge_articles");
    }

    openTrash() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Trash",
            res_model: "community.knowledge.article",
            views: [[false, "list"], [false, "form"]],
            domain: [["active", "=", false]],
            context: { active_test: false },
        });
    }
}

registry.category("actions").add("community_knowledge.home", CommunityKnowledgeAction);
