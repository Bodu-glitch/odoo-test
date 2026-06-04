from odoo import api, fields, models


PRIORITY_SELECTION = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Urgent'),
]


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char('Subject', required=True, tracking=True)
    ticket_ref = fields.Char('Ticket Reference', readonly=True, copy=False, index=True)
    team_id = fields.Many2one(
        'helpdesk.team', string='Helpdesk Team', required=True,
        default=lambda self: self._default_team_id(),
        tracking=True,
    )
    stage_id = fields.Many2one(
        'helpdesk.stage', string='Stage', ondelete='restrict',
        group_expand='_read_group_stage_ids',
        copy=False, index=True, tracking=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Assigned to', tracking=True,
        domain="[('share', '=', False)]",
    )
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    partner_phone = fields.Char('Phone', compute='_compute_partner_phone',
                                 inverse='_set_partner_phone', store=True)
    priority = fields.Selection(PRIORITY_SELECTION, default='0', tracking=True, string='Priority')
    tag_ids = fields.Many2many('helpdesk.tag', string='Tags')
    description = fields.Html('Description')
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, tracking=True)
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready for Next Stage'),
        ('blocked', 'Blocked'),
    ], default='normal', tracking=True, string='Kanban State')
    close_date = fields.Datetime('Closed Date')
    open_hours = fields.Float('Hours Open', compute='_compute_open_hours', store=True)

    sla_status_ids = fields.One2many('helpdesk.sla.status', 'ticket_id', string='SLA Status')
    sla_deadline = fields.Datetime('SLA Deadline', compute='_compute_sla_deadline', store=True)
    sla_fail = fields.Boolean('Failed SLA', compute='_compute_sla_fail', store=True)

    @api.model
    def _default_team_id(self):
        team = self.env['helpdesk.team'].search([], limit=1)
        return team.id if team else False

    def _read_group_stage_ids(self, stages, domain, order):
        team_id = self._context.get('default_team_id')
        if team_id:
            team = self.env['helpdesk.team'].browse(team_id)
            return team.stage_ids.sorted('sequence')
        return stages.search([], order=order)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('ticket_ref'):
                vals['ticket_ref'] = self.env['ir.sequence'].next_by_code('helpdesk.ticket') or '/'
            if vals.get('team_id') and not vals.get('stage_id'):
                team = self.env['helpdesk.team'].browse(vals['team_id'])
                first_stage = team.stage_ids.sorted('sequence')[:1]
                if first_stage:
                    vals['stage_id'] = first_stage.id
        tickets = super().create(vals_list)
        for ticket in tickets:
            ticket._send_creation_email()
        return tickets

    def write(self, vals):
        if 'stage_id' in vals:
            stage = self.env['helpdesk.stage'].browse(vals['stage_id'])
            if stage.is_close:
                vals.setdefault('close_date', fields.Datetime.now())
            else:
                vals['close_date'] = False
        return super().write(vals)

    def _send_creation_email(self):
        template = self.env.ref('helpdesk_ce.mail_template_helpdesk_ticket_confirmation', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)

    @api.depends('partner_id')
    def _compute_partner_phone(self):
        for ticket in self:
            ticket.partner_phone = ticket.partner_id.phone or ''

    def _set_partner_phone(self):
        for ticket in self:
            if ticket.partner_id and ticket.partner_phone:
                ticket.partner_id.phone = ticket.partner_phone

    @api.depends('create_date', 'close_date')
    def _compute_open_hours(self):
        for ticket in self:
            if ticket.close_date and ticket.create_date:
                delta = ticket.close_date - ticket.create_date
                ticket.open_hours = delta.total_seconds() / 3600
            elif ticket.create_date:
                delta = fields.Datetime.now() - ticket.create_date
                ticket.open_hours = delta.total_seconds() / 3600
            else:
                ticket.open_hours = 0.0

    @api.depends('sla_status_ids.deadline')
    def _compute_sla_deadline(self):
        for ticket in self:
            deadlines = ticket.sla_status_ids.filtered(
                lambda s: s.status == 'in_progress' and s.deadline
            ).mapped('deadline')
            ticket.sla_deadline = min(deadlines) if deadlines else False

    @api.depends('sla_status_ids.status')
    def _compute_sla_fail(self):
        for ticket in self:
            ticket.sla_fail = any(s.status == 'failed' for s in ticket.sla_status_ids)

    def get_portal_url(self):
        self.ensure_one()
        return f'/my/tickets/{self.id}'

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = list(domain or [])
        if name:
            domain = ['|', ('name', operator, name), ('ticket_ref', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)
