from odoo import api, models, fields, _, SUPERUSER_ID
import datetime
from datetime import timedelta

from odoo import exceptions

class ouc_account_asset(models.Model):
    _inherit = 'account.asset.asset'
    
    # FOR LA PARTNER
    @api.model
    def createDeferredEntry(self, data):
        partner_id = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner_id.id:
            raise exceptions.ValidationError(_('No Partner found'))
        invoice = self.env['account.invoice'].search([('number', '=', data["invoiceNumber"])])
        
        if not invoice:
            raise exceptions.ValidationError(_('No invoice found with number %s'.format(data["invoiceNumber"])))
        invoice_id = invoice[0]
        
        package_id = data["packageId"]
        product = self.env['product.product'].search([('c_package_id', '=', package_id)])
        if not product:
            raise exceptions.ValidationError(_('No Product found for this packageID'))
        
        amount = data["amount"]
        product_id = product[0]
        date = datetime.date.today()
        validity = int(product_id.c_validity)
        name = product_id.name
        print ">>>>>", validity
        revenue_type = self.env['account.asset.category'].search(['&',('method_number','=', validity), ('c_for_la', '=', True)])
        if not revenue_type:
            raise exceptions.ValidationError(_("No Deferred revenue type found for product, Please contact account department to create a new type"))
        revenue_type_id = revenue_type[0]
        vals = {
            'name' : name,
            'category_id' : revenue_type_id.id,
            'date' : date,
            'value': amount,
            'partner_id': partner_id.id,
            'invoice_id': invoice_id.id,
            'method_period': revenue_type_id.method_period,
            'method_number': revenue_type_id.method_number,
            'prorata': True
            }
        
        res = self.create(vals)
        if res:
            return "Successfully created Deferred Entry"
        else:
            raise exceptions.ValidationError(_('Some error came, while creating deferred Entry'))

class ouc_account_asset_categ(models.Model):
    _inherit = 'account.asset.category'
    
    c_for_la = fields.Boolean('For LA?')
        