# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    # Fees fields
    stripe_fees_active = fields.Boolean(string="Add Extra Fees")
    stripe_fees_dom_fixed = fields.Float(string="Fixed domestic fees")
    stripe_fees_dom_var = fields.Float(string="Variable domestic fees (in percents)")
    stripe_fees_int_fixed = fields.Float(string="Fixed international fees")
    stripe_fees_int_var = fields.Float(string="Variable international fees (in percents)")

    # ACH Fees fields
    stripe_fees_active_ach = fields.Boolean(string="Add Extra Fees ACH")
    stripe_fees_dom_fixed_ach = fields.Float(string="Fixed domestic fees ACH")
    stripe_fees_dom_var_ach = fields.Float(string="Variable domestic fees (in percents) ACH")
    stripe_fees_int_fixed_ach = fields.Float(string="Fixed international fees ACH")
    stripe_fees_int_var_ach = fields.Float(string="Variable international fees (in percents) ACH")

    @api.constrains('stripe_fees_dom_var', 'stripe_fees_int_var')
    def _check_fee_var_within_boundaries(self):
        """ Check that variable fees are within realistic boundaries.

        Variable fee values should always be positive and below 100% to respectively avoid negative
        and infinite (division by zero) fee amounts.

        :return None
        """
        for provider in self:
            if any(not 0 <= fee < 100 for fee in (provider.stripe_fees_dom_var, provider.stripe_fees_int_var)):
                raise ValidationError(_("Variable fees must always be positive and below 100%."))

    @api.constrains('stripe_fees_dom_var_ach', 'stripe_fees_int_var_ach')
    def _check_ach_fee_var_within_boundaries(self):
        """ Check that variable fees are within realistic boundaries.

        Variable fee values should always be positive and below 100% to respectively avoid negative
        and infinite (division by zero) fee amounts.

        :return None
        """
        for provider in self:
            if any(not 0 <= fee_ach < 100 for fee_ach in (provider.stripe_fees_dom_var_ach, provider.stripe_fees_int_var_ach)):
                raise ValidationError(_("Variable fees must always be positive and below 100%."))

    def _compute_fees(self, amount, country):
        self.ensure_one()
        fees = 0.0
        if self.stripe_fees_active:
            if country == self.company_id.country_id:
                fixed = self.stripe_fees_dom_fixed
                variable = self.stripe_fees_dom_var
            else:
                fixed = self.stripe_fees_int_fixed
                variable = self.stripe_fees_int_var
            fees = (amount * variable / 100.0 + fixed) / (1 - variable / 100.0)
        return fees

    def _compute_fees_ach(self, amount, country):
        self.ensure_one()
        fees_ach = 0.0
        if self.stripe_fees_active_ach:
            if country == self.company_id.country_id:
                fixed = self.stripe_fees_dom_fixed_ach
                variable = self.stripe_fees_dom_var_ach
            else:
                fixed = self.stripe_fees_int_fixed_ach
                variable = self.stripe_fees_int_var_ach
            fees_ach = (amount * variable / 100.0 + fixed) / (1 - variable / 100.0)
        return fees_ach

    def get_fees(self, amount, partner_id):
        fees = 0.0
        if amount and partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            fees = self._compute_fees(amount, partner.country_id)
        return fees

    def get_fees_ach(self, amount, partner_id):
        fees_ach = 0.0
        if amount and partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            fees_ach = self._compute_fees_ach(amount, partner.country_id)
        return fees_ach
