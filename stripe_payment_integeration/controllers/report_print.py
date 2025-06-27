from odoo import http
from odoo.http import request


class InvoicePrintController(http.Controller):

    @http.route('/pdf/invoice/<int:move_id>', type='http', auth='user')
    def serve_invoice_pdf(self, move_id):
        move = request.env['account.move'].sudo().browse(move_id)
        if not move.exists():
            return request.not_found()

        report = request.env.ref('account.account_invoices')
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(report, move.id)
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', str(len(pdf_content))),
            ('Content-Disposition', f'inline; filename="{move.name}.pdf"')
        ]
        return request.make_response(pdf_content, headers=headers)

    @http.route('/print/invoice/<int:move_id>', type='http', auth='user')
    def print_invoice_page(self, move_id):
        html = f"""
            <html>
                <body style="margin:0;">
                    <iframe id="pdfFrame" src="/pdf/invoice/{move_id}" style="width:100vw;height:100vh;border:none;" onload="this.contentWindow.focus(); this.contentWindow.print();"></iframe>
                </body>
            </html>
        """
        return request.make_response(html, headers=[('Content-Type', 'text/html')])
