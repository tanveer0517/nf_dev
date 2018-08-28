from odoo import api, models, fields, _, SUPERUSER_ID

class ouc_hr_department(models.Model):
    _inherit = 'hr.department'
    
    c_type = fields.Selection([('FOS', 'FOS Sales'), ('mlc', 'MLC Sales'), ('la', 'LA/NA Sales')], string='Category(If Sales type)')
