# -*- coding: utf-8 -*-
{
	'name': 'Adelanta tu pago',
	'version': '14.0',
    'author': 'Ivan Arriola - Autodidacta-TI',
	'category': 'Tools',
	'summary': 'Cuenta por cobrar de cliente a tercero',
    'license': 'OPL-1',
    'website': 'https://autodidactati.com',
	'depends': ['account','contacts','l10n_co_e-invoice','l10n_co_e-invoice_bulk_load'],
	'data': [
		'security/ir.model.access.csv',
		'views/account_move_inherit.xml',
		'views/account_payment_inherit.xml',
		'views/import_payments_view.xml',
		'wizards/res_config_settings_views.xml'
	],
	'demo': [
		],
	'css': [],
	'installable': True,
	'auto_install': False,
	'application': False,
}
