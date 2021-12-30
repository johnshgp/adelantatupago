# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import base64
import csv
from datetime import date as dt
import logging
_logger = logging.getLogger(__name__)
class ImportPayments(models.Model):
    _name = 'import.payments'
    _description = 'import.payments'
        
    def btn_process(self):
        _payments_ids = ""
        _procesados = ""
        _procesados_stock = ""
        _noprocesados = ""
        vals={}    
        self.ensure_one()
        if not self.delimiter:
            raise ValidationError('Debe ingresar el delimitador')
        if not self.payments_file:
            raise ValidationError('Debe seleccionar el archivo')
        if self.state != 'draft':
            raise ValidationError('Archivo procesado!')
        self.file_content = base64.decodebytes(self.payments_file)

        lines = self.file_content.split('\n')
        for i,line in enumerate(lines):
            if self.skip_first_line and i == 0:
                continue
            lista = line.split(self.delimiter)
            if len(lista) == 6:

                dato = lista[0]
                doc_empleado = lista[1]
                concepto = lista[2]
                fecha = lista[3]
                importe = lista[4]
                cuenta_bancaria = lista[5]

                vals.clear()

                # Carga vals
                if doc_empleado != '':
                    
                    if doc_empleado != '':
                        cliente_tmp = self.env['res.partner'].search([('vat','=',doc_empleado)])
                        if len(cliente_tmp) == 0:
                            raise ValidationError("El CSV no se procesara porque el Cliente con Documento de empleado N° {0} no existe, en la linea {1}, contenido de linea: {2}".format(doc_empleado, i, line))
                        else:
                            cbancaria_tmp = self.env['res.partner.bank'].search([('acc_number','=',cuenta_bancaria),('partner_id','=',self.env.company.id)])


                    else:
                        raise ValidationError("El CSV no se procesara por falta de Documento Empleado en la linea {0}, contenido de linea: {1}".format(i, line))



                    if fecha != '':
                        fecha = datetime.strptime(fecha, '%Y-%m-%d')
                    else:
                        raise ValidationError("El CSV no se procesara por falta de Fecha en la linea {0}, contenido de linea: {1}".format(i, line))

                    
                    
                    if importe == '':
                        raise ValidationError("El CSV no se procesara por falta de importe en la linea {0}, contenido de linea: {1}".format(i, line))
                    else:
                        importe = importe.replace('.','')
                        importe = importe.replace(',','.')
                        importe = importe.replace('$','')
                        importe = float(importe.replace('\r',''))

                    if cuenta_bancaria != '':
                        dierio_tmp = self.env['account.journal'].search([('bank_account_id.acc_number','=',cuenta_bancaria)])
                        if len(dierio_tmp) == 0:
                            raise ValidationError("El CSV no se procesara porque la cuenta bancaria N° {0} no existe, en la linea {1}, contenido de linea: {2}".format(cuenta_bancaria, i, line))

                    else:
                        raise ValidationError("El CSV no se procesara por falta de cuenta bancaria en la linea {0}, contenido de linea: {1}".format(i, line))
    

                    vals = {
                        "date": fecha,
                        "payment_type": "inbound",
                        "partner_type": "customer",
                        "partner_id": cliente_tmp.id,
                        "destination_account_id": cliente_tmp.property_account_receivable_id.id,
                        "amount": importe,
                        "journal_id": dierio_tmp.id,
                        "partner_bank_id": cbancaria_tmp.id,
                        "ref": concepto
                    }

                    pago = self.env['account.payment'].sudo().create(vals)

                    _payments_ids += "{} \n".format(str(pago.id))
                    _procesados += "{} \n".format("id:" + str(pago.id) + "| " + doc_empleado + " $" + str(importe))
                else:
                    _noprocesados += "{} \n".format(doc_empleado + " $" + str(importe))

            else:
                raise ValidationError("El CSV no se procesara por estar mal formado en la linea {0}, contenido de linea: {1}".format(i, line))
                
        self.payments_ids = _payments_ids
        self.pagos_creados = _procesados
        self.not_processed_content = _noprocesados
        self.state = 'processed'

    def btn_validated_reconciled(self):
        if len(self.pagos_creados)>0:

            lines = self.payments_ids.split('\n')
            for i,payment_id in enumerate(lines):
                #se salta la ultima linea del Text ya que no contiene nada
                if i == len(lines) - 1:
                    continue

                # Se busca con id el pago y se valida
                pago_tmp = self.env['account.payment'].browse(int(payment_id))
                pago_tmp.action_post()
                
                # Se buscan todos los asientos contables con cuenta por pagar del cliente para luego ser conciliados con el asiento contable del pago
                amls = self.env['account.move.line'].search([('partner_id','=',pago_tmp.partner_id.id),
                                                            ('amount_residual','>',0),
                                                            ('account_id.id','=',pago_tmp.partner_id.property_account_receivable_id.id)])
                if len(amls) > 0:
                    # se buscar asiento conbale con cuenta por pagar del pago
                    for l in pago_tmp.move_id.line_ids:
                        if l.account_id.id == pago_tmp.partner_id.property_account_receivable_id.id:
                            amls += l
                    # Conciliamos el pago con todos los asientos contables buscados
                    amls.reconcile()
                else:
                    _logger.warning('************ No se encuentran asientos contables para conciliar el pago con id: {0}'.format(pago_tmp.id))
            

        else:
            raise ValidationError("No hay registros de pagos por validar")

        self.state = 'reconciled'

    payments_ids = fields.Text('Ids de pagos')
    name = fields.Char('Nombre')
    payments_file = fields.Binary('Archivo')
    delimiter = fields.Char('Delimitador',default=";")
    state = fields.Selection(selection=[
        ('draft','Borrador'),
        ('processed','Procesado'),
        ('reconciled','Validados y conciliados')],
        string='Estado',default='draft')
    file_content = fields.Text('Texto archivo')
    not_processed_content = fields.Text('Texto no procesado')
    pagos_creados = fields.Text('Pagos Creados')
    skip_first_line = fields.Boolean('Saltear primera linea',default=True)
