from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pos_order_id = fields.Many2one('pos.order', string="POS Order", readonly=True)

    def create_pos_order(self, config_id=None):
        self.ensure_one()

        if self.pos_order_id:
            raise UserError("POS Order already created for this Sale Order.")

        pos_config = self.env['pos.config'].browse(config_id) if config_id else self.env['pos.config'].search([],
                                                                                                              limit=1)
        if not pos_config:
            raise UserError("No POS Configuration found.")

        pos_session = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('config_id', '=', pos_config.id)
        ], limit=1)

        if not pos_session:
            pos_session = self.env['pos.session'].create({'config_id': pos_config.id})
            pos_session.action_pos_session_open()

        total_tax = 0.0
        total_amount = 0.0
        subtotal_wo_tax = 0.0
        pos_lines = []

        for line in self.order_line:
            product = line.product_id
            qty = line.product_uom_qty
            price_unit = line.price_unit
            discount = line.discount or 0.0

            taxes = product.taxes_id.filtered(lambda t: t.company_id == self.company_id)
            if self.fiscal_position_id:
                taxes = self.fiscal_position_id.map_tax(taxes)

            # Base price after discount
            price_after_discount = price_unit * (1 - discount / 100.0)

            # Compute taxes
            taxes_res = taxes.compute_all(
                price_after_discount,
                currency=self.currency_id,
                quantity=qty,
                product=product,
                partner=self.partner_id,
            )

            tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
            price_subtotal = taxes_res['total_excluded']
            price_subtotal_incl = taxes_res['total_included']

            total_tax += tax_amount
            subtotal_wo_tax += price_subtotal
            total_amount += price_subtotal_incl

            line_vals = {
                'product_id': product.id,
                'qty': qty,
                'price_unit': price_unit,
                'discount': discount,
                'tax_ids': [(6, 0, taxes.ids)],
                'price_subtotal': price_subtotal,
                'price_subtotal_incl': price_subtotal_incl,
            }
            pos_lines.append((0, 0, line_vals))

        order_vals = {
            'partner_id': self.partner_id.id,
            'session_id': pos_session.id,
            'lines': pos_lines,
            'amount_tax': total_tax,
            'amount_total': total_amount,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        }

        pos_order = self.env['pos.order'].create(order_vals)
        self.pos_order_id = pos_order.id

        return pos_order


class POSOrder(models.Model):
    _inherit = 'pos.order'

    sale_order_id = fields.Many2one('sale.order', string='Source Sale Order')