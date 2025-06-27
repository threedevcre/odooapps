{
    'name': 'RingCentral SMS Integration',
    'version': '1.0',
    'summary': 'Integrate RingCentral SMS with Odoo',
    'description': """
        Enable two-way SMS communication with customers directly from Odoo.
        Messages are linked to customer records and appear alongside emails.
    """,
    'author': 'Saqib Crecentech',
    'website': 'https://crecentech.com',
    'category': 'Tools',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/ringcentral_config_views.xml',
        'views/sms_message_views.xml',
        'views/res_partner_views.xml',
        'views/sms_compose_views.xml',
        'data/ringcentral_data.xml',
    ],
    'external_dependencies': {
        'python': ['ringcentral'],
    },
    'installable': True,
    'application': True,
}