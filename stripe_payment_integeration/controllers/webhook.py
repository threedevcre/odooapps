from odoo import http
from odoo.http import request
import stripe
import logging

from odoo.addons.payment_stripe import utils as stripe_utils

_logger = logging.getLogger(__name__)


class StripeWebhookController(http.Controller):

    @http.route('/webhook/payment/stripe', type='http', auth='public', csrf=False)
    def stripe_webhook(self, **post):
        provider = request.env['payment.provider'].sudo().search([('code', '=', 'stripe')], limit=1)
        if not provider:
            return "Provider not found", 400

        webhook_secret = stripe_utils.get_webhook_secret(provider)
        payload = request.httprequest.data
        sig_header = request.httprequest.headers.get('Stripe-Signature')

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError as e:
            _logger.error("Webhook signature verification failed: %s", str(e))
            return "Signature Error", 400
        except Exception as e:
            _logger.error("Invalid webhook payload: %s", str(e))
            return "Invalid Payload", 400

        event_type = event['type']
        intent = event['data']['object']
        description = intent.get('description', '')
        invoice_name = description.split()[-1] if description else ''

        move = request.env['account.move'].sudo().search([('name', '=', invoice_name)], limit=1)
        if not move:
            _logger.warning("Invoice not found for webhook: %s", description)
            return "Invoice not found", 404

        if event_type == 'payment_intent.succeeded':
            move.write({
                'stripe_payment_status': 'paid'
            })
            _logger.info("Payment succeeded for %s", move.name)

        elif event_type == 'payment_intent.payment_failed':
            failure_reason = intent.get('last_payment_error', {}).get('message', 'Unknown failure')
            move.write({
                'stripe_payment_status': 'failed',
                'stripe_failure_reason': failure_reason,
            })
            _logger.warning("Payment failed for %s: %s", move.name, failure_reason)

        return "Webhook processed", 200
