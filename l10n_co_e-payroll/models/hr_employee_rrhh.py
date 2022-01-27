from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class HrEmpleado(models.Model):
    _inherit = "hr.employee"
    _description = "Empleado RRHH"

    salud_ids = fields.Many2one('res.partner', string='Salud')
    cesantias_ids = fields.Many2one('res.partner', string='Cesantias')
    pension_ids = fields.Many2one('res.partner', string='Pensión')