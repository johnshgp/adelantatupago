# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ValidateInvoiceCron(models.TransientModel):
    _name = "validate.invoice.cron"

    def validate_invoice(self):
        inv_to_validate = self.env['account.move'].search([('validate_cron','=',True),('state','=','draft')])
        for i in inv_to_validate:
            i.action_post()
            i.validate_dian()
            if i.state_dian_document == 'Exitoso':
                i.pago_tercero()
            elif i.state_dian_document == 'Por validar':
                i.validate_dian()
                if i.state_dian_document == 'Exitoso':
                    i.pago_tercero()

        inv_to_validate_dian = self.env['account.move'].search([('validate_cron','=',True),('state','=','posted'),('state_dian_document','!=','Existoso')])
        for idian in inv_to_validate_dian:
            idian.validate_dian()
            if idian.pago_tercero_creado == False and idian.state_dian_document == 'Exitoso':
                idian.pago_tercero()
            elif i.state_dian_document == 'Por validar':
                idian.validate_dian()
                if idian.pago_tercero_creado == False and idian.state_dian_document == 'Exitoso':
                    idian.pago_tercero()
