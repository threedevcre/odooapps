from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SMSCompose(models.TransientModel):
    _name = 'sms.compose'
    _description = 'SMS Composition Wizard'

    partner_id = fields.Many2one('res.partner', string='Customer')
    to_number = fields.Char(string='To Number', required=True)
    body = fields.Text(string='Message', required=True)

    def send_sms(self):
        self.ensure_one()
        if not self.to_number:
            raise ValidationError("Phone number is required to send SMS")

        # Get the RingCentral API and send SMS
        self.env['ringcentral.api'].send_sms(
            to_number=self.to_number,
            text=self.body,
            partner_id=self.partner_id.id
        )

        return {'type': 'ir.actions.act_window_close'}