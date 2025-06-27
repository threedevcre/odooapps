# -*- coding: utf-8 -*-
import requests
from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.home import Home


class AuthSignupRecaptcha(AuthSignupHome):

    @http.route('/web/signup', type='http', auth='public', website=True, csrf=False)
    def web_auth_signup(self, *args, **kw):
        recaptcha_secret = request.env["ir.config_parameter"].sudo().get_param("recaptcha_signup.private_key")
        recaptcha_response = kw.get("g-recaptcha-response")
        if recaptcha_secret:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": recaptcha_secret, "response": recaptcha_response},
            )
            result = response.json()
            if not result.get("success") and isinstance(recaptcha_response, str):
                return request.render("auth_signup.signup", {
                    "error": "Invalid reCAPTCHA. Please try again."
                })
            elif not result.get("success") and recaptcha_response == None:
                return request.render("auth_signup.signup", {
                })
        return super(AuthSignupRecaptcha, self).web_auth_signup(*args, **kw)

class AuthLoginRecaptcha(Home):
    @http.route('/web/login', type='http', auth='public', website=True, csrf=False)
    def web_login(self, *args, **kw):
        recaptcha_secret = request.env["ir.config_parameter"].sudo().get_param("recaptcha_signup.private_key")
        recaptcha_response = kw.get("g-recaptcha-response")
        if recaptcha_secret:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": recaptcha_secret, "response": recaptcha_response},
            )
            result = response.json()
            if not result.get("success") and isinstance(recaptcha_response, str):
                return request.render("web.login", {
                    "error": "Invalid reCAPTCHA. Please try again."
                })
            elif not result.get("success") and recaptcha_response == None:
                return request.render("web.login", {
                })
        return super(AuthLoginRecaptcha, self).web_login(*args, **kw)