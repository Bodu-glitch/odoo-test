from odoo import api, fields, models


class HelpdeskTeam(models.Model):
    _name = 'helpdesk.team'
    _description = 'Helpdesk Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    description = fields.Text('Description', translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True)
    member_ids = fields.Many2many('res.users', string='Members',
                                   domain="[('share', '=', False)]")
    visibility = fields.Selection([
        ('invited_internal', 'Invited internal users (private)'),
        ('all_internal', 'All internal users (company)'),
        ('portal_all', 'Invited portal users and all internal users (public)'),
    ], string='Visibility', default='portal_all', required=True)

    use_alias = fields.Boolean('Email Alias', default=True)
    alias_name = fields.Char('Alias Name')
    alias_email = fields.Char('Alias Email', compute='_compute_alias_email')

    use_website_form = fields.Boolean('Website Form', default=True)
    use_sla = fields.Boolean('SLA Policies')

    stage_ids = fields.Many2many(
        'helpdesk.stage', 'helpdesk_team_stage_rel', 'team_id', 'stage_id',
        string='Stages',
    )
    ticket_ids = fields.One2many('helpdesk.ticket', 'team_id', string='Tickets')
    sla_policy_ids = fields.One2many('helpdesk.sla', 'team_id', string='SLA Policy List')

    ticket_count = fields.Integer(compute='_compute_ticket_stats', store=False)
    open_ticket_count = fields.Integer(compute='_compute_ticket_stats', store=False)
    urgent_ticket_count = fields.Integer(compute='_compute_ticket_stats', store=False)
    unassigned_ticket_count = fields.Integer(compute='_compute_ticket_stats', store=False)
    closed_ticket_count = fields.Integer(compute='_compute_ticket_stats', store=False)
    sla_policy_count = fields.Integer(compute='_compute_sla_policy_count', store=False)

    @api.depends('alias_name')
    def _compute_alias_email(self):
        domain = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.domain', '')
        for team in self:
            if team.alias_name and domain:
                team.alias_email = f'{team.alias_name}@{domain}'
            else:
                team.alias_email = team.alias_name or ''

    def _compute_ticket_stats(self):
        Ticket = self.env['helpdesk.ticket']
        for team in self:
            all_tickets = Ticket.search([('team_id', '=', team.id)])
            open_tickets = all_tickets.filtered(lambda t: not t.stage_id.is_close)
            team.ticket_count = len(all_tickets)
            team.open_ticket_count = len(open_tickets)
            team.urgent_ticket_count = len(open_tickets.filtered(lambda t: t.priority == '3'))
            team.unassigned_ticket_count = len(open_tickets.filtered(lambda t: not t.user_id))
            team.closed_ticket_count = len(all_tickets.filtered(lambda t: t.stage_id.is_close))

    def _compute_sla_policy_count(self):
        for team in self:
            team.sla_policy_count = len(team.sla_policy_ids)

    @api.model
    def _get_default_stage_ids(self):
        return self.env['helpdesk.stage'].search([('team_ids', '=', False)])

    def action_open_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tickets',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'kanban,list,form',
            'domain': [('team_id', '=', self.id)],
            'context': {'default_team_id': self.id},
        }

    def action_open_sla_policies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SLA Policies',
            'res_model': 'helpdesk.sla',
            'view_mode': 'list,form',
            'domain': [('team_id', '=', self.id)],
            'context': {'default_team_id': self.id},
        }
