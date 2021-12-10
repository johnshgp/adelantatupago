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

from odoo import api, fields, models

import pprint
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class AccountBaseTax(models.Model):
	_name = 'account.base.tax'
	_rec_name = 'tax_id'

	tax_id = fields.Many2one('account.tax', string='Tax related')
	start_date = fields.Date(string='Since date', required=True)
	end_date = fields.Date(string='Until date', required=True)
	amount = fields.Float(digits=0, default=0, string="Tax amount", required=True)
	# currency_id = fields.Many2one('res.currency', related='tax_id.company_id.currency_id', store=True)

	#@api.one
	@api.constrains('start_date', 'end_date')
	def _check_closing_date(self):
		if self.start_date and self.end_date and self.end_date < self.start_date:
			raise ValidationError("Error! End date cannot be set before start date.")


	@api.constrains('start_date', 'end_date')
	def _dont_overlap_date(self):

		domain = [	('start_date', '<=', self.end_date), 
					('end_date', '>=', self.start_date), 
					('tax_id', '=', self.tax_id.id), 
					('id', '<>', self.id)]

		bases_ids = self.search(domain)

		if bases_ids:
			raise ValidationError("Error! cannot have overlap date range.")

AccountBaseTax()
