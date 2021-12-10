# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date

class IrAttachmentInherit(models.Model):
    _inherit = "ir.attachment"

    TYPE = [('url', 'URL'),
			('binary', 'File'),
			('out_invoice', 'Out Invoice'),
			('out_refund', 'Out Refund')]

    type = fields.Selection(TYPE, string='Type', required=True, default='binary', change_default=True)

IrAttachmentInherit()