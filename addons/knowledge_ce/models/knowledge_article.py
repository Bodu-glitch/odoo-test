from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KnowledgeArticle(models.Model):
    _name = 'knowledge.article'
    _description = 'Knowledge Article'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'name'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Title', required=True, default='New Article', tracking=True)
    icon = fields.Char('Emoji', default='📄')
    body = fields.Html('Content', sanitize=False)

    parent_id = fields.Many2one(
        'knowledge.article', 'Parent Article',
        ondelete='cascade', index=True,
    )
    child_ids = fields.One2many('knowledge.article', 'parent_id', 'Sub-articles')
    parent_path = fields.Char(index=True, unaccent=False)
    child_count = fields.Integer(compute='_compute_child_count', string='Children Count')

    sequence = fields.Integer(default=10)

    category = fields.Selection([
        ('private', 'Private'),
        ('shared', 'Shared'),
        ('workspace', 'Workspace'),
    ], string='Access', default='private', required=True, tracking=True)

    workspace_dimension = fields.Selection([
        ('hr',    'HR'),
        ('it',    'IT'),
        ('legal', 'Legal'),
        ('sales', 'Sales'),
        ('ops',   'Operations'),
    ], string='Workspace Dimension', tracking=True)

    tag_ids = fields.Many2many(
        'res.partner.category',
        'knowledge_article_tag_rel',
        'article_id',
        'tag_id',
        string='Tags',
    )

    author_id = fields.Many2one(
        'res.users', 'Author',
        default=lambda self: self.env.user,
        required=True, tracking=True,
    )
    last_edition_uid = fields.Many2one('res.users', 'Last Edited by', readonly=True)

    is_favorite = fields.Boolean(
        'Favorite',
        compute='_compute_is_favorite',
        inverse='_inverse_is_favorite',
        search='_search_is_favorite',
    )
    favorite_ids = fields.Many2many(
        'res.users',
        'knowledge_article_favorite_rel',
        'article_id', 'user_id',
        string='Favorited by',
    )

    member_ids = fields.One2many(
        'knowledge.article.member', 'article_id', 'Members',
    )

    active = fields.Boolean(default=True)

    @api.depends('child_ids')
    def _compute_child_count(self):
        for article in self:
            article.child_count = len(article.child_ids)

    def _compute_is_favorite(self):
        for article in self:
            article.is_favorite = self.env.user in article.favorite_ids

    def _inverse_is_favorite(self):
        for article in self:
            if article.is_favorite:
                article.favorite_ids = [(4, self.env.user.id)]
            else:
                article.favorite_ids = [(3, self.env.user.id)]

    def _search_is_favorite(self, operator, value):
        if operator == '=' and value:
            return [('favorite_ids', 'in', [self.env.user.id])]
        return [('favorite_ids', 'not in', [self.env.user.id])]

    @api.constrains('parent_id')
    def _check_article_recursion(self):
        if not self._check_recursion():
            raise ValidationError('An article cannot be its own parent (circular reference detected).')

    def write(self, vals):
        if 'body' in vals or 'name' in vals:
            vals['last_edition_uid'] = self.env.uid
        return super().write(vals)

    def action_toggle_favorite(self):
        self.ensure_one()
        self.is_favorite = not self.is_favorite

    def action_new_subarticle(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'knowledge.article',
            'view_mode': 'form',
            'context': {
                'default_parent_id': self.id,
                'default_category': self.category,
            },
            'target': 'current',
        }

    def action_open_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sub-articles of %s' % self.name,
            'res_model': 'knowledge.article',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_category': self.category,
            },
        }
