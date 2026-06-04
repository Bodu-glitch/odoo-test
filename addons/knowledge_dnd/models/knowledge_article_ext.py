from odoo import models, fields


class KnowledgeArticleExt(models.Model):
    _inherit = 'knowledge.article'

    folder_id = fields.Many2one(
        'knowledge.folder', 'Folder',
        index=True, ondelete='set null',
        tracking=True,
    )
