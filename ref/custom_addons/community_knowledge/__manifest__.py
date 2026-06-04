{
    'name': 'Community Knowledge',
    'version': '1.0',
    'category': 'Productivity',
    'summary': 'Internal knowledge base for Odoo Community',
    'description': """
Community Knowledge
===================

Create and organize internal articles, notes, procedures, and team knowledge
inside Odoo Community.
    """,
    'depends': [
        'mail',
        'web_hierarchy',
    ],
    'data': [
        'security/community_knowledge_security.xml',
        'security/ir.model.access.csv',
        'views/community_knowledge_article_views.xml',
        'views/community_knowledge_tag_views.xml',
        'views/community_knowledge_menus.xml',
        'data/community_knowledge_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'community_knowledge/static/src/client_action/knowledge_action.js',
            'community_knowledge/static/src/client_action/knowledge_action.xml',
            'community_knowledge/static/src/client_action/knowledge_action.scss',
        ],
    },
    'application': True,
    'installable': True,
    'author': 'Community',
    'license': 'LGPL-3',
}
