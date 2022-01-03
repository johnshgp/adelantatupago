# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

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
                    
                    
        inv_to_validate_dian_false = self.env['account.move'].sudo().search([('validate_cron','=',True),('state','=','posted'),('diancode_id.state','=',[])])
        #for idianf in inv_to_validate_dian_false:
        #    idianf.validate_dian()
        #    if idianf.pago_tercero_creado == False and idianf.state_dian_document == 'exitoso':
        #        idianf.pago_tercero()
        #    elif idianf.state_dian_document == 'por_validar':
        #        idianf.validate_dian()
        #        if idianf.pago_tercero_creado == False and idianf.state_dian_document == 'exitoso':
        #            idianf.pago_tercero()
        invoice = self.env['account.move'].sudo().browse(16)
        raise ValidationError('inv_to_validate: {0}, inv_to_validate_dian: {1}, idianf: {2}********** Factura: {3}, state_dian{4}, state{5} '.format(inv_to_validate,inv_to_validate_dian,inv_to_validate_dian_false,invoice.name,invoice.diancode_id.state,invoice.state))                  
  
