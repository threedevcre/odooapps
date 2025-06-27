# -*- coding: utf-8 -*-

from werkzeug import urls

from odoo import models, fields, api, _
from odoo.addons.payment import utils as payment_utils
# from odoo.addons.payment_stripe.const import PAYMENT_METHOD_TYPES
from odoo.addons.payment_stripe.controllers.main import StripeController

from odoo.exceptions import UserError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    stripe_fees = fields.Monetary(
        string="Fees", currency_field='currency_id',
        help="The fees amount; set by the system as it depends on the provider", readonly=True)

    def _mark_draft_transactions_done(self):
        """
        Method to move draft transactions to done/successful state
        """
        draft_transactions = self.search([('state', '=', 'draft')])

        for tx in draft_transactions:
            try:
                # Update transaction state to done
                tx.write({'state': 'done'})

                # If you need to perform additional actions when payment succeeds
                if tx.sale_order_ids:
                    tx.sale_order_ids._payment_succeeded()

                # Log the successful update
                print(f"Transaction {tx.reference} moved from draft to done")

            except Exception as e:
                print(f"Failed to update transaction {tx.reference}: {str(e)}")
                continue

        return True

    def _set_done(self):
        res = super()._set_done()

        for transaction in self:
            if transaction.provider_id.name != 'Stripe' or transaction.stripe_fees <= 0:
                continue

            stripe_fee_product = self.env['product.product'].search([
                ('name', '=', 'Stripe 2.90% Fee')
            ], limit=1)
            if not stripe_fee_product:
                continue  # optionally log

            # Add to Sale Order (keeping your original code)
            for order in transaction.sale_order_ids:
                existing_fee = order.order_line.filtered(lambda l: l.product_id.id == stripe_fee_product.id)
                if not existing_fee:
                    order.order_line.create({
                        'order_id': order.id,
                        'product_id': stripe_fee_product.id,
                        'name': 'Stripe Fee',
                        'product_uom_qty': 1,
                        'price_unit': transaction.stripe_fees,
                    })

            # Add to Invoice - Modified to handle payment reconciliation
            for invoice in transaction.invoice_ids:
                if invoice.move_type != 'out_invoice':
                    continue  # only add fee if invoice is still in draft

                existing_fee_line = invoice.invoice_line_ids.filtered(
                    lambda l: l.product_id.id == stripe_fee_product.id)
                if not existing_fee_line:
                    # Create fee line (your original code)
                    fee_line = invoice.invoice_line_ids.create({
                        'move_id': invoice.id,
                        'product_id': stripe_fee_product.id,
                        'name': 'Stripe Fee',
                        'quantity': 1,
                        'price_unit': transaction.stripe_fees,
                        'account_id': stripe_fee_product.property_account_income_id.id or
                                      stripe_fee_product.categ_id.property_account_income_categ_id.id,
                    })
                    invoice._compute_amount()

                    # NEW: Automatically reconcile the fee if invoice was already paid
                    if invoice.payment_state == 'not_paid':
                        # Create a payment for the fee amount
                        payment = self.env['account.payment'].create({
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'partner_id': invoice.partner_id.id,
                            'amount': transaction.stripe_fees,
                            'currency_id': invoice.currency_id.id,
                            'destination_journal_id': invoice.journal_id.id,
                        })
                        payment.action_post()

                        # Reconcile with the invoice
                        (invoice.line_ids + payment.move_id.line_ids).filtered(
                            lambda line: line.account_id == payment.destination_account_id
                                         and not line.reconciled
                        ).reconcile()

                    # Your original sale order fee creation
                    sale_orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')
                    for sale_order in sale_orders:
                        existing_so_fee = sale_order.order_line.filtered(
                            lambda l: l.product_id.id == stripe_fee_product.id)
                        if not existing_so_fee:
                            new_so_line = sale_order.order_line.create({
                                'order_id': sale_order.id,
                                'product_id': stripe_fee_product.id,
                                'name': 'Stripe Fee',
                                'product_uom_qty': 1,
                                'price_unit': transaction.stripe_fees,
                            })

                            # Link the SO line to the newly created invoice line
                            if fee_line:
                                new_so_line.write({'invoice_lines': [(6, 0, fee_line.ids)]})

        return res

    def _handle_pending_stripe_direct_debit_fees(self):
        for transaction in self:
            if transaction.provider_id.name != 'Stripe':
                continue
            if transaction.state != 'pending':
                continue
            if transaction.stripe_fees <= 0:
                continue

            stripe_fee_product = self.env['product.product'].search([
                ('name', '=', 'ACH 1% Fee')
            ], limit=1)
            if not stripe_fee_product:
                continue  # optionally log

            # Sale Order
            for order in transaction.sale_order_ids:
                existing_fee = order.order_line.filtered(
                    lambda l: l.product_id.id == stripe_fee_product.id
                )
                if not existing_fee:
                    order.order_line.create({
                        'order_id': order.id,
                        'product_id': stripe_fee_product.id,
                        'name': 'ACH Direct Debit Fee',
                        'product_uom_qty': 1,
                        'price_unit': transaction.stripe_fees,
                    })

            # Invoice
            for invoice in transaction.invoice_ids:
                if invoice.move_type != 'out_invoice':
                    continue

                existing_fee_line = invoice.invoice_line_ids.filtered(
                    lambda l: l.product_id.id == stripe_fee_product.id
                )
                if not existing_fee_line:
                    new_invoice_line = invoice.invoice_line_ids.create({
                        'move_id': invoice.id,
                        'product_id': stripe_fee_product.id,
                        'name': 'ACH Direct Debit Fee',
                        'quantity': 1,
                        'price_unit': transaction.stripe_fees,
                        'account_id': stripe_fee_product.property_account_income_id.id or
                                      stripe_fee_product.categ_id.property_account_income_categ_id.id,
                    })
                    invoice._compute_amount()

                    # NEW: Automatically reconcile the fee if invoice was already paid
                    if invoice.payment_state == 'not_paid':
                        # Create a payment for the fee amount
                        payment = self.env['account.payment'].create({
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'partner_id': invoice.partner_id.id,
                            'amount': transaction.stripe_fees,
                            'currency_id': invoice.currency_id.id,
                            'destination_journal_id': invoice.journal_id.id,
                        })
                        payment.action_post()

                        # Reconcile with the invoice
                        (invoice.line_ids + payment.move_id.line_ids).filtered(
                            lambda line: line.account_id == payment.destination_account_id
                                         and not line.reconciled
                        ).reconcile()

                    # Your original sale order fee creation
                    sale_orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')
                    for sale_order in sale_orders:
                        existing_so_fee = sale_order.order_line.filtered(
                            lambda l: l.product_id.id == stripe_fee_product.id)
                        if not existing_so_fee:
                            new_so_line = sale_order.order_line.create({
                                'order_id': sale_order.id,
                                'product_id': stripe_fee_product.id,
                                'name': 'ACH Direct Debit Fee',
                                'product_uom_qty': 1,
                                'price_unit': transaction.stripe_fees,
                            })

                            # Link the SO line to the newly created invoice line
                            if new_invoice_line:
                                new_so_line.write({'invoice_lines': [(6, 0, new_invoice_line.ids)]})


    @api.model
    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'pending':
            self._handle_pending_stripe_direct_debit_fees()
        return res

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            payment_method = self.env['payment.method'].browse(values.get('payment_method_id'))
            if payment_method.name == 'Card':
                provider = self.env['payment.provider'].browse(values['provider_id'])
                partner = self.env['res.partner'].browse(values['partner_id'])
                if values.get('operation') == 'validation':
                    values['stripe_fees'] = 0
                else:
                    currency = self.env['res.currency'].browse(values.get('currency_id')).exists()
                    values['stripe_fees'] = provider._compute_fees(
                        values.get('amount', 0), partner.country_id,
                    )
            elif payment_method.name == 'ACH Direct Debit':
                provider = self.env['payment.provider'].browse(values['provider_id'])
                partner = self.env['res.partner'].browse(values['partner_id'])
                if values.get('operation') == 'validation':
                    values['stripe_fees'] = 0
                else:
                    currency = self.env['res.currency'].browse(values.get('currency_id')).exists()
                    values['stripe_fees'] = provider._compute_fees_ach(
                        values.get('amount', 0), partner.country_id,
                    )
        txs = super().create(values_list)
        txs.invalidate_recordset(['amount', 'stripe_fees'])
        return txs

    def _stripe_prepare_payment_intent_payload(self):
        """ Prepare the payload for the creation of a payment intent in Stripe format.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.
        Note: self.ensure_one()

        :return: The Stripe-formatted payload for the payment intent request
        :rtype: dict
        """

        res = super(PaymentTransaction, self)._stripe_prepare_payment_intent_payload()
        res.update({
            'amount': payment_utils.to_minor_currency_units(
                self.amount + self.stripe_fees, self.currency_id),
        })
        return res

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        # First, call original action_post to ensure invoice is properly posted
        res = super(AccountMove, self).action_post()

        # Process Stripe fees after posting
        for move in self:
            if move.move_type in ('out_invoice', 'in_invoice'):
                for line in move.invoice_line_ids:
                    if (line.product_id and
                            line.product_id.name == 'Stripe 2.90% Fee' or line.product_id.name == 'ACH 1% Fee' and
                            line.price_subtotal != 0):
                        # Create payment for the Stripe fee line amount
                        self._create_stripe_fee_payment(line)
        return res

    def _create_stripe_fee_payment(self, invoice_line):
        """Create and reconcile payment for Stripe fee line"""
        self.ensure_one()

        # Get the exact amount from the fee line
        amount = abs(invoice_line.price_total)

        # Find appropriate journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not journal:
            raise UserError(_("No bank journal found for automatic Stripe fee payment"))

        payment_method = self.env.ref('account.account_payment_method_manual_in')

        payment_vals = {
            'payment_type': 'inbound' if self.move_type == 'out_invoice' else 'outbound',
            'partner_id': self.partner_id.id,
            'amount': amount,
            'currency_id': self.currency_id.id,
            'destination_journal_id': journal.id,
            'payment_method_id': payment_method.id,
            'partner_type': 'customer' if self.move_type == 'out_invoice' else 'supplier',
            'ref': _('Automatic payment for Stripe fee on invoice %s') % self.name,
        }

        # Create and post payment
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        # Find the account move lines to reconcile
        payment_move_lines = payment.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
        )

        invoice_move_lines = self.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
        )

        # Reconcile the lines
        if payment_move_lines and invoice_move_lines:
            (payment_move_lines + invoice_move_lines).reconcile()