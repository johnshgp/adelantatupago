# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, tools
from odoo.exceptions import Warning, UserError, ValidationError
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)


class HrAccruedRule(models.Model):
    _name = 'hr.accrued.rule'
    _description = 'Accrued Rule'

    name = fields.Char(required=True, string='Nombre')
    code = fields.Char(required=True, string='Código')
    sub_element = fields.Boolean(string='Sub Elemento')

