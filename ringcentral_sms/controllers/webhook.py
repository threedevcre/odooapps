import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class RingCentralWebhook(http.Controller):
    @http.route('/ringcentral/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook_handler(self, **kwargs):
        data = request.jsonrequest

        if data.get('event') == '/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS':
            try:
                message_info = data.get('body', {})

                # Create message record
                sms = request.env['sms.message'].create({
                    'direction': 'inbound',
                    'to_number': message_info.get('to', [{}])[0].get('phoneNumber', ''),
                    'from_number': message_info.get('from', {}).get('phoneNumber', ''),
                    'body': message_info.get('subject', ''),
                    'status': 'received',
                    'ringcentral_id': message_info.get('messageId', ''),
                })

                # Log the SMS in partner's chatter if found
                if sms.partner_id:
                    _logger.info(f"Logged inbound SMS to partner {sms.partner_id.id} chatter")

                return {'status': 'success'}
            except Exception as e:
                _logger.error("Failed to process inbound SMS: %s", str(e))
                return {'status': 'error', 'message': str(e)}

        return {'status': 'ignored'}