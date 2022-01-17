# -*- coding: utf-8 -*-

{
    'name': "Colombian e-invoice",

    'summary': """
        Genera la facturacion electronica para la distribucion colombiana segun requisitos de la DIAN""",
    'category': 'Administration',
    'version': '10.0',
    'depends': [
        'account', 'l10n_co_tax_extension', 'base', 'contacts', 'od_journal_sequence'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/dian_fiscal_responsability_data.xml',
        'data/dian_tributes_data.xml',
        'data/sequence.xml',
        'data/dian_cron.xml',
        'data/scheduled_actions.xml',
        'views/dian_document_view.xml',
        'views/res_company_inherit_view.xml',
        'views/account_journal_inherit_view.xml',
        'views/account_move_inherit_view.xml',
        'views/res_partner_inherit_view.xml',
        'views/report_invoice.xml',
        'views/account_tax_inherit_view.xml',
        'views/ir_sequence_inherit_view.xml',
        'views/product_template_inherit_view.xml',
        'views/l10n_cities_co_view.xml',
        'wizards/validate_invoice.xml'
    ],

	'external_dependencies': {
		'python': ['pyopenssl', 
					'pyOpenSSL',
					'requests',
					'xmltodict',
					'PyQRCode',
					'pypng',
					'pyqrcode',
					'cryptography',
					'crypto',
					'xmltodict',
					'uuid',
					'hashlib'
					],
	},
	
    'installable' : True
}
