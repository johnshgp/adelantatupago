# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
#                                                                             #
# Part of Odoo. See LICENSE file for full copyright and licensing details.    #
#                                                                             #
#                                                                             #
# Copyright (C)                                               				  #
#    Autor: Brayhan Andres Jaramillo Castaño								  #
#    Correo: brayhanjaramillo@hotmail.com 		                  			  #
#                                                                             #
# Co-Authors    Odoo LoCo                                                     #
#               Localización funcional de Odoo para Colombia                  #
#                                                                             #
###############################################################################

# Extended Partner Module
from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
import re
import logging
_logger = logging.getLogger(__name__)


class ResPartnerInherit(models.Model):
	_inherit = 'res.partner'

	def _display_address(self, without_company=False):

		'''
		The purpose of this function is to build and return an address formatted accordingly to the
		standards of the country where it belongs.

		:param address: browse record of the res.partner to format
		:returns: the address formatted in a display that fit its country habits (or the default ones
			if not country is specified)
		:rtype: string
		'''
		# get the information that will be injected into the display format
		# get the address format
		address_format = self._get_address_format()
		args = {
			'state_code': self.state_id.code or '',
			'state_name': self.state_id.name or '',
			'country_code': self.country_id.code or '',
			'country_name': self._get_country_name(),
			'company_name': self.commercial_company_name or '',
		}
		for field in self._formatting_address_fields():
			args[field] = getattr(self, field) or ''
		if without_company:
			args['company_name'] = ''
		elif self.commercial_company_name:
			address_format = '%(company_name)s\n' + address_format

		args['city'] = args['city'].capitalize() + ','
		return address_format % args


ResPartnerInherit()

