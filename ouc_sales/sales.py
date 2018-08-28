from odoo import api, models, fields, _, SUPERUSER_ID
import string
from odoo import exceptions
from odoo.exceptions import ValidationError
import requests
from dateutil.relativedelta import relativedelta
import datetime
import json
import odoo.addons.decimal_precision as dp
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import base64
import smtplib

class ouc_sale_order(models.Model):
    _inherit = 'sale.order'
    
    _order = "create_date desc"

    def _compute_subscription(self):
        for order in self:
            order.subscription_id = self.env['sale.subscription'].sudo().search([('partner_id', '=', order.partner_id.id)], limit=1)

    state = fields.Selection([
    ('draft', 'Quotation Created'),
    ('sent', 'Quotation Sent'),
    ('accept', 'Quotation Accepted'),
    ('sale', 'Sales Order'),
    ('done', 'S.O. Logged'),
    ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    project_id = fields.Many2one('account.analytic.account', 'Analytic Account', compute='auto_fill_division_value',store=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="The analytic account related to a sales order.", copy=False)
    
    template_id = fields.Many2one(
        'sale.quote.template', 'Quotation Template',
        default=False, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    
    c_company_name = fields.Char('Company Name')
    c_ex_website = fields.Char('Business Website')
    c_quotation_type = fields.Selection([('new','New'),('renewalupsell','Renewal/Upsell')], string='Quotation Type',default='new')
    #c_gstn_num = fields.Char('GSTN', related='partner_id.c_gstn_num')
    x_gstin = fields.Char(string='GSTIN')
    c_comp_taxable = fields.Selection([('Yes','Yes'),('No','No')],string='Composition Taxable')
    c_gstin_reg = fields.Selection([('Yes','Yes'),('No','No')],string='GSTIN Registered')
    c_gstin_link = fields.Char('GSTIN Validation Link',default='https://services.gst.gov.in/services/searchtp')
    is_gstin_verified = fields.Boolean('Is GSTIN Verified')
    
    # OVC / Claim FPTAG
    c_tds_percent = fields.Selection([("2","2 percent(%)"),("10","10 percent(10%)")],string='TDS percentage')
    c_default_fptag = fields.Char('Deafult FPTAG')
    c_online_voucher_fptag = fields.Char('FPTAG for online Voucher', related='c_default_fptag')
    c_coupon_code_store = fields.Char('OV storing value')
    c_tan_number = fields.Char(string='TAN Number')
    c_coupon_code = fields.Char('Online Voucher', related='c_coupon_code_store')
    c_tds_amount = fields.Monetary('Deducted TDS Amount',compute='calculate_tds')
    c_total_payable_amount = fields.Monetary('Total Payable', compute='get_tds_ammount')

    # Other info
    c_cost_center = fields.Many2one('account.analytic.account', string='Cost Centre', related='c_sp_dep')
    c_sp_dep = fields.Many2one('account.analytic.account', string='Salesperson')
    c_sp_branch = fields.Many2one('hr.branch', string='Branch', help='Sales Person Branch')
    c_invoice_addr_id = fields.Many2one('res.partner', string='Invoice Address')
    c_shipping_addr_id = fields.Many2one('res.partner', string='Deliver Address')
    c_customer_ref = fields.Char('Customer Reference')
    c_portal_payment_options = fields.Html('Portal Payment Options')
    c_currency = fields.Many2one('res.currency', 'Currency' )
    c_is_pkg_extension_req = fields.Boolean('Package Extension required?')
    c_auto_create_fp = fields.Boolean(string="Auto create FPs")
    c_incoterm_id = fields.Many2one('ouc.stock.incoterms')
    c_picking_policy = fields.Selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
        string='Picking Policy', default='direct')
    c_order_policy = fields.Selection([('manual', 'On Demand'), ('picking', 'On Delivery Order'), ('prepaid', 'Before Delivery')],
        string='Create Invoice Policy', default='picking')

    # lead
    c_lead_source_id = fields.Many2one(string='Lead Source', related='opportunity_id.c_lead_source_id')
    c_lead_creator_id = fields.Many2one(string='Lead Creator', related='opportunity_id.c_lead_creator_id',store=True)
    c_sales_support_id = fields.Many2one('hr.employee', string='Sales Support')
    c_partner_ref_id = fields.Many2one(string='Partner reference', related='opportunity_id.c_partner_ref_id')
    c_mangers_hierarchy = fields.Char('Managers',store=True, related='opportunity_id.c_managers_hierarchy')
    c_tc_manager_hierarchy = fields.Char(string='Tele Caller Manager Hierarchy',store=True, related='opportunity_id.c_tc_manager_hierarchy')
    c_product_specialist = fields.Char('Product Specialist Email')
    c_company_id = fields.Many2one('res.company', 'Company')
    c_invoice_exists = fields.Boolean('Invoiced')
    
    # Payment Details
    c_add_payment_details = fields.One2many('ouc.additional.payment.details','sale_order_id',string='Received Payment Details')
   
    # LA case
    is_la_case = fields.Boolean('Is a LA case?', related='partner_id.c_is_partner')
    
    # escalation from contract
    c_escalation_status = fields.Boolean('Is Escalated to Sales Team?')
    c_escalation_reason = fields.Char('Escalation Reason')
    c_escalation_remarks = fields.Text('Remarks for Escalation')    
    c_quotation_is_new = fields.Boolean('If it is not created from any lead', default=False)
    
    #for button utils purpose
    c_online_vocher = fields.Boolean(string='Online voucher',default=False)
    c_online_vocher1 = fields.Boolean(string='Online voucher', default=False)

    c_auto_create_fptag = fields.Boolean(string='Auto Create FPTAG')

    contract_template = fields.Many2one('sale.subscription.template', related='template_id.contract_template')
    claim_id = fields.Char('Claim ID')
    is_claim = fields.Boolean('Claimed ?')
    
    # state
    c_state = fields.Selection(
        [("draft", "Draft Quotation"), ("sent", "Quotation Sent"), ("cancel", "Cancelled"),
         ("waiting_date", "Waiting Schedule"), ("progress", "Sales Order"), ("manual", "Sale to Invoice"),
         ("shipping_except", "Shipping Exception"), ("invoice_except", "Invoice Exception"), ("done", "Done")],
        string='State')
    c_telecaller = fields.Many2one('res.users',string='Tele caller')
    welcome_call_status = fields.Char(string='Welcome Call Status')
    mib_status = fields.Selection([('Yes','MIB done'),('Hold','MIB on hold'),('Not Done Yet','MIB not done yet'), ('MIB Not Required','MIB Not Required'), ('MIB Rejected','MIB Rejected'), ('S.O. Not Claimed','S.O. Not Claimed')], string='MIB Status', track_visibility='onchange', default='Not Done Yet')
    sub_inv_id = fields.Many2one('account.invoice',string="Invoice")
    #mib_hold_issue = fields.Selection([('Name Mismatch','Name Mismatch'),('Payment Issue','Payment Issue'),('Cheque bounced: Funds Insufficient','Cheque bounced: Funds Insufficient'),('Cheque bounced: Payment stopped by customer','Cheque bounced: Payment stopped by customer'),('Cheque bounced: cheque details mistakes','Cheque bounced: cheque details mistakes'),('Fake sale: Deposit slip not attached & Amount not received','Fake sale: Deposit slip not attached & Amount not received'),('Fake sale: Deposit slip not stamped & Amount not received','Fake sale: Deposit slip not stamped & Amount not received'),('Partial payment without second payment details','Partial payment without second payment details'),('Duplicate invoice created','Duplicate invoice created'),('No Issue','No Issue'),('Cheque Bounce','Cheque Bounce'),('Revise Payment received','Revise Payment received')],'MIB Hold Reason', track_visibility='onchange')
    mib_hold_issue = fields.Selection(
        [('Name Mismatch', 'Name Mismatch'), ('Payment Amount Differential', 'Payment Amount Differential'),
         ('Cheque Bounced: Funds Insufficient', 'Cheque Bounced: Funds Insufficient'),
         ('Cheque Bounced: Payment stopped by customer', 'Cheque Bounced: Payment stopped by customer'),
         ('Cheque Bounced: cheque details mistakes', 'Cheque Bounced: cheque details mistakes'), (
         'Payment Untraceable: Deposit slip not attached & Amount not received',
         'Payment Untraceable: Deposit slip not attached & Amount not received'), (
         'Payment Untraceable: Deposit slip not stamped & Amount not received',
         'Payment Untraceable: Deposit slip not stamped & Amount not received'),
         ('Partial payment without second payment details', 'Partial payment without second payment details'),
         ('Duplicate invoice created', 'Duplicate invoice created'), ('No Issue', 'No Issue'),
         ('Cheque Bounce', 'Cheque Bounce'),
         ('Cheque Bounced - No Recovery@SalesAudit', 'Cheque Bounced - No Recovery@SalesAudit'),
         ('Revise Payment Received', 'Revised Payment Received'),
         ('MIB Test Cases', 'MIB Test Cases'),
         ('S.O. Without Attachment', 'S.O. Without Attachment')], 'MIB Hold Reason', track_visibility='onchange')
    vc_status = fields.Char('VC Status',default='Not done yet')
    inv_status = fields.Char('Activation and Invoice Status',default="Activation pending & Invoice Pending")
    disc_approval_status = fields.Selection([('Approved with incentive', 'Approved with incentive'), ('Approved without incentive', 'Approved without incentive'),('Discount updation failed! Sales Order already confirmed', 'Discount updation failed! Sales Order already confirmed')],'Discount Approval Status', track_visibility='onchange')
    upgrade_fptag = fields.Many2one('ouc.fptag',string='Upgrade FPTAG')
    mlc_onboarding_form = fields.Many2one('nf.mlc.onboarding','MLC Onboarding Form')
    onboarding_done = fields.Boolean('MLC Onboarding Done')
    presale = fields.Boolean('Presale')
    presale_rqst_sent = fields.Boolean('Presale Request')
    presale_status = fields.Boolean('Presale Status')
    c_discount_coupon_code = fields.Char('Discount Coupon code')
    c_dicsount_coupon_validity = fields.Float('Discount Coupon Validity')
    mib_action_date = fields.Date('MIB Action Date')
    sales_assist_id = fields.Many2one('hr.employee', 'Sales Assistant')
    sales_assist_branch_id = fields.Many2one('hr.branch', 'Sales Assistant Branch')
    fptag_city = fields.Char('Fptag City')
    fptag_branch_id = fields.Many2one('hr.branch', 'FPtag Branch')
    is_corporate_website = fields.Boolean('Is Corporate Website?')
    is_kitsune = fields.Boolean('Is Kitsune?')

    @api.multi
    def rqst_for_price_update(self):
        template = self.env['mail.template'].sudo().search([('name', '=', 'Request for presale approval')], limit=1)
        if template:
            template.send_mail(self.id)
        self.presale_rqst_sent = True
        return True

    @api.model
    def update_managers_email(self):
        sale_ids=self.sudo().search([])
        for rec in sale_ids:
            managers_email=''
            if rec.user_id:
                emp_obj=self.env['hr.employee']
                emp_ids=emp_obj.sudo().search([('user_id','=',rec.user_id.id)])
                man_email=''
                coach_email=''
                if emp_ids:
                    emp_ids=emp_ids[0]
                    if emp_ids.parent_id:
                        man_email=emp_ids.parent_id.work_email
                    if emp_ids.coach_id:
                        coach_email=emp_ids.coach_id.work_email
                managers_email=man_email
                if man_email and coach_email:
                    while man_email!=coach_email:
                        managers_email=managers_email+','+coach_email
                        emp_ids=emp_ids.coach_id
                        if emp_ids.coach_id:
                            coach_email=emp_ids.coach_id.work_email
                        else:
                            break
            self.env.cr.execute("update sale_order set c_mangers_hierarchy=%s where id = %s",(managers_email,rec.id,))
        return True

    @api.multi
    def create_mlc_onboarding(self):
        for rec in self:
            if rec.state != 'done':
                raise exceptions.ValidationError(_('You can not onboard this because the sale is not logged yet.'))
            else:
                rec_id = self.env['wiz.mlc.onboarding'].create({'so_id':rec.id,'sales_person_id':rec.user_id.id,'partner_id':rec.partner_id.id,'company_name':rec.c_company_name,'partner_email':rec.partner_id and rec.partner_id.email or False,'partner_contact':rec.partner_id and rec.partner_id.mobile or False,'contract_id':rec.subscription_id and rec.subscription_id.id or False})
                #open register note wizard 
                return {
                    'name':_("MLC Onboarding Form"),
                    'view_mode': 'form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_model': 'wiz.mlc.onboarding',
                    'res_id': rec_id.id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True,
                    'domain': '[]'
                    }

    @api.onchange('c_lead_source_id','c_lead_creator_id', 'c_company_name')
    def update_value_from_opportunity(self):
        active_model = self.env.context.get('active_model')
        if active_model:
            self.c_quotation_is_new = False

    @api.onchange('partner_id')
    def is_customer_already_subscribed(self):
        if not self.partner_id:
            return
        
        record = self.env['sale.subscription'].sudo().search([('partner_id', '=', self.partner_id.id)])
        if record:
            self.partner_id = 0
            return {
                'warning': {
                    'message': 'It\'s a case of up-sell, You can only create a quotation from subscription' 
                }
            }
        
        if self.partner_id.parent_id:
            print "Parent Name", self.partner_id.parent_id.name
            self.c_company_name = self.partner_id.parent_id.name
        else:
            print "Company Name", self.partner_id.name
            self.c_company_name = self.partner_id.name
    
    @api.onchange('partner_id', 'user_id')
    def auto_fill_division_value(self):
        if not self.user_id:
            return True
        
        record = self.env['hr.employee'].sudo().search([('user_id', '=', self.user_id.id)], limit = 1)
        if not record:
            return True

        cc = record.cost_centr
        self.c_sp_branch = record.branch_id
        self.c_sp_dep = cc
        self.c_cost_center = cc
        self.project_id = cc
        self.related_project_id = cc

    # Mark opportunity won
    @api.model        
    def create(self, vals):
        if self.opportunity_id:
            self.opportunity_id.action_set_won()
            self.opportunity_id.sudo().write({'c_quotation_created': True})
        # gstin validation
        gstn = vals.get('x_gstin', False)
        gstn_regist = vals.get('c_gstin_reg', 'Yes')
        if gstn and gstn_regist == 'Yes':
            vals['x_gstin'] = gstn.upper()
            if len(gstn) == 15:
                for val in enumerate(gstn):
                    if val[0] in (0, 1, 7, 8, 9, 10, 12):
                        try:
                            numeric_val = int(val[1])
                        except:
                            raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))
                    elif val[0] in (2, 3, 4, 5, 6, 11, 13):
                        if val[1] not in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
                            try:
                                if val[1].isspace():
                                    raise exceptions.ValidationError(
                                        _('Invalid GSTN No.!, Please provide correct GSTN No.'))

                            except:
                                raise exceptions.ValidationError(
                                    _('Invalid GSTN No.!, Please provide correct GSTN No.'))
                        else:
                            raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))

            else:
                raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))
        res = super(ouc_sale_order, self).create(vals)
        res.auto_fill_division_value()
        return res

    #gstin validation
    def write(self, vals):
        gstn = vals.get('x_gstin', False)
        gstn_regist = vals.get('c_gstin_reg', 'Yes')
        if gstn and gstn_regist == 'Yes':
            vals['x_gstin'] = gstn.upper()
            if len(gstn) == 15:
                for val in enumerate(gstn):
                    if val[0] in (0, 1, 7, 8, 9, 10, 12):
                        try:
                            numeric_val = int(val[1])
                        except:
                            raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))
                    elif val[0] in (2, 3, 4, 5, 6, 11, 13):
                        if val[1] not in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
                            try:
                                if val[1].isspace():
                                    raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))

                            except:
                                raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))
                        else:
                            raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))

            else:
                raise exceptions.ValidationError(_('Invalid GSTN No.!, Please provide correct GSTN No.'))

        res = super(ouc_sale_order, self).write(vals)
        return res

    #adding the package value at order_lines in sales order
    @api.onchange('contract_template')
    def onchange_contract_template(self):
        param = self.env['ir.config_parameter']
        line_status = 'new'
        if self.c_quotation_type == 'new':
            line_status = 'new'
            
        if self.c_quotation_type == 'renewalupsell':
            line_status = 'renewalupsell'
        if self.template_id and ('Upgrade' in self.template_id.name):
            res = {}
            if not self.upgrade_fptag:
                res['warning'] = {
                        'title': "Warning",
                        'message': "Please enter the FPTAG to upgrade!",
                    }
                res['value'] = {'template_id': False}
                return res

            if 'Manufacturing' in self.template_id.name:
                upgradePackageId = '59ce2de23a80351b64d9a689'
            elif 'Hotel' in self.template_id.name:
                upgradePackageId = '59ce2cba4873941df491b532'
            elif 'Education' in self.template_id.name:
                upgradePackageId = '5aaf971930fd11054897cdb3'
            elif 'Doctor' in self.template_id.name:
                upgradePackageId = '59f70c3dcb6ab3415c370309'
            elif 'Restaurant' in self.template_id.name:
                upgradePackageId = '5afb053b3c7371c64c86d5ad'
            elif 'Clinics' in self.template_id.name:
                upgradePackageId = '5a380e6607d61e9454f6c350' 
            else:
                raise exceptions.ValidationError(_('No Package Id Defined for this vertical'))
            fptag = self.upgrade_fptag.name
            getFpDetailsApiUrl = param.sudo().search([('key', '=', 'getFpDetailsApiUrl')])
            getFpDetailsApiClientId = param.sudo().search([('key', '=', 'getFpDetailsApiClientId')])

            url = "https://api.withfloats.com/Discover/v2/floatingPoint/nf-web/" + fptag + "?clientId=AC16E0892F2F45388F439BDE9F6F3FB5C31F0FAA628D40CD9814A79D8841397E"
            response = requests.get(url)
            if int(response.status_code) == 200:
                fpdetails = json.loads(response.text)
                fpId = fpdetails['_id']
            else:
                fpId = ""
                return False

            getUpgradePriceURL = "https://api.withfloats.com/Support/v1/CalculatePackageUpgradePrice?clientId=A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E&upgradePackageId=" + str(upgradePackageId) + "&fpId=" + str(fpId)
            upgradepriceresponse = requests.get(getUpgradePriceURL, headers={"Content-Type": "application/json", "Accept": "application/json"})
            if upgradepriceresponse.status_code == 200:
                upgrade_details = json.loads(upgradepriceresponse.text)
                expected_price = upgrade_details['Result']['Price']
            else:
                return False

            createPackageURL = "https://api.withfloats.com/Support/v1/Upgradepackage?clientId=A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E&upgradePackageId=" + str(upgradePackageId) + "&fpId=" + str(fpId)
            createPackageResponse = requests.get(createPackageURL, headers={"Content-Type": "application/json", "Accept": "application/json"})
            if createPackageResponse.status_code == 200:
                upgrade_package_details = json.loads(createPackageResponse.text)
                upgrade_package_id = upgrade_package_details['Result']['_id']
                validityInMnths = upgrade_package_details['Result']['ValidityInMths']
            else:
                return False
            vals = {
                'name': self.template_id.name + ' - ' + self.upgrade_fptag.name,
                'product_type': 'consu',
                'c_package_id': str(upgrade_package_id),
                'c_activation_req': 1,
                'c_validity': validityInMnths,
                'list_price': expected_price,
                'sale_ok': 't',
                'product_uom':1,
                'recurring_invoice':'t'
            }
            new_product_id = self.env['product.product'].sudo().create(vals)
            new_template_id = new_product_id.product_tmpl_id
            new_template_id.sudo().write({'c_validity':validityInMnths, 'c_package_id': upgrade_package_id})


        if self.template_id.contract_template and ('Upgrade' not in  self.template_id.name):
            subscription_lines = [(0, 0, {
                'product_id': mand_line.product_id.id,
                'c_subscription_status': True,
                'c_status': line_status,
                'uom_id': mand_line.uom_id.id,
                'name': mand_line.name,
                'c_fptag_not_required': self.contract_template.c_auto_create_fptag,
                'product_uom_qty': mand_line.quantity,
                'c_max_discount': mand_line.c_max_discount,
                'discount': mand_line.c_default_discount,
                'c_default_discount': mand_line.c_default_discount,
                'c_default_quantity':mand_line.c_default_quantity,
                'c_maximum_quantity':mand_line.c_maximum_quantity,
                'product_uom': mand_line.uom_id.id,
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
            # print "options \n",options
            
            self.order_line = subscription_lines
            # print "self.order_line \n",self.order_line
            self.c_auto_create_fptag = self.contract_template.c_auto_create_fptag
            self.presale = self.contract_template.presale
            self.presale_rqst_sent = False
            self.presale_status = False
            for line in self.order_line:
                line._compute_tax_id()
            
            self.options = options
            
            if self.contract_template:
                self.note = self.contract_template.description



        elif self.template_id and ('Upgrade' in self.template_id.name):
            print "upgrade"
            subscription_lines = [(0, 0, {
                'product_id': new_product_id,
                'c_subscription_status': True,
                'c_status': line_status,
                'uom_id': 1,
                'name': self.template_id.name,
                'c_fptag_not_required': 'f',
                'product_uom_qty': 1,
                'c_max_discount': 0.00,
                'discount': 0.00,
                'c_default_discount': 0.00,
                'c_default_quantity':1,
                'c_maximum_quantity':1,
                'product_uom': 1,
                'price_unit': expected_price,
                'c_fptags_id': self.upgrade_fptag.id,
            })]
            
            options = [(0, 0, {
                'product_id': opt_line.product_id.id,
                'uom_id': opt_line.uom_id.id,
                'name': opt_line.name,
                'quantity': opt_line.quantity,
                'price_unit': self.pricelist_id.get_product_price(opt_line.product_id, 1, self.partner_id,
                                                                  uom_id=opt_line.uom_id.id) if self.pricelist_id else 0,
            }) for opt_line in self.contract_template.subscription_template_option_ids]
            
            self.order_line = subscription_lines
            self.c_auto_create_fptag = self.contract_template.c_auto_create_fptag
            for line in self.order_line:
                line._compute_tax_id()
            
            self.options = options
            
            if self.contract_template:
                self.note = self.contract_template.description
    
    @api.onchange('x_gstin')
    def update_customer(self):
        if not self.x_gstin:
            return
        if not self.partner_id:
            return{
                'warning': {
                    'title': 'GSTN Warning',
                    'message': 'Please select a partner to update GSTN number'
                }
            }
        if not self.partner_id.x_gstin or self.partner_id.x_gstin != self.x_gstin:
            self.partner_id.sudo().write({
                'x_gstin' : self.x_gstin
                })
    
    # API calling[2]
    @api.onchange('order_line')
    def set_fp_value_to_first(self):
        order_line = self.get_default_order_line()
        if order_line:
            self.c_default_fptag = order_line.c_fptags_id.name
    
    def get_default_order_line(self):
        for each_order_line in self.order_line:
            return each_order_line
    
    @api.onchange('c_tds_percent')
    def calculate_tds(self):
        if self.c_tds_percent:
            self.c_tds_amount= (int(self.c_tds_percent)*self.amount_untaxed)/100

    @api.onchange('c_tds_amount')
    def get_tds_ammount(self):
        if self.c_tds_amount > 0:
            self.c_total_payable_amount = self.amount_total - self.c_tds_amount
        if self.amount_total== 0.00 :
            self.c_total_payable_amount = self.amount_total

    @api.multi
    def claim_fptag(self):
        
        param = self.env['ir.config_parameter']
        claimFpApiUrl = param.sudo().search([('key', '=', 'claimFpApiUrl')])
        # calling api for claiming fptag
        #url = "http://api2.nowfloatsdev.com/Support/v1/claimFP/A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"
        url = claimFpApiUrl.value
        data = '"{}"'.format(self.c_default_fptag)
        
        response = requests.post(url, data = data, headers={"Content-Type": "application/json"})
        print ">>>>>>>>", response.text
        if response.text != '"OK"':
            raise exceptions.ValidationError(_('Some error occured in claiming FPTAG, please contact ERP Team'))
            
        self.c_online_vocher = True
        self.c_online_vocher1 = True
        if self.c_state == 'sent':
            return True

    @api.multi
    def generate_online_vocher(self):

        sales_persorn = self.get_hr_employee(self.user_id.id)
        
        items = ''
        valid_until = datetime.date.today()
        order_line = self.get_default_order_line()
        if order_line:
            items = {
                "PackageID" : str(order_line.c_product_template_id.c_package_id),
                "Unitprice" : str(order_line.price_unit),
                "Quantity" : str(order_line.product_uom_qty),
                "Discount" :  str(order_line.discount),
                "productSubtotalAmount" : str(order_line.price_subtotal)
            }

            #method for seprating days
            p_months = order_line.c_pkg_validity
            
            # converting float validity into month and remaining in days
            days = int((p_months - int(p_months))*30)
            package_expiry_months = relativedelta(days=days, months=int(p_months))

            valid_until = valid_until + package_expiry_months
        
        valid_until = datetime.date.strftime(valid_until, "%d/%m/%y")

        email = ""
        if not sales_persorn.work_email:
            email = "erp@erp.com"
        tax = []
        for tax_id in order_line.tax_id:
            tax.append({"Key": str(tax_id.name), "Value": tax_id.amount})

        fpdetails = {
            "FpId":str(self.c_default_fptag),
            "ERPId":str(self.name),
            "CreatedBy":str(email),
            "Invoice":{ "TanNumber": str(self.c_tan_number),
                        "TdsAmount": str(self.c_tds_amount),
                        "TotalPayableAmount": str(self.c_total_payable_amount),
                        "CurrencyCode": "INR",
                        "TotalAmount": str(self.amount_total),
                        "NetAmount": str(self.amount_untaxed),
                        "Taxes": tax,
                        "Items": items
                    },
            "ValidUntil":str(valid_until),
            "Type": 0,
            "ToBeActivatedOn": ""
        }

        param = self.env['ir.config_parameter']
        generatePaymentTokenApiUrl = param.sudo().search([('key', '=', 'generatePaymentTokenApiUrl')])

       # url = "http://api2.nowfloatsdev.com/Internal/v1/GeneratePaymentToken?clientId=A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"
        url = generatePaymentTokenApiUrl.value
        json_fpdetails = json.dumps(fpdetails,sort_keys=True,indent=4, separators=(',', ': '))
        data = str(json_fpdetails)
        response = requests.post(url, data=data, headers={"Content-Type": "application/json"})
        if int(response.status_code) == 200:
            self.c_coupon_code_store = response.text

    def get_hr_employee(self, user_id):
        record = self.env['hr.employee'].sudo().search([('user_id', '=', user_id)])
        return record
    
    def _prepare_contract_data(self, payment_token_id=False):
        if self.template_id and self.template_id.contract_template:
            contract_tmp = self.template_id.contract_template
        else:
            contract_tmp = self.contract_template
        values = {
            'name': contract_tmp.name,
            'state': 'open',
            'template_id': contract_tmp.id,
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'date_start': fields.Date.today(),
            'description': self.note,
            'payment_token_id': payment_token_id,
            'pricelist_id': self.pricelist_id.id,
            'recurring_rule_type': contract_tmp.recurring_rule_type,
            'recurring_interval': contract_tmp.recurring_interval,
            'company_id': self.company_id.id,
        }
        print "contract_tmp.recurring_rule_type", contract_tmp.recurring_rule_type
        print "contract_tmp.recurring_interval", contract_tmp.recurring_interval
        
        if self.project_id:
            values["analytic_account_id"] = self.project_id.id
        
        # compute the next date
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
        recurring_next_date = today + invoicing_period
        values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        if 'template_asset_category_id' in contract_tmp._fields:
            values['asset_category_id'] = contract_tmp.with_context(force_company=self.company_id.id).template_asset_category_id.id
        return values


    def so_confirmation_email(self):
        cr = self.env.cr
        for obj in self:
            msg = MIMEMultipart()
            sp_name = ''
            sp_email = ''
            sp_mobile = ''
            sp_branch = ''
            mode_of_payment = ''
            amount = ''
            sp_reporting_head = ''
            sp_manager = ''
            str_sql = "SELECT " \
                      "emp.name_related," \
                      "emp.work_email," \
                      "emp.mobile_phone," \
                      "branch.name AS branch," \
                      "(SELECT name_related FROM hr_employee WHERE id = emp.coach_id) AS sp_reporting_head," \
                      "(SELECT name_related FROM hr_employee WHERE id = emp.parent_id) AS sp_manager " \
                      "FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN hr_branch branch ON emp.branch_id = branch.id " \
                      "WHERE res.user_id = {}" \
                .format(obj.user_id.id)

            cr.execute(str_sql)
            emp = cr.fetchall()
            if emp:
                sp_name = emp[0][0]
                sp_email = emp[0][1]
                sp_mobile = emp[0][2]
                sp_branch = emp[0][3]
                sp_reporting_head = emp[0][4]
                sp_manager = emp[0][5]

            mail_subject = "Sales Order Confirmed : {} : {}"\
                .format(obj.name,sp_branch)

            heading = "Sales Order {} Confirmed"\
                .format(obj.name)
            i = 0
            cheque_pic_url = ''
            receipt_pic_url = ''
            for f in obj.c_add_payment_details:

                if f.payment_method and i == 0:
                    mode_of_payment = f.payment_method
                elif f.payment_method and i > 0:
                    mode_of_payment = mode_of_payment + ' + ' + f.payment_method

                if f.amount and i == 0:
                    amount = str(f.amount)
                elif f.amount and i > 0:
                    amount = amount + ' + ' + str(f.amount)

                i = i + 1

                if f.cheque_pic:
                    cheque_attachment = base64.b64decode(f.cheque_pic)
                    part = MIMEApplication(
                        cheque_attachment,
                        Name='cheque'
                    )
                    part['Content-Disposition'] = 'attachment; filename="{}"'\
                        .format(f.cheque_pic_name and f.cheque_pic_name or 'cheque')
                    msg.attach(part)
                if f.receipt_pic:
                    receipt_attachment = base64.b64decode(f.receipt_pic)
                    part = MIMEApplication(
                        receipt_attachment,
                        Name='receipt'
                    )
                    part['Content-Disposition'] = 'attachment; filename="{}"'\
                        .format(f.receipt_pic_name and f.receipt_pic_name or 'receipt')
                    msg.attach(part)

                if not f.cheque_pic and f.cheque_pic_name:
                    cheque_pic_url = f.cheque_pic_name

                if not f.receipt_pic and f.receipt_pic_name:
                    receipt_pic_url = f.receipt_pic_name

            html1 = """<tr style="width:100%">
                                 <td style="width:30%"><b>Cheque Image</b></td>
                                 <td style="width:70%">: <span>""" + str(cheque_pic_url or '') + """</span></td>
                              </tr>"""

            html2 = """<tr style="width:100%">
                                 <td style="width:30%"><b>Deposit Slip</b></td>
                                 <td style="width:70%">: <span>""" + str(receipt_pic_url or '') + """</span></td>
                            </tr> """


            html = """<!DOCTYPE html>
                     <html>

                       <body>
                         <table style="width:100%">
                              <tr>
                                 <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></left></td>
                              </tr>
                         </table>
                              <br/>
                         <table style="width:100%">
                              <tr style="width:100%">
                                 <td style="width:30%"><b>SO No.</b></td>
                                <td style="width:70%">: <span>""" + str(obj.name or '') + """</span></td>
                              </tr>
                              <tr style="width:100%">
                                 <td style="width:30%"><b>SO Date</b></td>
                                <td style="width:70%">: <span>""" + str(obj.confirmation_date or '') + """</span></td>
                              </tr>
                              <tr style="width:100%">
                                 <td style="width:30%"><b>Customer</b></td>
                                <td style="width:70%">: <span>""" + str(obj.partner_id.name or '') + """</span></td>
                              </tr>
                          <tr style="width:100%">
                                 <td style="width:30%"><b>Customer City</b></td>
                                <td style="width:70%">: <span>""" + str(obj.partner_id.c_city_id and obj.partner_id.c_city_id.name or '') + """</span></td>
                              </tr>
                          <tr style="width:100%">
                                 <td style="width:30%"><b>Sales Person</b></td>
                                <td style="width:70%">: <span>""" + str(sp_name or '') + """</span></td>
                              </tr>

                          <tr style="width:100%">
                                 <td style="width:30%"><b>SP Email ID</b></td>
                                <td style="width:70%">: <span>""" + str(sp_email or '') + """</span></td>
                              </tr>

                          <tr style="width:100%">
                                 <td style="width:30%"><b>SP Mobile</b></td>
                                <td style="width:70%">: <span>""" + str(sp_mobile or '') + """</span></td>
                              </tr>

                              <tr style="width:100%">
                                 <td style="width:30%"><b>SP Branch</b></td>
                                <td style="width:70%">: <span>""" + str(sp_branch or '') + """</span></td>
                              </tr>
                          <tr style="width:100%">
                                 <td style="width:30%"><b>SP Reporting Head</b></td>
                                <td style="width:70%">: <span>""" + str(sp_reporting_head or '') + """</span></td>
                              </tr>
                          <tr style="width:100%">
                                 <td style="width:30%"><b>SP Manager</b></td>
                                <td style="width:70%">: <span>""" + str(sp_manager or '') + """</span></td>
                              </tr>
                              <tr style="width:100%">
                                 <td style="width:30%"><b>Sales Team</b></td>
                                 <td style="width:70%">: <span>""" + str(obj.team_id.name or '') + """</span></td>
                              </tr>

                          <tr style="width:100%">
                                 <td style="width:30%"><b>Mode of Payment</b></td>
                                 <td style="width:70%">: <span>""" + str(mode_of_payment or '') + """</span></td>
                              </tr>

                          <tr style="width:100%">
                                 <td style="width:30%"><b>Amount</b></td>
                                 <td style="width:70%">: <span>""" + str(amount or '') + """</span></td>
                              </tr>

                          <tr style="width:100%">
                                 <td style="width:30%"><b>Total Amount</b></td>
                                 <td style="width:70%">: <span>""" + str(obj.amount_total or '') + """</span></td>
                              </tr>"""
                          
                          

            html3 = """       <tr style="width:100%">
                                 <td style="width:30%"></td>
                                 <td style="width:70%"></td>
                              </tr>
                        </table>
                       <p>----------------------------------------------------------------------------------------------</p>
                    </body>

                                <body>
                                 <p>You can access document by clicking Sales Order button</p>
                                   <p> <a href="http://erp.nowfloats.com/web#id={}&view_type=form&model=sale.order&action=471&menu_id=324" target="_parent"><button style="background-color:#00bfff"><font color="#ffffff">Sales Order</font></button></a></p>
                                </body>
                <html>"""\
                .format(obj.id)

            if cheque_pic_url and receipt_pic_url:
                html = html + html1 + html2 + html3

            elif cheque_pic_url:
                html = html + html1 + html3

            elif receipt_pic_url:
                html = html + html2 + html3

            else:
                html = html + html3

            emailto = ['salesaudit@nowfloats.com', 'neha.shrikhande@nowfloats.com']
            emailfrom = "hello@nowfloats.com"
            msg['From'] = emailfrom
            msg['To'] = ", ".join(emailto)
            # msg['CC'] = ", ".join(emailto)
            msg['Subject'] = mail_subject

            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE smtp_user = 'hello@nowfloats.com'")
            mail_server = cr.fetchone()
            smtp_user = mail_server[0]
            smtp_pass = mail_server[1]
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            server.sendmail(emailfrom, emailto, text)
            server.quit()
        return True


    def create_contract(self):
        """ Create a contract based on the order's quote template's contract template """
        self.ensure_one()
        if self.require_payment:
            tx = self.env['payment.transaction'].search([('reference', '=', self.name)])
            payment_token = tx.payment_token_id
        if (self.template_id and self.template_id.contract_template or self.contract_template) and not self.subscription_id \
                and any(self.order_line.mapped('product_id').mapped('recurring_invoice')):
            values = self._prepare_contract_data(payment_token_id=payment_token.id if self.require_payment else False)
            subscription = self.env['sale.subscription'].sudo().create(values)
            subscription.name = self.partner_id.name + ' - ' + subscription.code

            # Comment subscription line creation at the time of subscription creation
            #invoice_line_ids = []
            #for line in self.order_line:
             #   if line.product_id.recurring_invoice:
              #      invoice_line_ids.append((0, 0, {
               #         'product_id': line.product_id.id,
                #        'analytic_account_id': subscription.id,
                 #       'name': line.name,
                  #      'sold_quantity': line.product_uom_qty,
                   #     'discount': line.discount,
                    #    'uom_id': line.product_uom.id,
                     #   'price_unit': line.price_unit,
                    #}))
            #if invoice_line_ids:
             #   sub_values = {'recurring_invoice_line_ids': invoice_line_ids}
              #  subscription.write(sub_values)

            self.write({
                'project_id': subscription.analytic_account_id.id,
                'subscription_management': 'create',
            })
            return subscription
        return False
    
    
    def action_accepted(self):
        if self.state in ('done','sale','cancel'):
            return
        self.state = 'accept'

    def action_accept_and_confirm(self):
        self.env.cr.execute("update sale_order set state='accept' where id='%s'",(self.id,))
        return self.action_confirm()
    
    #over riding the sales confirm button
    def action_confirm(self):
        mail_ids = []
        if self.state in ('sent','draft'):
            self.action_accepted()
            return
        if not self.c_add_payment_details:
            raise exceptions.ValidationError(_('Please provide Payment details received from customer'))
        
        for val in self.c_add_payment_details:
            if val.payment_status == False:
                raise exceptions.ValidationError(_('Please send Payment Confirm Status to customer!'))

        subscription_id = self.sudo().subscription_id
        if subscription_id:
            self.subscription_id.sudo().write({'user_id':self.user_id.id})
            if not subscription_id.c_is_invoiced and subscription_id.c_invoice_status=='yes' and not self.is_kitsune:
                raise exceptions.ValidationError(_('There are sale order in Subscription, pending for generating invoice.'))
        project_name = self.project_id.name
        res = super(ouc_sale_order, self).action_confirm()
        
        self.project_id.sudo().write({'name':project_name,'partner_id': False})
        
        for order in self:
            if order.subscription_id:
                order.auto_fill_division_value()
                c_auto_create_fptag = self.c_auto_create_fptag
                order.subscription_id.sudo().write({
                            'c_sale_order':order.name,
                            'c_is_invoiced' : False,
                            'c_sales_order_id': order.id,
                            'c_company_name': order.c_company_name,
                            'c_ex_website': order.c_ex_website,
                            'c_auto_create_fptag':c_auto_create_fptag,
                            'c_invoice_status': 'yes',
                            'c_team_id':order.team_id.id
                            })
                sub_id = [subsc_id for subsc_id in order.sudo().subscription_id.ids][0]
                for payment_details in self.c_add_payment_details:
                    payment_details.sudo().write({
                             'subscription_id' : sub_id
                         })
                    
        for order in self:
            if order.subscription_id:
                # no need for updates if the contract was just created
                if not self.env.context.get('no_upsell', dict()).get(order.id):
                    # wipe the subscription clean if needed
                    if order.subscription_management == 'renew':
                        order.subscription_id.sudo().write({'description': order.note, 'pricelist_id': order.pricelist_id.id})
                        order.subscription_id.sudo().set_open()
                        order.subscription_id.sudo().increment_period()
                    if not order.subscription_management:
                        order.subscription_management = 'upsell'
                    values = {'recurring_invoice_line_ids': []}
                    for line in order.order_line:
                        if line.product_id.recurring_invoice:
                            values = self.updating_subscription_line(order, line, values)
                            
                    if order.c_auto_create_fptag:
                        values = self.convert_qty_to_lines(values, order.c_quotation_type, order.team_id.id)
                        if order.order_line[0].product_id.is_corporate_website:
                            values['is_corporate_website'] = True
                    values['recurring_next_date'] = datetime.date.today()
                    order.subscription_id.sudo().write(values)
                order.action_done()
            try:
                order.so_confirmation_email()
            except:
                pass

        template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats Sale Order')], limit=1)
        if template:
            mail_id = template.send_mail(self.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})

        template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats Welcome Call')], limit=1)
        if template:
            mail_id = template.send_mail(self.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})

        return res
    
    def updating_subscription_line(self, order, line, values):
        subscription_id = order.sudo().subscription_id
                            
        quotation_type = 'new' if order.c_quotation_type == 'new' else 'renewalupsell'

        values['recurring_invoice_line_ids'].append((0, 0, {
            'product_id': line.product_id.id,
            'analytic_account_id': subscription_id.id,
            'name': line.name,
            'sold_quantity': line.product_uom_qty,
            'uom_id': line.product_uom.id,
            'c_fptags_id': line.c_fptags_id.id,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'c_validity': line.c_pkg_validity,
            'c_sale_order_id': order.id,
            'c_sales_person_id': order.user_id.id,
            'c_price_tax': line.price_tax,
            'c_price_total': line.price_total,
            'c_tax_ids': [(6, 0, line.tax_id.ids)],
            'c_sale_date': datetime.date.today(),
            'c_cost_center': order.c_cost_center.id,
            'c_sp_branch': order.c_sp_branch.id,
            'c_status': quotation_type,
            'c_team_id':order.team_id.id
            }))
        
        return values
    
    
    def convert_qty_to_lines(self, values, order_type, team_id):

        values = self.lines_for_mlc_subscription(values, team_id)
        for ind in range(0, len(values["recurring_invoice_line_ids"])):
            values["recurring_invoice_line_ids"][ind][2]["sold_quantity"] = 1.0
            
        return values
    
    def lines_for_new_subscription(self, values, team_id):
        new_values = values["recurring_invoice_line_ids"]
        all_lines = len(new_values)
        
        for ind_l in range(0, all_lines):
            line = new_values[ind_l]
            recuring_line_id = int(line[1])
            recurring_line = self.env['sale.subscription.line'].sudo().browse(recuring_line_id)
            if not recurring_line:
                continue
            
            recuring_line_list = line[2]

            qty = recurring_line[0].sold_quantity
            
            recuring_line_list["c_price_tax"] = recuring_line_list["c_price_tax"]/qty
            recuring_line_list["c_price_total"] = recuring_line_list["c_price_total"]/qty
            recurring_line[0].sudo()._compute_price_subtotal()
            
            for each_qty in range(1, int(qty)):
                print each_qty
                values['recurring_invoice_line_ids'].append((0, 0, {
                    'product_id': recurring_line.product_id.id,
                    'c_sales_person_id':  recuring_line_list["c_sales_person_id"],
                    'c_sp_branch':  recuring_line_list["c_sp_branch"],
                    'c_sale_order_id':  recuring_line_list["c_sale_order_id"],
                    'c_tax_ids':  recuring_line_list["c_tax_ids"],
                    'c_status':  recuring_line_list["c_status"],
                    'c_price_total':  recuring_line_list["c_price_total"],
                    'c_validity':  recuring_line_list["c_validity"],
                    'c_price_tax':  recuring_line_list["c_price_tax"],
                    'c_cost_center':  recuring_line_list["c_cost_center"],
                    'sold_quantity':  1.0,
                    'name': recurring_line.name,
                    'analytic_account_id':recurring_line.c_cost_center.id,
                    'price_unit': recurring_line.price_unit,
                    'discount': recurring_line.discount,
                    'c_sale_date':  recuring_line_list["c_sale_date"],
                    'uom_id': recurring_line.uom_id.id,
                    'c_team_id': team_id
                }))
        return values
    
    def lines_for_mlc_subscription(self, values, team_id):
        new_values = values["recurring_invoice_line_ids"]
        all_lines = len(new_values)
        
        for ind_l in range(0, all_lines):
            line = new_values[ind_l]
            print ">>>>>>>",line
            line_type = int(line[0])
            print "LINE TYPE>>>>", line_type
            if line_type == 1:
                continue
            
            recuring_line_list = line[2]

            qty = recuring_line_list["sold_quantity"]
            
            print ">>>>",
            recuring_line_list["c_price_tax"] = recuring_line_list["c_price_tax"]/qty
            recuring_line_list["c_price_total"] = recuring_line_list["c_price_total"]/qty
            
            print ">>>>>Price TAX", recuring_line_list["c_price_tax"]
            print "QTY>>>>>>>>", qty
            for each_qty in range(1, int(qty)):
                print each_qty
                values['recurring_invoice_line_ids'].append((0, 0, {
                    'product_id': recuring_line_list["product_id"],
                    'c_fptags_id':  recuring_line_list["c_fptags_id"],
                    'c_sales_person_id':  recuring_line_list["c_sales_person_id"],
                    'c_sp_branch':  recuring_line_list["c_sp_branch"],
                    'c_sale_order_id':  recuring_line_list["c_sale_order_id"],
                    'c_tax_ids':  recuring_line_list["c_tax_ids"],
                    'c_status':  recuring_line_list["c_status"],
                    'c_price_total':  recuring_line_list["c_price_total"],
                    'c_validity':  recuring_line_list["c_validity"],
                    'c_price_tax':  recuring_line_list["c_price_tax"],
                    'c_cost_center':  recuring_line_list["c_cost_center"],
                    'sold_quantity':  1.0,
                    'name': recuring_line_list["name"],
                    'analytic_account_id':recuring_line_list["c_cost_center"],
                    'price_unit': recuring_line_list["price_unit"],
                    'discount': recuring_line_list["discount"],
                    'c_sale_date':  recuring_line_list["c_sale_date"],
                    'uom_id': recuring_line_list["uom_id"],
                    'c_team_id': team_id
                }))
        return values
        

    def close_escalation(self):
        for order in self:
            if not order.subscription_id:
                continue
            
            print ">>>>>>>>>CLOSING ESCALATION IN SUBSCRIPTION"
            order.subscription_id.sudo().write({
                'c_verification_status': 'Escalation Closed',
                'c_rta_status': 'In Progress',
                'c_verification_call_status': False
            })
            self.c_escalation_status = False

    def open_subscription(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.subscription",
            "views": [[self.env.ref('sale_contract.sale_subscription_view_form').id, "form"]],
            "domain": [],
            'res_id': self.subscription_id and self.subscription_id.id or False,
            "context": {},
            'view_mode':'form',
            'target': 'new',
            "name": "Contract"
               }

    @api.multi
    def create_website_mlc(self):
        for rec in self:
            website_id = ''
            if rec.order_line and rec.order_line[0].c_product_template_id.is_corporate_website:
                param = self.env['ir.config_parameter']
                createWebsite = param.search([('key', '=', 'createWebsiteMLC')])
                createWebsite_url = createWebsite.value
                partner = rec.partner_id
                partner_phone = partner.mobile
                partner_email = partner.email
                partner_name = partner.name
                website_tag = partner_name.replace(' ','')+str(rec.id)
                authorize_createWebsite = param.search([('key', '=', 'authorizeCreateWebsite')])
                payload = {
                            "PhoneNumber" : partner_phone,
                            "Email" : partner_email,
                            "FullName" : partner_name,
                            "ProjectId" : rec.order_line[0].c_product_template_id.c_package_id,
                            "WebsiteTag" : website_tag
                           }
                data = json.dumps(payload)
                headers = {
                    'content-type': "application/json",
                    'Authorization': authorize_createWebsite.value
                }
                response = requests.request("POST", createWebsite_url, data=data, headers=headers)
                if response:
                    website_id = response.text
        print "###################website_id",website_id
        return website_id

    @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.contract_template and self.contract_template.c_auto_create_fptag:
                template_id = self.env['mail.template'].sudo().search([('name', '=', 'MLC Sales Order - Send by Email')], limit=1).id
                if self.order_line and self.order_line[0].c_product_template_id.is_kitsune:
                    self.env.cr.execute("UPDATE sale_order SET is_kitsune = True WHERE id = {}".format(self.id))

                website_id = self.create_website_mlc()
                if website_id:
                    self.env.cr.execute("UPDATE sale_order SET is_corporate_website = True WHERE id = {}".format(self.id))
                    fp_rec = self.env['ouc.fptag'].sudo().create({'name':website_id,'is_corporate_website':True,'customer_id':self.partner_id.id})
                    if fp_rec:
                        self.order_line[0].sudo().write({'c_fptags_id':fp_rec.id})
                    template_id = self.env['mail.template'].sudo().search([('name', '=', 'MLC Corporate Sales Order - Send by Email')], limit = 1).id
            else:
               template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
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

    #Cancel Sales Order and Deactivate Package

    @api.multi
    def action_remove_contract_line(self):
        cr = self.env.cr
        so_id = self.id
        cr.execute(
            "SELECT id FROM sale_subscription_line WHERE c_sale_order_id = {} AND c_invoice_id IS NOT NULL".format(
                so_id))
        contract_line_ids = cr.fetchall()
        if contract_line_ids:
            raise exceptions.ValidationError(_('Tax invoice been raised for S.O.'))

        str_sql1 = "DELETE " \
                   "FROM " \
                   "sale_subscription_line " \
                   "WHERE c_sale_order_id ={} " \
                   "AND c_invoice_id IS NULL AND c_sale_order_id IS NOT NULL" \
            .format(so_id)

        cr.execute(str_sql1)

        str_sql2 = "UPDATE " \
                   "sale_order " \
                   "SET state = 'cancel' " \
                   "WHERE id = {}" \
            .format(so_id)

        cr.execute(str_sql2)

        return True

    @api.multi
    def action_deactivate_package(self):
        param = self.env['ir.config_parameter']
        deactivatePackageApiUrl = param.search([('key', '=', 'deactivatePackageApiUrl')])
        deactivatePackageApiClinetId = param.search([('key', '=', 'deactivatePackageApiClinetId')])

        url = deactivatePackageApiUrl.value
        clienId = deactivatePackageApiClinetId.value

        sale_order = self.name

        for val in self.order_line:
            fptag_obj = val.c_fptags_id

            if not fptag_obj:
                continue

            fptag_obj.get_fp_external_id()

            payload = {"_nfInternalERPId": sale_order,
                       "_nfInternalERPInvoiceId": None,
                       "clientId": clienId,
                       "fpId": fptag_obj.externalSourceId,
                       "paymentTransactionId": None
                       }
            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache",
            }

            data = json.dumps(payload)

            response = requests.request("POST", url, data=data, headers=headers)

            response = json.loads(response.text) #response.get('Result', '')

        try:
            self.action_cancel_payment_by_sale_order()
        except:
            pass

        return True

    @api.multi
    def action_cancel_payment_by_sale_order(self):
        param = self.env['ir.config_parameter']
        CancelPaymentBySaleOrderUrl = param.search([('key', '=', 'CancelPaymentBySaleOrderUrl')])
        deactivatePackageApiClinetId = param.search([('key', '=', 'deactivatePackageApiClinetId')])

        url = CancelPaymentBySaleOrderUrl.value
        clienId = deactivatePackageApiClinetId.value

        sale_order = self.name

        cancel_reason = self.note

        querystring = {"clientId": clienId,
                       "rejectionReason": cancel_reason,
                       "saleOrderNumber": sale_order
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("POST", url, headers=headers, params=querystring)

        print(response.text)

        return True

    @api.multi
    def cancel_sale_order(self):
         self.note = self.note if self.note else '' + 'Cancel S.O. & Deactivated Package'
         self.action_remove_contract_line()
         self.action_deactivate_package()
         return True

        
class ouc_sales_order_line(models.Model):
    _inherit = 'sale.order.line'

    c_status = fields.Selection([('new', 'New'), ('renewalupsell', 'Renewal/Upsell')], string='Status', default='new')
    c_fptags_id = fields.Many2one('ouc.fptag', string='Primary FPTAG')
    c_product_template_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id')
    c_package_id = fields.Many2one('ouc.package', string='Packages')
    c_pkg_validity = fields.Float(string='Validity (in months)', related='c_product_template_id.c_validity')
    c_client_id = fields.Char('Client Id')
    
    c_subscription_status = fields.Boolean(string='Subscription')
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'),store=True, default=0.0)
    
    c_default_discount = fields.Float('Default Discount (%)')
    c_max_discount = fields.Float('Maximum Discount (%)')
    c_default_quantity = fields.Integer(string='Default Quantity')
    c_maximum_quantity = fields.Integer(string='Maximum Quantity')
    
    c_fptag_not_required = fields.Boolean(string='Auto Create FPTAG', default=False)
            
    is_la_case = fields.Boolean(string='Is a LA case?', related='order_id.is_la_case')
    c_discount_value = fields.Float(string='Discount Value')
    c_emi_option = fields.Selection([('No EMI', 'No EMI'), ('3 Months EMI', '3 Months EMI'), ('6 Months EMI', '6 Months EMI')], string='Emi Option')
    c_tax_amount = fields.Float(string='Tax Amount')
    c_price_sub_with_tax = fields.Float(string='Price with Tax')
    fptag_city = fields.Char('FPTag City')

    @api.onchange('discount')
    def check_discount_validity(self):
        if self.discount > self.c_max_discount:
            self.discount = self.c_max_discount
            return {
            
                'warning': {
                    'title': 'Discount Warning',
                    'message': 'Discount cannot be more than {}'.format(self.c_max_discount)}
            }


    @api.onchange('product_uom_qty')
    def quantity_check(self):

        if self.product_uom_qty > self.c_maximum_quantity:
            self.product_uom_qty = self.c_maximum_quantity
            return {
                'warning': {
                    'title': 'Quantity Warning',
                    'message': 'Quantity cannot be more than {}'.format(self.product_uom_qty)}

            }
        elif self.product_uom_qty < self.c_default_quantity:
            self.product_uom_qty = self.c_default_quantity
            return {
                'warning': {
                    'title': 'Quantity Warning',
                    'message': 'Quantity cannot be less than {}'.format(self.product_uom_qty)}

            }
    

class ouc_sale_quote_line(models.Model):
    _inherit = 'sale.quote.line'
    
    c_product_template_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id')


class sale_quote_template(models.Model):
    _inherit = 'sale.quote.template'

    contract_template = fields.Many2one('sale.subscription.template', 'Contract Template',
        help="Specify a contract template in order to automatically generate a subscription when products of type subscription are sold.")
    c_additinal_email = fields.Text(string='Additional Email')
    c_type = fields.Selection([('new', 'Only For New'), ('renewalupsell', 'Only for Renewal/Upsell'),('all','For All')], string='Template Type', default='all')
    active = fields.Boolean(default=True, help="Set active to false to hide template.")
    single_store = fields.Boolean('Single Store')

    @api.onchange('contract_template')
    def onchange_contract_template(self):
        quote_lines = [(0, 0, {
            'product_id': mand_line.product_id.id,
            'uom_id': mand_line.uom_id.id,
            'name': mand_line.name,
            'c_status':mand_line.c_status,
            'discount': mand_line.c_default_discount,
            'product_uom_qty': mand_line.quantity,
            'product_uom_id': mand_line.uom_id.id,
        }) for mand_line in self.contract_template.subscription_template_line_ids]
        options = [(0, 0, {
            'product_id': opt_line.product_id.id,
            'uom_id': opt_line.uom_id.id,
            'name': opt_line.name,
            'quantity': opt_line.quantity,
        }) for opt_line in self.contract_template.subscription_template_option_ids]
        self.quote_line = quote_lines
        self.options = options
        self.note = self.contract_template.description

class nf_mlc_onboarding(models.Model):
    _name = 'nf.mlc.onboarding'
    _description = 'MLC Onboarding'

    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner','Customer')
    partner_email = fields.Char('Partner Email')
    partner_contact = fields.Char('Partner Contact')
    company_name = fields.Char('Business Name')
    sales_person_id = fields.Many2one('res.users','Sales Person')
    so_id = fields.Many2one('sale.order','Sale Order')
    contract_id = fields.Many2one('sale.subscription','Contract')
    onboarding_line = fields.One2many('nf.mlc.onboarding.line','onboarding_id','Onboarding Line')
    existing_domain = fields.Selection([('Yes','Yes'),('No','No')],'Existing Domain*')
    domain_url = fields.Char('Domain URL')
    cpanel_user = fields.Char('CPanel Username')
    cpanel_pwd = fields.Char('CPanel Password')


class nf_mlc_onboarding_line(models.Model):
    _name = 'nf.mlc.onboarding.line'
    _description = 'MLC Onboarding Line'

    onboarding_id = fields.Many2one('nf.mlc.onboarding','Onboarding ID')
    country_id = fields.Many2one('res.country','Country')
    city_id = fields.Many2one('ouc.city','City1')
    city = fields.Char('City')
    address = fields.Char('Address')
    contact_no = fields.Char('Contact No')
    email_id = fields.Char('Email ID')
    url = fields.Char('URL')
    location_type = fields.Selection([('Physical','Physical'),('Virtual','Virtual')],'Location Type')