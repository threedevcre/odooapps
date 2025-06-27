from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    mobile_sms_enabled = fields.Boolean(string='Enable SMS', default=True)
    sms_messages_ids = fields.One2many(
        'sms.message',
        'partner_id',
        string='SMS Messages'
    )
    sms_count = fields.Integer(
        compute='_compute_sms_count',
        string='SMS Count'
    )

    def _compute_sms_count(self):
        for partner in self:
            partner.sms_count = len(partner.sms_messages_ids)

    def action_view_sms(self):
        self.ensure_one()
        action = self.env.ref('ringcentral_sms.sms_message_action').read()[0]
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action

    def send_sms_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send SMS',
            'res_model': 'sms.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_to_number': self.mobile,
            },
        }