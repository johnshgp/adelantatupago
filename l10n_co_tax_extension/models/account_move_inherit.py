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
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo.tools.misc import formatLang, format_date

from datetime import date, timedelta
from itertools import groupby
from stdnum.iso7064 import mod_97_10
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import json
import re
import logging
import psycopg2

_logger = logging.getLogger(__name__)

#forbidden fields
INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')
INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')

class AccountMoveInherit(models.Model):
	""" This Model calculates and saves withholding tax that apply in
	Colombia"""
	_inherit = 'account.move'


	def compute_show_taxes_invoice(self):
		"""
			Funcion computada que permite calcular los impuestos y retenciones de la factura
		"""
		data = self.show_taxes_invoice()
		for x in self:
			x.html_tax_line_ids = data

	@api.model
	def create(self, vals):
		if not ('invoice_date' in vals) or vals['invoice_date'] == False:
			vals['invoice_date'] = fields.Date.context_today(self)
		res = super(AccountMoveInherit, self).create(vals)
		return res

	#@api.one
	def _get_has_valid_dian_info_JSON(self):
		if self.journal_id.secure_sequence_id.use_dian_control:
			remaining_numbers = self.journal_id.secure_sequence_id.remaining_numbers
			remaining_days = self.journal_id.secure_sequence_id.remaining_days
			dian_resolution = self.env['ir.sequence.dian_resolution'].search([('sequence_id','=',self.journal_id.secure_sequence_id.id),('active_resolution','=',True)])
			today = datetime.strptime(str(fields.Date.context_today(self)), '%Y-%m-%d')

			not_valid = False
			spent = False
			if len(dian_resolution) == 1 and self.state == 'draft':
				dian_resolution.ensure_one()
				date_to = datetime.strptime(str(dian_resolution['date_to']), '%Y-%m-%d')
				days = (date_to - today).days
				print('dias')
				print(days)

				if dian_resolution['number_to'] - dian_resolution['number_next'] < remaining_numbers or days < remaining_days:
					not_valid = True

				if dian_resolution['number_next'] > dian_resolution['number_to']:
					spent = True

			if spent:
				pass # This is when the resolution it's spent and we keep generating numbers

			self.not_has_valid_dian = not_valid
		else:
			self.not_has_valid_dian = False


	amount_without_wh_tax = fields.Monetary('Total With Tax', store=True, compute="_compute_amount")
	wh_taxes = fields.Float(string="Withholding Tax", store=True, compute="_compute_amount")
	#date_invoice = fields.Date(required=True)
	not_has_valid_dian = fields.Boolean(compute='_get_has_valid_dian_info_JSON', default=False)
	resolution_number = fields.Char('Resolution number in invoice')
	resolution_date = fields.Date(string="Resolution Date")
	resolution_date_to = fields.Date(string="Resolution Date To")
	resolution_number_from = fields.Integer(string="Resolution Number From")
	resolution_number_to = fields.Integer(string="Resolution Number To")
	#tax_line_ids = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines', oldname='tax_line', readonly=True, states={'draft': [('readonly', False)]}, copy=True)
	html_tax_line_ids = fields.Html(string="Tax Line ids", compute='compute_show_taxes_invoice')


	def validate_number_phone(self, data):
		"""
			Funcion que es utilizada en el reporte de factura para retornar la información de:
				->	Telefono
				->	Celular
		"""
		if data.phone and data.mobile:
			return data.phone + ' - ' + data.mobile
		if data.phone and not data.mobile:
			return data.phone
		if data.mobile and not data.phone:
			return data.mobile

	def validate_state_city(self, data):
		"""
			Funcion que es utilizada en el reporte de factura para retornar la información de:
				->	Pais
				->	Departamento
				->	Ciudad
		"""
		return ((data.country_id.name + ' ') if data.country_id.name else ' ') + ( ' ' + (data.state_id.name + ' ') if data.state_id.name else ' ') + (' ' + data.xcity.name if data.xcity.name else '')


	def search_tax_line(self, data, tax_group_id):
		"""
			Funcion que permite buscar el grupo de impuesto al que pertenece el impuesto
		"""
		if data:

			for x in data:
				if x['tax_group_id'] == tax_group_id:
					return True
		return False

	def update_data_tax_line(self, data, tax_group_id, vals):
		"""
			Funcion que permite actualizar la data del grupo de impuestos
		"""
		data_new = []
		if data:

			for x in data:
				if x['tax_group_id'] == tax_group_id:
					if x['taxes']:
						for tax in x['taxes']:
							data_new.append(tax)
					data_new.append(vals)
					x['taxes'] = data_new


	def load_line_tax_ids(self):
		"""
			Funcion que permite cargar los impuestos agrupados
		"""
		data = []
		for x in self.line_ids:
			if x.tax_line_id:

				vals = {
				'account_name': x.account_id.name,
				'account_code': x.account_id.code,
				'tax_id': x.tax_line_id.id,
				'tax': x.tax_line_id.name,
				'tax_amount': x.price_total,
				'base': x.tax_base_amount
				}
				if self.search_tax_line(data, x.tax_group_id.id) == False:
					value = {
					'tax_group_id': x.tax_group_id.id,
					'tax_group_name': x.tax_group_id.name,
					'taxes': [vals]
					}
					data.append(value)
				else:
					self.update_data_tax_line(data, x.tax_group_id.id, vals)

		return data

	def show_taxes_invoice(self):
		"""
			Funcion que permite cargar la tabla con los impuestos
		"""
		data = self.load_line_tax_ids()

		if data:

			thead = """

					<div class="table-wrapper-scroll-y my-custom-scrollbar">
						<table class="table">
						  <thead class="thead-light">
							<tr>
							  <th scope="col">#</th>
							  <th scope="col">Cuenta</th>
							  <th scope="col">Descripción</th>
							  <th scope="col">Base</th>
							  <th scope="col">Valor</th>
							</tr>
						  </thead>
						  <tbody>

					  """
			body= ""
			flag = 1
			count = 1
			for x in data:
				if x['tax_group_id']:
					body += "<tr>\n"
					body += "<th scope='row'>" + str(count) + "</th> \n"
					body += "<th scope='row'>" + '' + "</th>\n"
					body += "<th scope='row'>" + str(x['tax_group_name']) + "</th>\n"
					body += "<th scope='row'>" + '' + "</th>\n"
					body += "<tr>\n"

					for tax in x['taxes']:

						body += "<tr>\n"
						body += "<th scope='row'>" + str(count) + '.' + str(flag) + "</th> \n"
						body += "<th scope='row'>" + str(tax['account_code']) + ' ' + str(tax['account_name']) + "</th>\n"
						body += "<th scope='row'>" + str(tax['tax']) + "</th>\n"
						body += "<th scope='row'>" + str(tax['base']) + "</th>\n"
						body += "<th scope='row'>" + str(tax['tax_amount']) + "</th>\n"
						body += "<tr>\n"
						flag +=1
				count +=1
				flag=1

			end_table = """
								</tbody>
							</table>
						</div>


					"""

			table =  thead + body + end_table

			return table




	@api.onchange('invoice_line_ids')
	def _onchange_tax_line_ids(self):
		"""
			Funcion que permite actualizar los impuestos y retenciones
		"""
		self.html_tax_line_ids = self.show_taxes_invoice()



	"""
	#@api.one
	@api.depends('state', 'currency_id', 'invoice_line_ids.price_subtotal', 'move_id.line_ids.amount_residual', 'move_id.line_ids.currency_id')
	def _compute_residual(self):
		fp_company = self.env['account.fiscal.position'].search([('id', '=', self.company_id.partner_id.property_account_position_id.id)])
		company_tax_ids = [base_tax.tax_id.id for base_tax in fp_company.tax_ids_invoice]

		residual = 0.0
		residual_company_signed = 0.0
		sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
		for line in self.sudo().move_id.line_ids:
			if line.tax_line_id.id not in company_tax_ids:
				if line.account_id.internal_type in ('receivable', 'payable'):
					residual_company_signed += line.amount_residual
					if line.currency_id == self.currency_id:
						residual += line.amount_residual_currency if line.currency_id else line.amount_residual
					else:
						from_currency = (line.currency_id and line.currency_id.with_context(date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
						residual += from_currency.compute(line.amount_residual, self.currency_id)
		self.residual_company_signed = abs(residual_company_signed) * sign
		self.residual_signed = abs(residual) * sign
		self.residual = abs(residual)
		digits_rounding_precision = self.currency_id.rounding
		if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
			self.reconciled = True
		else:
			self.reconciled = False
	"""


	def validate_type(self, record, type_tax_use, date_record):
		"""
			Funcion que permite validar si el valor de la factura es superior al impuesto configurado para poderlo aplicar
		"""

		if record.type_tax_use == type_tax_use:
		
			if record.base_taxes:
			
				for y in record.base_taxes:

					if y.start_date and y.end_date:

						if datetime.strptime(str(y.start_date), '%Y-%m-%d').date() >= date_record or date_record <= datetime.strptime(str(y.end_date), '%Y-%m-%d').date():
			
							sum_total = sum(x.price_subtotal for x in self.invoice_line_ids if self.invoice_line_ids)
							
							if sum_total >= y.amount:
								
								return True

		return False




	def return_data_wh_taxes(self):
		"""
			Funcion que permite retornar los impuestos anteriormente configurados en la posicion fiscal,
			para mostrar la data de los impuestos de las retenciones
		"""

		data=[]
		flag= False
		if self.invoice_date:
			date= datetime.strptime(str(self.invoice_date), '%Y-%m-%d').date()

			fiscal_position = self.fiscal_position_id

			if fiscal_position:

				if fiscal_position.tax_ids_invoice:

					for x in fiscal_position.tax_ids_invoice:

						if x.tax_id:

							#factura proveedor
							if self.move_type == 'in_invoice':
								flag=self.validate_type(x.tax_id, 'purchase', date)
							#factura cliente
							if self.move_type == 'out_invoice':
								flag=self.validate_type(x.tax_id, 'sale', date)

							if self.move_type == 'out_refund':
								flag=self.validate_type(x.tax_id, 'sale', date)

							if flag:
								data.append(x.tax_id.id)

		#data contiene las retenciones que fueron establecidas en la posicion fiscal
		return data


	@api.depends(
		'line_ids.debit',
		'line_ids.credit',
		'line_ids.currency_id',
		'line_ids.amount_currency',
		'line_ids.amount_residual',
		'line_ids.amount_residual_currency',
		'line_ids.payment_id.state', 'amount_tax', 'amount_tax_signed')
	def _compute_amount(self):
		"""
			Funcion que permite calcular el total de la factura y retenciones
		"""
		super(AccountMoveInherit, self)._compute_amount()

		fp_company = self.env['account.fiscal.position'].search([('id', '=', self.company_id.partner_id.property_account_position_id.id)])
		company_tax_ids = [base_tax.tax_id.id for base_tax in fp_company.tax_ids_invoice]

		data_wh_taxes = None
		for record in self:
			data_wh_taxes = record.return_data_wh_taxes()

			tax_line_ids = []
			for x in record.load_line_tax_ids():
				for tax in x['taxes']:
					vals = {
					'tax_id': tax['tax_id'],
					'tax_amount': tax['tax_amount']
					}
					tax_line_ids.append(vals)

			if record.fiscal_position_id:
				fp_partner = self.env['account.fiscal.position'].search([('id','=',record.fiscal_position_id.id)])
				partner_tax_ids = [base_tax.tax_id.id for base_tax in fp_partner.tax_ids_invoice]
				sum_amount_total = sum(
					line['tax_amount'] for line in tax_line_ids if line['tax_id'] not in partner_tax_ids)
			
				#suma de retenciones
				sum_wh_taxes = 0
				if data_wh_taxes and record.move_type != 'out_refund':
					sum_wh_taxes = sum(line['tax_amount'] for line in tax_line_ids if line['tax_id'] in partner_tax_ids)

				record.wh_taxes = abs(sum_wh_taxes)
				record.amount_tax = sum_amount_total
				record.amount_tax_signed = sum_amount_total 

			else:
				record.wh_taxes = 0

			record.amount_without_wh_tax = record.amount_untaxed + record.amount_tax
			record.amount_total = record.amount_without_wh_tax - record.wh_taxes
			sign = record.move_type in ['in_refund', 'out_refund'] and -1 or 1
			record.amount_total_signed = record.amount_total * sign


	@api.onchange('partner_id', 'company_id',)
	def _onchange_partner_id(self):
		#self.invoice_date = fields.Date.context_today(self)
		res = super(AccountMoveInherit, self)._onchange_partner_id()
		self._onchange_invoice_line_ids()
		return res



	@api.onchange('fiscal_position_id','invoice_date')
	def _onchange_fiscal_position_id(self):
		if not self.invoice_date:
			self.invoice_date = fields.Date.context_today(self)
		self._onchange_invoice_line_ids()


	def post(self):
		"""
			Funcion que permite guardar los datos de la resolucion de la factura cuando esta es confirmada
		"""
		result = super(AccountMoveInherit, self).post()

		for inv in self:
			sequence = self.env['ir.sequence.dian_resolution'].search([('sequence_id','=',self.journal_id.secure_sequence_id.id),('active_resolution','=',True)], limit=1)

			inv.resolution_number = sequence['resolution_number']
			inv.resolution_date = sequence['date_from']
			inv.resolution_date_to = sequence['date_to']
			inv.resolution_number_from = sequence['number_from']
			inv.resolution_number_to = sequence['number_to']
		return result


	def _recompute_tax_lines(self, recompute_tax_base_amount=False):
		''' Compute the dynamic tax lines of the journal entry.

		:param lines_map: The line_ids dispatched by type containing:
			* base_lines: The lines having a tax_ids set.
			* tax_lines: The lines having a tax_line_id set.
			* terms_lines: The lines generated by the payment terms of the invoice.
			* rounding_lines: The cash rounding lines of the invoice.
		'''
		self.ensure_one()
		in_draft_mode = self != self._origin

		def _serialize_tax_grouping_key(grouping_dict):
			''' Serialize the dictionary values to be used in the taxes_map.
			:param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
			:return: A string representing the values.
			'''
			return '-'.join(str(v) for v in grouping_dict.values())

		def _compute_base_line_taxes(base_line):
			''' Compute taxes amounts both in company currency / foreign currency as the ratio between
			amount_currency & balance could not be the same as the expected currency rate.
			The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
			:param base_line:   The account.move.line owning the taxes.
			:return:            The result of the compute_all method.
			'''
			move = base_line.move_id

			if move.is_invoice(include_receipts=True):
				sign = -1 if move.is_inbound() else 1
				quantity = base_line.quantity
				if base_line.currency_id:
					price_unit_foreign_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
					price_unit_comp_curr = base_line.currency_id._convert(price_unit_foreign_curr, move.company_id.currency_id, move.company_id, move.date)
				else:
					price_unit_foreign_curr = 0.0
					price_unit_comp_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
			else:
				quantity = 1.0
				price_unit_foreign_curr = base_line.amount_currency
				price_unit_comp_curr = base_line.balance

			taxes = base_line.tax_ids._origin

			fp = self.env['account.fiscal.position'].search([('id','=',self.fiscal_position_id.id)])
			if fp:
				type_tax = 'sale' if self.move_type in ('out_invoice', 'out_refund') else 'purchase'

				tax_ids = self.env['account.tax'].search([('id','in',[tax.tax_id.id for tax in fp.tax_ids_invoice]),
															  ('type_tax_use','=',type_tax),
															  ('base_taxes','>',0)])
				tax_ids = [tax.id for tax in tax_ids]

				base_taxes = []
				if self.move_type in ('in_refund', 'out_refund') and self.wh_taxes:
					base_taxes = self.env['account.base.tax'].search([('start_date', '<=', self.invoice_date),
																	  ('end_date', '>=', self.invoice_date),
																	  # ('amount', '<=', self.amount_untaxed),
																	  ('tax_id', 'in', tax_ids)])
				else:
					base_taxes = self.env['account.base.tax'].search([('start_date','<=',self.invoice_date),
																	  ('end_date','>=',self.invoice_date),
																	  ('amount', '<=', self.amount_untaxed),
																	  ('tax_id','in',tax_ids)])

				if base_taxes:

					taxes_update = []
					for x in taxes:
						taxes_update.append(x.id)
					for x in base_taxes:
						taxes_update.append(x.tax_id.id)

					taxes = self.env['account.tax'].search([('id', 'in', taxes_update)])
					print('all taxes')
					print(taxes)


			balance_taxes_res = taxes.compute_all(
				price_unit_comp_curr,
				currency=base_line.company_currency_id,
				quantity=quantity,
				product=base_line.product_id,
				partner=base_line.partner_id,
				is_refund=self.move_type in ('out_refund', 'in_refund'),
			)

		
			if base_line.currency_id:
				# Multi-currencies mode: Taxes are computed both in company's currency / foreign currency.
				amount_currency_taxes_res = base_line.tax_ids._origin.compute_all(
					price_unit_foreign_curr,
					currency=base_line.currency_id,
					quantity=quantity,
					product=base_line.product_id,
					partner=base_line.partner_id,
					is_refund=self.move_type in ('out_refund', 'in_refund'),
				)
				for b_tax_res, ac_tax_res in zip(balance_taxes_res['taxes'], amount_currency_taxes_res['taxes']):
					tax = self.env['account.tax'].browse(b_tax_res['id'])
					b_tax_res['amount_currency'] = ac_tax_res['amount']

					# A tax having a fixed amount must be converted into the company currency when dealing with a
					# foreign currency.
					if tax.amount_type == 'fixed':
						b_tax_res['amount'] = base_line.currency_id._convert(b_tax_res['amount'], move.company_id.currency_id, move.company_id, move.date)

			return balance_taxes_res

		taxes_map = {}

		# ==== Add tax lines ====
		for line in self.line_ids.filtered('tax_repartition_line_id'):
			grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
			grouping_key = _serialize_tax_grouping_key(grouping_dict)
			taxes_map[grouping_key] = {
				'tax_line': line,
				'balance': 0.0,
				'amount_currency': 0.0,
				'tax_base_amount': 0.0,
				'grouping_dict': False,
			}
			print('****')
			print(taxes_map[grouping_key])

		# ==== Mount base lines ====
		for line in self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab):
			# Don't call compute_all if there is no tax.
			if not line.tax_ids:
				line.tax_tag_ids = [(5, 0, 0)]
				continue

			print('----')
			print(line)
			compute_all_vals = _compute_base_line_taxes(line)

			# Assign tags on base line
			line.tax_tag_ids = compute_all_vals['base_tags']

			tax_exigible = True
			for tax_vals in compute_all_vals['taxes']:
				grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
				grouping_key = _serialize_tax_grouping_key(grouping_dict)

				tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
				tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

				if tax.tax_exigibility == 'on_payment':
					tax_exigible = False

				taxes_map_entry = taxes_map.setdefault(grouping_key, {
					'tax_line': None,
					'balance': 0.0,
					'amount_currency': 0.0,
					'tax_base_amount': 0.0,
					'grouping_dict': False,
				})
				taxes_map_entry['balance'] += tax_vals['amount']
				taxes_map_entry['amount_currency'] += tax_vals.get('amount_currency', 0.0)
				taxes_map_entry['tax_base_amount'] += tax_vals['base']
				taxes_map_entry['grouping_dict'] = grouping_dict
			line.tax_exigible = tax_exigible

		# ==== Process taxes_map ====
		for taxes_map_entry in taxes_map.values():
			# Don't create tax lines with zero balance.
			if self.currency_id.is_zero(taxes_map_entry['balance']) and self.currency_id.is_zero(taxes_map_entry['amount_currency']):
				taxes_map_entry['grouping_dict'] = False

			tax_line = taxes_map_entry['tax_line']
			tax_base_amount = -taxes_map_entry['tax_base_amount'] if self.is_inbound() else taxes_map_entry['tax_base_amount']

			if not tax_line and not taxes_map_entry['grouping_dict']:
				continue
			elif tax_line and not taxes_map_entry['grouping_dict']:
				# The tax line is no longer used, drop it.
				self.line_ids -= tax_line
			elif tax_line:
				tax_line.update({
					'amount_currency': taxes_map_entry['amount_currency'],
					'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
					'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
					'tax_base_amount': tax_base_amount,
				})
			else:
				create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
				tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
				tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
				tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
				tax_line = create_method({
					'name': tax.name,
					'move_id': self.id,
					'partner_id': line.partner_id.id,
					'company_id': line.company_id.id,
					'company_currency_id': line.company_currency_id.id,
					'quantity': 1.0,
					'date_maturity': False,
					'amount_currency': taxes_map_entry['amount_currency'],
					'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
					'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
					'tax_base_amount': tax_base_amount,
					'exclude_from_invoice_tab': True,
					'tax_exigible': tax.tax_exigibility == 'on_invoice',
					**taxes_map_entry['grouping_dict'],
				})

			if in_draft_mode:
				tax_line._onchange_amount_currency()
				tax_line._onchange_balance()


	#@api.multi
	# def _get_tax_amount_by_group(self):
	# 	self.ensure_one()
	# 	res = {}
	# 	currency = self.currency_id or self.company_id.currency_id
	# 	for line in self.tax_line_ids:
	# 		if not line.tax_id.dont_impact_balance:
	# 			res.setdefault(line.tax_id.tax_group_id, 0.0)
	# 			res[line.tax_id.tax_group_id] += line.amount
			
	# 	res = sorted(res.items(), key=lambda l: l[0].sequence)
	# 	res = map(lambda l: (l[0].name, formatLang(self.env, l[1], currency_obj=currency)), res)

	# 	groups_not_in_invoice = self.env['account.tax.group'].search_read([('not_in_invoice','=',True)],['name'])

	# 	for g in groups_not_in_invoice:
	# 		for i in res:
	# 			if g['name'] == i[0]:
	# 				res.remove(i)
	# 	return res
				
AccountMoveInherit()