# -*- coding: utf-8 -*-
import io
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from pytz import timezone

from odoo import fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import first

_logger = logging.getLogger(__name__)

try:
    from lxml import etree
except:
    _logger.warning("Cannot import  etree *************************************")

from odoo.tools.translate import _

try:
    import pyqrcode
except ImportError:
    _logger.warning('Cannot import pyqrcode library ***************************')

try:
    import png
except ImportError:
    _logger.warning('Cannot import png library ********************************')

try:
    import hashlib
except ImportError:
    _logger.warning('Cannot import hashlib library ****************************')

try:
    import base64
except ImportError:
    _logger.warning('Cannot import base64 library *****************************')

try:
    import textwrap
except:
    _logger.warning("no se ha cargado textwrap ********************************")

try:
    import gzip
except:
    _logger.warning("no se ha cargado gzip ***********************")

import zipfile

try:
    import zlib

    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    import OpenSSL
    from OpenSSL import crypto

    type_ = crypto.FILETYPE_PEM
except:
    _logger.warning('Cannot import OpenSSL library')

try:
    import requests
except:
    _logger.warning("no se ha cargado requests")

try:
    import xmltodict
except ImportError:
    _logger.warning('Cannot import xmltodict library')

try:
    import uuid
except ImportError:
    _logger.warning('Cannot import uuid library')

try:
    import re
except ImportError:
    _logger.warning('Cannot import re library')

tipo_ambiente = {
    'PRODUCCION': '1',
    'PRUEBA': '2',
}

server_url = {
    'TEST': 'https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl',
    'PRODUCCION': 'https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl'
}

XML_TEMPLATE_NOMINA_INDIVIDUAL = 'l10n_co_e-payroll.nomina_electronica_individual'
XML_TEMPLATE_SIGNATURE = "l10n_co_e-payroll.nomina_electronica_signature"


class HrPaySlipAbstrct(models.AbstractModel):
    _name = 'hr.payslip.abstract'

    payroll_period = fields.Many2one("hr.payroll.period", string="Periodo de Nomina")
    xml_response_dian = fields.Text(string='Contenido XML de la respuesta DIAN', readonly=True, copy=False)
    xml_send_query_dian = fields.Text(string='Contenido XML de envío de consulta de documento DIAN', readonly=True,
                                      copy=False)
    response_message_dian = fields.Text(string="Respuesta DIAN", readonly=True, copy=False)
    ZipKey = fields.Char(string='Identificador del docuemnto enviado', readonly=True, copy=False)
    state_dian = fields.Selection([('por_notificar', 'Por notificar'),
                                   ('error', 'Error'),
                                   ('por_validar', 'Por validar'),
                                   ('exitoso', 'Exitoso'),
                                   ('rechazado', 'Rechazado')],
                                  string="Estatus",
                                  readonly=True,
                                  default='por_notificar',
                                  required=True, copy=False)
    resend = fields.Boolean(string="Autorizar reenvio?", default=False, copy=False)
    previous_cune = fields.Char(string="Previous CUNE", copy=False)
    current_cune = fields.Char(string="CUNE", readonly=1, copy=False)
    type_note = fields.Selection([
        ('1', 'Reemplazar'),
        ('2', 'Eliminar')
    ], string="Tipo de Nota", copy=False)
    contract_id = fields.Many2one(
        "hr.contract",
        required=True,
        string="Contract",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    payment_date = fields.Date(string="Fecha de Pago", default=fields.Date.today())
    xml_sended = fields.Char(string="XML ENVIADO", copy=False)


    def _generate_signature(self, data_xml_document, template_signature_data_xml, dian_constants,
                            data_constants_document):
        data_xml_keyinfo_base = ''
        data_xml_politics = ''
        data_xml_SignedProperties_base = ''
        data_xml_SigningTime = ''
        data_xml_SignatureValue = ''
        # Generar clave de referencia 0 para la firma del documento (referencia ref0)
        # Actualizar datos de signature
        #    Generar certificado publico para la firma del documento en el elemento keyinfo
        data_public_certificate_base = dian_constants['Certificate']
        #    Generar clave de politica de firma para la firma del documento (SigPolicyHash)
        data_xml_politics = self._generate_signature_politics(dian_constants['document_repository'])
        #    Obtener la hora de Colombia desde la hora del pc
        data_xml_SigningTime = self._generate_signature_signingtime()
        #    Generar clave de referencia 0 para la firma del documento (referencia ref0)
        #    1ra. Actualización de firma ref0 (leer todo el xml sin firma)
        data_xml_signature_ref_zero = self._generate_signature_ref0(data_xml_document,
                                                                    dian_constants['document_repository'],
                                                                    dian_constants['CertificateKey'])
        data_xml_signature = self._update_signature(template_signature_data_xml,
                                                    data_xml_signature_ref_zero, data_public_certificate_base,
                                                    data_xml_keyinfo_base, data_xml_politics,
                                                    data_xml_SignedProperties_base, data_xml_SigningTime,
                                                    dian_constants, data_xml_SignatureValue, data_constants_document)
        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_signature = etree.tostring(etree.XML(data_xml_signature, parser=parser))
        data_xml_signature = data_xml_signature.decode()
        #    Actualiza Keyinfo
        KeyInfo = etree.fromstring(data_xml_signature)
        KeyInfo = etree.tostring(KeyInfo[2])
        KeyInfo = KeyInfo.decode()
        if data_constants_document.get('InvoiceTypeCode', False) == '102':  # Factura
            xmlns = 'xmlns="dian:gov:co:facturaelectronica:NominaIndividual" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            KeyInfo = KeyInfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns)

        if data_constants_document.get('InvoiceTypeCode', False) == '103':  # Factura
            xmlns = 'xmlns="dian:gov:co:facturaelectronica:NominaIndividualDeAjuste" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            KeyInfo = KeyInfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns)

        data_xml_keyinfo_base = self._generate_signature_ref1(KeyInfo, dian_constants['document_repository'],
                                                              dian_constants['CertificateKey'])
        data_xml_signature = data_xml_signature.replace("<ds:DigestValue/>",
                                                        "<ds:DigestValue>%s</ds:DigestValue>" % data_xml_keyinfo_base,
                                                        1)
        #    Actualiza SignedProperties
        SignedProperties = etree.fromstring(data_xml_signature)
        SignedProperties = etree.tostring(SignedProperties[3])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = SignedProperties.decode()
        if data_constants_document['InvoiceTypeCode'] in ('102'):
            xmlns = 'xmlns="dian:gov:co:facturaelectronica:NominaIndividual" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            SignedProperties = SignedProperties.replace(
                'xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"',
                '%s' % xmlns)

        if data_constants_document.get('InvoiceTypeCode', False) == '103':  # Factura
            xmlns = 'xmlns="dian:gov:co:facturaelectronica:NominaIndividualDeAjuste" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            SignedProperties = SignedProperties.replace(
                'xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"',
                '%s' % xmlns)


        data_xml_SignedProperties_base = self._generate_signature_ref2(SignedProperties)
        data_xml_signature = data_xml_signature.replace("<ds:DigestValue/>",
                                                        "<ds:DigestValue>%s</ds:DigestValue>" % data_xml_SignedProperties_base,
                                                        1)
        #    Actualiza Signeinfo
        Signedinfo = etree.fromstring(data_xml_signature)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        if data_constants_document['InvoiceTypeCode'] in ('102'):
            xmlns = 'xmlns="dian:gov:co:facturaelectronica:NominaIndividual" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            Signedinfo = Signedinfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns)

        if data_constants_document.get('InvoiceTypeCode', False) == '103':  # Factura
            xmlns = 'xmlns="dian:gov:co:facturaelectronica:NominaIndividualDeAjuste" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            Signedinfo = Signedinfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns)

        data_xml_SignatureValue = self._generate_SignatureValue(dian_constants['document_repository'],
                                                                dian_constants['CertificateKey'], Signedinfo,
                                                                dian_constants['archivo_pem'],
                                                                dian_constants['archivo_certificado'])
        SignatureValue = etree.fromstring(data_xml_signature)
        SignatureValue = etree.tostring(SignatureValue[1])
        SignatureValue = SignatureValue.decode()
        data_xml_signature = data_xml_signature.replace('-sigvalue"/>',
                                                        '-sigvalue">%s</ds:SignatureValue>' % data_xml_SignatureValue,
                                                        1)
        return data_xml_signature

    def request_validating_dian(self):
        dian_constants = self._get_dian_constants()
        trackId = self.ZipKey
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self._generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        template_GetStatus_xml = self._template_GetStatus_xml()
        data_xml_send = self._generate_GetStatus_send_xml(template_GetStatus_xml, identifier, Created, Expires,
                                                          dian_constants['Certificate'], identifierSecurityToken,
                                                          identifierTo, trackId)

        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_send = etree.tostring(etree.XML(data_xml_send, parser=parser))
        data_xml_send = data_xml_send.decode()
        #   Generar DigestValue Elemento to y lo reemplaza en el xml
        ElementTO = etree.fromstring(data_xml_send)
        ElementTO = etree.tostring(ElementTO[0])
        ElementTO = etree.fromstring(ElementTO)
        ElementTO = etree.tostring(ElementTO[2])
        DigestValueTO = self._generate_digestvalue_to(ElementTO)
        data_xml_send = data_xml_send.replace('<ds:DigestValue/>',
                                              '<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
        #   Generar firma para el header de envío con el Signedinfo
        Signedinfo = etree.fromstring(data_xml_send)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[2])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        Signedinfo = Signedinfo.replace(
            '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">',
            '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia" xmlns:wsa="http://www.w3.org/2005/08/addressing">')
        SignatureValue = self._generate_SignatureValue_GetStatus(dian_constants['document_repository'],
                                                                 dian_constants['CertificateKey'], Signedinfo,
                                                                 dian_constants['archivo_pem'],
                                                                 dian_constants['archivo_certificado'])
        data_xml_send = data_xml_send.replace('<ds:SignatureValue/>',
                                              '<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
        #   Contruye XML de envío de petición
        headers = {'content-type': 'application/soap+xml'}
        URL_WEBService_DIAN = server_url['PRODUCCION'] if self.company_id.production_payroll else server_url['TEST']
        try:
            response = requests.post(URL_WEBService_DIAN, data=data_xml_send, headers=headers)
        except:
            raise ValidationError(
                'No existe comunicación con la DIAN para el servicio de recepción de Facturas Electrónicas. Por favor, revise su red o el acceso a internet.')
        #   Respuesta de petición
        if response.status_code != 200:  # Respuesta de envío no exitosa
            if response.status_code == 500:
                raise ValidationError('Error 500 = Error de servidor interno.')
            elif response.status_code == 503:
                raise ValidationError('Error 503 = Servicio no disponible.')
            elif response.status_code == 507:
                raise ValidationError('Error 507 = Espacio insuficiente.')
            elif response.status_code == 508:
                raise ValidationError('Error 508 = Ciclo detectado.')
            else:
                raise ValidationError('Se ha producido un error de comunicación con la DIAN.')
        response_dict = xmltodict.parse(response.content)
        if response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse'][
            'b:StatusCode'] == '00':
            self.response_message_dian += '- Respuesta consulta estado del documento: Procesado correctamente \n'
            self.write({'state_dian': 'exitoso', 'resend': False})
            self.send_email_from_template(str(self.xml_sended))
        else:
            if response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse'][
                'b:StatusCode'] == '90':
                self.response_message_dian += '- Respuesta consulta estado del documento: TrackId no encontrado'
                self.write({'state_dian': 'por_validar', 'resend': False})
            elif response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse'][
                'b:StatusCode'] == '99':
                self.response_message_dian += '- Respuesta consulta estado del documento: Validaciones contiene errores en campos mandatorios'
                self.write({'state_dian': 'rechazado', 'resend': True})
            elif response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse'][
                'b:StatusCode'] == '66':
                self.response_message_dian += '- Respuesta consulta estado del documento: NSU no encontrado'
                self.write({'state_dian': 'por_validar', 'resend': False})
            self.xml_response_dian = response.content
            self.xml_send_query_dian = data_xml_send
        return True

    def test_xml(self):
        dian_constants = self._get_dian_constants()
        data_constants_document = self._generate_data_constants_document(dian_constants)
        template_basic_data_nomina_individual_xml = self._template_nomina_individual(dian_constants)
        if self.credit_note:
            template_basic_data_nomina_individual_xml = self._template_nomina_individual_ajuste(dian_constants)

        raise UserError(template_basic_data_nomina_individual_xml)

    def send_pending_dian(self):
        dic_result_verify_status = self.exist_dian(self.ZipKey)
        if dic_result_verify_status['result_verify_status'] == False:

            dian_constants = self._get_dian_constants()
            data_constants_document = self._generate_data_constants_document(dian_constants)
            template_basic_data_nomina_individual_xml = self._template_nomina_individual(dian_constants)
            if self.credit_note:
                template_basic_data_nomina_individual_xml = self._template_nomina_individual_ajuste(dian_constants)

            parser = etree.XMLParser(remove_blank_text=True)
            template_basic_data_nomina_individual_xml = '<?xml version="1.0"?>' + template_basic_data_nomina_individual_xml
            template_basic_data_nomina_individual_xml = etree.tostring(
                etree.XML(template_basic_data_nomina_individual_xml, parser=parser))
            template_basic_data_nomina_individual_xml = template_basic_data_nomina_individual_xml.decode()
            data_xml_document = template_basic_data_nomina_individual_xml

            data_xml_document = data_xml_document.replace("<ext:ExtensionContent/>",
                                                          "<ext:ExtensionContent></ext:ExtensionContent>")

            template_signature_data_xml = self._template_signature_data_xml()
            data_xml_signature = self._generate_signature(data_xml_document, template_signature_data_xml,
                                                          dian_constants, data_constants_document)
            data_xml_signature = etree.tostring(etree.XML(data_xml_signature, parser=parser))
            data_xml_signature = data_xml_signature.decode()

            data_xml_document = data_xml_document.replace("<ext:ExtensionContent></ext:ExtensionContent>",
                                                          "<ext:ExtensionContent>%s</ext:ExtensionContent>" % data_xml_signature)
            data_xml_document = '<?xml version="1.0" encoding="UTF-8"?>' + data_xml_document

            Document = self._generate_zip_content(data_constants_document['FileNameXML'],
                                                  data_constants_document['FileNameZIP'], data_xml_document,
                                                  dian_constants['document_repository'])
            fileName = data_constants_document['FileNameZIP'][:-4]
            # Fecha y hora de la petición y expiración del envío del documento
            timestamp = self._generate_datetime_timestamp()
            Created = timestamp['Created']
            Expires = timestamp['Expires']
            # Id de pruebas
            testSetId = self.company_id.identificador_set_pruebas_payroll
            identifierSecurityToken = uuid.uuid4()
            identifierTo = uuid.uuid4()

            if self.company_id.production_payroll:
                template_SendBillSyncsend_xml = self._template_SendBillSyncsend_xml()
                data_xml_send = self._generate_SendBillSync_send_xml(template_SendBillSyncsend_xml, fileName,
                                                                     Document, Created, testSetId,
                                                                     data_constants_document['identifier'], Expires,
                                                                     dian_constants['Certificate'],
                                                                     identifierSecurityToken,
                                                                     identifierTo)
            else:
                template_SendTestSetAsyncsend_xml = self._template_SendBillSyncTestsend_xml()
                data_xml_send = self._generate_SendTestSetAsync_send_xml(template_SendTestSetAsyncsend_xml, fileName,
                                                                         Document, Created, testSetId,
                                                                         data_constants_document['identifier'], Expires,
                                                                         dian_constants['Certificate'],
                                                                         identifierSecurityToken, identifierTo)

            parser = etree.XMLParser(remove_blank_text=True)
            data_xml_send = etree.tostring(etree.XML(data_xml_send, parser=parser))
            data_xml_send = data_xml_send.decode()
            #   Generar DigestValue Elemento to y lo reemplaza en el xml
            ElementTO = etree.fromstring(data_xml_send)
            ElementTO = etree.tostring(ElementTO[0])
            ElementTO = etree.fromstring(ElementTO)
            ElementTO = etree.tostring(ElementTO[2])
            DigestValueTO = self._generate_digestvalue_to(ElementTO)
            data_xml_send = data_xml_send.replace('<ds:DigestValue/>',
                                                  '<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
            #   Generar firma para el header de envío con el Signedinfo
            Signedinfo = etree.fromstring(data_xml_send)
            Signedinfo = etree.tostring(Signedinfo[0])
            Signedinfo = etree.fromstring(Signedinfo)
            Signedinfo = etree.tostring(Signedinfo[0])
            Signedinfo = etree.fromstring(Signedinfo)
            Signedinfo = etree.tostring(Signedinfo[2])
            Signedinfo = etree.fromstring(Signedinfo)
            Signedinfo = etree.tostring(Signedinfo[0])
            Signedinfo = Signedinfo.decode()
            Signedinfo = Signedinfo.replace(
                '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">',
                '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia" xmlns:wsa="http://www.w3.org/2005/08/addressing">')
            SignatureValue = self._generate_SignatureValue_GetStatus(dian_constants['document_repository'],
                                                                     dian_constants['CertificateKey'], Signedinfo,
                                                                     dian_constants['archivo_pem'],
                                                                     dian_constants['archivo_certificado'])
            data_xml_send = data_xml_send.replace('<ds:SignatureValue/>',
                                                  '<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)

            URL_WEBService_DIAN = server_url['PRODUCCION'] if self.company_id.production_payroll else server_url['TEST']

            try:
                headers = {'content-type': 'application/soap+xml'}
                response = requests.post(URL_WEBService_DIAN, data=data_xml_send, headers=headers)

            except Exception as e:
                raise ValidationError(
                    'No existe comunicación con la DIAN para el servicio de recepción de Facturas Electrónicas. Por favor, revise su red o el acceso a internet.')

            if response.status_code != 200:  # Respuesta de envío no exitosa
                pass
                # TODO: Revisar
            else:
                # Procesa respuesta DIAN
                response_dict = xmltodict.parse(response.content)
                dict_mensaje = {}
                if self.company_id.production_payroll:
                    pass
                else:  # Ambiente de pruebas
                    dict_mensaje = \
                        response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult'][
                            'b:ErrorMessageList']
                    if '@i:nil' in dict_mensaje:
                        if response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult'][
                            'b:ErrorMessageList']['@i:nil'] == 'true':
                            self.response_message_dian = '- Respuesta envío: Documento enviado con éxito. Falta validar su estado \n'
                            self.ZipKey = \
                                response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse'][
                                    'SendTestSetAsyncResult'][
                                    'b:ZipKey']
                            self.state_dian = 'por_validar'
                            self.xml_sended = data_xml_document
                        else:
                            self.response_message_dian = '- Respuesta envío: Documento enviado con éxito, pero la DIAN detectó errores \n'
                            self.ZipKey = \
                                response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse'][
                                    'SendTestSetAsyncResult'][
                                    'b:ZipKey']
                            self.state_dian = 'por_notificar'
                    elif 'i:nil' in dict_mensaje:
                        if response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult'][
                            'b:ErrorMessageList']['i:nil'] == 'true':
                            self.response_message_dian = '- Respuesta envío: Documento enviado con éxito. Falta validar su estado \n'
                            self.ZipKey = \
                                response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse'][
                                    'SendTestSetAsyncResult'][
                                    'b:ZipKey']
                            self.state_dian = 'por_validar'
                        else:
                            self.response_message_dian = '- Respuesta envío: Documento enviado con éxito, pero la DIAN detectó errores \n'
                            self.ZipKey = \
                                response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse'][
                                    'SendTestSetAsyncResult'][
                                    'b:ZipKey']
                            self.state_dian = 'por_notificar'
                    else:
                        raise ValidationError('Mensaje de respuesta cambió en su estructura xml')

    def validate(self):
        if self.state_dian in ('rechazado', 'por_notificar'):
            self.send_pending_dian()

        if not self.company_id.production_payroll:
            if self.state_dian == 'por_validar':
                self.request_validating_dian()

    def _generate_SignatureValue_GetStatus(self, document_repository, password, data_xml_SignedInfo_generate,
                                           archivo_pem, archivo_certificado):
        data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(data_xml_SignedInfo_generate), method="c14n")
        # data_xml_SignatureValue_c14n = data_xml_SignatureValue_c14n.decode()
        archivo_key = document_repository + '/' + archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        try:
            signature = crypto.sign(key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha256')
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        SignatureValue = base64.b64encode(signature).decode()
        archivo_pem = document_repository + '/' + archivo_pem
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(pem, signature, data_xml_SignatureValue_c14n, 'sha256')
        except:
            raise ValidationError("Firma para el GestStatus no fué validada exitosamente")
        return SignatureValue

    def zip(self, src, dst):
        import os
        zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
        abs_src = os.path.abspath(src)
        for dirname, subdirs, files in os.walk(src):
            for filename in files:
                absname = os.path.abspath(os.path.join(dirname, filename))
                arcname = absname[len(abs_src) + 1:]
                zf.write(absname, arcname)
        zf.close()

    def _generate_zip_content(self, FileNameXML, FileNameZIP, data_xml_document, document_repository):
        # Almacena archvio XML
        xml_file = document_repository + '/' + FileNameXML
        f = open(xml_file, 'w')
        f.write(str(data_xml_document))
        f.close()
        # Comprime archvio XML
        zip_file = document_repository + '/' + FileNameZIP
        zf = zipfile.ZipFile(zip_file, mode="w")
        try:
            zf.write(xml_file, FileNameXML, compress_type=compression)
        finally:
            zf.close()
        # Obtiene datos comprimidos
        data_xml = zip_file
        data_xml = open(data_xml, 'rb')
        data_xml = data_xml.read()
        contenido_data_xml_b64 = base64.b64encode(data_xml)
        contenido_data_xml_b64 = contenido_data_xml_b64.decode()
        return contenido_data_xml_b64

    def _generate_xml_filename(self):
        # TODO: Generar valor correcto
        # pagina 96 nie para : Documento Soporte de Pago de Nómina Electrónica hay otro para el ajuste
        sequece = self.env['ir.sequence'].next_by_code('hr.payslip.sequence_documents_xml') or '00000001'
        dian_code_int = int(sequece)
        dian_code_hex = self.IntToHex(dian_code_int)
        dian_code_hex.zfill(10)
        if self._get_tipo_xml() == '102':
            name = 'nie{0}{1}{2}.xml'.format(self._get_emisor().vat, self.date_to.strftime('%y'),
                                             dian_code_hex.zfill(10))
        else:
            name = 'niae{0}{1}{2}.xml'.format(self._get_emisor().vat, self.date_to.strftime('%y'),
                                              dian_code_hex.zfill(10))
        file_name_xml = name
        return file_name_xml

    def IntToHex(self, dian_code_int):
        dian_code_hex = '%02x' % dian_code_int
        return dian_code_hex

    def add_attachment(self, xml_element, name):
        buf = io.StringIO()
        buf.write(xml_element)
        document = base64.encodestring(buf.getvalue().encode())
        buf.close()
        ctx = self.env.context.copy()
        ctx.pop('default_type', False)
        values = {
            'name': '{0}.xml'.format(name),
            'store_fname': '{0}.xml'.format(name),
            'datas': document,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary'
        }
        attach = self.env['ir.attachment'].with_context(ctx).create(values)
        self.env.cr.commit()
        return attach

    def hook_mail_template(self):
        return ""

    def send_email_from_template(self, xml_element):
        # We warn ~ once by hour ~ instead of every 10 min if the interval unit is more than 'hours'.
        mail = self.hook_mail_template()
        for payslip in self:
            tmpl = self.env.ref(mail, False)
            ctx = payslip.env.context.copy()
            attachments = payslip.add_attachment(xml_element, self.name)
            email_values = {'attachment_ids': [(4, int(attachments.id)), ]}
            tmpl.with_context(ctx).send_mail(  # noqa
                payslip.id, force_send=True,
                email_values=email_values
            )
        return {
            'name': 'Correo',
            'type': 'ir.actions.act_window',
            'res_model': 'message.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_message': "Correo Enviado exitosamente"
            }
        }

    def _generate_zip_filename(self):
        # TODO: Generar valor correcto
        sequece = self.env['ir.sequence'].next_by_code('hr.payslip.sequence_documents_zip') or '00000001'
        dian_code_int = int(sequece)
        dian_code_hex = self.IntToHex(dian_code_int)
        name = 'z{0}{1}{2}.zip'.format(self._get_emisor().vat, self.date_to.strftime('%y'),
                                       dian_code_hex.zfill(10))
        file_name_zip = name
        return file_name_zip

    def _generate_software_security_code(self, software_identification_code, software_pin, NroDocumento):
        software_security_code = hashlib.sha384((software_identification_code + software_pin + NroDocumento).encode())
        software_security_code = software_security_code.hexdigest()
        return software_security_code

    def _generate_CertDigestDigestValue(self, digital_certificate, password, document_repository, archivo_certificado):
        archivo_key = document_repository + '/' + archivo_certificado
        key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        certificate = hashlib.sha256(crypto.dump_certificate(crypto.FILETYPE_ASN1, key.get_certificate()))
        CertDigestDigestValue = base64.b64encode(certificate.digest())
        CertDigestDigestValue = CertDigestDigestValue.decode()
        return CertDigestDigestValue

    def _generate_digestvalue_to(self, elementTo):
        # Generar el digestvalue de to
        elementTo = etree.tostring(etree.fromstring(elementTo), method="c14n")
        elementTo_sha256 = hashlib.new('sha256', elementTo)
        elementTo_digest = elementTo_sha256.digest()
        elementTo_base = base64.b64encode(elementTo_digest)
        elementTo_base = elementTo_base.decode()
        return elementTo_base

    def _get_sequence(self):
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', 'salary.slip')])
        return sequence

    def _get_number(self):
        if not self.number:
            raise UserError(_("Se debe de configurar la referencia"))
        return self.number

    def _get_consecutivo(self):
        sequence = self._get_sequence()
        return self.number.replace(sequence.prefix, '') if self.number else ''

    def _get_generation_date(self):
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc
        issue_date = now_bogota.strftime("%Y-%m-%d")
        return issue_date

    def _get_time_colombia(self):
        fmt = "%H:%M:%S-05:00"
        now_utc = datetime.now(timezone('UTC'))
        now_time = now_utc.strftime(fmt)
        return now_time

    def _get_emisor(self):
        if not self.company_id.partner_id.vat:
            raise UserError('El NIT del emisor del documento es requerido')
        if not self.company_id.partner_id.dv:
            raise UserError(_("Falta configurar el DV en el empleado - RES.PARTNER.DV"))
        return self.company_id.partner_id

    def _get_employee_object(self):
        if not self.employee_id:
            raise UserError('Por favor defina el empleado')
        if not self.employee_id.type_worker:
            raise UserError("Por Favor defina el tipo de trabajador del empleado")
        if not self.employee_id.sub_type_worker:
            raise UserError("Por favor defina el sub tipo de trabajador del empleado")
        if not self.employee_id.bank_account_id.acc_type:
            raise UserError("Por favor defina el tipo de la cuenta bancaria del empleado")
        if not self.employee_id.bank_account_id.acc_number:
            raise UserError("Por favor defina el numero de la cuenta bancaria del empleado")
        if not self.employee_id.contract_id.type_contract.code:
            raise UserError("Por favor defina el tipo de contrato")
        return self.employee_id

    def _get_employee(self):
        if not self.employee_id.address_id:
            raise UserError('Por favor defina el tercero del empleado')
        if not self.employee_id.address_id.vat:
            raise UserError('El numero de identificacion del empleado es requerido')
        if not self.employee_id.address_id.state_id:
            raise UserError(_("Se debe registrar la provincia o estado del empleado"))
        if not self.employee_id.address_id.city:
            raise UserError(_("Se debe registrar la ciudad del empleado"))
        if not self.employee_id.address_id.country_id.code:
            raise UserError(_("Se debe registrar el codigo del pais del empleado"))
        if not self.employee_id.address_id.street:
            raise UserError(_("Se debe registrar la dirreccion del empleado"))

        return self.employee_id.address_id

    def _get_contract(self):
        if not self.contract_id:
            raise UserError('Por favor define al contrato del empleado')
        if not self.contract_id.way_pay_id:
            raise UserError('Por favor definir la forma de pago')
        if not self.contract_id.payment_method_id:
            raise UserError('Por favor definir el metodo de pago')
        return self.contract_id

    def _get_total_devengados(self):
        if not first(self.line_ids.filtered(lambda x: x.salary_rule_id.code == 'DevengadosTotal')):
            raise UserError(_("Se debe de tener configurado el devengado total en la nomina"))
        return "{:.2f}".format(
            abs(first(self.line_ids.filtered(lambda x: x.salary_rule_id.code == 'DevengadosTotal')).total))

    def _get_total_deducciones(self):
        if not first(self.line_ids.filtered(lambda x: x.salary_rule_id.code == 'DeduccionesTotal')):
            raise UserError(_("Se debe de tener configurado el deducible total en la nomina"))
        return "{:.2f}".format(
            abs(first(self.line_ids.filtered(lambda x: x.salary_rule_id.code == 'DeduccionesTotal')).total))

    def _get_total_pagado(self):
        if not first(self.line_ids.filtered(lambda x: x.salary_rule_id.code == 'ComprobanteTotal')):
            raise UserError(_("Se debe de tener configurado el comprobante total en la nomina"))
        return "{:.2f}".format(
            abs(first(self.line_ids.filtered(lambda x: x.salary_rule_id.code == 'ComprobanteTotal')).total))

    def _get_tipo_xml(self):
        return "103" if self.credit_note else "102"

    def _get_tipo_ambiente(self):
        return "1" if self.company_id.production_payroll else "2"

    def _get_cune(self, dian_constants):
        print("nuevo")
        res = f"""{self._get_number() + dian_constants.get('FechaGen') + dian_constants.get('HoraGen') + self._get_total_devengados() +
                   self._get_total_deducciones() + self._get_total_pagado() + self._get_emisor().vat + self._get_employee().vat +
                   self._get_tipo_xml() + self.company_id.software_pin_payroll + self._get_tipo_ambiente()}"""
        cune = hashlib.sha384((res).encode())
        cune = cune.hexdigest()
        return cune

    def _get_dian_constants(self):
        company = self.env.company
        sequence = self._get_sequence()
        consecutivo = self._get_consecutivo()
        number = self._get_number()

        dian_constants = {}
        dian_constants['document_repository'] = company.document_repository_payroll
        dian_constants['Username'] = company.software_identification_code_payroll
        dian_constants['Password'] = hashlib.new('sha256', company.password_environment_payroll.encode()).hexdigest()
        dian_constants['SoftwareID'] = company.software_identification_code_payroll
        dian_constants['SoftwareSecurityCode'] = self._generate_software_security_code(
            company.software_identification_code_payroll, company.software_pin_payroll, number)
        dian_constants['Number'] = number
        dian_constants['Prefix'] = sequence.prefix
        dian_constants['Consecutivo'] = consecutivo
        dian_constants['PINSoftware'] = company.software_pin_payroll
        dian_constants['SeedCode'] = company.seed_code_payroll

        dian_constants['ProfileExecutionID'] = tipo_ambiente['PRODUCCION'] if company.production_payroll else \
            tipo_ambiente['PRUEBA']
        dian_constants['CertificateKey'] = company.certificate_key_payroll
        dian_constants['archivo_pem'] = company.pem_payroll
        dian_constants['archivo_certificado'] = company.certificate_payroll
        dian_constants['CertDigestDigestValue'] = self._generate_CertDigestDigestValue(
            company.digital_certificate_payroll, dian_constants['CertificateKey'],
            dian_constants['document_repository'], dian_constants['archivo_certificado'])
        dian_constants['IssuerName'] = self._get_emisor().name
        dian_constants['SerialNumber'] = company.serial_number_payroll
        dian_constants['Certificate'] = company.digital_certificate_payroll
        dian_constants['CertificateKey'] = company.certificate_key_payroll

        dian_constants['HoraGen'] = self._get_time_colombia()
        dian_constants['FechaGen'] = self._get_generation_date()

        return dian_constants

    def _generate_data_constants_document(self, dian_constants):
        data_constants_document = {}

        identifier = uuid.uuid4()
        data_constants_document['identifier'] = identifier
        identifierkeyinfo = uuid.uuid4()
        data_constants_document['identifierkeyinfo'] = identifierkeyinfo
        data_constants_document['InvoiceTypeCode'] = self._get_tipo_xml()
        data_constants_document['FileNameXML'] = self._generate_xml_filename()
        data_constants_document['FileNameZIP'] = self._generate_zip_filename()

        return data_constants_document

    def _generate_data_constant_document(self):
        data_constants_document = {}
        identifier = uuid.uuid4()
        data_constants_document['identifier'] = 'xmldsig' + identifier + 'ref0'

    def _generate_datetime_timestamp(self):
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        # now_utc = datetime.now(timezone('UTC'))
        now_bogota = datetime.now(timezone('UTC'))
        # now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        Created = now_bogota.strftime(fmt)[:-3] + 'Z'
        now_bogota = now_bogota + timedelta(minutes=5)
        Expires = now_bogota.strftime(fmt)[:-3] + 'Z'
        timestamp = {'Created': Created,
                     'Expires': Expires
                     }
        return timestamp

    def _generate_signature_ref0(self, data_xml_document, document_repository, password):
        # 1er paso. Generar la referencia 0 que consiste en obtener keyvalue desde todo el xml del
        #           documento electronico aplicando el algoritmo SHA256 y convirtiendolo a base64
        template_basic_data_fe_xml = data_xml_document
        template_basic_data_fe_xml = etree.tostring(etree.fromstring(template_basic_data_fe_xml), method="c14n",
                                                    exclusive=False, with_comments=False, inclusive_ns_prefixes=None)
        data_xml_sha256 = hashlib.new('sha256', template_basic_data_fe_xml)
        data_xml_digest = data_xml_sha256.digest()
        data_xml_signature_ref_zero = base64.b64encode(data_xml_digest)
        data_xml_signature_ref_zero = data_xml_signature_ref_zero.decode()
        return data_xml_signature_ref_zero

    def _generate_signature_ref1(self, data_xml_keyinfo_generate, document_repository, password):
        # Generar la referencia 1 que consiste en obtener keyvalue desde el keyinfo contenido
        # en el documento electrónico aplicando el algoritmo SHA256 y convirtiendolo a base64
        data_xml_keyinfo_generate = etree.tostring(etree.fromstring(data_xml_keyinfo_generate), method="c14n")
        data_xml_keyinfo_sha256 = hashlib.new('sha256', data_xml_keyinfo_generate)
        data_xml_keyinfo_digest = data_xml_keyinfo_sha256.digest()
        data_xml_keyinfo_base = base64.b64encode(data_xml_keyinfo_digest)
        data_xml_keyinfo_base = data_xml_keyinfo_base.decode()
        return data_xml_keyinfo_base

    def _generate_signature_ref2(self, data_xml_SignedProperties_generate):
        # Generar la referencia 2, se obtine desde el elemento SignedProperties que se
        # encuentra en la firma aplicando el algoritmo SHA256 y convirtiendolo a base64.
        data_xml_SignedProperties_c14n = etree.tostring(etree.fromstring(data_xml_SignedProperties_generate),
                                                        method="c14n")
        data_xml_SignedProperties_sha256 = hashlib.new('sha256', data_xml_SignedProperties_c14n)
        data_xml_SignedProperties_digest = data_xml_SignedProperties_sha256.digest()
        data_xml_SignedProperties_base = base64.b64encode(data_xml_SignedProperties_digest)
        data_xml_SignedProperties_base = data_xml_SignedProperties_base.decode()
        return data_xml_SignedProperties_base

    def _generate_SignatureValue(self, document_repository, password, data_xml_SignedInfo_generate,
                                 archivo_pem, archivo_certificado):
        data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(data_xml_SignedInfo_generate), method="c14n",
                                                      exclusive=False, with_comments=False)
        archivo_key = document_repository + '/' + archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        try:
            signature = crypto.sign(key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha256')
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        SignatureValue = base64.b64encode(signature)
        SignatureValue = SignatureValue.decode()
        archivo_pem = document_repository + '/' + archivo_pem
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(pem, signature, data_xml_SignatureValue_c14n, 'sha256')
        except:
            raise ValidationError("Firma no fué validada exitosamente")
        # serial = key.get_certificate().get_serial_number()
        return SignatureValue

    def _update_signature(self, template_signature_data_xml, data_xml_signature_ref_zero, data_public_certificate_base,
                          data_xml_keyinfo_base, data_xml_politics,
                          data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants,
                          data_xml_SignatureValue, data_constants_document):
        data_xml_signature = template_signature_data_xml % {'data_xml_signature_ref_zero': data_xml_signature_ref_zero,
                                                            'data_public_certificate_base': data_public_certificate_base,
                                                            'data_xml_keyinfo_base': data_xml_keyinfo_base,
                                                            'data_xml_politics': data_xml_politics,
                                                            'data_xml_SignedProperties_base': data_xml_SignedProperties_base,
                                                            'data_xml_SigningTime': data_xml_SigningTime,
                                                            'CertDigestDigestValue': dian_constants[
                                                                'CertDigestDigestValue'],
                                                            'IssuerName': dian_constants['IssuerName'],
                                                            'SerialNumber': dian_constants['SerialNumber'],
                                                            'SignatureValue': data_xml_SignatureValue,
                                                            'identifier': data_constants_document['identifier'],
                                                            'identifierkeyinfo': data_constants_document[
                                                                'identifierkeyinfo'],
                                                            }
        return data_xml_signature

    # @api.multi
    def _generate_signature_politics(self, document_repository):
        data_xml_politics = 'dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y='
        return data_xml_politics

    def _generate_signature_signingtime(self):
        fmt = "%Y-%m-%dT%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc
        data_xml_SigningTime = now_bogota.strftime(fmt) + '-05:00'
        return data_xml_SigningTime

    def _generate_SendTestSetAsync_send_xml(self, template_send_data_xml, fileName, contentFile, Created,
                                            testSetId, identifier, Expires, Certificate, identifierSecurityToken,
                                            identifierTo):
        data_send_xml = template_send_data_xml % {
            'fileName': fileName,
            'contentFile': contentFile,
            'testSetId': testSetId,
            'identifier': identifier,
            'Created': Created,
            'Expires': Expires,
            'Certificate': Certificate,
            'identifierSecurityToken': identifierSecurityToken,
            'identifierTo': identifierTo,
        }
        return data_send_xml

    def _get_company_id(self):
        if not self.env.company.country_id.code:
            raise UserError("Se debe configurar el codigo del pais en la compañia")
        if not self.env.company.state_id.code:
            raise UserError("Se debe configurar el estado o provincia en la compañia")
        if not self.env.company.partner_id.xcity:
            raise UserError("Se debe configurar la ciudad de la compañia")
        if not self.env.company.partner_id.state_id.code_dian:
            raise UserError("Se debe configurar el codigo Dian de la provincia de la compañia")
        return self.env.company

    def _get_notes(self):
        if not self.note:
            return 'sin notas'
        return self.note

    def return_number_document_type(self, document_type):
        number_document_type = 13

        if document_type:
            if document_type == '31' or document_type == 'rut':
                number_document_type = 31
            if document_type == 'national_citizen_id':
                number_document_type = 13
            if document_type == 'civil_registration':
                number_document_type = 11
            if document_type == 'id_card':
                number_document_type = 12
            if document_type == '21':
                number_document_type = 21
            if document_type == 'foreign_id_card':
                number_document_type = 22
            if document_type == 'passport':
                number_document_type = 41
            if document_type == '43':
                number_document_type = 43
        else:
            raise UserError(_("Debe de ingresar el tipo de documento"))
        return str(number_document_type)

    def template_generate_devengados_deducciones(self):
        # https://stackoverflow.com/questions/18796280/how-do-i-set-attributes-for-an-xml-element-with-python
        devengados = ''
        deducciones = ''
        elements = {}
        line_obj = self.line_ids.filtered(
            lambda x: x.salary_rule_id.code not in ('DevengadosTotal', 'DeduccionesTotal', 'ComprobanteTotal')
        ).sorted("sequence")
        current_codes = line_obj.mapped('salary_rule_id.devengado_rule_id.code')
        current_codes.extend(line_obj.mapped('salary_rule_id.deduccion_rule_id.code'))
        # current_codes = list(set(current_codes))
        root_devengado = ET.Element("Devengados")
        root_deducion = ET.Element("Deducciones")
        for current_code in current_codes:
            line_ids = line_obj.filtered(
                lambda
                    x: x.salary_rule_id.devengado_rule_id.code == current_code or x.salary_rule_id.deduccion_rule_id.code == current_code)
            for record in line_ids:
                if not record.salary_rule_id.type_rule:
                    raise UserError(f'Por favor configure el tipo de regla: {record.salary_rule_id.name}')

                if not record.salary_rule_id.devengado_rule_id and not record.salary_rule_id.deduccion_rule_id:
                    raise UserError(f'Por favor configure el sub tipo de la regla: {record.salary_rule_id.name}')
                rule_id = record.salary_rule_id.devengado_rule_id or record.salary_rule_id.deduccion_rule_id
                if not rule_id.code:
                    raise UserError(f'El codigo de la regla es obligatorio {rule_id.name}')
                if not rule_id.sub_element:
                    code = rule_id.code
                    code_split = code.split('-')
                    root_str = ""
                    element_str = []
                    for element in range(len(code_split)):
                        if element == 0:
                            root_str = code_split[element]
                        else:
                            element_str.append(code_split[element])
                    root_for_bucle = root_devengado
                    if record.salary_rule_id.type_rule == 'deduccion':
                        root_for_bucle = root_deducion
                    exist_element = root_for_bucle.get(root_str, False)
                    root = exist_element or ET.Element(root_str)
                    if element_str:
                        for element in range(len(element_str)):
                            value = root.get(element_str[element], default=0) if root.get(element_str[element],
                                                                                          default=0) != None else 0
                            if element_str[element] == 'Porcentaje':
                                root.set(element_str[element], "{:.2f}".format(abs(value + record.rate)))
                            else:
                                root.set(element_str[element], "{:.2f}".format(abs(value + record.total)))
                    else:
                        value = root.text if root.text != None else 0
                        root.text = "{:.2f}".format(abs(value + record.total))
                    if root_str == 'Basico':
                        if not self.worked_days_line_ids.filtered(lambda x: x.code == 'WORK100'):
                            raise UserError(_("Se debe insertar los dias trabajados con codigo WORK100"))
                        days_id = first(self.worked_days_line_ids.filtered(lambda x: x.code == 'WORK100'))
                        element_str = 'DiasTrabajados'
                        root.set(element_str, str(int(days_id.number_of_days)))
                    root_for_bucle.append(root)
                else:
                    code = rule_id.code
                    code_split = code.split('-')
                    element_str = []
                    for element in range(len(code_split)):
                        if element == 0:
                            root_str = code_split[element]
                        elif element == 1:
                            sub_root_str = code_split[element]
                        else:
                            element_str.append(code_split[element])
                    root_for_bucle = root_deducion \
                        if record.salary_rule_id.type_rule == 'deduccion' else root_devengado
                    if root_for_bucle.find(root_str):
                        obj_root = root_for_bucle.find(root_str)
                        if obj_root.findall(sub_root_str):
                            sub_root = obj_root.find(sub_root_str)
                        else:
                            sub_root = ET.Element(sub_root_str)
                            obj_root.append(sub_root)
                        if element_str:
                            for element in range(len(element_str)):
                                value = sub_root.get(element_str[element], default=0)
                                if element_str[element] == 'Porcentaje':
                                    sub_root.set(element_str[element], "{:.2f}".format(abs(value + record.rate)))
                                else:
                                    sub_root.set(element_str[element], "{:.2f}".format(abs(value + record.total)))
                        else:
                            sub_root.text += "{:.2f}".format(abs(record.total))
                    else:
                        root = ET.Element(root_str)
                        sub_root = ET.Element(sub_root_str)
                        if element_str:
                            for element in range(len(element_str)):
                                sub_root.set(element_str[element], "{:.2f}".format(abs(record.total)))
                        else:
                            sub_root.text = "{:.2f}".format(abs(record.total))
                        root.append(sub_root)
                        root_for_bucle.append(root)
        root_devengado_str = ET.tostring(root_devengado).decode()
        root_deduccion_str = ET.tostring(root_deducion).decode()
        return root_devengado_str + root_deduccion_str

    def _template_nomina_individual(self, dian_constants):
        cune = self._get_cune(dian_constants)
        if not self.payment_date:
            raise UserError(_("Debe configurar la fecha de pago"))
        if not self.payroll_period:
            raise UserError(_("Debe configurar el periodo de la nomina"))
        if not self.worked_days_line_ids.filtered(lambda x: x.code == 'WORK100'):
            raise UserError(_("Debes ingresar el numero de dias trabajado con el codifo WORK100"))
        nomina_payroll = self.payroll_period.code
        number_days = first(self.worked_days_line_ids.filtered(lambda x: x.code == 'WORK100')).number_of_days
        self.current_cune = cune
        xml = f"""<NominaIndividual xmlns="dian:gov:co:facturaelectronica:NominaIndividual" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" SchemaLocation="" xsi:schemaLocation="dian:gov:co:facturaelectronica:NominaIndividual NominaIndividualElectronicaXSD.xsd">
                <ext:UBLExtensions>
                    <ext:UBLExtension>
                        <ext:ExtensionContent></ext:ExtensionContent>
                    </ext:UBLExtension>
                </ext:UBLExtensions>
          <Periodo FechaIngreso="{str(self._get_contract().date_start)}" FechaLiquidacionInicio="{str(self.date_from)}" FechaLiquidacionFin="{str(self.date_to)}" TiempoLaborado="{number_days}" FechaGen="{dian_constants.get('FechaGen')}" />
          <NumeroSecuenciaXML CodigoTrabajador="{self._get_employee().vat}" Prefijo="{dian_constants.get('Prefix')}" Consecutivo="{dian_constants.get('Consecutivo')}" Numero="{dian_constants.get('Number')}" />
          <LugarGeneracionXML Pais="{str(self._get_company_id().partner_id.country_id.code) or ''}" DepartamentoEstado="{str(self._get_company_id().partner_id.state_id.code_dian)}" MunicipioCiudad="{str(self._get_company_id().partner_id.xcity.code)}" Idioma="es" />
          <ProveedorXML NIT="{self._get_emisor().vat}" RazonSocial="{self._get_emisor().name}" DV="{self._get_emisor().dv}" SoftwareID="{dian_constants.get('SoftwareID')}" SoftwareSC="{dian_constants.get('SoftwareSecurityCode')}" />
          <CodigoQR>https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={cune}</CodigoQR>
          <InformacionGeneral Version="V1.0: Documento Soporte de Pago de Nómina Electrónica" Ambiente="{self._get_tipo_ambiente()}" TipoXML="{self._get_tipo_xml()}" CUNE="{cune}" EncripCUNE="CUNE-SHA384" FechaGen="{dian_constants.get('FechaGen')}" HoraGen="{dian_constants.get('HoraGen')}" PeriodoNomina="{nomina_payroll}" TipoMoneda="COP" TRM="0" />
          <Notas>{str(self._get_notes())}</Notas>
          <Empleador RazonSocial="{self._get_emisor().name}" NIT="{self._get_emisor().vat}" DV="{str(self._get_emisor().dv)}" Pais="{str(self._get_emisor().country_id.code)}" DepartamentoEstado="{str(self._get_emisor().state_id.code_dian)}" MunicipioCiudad="{str(self._get_company_id().partner_id.xcity.code)}" Direccion="{str(self._get_emisor().street)}" />
          <Trabajador TipoTrabajador="{self._get_employee_object().type_worker.code}" SubTipoTrabajador="{self._get_employee_object().sub_type_worker.code}" AltoRiesgoPension="false" TipoDocumento="{self._get_employee().l10n_latam_identification_type_id.l10n_co_document_code}" NumeroDocumento="{self._get_employee().vat}" PrimerApellido="{self._get_employee().x_lastname1}" SegundoApellido="{self._get_employee().x_lastname2}" PrimerNombre="{self._get_employee().x_name1}" OtrosNombres="{self._get_employee().x_name2}" LugarTrabajoPais="{self._get_employee().country_id.code}" LugarTrabajoDepartamentoEstado="{self._get_employee().state_id.code_dian}" LugarTrabajoMunicipioCiudad="{self._get_employee().xcity.code}" LugarTrabajoDireccion="{self._get_employee().street}" SalarioIntegral="false" TipoContrato="{self._get_employee_object().contract_id.type_contract.code}" Sueldo="{self._get_employee_object().contract_id.wage}" CodigoTrabajador="{self._get_employee().vat}" />
          <Pago Forma="{self._get_contract().way_pay_id.code}" Metodo="{self._get_contract().payment_method_id.code}" Banco="{self._get_employee_object().bank_account_id.bank_id.name}" TipoCuenta="{self._get_employee_object().bank_account_id.acc_type}" NumeroCuenta="{self._get_employee_object().bank_account_id.acc_number}" />
          <FechasPagos>
            <FechaPago>{self.payment_date}</FechaPago>
          </FechasPagos>
          {self.template_generate_devengados_deducciones()}
          <DevengadosTotal>{self._get_total_devengados()}</DevengadosTotal>
          <DeduccionesTotal>{self._get_total_deducciones()}</DeduccionesTotal>
          <ComprobanteTotal>{self._get_total_pagado()}</ComprobanteTotal>
        </NominaIndividual>"""
        return xml

    def get_values_for_previous_xml(self, xml_sended):
        xml = xmltodict.parse(xml_sended)
        return {
            'Prefix': xml['NominaIndividual']['NumeroSecuenciaXML']['@Prefijo'],
            'consecutivo': xml['NominaIndividual']['NumeroSecuenciaXML']['@Consecutivo'],
            'numero': xml['NominaIndividual']['NumeroSecuenciaXML']['@Numero'],
            'pais': xml['NominaIndividual']['LugarGeneracionXML']['@Pais'],
            'departamento': xml['NominaIndividual']['LugarGeneracionXML']['@DepartamentoEstado'],
            'idioma': xml['NominaIndividual']['LugarGeneracionXML']['@Idioma'],
            'municipio': xml['NominaIndividual']['LugarGeneracionXML']['@MunicipioCiudad'],
            'softwareid': xml['NominaIndividual']['ProveedorXML']['@SoftwareID'],
            'softwaresc': xml['NominaIndividual']['ProveedorXML']['@SoftwareSC'],
            'codeqr': xml['NominaIndividual']['CodigoQR'],
            'cune': xml['NominaIndividual']['InformacionGeneral']['@CUNE'],
            'fechagen': xml['NominaIndividual']['InformacionGeneral']['@FechaGen'],
            'horagen': xml['NominaIndividual']['InformacionGeneral']['@HoraGen'],
        }


    def get_code_nomina_individual_ajuste(self, code, cune, dian_constants, number_days, nomina_payroll, payslip_id):
        values = self.get_values_for_previous_xml(payslip_id.xml_sended)
        if code == 1:
            xml = f"""
            <Reemplazar>
                  <ReemplazandoPredecesor NumeroPred="{payslip_id.number}" CUNEPred="{payslip_id.current_cune}" FechaGenPred="{payslip_id.payment_date}"/>
                  <Periodo FechaIngreso="{str(self._get_contract().date_start)}" FechaLiquidacionInicio="{str(self.date_from)}" FechaLiquidacionFin="{str(self.date_to)}" TiempoLaborado="{number_days}" FechaGen="{dian_constants.get('FechaGen')}" />
                  <NumeroSecuenciaXML CodigoTrabajador="{self._get_employee().vat}" Prefijo="{dian_constants.get('Prefix')}" Consecutivo="{dian_constants.get('Consecutivo')}" Numero="{dian_constants.get('Number')}" />
                  <LugarGeneracionXML Pais="{str(self._get_company_id().partner_id.country_id.code) or ''}" DepartamentoEstado="{str(self._get_company_id().partner_id.state_id.code_dian)}" MunicipioCiudad="{str(self._get_company_id().partner_id.xcity.code)}" Idioma="es" />
                  <ProveedorXML NIT="{self._get_emisor().vat}" RazonSocial="{self._get_emisor().name}" DV="{self._get_emisor().dv}" SoftwareID="{dian_constants.get('SoftwareID')}" SoftwareSC="{dian_constants.get('SoftwareSecurityCode')}" />
                  <CodigoQR>https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={cune}</CodigoQR>
                  <InformacionGeneral Version="V1.0: Documento Soporte de Pago de Nómina Electrónica" Ambiente="{self._get_tipo_ambiente()}" TipoXML="{self._get_tipo_xml()}" CUNE="{cune}" EncripCUNE="CUNE-SHA384" FechaGen="{dian_constants.get('FechaGen')}" HoraGen="{dian_constants.get('HoraGen')}" PeriodoNomina="{nomina_payroll}" TipoMoneda="COP" TRM="0" />
                  <Notas>{str(self._get_notes())}</Notas>
                  <Empleador RazonSocial="{self._get_emisor().name}" NIT="{self._get_emisor().vat}" DV="{str(self._get_emisor().dv)}" Pais="{str(self._get_emisor().country_id.code)}" DepartamentoEstado="{str(self._get_emisor().state_id.code_dian)}" MunicipioCiudad="{str(self._get_company_id().partner_id.xcity.code)}" Direccion="{str(self._get_emisor().street)}" />
                  <Trabajador TipoTrabajador="{self._get_employee_object().type_worker.code}" SubTipoTrabajador="{self._get_employee_object().sub_type_worker.code}" AltoRiesgoPension="false" TipoDocumento="{self._get_employee().l10n_latam_identification_type_id.l10n_co_document_code}" NumeroDocumento="{self._get_employee().vat}" PrimerApellido="{self._get_employee().x_lastname1}" SegundoApellido="{self._get_employee().x_lastname2}" PrimerNombre="{self._get_employee().x_name1}" OtrosNombres="{self._get_employee().x_name2}" LugarTrabajoPais="{self._get_employee().country_id.code}" LugarTrabajoDepartamentoEstado="{self._get_employee().state_id.code_dian}" LugarTrabajoMunicipioCiudad="{self._get_employee().xcity.code}" LugarTrabajoDireccion="{self._get_employee().street}" SalarioIntegral="false" TipoContrato="{self._get_employee_object().contract_id.type_contract.code}" Sueldo="{self._get_employee_object().contract_id.wage}" CodigoTrabajador="{self._get_employee().vat}" />
                  <Pago Forma="{self._get_contract().way_pay_id.code}" Metodo="{self._get_contract().payment_method_id.code}" Banco="{self._get_employee_object().bank_account_id.bank_id.name}" TipoCuenta="{self._get_employee_object().bank_account_id.acc_type}" NumeroCuenta="{self._get_employee_object().bank_account_id.acc_number}" />
                  <FechasPagos>
                    <FechaPago>{self.payment_date}</FechaPago>
                  </FechasPagos>
                  {self.template_generate_devengados_deducciones()}
                  <DevengadosTotal>{self._get_total_devengados()}</DevengadosTotal>
                  <DeduccionesTotal>{self._get_total_deducciones()}</DeduccionesTotal>
                  <ComprobanteTotal>{self._get_total_pagado()}</ComprobanteTotal>
            </Reemplazar>
            """
        else:
            xml = f"""
            <Eliminar>
                <EliminandoPredecesor NumeroPred="{payslip_id.number}" CUNEPred="{payslip_id.current_cune}" FechaGenPred="{payslip_id.payment_date}"/>
                <NumeroSecuenciaXML Prefijo="{values.get('Prefix')}" Consecutivo="{values.get('consecutivo')}" Numero="{values.get('numero')}"/>
                <LugarGeneracionXML Pais="{values.get('pais')}" DepartamentoEstado="{values.get('departamento')}" MunicipioCiudad="{values.get('municipio')}" Idioma="{values.get('idioma')}"/>
                <ProveedorXML RazonSocial="{payslip_id._get_emisor().name} PrimerApellido="{payslip_id._get_emisor().x_lastname1}" SegundoApellido="{payslip_id._get_emisor().x_lastname2}" PrimerNombre="{payslip_id._get_emisor().x_name1}" OtrosNombres="{payslip_id._get_emisor().x_name2}" NIT="{payslip_id._get_emisor().vat}" DV="{payslip_id._get_emisor().dv}" SoftwareID="{values.get('softwareid')}" SoftwareSC="{values.get('softwaresc')}"/>
                <CodigoQR>{values.get('codeqr')}</CodigoQR>
                <InformacionGeneral Version="V1.0: Documento Soporte de Pago de Nómina Electrónica" Ambiente="{self._get_tipo_ambiente()}" TipoXML="{self._get_tipo_xml()}" CUNE="{values.get('cune')}" EncripCUNE="CUNE-SHA384" FechaGen="{values.get('fechagen')}" HoraGen="{values.get('horagen')}"/>
                <Notas>{payslip_id.note}</Notas>
                <Empleador RazonSocial="{payslip_id._get_emisor().name}" PrimerApellido="{payslip_id._get_emisor().x_lastname1}" SegundoApellido="{payslip_id._get_emisor().x_lastname2}" PrimerNombre="{payslip_id._get_emisor().x_name1}" OtrosNombres="{payslip_id._get_emisor().x_name2}" NIT="{payslip_id._get_emisor().vat}" DV="{payslip_id._get_emisor().dv}" Pais="{payslip_id._get_emisor().country_id.code}" DepartamentoEstado="{str(payslip_id._get_emisor().state_id.code_dian)}" MunicipioCiudad="{str(payslip_id._get_company_id().partner_id.xcity.code)}" Direccion="{str(payslip_id._get_emisor().street)}"/>
            </Eliminar>
            """
        return xml

    def _template_nomina_individual_ajuste(self, dian_constants):
        cune = self._get_cune(dian_constants)
        if not self.payment_date:
            raise UserError(_("Debe configurar la fecha de pago"))
        if not self.payroll_period:
            raise UserError(_("Debe configurar el periodo de la nomina"))
        if not self.worked_days_line_ids.filtered(lambda x: x.code == 'WORK100'):
            raise UserError(_("Debes ingresar el numer de dias trabajado con el codifo WORK100"))
        if not self.previous_cune:
            raise UserError(_("Debes ingresar el identificador Cune de la nomina a afectar"))
        nomina_payroll = self.payroll_period.code
        number_days = first(self.worked_days_line_ids.filtered(lambda x: x.code == 'WORK100')).number_of_days
        previous_payslip = self.env['hr.payslip'].search([('current_cune', '=', self.previous_cune)], limit=1)
        if not previous_payslip:
            raise UserError(_("No se encontró ninguna nomina asociada"))

        xml = f"""<NominaIndividualDeAjuste xmlns="dian:gov:co:facturaelectronica:NominaIndividualDeAjuste" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" SchemaLocation="" xsi:schemaLocation="dian:gov:co:facturaelectronica:NominaIndividualDeAjuste NominaIndividualDeAjusteElectronicaXSD.xsd">
                <ext:UBLExtensions>
                    <ext:UBLExtension>
                        <ext:ExtensionContent></ext:ExtensionContent>
                    </ext:UBLExtension>
                </ext:UBLExtensions>
          <TipoNota>{self.type_note}</TipoNota>  
          {self.get_code_nomina_individual_ajuste(int(self.type_note), cune, dian_constants, number_days, nomina_payroll
                                                  , previous_payslip)}
        </NominaIndividualDeAjuste>"""
        return xml

    def _template_signature_data_xml(self):
        return """
            <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-%(identifier)s">
                    <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference Id="xmldsig-%(identifier)s-ref0" URI="">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                        </ds:Transforms>
                        <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>                                             
                        <ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
                    </ds:Reference>
                    <ds:Reference URI="#xmldsig-%(identifierkeyinfo)s-keyinfo">
                        <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
                    </ds:Reference>
                    <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-%(identifier)s-signedprops">
                        <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue Id="xmldsig-%(identifier)s-sigvalue">%(SignatureValue)s</ds:SignatureValue>
                <ds:KeyInfo Id="xmldsig-%(identifierkeyinfo)s-keyinfo">
                    <ds:X509Data>
                        <ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
                    </ds:X509Data>
                </ds:KeyInfo>
                <ds:Object>
                    <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-%(identifier)s">
                        <xades:SignedProperties Id="xmldsig-%(identifier)s-signedprops">
                            <xades:SignedSignatureProperties>
                                <xades:SigningTime>%(data_xml_SigningTime)s</xades:SigningTime>
                                <xades:SigningCertificate>
                                    <xades:Cert>
                                        <xades:CertDigest>
                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                                            <ds:DigestValue>%(CertDigestDigestValue)s</ds:DigestValue>
                                        </xades:CertDigest>
                                        <xades:IssuerSerial>
                                            <ds:X509IssuerName>%(IssuerName)s</ds:X509IssuerName>
                                            <ds:X509SerialNumber>%(SerialNumber)s</ds:X509SerialNumber>
                                        </xades:IssuerSerial>
                                    </xades:Cert>
                                </xades:SigningCertificate>
                                <xades:SignaturePolicyIdentifier>
                                    <xades:SignaturePolicyId>
                                        <xades:SigPolicyId>
                                            <xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
                                            <xades:Description>Politica de firma para nominas electronicas de la Republica de Colombia</xades:Description>
                                        </xades:SigPolicyId>
                                        <xades:SigPolicyHash>
                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                                            <ds:DigestValue>%(data_xml_politics)s</ds:DigestValue>
                                        </xades:SigPolicyHash>
                                    </xades:SignaturePolicyId>
                                </xades:SignaturePolicyIdentifier>
                                <xades:SignerRole>
                                    <xades:ClaimedRoles>
                                        <xades:ClaimedRole>supplier</xades:ClaimedRole>
                                    </xades:ClaimedRoles>
                                </xades:SignerRole>
                            </xades:SignedSignatureProperties>
                        </xades:SignedProperties>
                    </xades:QualifyingProperties>
                </ds:Object>
            </ds:Signature>"""

    def _template_SendBillSyncTestsend_xml(self):
        template_SendBillSyncTestsend_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:SendTestSetAsync>
            <wcf:fileName>%(fileName)s</wcf:fileName>
            <wcf:contentFile>%(contentFile)s</wcf:contentFile>
            <wcf:testSetId>%(testSetId)s</wcf:testSetId>
        </wcf:SendTestSetAsync>
    </soap:Body>
</soap:Envelope>
"""
        return template_SendBillSyncTestsend_xml

    def _template_GetStatus_xml(self):
        template_GetStatus_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatusZip</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:GetStatusZip>
            <wcf:trackId>%(trackId)s</wcf:trackId>
        </wcf:GetStatusZip>
    </soap:Body>
</soap:Envelope>
"""
        return template_GetStatus_xml

    def _generate_GetStatus_send_xml(self, template_getstatus_send_data_xml, identifier, Created, Expires, Certificate,
                                     identifierSecurityToken, identifierTo, trackId):
        data_getstatus_send_xml = template_getstatus_send_data_xml % {
            'identifier': identifier,
            'Created': Created,
            'Expires': Expires,
            'Certificate': Certificate,
            'identifierSecurityToken': identifierSecurityToken,
            'identifierTo': identifierTo,
            'trackId': trackId,
        }
        return data_getstatus_send_xml

    def exist_dian(self, document_id):
        dic_result_verify_status = {}
        dian_constants = self._get_dian_constants()
        trackId = self.ZipKey
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self._generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']

        if self.company_id.production_payroll:
            template_GetStatus_xml = self._template_GetStatusExist_xml()
        else:
            template_GetStatus_xml = self._template_GetStatusExistTest_xml()

        data_xml_send = self._generate_GetStatus_send_xml(template_GetStatus_xml, identifier, Created, Expires,
                                                          dian_constants['Certificate'], identifierSecurityToken,
                                                          identifierTo, trackId)

        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_send = etree.tostring(etree.XML(data_xml_send, parser=parser))
        data_xml_send = data_xml_send.decode()
        #   Generar DigestValue Elemento to y lo reemplaza en el xml
        ElementTO = etree.fromstring(data_xml_send)
        ElementTO = etree.tostring(ElementTO[0])
        ElementTO = etree.fromstring(ElementTO)
        ElementTO = etree.tostring(ElementTO[2])
        DigestValueTO = self._generate_digestvalue_to(ElementTO)
        data_xml_send = data_xml_send.replace('<ds:DigestValue/>',
                                              '<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
        #   Generar firma para el header de envío con el Signedinfo
        Signedinfo = etree.fromstring(data_xml_send)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[2])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        Signedinfo = Signedinfo.replace(
            '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">',
            '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia" xmlns:wsa="http://www.w3.org/2005/08/addressing">')
        SignatureValue = self._generate_SignatureValue_GetStatus(dian_constants['document_repository'],
                                                                 dian_constants['CertificateKey'], Signedinfo,
                                                                 dian_constants['archivo_pem'],
                                                                 dian_constants['archivo_certificado'])
        data_xml_send = data_xml_send.replace('<ds:SignatureValue/>',
                                              '<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
        #   Contruye XML de envío de petición
        headers = {'content-type': 'application/soap+xml'}
        URL_WEBService_DIAN = server_url['PRODUCCION'] if self.company_id.production_payroll else server_url['TEST']
        try:
            response = requests.post(URL_WEBService_DIAN, data=data_xml_send, headers=headers)
        except:
            raise ValidationError(
                'No existe comunicación con la DIAN para el servicio de recepción de Facturas Electrónicas. Por favor, revise su red o el acceso a internet.')
        #   Respuesta de petición
        if response.status_code != 200:  # Respuesta de envío no exitosa
            if response.status_code == 500:
                raise ValidationError('Error 500 = Error de servidor interno.')
            elif response.status_code == 503:
                raise ValidationError('Error 503 = Servicio no disponible.')
            elif response.status_code == 507:
                raise ValidationError('Error 507 = Espacio insuficiente.')
            elif response.status_code == 508:
                raise ValidationError('Error 508 = Ciclo detectado.')
            else:
                raise ValidationError('Se ha producido un error de comunicación con la DIAN.')
        response_dict = xmltodict.parse(response.content)

        dic_result_verify_status['result_verify_status'] = False
        if response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusCode'] == '00':
            dic_result_verify_status['result_verify_status'] = True

        dic_result_verify_status['response_message_dian'] = \
            response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusCode'] + ' '
        dic_result_verify_status['response_message_dian'] += \
            response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusDescription'] + '\n'
        # dic_result_verify_status['response_message_dian'] += response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusMessage']
        dic_result_verify_status['ZipKey'] = \
            response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:XmlDocumentKey']
        return dic_result_verify_status

    def _template_GetStatusExistTest_xml(self):
        template_GetStatus_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatus</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:GetStatus>
            <wcf:trackId>%(trackId)s</wcf:trackId>
        </wcf:GetStatus>
    </soap:Body>
</soap:Envelope>
"""
        return template_GetStatus_xml
