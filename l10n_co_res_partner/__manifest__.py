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
    'name': 'Terceros - Colombia',
    'category': 'Localization',
    'version': '14.0',
    'author': 'Brayhan Andres Jaramillo Castaño, Odoo LoCo',
    'license': 'AGPL-3',
    'maintainer': 'brayhanjaramillo@hotmail.com',
    'website': 'https://github.com/odooloco',
    'summary': 'Terceros Colombia: Extendido de Partner / '
               'Modulo de Contactos - Odoo 14.0',
    'images': ['images/main_screenshot.png'],
    'depends': [
        'base',
        'base_address_city',
        'l10n_co',
        'account',
        'contacts'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_co_cities_data.xml',
        'data/ciiu.csv',
        'data/l10n_latam.identification.type.csv',
        'views/ciiu_view.xml',
        'views/menu.xml',
        'views/l10n_co_res_partner.xml',
        #'views/website.xml',



    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
