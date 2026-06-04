from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KnowledgeFolder(models.Model):
    _name = 'knowledge.folder'
    _description = 'Knowledge Folder'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'name'
    _order = 'sequence, name'

    name = fields.Char('Name', required=True)
    icon = fields.Char('Icon', default='📁')

    parent_id = fields.Many2one(
        'knowledge.folder', 'Parent Folder',
        ondelete='cascade', index=True,
    )
    child_ids = fields.One2many('knowledge.folder', 'parent_id', 'Sub-folders')
    parent_path = fields.Char(index=True, unaccent=False)

    article_ids = fields.One2many('knowledge.article', 'folder_id', 'Articles')
    article_count = fields.Integer(compute='_compute_article_count', string='Article Count')

    sequence = fields.Integer(default=10)

    @api.depends('article_ids')
    def _compute_article_count(self):
        for folder in self:
            folder.article_count = len(folder.article_ids)

    @api.constrains('parent_id')
    def _check_folder_recursion(self):
        if not self._check_recursion():
            raise ValidationError('A folder cannot be its own ancestor (circular reference).')

    def action_move_to(self, new_parent_id):
        """Move this folder under new_parent_id (pass False for root)."""
        self.ensure_one()
        self.write({'parent_id': new_parent_id or False})
