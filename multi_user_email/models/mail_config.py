from odoo import models, fields, api


class MailConfig(models.Model):
    _name = 'mail.config'
    _description = 'mail.configuration'

    mail_server_id = fields.Many2one('ir.mail_server',string='Outgoing mail server',required=True)
    name = fields.Char(related="user_id.name",store=True)
    user_id = fields.Many2one('res.users', string='User')

    _sql_constraints = [
        ('user_uniq', 'unique(user_id)', "Each user can only have one mail config!"),
    ]
