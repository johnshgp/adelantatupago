# -*- coding: utf-8 -*-
from typing import Sequence
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime, timedelta, date
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
import logging
_logger = logging.getLogger(__name__)

class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    validate_cron = fields.Boolean(string="Validar con CRON", default=False, copy=False)
    diancode_id = fields.Many2one('dian.document', string="Código DIAN", readonly=True, tracking=True,)
    state_dian_document = fields.Selection(string="Estado documento DIAN", related='diancode_id.state')
    shipping_response = fields.Selection(string="Respuesta de envío DIAN", related='diancode_id.shipping_response')
    response_document_dian = fields.Selection(string="Respuesta de consulta DIAN", related='diancode_id.response_document_dian')
    email_response = fields.Selection(string='Decisión del cliente', related='diancode_id.email_response', tracking=True,)
    response_message_dian = fields.Text(string='Mensaje de respuesta DIAN', related='diancode_id.response_message_dian')
    is_debit_note = fields.Boolean(string='Nota de débito', default=False, tracking=True,)

    QR_code = fields.Binary(string='Código QR', readonly=True, related = 'diancode_id.QR_code', tracking=True,)
    cufe = fields.Char(string='CUFE', readonly=True, related = 'diancode_id.cufe')
    xml_response_dian = fields.Text(string='Contenido XML de la respuesta DIAN', readonly=True, related = 'diancode_id.xml_response_dian')
    mandante_id = fields.Many2one('res.partner', 'Mandante')

    contingency_3 = fields.Boolean(string='Contingencia tipo 3', default=False, help='Cuando el facturador no puede expedir la factura electrónica por inconvenientes tecnológicos')
    contingency_4 = fields.Boolean(string='Contingencia tipo 4', default=False, help='Cuando las causas son atribuibles a situaciones de índole tecnológico a cargo de la DIAN')
    # contingency_type = fields.Selection([('no_contingency','Sin contigencia'),
    #     ('contingency_type3','Contigencia tipo 3 - Cuando el facturador no puede expedir la factura electrónica por inconvenientes tecnológicos'),
    #     ('contingency_type4','Contigencia tipo 4 - Cuando las causas son atribuibles a situaciones de índole tecnológico a cargo de la DIAN')], 
    #     string='Tipo de contigencia', required=True, default='no_contingency')
    xml_response_contingency_dian = fields.Text(string='Mensaje de respuesta DIAN al envío de la contigencia', related='diancode_id.xml_response_contingency_dian')
    state_contingency = fields.Selection(string="Estatus de contingencia", related='diancode_id.state_contingency')
    contingency_invoice_number = fields.Char('Número de factura de contigencia')
    count_error_DIAN =  fields.Integer(string="contador de intentos fallidos por problemas de la DIAN", related='diancode_id.count_error_DIAN')
    in_contingency_4 = fields.Boolean(string="En contingencia", related='company_id.in_contingency_4')
    exists_invoice_contingency_4 = fields.Boolean(string="Cantidad de facturas con contingencia 4 sin reportar a la DIAN", related='company_id.exists_invoice_contingency_4')
    archivo_xml_invoice = fields.Binary('archivo DIAN xml de factura', readonly=True, tracking=True,)
    xml_adjunto_ids = fields.Many2many('ir.attachment', string="Archivo adjunto xml de factura", tracking=True,)

    hide_button_dian = fields.Boolean(string="Ocultar", compute='_computeHidebuttonDian', default=False)

    concepto_credit_note = fields.Selection(
		[('1', 'Devolución parcial de los bienes y/o no aceptación parcial del servicio'),
		 ('2', 'Anulación de factura electrónica'),
		 ('3', 'Rebaja  o descuento parcial o total'),
		 ('4', 'Ajuste de precio'),
		 ('5', 'Otros')], u'Concepto Corrección')

    concept_debit_note = fields.Selection(
        [('1', 'Intereses'),
		 ('2', 'Gastos por cobrar'),
		 ('3', 'Cambio del valor'),
		 ('4', 'Otros')], u'Concepto Corrección')
         
    def _computeHidebuttonDian(self):
        for x in self:
            if x.journal_id:
                if x.journal_id.secure_sequence_id.use_dian_control:
                    x.hide_button_dian = True
                else:
                    x.hide_button_dian = False
                    
    #@api.multi
    def write(self, vals):
        for invoice in self:
            before_state = invoice.state
            
            after_state = invoice.state

            if 'state' in vals:
                after_state = vals['state']


            rec_dian_document = self.env['dian.document'].search([('document_id', '=', invoice.id)])
            if not rec_dian_document:
                if before_state == 'draft' and after_state == 'posted' and invoice.move_type == 'out_invoice' and not invoice.debit_origin_id:
                    new_dian_document = invoice.env['dian.document'].sudo().create({'document_id' : invoice.id, 'document_type' : 'f'})

                if before_state == 'draft' and after_state == 'posted' and invoice.move_type == 'out_refund':
                    new_dian_document = invoice.env['dian.document'].sudo().create({'document_id' : invoice.id, 'document_type' : 'c'})
                    
                if before_state == 'draft' and after_state == 'posted' and invoice.move_type == 'out_invoice' and invoice.debit_origin_id:
                    new_dian_document = invoice.env['dian.document'].sudo().create({'document_id' : invoice.id, 'document_type' : 'd'})

        return super(AccountMoveInherit, self).write(vals)

    @api.model
    def create(self, vals):
        if 'move_type' in vals:
            if vals['move_type'] == 'out_refund':
                if 'refund_invoice_id' in vals and 'invoice_payment_term_id' in vals:
                    rec_account_invoice = self.env['account.move'].search([('id', '=', vals['refund_invoice_id'])])
                    vals['payment_term_id'] = rec_account_invoice.payment_term_id.id
        return super(AccountMoveInherit, self).create(vals)

 
    @api.onchange('contingency_3')
    def _onchange_contingency_3(self):
        if self.contingency_3 == False:
            self.contingency_invoice_number = ''


    #@api.multi
    def button_cancel(self):
        if self.state_dian_document == 'exitoso':
            raise ValidationError('Una factura en estado exitoso, no puede ser cancelada')

        rec = super(AccountMoveInherit, self).button_cancel()
        return rec        

    #@api.multi
    def action_invoice_dian_resend(self):
        """ Open a window to compose an email, with the edi invoice dian template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('l10n_co_e-invoice.email_template_edi_invoice_dian', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }


    #@api.multi
    #verificar invoice_line_ids - tax_line_ids
    def create_nota_debit(self):
        invoice_tax_lines_new = []
        invoice_new = self.env['account.move']
        invoice_new = invoice_new.create(
            {
            #'journal' : self.journal_id.id,
            'partner_id' : self.partner_id.id,
            'company_id' : self.company_id.id,
            'state' : 'draft',
            'move_type' : self.move_type,
            'is_move_sent' : self.is_move_sent,
            'invoice_origin' : self.name,
            #'account_id' : self.account_id.id,
            'invoice_date' : date.today(),
            'invoice_payment_term_id' : self.invoice_payment_term_id.id,
            'date' : date.today(),
            'invoice_date_due' : self.invoice_date_due,
            'user_id' : self.env.uid,
            'currency_id' : self.currency_id.id,
            'commercial_partner_id' : self.commercial_partner_id.id,
            'partner_shipping_id' : self.partner_shipping_id.id,
            'team_id' : self.team_id.id,
            'resolution_date' : self.resolution_date,
            'resolution_date_to' : self.resolution_date_to,
            'resolution_number_from' : self.resolution_number_from,
            'resolution_number_to' : self.resolution_number_to,
            'resolution_number' : self.resolution_number,
            'is_debit_note' : True,
            })

        print(invoice_new)

        if invoice_new:
            for line_invoice in self.invoice_line_ids:
                invoice_line_new = []  
                invoice_tax_line_new = []
                invoice_line_tax = []
                for invoice_line_tax in line_invoice.tax_ids:
                    invoice_tax_line_new.append((0,0,{
                        'tax_id' : invoice_line_tax.id,
                     }))

                invoice_line_new.append((0,0,{
                    'move_id' : invoice_new.id, 
                    #'invoice_origin' : line_invoice.invoice_origin, 
                    'price_unit' : line_invoice.price_unit, 
                    'price_subtotal' : line_invoice.price_subtotal, 
                    'currency_id' : line_invoice.currency_id.id,
                    'product_uom_id' : line_invoice.product_uom_id.id, 
                    'partner_id' : line_invoice.partner_id.id, 
                    'sequence' : line_invoice.sequence,  
                    'company_id' : line_invoice.company_id.id,  
                    #'analytic_account_id' : line_invoice.account_analytic_id.id if line_invoice.account_analytic_id else None,  
                    'account_id' : line_invoice.account_id.id if line_invoice.account_id else None,  
                    #'price_subtotal_signed' : line_invoice.price_subtotal_signed, 
                    'name' : line_invoice.name,  
                    'product_id' : line_invoice.product_id.id,  
                    'move_id' : line_invoice.move_id.id,
                    'quantity' : line_invoice.quantity,
                    #'layout_category_sequence' : line_invoice.layout_category_sequence,
                    #'layout_category_id' : line_invoice.layout_category_id.id,
                    'purchase_line_id' : line_invoice.purchase_line_id.id,
                    'tax_ids' : line_invoice.tax_ids,
                    }))           
                invoice_new.invoice_line_ids = invoice_line_new  

            """
            for invoice_tax_line in self.tax_line_ids:
                invoice_tax_lines_new.append((0,0,{
                    'account_id' : invoice_tax_line.account_id.id,
                    'name' : invoice_tax_line.name,
                    'sequence' : invoice_tax_line.sequence,
                    'move_id' : invoice_new.id,
                    'manual' : invoice_tax_line.manual,
                    'company_id' : invoice_tax_line.company_id.id,
                    'currency_id' : invoice_tax_line.currency_id.id,
                    'account_analytic_id' : invoice_tax_line.account_analytic_id.id,
                    'tax_id' : invoice_tax_line.tax_id.id,
                    'amount' : invoice_tax_line.amount,
                    }))
            invoice_new.tax_line_ids = invoice_tax_lines_new
            """

        #migrate to v13
        my_view = self.env.ref('account.view_move_form')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'name' : self.name,
            'view_id': my_view.id,
            'view_mode': 'form',
            'res_id': invoice_new.id,
        }  


    #@api.multi
    def action_post(self):
        mensaje = ''
        rec = super(AccountMoveInherit, self).action_post()
        if self.journal_id.secure_sequence_id.use_dian_control:
            if self.move_type == 'out_invoice':
                if self.debit_origin_id:
                    rec_sequence_nd = self.env['ir.sequence']
                    sequence_code = self.journal_id.debit_note_sequence_id.code
                    print(self.journal_id.debit_note_sequence_id)
                    if sequence_code == False:
                        raise ValidationError('Debe definir el código de secuencia de la nota de débito en Ajuste / Técnico / Secuencia')
                    number = rec_sequence_nd.next_by_code(sequence_code)
                    #self.move_name = number
                    self.name = number

                rec_resolution_invoice = self.journal_id.secure_sequence_id.dian_resolution_ids.filtered(lambda r: r.active_resolution == True)
                # Verifica datos de la resolucion DIAN
                if not rec_resolution_invoice:
                    mensaje += '- La factura no tiene resolución DIAN asociada.' + '\n'

                if not rec_resolution_invoice:
                    mensaje += '- La resolución DIAN asociada a la factura no existe.' + '\n'
                if not rec_resolution_invoice.technical_key:
                    mensaje += '- La resolución DIAN  no tiene asociada la clave técnica.' + '\n'

                if mensaje:
                    mensaje += '- El diario seleccionado es '+ str((self.journal_id.name.encode('utf-8'))) +', verifique si es el correcto, este debe tener bien configurada la clave tecnica y el numero de resolucion que la DIAN le otorgo' + '\n'

                # Verifica datos de la compañia
                company = self.company_id
                partner = company.partner_id 
                if not company.document_repository:
                    mensaje += '- Se debe asociar un repositorio en donde se almacenarán los archivos de FE.' + '\n'
                if not company.software_identification_code:
                    mensaje += '- No se encuentra registrado el código de identificación del software.' + '\n'
                if not company.password_environment:
                    mensaje += '- No se encuentra registrado el password del ambiente.' + '\n'
                if not partner.country_id.code:
                    mensaje += '- Su empresa no tiene registrado el país.' + '\n'
                if not partner.vat:
                    mensaje += '- Su empresa no tiene registrado el NIT.' + '\n'
                if not partner.company_type:
                    mensaje += '- Su empresa no está identificada como persona juríduca o persona natural.' + '\n'
                if not partner.l10n_co_document_code:
                    mensaje += '- Su empresa no tiene asociada un tipo de documento.' + '\n'
                if not partner.state_id:
                    mensaje += '- Su empresa no tiene asociada un estado.' + '\n'
                if not partner.tribute_id:
                    mensaje += '- Su empresa no tiene asociada un tributo.' + '\n' 
                if not partner.fiscal_responsability_ids:
                    mensaje += '- Su empresa no tiene asociada una responsabilidad fiscal.' + '\n' 
                if not company.operation_type:
                    mensaje += '- Su empresa no tiene asociada un tipo de operación.' + '\n' 
                if not partner.xcity:
                    mensaje += '- Su empresa no tiene asociada un municipio.' + '\n'
                if not partner.street:
                    mensaje += '- Su empresa no tiene asocida una dirección.' + '\n'
                if not company.trade_name:
                    mensaje += '- Su empresa no tiene definida una razón social.' + '\n'
                if not company.digital_certificate:
                    mensaje += '- No se ha registrado el certificado digital.' + '\n'
                if not company.certificate_key:
                    mensaje += '- No se ha registrado la clave del certificado.' + '\n'
                if not company.issuer_name:
                    mensaje += '- No se ha registrado el proveedor del certificado.' + '\n'
                if not company.serial_number:
                    mensaje += '- No se ha registrado el serial del certificado.' + '\n'
                # Verifica datos del cliente
                if not self.currency_id.name:
                    mensaje += '- El cliente no posee una moneda asociada.' + '\n'
                if not self.partner_id.company_type:
                    mensaje += '- No se ha definido si el cliente es una persona natural o juridica.' + '\n'
                if not self.partner_id.vat:
                    mensaje += '- El cliente no tiene registrado el NIT.' + '\n'
                if not self.partner_id.l10n_co_document_code:
                    mensaje += '- El cliente no tiene asociada un tipo de documento.' + '\n'
                if not self.partner_id.fiscal_responsability_ids:
                    mensaje += '- El cliente no tiene asociada una responsabilidad fiscal, para solucionarlo abra el cliente y busque asegure que el campo posicion fiscal tiene valor' + '\n'
                if not self.partner_id.country_id.code:
                    mensaje += '- El cliente no tiene asociada un país.' + '\n'
                if not self.partner_id.state_id.name:
                    mensaje += '- El cliente no tiene asociada un estado.' + '\n'
                if not self.partner_id.city:
                    mensaje += '- El cliente no tiene asociada una ciudad.' + '\n'
                if not self.partner_id.xcity.name:
                    mensaje += '- El cliente no tiene asociada un municipio.' + '\n'
                if not self.partner_id.street:
                    mensaje += '- El cliente no tiene asociada una dirección.' + '\n'
                if not self.partner_id.tribute_id:
                    mensaje += '- El cliente no tiene asociada un tributo de los indicados en la tabla 6.2.2 Tributos indicado en la tabla 6.2.2 Tributos, para solucionarlo abra el cliente y busque asegure que el campo tributos tiene valor' + '\n' 
                if not self.partner_id.email:
                    mensaje += '- El cliente no tiene definido un email.' + '\n'
                # Verifica que existan asociados impuestos al grupo de impuestos IVA, ICA y ICO  

                #migrate to v13 account.invoice.tax  
                rec_account_invoice_tax = self.env['account.move.line'].search([('move_id', '=', self.id), ('tax_line_id', '!=', None)])

                if self.invoice_line_ids:

                    for x in self.invoice_line_ids:

                        if len(x.tax_ids) > 1:
                            mensaje += '- Existen líneas de factura que poseen más de un impuesto asociado' + '\n'

                        if x.tax_ids:
                            for tax in x.tax_ids:
                                if tax.tax_group_fe not  in ['iva_fe','ica_fe','ico_fe','ret_fe']:
                                    mensaje += '- La factura contiene impuestos que no están asociados al grupo de impuestos DIAN FE.' + '\n'

                                if not tax.tributes:
                                    mensaje += '- Algunos impueso indicados en la factura no tiene un tributo asociado según los tributos indicados en la tabla 6.2.2 Tributos.' + '\n'
                
                
                if not self.invoice_payment_term_id:
                    mensaje += '- La factura no tiene un término de pago definido' + '\n'
                if mensaje:
                    raise ValidationError(mensaje)

        return rec


    #@api.multi
    def validate_dian(self):
        
        document_dian = self.env['dian.document'].search([('document_id', '=', self.id)])
	
        if not document_dian:
            if self.state == 'posted' and self.move_type == 'out_invoice' and self.is_debit_note == False:
                document_dian = self.env['dian.document'].sudo().create({'document_id': self.id, 'document_type': 'f'})	

        #if document_dian.exist_dian(document_dian.id) == False:
        if self.in_contingency_4:
            # Documento de ND
            if self.move_type == 'out_invoice' and self.debit_origin_id:
                raise ValidationError("No puede validar notas de débito mientras se encuentra en estado de contingencia tipo 4")
            # Documento de NC
            elif self.move_type == 'out_refund': 
                raise ValidationError("No puede validar notas de crédito mientras se encuentra en estado de contingencia tipo 4")
            if self.state_contingency == 'exitosa':
                raise ValidationError("Factura de contingencia tipo 4 ya fue enviada al cliente. Una vez se restablezca el servicio, debe pulsar este bóton para enviar la contingencia tipo 4 bota la DIAN")

        if document_dian.state == 'rechazado':
            document_dian.response_message_dian = ' '
            document_dian.xml_response_dian = ' '
            document_dian.xml_send_query_dian = ' '
            document_dian.response_message_dian = ' '
            document_dian.xml_document = ' '
            document_dian.xml_file_name = ' '
            document_dian.zip_file_name = ' '
            document_dian.cufe = ' '
            document_dian.date_document_dian = ' '
            document_dian.write({'state' : 'por_notificar', 'resend' : False})
            if self.in_contingency_4 == True and self.contingency_3 == False:
                document_type = document_dian.document_type
            else:
                document_type = document_dian.document_type if self.contingency_3 == False else 'contingency'
            document_dian.send_pending_dian(document_dian.id, document_type)

        if document_dian.state == ('por_notificar'):
            if self.in_contingency_4 == True and self.contingency_3 == False:
                document_type = document_dian.document_type
            else:
                document_type = document_dian.document_type if self.contingency_3 == False else 'contingency'
            document_dian.send_pending_dian(document_dian.id, document_type)

        company = self.env['res.company'].sudo().search([('id', '=', self.company_id.id)])
        # Ambiente pruebas
        if company.production == False and self.in_contingency_4 == False:
            if document_dian.state == 'por_validar':
                document_dian.request_validating_dian(document_dian.id)
        # Determina si existen facturas con contingencias tipo 4 que no han sidoenviadas a la DIAN
        #company.exists_invoice_contingency_4 = False
        documents_dian_contingency = self.env['dian.document'].search([('state', '=', 'por_notificar'), ('contingency_4', '=', True), ('document_type', '=', 'f')])
        for document_dian_contingency in documents_dian_contingency:
            company.exists_invoice_contingency_4 = True 
            break
        return
        


AccountMoveInherit()
