from odoo import models, api

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.depends('partner_ids')
    @api.depends_context('uid')
    def _compute_user_can_edit(self):
        # First, call the original method
        super(CalendarEvent, self)._compute_user_can_edit()

        # Now add custom logic for Manager/Editor
        MANAGER_GROUP = 'trionex_access_rights.group_calendar_manager'

        for event in self:
            # Start with original computed value
            if event.user_can_edit:
                continue  # Already editable, no need to modify

            editor_candidates = set(event.partner_ids.user_ids + event.user_id)
            if event._origin:
                editor_candidates |= set(event._origin.partner_ids.user_ids)

            # Admins can edit non-private events
            if self.env.user.has_group('base.group_system') and event.privacy != 'private':
                editor_candidates.add(self.env.user)

            # Calendar Manager can edit all events
            if self.env.user.has_group(MANAGER_GROUP):
                editor_candidates.add(self.env.user)

            # Update the field
            event.user_can_edit = self.env.user in editor_candidates
