from odoo import models, fields


class KnowledgeArticleMember(models.Model):
    _name = 'knowledge.article.member'
    _description = 'Knowledge Article Member'

    article_id = fields.Many2one(
        'knowledge.article', 'Article',
        required=True, ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    permission = fields.Selection([
        ('read', 'Can Read'),
        ('write', 'Can Edit'),
    ], required=True, default='read')
