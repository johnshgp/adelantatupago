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

from odoo import api, fields, models

import pprint
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class AccountJournalInherit(models.Model):
	_name = "account.journal"
	_inherit = "account.journal"

	@api.model
	def create(self, vals):
		return super(AccountJournalInherit, self).create(vals)

	@api.model
	def _create_sequence(self, vals, refund=False):
		return super(AccountJournalInherit, self)._create_sequence(vals, refund)

AccountJournalInherit()
