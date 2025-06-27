from odoo import models, fields, api
from odoo.exceptions import UserError


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model_create_multi
    def create(self, values_list):
        new_mails = super(MailMail, self).create(values_list)
        for mail in new_mails:
            mail_config = self.env['mail.config'].sudo().search(
                [('user_id', '=', self.env.user.id)], limit=1)
            if not mail_config:
                return new_mails
            if mail_config:
                mail.mail_server_id = mail_config.mail_server_id.id
                mail.email_from = mail_config.mail_server_id.smtp_user
        return new_mails
