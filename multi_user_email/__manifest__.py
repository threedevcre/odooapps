{
    'name': 'Multi Users Email Setup',
    'version': '17.0.1.0',
    'author': 'Fawad Hussain',
    'maintainer': 'Fawad Hussain',
    'category': 'Accounting',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_config.xml',
    ],
    'demo': [],
    'application': True,
    'auto_install': False,
    "installable": True,
}
