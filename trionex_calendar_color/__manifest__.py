# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Calendar Color Contact(Trionex)",
    "summary": "Colorize calendar view depending on contact color",
    "version": "18.0.1.0.0",
    'author': 'Trionex',
    'website': 'https://www.trionex.pk',
    "maintainers": ["Trionex"],
    "license": "AGPL-3",
    "category": "Usability",
    "depends": ["calendar","dow_calendar"],
    "data": [
             "views/calendar_event_views.xml",

    ],
    "assets": {
        "web.assets_backend": [
            "trionex_calendar_color/static/src/views/**/*",
        ]
    },
}
