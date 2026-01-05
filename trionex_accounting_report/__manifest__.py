{
    "name": "Accounting Reports Customization(Trionex)",
    "summary": "Accounting Reports Customization",
    "version": "18.0.1.0.0",
    "author": "Trionex",
    "website": "https://www.trionex.pk",
    "maintainers": ["Trionex"],
    "license": "AGPL-3",
    "category": "Usability",
    "depends": ["account", "account_reports", "accountant"],
    "data": [
        "views/account_general_ledger_report.xml",
        "views/account_partner_ledger_report.xml",
        "views/account_aged_receiveable_report.xml",
        "views/account_aged_payable_report.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'trionex_accounting_report/static/src/xml/aged_partner_balance_filters.xml',
            'trionex_accounting_report/static/src/xml/aged_general_ledger_filters.xml',
            'trionex_accounting_report/static/src/xml/aged_partner_ledger_filters.xml',
        ],
    },
}
