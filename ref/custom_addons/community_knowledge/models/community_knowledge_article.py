from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext


class CommunityKnowledgeArticle(models.Model):
    _name = 'community.knowledge.article'
    _description = 'Knowledge Article'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'sequence, complete_name, id'

    name = fields.Char(required=True, default=lambda self: _('Untitled'), index='trigram', tracking=True)
    complete_name = fields.Char(compute='_compute_complete_name', recursive=True, store=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(default=0)
    body = fields.Html('Content', sanitize=True, sanitize_style=True)
    body_summary = fields.Char(compute='_compute_body_summary', store=True)
    parent_id = fields.Many2one(
        'community.knowledge.article',
        string='Parent Article',
        index=True,
        ondelete='cascade',
        domain="['!', ('id', 'child_of', id)]",
        tracking=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('community.knowledge.article', 'parent_id', string='Sub Articles')
    child_count = fields.Integer(compute='_compute_child_count')
    tag_ids = fields.Many2many(
        'community.knowledge.tag',
        'community_knowledge_article_tag_rel',
        'article_id',
        'tag_id',
        string='Tags',
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    member_ids = fields.Many2many(
        'res.users',
        'community_knowledge_article_member_rel',
        'article_id',
        'user_id',
        string='Extra Editors',
        help='Users who can access private articles and help edit them.',
    )
    access_mode = fields.Selection(
        [
            ('internal', 'Workspace'),
            ('private', 'Private'),
        ],
        string='Visibility',
        default='internal',
        required=True,
        tracking=True,
    )
    favorite_user_ids = fields.Many2many(
        'res.users',
        'community_knowledge_article_favorite_rel',
        'article_id',
        'user_id',
        string='Favorited By',
    )
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for article in self:
            if article.parent_id:
                article.complete_name = '%s / %s' % (article.parent_id.complete_name, article.name)
            else:
                article.complete_name = article.name

    @api.depends('body')
    def _compute_body_summary(self):
        for article in self:
            text = html2plaintext(article.body or '').strip()
            text = ' '.join(text.split())
            article.body_summary = (text[:157] + '...') if len(text) > 160 else text

    def _compute_child_count(self):
        counts = dict(self.env['community.knowledge.article']._read_group(
            [('parent_id', 'in', self.ids)],
            ['parent_id'],
            ['__count'],
        ))
        for article in self:
            article.child_count = counts.get(article, 0)

    @api.depends_context('uid')
    @api.depends('favorite_user_ids')
    def _compute_is_favorite(self):
        current_user = self.env.user
        for article in self:
            article.is_favorite = current_user in article.favorite_user_ids

    def _inverse_is_favorite(self):
        current_user_id = self.env.uid
        to_favorite = self.filtered(
            lambda article: article.is_favorite and current_user_id not in article.sudo().favorite_user_ids.ids
        )
        to_unfavorite = self.filtered(
            lambda article: not article.is_favorite and current_user_id in article.sudo().favorite_user_ids.ids
        )
        if to_favorite:
            to_favorite.sudo().write({'favorite_user_ids': [Command.link(current_user_id)]})
        if to_unfavorite:
            to_unfavorite.sudo().write({'favorite_user_ids': [Command.unlink(current_user_id)]})

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive knowledge articles.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') and vals.get('body'):
                text = html2plaintext(vals['body']).strip().partition('\n')[0]
                vals['name'] = (text[:97] + '...') if len(text) > 100 else text or _('Untitled')
        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for article, vals in zip(self, vals_list):
                vals['name'] = _('%s (copy)', article.name)
        return vals_list

    def action_toggle_favorite(self):
        current_user_id = self.env.uid
        for article in self.sudo():
            if current_user_id in article.favorite_user_ids.ids:
                article.favorite_user_ids = [Command.unlink(current_user_id)]
            else:
                article.favorite_user_ids = [Command.link(current_user_id)]
        return False

    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub Articles'),
            'res_model': 'community.knowledge.article',
            'view_mode': 'kanban,list,form,activity',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_access_mode': self.access_mode,
                'default_owner_id': self.owner_id.id,
            },
        }
