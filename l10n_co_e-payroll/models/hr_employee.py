from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    type_worker = fields.Many2one('hr.type.worker', string="Tipo de Trabajador")
    sub_type_worker = fields.Many2one('hr.sub.type.worker', string="Sub tipo de Trabajador")
