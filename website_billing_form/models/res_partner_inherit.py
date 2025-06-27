# -*- coding: utf-8 -*-

from odoo import _,api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    custom_field = fields.Char(string='Custom Field')


