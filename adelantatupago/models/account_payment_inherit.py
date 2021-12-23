# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    empleador = fields.Many2one(comodel_name="res.partner", string="Empleador")

    def action_post(self):
        result = super(AccountPaymentInherit, self).action_post()
        if self.empleador:
            move_line_vals = []

            #Diario a utilizar
            diario = self.env['account.journal'].browse(int(self.env['ir.config_parameter'].sudo().get_param('adelantatupago.journal_def')))

            line_cliente =(0, 0, {'account_id': self.partner_id.property_account_payable_id.id,
                            'partner_id': self.partner_id.id,
                            'credit': self.amount})
            move_line_vals.append(line_cliente)

            # Validando cliente tercero y creando linea de tercero, se toma cuenta a pagar de tercero para registrar el movimiento
            line_tercero =(0, 0, {'account_id': self.empleador.property_account_receivable_id.id,
                                'partner_id': self.empleador.id,
                                'debit': self.amount})


            move_line_vals.append(line_tercero)

            #Se crea asiento contable
            account = self.env['account.move'].create({
                'ref': self.name,
                'journal_id': diario.id,
                'invoice_payment_term_id': 1,
                'line_ids': move_line_vals,
                'date': self.date,
                'move_type': 'entry'
            })

            #Se Valida el asiento contable
            account.action_post()

        return result