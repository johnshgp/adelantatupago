# -*- coding: utf-8 -*-
{
	'name': 'Invoice Loader',
	'version': '14.0',
    'author': 'Ivan Arriola - Autodidacta TI',
	'category': 'Tools',
	'summary': 'Carga de facturas y clientes por CSV',
    'license': 'OPL-1',
    'website': 'https://autodidactati.com',
	'depends': ['account','contacts','l10n_co_res_partner'],
	'data': [
		'security/ir.model.access.csv',
		'views/import_clients.xml',
		'views/import_invoice.xml',
		'views/account_move_inherit.xml',
	],
	'demo': [
		],
	'css': [],
	'installable': True,
	'auto_install': False,
	'application': False,
}
