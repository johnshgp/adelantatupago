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


{
	'name': 'Impuestos - Colombia',
	'category': 'Localization',
    'version': '13.0',
    'author': 'Brayhan Andres Jaramillo Castaño, Odoo LoCo',
    'license': 'AGPL-3',
    'maintainer': 'brayhanjaramillo@hotmail.com, Odoo LoCo',
    'website': 'https://github.com/odooloco',
	'summary': 'Impuestos de Colombia: Modulo de Facturacion - Odoo 12.0',
	'description': """
Impuestos Colombia:
======================
	* Este módulo calcula algunos impuestos colombianos que deben aplicarse.
	* Primer impuesto: retención de impuestos, que se calcula en un 2,4% del monto no tributado y se calcula con el monto total
	""",
	'depends': [
		'account',
		'sale',
		'purchase',
		'l10n_co_res_partner',
		'web'
	],
	'data': [
		'security/ir.model.access.csv',
		'views/account_base_tax_view.xml',
		'views/account_fiscal_position_base_tax_view.xml',
		'views/account_fiscal_position_inherit_view.xml',
		'views/account_tax_inherit_view.xml',
		'views/ir_sequence_view.xml',
		'views/product_template_inherit_view.xml',
		'views/account_move_inherit_view.xml',
		'report/external_layout_report.xml',
		'report/report_invoice_inherit_view.xml',


		#'views/l10n_co_tax_extension.xml',
		#'views/report_invoice_document_inherit.xml',
		#
	],
	'installable': True,
	'application': True,
	'auto_install': False,
}
