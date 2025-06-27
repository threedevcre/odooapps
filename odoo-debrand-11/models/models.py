import base64
from odoo import fields, models, tools, exceptions, api

from urllib.parse import urlparse


class ResCompany(models.Model):
    _inherit = "res.company"

    brand_name = fields.Char(
        "Brand name",
        help="Brand Name To Do The Debranding"
    )
    brand_logo = fields.Binary(
        "Brand Logo"
    )
    brand_url = fields.Char("Brand URL")
    favicon = fields.Binary(
        string="Favicon",
        help="This field holds the favicon"
             " used for the Company",
    )
    logo_branding = fields.Binary(
        compute='_compute_logo_branding',
        store=True,
        attachment=False
    )

    @api.depends('brand_logo')
    def _compute_logo_branding(self):
        for company in self:
            img = company.brand_logo
            if img:
                data = base64.b64decode(img)
                company.logo_branding = img and tools.image_process(data, size=(180, 0), crop='center')

    @api.model
    def get_current_company(self):
        return self.env.company.id


class WebsiteConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    favicon = fields.Binary(
        string="Favicon",
        help="This field holds the favicon"
             " used for the Company",
        readonly=False)
    brand_logo = fields.Binary(
        readonly=False
    )
    brand_name = fields.Char(
        readonly=False
    )
    brand_url = fields.Char(
        readonly=False
    )

    @api.constrains('brand_url')
    def validate_url(self):
        """
        print(is_valid_url('http://www.example.com'))  # True
        print(is_valid_url('ftp://ftp.example.com'))  # True
        print(is_valid_url('example.com'))  # False
        print(is_valid_url('http://'))  # False
        """
        try:
            result = urlparse(self.brand_url)
            if not all([result.scheme, result.netloc]):
                raise exceptions.UserError("URL Validation Failed, URL Must be in a format of http://www.example.com")
            else:
                return True
        except ValueError:
            return False

    # Sample Error Dialogue
    def error(self):
        raise exceptions.ValidationError(
            "This is a test Error message. You dont need to save the config after pop wizard.")

    # Sample Warning Dialogue
    def warning(self):
        raise exceptions.UserError("This is a test Error message. You don't need to save the config after pop wizard.")

    @api.model
    def get_values(self):
        """Add values of `helpdesk_team` field to ResConfigSettings return."""
        res = super(WebsiteConfig, self).get_values()
        company = self.env.company
        res.update({
            'favicon': company.favicon,
            'brand_logo': company.brand_logo,
            'brand_name': company.brand_name,
            'brand_url': company.brand_url,
        })
        return res

    def set_values(self):
        """Set values of `helpdesk_team` field."""
        super(WebsiteConfig, self).set_values()
        company = self.env.company
        fields_to_check = [
            'favicon',
            'brand_logo',
            'brand_name',
            'brand_url',
        ]
        if any(self[field] != company[field] for field in fields_to_check):
            company.write({field: self[field] for field in fields_to_check})
