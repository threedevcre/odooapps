# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    color = fields.Char(
        string="Color",
        compute="_compute_color_from_event_type",
        store=False,
    )

    @api.depends('event_calendar_id')
    def _compute_color_from_event_type(self):
        for event in self:
            if event.event_calendar_id:
                event.color = event.event_calendar_id.color or "#EFC8A4"
            else:
                event.color = "#EFC8A4"

    def read(self, fields=None, load='_classic_read'):
        fields = list(fields or [])
        if "color" not in fields:
            fields.append("color")
        return super().read(fields, load)
