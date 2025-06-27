import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ringcentral import SDK

_logger = logging.getLogger(__name__)


class RingCentralAPI(models.Model):
    _name = 'ringcentral.api'
    _description = 'RingCentral API Configuration'

    name = fields.Char(string='Name', required=True)
    app_key = fields.Char(string='App Key', required=True)
    app_secret = fields.Char(string='App Secret', required=True)
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    extension = fields.Char(string='Extension')
    sandbox = fields.Boolean(string='Use Sandbox', default=True)
    active = fields.Boolean(string='Active', default=True)

    def get_platform(self):
        return SDK.PRODUCTION if not self.sandbox else SDK.SANDBOX

    def get_client(self):
        try:
            rcsdk = SDK(
                self.app_key,
                self.app_secret,
                self.get_platform()
            )
            platform = rcsdk.platform()
            platform.login(
                self.username,
                self.password,
                self.extension or ''
            )
            return platform
        except Exception as e:
            _logger.error("RingCentral connection failed: %s", str(e))
            raise UserError(_("RingCentral connection failed: %s") % str(e))

    @api.model
    def send_sms(self, to_number, text, partner_id=None):
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_("No active RingCentral configuration found."))

        try:
            platform = config.get_client()
            response = platform.post('/restapi/v1.0/account/~/extension/~/sms', {
                'from': {'phoneNumber': platform.token()['owner_id']},
                'to': [{'phoneNumber': to_number}],
                'text': text
            })

            # Create message record
            message_data = {
                'direction': 'outbound',
                'to_number': to_number,
                'from_number': platform.token()['owner_id'],
                'body': text,
                'status': 'sent',
                'ringcentral_id': response.json().get('id'),
                'partner_id': partner_id,
            }
            self.env['sms.message'].create(message_data)

            return True
        except Exception as e:
            _logger.error("Failed to send SMS: %s", str(e))
            raise UserError(_("Failed to send SMS: %s") % str(e))