from odoo import models, api, _
from odoo.tools import SQL


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    # @api.model
    # def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
    #     rslt = super()._get_aml_values(
    #         options,
    #         partner_ids,
    #         offset=offset,
    #         limit=limit
    #     )
    #
    #     for partner_id, aml_lines in rslt.items():
    #         for aml in aml_lines:
    #
    #             # Keep reference empty (you don't have ref)
    #             aml['reference'] = aml.get('move_name') or ''
    #
    #             # Explicit description
    #             aml['description'] = aml.get('name') or ''
    #             aml['bill_ref'] = aml.get('ref') or ''
    #             aml['po_ref'] = aml.get('po_number') or ''
    #     return rslt


    @api.model
    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        # Get existing AML values
        rslt = super()._get_aml_values(
            options,
            partner_ids,
            offset=offset,
            limit=limit
        )

        # ----------------------------------------------------
        # Collect all AML ids
        # ----------------------------------------------------
        aml_ids = []
        for aml_lines in rslt.values():
            for aml in aml_lines:
                if aml.get('id'):
                    aml_ids.append(aml['id'])

        if not aml_ids:
            return rslt

        # ----------------------------------------------------
        # SQL query to get bill_ref and po_number from account_move
        # ----------------------------------------------------
        self.env.cr.execute("""
            SELECT
                aml.id AS aml_id,
                am.ref AS bill_ref,
                am.po_number AS po_ref
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.id = ANY(%s)
        """, (aml_ids,))

        sql_data = {row['aml_id']: row for row in self.env.cr.dictfetchall()}

        # ----------------------------------------------------
        # Inject values into report lines
        # ----------------------------------------------------
        for partner_id, aml_lines in rslt.items():
            for aml in aml_lines:
                aml_id = aml.get('id')
                extra = sql_data.get(aml_id, {})

                aml['reference'] = aml.get('move_name') or ''
                aml['description'] = aml.get('name') or ''
                aml['bill_ref'] = extra.get('bill_ref') or ''
                aml['po_ref'] = extra.get('po_ref') or ''

        return rslt

    def _format_aml_name(self, line_name, move_ref, move_name=None):
        names = []

        # Always show move name once
        if move_name and move_name != '/':
            names.append(move_name)

        # Add ref ONLY if different from move_name
        if move_ref and move_ref != '/' and move_ref != move_name:
            names.append(move_ref)

        # Add line name ONLY if different from both
        if (
            line_name
            and line_name != '/'
            and line_name != move_name
            and line_name != move_ref
        ):
            names.append(line_name)

        return ' - '.join(names)

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        domain = []

        company_ids = report.get_report_company_ids(options)
        exch_code = self.env['res.company'].browse(company_ids).mapped('currency_exchange_journal_id')
        if exch_code:
            domain += ['!', '&', '&', '&', ('credit', '=', 0.0), ('debit', '=', 0.0), ('amount_currency', '!=', 0.0), ('journal_id', 'in', exch_code.ids)]

        if options['export_mode'] == 'print' and options.get('filter_search_bar'):
            domain += [
                '|', ('matched_debit_ids.debit_move_id.partner_id.name', 'ilike', options['filter_search_bar']),
                '|', ('matched_credit_ids.credit_move_id.partner_id.name', 'ilike', options['filter_search_bar']),
                ('partner_id.name', 'ilike', options['filter_search_bar']),
            ]

        options['forced_domain'] = options.get('forced_domain', []) + domain

        if self.env.user.has_group('base.group_multi_currency'):
            options['multi_currency'] = True

        columns_to_hide = []
        options['hide_account'] = (previous_options or {}).get('hide_account', False)
        columns_to_hide += ['journal_code', 'account_code', 'matching_number'] if options['hide_account'] else []

        options['hide_debit_credit'] = (previous_options or {}).get('hide_debit_credit', False)
        columns_to_hide += ['debit', 'credit'] if options['hide_debit_credit'] else ['amount']

        options['hide_description'] = (previous_options or {}).get('hide_description', False)
        columns_to_hide += ['description'] if options['hide_description'] else []

        options['hide_bill'] = (previous_options or {}).get('hide_bill', False)
        columns_to_hide += ['bill_ref'] if options['hide_bill'] else []

        options['hide_po'] = (previous_options or {}).get('hide_po', False)
        columns_to_hide += ['po_ref'] if options['hide_po'] else []

        options['columns'] = [col for col in options['columns'] if col['expression_label'] not in columns_to_hide]

        options['buttons'].append({
            'name': _('Send'),
            'action': 'action_send_statements',
            'sequence': 90,
            'always_show': True,
        })