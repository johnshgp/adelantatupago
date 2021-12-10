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


class AccountTaxInherit(models.Model):
	_inherit = 'account.tax'

	tax_in_invoice = fields.Boolean(string="Evaluate in invoice", default=False, help="Check this if you want to hide the tax from the taxes list in products")
	dont_impact_balance = fields.Boolean(string="Don't impact balance", default=False, help="Check this if you want to assign counterpart taxes accounts")
	account_id_counterpart = fields.Many2one('account.account', string='Tax Account Counterpart', ondelete='restrict', help="Account that will be set on invoice tax lines for invoices. Leave empty to use the expense account.")
	refund_account_id_counterpart = fields.Many2one('account.account', string='Tax Account Counterpart on Refunds', ondelete='restrict', help="Account that will be set on invoice tax lines for refunds. Leave empty to use the expense account.")
	position_id = fields.Many2one('account.fiscal.position', string='Fiscal position related id')
	base_taxes = fields.One2many('account.base.tax', 'tax_id', string='Base taxes', help='This field show related taxes applied to this tax')

	@api.onchange('account_id_counterpart')
	def onchange_account_id_counterpart(self):
		self.refund_account_id_counterpart = self.account_id_counterpart

	def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True):
		result = super(AccountTaxInherit, self).compute_all(price_unit, currency=currency, quantity=quantity, product=product, partner=partner, is_refund=is_refund, handle_price_include=handle_price_include)
		for tax in self.sorted(key=lambda r: r.sequence):
			for iter_tax in result['taxes']:
				if iter_tax['id'] == tax.id:
					iter_tax['account_id_counterpart'] = tax.account_id_counterpart.id
					iter_tax['refund_account_id_counterpart'] = tax.refund_account_id_counterpart.id

		return result

AccountTaxInherit()
