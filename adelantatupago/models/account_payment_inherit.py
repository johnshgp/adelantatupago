# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    empleador = fields.Many2one(comodel_name="res.partner", string="Empleador")

    def action_post(self):
        for rec in self:
            result = super(AccountPaymentInherit, rec).action_post()
            if rec.empleador:
                move_line_vals = []

                #Diario a utilizar
                diario = rec.env['account.journal'].browse(int(rec.env['ir.config_parameter'].sudo().get_param('adelantatupago.journal_def')))

                line_cliente =(0, 0, {'account_id': rec.partner_id.property_account_payable_id.id,
                                'partner_id': rec.partner_id.id,
                                'credit': rec.amount})
                move_line_vals.append(line_cliente)

                # Validando cliente tercero y creando linea de tercero, se toma cuenta a pagar de tercero para registrar el movimiento
                line_tercero =(0, 0, {'account_id': rec.empleador.property_account_receivable_id.id,
                                    'partner_id': rec.empleador.id,
                                    'debit': rec.amount})


                move_line_vals.append(line_tercero)

                #Se crea asiento contable
                account = rec.env['account.move'].sudo().create({
                    'ref': rec.name,
                    'journal_id': diario.id,
                    'invoice_payment_term_id': 1,
                    'line_ids': move_line_vals,
                    'date': rec.date,
                    'move_type': 'entry'
                })

                #Se Valida el asiento contable
                account.action_post()

        return result
    
    def action_draft(self):
        for rec in self:
            result = super(AccountPaymentInherit, rec).action_draft()
            if rec.empleador:
                #asiento a cancelar
                amcancel = rec.env['account.move'].search([('ref','=',rec.name),('state','=','posted')])

                if len(amcancel) > 0:
                    # se pasa asiento a borrador
                    amcancel.button_draft()
                    # se pasa asiento a cancelado
                    amcancel.button_cancel()

        return result    
