from odoo import fields, models, api,_
import re
from odoo import exceptions
import requests
import json
import os.path

class ouc_fptag(models.Model):
    _name='ouc.fptag'
    _rec_name = 'name'
    
    name = fields.Char(string='FPTAG')
    state = fields.Selection([('invalid','Invalid'),('valid','Valid'),('active','Active')],default='invalid',string='State')
    customer_id = fields.Many2one('res.partner', string='Customer')
    
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity')
    externalSourceId = fields.Char('ExternalSourceId')
    claimed = fields.Boolean('Claim FPTAG')
    fp_creation_date = fields.Datetime('FP Creation Date')
    fp_city = fields.Char('FP City')
    fp_address = fields.Char('FP Address')
    is_corporate_website = fields.Boolean('Is Corporate Website?')
    
    @api.onchange('name')
    def validate_fptag(self):
        if self.name:
            opportunity_partner_id = 0
            context = self._context
            
            if context.has_key('partner_id'):
                partner_id = context.get('partner_id')
                if partner_id:
                    opportunity_partner_id = partner_id
                    
                else:
                    self.name = ''
                    return {
                        'warning': {
                            'message': 'Please select a customer first'
                        }
                    }
            
            self.name = str(self.name).upper()
            fp = self.sudo().search([('name', '=', self.name)], limit=1)
            if fp:
                self.name = ''
                
                # FOR OPPORTUNITY checks if renewal of existing FPTAG
                if opportunity_partner_id != 0 and fp.customer_id.id == opportunity_partner_id:
                    return {
                        'warning': {
                            'message': 'This FPTAG is already existing with selected customer \'{}\', if it is a renewal case proceed to Quotation without adding FPTAG'.format(fp.customer_id.name)
                        }
                    }
                
                if fp.customer_id and fp.lead_id:
                    return {
                        'warning': {
                            'message': 'FPTAG \'{}\' already existing in system and linked to opportunity \'{}\' with customer \'{}\' '.format(fp.name, fp.lead_id.name, fp.customer_id.name)
                        }
                    }
                return {
                        'warning': {
                            'message': 'FPTAG \'{}\' already existing in system and linked to lead \'{}\' '.format(fp.name, fp.lead_id.name)
                        }
                    }
            if not self.validate_fptag_from_api():
                self.name = ''
                return {
                        'warning': {
                            'message': 'FPTAG {} is not valid'.format(self.name)
                        }
                    }            
            
    def validate_fptag_from_api(self):
        param = self.env['ir.config_parameter']
        checkFpExistsApiUrl = param.sudo().search([('key', '=', 'checkFpExistsApiUrl')])
        checkFpExistsApiClientId = param.sudo().search([('key', '=', 'checkFpExistsApiClientId')])

        url = "{}/{}".format(checkFpExistsApiUrl.value, self.name)
        
        #url = "http://api.nowfloatsdev.com/Discover/v1/floatingPoint/Exists/{}"
        #data = '"A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"'

        querystring = {"clientId": checkFpExistsApiClientId.value
                       }
        
        response = requests.post(url, params=querystring, headers={"Content-Type": "application/json"})
        if response.status_code != 200:
            return False
        if response.text != 'true':
            return False
        return True
    
    @api.multi
    def get_fp_external_id(self):
        param = self.env['ir.config_parameter']
        getFpDetailsApiUrl = param.sudo().search([('key', '=', 'getFpDetailsApiUrl')])
        getFpDetailsApiClientId = param.sudo().search([('key', '=', 'getFpDetailsApiClientId')])
        
        self.ensure_one()
        #url = "http://api.nowfloatsdev.com/Discover/v1/floatingPoint/nf-web/{}?clientId=A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"
        url = "{}/{}?clientId={}".format(getFpDetailsApiUrl.value,self.name,getFpDetailsApiClientId.value)
        response = requests.get(url)
        print ">>>>>>>", response.status_code
        if int(response.status_code) == 200:
            fpdetails = json.loads(response.text)
            print ">>>>>>>>>", fpdetails['_id']
            self.externalSourceId = fpdetails['_id']
            return True
        
        return False
    
    @api.model
    def create(self, values):
        if values["name"]:
            values["name"] = str(values["name"]).upper()
        res = super(ouc_fptag, self).create(values)
        if res.customer_id:
            return res
        if not res.lead_id:
            return res
        if res.lead_id.partner_id:
            res.sudo().write({"customer_id":res.lead_id.partner_id.id})
        return res
class ouc_lead_source(models.Model):
    _name = 'ouc.lead.source'
    _rec_name='lead_source'

    lead_source = fields.Char(String='Lead Source')

    
class ouc_employee_manager_heirarchy(models.Model):
    _name = 'ouc.employee.manager.heirarchy'
    
    employee_id = fields.Many2one('hr.employee', string = 'Employee')
    managers_ids = fields.Many2many('hr.employee', 'employee_heirarchy_rel', 'heirarchy_id', 'employee_id', string = 'Manager IDs')
    
    @api.onchange('employee_id')
    def autofill_heirarchy_managers(self):
        if self.employee_id:
            print ">>>>>>>", self.employee_id.id
            print ">>>>>>>>>MANY2MANY", self.managers_ids
            managers_id = []
            self.get_manager(self.employee_id, managers_id)
            self.managers_ids = self.env['hr.employee'].sudo().search([('id', 'in', managers_id)])
            
    
    def get_manager(self, emp_hr_id, managers_id):
        if emp_hr_id.parent_id:
            print ">>>>>>>>MANAGER>>>>", emp_hr_id.parent_id
            managers_id.append(emp_hr_id.parent_id.id)
            self.get_manager(emp_hr_id.parent_id, managers_id)



# City as a seperate entity/class just like state and country.
class ouc_city(models.Model):
    _name = 'ouc.city'

    name = fields.Char(string='City Name', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    active = fields.Boolean(string='Active', default=True)

class ouc_additional_payment_details(models.Model):
    _name = 'ouc.additional.payment.details'

    name = fields.Char(string='Name')
    entry_date = fields.Date('Entry date', default=fields.Date.context_today)
    downpay_type = fields.Selection(
        [('not_emi', 'Not EMI'), ('down_payment_to_nowfloats', 'Down Payment To NowFloats'),
         ('down_payment_to_zest', 'Down Payment To Zest'),('Revise Payment','Revised Payment')], string='Downpay Type', default='not_emi')
    payment_method = fields.Selection(
        [('cash', 'Cash'), ('cheque', 'Cheque'), ('online_transfer', 'Online Transfer')], string='Payment Method')
    bifurcation = fields.Selection([('NEFT', 'NEFT'), ('IMPS', 'IMPS'), ('RTGS', 'RTGS'),('Boost','Boost'),('Manager','Manager'),('Partner Dashboard','Partner Dashboard')], string='Bifurcation')
    cheque_pic_name = fields.Char('Cheque Picture Name')
    cheque_pic = fields.Binary('Cheque Picture')
    cheque_number = fields.Char('Cheque Number')
    cheque_date = fields.Date('Cheque Date')
    bank_id = fields.Many2one('res.bank', string='Bank Name')
    transfer_ref_number = fields.Char('Transfer Reference Number')
    receipt_number = fields.Char('Receipt Number')
    receipt_pic_name = fields.Char('Receipt Picture Name')
    receipt_pic = fields.Binary('Receipt Picture')
    mismatch_decl_name = fields.Char('Mismatch Dec Name')
    mismatch_declaration = fields.Binary('Mismatch Declaration')
    amount = fields.Float('Amount')
    payment_configaration_status = fields.Boolean('Payment Configaration Status')
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')
    invoice_id = fields.Many2one('account.invoice', string='Invoice')
    payment_status = fields.Boolean(string='Payment confirmation sent?')
    subscription_id = fields.Many2one('sale.subscription','Subscription')
    cms_slip_num = fields.Char('CMS Slip No.')


    @api.multi
    def checking_payment_details(self):
        print self.downpay_type
        self.payment_status = True
        sale_order = self.sale_order_id
        if sale_order.subscription_id and sale_order.state in ('done','sale'):
            self.subscription_id = sale_order.subscription_id
        template = self.env['mail.template'].sudo().search(
            [('name', '=', 'NowFloats Payment Confirmation Email from payment details')], limit=1)
        if template:
            mail_id = template.send_mail(self.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})
            return True

    @api.onchange('cheque_pic')
    def checking_cheque_pic(self):
        if self.cheque_pic:
            name, ext = os.path.splitext(self.cheque_pic_name)
            if ext not in ['.png', '.jpg', '.jpeg']:
                raise exceptions.ValidationError(_('Extension should be jpg,jpeg or png'))

    @api.onchange('receipt_pic')
    def checking_receipt_pic(self):
        if self.receipt_pic:
            name, ext = os.path.splitext(self.receipt_pic_name)
            if ext not in ['.png', '.jpg', '.jpeg']:
                raise exceptions.ValidationError(_('Extension should be jpg,jpeg or png'))

    @api.onchange('mismatch_declaration')
    def checking_mismatch_declaration(self):
        if self.mismatch_declaration:
            name, ext = os.path.splitext(self.mismatch_decl_name)
            if ext not in ['.png', '.jpg', '.jpeg']:
                raise exceptions.ValidationError(_('Extension should be jpg,jpeg or png'))


class ouc_stock_incoterms(models.Model):
    _name = 'ouc.stock.incoterms'

    active = fields.Boolean('Active',
                                help='By unchecking the active field, you may hide an INCOTERM without deleting it')
    code = fields.Char('Code', help='Code Incoterm')
    name = fields.Char('Name',
                           help='Incoterms are series of sales terms.They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.',
                           size=64)


class ouc_sale_journal_invoice_type(models.Model):
    _name = 'ouc.sale_journal.invoice.type'

    active = fields.Boolean('Active',
                                help='If the actice field is set to False, it will allow you to hide the invoice type witout removing it')
    note = fields.Text('Note')
    invoicing_method = fields.Selection([('simple', 'Non grouped'), ('grouped', 'Grouped')],
                                            string='Invoicing Method')
    name = fields.Char('Invoive Type',  size=64)


class ouc_crm_case_categ(models.Model):
    _name = 'ouc.crm.case.categ'

    name = fields.Char(string='Name')
    object_id = fields.Many2one('ir.model', string='Object Id', invisible='1')
    section_id = fields.Many2one('hr.department', string='Sales Team')

# product specialist configaration

class ouc_product_specialist(models.Model):
    _name = 'ouc.product.specialist'

    city_id = fields.Many2one('ouc.city', string='City')
    specialists_id = fields.One2many('ouc.ps.config.list', 'ps_id', string='Product Specialists')
    emails = fields.Char(string='Product Specialist Emails')


class ouc_ps_config_list(models.Model):
    _name = 'ouc.ps.config.list'
    _rec_name = 'employee_id'

    ps_id = fields.Integer(string='Product Specialist Id')
    employee_id = fields.Many2one('hr.employee', string='Product Specialist List')


class ouc_bankdetails(models.Model):
    _name='ouc.bankdetails'
    bankdetails_id=fields.Many2one('sale.subscription')
    bankaccountnumber=fields.Char(string='Bank Account Number ')
    bank_id = fields.Many2one('res.bank', string='Bank Name')
    ifsccode=fields.Char(string='IFSC')
    accountholder=fields.Char(string='Account Holder Name')
    reason_to_reject = fields.Char(string='Rejection reason')


class ouc_res_company(models.Model):
    _inherit = 'res.company'

    c_tnc_inv = fields.Text(string='Custom Terms & Conditions on Invoice')
    sac_code = fields.Char('SAC',default='9973')

class ouc_res_users(models.Model):
    _inherit = 'res.users'
    _order = "id desc"

class renewal_cohort(models.Model):
    _name = 'renewal.cohort'
    _description = 'Renewal Cohort'
    _rec_name = 'widget_name'

    location_id = fields.Char('Location ID')
    widget_name = fields.Char('Name Of Widget')
    parent_id = fields.Char('Parent ID')
    activattion_date = fields.Datetime('To Be Activated On')
    extrnl_id = fields.Char('ID')
    internal_erp_id = fields.Char('NF Internal ERP ID')
    internal_erp_invoice_id = fields.Char('NF Internal ERP Invoice ID')
    internal_erp_line_id = fields.Char('NF Internal ERP Line ID')
    internal_erp_sale_date = fields.Datetime('NF Internal ERP Sale Date')
    base_amount = fields.Float('Base Amount')
    client_id = fields.Char('Client ID')
    client_product_id = fields.Char('Client Product ID')
    currency_code = fields.Char('Currency Code')
    discount = fields.Float('Discount')
    expiry_date = fields.Datetime('Expiry Date')
    fp_id = fields.Char('FP ID')
    fp_tag = fields.Char('FP Tag')
    invoice_url = fields.Char('Invoice Url')
    active = fields.Boolean('Is Active')
    business_closed = fields.Boolean('Is Business Closed')
    marked_deletion = fields.Boolean('Marked For Deletion')
    multi_year_renewal = fields.Boolean('Multi Year Renewal')
    multi_year_status = fields.Integer('Multi Year Status')
    multi_year_upgrade = fields.Boolean('Multi Year Upgrade')
    pack_type = fields.Integer('Pack Type')
    package_sale_transaction_type = fields.Integer('Package Sale Transaction Type')
    paid_amount = fields.Float('Paid Amount')
    product_line = fields.Integer('Product Line')
    renewal_probability = fields.Float('Renewal Probability')
    renewal_status = fields.Integer('Renewal Status')
    renewal_date = fields.Datetime('Renewed On')
    target_renewal_cohort = fields.Char('Target Renewal Cohort')
    tax_amount = fields.Float('Tax Amount')
    total_months_validity = fields.Integer('Total Months Validity')
    update_flags_new_multi_year = fields.Boolean('Update Flags Is New Multi Year')
    update_flags_new_vertical = fields.Boolean('Update Flags Is New Vertical')
    update_flags_renewal_multi_year = fields.Boolean('Update Flags Is Renewal Multi Year')
    update_flags_renewal_vertical = fields.Boolean('Update Flags Is Renewal Vertical')
    update_flags_upgrade_multi_year = fields.Boolean('Update Flags Is Upgrade Multi Year')
    update_flags_upgrade_vertical = fields.Boolean('Update Flags Is Upgrade Vertical')
    vertical_status = fields.Integer('Vertical Status')
    branch_id = fields.Integer('Branch ID')