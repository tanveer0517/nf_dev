from odoo import api, models, fields, _, SUPERUSER_ID
import string
from odoo import exceptions
from odoo.exceptions import ValidationError
import requests
from dateutil.relativedelta import relativedelta
import datetime
import json
import requests
import os.path

class ouc_package_extension(models.Model):
    _name = 'package.extension'
    _rec_name = 'c_reference'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    c_reference = fields.Char(string='Reference')
    c_creation_date = fields.Date(string = 'Creation Date',default=fields.Date.context_today)
    c_customer_name = fields.Many2one('res.partner',string='Customer Name',track_visibility='onchange')
    c_division = fields.Many2one('hr.department',string='Division')
    c_quantity = fields.Float(string='Quantity', default="1")
    c_fptags = fields.Many2one('ouc.fptag',string='FPTAG',track_visibility='onchange')
    c_product_tem_id = fields.Many2one('product.product',string='Product Id')
    c_package_extension = fields.Boolean(string='Package Extension',related='c_product_tem_id.c_package_extension')
    c_product = fields.Many2one('product.template',string='Product')
    c_type_of_sale = fields.Selection([('new','New'),('renewal','Renewal')],string='Type of Activation')
    c_approved_by = fields.Many2one('res.users',string='Approved By',default=lambda self: self.env.uid)
    c_invoice_no = fields.Many2one('account.invoice',string='Invoice Number')
    c_comments = fields.Text(string='Comments',track_visibility='onchange')
    c_approval_att_name = fields.Char('Approval Attachment Name')
    c_approval_attachement = fields.Binary(string='Approval Attachment')
    c_pkg_activation_status = fields.Boolean(string='Package Activation Status')
    c_pkg_activation_date = fields.Date(string='Package Activation Date',track_visibility='onchange')
    c_pkg_approved_by = fields.Many2one('res.users',string='Package Approved By',track_visibility='onchange')
    activation_type = fields.Selection([('fos','FOS'),('mlc','MLC')],string='Activation Type', default='fos')

    def activate_all_packages(self):
        print "Activate packages"
        
        param = self.env['ir.config_parameter']
        markFloatingPointAsPaidUrl = param.search([('key', '=', 'markFloatingPointAsPaidUrl')])
        clientIdForActivatingPackage = param.search([('key', '=', 'clientIdForGeneratingFps')])

        if self.activation_type == 'fos':
            clientIdForActivatingPackage = param.search([('key', '=', 'clientIdForActivatingPackage')])

        packageSaleTransactionType = 1
        if self.c_type_of_sale == 'new':
            packageSaleTransactionType = 0
            
        externalSourceId = self.c_fptags.get_fp_external_id()
        print ">>>>>>>>>>>>>>>>>>>>>",self.c_fptags.externalSourceId
        
        activation_data = {
                "BaseAmount": 0,
                "ClientId": clientIdForActivatingPackage.value,
                "ExpectedAmount": 0,
                "TaxAmount": 0,
                "ExternalSourceId": '',
                "FpId": self.c_fptags.externalSourceId,
                "FpTag": str(self.c_fptags.name),
                "IsPaid": True,
                "currencyCode": 'INR',
                "packages": [{
                               "packageId": str(self.c_product.c_package_id),
                               "quantity": int(self.c_quantity)
                            }],
                "type": int(packageSaleTransactionType),
                "customerSalesOrderRequest":
                    {
                        "_nfInternalERPId": str(self.c_reference),
                        "_nfInternalERPSaleDate": str(self.c_pkg_activation_date),
                        "customerEmailId": self.c_customer_name.email,
                        "discountPercentageValue": 0,
                        "invoiceStatus": 0,
                        "paymentMode": 0,
                        "paymentTransactionStatus": 0,
                        "purchasedUnits": 1,
                        "sendEmail": False
                    }
        }
        print ">>>>>>>>>>activation_data>>>>>>>>>",activation_data
        data = json.dumps(activation_data)

        print ">>>>>>>>>>> ", data
        response = requests.post(markFloatingPointAsPaidUrl.value, data=data,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        print ">>>>>>>>>>>>>>response", response, response.status_code, response.text
        if int(response.status_code) != 200:
            print 'Package Activation unsuccessful'
            return False
        if not response.text:
            print 'Package Activation unsuccessful'
            return False
        print ">>>>>>>>>Activation Successful"
        activ_id = json.loads(response.text)
        print ">>>>>>>>>>>>>activ_id>>>>>>>>>>>>",activ_id

        return True




    @api.model
    def create(self, create_values):
        seq = self.env['ir.sequence'].next_by_code('package_sequence')
        create_values["c_reference"] = seq
        res = super(ouc_package_extension, self).create(create_values)
        return res

    @api.onchange('c_division')
    def auto_filling_division(self):
        record = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        if record:
            for div in self.env['hr.employee'].browse(record.id):
                self.c_division = div.sub_dep

    def extend_package(self):
        self.c_pkg_activation_date = datetime.date.today()
        self.c_pkg_activation_status = True
        self.c_pkg_approved_by = self.env.uid
        self.activate_all_packages()

    @api.onchange('c_approval_attachement')
    def checking_app_attachement(self):
        if self.c_approval_attachement:
            name, ext = os.path.splitext(self.c_approval_att_name)
            if ext not in ['.png', '.jpg', '.jpeg']:
                raise exceptions.ValidationError(_('Extension should be jpg,jpeg or png'))





