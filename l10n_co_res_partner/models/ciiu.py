#!/usr/bin/env python
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

from odoo import models, fields, api
import unicodedata

class Ciiu(models.Model):
	_name = "ciiu"  # res.co.ciiu
	_description = "ISIC List"


	HIERARCHY = [('1', 'Has Parent?'),
				('2', 'Has Division?'),
				('3', 'Has Section?')]

	name = fields.Char(string=u"Code and Description", store=True, compute="_compute_concat_name")
	code = fields.Char(string='Code', required=True)
	description = fields.Char(string='Description', required=True)
	type = fields.Char('Type',store=True,compute="_compute_set_type")
	has_parent = fields.Boolean(string='Has Parent?')
	parent = fields.Many2one('ciiu', string='Parent')
	has_division = fields.Boolean(string='Has Division?', default=False)
	division = fields.Many2one('ciiu', string='Division')
	has_section = fields.Boolean(string='Has Section?', default=False)
	section = fields.Many2one('ciiu', string='Section')
	hierarchy = fields.Selection(HIERARCHY, string='Hierarchy')


	@api.depends('code', 'description')
	def _compute_concat_name(self):
		"""
		This function concatinates two fields in order to be able to search
		for CIIU as number or string
		@return: void
		"""
		def remove_accent(cadena):
			s = ''.join((c for c in unicodedata.normalize('NFD',cadena) if unicodedata.category(c) != 'Mn'))
			return s

		for rec in self:
			if rec.code is False or rec.description is False:
				rec.name = ''
			else:
				rec.name = str(rec.code) + ' - ' + remove_accent(str(rec.description))



	@api.depends('has_parent')
	def _compute_set_type(self):
		"""
		Section, Division and Parent should be visually separated in the tree
		view. Therefore we tag them accordingly as 'view' or 'other'
		@return: void
		"""
		for rec in self:
			# Child
			if rec.has_parent is True:
				if rec.division is True:
					rec.type = 'view'
				elif rec.section is True:
					rec.type = 'view'
				else:
					rec.type = 'other'
			# Division
			else:
				rec.type = 'view'

Ciiu()