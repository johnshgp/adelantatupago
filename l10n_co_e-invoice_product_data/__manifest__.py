# -*- coding: utf-8 -*-
{
	'name': 'Product Data - Colombia',
	'version': '14.0',
    'author': 'Ivan Arriola - Autodidacta TI - Backendevs',
	'category': 'Tools',
	'summary': 'Carga las datos necesarios en productos de localizacion Colombiana',
    'license': 'OPL-1',
    'website': 'https://autodidactati.com',
	'depends': ['l10n_co_e-invoice','base'],
	'data': [
		'data/data_class.xml',
		'data/data_family.xml',
		'data/data_segment.xml',
		'data/data_producto.xml',
		'views/menu_data.xml',
	],
	'demo': [
		],
	'css': [],
	'installable': True,
	'auto_install': False,
	'application': False,
}
