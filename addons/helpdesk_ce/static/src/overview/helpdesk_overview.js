/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class HelpdeskOverview extends Component {
    static template = "helpdesk_ce.HelpdeskOverview";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");
        this.state = useState({
            teams: [],
            myStats: {
                total: 0,
                high_priority: 0,
                urgent: 0,
                avg_open: "0:00",
                closed_today: 0,
            },
        });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        const [teams, myStats] = await Promise.all([
            this._loadTeams(),
            this._loadMyStats(),
        ]);
        this.state.teams = teams;
        this.state.myStats = myStats;
    }

    async _loadTeams() {
        return await this.orm.searchRead(
            "helpdesk.team",
            [["active", "=", true]],
            ["id", "name", "alias_email", "open_ticket_count",
             "unassigned_ticket_count", "urgent_ticket_count", "closed_ticket_count"],
        );
    }

    async _loadMyStats() {
        const uid = this.user.userId;
        const tickets = await this.orm.searchRead(
            "helpdesk.ticket",
            [["user_id", "=", uid], ["stage_id.is_close", "=", false]],
            ["id", "priority", "open_hours"],
        );
        const total = tickets.length;
        const urgent = tickets.filter((t) => t.priority === "3").length;
        const high_priority = tickets.filter((t) => ["2", "3"].includes(t.priority)).length;
        const avgHours = total
            ? tickets.reduce((s, t) => s + (t.open_hours || 0), 0) / total
            : 0;
        const h = Math.floor(avgHours);
        const m = Math.round((avgHours - h) * 60);
        return {
            total,
            urgent,
            high_priority,
            avg_open: `${h}:${String(m).padStart(2, "0")}`,
            closed_today: 0,
        };
    }

    openTeamTickets(teamId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tickets",
            res_model: "helpdesk.ticket",
            view_mode: "kanban,tree,form",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["team_id", "=", teamId]],
            context: { default_team_id: teamId },
        });
    }

    openMyTickets(minPriority) {
        const domain = [["user_id", "=", this.user.userId]];
        if (minPriority) {
            domain.push(["priority", ">=", minPriority]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Tickets",
            res_model: "helpdesk.ticket",
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain,
        });
    }
}

registry.category("actions").add("helpdesk_ce.overview", HelpdeskOverview);
