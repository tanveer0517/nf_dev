from odoo import api, models, fields, _, SUPERUSER_ID


class ouc_product_product(models.Model):
    _inherit="product.product"

    c_default_discount = fields.Float('Default Discount (%)', related='product_tmpl_id.c_default_discount')
    c_max_discount = fields.Float('Maximum Discount (%)', related='product_tmpl_id.c_default_discount')
    partner_id = fields.Many2one("res.partner", string="Partner", related='product_tmpl_id.partner_id')
    c_package_id = fields.Char(string='Package ID', related='product_tmpl_id.c_package_id')
    c_validity = fields.Float('Validity', related='product_tmpl_id.c_validity')
    c_package_extension = fields.Boolean(string='Package Extension',related='product_tmpl_id.c_package_extension')
    c_activation_req = fields.Integer("Number of Activation required", default=1, related='product_tmpl_id.c_activation_req')
    is_corporate_website = fields.Boolean('Is Corporate Website?', related='product_tmpl_id.is_corporate_website')