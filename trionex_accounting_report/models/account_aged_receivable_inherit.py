from odoo import models


class TrnAgedHandler(models.AbstractModel):
    _inherit = "account.aged.partner.balance.report.handler"

    def _custom_line_postprocessor(self, report, options, lines, **kwargs):
        """
        Fill our XML-added columns:
          - expression_label 'reference'    -> aml.move_id.name (INV223344)
          - expression_label 'description'  -> aml.name (payment line label / journal item label)
        """
        lines = super()._custom_line_postprocessor(report, options, lines, **kwargs)

        # options['columns'] is a list of dicts in display order:
        # each dict typically contains 'expression_label'
        cols = options.get("columns", [])
        expr_to_idx = {}
        for idx, c in enumerate(cols):
            label = c.get("expression_label")
            if label:
                expr_to_idx[label] = idx

        ref_idx = expr_to_idx.get("reference")
        po_number = expr_to_idx.get("po_ref")
        bill_number = expr_to_idx.get("bill_ref")
        desc_idx = expr_to_idx.get("description")

        if ref_idx is None and desc_idx is None and po_number is None and bill_number is None:
            return lines  # columns not present on this report

        # Collect account.move.line ids from report lines (batch browse)
        aml_ids = []
        aml_line_pairs = []

        for line in lines:
            line_id = line.get("id")
            if not line_id:
                continue

            # Odoo report helper: returns (model_name, res_id)
            if not hasattr(report, "_get_model_info_from_id"):
                continue

            model_name, res_id = report._get_model_info_from_id(line_id)

            if model_name == "account.move.line" and res_id:
                aml_ids.append(res_id)
                aml_line_pairs.append((res_id, line))

        if not aml_ids:
            return lines

        amls = self.env["account.move.line"].browse(list(set(aml_ids))).exists()
        aml_map = {aml.id: aml for aml in amls}

        def _set_text(line_dict, idx, value):
            cols_list = line_dict.get("columns") or []
            if idx is None:
                return
            if idx < 0 or idx >= len(cols_list):
                return
            # For text cells, 'name' is what is rendered.
            cols_list[idx] = {
                "name": value or "",
                "no_format": value or "",
            }

        for aml_id, line in aml_line_pairs:
            aml = aml_map.get(aml_id)
            if not aml:
                continue

            reference = aml.move_id.name or ""
            po_ref = aml.move_id.po_number or ""
            bill_ref = aml.move_id.ref or ""
            description = aml.name or ""

            _set_text(line, ref_idx, reference)
            _set_text(line, po_number, po_ref)
            _set_text(line, bill_number, bill_ref)
            _set_text(line, desc_idx, description)

        return lines

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        hidden_columns = set()

        options['multi_currency'] = report.env.user.has_group('base.group_multi_currency')
        options['show_currency'] = options['multi_currency'] and (previous_options or {}).get('show_currency', False)
        if not options['show_currency']:
            hidden_columns.update(['amount_currency', 'currency'])

        options['show_account'] = (previous_options or {}).get('show_account', False)
        if not options['show_account']:
            hidden_columns.add('account_name')

        options['show_description'] = (previous_options or {}).get('show_description', False)
        if not options['show_description']:
            hidden_columns.add('description')

        options['show_po'] = (previous_options or {}).get('show_po', False)
        if not options['show_po']:
            hidden_columns.add('po_ref')

        options['show_bill'] = (previous_options or {}).get('show_bill', False)
        if not options['show_bill']:
            hidden_columns.add('bill_ref')

        options['columns'] = [
            column for column in options['columns']
            if column['expression_label'] not in hidden_columns
        ]

        default_order_column = {
            'expression_label': 'invoice_date',
            'direction': 'ASC',
        }

        options['order_column'] = previous_options.get('order_column') or default_order_column
        options['aging_based_on'] = previous_options.get('aging_based_on') or 'base_on_maturity_date'
        options['aging_interval'] = previous_options.get('aging_interval') or 30

        # Set aging column names
        interval = options['aging_interval']
        for column in options['columns']:
            if column['expression_label'].startswith('period'):
                period_number = int(column['expression_label'].replace('period', '')) - 1
                if 0 <= period_number < 4:
                    column['name'] = f'{interval * period_number + 1}-{interval * (period_number + 1)}'


