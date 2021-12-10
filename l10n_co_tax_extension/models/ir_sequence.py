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


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.tools.misc import formatLang, format_date
from datetime import datetime, timedelta, date
from odoo.addons.base.models.ir_sequence import _update_nogap

import pprint
import logging
_logger = logging.getLogger(__name__)

class IrSequenceInherit(models.Model):
	_inherit = 'ir.sequence'


	DIAN_TYPE = [	('invoice_computer_generated', 'Invoice generated from computer'),
					('pos_invoice', 'POS Invoice')]

	use_dian_control = fields.Boolean('Use DIAN control resolutions', default=False)
	remaining_numbers = fields.Integer(default=1, help='Remaining numbers')
	remaining_days = fields.Integer(default=1, help='Remaining days')
	sequence_dian_type = fields.Selection(DIAN_TYPE, 'Type', required=True, default='invoice_computer_generated')
	dian_resolution_ids = fields.One2many('ir.sequence.dian_resolution', 'sequence_id', 'DIAN Resolutions')

	@api.model
	def check_active_resolution(self, sequence_id):    
		
		dian_resolutions_sequences_ids = self.search([('use_dian_control', '=', True),('id', '=', sequence_id)])

		for record in dian_resolutions_sequences_ids:
			if record:

				if len( record.dian_resolution_ids ) > 1:
					actual_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

					for resolution in record.dian_resolution_ids:
						if resolution.number_next_actual >= resolution.number_from and resolution.number_next_actual <= resolution.number_to and  actual_date <= resolution.date_to:
							self.check_active_resolution_cron()
							return True

		return False

	@api.model
	def check_active_resolution_cron(self):

		dian_resolutions_sequences_ids = self.search([('use_dian_control', '=', True)])

		for record in dian_resolutions_sequences_ids:
			if record:

				if len( record.dian_resolution_ids ) > 1:
					actual_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
					_active_resolution = False

				   
					for resolution in record.dian_resolution_ids:

						if resolution.number_next_actual >= resolution.number_from and resolution.number_next_actual <= resolution.number_to and  actual_date <= resolution.date_to and resolution.active_resolution:
							continue
							continue

					_active_resolution = False
												   
					for resolution in record.dian_resolution_ids:
						if _active_resolution:
							continue
							continue

						if resolution.number_next_actual >= resolution.number_from and resolution.number_next_actual <= resolution.number_to and  actual_date <= resolution.date_to:
							record.dian_resolution_ids.write({
								'active_resolution' : False
							})

							resolution.write({
									'active_resolution' : True        
							}) 

							_active_resolution = True                           

								 
	def _next(self, sequence_date=None):
		if not self.use_dian_control:
			return super(IrSequenceInherit, self)._next(sequence_date=sequence_date)

		seq_dian_actual = self.env['ir.sequence.dian_resolution'].search([('sequence_id','=',self.id),('active_resolution','=',True)], limit=1)
		_logger.info(seq_dian_actual)

		if seq_dian_actual.exists(): 
			number_actual = seq_dian_actual._next()
			if seq_dian_actual['number_next']-1 > seq_dian_actual['number_to']:
				seq_dian_next = self.env['ir.sequence.dian_resolution'].search([('sequence_id','=',self.id),('active_resolution','=',True)], limit=1, offset=1)
				if seq_dian_next.exists():
					seq_dian_actual.active_resolution = False
					return seq_dian_next._next()
			return number_actual
		return super(IrSequenceInherit, self)._next(sequence_date=sequence_date)

		

	@api.constrains('dian_resolution_ids')   
	def val_active_resolution(self):  

		_active_resolution = 0

		if self.use_dian_control:

			for record in self.dian_resolution_ids:
				if record.active_resolution:
					_active_resolution += 1

			if _active_resolution > 1:
				raise ValidationError( _('The system needs only one active DIAN resolution') )

			if _active_resolution == 0:
				raise ValidationError( _('The system needs at least one active DIAN resolution') )
				 

IrSequenceInherit()				


