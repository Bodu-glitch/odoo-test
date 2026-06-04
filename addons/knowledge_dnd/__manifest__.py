{
    'name': 'Knowledge DnD',
    'version': '17.0.1.0.0',
    'category': 'Productivity/Knowledge',
    'summary': 'Knowledge Explorer with drag-and-drop sub-folder organization',
    'depends': ['knowledge_ce'],
    'data': [
        'security/ir.model.access.csv',
        'views/knowledge_folder_views.xml',
        'views/knowledge_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'knowledge_dnd/static/src/scss/knowledge_dnd.scss',
            'knowledge_dnd/static/src/xml/knowledge_explorer.xml',
            'knowledge_dnd/static/src/js/knowledge_explorer.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
