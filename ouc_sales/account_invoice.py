from odoo import api, fields, models, _, SUPERUSER_ID
import datetime
from datetime import timedelta

from odoo import exceptions
from openerp.tools import amount_to_text_en
import requests
import json
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class ouc_account_invoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('currency_id', 'amount_untaxed')
    def _compute_amt_in_inr(self):
        company_currency = self.company_id.currency_id
        currency_id = self.currency_id
        if currency_id != company_currency:
            currency = currency_id.with_context(date=self.c_sale_date or fields.Date.context_today(self))
            self.amount_in_inr = currency.compute(self.amount_untaxed, company_currency)
        else:
            self.amount_in_inr = self.amount_untaxed

    c_pkg_act_status = fields.Boolean(string="Package Activation Status")  # custom added field
    c_pkg_act_date = fields.Date("Invoice Activation Date")  # custom added field
    c_inv_validated_date = fields.Date("Invoice Validated Date")  # custom added field
    c_rta_done_date = fields.Date("RTA Done Date")  # custom added field
    c_cancel_date = fields.Date("Invoice Cancel date")  # date of cancellation of invoice
    c_alt_mobile_number = fields.Char("Alternate Mobile Number")  # Customer alternate mobile
    c_ex_website = fields.Char("Existing Website")  # Customer website

    c_sale_date = fields.Date(string="Sale Date")
    c_invoice_date=fields.Date(string="Date Invoice")
    c_activation_date = fields.Date(string="Activation Date")



    c_company_name = fields.Char("Company Name")
    c_cost_center = fields.Many2one("account.analytic.account", string="Cost Centre", related='c_sales_order_id.c_cost_center')
    c_is_pkg_extn_req = fields.Boolean("Package Extension Required")
    c_auto_create_fp = fields.Boolean("Enable Auto create FP")

    # Other info
    c_lead_creator_id = fields.Many2one("res.users", "Lead Creator")
    c_sales_support_id = fields.Many2one("hr.employee", "Sales Support")
    c_partner_ref_id = fields.Many2one("res.partner", "Partner Reference")
    c_package_act_status = fields.Boolean("Package Activation Status")
    c_partner_bank_id = fields.Many2one("res.partner.bank", "Bank Account")
    c_partner_account_period = fields.Char(string="Accounting Period")

    c_add_payment_details = fields.One2many('ouc.additional.payment.details', 'invoice_id',
                                            string='Received Payment Details')

    c_payment_terms_id = fields.Many2one('account.payment.term', string='Payment Terms')
    c_add_info = fields.Text(string='Additional information')
    c_sales_user_id = fields.Many2one('res.users', string='Sales Person')
    c_sales_team_id = fields.Many2one('crm.team', string='Team [C]')
    c_sales_origin = fields.Char(string='Source Document')
    c_manager_hierarchy = fields.Char(string='Managers', store=True, related='c_sales_order_id.c_mangers_hierarchy')
    c_product_specialist = fields.Char(string='Product Specialist Email')
    c_tc_manager_hierarchy = fields.Char('Tele Caller Manager Hierarchy',store=True,related='c_sales_order_id.c_tc_manager_hierarchy')


    # Payment related info
    c_journal_id = fields.Many2one("account.journal", string="Payment Method")
    c_payement_type = fields.Selection([('Full Payment', 'Full Payment'), ('Partial Payment', 'Partial Payment')],
                                       string="Payment Type")
    c_tds_check = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="TDS Deducted or Not?")
    c_tds_percent = fields.Float("TDS Percentage")
    c_tds_amount = fields.Monetary("TDS Amount", default=0)
    c_paid_amount = fields.Float("Paid Amount")
    c_payment_ref = fields.Char(string="Payement Reference Number", size=128)
    c_payment_receive_date = fields.Date("Payment Received Date")
   # c_payment_receive_date_2 = fields.Date("Payment Received Date")

    c_case_lh_mlc = fields.Boolean(string="LH to MLC")
    c_case_mlc_mlc = fields.Boolean(string="MLC to MLC")
    c_case_new_mlc = fields.Boolean(string="New MLC")
    c_case_renew_mlc = fields.Boolean(string="Renew MLC")
    c_username = fields.Char("Username")
    c_primary_fp = fields.Char("Primary FPTAG")

    c_rta_hold_issue = fields.Selection([('Name Mismatch','Name Mismatch'),('Payment Amount Differential','Payment Amount Differential'),('Cheque Bounced: Funds Insufficient','Cheque Bounced: Funds Insufficient'),('Cheque Bounced: Payment stopped by customer','Cheque Bounced: Payment stopped by customer'),('Cheque Bounced: cheque details mistakes','Cheque Bounced: cheque details mistakes'),('Payment Untraceable: Deposit slip not attached & Amount not received','Payment Untraceable: Deposit slip not attached & Amount not received'),('Payment Untraceable: Deposit slip not stamped & Amount not received','Payment Untraceable: Deposit slip not stamped & Amount not received'),('Partial payment without second payment details','Partial payment without second payment details'),('Duplicate invoice created','Duplicate invoice created'),('No Issue','No Issue'),('Cheque Bounce','Cheque Bounce'),('Cheque Bounced - No Recovery@SalesAudit','Cheque Bounced - No Recovery@SalesAudit'),('Revise Payment Received','Revised Payment Received'), ('MIB Test Cases', 'MIB Test Cases'),('S.O. Without Attachment', 'S.O. Without Attachment')],'MIB Hold Reason', default = 'No Issue',track_visibility='onchange')

    c_rta_hold_description = fields.Text(string='Details for Holding RTA')

    c_rta_sent_status = fields.Boolean(string="RTA sent?")
    c_rta_status = fields.Boolean(string='RTA status')
    c_phone_number = fields.Char("Mobile", size=20)
    c_verification_status = fields.Char("RTA & VC Status")
    c_rta_done_date = fields.Date("RTA Done date")
    c_verification_call_status = fields.Boolean(string='Verification Call Status')
    c_reject_reason = fields.Selection(
        [["Customer Refused as wanted assured Google Position", "Customer Refused as wanted assured Google Position"],
         ["Customer Refused as wanted committed leads", "Customer Refused as wanted committed leads"],
         ["Customer refused over Commitment v/s delivered", "Customer refused over Commitment v/s delivered"],
         ["Customer refused over SEO understanding", "Customer refused over SEO understanding"], ["Others", "Others"]],
        string='Reason to Reject')
    c_other_reject = fields.Char(string='Other Reason for Reject/Refund')
    c_verified_by_id = fields.Many2one('hr.employee', string='Verification Done by')
    c_verification_remarks = fields.Text(string='Verification Remarks')
    c_rta_case0 = fields.Boolean(string='Accepted with T&C', related='c_vc_cl_all')
    c_rta_case1 = fields.Boolean(string='Acceptance Case')
    c_rta_case2 = fields.Boolean('On Hold')
    c_rta_case3 = fields.Boolean('Reject & Refund')
    c_call_links = fields.Text(string='Call Record Links')
    c_vc_cl1 = fields.Boolean(string='Informed about NO Guarantee on Google Position?')
    c_vc_cl2 = fields.Boolean(string='Informed about Organic SEO?')
    c_vc_cl3 = fields.Boolean(string='Checked if any existing Website needs to be Integrated?')
    c_vc_cl4 = fields.Boolean(string='Informed about Self Contained Updates?')
    c_vc_cl5 = fields.Boolean(string='Checked and Confirmedall details related to FP?')
    c_vc_cl_all = fields.Boolean(string='VC CL All')

    c_acc_mngr_email = fields.Char(string='Account Manager Email')
    c_acc_mngr = fields.Char(string='Account Manager')
    c_calendar_link = fields.Text(string='Check the availability of Account Manager')
    c_acc_mngr_call_link = fields.Char(string='Account Manager video call link')

    c_onboard_time = fields.Datetime(string='On Boarding Schedule Time')
    c_onboarding_type = fields.Selection(
        [["Video Call without FOS", "Video Call without FOS"], ["Video Call with FOS", "Video Call with FOS"],
         ["Audio Call without FOS", "Audio Call without FOS"], ["Audio Call with FOS", "Audio Call with FOS"],
         ["No onboarding Required", "No onboarding Required"]], string='On Boarding Call Type')
    c_no_of_fps = fields.Float(string='no of FPTAGs')
    c_verification_status = fields.Char(string='RTA VC status')
    c_call_hold_reason = fields.Selection(
        [["Customer Concerns over Google Position", "Customer Concerns over Google Position"],
         ["Customer Concerns over Visible Location", "Customer Concerns over Visible Location"],
         ["Customer Concerns over SEO and Ranking", "Customer Concerns over SEO and Ranking"],
         ["Customer Concerns over Leads", "Customer Concerns over Leads"],
         ["Customer Concerns over other Commitments made", "Customer Concerns over other Commitments made"],
         ["Sales commitment to do content updation to the customer",
          "Sales commitment to do content updation to the customer"]], string='Reason to Hold')
    c_escalation_remarks = fields.Text(string='Escalation remarks')
    c_dup_state = fields.Char(string='Duplicate State')
    c_rta_hold_description = fields.Text(string='Details for Holding Data')

    c_sales_order_id = fields.Many2one('sale.order', string='Sales order Reference')

    c_duplicate_state = fields.Char(string='Duplicate State')
    state = fields.Selection(
        [["draft", "Draft"], ["proforma", "Pro-forma"], ["proforma2", "Pro-forma"], ["open", "Open"], ["paid", "Paid"],
         ["open2", "Open2"], ["cancel", "Cancelled"], ["hold", "Hold"],["Paid Partial","Paid Partial"], ["Paid Refund","Paid Refund"]])

    # page[4]
    c_customer_payments = fields.Many2many('account.move.line', 'account_move_line_rel', 'account_id', 'account_rel_id',
                                           string='Payments')
    c_gstn = fields.Char(string='GSTN Number',readonly=1)
    c_chc = fields.Many2one('hr.employee',string='CHC')
    c_telecaller = fields.Many2one('res.users',string='Telecaller')
    c_comments = fields.Text(string='Comments')
    c_amount_in_inr = fields.Float(string='Amount in INR')
    c_sales_per_br = fields.Many2one('hr.branch','Sales Person Branch')
    c_static_tc_br = fields.Many2one('hr.branch','Static Person Branch')
    c_tele_employee = fields.Many2one('hr.employee','Tele Employee')
    c_rcm = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string='RCM')
    c_po_not_reason = fields.Char(string='Reason For No Purchase Order')
    c_supp_inv_num = fields.Char(string='Description')
    welcome_call = fields.Char('Welcome Call')
    vc_followup_status = fields.Selection([('0', 'Not Reachable - Switch off / out of coverage'),
                                           ('1', 'Not Reachable - Wrong Number'),
                                           ('2', 'Not Reachable - Ringing'),
                                           ('3', 'Connected & call later'),
                                           ('4', 'Connected & not right party'),
                                           ('5', 'Connected & Accepted with T&C without concern'),
                                           ('6', 'Connected & expressed concern'),
                                           ('7', 'Connected & re-verified & Dispute'),
                                           ('8', 'Connected & expressed concern & Got Satisfied & T&C Accepted'),
                                           ('9', 'Connected & re-verified & Customer Refunded')],
                                          string='VC Follow-up Status', track_visibility='onchange')
    amount_in_inr = fields.Float(compute='_compute_amt_in_inr', string='Amount in INR', store = True)
    refund_api_sts = fields.Char('Refund API Status')
    marketplace_transaction_id = fields.Char('MarketPlace Transaction ID')
    marketplace_server_id = fields.Char('MarketPlace Server ID')
    mps_claim = fields.Boolean('Is Claimed ?')
    cfc_contract_id = fields.Many2one('cfc.contract', 'Assigned CFC')
    partner_username = fields.Char('Partner Username')
    cfc_mlc_contract_id = fields.Many2one('cfc.contract', 'MLC CFC')
    assigned_cfc_name = fields.Char('Assigned CFC Name')

    @api.multi
    def create_training_request(self):

        param = self.env['ir.config_parameter']
        createTrainingRequestForCustomerApiUrl = param.search([('key', '=', 'createTrainingRequestForCustomerApiUrl')])
        UpdateCHCDetailsClientId = param.search([('key', '=', 'getFpDetailsApiClientId')])

        url = createTrainingRequestForCustomerApiUrl.value

        querystring = {"clientId": UpdateCHCDetailsClientId.value}

        self.env.cr.execute("""SELECT fp.name, fp."externalSourceId"
             FROM account_invoice_line ail
             LEFT JOIN ouc_fptag fp ON ail.c_fptags_id = fp.id
             LEFT JOIN account_invoice ai ON ail.invoice_id = ai.id
             WHERE ai.id = {} AND ai.c_sales_order_id = {}
             AND ail.c_fptags_id IS NOT NULL LIMIT 1"""
                            .format(self.id, self.c_sales_order_id.id))

        fptag_details = self.env.cr.fetchone()

        if not fptag_details:
            return False

        fptag = fptag_details[0]
        fp_id = fptag_details[1]

        customer = self.partner_id
        customer_name = customer.name
        customer_address = customer.street if customer.street else '' + ', ' + customer.street2 if customer.street2 else ''
        customer_email = customer.email or ''
        customer_mobile = customer.mobile or ''
        business_name = customer.parent_id and customer.parent_id.name or customer.name
        customer_city = customer.c_city_id and customer.c_city_id.name or ''
        customer_state = customer.state_id and customer.state_id.name or ''
        customer_country = customer.country_id and customer.country_id.name or 'India'
        customer_gstn = customer.x_gstin or ''
        meeting_date = self.c_onboard_time
        call_recording_links = self.c_call_links
        vc_remark = self.c_verification_remarks or ''
        partner_username = self.partner_username or ''

        payload = {'_id': None,
                   'clientId': "A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E",
                   'username': partner_username,
                   "customerDetails": {"name": customer_name,
                                       "address": customer_address,
                                       "email": customer_email,
                                       "phoneNumber": customer_mobile,
                                       "businessName": business_name,
                                       "alternatePhoneNumber": None,
                                       "city": customer_city,
                                       "state": customer_state,
                                       "GSTN": customer_gstn,
                                       "country": customer_country,
                                       "enterpriseUsername": None,
                                       "storeCount": 1,
                                       "FpTags": [fptag],
                                       "FpIds": [fp_id],
                                       "ParentId": None,
                                       "isEnterpriseCustomer": False,
                                       "singleStoreSeedFpTagForEnterprise": None,
                                       "isExistingSingleStoreCustomer": False
                                       },
                   "latestMeetingScheduledDate": "0001-01-01T00:00:00",
                   "transactionChannel": 0,
                   "trainingStatus": 0,
                   "trainingParameters": None,
                   "isTrainingScheduled": False,
                   "dispositionReason": None,
                   "remarks": None,
                   "callRecordingLink": call_recording_links,
                   "_NFInternalRIAMeetingID": None,
                   "_NFInternalERPID": self.c_sales_order_id.name
                   }

        data = json.dumps(payload)

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("POST", url, data=data, headers=headers, params=querystring)

        print"==========create_training_request===========", (response.text)
        return True

    @api.model
    def update_managers_email(self):
        inv_ids=self.sudo().search([])
        for rec in inv_ids:
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
            self.env.cr.execute("update account_invoice set c_manager_hierarchy=%s where id = %s",(managers_email,rec.id,))
        return True

    
    def calculate_tds_amount(self):
        percent = self.c_tds_percent        
        self.c_tds_amount = (percent * self.amount_untaxed)/100

    @api.multi
    def compute_num2_text(self):
        split_value = ''
        p = amount_to_text_en.amount_to_text(self.amount_total, 'en', self.currency_id.symbol)
        symbol = self.currency_id.symbol
        for val in p.split(symbol):
            split_value = split_value + val
        if self.currency_id.name == 'INR':
            split_value = split_value.replace('Cent', 'Paise')
            split_value = split_value.replace('Cents', 'Paisa')
        text = str(self.currency_id.name) + ' ' + split_value + ' Only'
        return text

    # FOR LA PARTNER
    @api.model
    def createProductAndVenderInvoice(self, data):
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))

        product_data = {
            "name": data["productName"],
            "list_price": data["amount"],
            "partner_id": partner.id,
            "c_package_id": data["packageId"],
            "c_validity": data["validity"],
            "type": 'service'
        }
        product_id = self.env['product.template'].create(product_data)
        product_id.create_variant_ids()
        product = self.env['product.product'].search([('product_tmpl_id', '=', product_id.id)])
        prod_id = product[0]

        return self._generate_vender_invoice(partner, prod_id, data["quantity"])

    # FOR LA PARTNER
    @api.model
    def createVenderInvoice(self, data):
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        package_id = data["packageId"]
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))
        product_id = self.env['product.product'].search([('c_package_id', '=', package_id)])
        if not product_id:
            raise exceptions.ValidationError(
                _('No Product found for this partner, please call createProductAndInvoice method'))
        else:
            for val in self.env['product.template'].browse(product_id[0].id):
                price_value = {
                    'list_price': data['amount']
                }
                product_id.write(price_value)

        return self._generate_vender_invoice(partner, product_id[0], data["quantity"])

    def _generate_vender_invoice(self, partner, prod_id, quantity):
        invoice_data = {
            "partner_id": partner.id,
            "type": 'in_invoice',
            "c_company_name": partner.name,
            "date_invoice": datetime.date.today(),
            "c_sale_date": datetime.date.today()
        }
        invoice_id = self.create(invoice_data)

        cost_centr = partner.c_int_lead_ref_id.c_cost_center

        account = prod_id.property_account_income_id
        if not account:
            account = prod_id.categ_id.property_account_income_categ_id
        account_id = invoice_id.fiscal_position_id.map_account(account).id

        invoice_line_data = {
            'product_id': prod_id.id,
            'account_id': account_id,
            'name': prod_id.name,
            'price_unit': prod_id.list_price or 0.0,
            'discount': 0.0,
            'quantity': quantity or 1.0,
            'c_pkg_validity': prod_id.c_validity,
            'c_status': 'new',
            'account_analytic_id': cost_centr.id or 0,
            'invoice_id': invoice_id.id
        }
        invoice_line = self.env['account.invoice.line'].create(invoice_line_data)
        print ">>>>>>>>>>>>>>>>>>>invoice_line>>>>>>>>>>>>>", invoice_line
        invoice_line._set_taxes()
        invoice_id._onchange_invoice_line_ids()
        invoice_id.action_invoice_open()

        return invoice_id.number or ""
    
    @api.model
    def get_la_account(self):
        param = self.env['ir.config_parameter']
        param_obj = param.search([('key', '=', 'la_income_account_code')])
        account_ids = self.env['account.account'].search([('code', '=', param_obj.value)],limit=1)
        print "account_for_la", account_ids
        return account_ids
    
    @api.model
    def get_sale_journal_id(self):
        param = self.env['ir.config_parameter']
        param_obj = param.search([('key', '=', 'sale_journal_code')])
        sj = self.env['account.journal'].search([('code', '=', param_obj.value),('type','=','sale')],limit=1)
        print "Sale Journal", sj
        return sj.id

    @api.model
    def generatePackagesAndInvoice(self, data):
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))

        tdsPercentage = float(data["tdsPercentage"])
        deferred_revenue_category_id = self.env['account.asset.category'].search([('c_for_la','=',True)], limit=1)
        packages = []
        for val in data["packages"]:
            product_data = {
                "name": val["productName"],
                "list_price": val["price"],
                "partner_id": partner.id,
                "c_package_id": val["packageId"],
                "c_validity": val["validity"],
                "deferred_revenue_category_id": deferred_revenue_category_id.id
            }
            print product_data
            product_id = self.env['product.template'].create(product_data)
            product_id.create_variant_ids()
            product = self.env['product.product'].search([('product_tmpl_id', '=', product_id.id)])
            prod_id = product[0]

            packages.append({
                "product_id": prod_id,
                "discount": val["discount"],
                "quantity": val["quantity"]
            })
        
        return self.generate_invoice_and_lines(partner, packages, tdsPercentage)

    # FOR LA PARTNER
    @api.model
    def generateInvoice(self, data):
        packages = []
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))
        
        tdsPercentage = float(data["tdsPercentage"])
        SalesOrderId = data.get('SalesOrderId', False)
        SalesOrder = data.get('SalesOrder', '')
        SubscriptionId = data.get('SubscriptionId', False)

        for val in data['packages']:
            package_id = val["packageId"]
            product_id = self.env['product.product'].search([('c_package_id', '=', package_id)])
            if not product_id:
                raise exceptions.ValidationError(
                    _('No Product found for this partner, please call createProductAndInvoice method'))
            packages.append({
                    "product_id": product_id[0],
                    "discount": val["discount"],
                    "quantity": val["quantity"]
            })
        return self.generate_invoice_and_lines(partner, packages, tdsPercentage, SalesOrderId, SalesOrder, SubscriptionId)

    def generate_invoice_and_lines(self, partner, packages, tdsPercentage, SalesOrderId = False, SalesOrder=False, SubscriptionId=False):
        user_id = self.env.uid
        lead = partner.c_int_lead_ref_id
        if lead:
            user_id = lead.user_id and lead.user_id.id or self.env.uid

        team_id = self.env['crm.team'].search([('name', '=', 'LA')], limit=1)
        team_id = team_id and team_id.id or False

        invoice_data = {
            "partner_id": partner.id,
            "type": 'out_invoice',
            "c_company_name": partner.name,
            "date_invoice": datetime.date.today(),
            "c_sale_date": datetime.date.today(),
            "c_tds_percent" : tdsPercentage,
            "journal_id" : self.get_sale_journal_id(),
            "user_id": user_id,
            "team_id": team_id,
            'c_sales_order_id':SalesOrderId,
            'origin':SalesOrder,
            'c_gstn': partner.x_gstin or ''
        }
        cost_centr = False
        c_sp_branch = False
        c_sp_emp_id = False
        invoice_id = self.create(invoice_data)
        emp_obj = self.env['hr.employee'].search([('user_id','=',user_id)])
        if emp_obj:
            cost_centr = emp_obj.cost_centr and emp_obj.cost_centr.id or False
            c_sp_branch = emp_obj.branch_id and emp_obj.branch_id.id or False
            c_sp_emp_id = emp_obj.id

        for rec in packages:
            account = self.get_la_account()
            if not account:
                account = rec['product_id'].categ_id.property_account_income_categ_id
            account_id = invoice_id.fiscal_position_id.map_account(account).id

            invoice_line_data = {
                'product_id': rec['product_id'].id,
                'account_id': account_id,
                'name': rec['product_id'].name,
                'price_unit': rec['product_id'].list_price or 0.0,
                'discount': rec['discount'] or 0.0,
                'quantity': rec['quantity'] or 1.0,
                'c_pkg_validity': rec['product_id'].c_validity,
                'c_status': 'new',
                'account_analytic_id': cost_centr,
                'c_sp_branch':c_sp_branch,
                'c_sp_emp_id':c_sp_emp_id,
                'invoice_id': invoice_id.id
            }
            invoice_line = self.env['account.invoice.line'].create(invoice_line_data)
            invoice_line._set_taxes()

        invoice_id._onchange_invoice_line_ids()
        invoice_id.calculate_tds_amount()
        invoice_id.action_invoice_open()

        if SalesOrderId and SubscriptionId:
            self.env.cr.execute("UPDATE "
                                "sale_subscription_line "
                                "SET c_invoice_id = {}, c_invoice_date = 'now'::date "
                                "WHERE c_sale_order_id = {} AND analytic_account_id = {}".format(invoice_id.id, SalesOrderId, SubscriptionId))


            # Update MIB Status
            self.env['nf.api'].update_mib_status({"SalesOrderId": SalesOrderId,
                                                  "mibStatus": 2,  # MIB done, Activation done and Invoice created
                                                  "invoiceId": invoice_id.id
                                                 })

        template = self.env['mail.template'].search([('name', '=', 'NowFloats LA Verification Call Mail Success')], limit=1)
        if template:
            mail_id = template.send_mail(invoice_id.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})
        return invoice_id.number or ""

    # FOR LA PARTNER
    @api.model
    def createProductAndInvoice(self, data):
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))
        deferred_revenue_category_id = self.env['account.asset.category'].search([('c_for_la','=',True)], limit=1)
        
        product_data = {
                "name": data["productName"],
                "list_price" : data["price"],
                "partner_id" : partner.id,
                "c_package_id": data["packageId"],
                "c_validity" : data["validity"],
                "deferred_revenue_category_id": deferred_revenue_category_id.id
            }
        product_id = self.env['product.template'].create(product_data)
        product_id.create_variant_ids()
        product = self.env['product.product'].search([('product_tmpl_id', '=', product_id.id)])
        prod_id = product[0]
        
        return self._generate_la_invoice(partner, prod_id, data["discount"], data["quantity"])
    
    # FOR LA PARTNER
    @api.model
    def createInvoice(self, data):
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        package_id = data["packageId"]
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))
        product_id = self.env['product.product'].search([('c_package_id', '=', package_id)])
        if not product_id:
            raise exceptions.ValidationError(_('No Product found for this partner, please call createProductAndInvoice method'))
        return self._generate_la_invoice(partner, product_id[0], data["discount"], data["quantity"])
    
    def _generate_la_invoice(self, partner, prod_id, discount, quantity):
        invoice_data = {
                "partner_id" : partner.id,
                "type": 'out_invoice',
                "c_company_name" : partner.name,
                "date_invoice" : datetime.date.today(),
                "c_sale_date" : datetime.date.today(),
                "journal_id" : self.get_sale_journal_id()
            }
        invoice_id = self.create(invoice_data)

        cost_centr = partner.c_int_lead_ref_id.c_cost_center
        
        account = self.get_la_account()
        if not account:
            account = prod_id.categ_id.property_account_income_categ_id
        account_id = invoice_id.fiscal_position_id.map_account(account).id
        
        invoice_line_data = {
            'product_id': prod_id.id,
            'account_id' : account_id,
            'name': prod_id.name,
            'price_unit': prod_id.list_price or 0.0,
            'discount': discount or 0.0,
            'quantity': quantity or 1.0,
            'c_pkg_validity': prod_id.c_validity,
            'c_status': 'new',
            'account_analytic_id': cost_centr.id or 0,
            'invoice_id' : invoice_id.id
        }
        invoice_line = self.env['account.invoice.line'].create(invoice_line_data)
        invoice_line._set_taxes()
        invoice_id._onchange_invoice_line_ids()
        invoice_id.action_invoice_open()

        return invoice_id.number or ""

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = \
                inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(total,
                                                                                                            date_invoice)[
                    0]
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
                'payment_ref' : inv.c_supp_inv_num
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True
    
class ouc_account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.one
    @api.depends('invoice_id.currency_id', 'price_subtotal')
    def _compute_amt_in_inr(self):
        inv = self.invoice_id
        company_currency = inv.company_id.currency_id
        currency_id = inv.currency_id
        if currency_id != company_currency:
            currency = currency_id.with_context(date=inv.c_sale_date or fields.Date.context_today(self))
            self.amount_in_inr = currency.compute(self.price_subtotal, company_currency)
        else:
            self.amount_in_inr = self.price_subtotal

    c_status = fields.Selection(
        [('new', 'New'), ('renewal', 'Renewal'), ('upgrade', 'Upgrade'), ('upsell', 'Upsell'), ('PDC', 'PDC'),
         ('etc', 'etc')], string='Status', default='new')
    c_pkg_validity = fields.Float(string='Package Expires After')
    c_analytic_acc_id = fields.Many2one('account.analytic.account', string='Analytical Account')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Cost Centre')
    c_tc_branch = fields.Many2one('hr.branch',string='TC Branch')
    c_sp_branch = fields.Many2one('hr.branch',string='SP Branch')
    c_tc_emp_id = fields.Many2one('hr.employee',string='Telecaller')
    c_sp_emp_id = fields.Many2one('hr.employee',string='Sales Person')
    c_fptags_id = fields.Many2one('ouc.fptag', string='FPTAGs')
    c_discount_value = fields.Float(string='Discount Value')
    c_amount_in_inr = fields.Float(string='Amount in INR')
    c_emi_option = fields.Selection(
        [('No EMI', 'No EMI'), ('3 Months EMI', '3 Months EMI'), ('6 Months EMI', '6 Months EMI')], string='Emi Option')
    c_tax_amount = fields.Float(string='Tax Amount')
    c_price_sub_with_tax = fields.Float(string='Price with Tax')
    amount_in_inr = fields.Float(compute='_compute_amt_in_inr', string='Amount in INR', store = True)


class ouc_account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'

    account_analytic_id = fields.Many2one('account.analytic.account', string='Cost Centre')

class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _inherit = "account.invoice.refund"

    @api.multi
    def action_deactivate_package(self):
        context = self.env.context
        active_model = context.get('active_model', '')
        active_id = context.get('active_id', False)
        type = context.get('type', False)
        if active_model == 'account.invoice' and active_id and type == 'out_invoice':
            res = ''
            param = self.env['ir.config_parameter']
            deactivatePackageApiUrl = param.search([('key', '=', 'deactivatePackageApiUrl')])
            deactivatePackageApiClinetId = param.search([('key', '=', 'deactivatePackageApiClinetId')])


            url = deactivatePackageApiUrl.value
            clienId = deactivatePackageApiClinetId.value

            self.env.cr.execute("""SELECT ai.number,
                                   CASE
                                      WHEN ai.c_sales_order_id IS NOT NULL
                                         THEN (SELECT name FROM sale_order WHERE id = ai.c_sales_order_id)
                                      ELSE ai.origin
                                   END AS sale_order,
                                   fp.id AS fptag_id,
                                   fp."externalSourceId",
                                   fp.name
                                   FROM account_invoice_line ail
                                   LEFT JOIN account_invoice ai ON ail.invoice_id = ai.id
                                   LEFT JOIN ouc_fptag fp ON ail.c_fptags_id = fp.id WHERE ai.id = {}"""
                                .format(active_id))

            invoice_lines = self.env.cr.fetchall()

            for val in invoice_lines:
                invoice_num = val[0]
                sale_order = val[1]
                fptag_id = val[2]
                fp_external_id = val[3]
                fptag = val[4]

                if not fptag:
                    continue;

                if not fp_external_id:
                    fptag_obj = self.env['ouc.fptag'].browse(fptag_id)
                    fptag_obj.get_fp_external_id()
                    fp_external_id = fptag_obj.externalSourceId

                payload = {"_nfInternalERPId": sale_order,
                           "_nfInternalERPInvoiceId": invoice_num,
                           "clientId": clienId,
                           "fpId": fp_external_id,
                           "paymentTransactionId": None
                           }

                headers = {
                    'content-type': "application/json",
                    'cache-control': "no-cache",
                }

                data = json.dumps(payload)

                response = requests.request("POST", url, data=data, headers=headers)

                response = json.loads(response.text)

                if 'Result' in response and response['Result']:
                    res = response['Result']
            self.env.cr.execute("UPDATE account_invoice SET refund_api_sts = '{}' , state = 'Paid Refund' WHERE id = {}".format(res, active_id))
        return True

    @api.multi
    def invoice_refund(self):
        data_refund = self.read(['filter_refund'])[0]['filter_refund']
        self.action_deactivate_package()
        return self.compute_refund(data_refund)

class invoice_line_image(models.Model):
	_name = 'invoice.line.image'
	_order = 'inv_num,rec_month'

	inv_date  = fields.Date('Date Invoice')
        activation_date = fields.Date('Activation Date')
        inv_expiry_date = fields.Date('Invoice Expriry Date')
        act_expiry_date =  fields.Date('Activation Expriry Date')
        product = fields.Char('Product')
        inv_num = fields.Char('Invoice No.')
        division = fields.Char('Division')
        partner = fields.Char('Partner')
        validity = fields.Float('Validity')
        subtotal_untaxed = fields.Float('Subtotal without tax')
        subtotal_with_tax = fields.Float('Subtotal with tax')
        sts = fields.Char('Status')
        state = fields.Char('State')
        rec_month = fields.Date('Recurring Month')
        rec_revenue_untaxed = fields.Float('Recurring Revenue')
        rec_revenue_with_tax = fields.Float('Recurring Revenue')
        fp_tags = fields.Char('FP Tags')
        price_unit = fields.Float('Price Unit')
        inv_amount_untaxed = fields.Float('Invoice Amount Without Taxed')
        inv_amount_with_tax = fields.Float('Invoice Amount With Taxed')
        business_name = fields.Char('Business Name')
        origin = fields.Char('Origin')
        inv_id = fields.Integer('Invoice Id')
        mrr_counter = fields.Integer('MRR Counter')


class act_invoice_line_image(models.Model):
	_name = 'act.invoice.line.image'
	_order = 'inv_num,rec_month'

	inv_date = fields.Date('Date Invoice')
	activation_date = fields.Date('Activation Date')
	inv_expiry_date = fields.Date('Invoice Expriry Date')
	act_expiry_date =  fields.Date('Activation Expriry Date')
	product = fields.Char('Product')
	inv_num = fields.Char('Invoice No.')
	division = fields.Char('Division')
	partner = fields.Char('Partner')
	validity = fields.Float('Validity')
	subtotal_untaxed = fields.Float('Subtotal without tax')
	subtotal_with_tax = fields.Float('Subtotal with tax')
	sts = fields.Char('Status')
	state = fields.Char('State')
	rec_month = fields.Date('Recurring Month')
	rec_revenue_untaxed =  fields.Float('Recurring Revenue')
	rec_revenue_with_tax = fields.Float('Recurring Revenue')
	fp_tags = fields.Char('FP Tags')
	price_unit = fields.Float('Price Unit')
	inv_amount_untaxed = fields.Float('Invoice Amount Without Taxed')
	inv_amount_with_tax = fields.Float('Invoice Amount With Taxed')
	business_name = fields.Char('Business Name')
	origin = fields.Char('Origin')
	p_aorg = fields.Char('Customer A Origin')
	f_aorg = fields.Char('FP A Origin')
	p_borg = fields.Char('Customer B Origin')
	f_borg = fields.Char('FP B Origin')
	inv_id = fields.Integer('Invoice Id')
	mrr_counter = fields.Integer('MRR Counter')



class inv_line_image_ad(models.Model):
	_name = 'inv.line.image.ad'
	_order = 'inv_num,rec_month'

	inv_date = fields.Date('Date Invoice')
	activation_date = fields.Date('Activation Date')
	inv_expiry_date = fields.Date('Invoice Expriry Date')
	act_expiry_date = fields.Date('Activation Expriry Date')
	product = fields.Char('Product')
	inv_num = fields.Char('Invoice No.')
	division = fields.Char('Division')
	partner = fields.Char('Partner')
	validity = fields.Float('Validity')
	subtotal_untaxed = fields.Float('Subtotal without tax')
	subtotal_with_tax = fields.Float('Subtotal with tax')
	sts = fields.Char('Status')
	state = fields.Char('State')
	rec_month = fields.Date('Recurring Month')
	rec_revenue_untaxed = fields.Float('Recurring Revenue')
	rec_revenue_with_tax = fields.Float('Recurring Revenue')
	fp_tags = fields.Char('FP Tags')
	price_unit = fields.Float('Price Unit')
	inv_amount_untaxed = fields.Float('Invoice Amount Without Taxed')
	inv_amount_with_tax = fields.Float('Invoice Amount With Taxed')
	business_name = fields.Char('Business Name')
	origin = fields.Char('Origin')
	p_aorg = fields.Char('Customer A Origin')
	f_aorg = fields.Char('FP A Origin')
	p_borg = fields.Char('Customer B Origin')
	f_borg = fields.Char('FP B Origin')
	inv_id = fields.Integer('Invoice Id')
	mrr_counter = fields.Integer('MRR Counter')


class act_inv_line_image_ad(models.Model):
	_name = 'act.inv.line.image.ad'
	_order = 'inv_num,rec_month'

	inv_date = fields.Date('Date Invoice')
	activation_date = fields.Date('Activation Date')
	inv_expiry_date = fields.Date('Invoice Expriry Date')
	act_expiry_date = fields.Date('Activation Expriry Date')
	product = fields.Char('Product')
	inv_num = fields.Char('Invoice No.')
	division = fields.Char('Division')
	partner = fields.Char('Partner')
	validity = fields.Float('Validity')
	subtotal_untaxed = fields.Float('Subtotal without tax')
	subtotal_with_tax = fields.Float('Subtotal with tax')
	sts = fields.Char('Status')
	state = fields.Char('State')
	rec_month = fields.Date('Recurring Month')
	rec_revenue_untaxed = fields.Float('Recurring Revenue')
	rec_revenue_with_tax = fields.Float('Recurring Revenue')
	fp_tags = fields.Char('FP Tags')
	price_unit = fields.Float('Price Unit')
	inv_amount_untaxed = fields.Float('Invoice Amount Without Taxed')
	inv_amount_with_tax = fields.Float('Invoice Amount With Taxed')
	business_name = fields.Char('Business Name')
	origin = fields.Char('Origin')
	p_aorg = fields.Char('Customer A Origin')
	f_aorg = fields.Char('FP A Origin')
	p_borg = fields.Char('Customer B Origin')
	f_borg = fields.Char('FP B Origin')
	inv_id = fields.Integer('Invoice Id')
	mrr_counter = fields.Integer('MRR Counter')


class contract_line_image(models.Model):
	_name = 'contract.line.image'
	_order = 'inv_num,rec_month'

	inv_date  = fields.Date('Date Invoice')
        activation_date = fields.Date('Activation Date')
        inv_expiry_date = fields.Date('Invoice Expriry Date')
        act_expiry_date =  fields.Date('Activation Expriry Date')
        product = fields.Char('Product')
        inv_num = fields.Char('Invoice No.')
        division = fields.Char('Division')
        partner = fields.Char('Partner')
        validity = fields.Float('Validity')
        subtotal_untaxed = fields.Float('Subtotal without tax')
        subtotal_with_tax = fields.Float('Subtotal with tax')
        sts = fields.Char('Status')
        state = fields.Char('State')
        rec_month = fields.Date('Recurring Month')
        rec_revenue_untaxed = fields.Float('Recurring Revenue')
        rec_revenue_with_tax = fields.Float('Recurring Revenue')
        fp_tags = fields.Char('FP Tags')
        price_unit = fields.Float('Price Unit')
        inv_amount_untaxed = fields.Float('Invoice Amount Without Taxed')
        inv_amount_with_tax = fields.Float('Invoice Amount With Taxed')
        business_name = fields.Char('Business Name')
        origin = fields.Char('Origin')
        inv_id = fields.Integer('Invoice Id')
        mrr_counter = fields.Integer('MRR Counter')
        inv_cancel_reason = fields.Char('Invoice Cancel Reason')


class act_contract_line_image_ad(models.Model):
	_name = 'act.contract.line.image.ad'
	_order = 'inv_num,rec_month'

	inv_date = fields.Date('Date Invoice')
	activation_date = fields.Date('Activation Date')
	inv_expiry_date = fields.Date('Invoice Expriry Date')
	act_expiry_date = fields.Date('Activation Expriry Date')
	product = fields.Char('Product')
	inv_num = fields.Char('Invoice No.')
	division = fields.Char('Division')
	partner = fields.Char('Partner')
	validity = fields.Float('Validity')
	subtotal_untaxed = fields.Float('Subtotal without tax')
	subtotal_with_tax = fields.Float('Subtotal with tax')
	sts = fields.Char('Status')
	state = fields.Char('State')
	rec_month = fields.Date('Recurring Month')
	rec_revenue_untaxed = fields.Float('Recurring Revenue')
	rec_revenue_with_tax = fields.Float('Recurring Revenue')
	fp_tags = fields.Char('FP Tags')
	price_unit = fields.Float('Price Unit')
	inv_amount_untaxed = fields.Float('Invoice Amount Without Taxed')
	inv_amount_with_tax = fields.Float('Invoice Amount With Taxed')
	business_name = fields.Char('Business Name')
	origin = fields.Char('Origin')
	p_aorg = fields.Char('Customer A Origin')
	f_aorg = fields.Char('FP A Origin')
	p_borg = fields.Char('Customer B Origin')
	f_borg = fields.Char('FP B Origin')
	inv_id = fields.Integer('Invoice Id')
	mrr_counter = fields.Integer('MRR Counter')
	inv_cancel_reason = fields.Char('Invoice Cancel Reason')





