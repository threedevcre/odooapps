from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo import http

class WebsiteSaleInherit(WebsiteSale):

    def checkout_form_validate(self, data, mode, all_form_values):
        # Save the custom field to partner
        if 'custom_field' in data:
            data['custom_field'] = data['custom_field'].upper()  # match `text-uppercase` class

        return super().checkout_form_validate(data, mode, all_form_values)

    @http.route()
    def address(self, **kw):
        if 'custom_field' in kw:
            kw['custom_field'] = kw['custom_field'].upper()
        return super().address(**kw)


    def _checkout_form_save(self, mode, checkout, all_values):
        # Let super handle most of the work
        order = request.website.sale_get_order()
        partner = order.partner_id

        # Save custom field if it's present
        if all_values.get('custom_field'):
            partner.write({'custom_field': all_values['custom_field']})

        return super()._checkout_form_save(mode, checkout, all_values)
