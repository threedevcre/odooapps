from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SMSMessage(models.Model):
    _name = 'sms.message'
    _description = 'SMS Message'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound')],
        string='Direction',
        required=True
    )
    to_number = fields.Char(string='To', required=True)
    from_number = fields.Char(string='From', required=True)
    body = fields.Text(string='Message', required=True)
    status = fields.Selection([
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('received', 'Received')],
        string='Status',
        default='sent'
    )
    create_date = fields.Datetime(string='Date', default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string='Customer', index=True)
    ringcentral_id = fields.Char(string='RingCentral ID')
    mail_message_id = fields.Many2one('mail.message', string='Linked Mail Message', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        for message in messages:
            message._create_partner_chatter_message()
        return messages

    def _create_partner_chatter_message(self):
        """Create a mail.message record linked to the partner's chatter"""
        self.ensure_one()
        if not self.partner_id:
            # Try to find partner by phone number
            self.partner_id = self.env['res.partner'].search([
                '|',
                ('mobile', '=', self.to_number),
                ('mobile', '=', self.from_number)
            ], limit=1)

        if self.partner_id:
            mail_message = self.env['mail.message'].create({
                'model': 'res.partner',
                'res_id': self.partner_id.id,
                'message_type': 'comment',
                'subtype_id': self.env.ref('mail.mt_comment').id,
                'body': self._format_message_body(),
                'date': self.create_date,
            })
            self.mail_message_id = mail_message.id

    def _format_message_body(self):
        """Format the message body for display in chatter"""
        self.ensure_one()
        direction_label = 'Received from' if self.direction == 'inbound' else 'Sent to'
        phone_number = self.from_number if self.direction == 'inbound' else self.to_number
        return f"""
        <div class="sms-message">
            <p><strong>SMS {direction_label} {phone_number}:</strong></p>
            <div class="sms-content">{self.body}</div>
            <small class="text-muted">{self.create_date}</small>
        </div>
        """