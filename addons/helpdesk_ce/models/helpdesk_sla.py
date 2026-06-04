from odoo import api, fields, models


class HelpdeskSla(models.Model):
    _name = 'helpdesk.sla'
    _description = 'Helpdesk SLA Policy'
    _order = 'name'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    active = fields.Boolean(default=True)
    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', required=True, ondelete='cascade')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Minimum Priority', default='0')
    tag_ids = fields.Many2many('helpdesk.tag', string='Tags')
    partner_ids = fields.Many2many('res.partner', string='Customers')
    stage_id = fields.Many2one(
        'helpdesk.stage', string='Reach Stage', required=True,
        domain="[('team_ids', 'in', team_id)]",
    )
    time = fields.Float('Within', default=0.0, help='Time in hours to reach the target stage.')
    exclude_stage_ids = fields.Many2many(
        'helpdesk.stage', 'helpdesk_sla_exclude_stage_rel', 'sla_id', 'stage_id',
        string='Excluding Stages',
        domain="[('team_ids', 'in', team_id)]",
    )


class HelpdeskSlaStatus(models.Model):
    _name = 'helpdesk.sla.status'
    _description = 'Helpdesk SLA Status'
    _order = 'deadline ASC'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', required=True, ondelete='cascade', index=True)
    sla_id = fields.Many2one('helpdesk.sla', string='SLA Policy', required=True, ondelete='cascade')
    deadline = fields.Datetime('Deadline')
    reached_datetime = fields.Datetime('Reached Date')
    status = fields.Selection([
        ('failed', 'Failed'),
        ('in_progress', 'In Progress'),
        ('reached', 'Reached'),
    ], string='Status', compute='_compute_status', store=True)

    @api.depends('deadline', 'reached_datetime')
    def _compute_status(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.reached_datetime:
                rec.status = 'reached' if (not rec.deadline or rec.reached_datetime <= rec.deadline) else 'failed'
            elif rec.deadline and rec.deadline < now:
                rec.status = 'failed'
            else:
                rec.status = 'in_progress'
