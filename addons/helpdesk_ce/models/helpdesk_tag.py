from odoo import fields, models


class HelpdeskTag(models.Model):
    _name = 'helpdesk.tag'
    _description = 'Helpdesk Tag'
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index')
    team_ids = fields.Many2many('helpdesk.team', string='Teams')
