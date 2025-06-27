from odoo import models, fields, api, _
from odoo.exceptions import UserError
import stripe
from odoo.addons.payment_stripe import utils as stripe_utils
import os
import subprocess


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    stripe_payment_status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ], string='Stripe Payment Status', default='draft', tracking=True)
    stripe_failure_reason = fields.Text(string="Stripe Failure Reason", tracking=True)
    stripe_payment_intent_id = fields.Char(string="Stripe Payment Intent ID")

    @api.model
    def create(self, vals):
        payment = super().create(vals)
        if vals.get('payment_method_line_id') == 5:
            if payment.amount <= 0.0:
                raise UserError(_("Total amount is zero."))
            provider = self.env['payment.provider'].sudo().search([
                ('code', '=', 'stripe'), ('state', 'in', ['enabled', 'test'])
            ], limit=1)
            payment.state = 'draft'
            ref = payment.ref
            if not provider:
                raise UserError(_("Stripe provider not found or not enabled."))
            secret_key = stripe_utils.get_secret_key(provider)
            stripe.api_key = secret_key
            try:
                amount_with_fee = round(payment.amount_total * 1.029, 2)
                amount_in_cents = int(amount_with_fee * 100)
                intent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency=payment.currency_id.name.lower(),
                    capture_method="manual",
                    payment_method_types=["card_present"],
                    description=f"Payment for Invoice {ref}",
                )
                reader_id = provider.terminal_reader_id
                stripe.terminal.Reader.process_payment_intent(
                    reader_id,
                    payment_intent=intent['id']
                )
                payment.write({
                    'stripe_payment_status': 'in_progress',
                    'stripe_payment_intent_id': intent['id'],
                })
            except stripe.error.CardError as e:
                payment.write({
                    'stripe_payment_status': 'failed',
                    'stripe_failure_reason': e.user_message,
                })
                raise UserError(_("Card was declined: %s" % e.user_message))
            except Exception as e:
                payment.write({
                    'stripe_payment_status': 'failed',
                    'stripe_failure_reason': str(e),
                })
                raise UserError(_("Stripe POS Error: %s" % str(e)))
        return payment

    def action_draft(self):
        res = super(AccountPayment, self).action_draft()
        for rec in self:
            move = self.env['account.move'].search([('name', '=', rec.ref)], limit=1)
            if rec.payment_method_line_id.id == 5:
                move.is_stripe_payment = False
                rec.stripe_payment_status = 'in_progress'
        return res

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for rec in self:
            move = self.env['account.move'].search([('name', '=', rec.ref)], limit=1)
            if rec.payment_method_line_id.id == 5:
                move_lines = move.line_ids.filtered(
                    lambda x: not x.reconciled and x.account_id.account_type in "asset_receivable")
                for move_line in move_lines:
                    outstanding_lines = rec.line_ids.filtered(
                        lambda x: x.account_id == move_line.account_id and not x.reconciled)
                    if outstanding_lines:
                        for l in outstanding_lines:
                            move.js_assign_outstanding_line(l.id)
                move.is_stripe_payment = True
                rec.stripe_payment_status = 'paid'
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/print/invoice/{move.id}',
                    'target': 'new',
                }
        return res


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    terminal_reader_id = fields.Char(string='Terminal Reader')


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _post_payments(self, to_process, edit_mode=False):
        """
        Override to prevent payments from being posted on creation.
        """
        payments = self.env['account.payment']
        for vals in to_process:
            payments |= vals['payment']
            for p in payments:
                if p.payment_method_line_id.id != 5:
                    p.action_post()


class AccountMove(models.Model):
    _inherit = "account.move"

    custom_payment_counts = fields.Integer(string='Payment Count', compute='_compute_account_payments')
    is_stripe_payment = fields.Boolean(string='Stripe Payment')

    def _compute_account_payments(self):
        for move in self:
            payments = self.env['account.payment'].search([('ref', '=', self.name), ('ref', '!=', False)])
            move.custom_payment_counts = len(payments)

    def action_view_custom_payments(self):
        self.ensure_one()
        return {
            'name': 'Related Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('ref', '=', self.name), ('ref', '!=', False)],
            'context': {'create': False},
        }
