from odoo import models, api, _
from odoo.tools import SQL


class GeneralLedgerCustomHandlerInherited(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    @api.model
    def _get_aml_values(self, report, options, expanded_account_ids, offset=0, limit=None):
        # Call super to get existing aml results
        rslt, has_more = super()._get_aml_values(report, options, expanded_account_ids, offset=offset, limit=limit)

        AnalyticAccount = self.env['account.analytic.account']

        for account_id, account_data in rslt.items():
            for aml_key, column_group_dict in account_data.items():
                for column_group_key, aml_result in column_group_dict.items():
                    if not aml_result:
                        continue

                    # Use your custom reference field (replace x_reference with your field)
                    aml_result['reference'] = aml_result.get('move_name') or ''
                    aml_result['description'] = aml_result.get('name') or ''
                    aml_result['po_ref'] = aml_result.get('po_number') or ''
                    aml_result['bill_ref'] = aml_result.get('ref') or ''
                    analytic_dist = aml_result.get('analytical_acc') or {}
                    analytic_labels = []

                    for analytic_id, percentage in analytic_dist.items():
                        analytic = AnalyticAccount.browse(int(analytic_id))
                        if analytic.exists():
                            analytic_labels.append(
                                f"{analytic.name} ({percentage}%)"
                            )

                    aml_result['analytical_acc'] = ", ".join(analytic_labels)

                    # Remove communication column if needed
                    aml_result.pop('communication', None)

        return rslt, has_more

    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None) -> SQL:
        additional_domain = [('account_id', 'in', expanded_account_ids)] if expanded_account_ids is not None else None
        queries = []
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')

        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(group_options, domain=additional_domain, date_scope='strict_range')
            account_alias = query.join(lhs_alias='account_move_line', lhs_column='account_id',
                                       rhs_table='account_account', rhs_column='id', link='account_id')
            account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)
            account_name = self.env['account.account']._field_to_sql(account_alias, 'name')
            account_type = self.env['account.account']._field_to_sql(account_alias, 'account_type')

            query_sql = SQL(
                '''
                SELECT
                    account_move_line.id,
                    account_move_line.date,
                    account_move_line.date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.analytic_distribution AS analytical_acc,
                    COALESCE(account_move_line.invoice_date, account_move_line.date) AS invoice_date,
                    %(debit_select)s AS debit,
                    %(credit_select)s AS credit,
                    %(balance_select)s AS balance,
                    move.name AS move_name,
                    move.po_number AS po_number,
                    company.currency_id AS company_currency_id,
                    partner.name AS partner_name,
                    move.move_type AS move_type,
                    %(account_code)s AS account_code,
                    %(account_name)s AS account_name,
                    %(account_type)s AS account_type,
                    journal.code AS journal_code,
                    %(journal_name)s AS journal_name,
                    full_rec.id AS full_rec_name,
                    %(column_group_key)s AS column_group_key
                FROM %(table_references)s
                JOIN account_move move ON move.id = account_move_line.move_id
                LEFT JOIN account_payment payment ON payment.id = account_move_line.payment_id
                %(currency_table_join)s
                LEFT JOIN res_company company ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
                LEFT JOIN account_journal journal ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec ON full_rec.id = account_move_line.full_reconcile_id
                WHERE %(search_condition)s
                ORDER BY account_move_line.date, account_move_line.move_name, account_move_line.id
                ''',
                account_code=account_code,
                account_name=account_name,
                account_type=account_type,
                journal_name=journal_name,
                column_group_key=column_group_key,
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join(group_options),
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                search_condition=query.where_clause,
            )
            queries.append(query_sql)

        full_query = SQL(" UNION ALL ").join(SQL("(%s)", query) for query in queries)

        if offset:
            full_query = SQL('%s OFFSET %s ', full_query, offset)
        if limit:
            full_query = SQL('%s LIMIT %s ', full_query, limit)

        return full_query

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # Example: remove "communication" column
        options['columns'] = [
            col for col in options['columns']
            if col.get('expression_label') != 'communication'
        ]

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