from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    
    journal_id_def = fields.Many2one(
        comodel_name='account.journal',
        string='Diario por defecto para pagos directos de factura', 
        config_parameter='adelantatupago.journal_def'
    )