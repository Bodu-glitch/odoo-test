from odoo import fields, models


class HelpdeskStage(models.Model):
    _name = 'helpdesk.stage'
    _description = 'Helpdesk Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean('Folded in Kanban')
    is_close = fields.Boolean('Closing Stage', help='Tickets in this stage are considered closed.')
    team_ids = fields.Many2many(
        'helpdesk.team', 'helpdesk_team_stage_rel', 'stage_id', 'team_id',
        string='Teams',
    )
    template_id = fields.Many2one('mail.template', string='Email Template',
                                   domain="[('model', '=', 'helpdesk.ticket')]")
