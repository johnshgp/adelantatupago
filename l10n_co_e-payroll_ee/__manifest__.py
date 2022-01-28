# -*- coding: utf-8 -*-
{
    'name': 'Nomina Electronica Colombia Enterprise',
    'version': '14.0.0.0.1',
    'category': 'Payroll',
    'license': 'OPL-1',
    'summary': 'Nomina Electronica Colombia',
    'description': """Nomina Electronica Colombia Enterprise""",
    'author': 'Backendevs',
    'website': 'http://www.backendevs.com',
    'maintaner': 'Backendevs',
    'depends': ['hr_payroll', 'l10n_co_e-payroll'],
    'data': [
        'views/menu.xml',
        'data/mail_template_hr_payslip.xml',
        'security/ir.model.access.csv',
        'views/hr_payslip.xml',
        'views/hr_salary_rule_inherit_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}