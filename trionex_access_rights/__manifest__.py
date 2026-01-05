{
    "name": "Calendar Access Control",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "summary": "Separate access rights for Calendar view and edit",
    "description": """
Calendar Access Control
=======================
- Separate read / edit / full access for Calendar
- No need to give Settings access
- Control who can edit all events or only own events
""",
    "author": "Trionex",
    'website': 'https://www.trionex.pk',
    "license": "LGPL-3",
    "depends": ["calendar"],
    "data": [
        "security/calendar_security.xml",
    ],
    "installable": True,
    "application": False,
}
