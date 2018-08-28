from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError


class ouc_analytic_account(models.Model):
    _inherit = 'account.move.line'
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Centre')
    c_pl_group = fields.Selection([('COGS','COGS'),('S&M','S&M'),('G&A','G&A')],"P & L Group")


class ouc_analytic_account_line(models.Model):
    _inherit='account.analytic.line'

    account_id = fields.Many2one('account.analytic.account', 'Cost Centre', required=True, ondelete='restrict', index=True)
    
    def _get_sale_order_line(self, vals=None):
        result = dict(vals or {})
        so_line = result.get('so_line', False) or self.so_line
        return result


class ouc_account_account(models.Model):
    _inherit = 'account.account'

    c_active = fields.Boolean(string='Active')

class account_move(models.Model):
    _inherit = 'account.move'

    payment_ref = fields.Char(string='Description')