from odoo import api, models, fields, _, SUPERUSER_ID

class ouc_product_template(models.Model):
    _inherit="product.template"


    c_default_discount = fields.Float('Default Discount (%)')
    c_max_discount = fields.Float('Maximum Discount (%)')

    partner_id = fields.Many2one("res.partner", string="Partner")
    c_package_id = fields.Char(string='Package ID')
    c_validity = fields.Float('Validity')
    c_package_extension = fields.Boolean(string='Package Extension')
    c_activation_req = fields.Integer("Number of Activation required", default=1)
    is_corporate_website = fields.Boolean('Is Corporate Website?')
    is_kitsune = fields.Boolean('Is Kitsune?')