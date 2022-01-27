# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from datetime import datetime, timedelta, date
from pytz import timezone
from odoo.exceptions import UserError, ValidationError


class ResCompanyInherit(models.Model):
    _inherit = 'res.company'

    digital_certificate_payroll = fields.Text(string="Certificado digital público", required=True, default="")
    software_identification_code_payroll = fields.Char(string="Código de identificación del software", required=True,
                                               default="")
    identificador_set_pruebas_payroll = fields.Char(string='Identificador del SET de pruebas', required=True)
    software_pin_payroll = fields.Char(string="PIN del software", required=True, default="")
    password_environment_payroll = fields.Char(string="Clave de ambiente", required=True, default="")
    seed_code_payroll = fields.Integer(string="Código de semilla", required=True, default=5000000)
    issuer_name_payroll = fields.Char(string="Ente emisor del certificado", required=True, default="")
    serial_number_payroll = fields.Char(string="Serial del certificado", required=True, default="")
    document_repository_payroll = fields.Char(string='Ruta de almacenamiento de archivos', required=True)
    certificate_key_payroll = fields.Char(string='Clave del certificado P12', required=True, default="")
    pem_payroll = fields.Char(string="Nombre del archivo PEM del certificado", required=True, default="")
    certificate_payroll = fields.Char(string="Nombre del archivo del certificado", required=True, default="")
    production_payroll = fields.Boolean(string='Pase a producción', default=False)
    xml_response_numbering_range_payroll = fields.Text(string='Contenido XML de la respuesta DIAN a la consulta de rangos',readonly=True)

