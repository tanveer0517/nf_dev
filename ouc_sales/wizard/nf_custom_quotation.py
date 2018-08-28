from openerp import api, models, fields, _, SUPERUSER_ID
from openerp.exceptions import except_orm, Warning
import time
from odoo import exceptions
from odoo.exceptions import ValidationError
from datetime import datetime
import requests
import json

class nf_custom_quotation(models.Model):
    _name = 'nf.custom.quotation'
    _description = 'Custom Quotation'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.depends('quote_line.price_total')
    def _amount_all(self):
        for quote in self:
            amount_untaxed = amount_tax = 0.0
            for line in quote.quote_line:
                if quote.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.quotation_id.currency_id, line.quantity, product=line.product_id, partner=order.partner_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
                amount_untaxed += line.price_subtotal
            quote.update({
                'amount_untaxed': quote.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': quote.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    name = fields.Char(string='Name')
    opportunity_id = fields.Many2one('crm.lead','Opportunity ID')
    quote_line = fields.One2many('nf.custom.quotation.line','quotation_id','Quotation Line')
    contract_template = fields.Many2one('sale.subscription.template','Quotation Template',track_visibility='onchange')
    partner_id = fields.Many2one('res.partner','Customer')
    team_id = fields.Many2one('crm.team','Team',track_visibility='onchange')
    company_name = fields.Char('Company Name')
    sales_person_id = fields.Many2one('res.users','Salesperson')
    date_order = fields.Datetime('Order Date')
    amount_untaxed = fields.Float(compute='_amount_all' ,string='Untaxed Amount' ,store=True)
    amount_tax = fields.Float(compute='_amount_all' ,string='Taxes' ,store=True)
    amount_total = fields.Float(compute='_amount_all' ,string='Total' ,store=True)
    currency_id = fields.Many2one("res.currency", string="Currency",track_visibility='onchange')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', help="Pricelist for current sales order.")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('nf.custom.quotation'))
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    discount_coupon_code = fields.Char('Discount Coupon code')
    dicsount_coupon_validity = fields.Float('Discount Coupon Validity')
    disc_approval_status = fields.Selection([('Approved with incentive', 'Approved with incentive'), ('Approved without incentive', 'Approved without incentive'),('Discount updation failed! Sales Order already claimed', 'Discount updation failed! Sales Order already claimed')],'Discount Approval Status', track_visibility='onchange')


    @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = self.env['mail.template'].sudo().search([('name', '=', 'Custom Quotation - Send by Email')], limit = 1).id
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'nf.custom.quotation',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "sale.mail_template_data_notification_email_sale_order"
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.onchange('contract_template')
    def onchange_contract_template(self):
        if self.contract_template:
            quote_lines = [(0, 0, {
                'product_id': mand_line.product_id.id,
                'name': mand_line.name,
                'quantity': mand_line.quantity,
                'default_discount': mand_line.c_default_discount,
                'price_unit': self.pricelist_id.get_product_price(mand_line.product_id, 1, self.partner_id,
                                                                  uom_id=mand_line.uom_id.id) if self.pricelist_id else 0,
            }) for mand_line in self.contract_template.subscription_template_line_ids]

            options = [(0, 0, {
                'product_id': opt_line.product_id.id,
                'uom_id': opt_line.uom_id.id,
                'name': opt_line.name,
                'quantity': opt_line.quantity,
                'price_unit': self.pricelist_id.get_product_price(opt_line.product_id, 1, self.partner_id,
                                                                  uom_id=opt_line.uom_id.id) if self.pricelist_id else 0,
            }) for opt_line in self.contract_template.subscription_template_option_ids]
            
            self.quote_line = quote_lines

            for line in self.quote_line:
                line._compute_tax_id()

    @api.constrains('opportunity_id')
    def unique_opportunity_id(self):
        for val in self:
            if val.opportunity_id:
                cn = self.sudo().search_count([('opportunity_id', '=', val.opportunity_id.id)])
                if cn and  cn > 1:
                    raise ValidationError(_('Quotation is already created with this Hot Prospect, Please click on View Button to access the quotation.'))
        return True

class nf_custom_quotation_line(models.Model):
    _name = 'nf.custom.quotation.line'

    @api.depends('discount', 'price_unit')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.quotation_id.currency_id, line.quantity, product=line.product_id, partner=line.quotation_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    name = fields.Char(string='Description')
    quotation_id = fields.Many2one('nf.custom.quotation','Quotation')
    product_id = fields.Many2one('product.product','Product')
    quantity = fields.Float('Quantity')
    discount = fields.Float('Discount')
    default_discount = fields.Float('Default Discount')
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    price_unit = fields.Float('Unit Price')
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal' ,store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Taxes' ,store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total' ,store=True)
    company_id = fields.Many2one(related='quotation_id.company_id', string='Company', store=True, readonly=True)

    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.quotation_id.fiscal_position_id or line.quotation_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(taxes, line.product_id, line.quotation_id.partner_id) if line.quotation_id.partner_id.state_id and line.quotation_id.partner_id.state_id.name != 'Telangana' else taxes
            