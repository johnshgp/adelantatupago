# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    pago_tercero_creado = fields.Boolean(string="Pago a tercero creado", default=False)

    def pago_tercero(self):

        if self.pago_tercero_creado:
            return False

        move_line_vals = []
        cuenta = self.env['account.account']

        #linea account_move_id a conciliar
        line_id_pagar = self.env['account.move.line']
        for line in self.line_ids:
            if line.account_id.user_type_id.type == 'receivable':
                cuenta = self.env['account.account'].browse(line.account_id.id)

        #Diario a utilizar
        diario = self.env['account.journal'].browse(int(self.env['ir.config_parameter'].sudo().get_param('adelantatupago.journal_def')))

        line_cliente =(0, 0, {'account_id': cuenta.id,
                        'partner_id': self.partner_id.id,
                        'credit': self.amount_total})
        move_line_vals.append(line_cliente)

        # Validando cliente tercero y creando linea de tercero, se toma cuenta a pagar de tercero para registrar el movimiento
        if self.tercero_relacionado:
            line_tercero =(0, 0, {'account_id': self.tercero_relacionado.property_account_receivable_id.id,
                            'partner_id': self.tercero_relacionado.id,
                            'debit': self.amount_total})
        else:
            raise ValidationError('No se establecio tercero relacionado para crear un pago')


        move_line_vals.append(line_tercero)
        
        #Se crea asiento contable
        account = self.env['account.move'].create({
            'ref': self.name,
            'journal_id': diario.id,
            'invoice_payment_term_id': 1,
            'line_ids': move_line_vals,
            'date': self.invoice_date,
            'move_type': 'entry'
        })
        
        #Se Valida el asiento contable
        account.action_post()

        #Se busca la linea a conciliar con la factura
        for line in account.line_ids:
            if line.credit == self.amount_total:
                line_id_pagar = line
        #Se pasa el id de la linea buscada en el for anterior para conciliar con factura
        self.js_assign_outstanding_line(line_id_pagar.id)

        #Se confirma que la factura fue pagada a travez del metodo de tercero
        self.pago_tercero_creado = True
