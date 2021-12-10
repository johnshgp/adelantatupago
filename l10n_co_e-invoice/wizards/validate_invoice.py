# -*- coding: utf-8 -*-

from odoo import models, api

class ValidateInvoice(models.TransientModel):
    _name = 'ati.validate.invoice'
    _description = "Wizard - Validate multiple invoice"

    def validate_invoice(self):
        invoices = self._context.get('active_ids')
        for i in invoices:
            invoice_tmp = self.env['account.move'].browse(i)
            invoice_tmp.action_post()
            invoice_tmp.validate_dian()
