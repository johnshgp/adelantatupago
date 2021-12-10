# -*- coding: utf-8 -*-
###################################################################################
###################################################################################
##                                                                               ##
##    OpenERP, Open Source Management Solution                                   ##
##    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).                      ##
##                                                                               ##
##    This program is free software: you can redistribute it and/or modify       ##
##    it under the terms of the GNU Affero General Public License as             ##
##    published by the Free Software Foundation, either version 3 of the         ##
##    License, or (at your option) any later version.                            ##
##                                                                               ##
##    This program is distributed in the hope that it will be useful,            ##
##    but WITHOUT ANY WARRANTY; without even the implied warranty of             ##
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              ##
##    GNU Affero General Public License for more details.                        ##
##                                                                               ##
##    Autor: Brayhan Andres Jaramillo Castaño                                    ##
##    Correo: brayhanjaramillo@hotmail.com                                       ##
##                                                                               ##
##    You should have received a copy of the GNU Affero General Public License   ##
##    along with this program.  If not, see <http://www.gnu.org/licenses/>.      ##
##                                                                               ##
##                                                                               ##
##     Co-Authors    Odoo LoCo                                                   ##
##     Localización funcional de Odoo para Colombia                              ##
##                                                                               ##
###################################################################################
###################################################################################


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.tools.misc import formatLang, format_date
from datetime import datetime, timedelta, date
from odoo.addons.base.models.ir_sequence import _update_nogap

import pprint
import logging
_logger = logging.getLogger(__name__)


class IrSequenceDianResolution(models.Model):
	_name = 'ir.sequence.dian_resolution'
	_rec_name = "sequence_id"

	def _get_number_next_actual(self):
		for element in self:
			element.number_next_actual = element.number_next

	def _set_number_next_actual(self):
		for record in self:
			record.write({'number_next': record.number_next_actual or 0})

	@api.depends('number_from')
	def _get_initial_number(self):
		for record in self:
			if not record.number_next:
				record.number_next = record.number_from

	resolution_number = fields.Char('Resolution number', required=True)
	date_from = fields.Date('From', required=True)
	date_to = fields.Date('To', required=True)
	number_from = fields.Integer('Initial number', required=True)
	number_to = fields.Integer('Final number', required=True)
	number_next = fields.Integer('Next Number', compute='_get_initial_number', store=True)
	number_next_actual = fields.Integer(compute='_get_number_next_actual', inverse='_set_number_next_actual', string='Next Number', required=True, default=1, help="Next number of this sequence")
	active_resolution = fields.Boolean('Active resolution', required=False, default=False)
	sequence_id = fields.Many2one("ir.sequence", 'Main Sequence', required=True, ondelete='cascade')

	def _next(self):
		number_next = _update_nogap(self, 1)
		return self.sequence_id.get_next_char(number_next)

	@api.model
	def create(self, values):
		res = super(IrSequenceDianResolution, self).create(values)
		return res

IrSequenceDianResolution()