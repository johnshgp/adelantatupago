from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class ValidateInvoiceCronInherit(models.TransientModel):
    _inherit = "validate.invoice.cron"

    def validate_invoice(self):
        result = super(ValidateInvoiceCronInherit, self).validate_invoice()
        inv_to_payments = self.env['account.move'].search([('validate_cron','=',True),('state','=','posted'),('pago_tercero_creado','=',False)])
        for i in inv_to_payments:
            if i.state_dian_document == 'exitoso':
                i.pago_tercero()
            elif i.state_dian_document == 'por_validar':
                i.validate_dian()
                if i.state_dian_document == 'exitoso':
                    i.pago_tercero()
        
        
        _logger.warning('inv_to_payments: {0}'.format(inv_to_payments))

        return result     
