{
    'name': 'Helpdesk',
    'version': '17.0.1.0.1',
    'category': 'Services/Helpdesk',
    'summary': 'Track, prioritize, and solve customer tickets',
    'description': 'Helpdesk management: tickets, teams, SLA, reporting.',
    'depends': ['mail', 'base_setup'],
    'data': [
        'security/helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/helpdesk_data.xml',
        'views/helpdesk_stage_views.xml',
        'views/helpdesk_tag_views.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_sla_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'helpdesk_ce/static/src/css/helpdesk.css',
            'helpdesk_ce/static/src/overview/helpdesk_overview.js',
            'helpdesk_ce/static/src/overview/helpdesk_overview.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
