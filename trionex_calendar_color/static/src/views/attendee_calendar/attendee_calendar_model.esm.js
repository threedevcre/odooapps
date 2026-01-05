/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { CalendarModel } from "@web/views/calendar/calendar_model";

/* ----------------------------------------------------------
 * FIX 1 — Properly override updateAttendeeData() in Odoo 18
 * Odoo removed _super, so we must save the original method.
 * ---------------------------------------------------------- */

const originalUpdateAttendeeData = AttendeeCalendarModel.prototype.updateAttendeeData;

patch(AttendeeCalendarModel.prototype, {
    async updateAttendeeData(data) {
        // Call original Odoo method
        await originalUpdateAttendeeData.call(this, data);

        // Apply backend event color
        for (const event of Object.values(data.records)) {
            const raw = event.rawRecord;

            if (raw.color !== null && raw.color !== undefined) {
                event.colorIndex = raw.color;
            }
        }
    },
});

/* ----------------------------------------------------------
 * FIX 2 — Apply backend color to CalendarModel (UI rendering)
 * ---------------------------------------------------------- */

const originalGetFullCalendarEvent = CalendarModel.prototype.getFullCalendarEvent;

patch(CalendarModel.prototype, {
    getFullCalendarEvent(record) {
        // get original event object
        const event = originalGetFullCalendarEvent.call(this, record);

        // backend color logic
        if (record.color !== undefined && record.color !== null) {
            const rgb = this._color(record.color);

            event.backgroundColor = rgb;
            event.borderColor = rgb;
            event.color = null;
            event.classNames = [];
        }

        return event;
    },
});
