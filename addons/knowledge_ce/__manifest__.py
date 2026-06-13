{
    'name': 'Knowledge',
    'version': '17.0.1.1.0',
    'category': 'Productivity/Knowledge',
    'summary': 'Centralize, share, and structure your knowledge base',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/knowledge_security.xml',
        'security/ir.model.access.csv',
        'views/knowledge_article_views.xml',
        'views/knowledge_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'knowledge_ce/static/src/scss/knowledge.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
