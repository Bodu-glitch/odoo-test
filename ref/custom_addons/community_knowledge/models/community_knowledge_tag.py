from odoo import fields, models


class CommunityKnowledgeTag(models.Model):
    _name = 'community.knowledge.tag'
    _description = 'Knowledge Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)
