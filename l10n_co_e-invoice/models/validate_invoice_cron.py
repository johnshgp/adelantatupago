# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class ValidateInvoiceCron(models.TransientModel):
    _name = "validate.invoice.cron"

    def validate_invoice(self):
        inv_to_validate = self.env['account.move'].search([('validate_cron','=',True),('state','=','draft')])
        for i in inv_to_validate:
            i.action_post()
            i.validate_dian()
            if i.state_dian_document == 'exitoso':
                i.pago_tercero()
            elif i.state_dian_document == 'por_validar':
                i.validate_dian()
                if i.state_dian_document == 'exitoso':
                    i.pago_tercero()

        inv_to_validate_dian = self.env['account.move'].sudo().search([('validate_cron','=',True),('state','=','posted'),('state_dian_document','!=','exitoso')])
        for idian in inv_to_validate_dian:
            idian.validate_dian()
            if idian.pago_tercero_creado == False and idian.state_dian_document == 'exitoso':
                idian.pago_tercero()
            elif idian.state_dian_document == 'por_validar':
                idian.validate_dian()
                if idian.pago_tercero_creado == False and idian.state_dian_document == 'exitoso':
                    idian.pago_tercero()
                    
                    
        inv_to_validate_dian_false = self.env['account.move'].sudo().search([('validate_cron','=',True),('state','=','posted'),('diancode_id.state','=',False)])
        sql = "select am.id from account_move am, dian_document dd where am.validate_cron is true and am.state = 'posted' and dd.document_id = am.id and dd.state != 'exitoso';"
        self.env.cr.execute(sql)
        sql_result = self.env.cr.dictfetchall()
        
        
        ids_invoice = self.env['account.move'].sudo().browse([n.get('id') for n in sql_result])
        _logger.warning('inv_to_validate: {0}, inv_to_validate_dian: {1}, idianf: {2}********** Facturas: {3}'.format(inv_to_validate,inv_to_validate_dian,inv_to_validate_dian_false,ids_invoice))                  
  
