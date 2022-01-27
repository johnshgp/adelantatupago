from odoo import fields, models, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    type_contract = fields.Many2one('hr.type.contract', string="Tipo de contrato")
