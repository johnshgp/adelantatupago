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

from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
import re
import logging
_logger = logging.getLogger(__name__)


class ResCountryStateCity(models.Model):
	"""
	Model added to manipulate separately the cities on Partner address.
	"""
	_description = 'Model to manipulate Cities'
	_name = 'res.country.state.city'
	_order = 'code'

	code = fields.Char(string='City Code', size=5, help='Code DANE - 5 digits-', required=True)
	name = fields.Char(string='City Name', size=64, required=True)
	state_id = fields.Many2one('res.country.state', string='State', required=True)
	country_id = fields.Many2one('res.country', string='Country', required=True)


	def name_get(self):
		result = []
		for record in self:
			result.append((record.id, "%s (%s)" % (record.name, record.state_id.code)))
		return result
		
ResCountryStateCity()

class ResCountryState(models.Model):
	_inherit = "res.country.state"

	code_dian = fields.Char(string="Code Dian", size=3, help="Code for dian")
