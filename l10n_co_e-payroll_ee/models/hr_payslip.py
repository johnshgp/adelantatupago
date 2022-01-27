# -*- coding: utf-8 -*-
import io

from odoo import api, fields, models, _, tools
from odoo.exceptions import Warning, UserError, ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import *
from pytz import timezone
import random

import logging

_logger = logging.getLogger(__name__)


class HrPaySlip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'hr.payslip.abstract']

    def hook_mail_template(self):
        return "email_template_hr_payslip"

    def refund_sheet(self):
        for payslip in self:
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            number = copied_payslip.number or self.env["ir.sequence"].next_by_code(
                "salary.slip"
            )
            copied_payslip.write({"number": number, 'previous_cune': payslip.current_cune, 'type_note': '1'})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'),
                      (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }
