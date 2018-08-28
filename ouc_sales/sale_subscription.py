from odoo import api,models,fields, _,SUPERUSER_ID
import datetime
from datetime import timedelta
from odoo import exceptions
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import json
import requests
import odoo.addons.decimal_precision as dp
import urllib

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



class ouc_sale_subscription(models.Model):
    
    _inherit = 'sale.subscription'
    
    _order = "c_sales_order_id, date_start desc"
    
    def _compute_invoice_count(self):
        for val in self:
            analytic_ids = [line.c_cost_center.id for line in val.recurring_invoice_line_ids]
            analytic_ids.append(val.analytic_account_id.id)
            invoice_line_data = self.env['account.invoice.line'].read_group(
                domain=[('account_analytic_id', 'in', analytic_ids),
                        ('invoice_id.partner_id', '=', val.partner_id.id),
                        ('invoice_id.state', 'in', ['draft', 'open', 'paid'])],
                fields=["account_analytic_id", "invoice_id"],
                groupby=["account_analytic_id", "invoice_id"],
                lazy=False)
            if not val.recurring_invoice_line_ids:
                print ">>>>>>ACC1>>>>>>>", val.recurring_invoice_line_ids
                val.invoice_count = 0
            else:
                print ">>>>>>ACC2>>>>>>>", val.recurring_invoice_line_ids[0].id
                print ">>>>>>", invoice_line_data
                val.invoice_count = len(invoice_line_data)
                
    def _compute_sale_order_count(self):
        sale_order_data = self.env['sale.order'].read_group(domain=[('project_id', 'in', self.mapped('analytic_account_id').ids),
                                                                    ('partner_id', '=', self.partner_id.id),
                                                                    ('subscription_management', '!=', False),
                                                                    ('state', 'in', ['draft', 'sent', 'sale', 'done'])],
                                                            fields=['project_id'],
                                                            groupby=['project_id'])
        mapped_data = dict([(m['project_id'][0], m['project_id_count']) for m in sale_order_data])
        for sub in self:
            sub.sale_order_count = mapped_data.get(sub.analytic_account_id.id, 0)


    @api.onchange('c_account_payment_ids')
    def calculate_remaining_amount(self):
        for val in self:
            if not val.c_sales_order_id:
                return
            self.env.cr.execute("select amount_total from sale_order where id=%s ", [val.c_sales_order_id.id])
            amount_total = 0
            amount = self.env.cr.fetchall()
            if amount:
                amount_total = amount[0][0]
            total = amount_total
            print "amount_total", amount_total
            print "total", total
            if not val.c_account_payment_ids:
                val.c_amount_to_be_paid = total
                return
            print "self.c_amount_to_be_paid", val.c_amount_to_be_paid
            for payment in val.c_account_payment_ids:
                total = total - payment.amount
            print "total", total
            print ">>>>>>>>", total
            val.c_amount_to_be_paid = total
        
    partner_id = fields.Many2one("res.partner", store=True)
    
    c_team_id = fields.Many2one('crm.team', string='Sales Team')
    
    c_company_name = fields.Char('Company Name')
    c_ex_website = fields.Char('Existing Website')
    c_sale_order = fields.Char('Sale Order', related="c_sales_order_id.name")
    
    # Invoice status field
    c_is_invoiced = fields.Boolean("Is invoiced?")
    c_invoice_status = fields.Selection([('no','Activation done & Invoice Created'), ('yes', 'Activation pending & Invoice Pending'),('MIB Done','MIB Done')], string = "Invoice Status", default='yes')
    
    #Payment related info - to remove
    c_journal_id = fields.Many2one("account.journal", string="Payment Method")
    c_payement_type = fields.Selection([('Full Payment','Full Payment'), ('Partial Payment','Partial Payment')], string="Payment Type")
    c_tds_check = fields.Selection([('Yes','Yes'), ('No','No')], string="TDS Deducted or Not?", default='No')
    c_paid_amount = fields.Float("Paid Amount")
    c_payment_ref = fields.Char(string = "Payement Reference Number", size = 128)
    c_payment_receive_date = fields.Date("Payment Received Date")
    c_package_ext_req = fields.Boolean("Package Extension required")
    
    #Before RTA sent
    c_rta_hold_issue = fields.Selection([('Name Mismatch','Name Mismatch'),('Payment Amount Differential','Payment Amount Differential'),('Cheque Bounced: Funds Insufficient','Cheque Bounced: Funds Insufficient'),('Cheque Bounced: Payment stopped by customer','Cheque Bounced: Payment stopped by customer'),('Cheque Bounced: cheque details mistakes','Cheque Bounced: cheque details mistakes'),('Payment Untraceable: Deposit slip not attached & Amount not received','Payment Untraceable: Deposit slip not attached & Amount not received'),('Payment Untraceable: Deposit slip not stamped & Amount not received','Payment Untraceable: Deposit slip not stamped & Amount not received'),('Partial payment without second payment details','Partial payment without second payment details'),('Duplicate invoice created','Duplicate invoice created'),('No Issue','No Issue'),('Cheque Bounce','Cheque Bounce'),('Cheque Bounced - No Recovery@SalesAudit','Cheque Bounced - No Recovery@SalesAudit'),('Revise Payment Received','Revised Payment Received'),('MIB Test Cases', 'MIB Test Cases'),('S.O. Without Attachment', 'S.O. Without Attachment')], string='MIB Hold Reason', default = 'No Issue',track_visibility='onchange')
    c_rta_hold_description = fields.Text(string='Details for Holding MIB', track_visibility='onchange')
    
    #After RTA sent - For MLC
    c_case_lh_mlc = fields.Boolean(string="LH to MLC")
    c_case_mlc_mlc = fields.Boolean(string="MLC to MLC")
    c_case_new_mlc = fields.Boolean(string="New MLC")
    c_case_renew_mlc = fields.Boolean(string="Renew MLC")
    c_username = fields.Char("Username")
    c_primary_fp = fields.Char("Primary FPTAG")
    
    #After RTA sent - Verification call fields starts
    c_rta_sent_status = fields.Boolean(string="MIB Confirm?")
    c_rta_status = fields.Boolean(string='MIB Status')
    c_phone_number = fields.Char("Mobile", size = 20)
    c_rta_done_date = fields.Date("MIB Done Date")
    c_verification_call_status = fields.Boolean(string='Verification Call Status')
    c_reject_reason = fields.Selection( [["Customer Refused as wanted assured Google Position","Customer Refused as wanted assured Google Position"],["Customer Refused as wanted committed leads","Customer Refused as wanted committed leads"],["Customer refused over Commitment v/s delivered","Customer refused over Commitment v/s delivered"],["Customer refused over SEO understanding","Customer refused over SEO understanding"],["Others","Others"]],string='Reason to Reject')
    c_other_reject = fields.Char(string='Other Reason for Reject & Refund')
    c_verified_by_id = fields.Many2one('hr.employee',string='Verification Done by')
    c_verification_remarks = fields.Text(string='Verification Remarks')
    c_rta_case0 = fields.Boolean(string='Accepted with T&C', related='c_vc_cl_all')
    c_rta_case1 = fields.Boolean(string='Acceptance Case', default=True)
    c_rta_case2 = fields.Boolean('On Hold')
    c_rta_case3 = fields.Boolean('Reject & Return Payment')
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
    
    c_onboard_time = fields.Datetime(string='On Boarding Schdule Time')
    c_onboarding_type = fields.Selection( [["Video Call without FOS","Video Call without FOS"],["Video Call with FOS","Video Call with FOS"],["Audio Call without FOS","Audio Call without FOS"],["Audio Call with FOS","Audio Call with FOS"],["No onboarding Required","No onboarding Required"]],string='On Boarding Call Type')
    c_no_of_fps = fields.Float(string='no of FPTAGs')
    c_verification_status = fields.Char(string='MIB & VC status')
    c_call_hold_reason = fields.Selection( [["Customer Concerns over Google Position","Customer Concerns over Google Position"],["Customer Concerns over Visible Location","Customer Concerns over Visible Location"],["Customer Concerns over SEO and Ranking","Customer Concerns over SEO and Ranking"],["Customer Concerns over Leads","Customer Concerns over Leads"],["Customer Concerns over other Commitments made","Customer Concerns over other Commitments made"],["Sales commitment to do content updation to the customer","Sales commitment to do content updation to the customer"]],string='Reason to Hold')
    c_escalation_remarks = fields.Text(string='Escalation remarks')
    c_dup_state = fields.Char(string='Duplicate State')
    c_onboard_local_time = fields.Datetime('On Boarding Time',compute='compute_time',store=True)

    # -- Verification call fields end

    # sales related fields
    c_sales_order_id = fields.Many2one('sale.order', string='Sales order Reference')
    c_sale_confirm_date = fields.Datetime('Sale Confirm Date', related='c_sales_order_id.confirmation_date')
    c_auto_create_fptag = fields.Boolean(string='Auto Create FPTAG')
    c_state = fields.Selection([["draft","Draft"],["proforma","Pro-forma"],["proforma2","Pro-forma"],["open","Open"],["paid","Paid"],["open2","Open2"],["cancel","Cancelled"],["hold","Hold"]])
    
    is_la_case = fields.Boolean(string='Is a LA case?', related='c_sales_order_id.is_la_case')
    c_tc_manager_hierarchy = fields.Char('Tele Caller Manager Hierarchy',store=True, related='c_sales_order_id.c_tc_manager_hierarchy')
    c_mangers_hierarchy = fields.Char('Tele Caller Manager Hierarchy',store=True, related='c_sales_order_id.c_mangers_hierarchy')

    # latest invoice
    c_invoice_id = fields.Many2one('account.invoice', string='Latest Invoice')
    
    # Payment related fields
    c_account_payment_ids = fields.One2many('account.payment', 'c_subscription_id', string='Account Payment')
    c_amount_to_be_paid = fields.Monetary('Remaining Amount',compute='calculate_remaining_amount')
    c_tds_amount = fields.Float('TDS Rec Amount')
    c_add_payment_details = fields.One2many('ouc.additional.payment.details','subscription_id',string='Received Payment Details')
    
    # Reject and refund bank details
    c_bank_details=fields.One2many('ouc.bankdetails','bankdetails_id')
    c_bank_account = fields.Char('Bank Account Number')
    c_bank_ifsc = fields.Char('IFSC')
    c_bank_id = fields.Many2one('res.bank', string='Bank Name')
    c_bank_account_holder = fields.Char('Account holder Name')
    welcome_call = fields.Char('Welcome Call Link')
    vc_followup_status = fields.Selection([('0','Not Reachable - Switch off / out of coverage'),
                                           ('1','Not Reachable - Wrong Number'),
                                           ('2','Not Reachable - Ringing'),
                                           ('3','Connected & call later'),
                                           ('4','Connected & not right party'),
                                           ('5','Connected & Accepted with T&C without concern'),
                                           ('6','Connected & expressed concern'),
                                           ('7','Connected & re-verified & Dispute'),
                                           ('8','Connected & expressed concern & Got Satisfied & T&C Accepted'),
                                           ('9','Connected & re-verified & Customer Refunded')],
                                          string='VC Follow-up Status', track_visibility='onchange')
    cfc_contract_id = fields.Many2one('cfc.contract', 'CF')
    partner_username = fields.Char('Partner Username')
    cfc_mlc_contract_id = fields.Many2one('cfc.contract', 'MLC CF')
    mlc_onboarding_form = fields.Many2one('nf.mlc.onboarding', 'MLC Onboarding Form')
    is_corporate_website = fields.Boolean('Is Corporate Website?')

    @api.multi
    def create_wc_ticket(self):

        lines_to_activate = [lines for lines in self.recurring_invoice_line_ids if
                            lines.c_sale_order_id == self.c_sales_order_id and not lines.c_activation_id]

        if not lines_to_activate:
            return True

        fptag = lines_to_activate[0].c_fptags_id.name

        param = self.env['ir.config_parameter']

        # assignFptoUrl
        getMemberForFpUrl = param.search([('key', '=', 'getMemberForFpTaUrl')])

        print "getMemberForFpUrl", getMemberForFpUrl.value

        url = "{}&fpTag={}&memType=WC".format(getMemberForFpUrl.value, fptag)
        print "url", url
        response = requests.get(url)

        print ">>>>>>>", response.status_code
        if int(response.status_code) != 200:
            return
        ria_acc_manager_details = json.loads(response.text)

        if not ria_acc_manager_details:
            # assigning member
            fpclientId = "A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"
            assignMemberToFpUrl = param.search([('key', '=', 'assignMemberToFpTaUrl')])
            url = "{}&fpTag={}&fpClientId={}&memType=WC".format(assignMemberToFpUrl.value, fptag, fpclientId)
            print "url", url
            response = requests.get(url.format(fptag, fpclientId))
            print ">>>>>>>", response.status_code
            if int(response.status_code) != 200:
                return

            ria_acc_manager_details = json.loads(response.text)

            # again get assigned member
            url = "{}&fpTag={}&memType=WC".format(getMemberForFpUrl.value, fptag)
            response = requests.get(url)
            print ">>>>>>>", response.status_code
            if int(response.status_code) != 200:
                return

            ria_acc_manager_details = json.loads(response.text)

        partner_username = ria_acc_manager_details.get("PartnerUsername", '')
        self.c_acc_mngr = ria_acc_manager_details.get("Name", '')
        user_email = ria_acc_manager_details.get("Email", '')


        #setMeetingOnTimeWithFpUrl
        setMeetingOnTimeWithFpUrl = param.search([('key', '=', 'setMeetingOnTimeWithFpUrl')])
        setMeetingOnTimeWithFpClientId = param.search([('key', '=', 'setMeetingOnTimeWithFpClientId')])

        skip_calendar = True
        date = fields.Date.context_today(self)
        description = 'Welcome Call'
        body = 'Welcome Call'
        onboarding_type = ''

        setMeeting_request_url = "{}?fpTag={}&clientId={}&meetingDateTime={}&summary={}&description={}&slotDurationMins=45&location={}&" \
                                 "meetingType=ONBOARDING&salesPersonName={}&salesPersonEmail={}&skipCalender={}&memType=WC" \
            .format(setMeetingOnTimeWithFpUrl.value, fptag, setMeetingOnTimeWithFpClientId.value,
                    date, description, body, onboarding_type, partner_username, user_email, skip_calendar)
        print"========setMeeting_request_url======", setMeeting_request_url
        response_obj = urllib.urlopen(setMeeting_request_url)
        obm_encoder = response_obj.read().decode('utf-8')
        print "============obm_encoder======b===========", obm_encoder

        if obm_encoder and 'MeetingCustomId' in obm_encoder:
            custom_meeting_id = json.loads(obm_encoder).get('MeetingCustomId', '')
            param = self.env['ir.config_parameter']
            setMeetingAsDoneUrl = param.search([('key', '=', 'setMeetingAsDoneUrl')])
            setMeetingOnTimeWithFpClientId = param.search([('key', '=', 'setMeetingOnTimeWithFpClientId')])

            url = setMeetingAsDoneUrl.value

            querystring = {"authClientId": setMeetingOnTimeWithFpClientId.value,
                           "customId": custom_meeting_id,
                           "updatedDesc": 'WelcomeCallDone',
                           "smsText": 'WelcomeCallDone'
                           }

            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache",
            }

            response = requests.request("GET", url, headers=headers, params=querystring)
            response = response.text
            print"========response=======",response
            if response:
                response = json.loads(response)

        return True

    @api.multi
    def write(self, vals):
        if 'welcome_call' in vals and vals['welcome_call']:
            self.env.cr.execute("UPDATE sale_order "
                                "SET welcome_call_status = 'Done' "
                                "WHERE id = {}"
                                .format(self.c_sales_order_id.id))
            self.create_wc_ticket()

        if 'c_rta_hold_issue' in vals and vals['c_rta_hold_issue'] == 'Revise Payment Received':
            self.env.cr.execute("UPDATE sale_order "
                                "SET mib_hold_issue = 'Revise Payment Received', mib_status = 'Not Done Yet', mib_action_date = 'now'::date "
                                "WHERE id = {}"
                                .format(self.c_sales_order_id.id))

            template = self.env['mail.template'].search([('name', '=', 'Revise Payment received')],
                                                        limit=1)
            if template:
                template.send_mail(self.id)
        res = super(ouc_sale_subscription, self).write(vals)
        return res

    @api.multi
    def open_mlc_onboarding_form(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "nf.mlc.onboarding",
            "views": [[self.env.ref('ouc_sales.nf_mlc_onboarding_form').id, "form"]],
            "domain": [('so_id','=',self.c_sales_order_id.id),('contract_id','=',self.id)],
            'res_id': self.mlc_onboarding_form and self.mlc_onboarding_form.id or False,
            "context": {},
            'view_mode':'form',
            'target': 'new',
            "name": "MLC Onboarding Form",
            'flags': {'initial_mode': 'view'}
               }

    @api.model
    def update_managers_email(self):
        subs_ids=self.sudo().search([])
        for rec in subs_ids:
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
            self.env.cr.execute("update sale_subscription set c_mangers_hierarchy=%s where id = %s",(managers_email,rec.id,))
        return True

    def rta_hold_email(self):
        reason = self.c_rta_hold_issue
        so_obj = self.c_sales_order_id
        user_id = so_obj.user_id.id
        cr = self.env.cr
        msg = MIMEMultipart()
        sp_name = ''
        sp_branch = ''
        sp_email = ''
        str_sql = "SELECT emp.name_related," \
                  "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch," \
                  "emp.work_email " \
                  "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                  "WHERE res.user_id = {}" \
            .format(user_id)
        cr.execute(str_sql)
        emp = cr.fetchall()
        if emp:
            sp_name = emp[0][0]
            sp_branch = emp[0][1]
            sp_email = emp[0][2]

        if reason == 'Payment Amount Differential':
            reason = 'Payment not recieved'
        so_name = so_obj.name
        mail_subject = "Attention: Sales Order " + str(so_name or '') + " MIB on hold - Reason : " + str(
            reason) + " by " + str(sp_name) + " from " + str(sp_branch)

        heading = "Sales Order " + str(so_name or '') + ' ' + "MIB on hold"
        for f in self.c_add_payment_details:
            if f.sale_order_id == so_obj:
                if f.cheque_pic:
                    cheque_attachment = base64.b64decode(f.cheque_pic)
                    part = MIMEApplication(
                        cheque_attachment,
                        Name='cheque'
                    )
                    part['Content-Disposition'] = 'attachment; filename="{}"' \
                        .format(f.cheque_pic_name and f.cheque_pic_name or 'cheque')
                    msg.attach(part)
                if f.receipt_pic:
                    receipt_attachment = base64.b64decode(f.receipt_pic)
                    part = MIMEApplication(
                        receipt_attachment,
                        Name='receipt'
                    )
                    part['Content-Disposition'] = 'attachment; filename="{}"' \
                        .format(f.receipt_pic_name and f.receipt_pic_name or 'receipt')
                    msg.attach(part)

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
                             <td style="width:30%"><b>Sales Order</b></td>
                            <td style="width:70%">: <span>""" + str(so_name or '') + """</span></td>
                          </tr>
                          <tr style="width:100%">
                             <td style="width:30%"><b>SO Confirmation Date</b></td>
                            <td style="width:70%">: <span>""" + str(so_obj.confirmation_date or '') + """</span></td>
                          </tr>

                          <tr style="width:100%">
                             <td style="width:30%"><b>Customer</b></td>
                            <td style="width:70%">: <span>""" + str(self.partner_id.name or '') + """</span></td>
                          </tr>

                  <tr style="width:100%">
                             <td style="width:30%"><b>Customer City</b></td>
                            <td style="width:70%">: <span>""" + str(self.partner_id.c_city_id and self.partner_id.c_city_id.name or '') + """</span></td>
                          </tr>

                  <tr style="width:100%">
                             <td style="width:30%"><b>Sales Person</b></td>
                            <td style="width:70%">: <span>""" + str(sp_name or '') + """</span></td>
                          </tr>
                          <tr style="width:100%">
                             <td style="width:30%"><b>SP Branch</b></td>
                            <td style="width:70%">: <span>""" + str(sp_branch or '') + """</span></td>
                          </tr>

                  <tr style="width:100%">
                             <td style="width:30%"><b>Amount</b></td>
                             <td style="width:70%">: <span>""" + str(so_obj.amount_total or '') + """</span></td>
                          </tr>
                  <tr style="width:100%">
                             <td style="width:30%"><b>Reason</b></td>
                             <td style="width:70%">: <span>""" + str(self.c_rta_hold_description or '') + """</span></td>
                          </tr>

                  <tr style="width:100%">
                             <td style="width:30%"></td>
                             <td style="width:70%"></td>
                          </tr>
                    </table>
               <p>----------------------------------------------------------------------------------------------</p>
                </body>



        <html>"""

        emailto = [sp_email, "salesaudit@nowfloats.com",
                   "findesk@nowfloats.com", "ops@nowfloats.com", "nitin@nowfloats.com",
                   "satesh.kohli@nowfloats.com"]
        emailfrom = "hello@nowfloats.com"
        msg['From'] = emailfrom
        msg['To'] = ", ".join(emailto)
        # msg['CC'] = ", ".join(emailto)
        msg['Subject'] = mail_subject

        part1 = MIMEText(html, 'html')
        msg.attach(part1)

        smtp_user = 'hello@nowfloats.com'
        cr.execute("SELECT smtp_pass FROM ir_mail_server WHERE smtp_user = '{}'".format(smtp_user))
        mail_server = cr.fetchone()
        smtp_pass = mail_server[0]
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_pass)
        text = msg.as_string()
        server.sendmail(emailfrom, emailto, text)
        server.quit()
        return True

    @api.multi
    def action_deactivate_package(self):
        param = self.env['ir.config_parameter']
        deactivatePackageApiUrl = param.search([('key', '=', 'deactivatePackageApiUrl')])
        deactivatePackageApiClinetId = param.search([('key', '=', 'deactivatePackageApiClinetId')])

        url =  deactivatePackageApiUrl.value
        clienId = deactivatePackageApiClinetId.value

        sale_order = self.c_sales_order_id.name
        self.env.cr.execute("SELECT ssl.id, ssl.c_fptags_id, fp.name "
                            "FROM sale_subscription_line ssl "
                            "LEFT JOIN ouc_fptag fp ON ssl.c_fptags_id = fp.id "
                            "WHERE analytic_account_id = {} AND c_sale_order_id = {}"
                            .format(self.id, self.c_sales_order_id.id))

        subscription_lines = self.env.cr.fetchall()

        for val in subscription_lines:
            line_id = val[0]
            fp_id = val[1]
            fptag = val[2]
            fptag_obj = self.env['ouc.fptag'].browse(fp_id)
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

            response = json.loads(response.text)
            print"===========response====a====", response
            if 'Result' in response and response['Result']:
                self.env.cr.execute("UPDATE sale_subscription_line "
                                    "SET c_activation_id = c_activation_id || '-Deleted' "
                                    "WHERE id = {}".format(line_id))

        return True

    @api.multi
    def action_cancel_payment_by_sale_order(self):
        param = self.env['ir.config_parameter']
        CancelPaymentBySaleOrderUrl = param.search([('key', '=', 'CancelPaymentBySaleOrderUrl')])
        deactivatePackageApiClinetId = param.search([('key', '=', 'deactivatePackageApiClinetId')])

        url = CancelPaymentBySaleOrderUrl.value
        clienId = deactivatePackageApiClinetId.value

        sale_order = self.c_sales_order_id.name

        cancel_reason = self.c_rta_hold_issue

        querystring = {"clientId": clienId,
                       "rejectionReason": cancel_reason,
                       "saleOrderNumber": sale_order
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("POST", url, headers=headers, params=querystring)
        print"==========response========b========", response
        print(response.text)
        return True

    def action_hold_rta(self):
        if self.c_rta_hold_issue in ('Cheque Bounced: Funds Insufficient', 'Cheque Bounced: Payment stopped by customer', 'Cheque Bounced: cheque details mistakes'):
            self.c_verification_status = 'MIB Rejected'
            so_mib_status = 'MIB Rejected'
        elif self.c_rta_hold_issue in ('Duplicate invoice created', 'Payment Untraceable: Deposit slip not attached & Amount not received', 'Payment Untraceable: Deposit slip not stamped & Amount not received'):
            self.c_verification_status = 'MIB Not Required'
            so_mib_status = 'MIB Not Required'
        else:
            self.c_verification_status = 'MIB on Hold'
            so_mib_status = 'Hold'

	self.env.cr.execute("UPDATE sale_order SET mib_hold_issue = %s, mib_status = %s, mib_action_date = 'now'::date WHERE id = %s", (self.c_rta_hold_issue, so_mib_status, self.c_sales_order_id.id))
        try:
           self.rta_hold_email()
        except:
           pass
        #self.action_deactivate_package()
        #self.action_cancel_payment_by_sale_order()
        return True

    @api.depends('c_onboard_time')
    def compute_time(self):
        for val in self:
            if val.c_onboard_time:
                time1 = datetime.datetime.strptime(val.c_onboard_time, "%Y-%m-%d %H:%M:%S")
                time_added = time1 + timedelta(hours=5, minutes=30)
                val.c_onboard_local_time = time_added

    def action_send_rta(self):
        if self.c_rta_hold_issue != 'No Issue':
            raise exceptions.ValidationError(_('There are MIB hold issue, Please put MIB on Hold'))
        
        if not self.c_account_payment_ids:
            raise exceptions.ValidationError(_('In order to send MIB, please fill all Payment related information'))
    
        if not self.c_auto_create_fptag:
            #self.assign_account_manager()
            self.assign_account_manager_for_ta()
        
        self.c_rta_sent_status = True
        self.c_verification_status = 'MIB Confirmed'
        self.c_rta_done_date = datetime.date.today()
        self.calculate_fptags()
        self.c_phone_number = self.partner_id.mobile
        self.env.cr.execute("update sale_order set mib_hold_issue=%s, mib_status='Yes', mib_action_date = 'now'::date where id = %s",(self.c_rta_hold_issue, self.c_sales_order_id.id))
        try:
            self.get_chc_profile()
        except:
           pass
        template = self.env['mail.template'].search([('name', '=', 'NowFloats RTA Done for Non-Enterprise')], limit=1)
        if template:
            template.send_mail(self.id)
            
    @api.onchange('c_username')
    def validate_username(self):
        if not self.c_username:
            return
        
        client_id = "A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"
        api_url = "https://api.withfloats.com/Discover/v1/fpuserprofile/verifyUniqueuname"
        request_data = {
                "clientId": client_id,
                "uname": self.c_username
            }
        
        data = json.dumps(request_data)

        print ">>>>>>>>>>> ", data
        response = requests.post(api_url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"})

        if int(response.status_code) != 200:
            self.c_username = ''
            error = 'Verifying User name API response is', response.status_code
            return {
                        'warning': {
                            'message': error
                        }
                    }
        username_validity = json.loads(response.text)
        if username_validity == True and (self.c_case_mlc_mlc or self.c_case_renew_mlc):
            self.c_username = ''
            return {
                        'warning': {
                            'message': 'User name is not existing, choose a new one'
                        }
                    }
            
        if username_validity != True and (self.c_case_new_mlc or self.c_case_lh_mlc):
            self.c_username = ''
            return {
                        'warning': {
                            'message': 'User name is not valid, choose a new one'
                        }
                    }
            
        
    def assign_account_manager(self):
        lines_to_activate = [lines for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id and lines.c_activation_id == False]
        if self.c_auto_create_fptag:
            return
        if not lines_to_activate:
            return
        
        fptag = lines_to_activate[0].c_fptags_id.name
        param = self.env['ir.config_parameter']
        getMemberForFpUrl = param.search([('key', '=', 'getMemberForFpUrl')])
        
        print "getMemberForFpUrl", getMemberForFpUrl.value
        
        url = "{}&fpTag={}".format(getMemberForFpUrl.value,fptag)
        print "url",url
        response = requests.get(url)
        
        print ">>>>>>>", response.status_code
        if int(response.status_code) != 200:
            return
        ria_acc_manager_details = json.loads(response.text)
        if not ria_acc_manager_details:
            # assigning member
            fpclientId = "A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"
            assignMemberToFpUrl = param.search([('key', '=', 'assignMemberToFpUrl')])
            url = "{}&fpTag={}&fpClientId={}".format(assignMemberToFpUrl.value,fptag,fpclientId)
            print "url",url
            response = requests.get(url.format(fptag, fpclientId))
            print ">>>>>>>", response.status_code
            if int(response.status_code) != 200:
                return
            
            ria_acc_manager_details = json.loads(response.text)
            
            # again get assigned member
            url = "{}&fpTag={}".format(getMemberForFpUrl.value,fptag)
            response = requests.get(url)
            print ">>>>>>>", response.status_code
            if int(response.status_code) != 200:
                return
            
            ria_acc_manager_details = json.loads(response.text)
            
        self.c_acc_mngr = ria_acc_manager_details["Name"]
        self.c_acc_mngr_email = ria_acc_manager_details["Email"]

        calendar_link = "https://calendar.google.com/calendar/embed?src={}%40nowfloats.com&ctz=Asia/Calcutta".format(self.c_acc_mngr)
        self.c_calendar_link = calendar_link
        self.c_acc_mngr_call_link = ria_acc_manager_details["VideoCallLink"]

    def assign_account_manager_for_ta(self):
        lines_to_activate = [lines for lines in self.recurring_invoice_line_ids if
                             lines.c_sale_order_id == self.c_sales_order_id and lines.c_activation_id == False]
        if self.c_auto_create_fptag:
            return
        if not lines_to_activate:
            return

        fptag = lines_to_activate[0].c_fptags_id.name
        param = self.env['ir.config_parameter']
        getMemberForFpUrl = param.search([('key', '=', 'getMemberForFpTaUrl')])

        print "getMemberForFpUrl", getMemberForFpUrl.value

        url = "{}&fpTag={}&memType=TA".format(getMemberForFpUrl.value, fptag)
        print "url", url
        response = requests.get(url)

        print ">>>>>>>", response.status_code
        if int(response.status_code) != 200:
            return
        ria_acc_manager_details = json.loads(response.text)
        if not ria_acc_manager_details:
            # assigning member
            fpclientId = "A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E"
            assignMemberToFpUrl = param.search([('key', '=', 'assignMemberToFpTaUrl')])
            url = "{}&fpTag={}&fpClientId={}&memType=TA".format(assignMemberToFpUrl.value, fptag, fpclientId)
            print "url", url
            response = requests.get(url.format(fptag, fpclientId))
            print ">>>>>>>", response.status_code
            if int(response.status_code) != 200:
                return

            ria_acc_manager_details = json.loads(response.text)

            # again get assigned member
            url = "{}&fpTag={}&memType=TA".format(getMemberForFpUrl.value, fptag)
            response = requests.get(url)
            print ">>>>>>>", response.status_code
            if int(response.status_code) != 200:
                return

            ria_acc_manager_details = json.loads(response.text)

        self.partner_username = ria_acc_manager_details.get("PartnerUsername", '')
        self.c_acc_mngr = ria_acc_manager_details.get("Name", '')
        self.c_acc_mngr_email = ria_acc_manager_details.get("Email", '')

        calendar_link = "https://calendar.google.com/calendar/embed?src={}%40nowfloats.com&ctz=Asia/Calcutta".format(
            self.c_acc_mngr)
        self.c_calendar_link = calendar_link
        self.c_acc_mngr_call_link = ria_acc_manager_details.get("VideoCallLink", '')
        return True
            
    def update_verification_user(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee:
            print "employee", employee
            print "self.c_verified_by", self.c_verified_by_id
            self.c_verified_by_id = employee


    def calculate_fptags(self):
        if self.c_auto_create_fptag == True:
            temp = []
            count = 0
            for val in self.c_sales_order_id.order_line:
                count = count + int(val.product_uom_qty)
                if val.c_fptags_id:
                    temp.append(val.c_fptags_id)
            self.c_no_of_fps = count - len(temp)
        else:
            temp =[]
            for val in self.c_sales_order_id.order_line:
                if val.c_fptags_id:
                    temp.append(val.c_fptags_id)
            uni_fp = list(set(temp))
            self.c_no_of_fps = len(uni_fp)
            
    @api.onchange('c_case_lh_mlc')
    def action_case_lh_mlc(self):
        self.c_username = ''
        if self.c_case_lh_mlc:
            self.c_case_mlc_mlc = False
            self.c_case_new_mlc = False
            self.c_case_renew_mlc = False

    @api.onchange('c_case_mlc_mlc')
    def action_case_mlc_mlc(self):
        self.c_username = ''
        if self.c_case_mlc_mlc:
            self.c_case_lh_mlc = False
            self.c_case_new_mlc = False
            self.c_case_renew_mlc = False

    @api.onchange('c_case_new_mlc')
    def action_case_new_mlc(self):
        self.c_username = ''
        if self.c_case_new_mlc:
            self.c_case_lh_mlc = False
            self.c_case_mlc_mlc = False
            self.c_case_renew_mlc = False

    @api.onchange('c_case_renew_mlc')
    def action_case_renew_mlc(self):
        self.c_username = ''
        if self.c_case_renew_mlc:
            self.c_case_lh_mlc = False
            self.c_case_mlc_mlc = False
            self.c_case_new_mlc = False

    @api.onchange('c_rta_case1')
    def action_rta_case1(self):
        if self.c_rta_case1:
            self.c_rta_case2 = False
            self.c_rta_case3 = False
            self.update_vc_all_status()
        
    @api.onchange('c_rta_case2')
    def action_rta_case2(self):
        if self.c_rta_case2:
            self.c_rta_case1 = False
            self.c_rta_case3 = False
            self.c_rta_case0 = False

    @api.onchange('c_rta_case3')
    def action_rta_case3(self):
        if self.c_rta_case3:
            self.c_rta_case1 = False
            self.c_rta_case2 = False
            self.c_rta_case0 = False
            
    @api.onchange('c_vc_cl_all')
    def vc_all_status(self):
        if self.c_vc_cl_all:
            self.c_vc_cl1 = True
            self.c_vc_cl2 = True
            self.c_vc_cl3 = True
            self.c_vc_cl4 = True
            self.c_vc_cl5 = True
            
    @api.onchange('c_vc_cl1', 'c_vc_cl2', 'c_vc_cl3', 'c_vc_cl4', 'c_vc_cl5')
    def update_vc_all_status(self):
        if self.c_vc_cl1 and self.c_vc_cl2 and self.c_vc_cl3 and self.c_vc_cl4 and self.c_vc_cl5:
            self.c_vc_cl_all = True
            self.c_rta_case0 = True
        else:
            self.c_vc_cl_all = False
            self.c_rta_case0 = False

    
    def generate_la_invoice(self):
        if self.is_la_case:
            self.generate_invoice_and_pay()
            activation_id = "absdjds121223eerd"
            self.partner_id.sudo().write({'c_alliance_id': activation_id})
            self.setting_rta_default()
            self.c_is_invoiced = True
            self.c_invoice_status = 'no'
            return self.action_subscription_invoice()

    def update_taxes_in_subscription(self):
        partner_state = self.partner_id.state_id and self.partner_id.state_id.name
        print "partner_state",partner_state
        sale_order_id = self.c_sales_order_id.id
        subscription_lines = self.env['sale.subscription.line'].sudo().search([('c_sale_order_id','=',sale_order_id)])
        if partner_state and partner_state == 'Telangana':
            for line in subscription_lines:
                self.env.cr.execute("delete from account_tax_sale_subscription_line_rel where sale_subscription_line_id=%s",(line.id,))
                self.env.cr.execute("INSERT into account_tax_sale_subscription_line_rel (sale_subscription_line_id,account_tax_id) values (%s,63)",(line.id,))
                self.env.cr.execute("INSERT into account_tax_sale_subscription_line_rel (sale_subscription_line_id,account_tax_id) values (%s,64)",(line.id,))
        else:
            for line in subscription_lines:
                self.env.cr.execute("delete from account_tax_sale_subscription_line_rel where sale_subscription_line_id=%s",(line.id,))
                self.env.cr.execute("INSERT into account_tax_sale_subscription_line_rel (sale_subscription_line_id,account_tax_id) values (%s,62)",(line.id,))
        return True


    
    def action_verification_done(self):
        # complete verification done

        self.update_verification_user()
        self.update_taxes_in_subscription()
        print "verification_user", self.c_verified_by_id

        self.generate_invoice_and_pay()

        try:
            meetingId = self.verification_call_process()
            self.create_training_request(meetingId)
            if not meetingId:
                v_remarks = self.c_invoice_id.c_verification_remarks
                self.c_invoice_id.sudo().write({'c_verification_remarks':"{}\nVerification call not scheduled, account manager is busy".format(v_remarks)})
        except:
            print "Error in Verification Call"

#         if not self.verification_call_process():
#             self.c_is_invoiced = False
#             self.c_verification_status = 'Problem Occurred in call process'
#             raise exceptions.ValidationError(_('The Account manager is busy'))
#             return
        
        if not self.activate_all_packages():
            self.c_is_invoiced = False
            raise exceptions.ValidationError(_('Packages activation failed'))
            return
        
        try:
            self.update_fps_in_invoice()
        except:
            print "Error in Updating"

        if self.c_auto_create_fptag:
            template = self.env['mail.template'].search([('name', '=', 'NowFloats MLC Verification Call Mail Success')],
                                                        limit=1)
        else:
            template = self.env['mail.template'].search([('name', '=', 'NowFloats Verification Call Mail Success')],
                                                        limit=1)

        if template:
            mail_id = template.send_mail(self.c_invoice_id.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})

        activation_id = "Last Invoice Paid: %s" % self.c_invoice_id
        self.partner_id.sudo().write({'c_alliance_id': activation_id})
        self.setting_rta_default()
        self.c_is_invoiced = True
        self.c_invoice_status = 'no'

        
        # Sending Email
        template = self.env['mail.template'].search([('name', '=', 'NowFloats Onboarding Call - AM')],
                                                    limit=1)
        if template:
            mail_id = template.send_mail(self.id)

        if self.c_onboarding_type == 'Video Call without FOS':
            template = self.env['mail.template'].search([('name', '=', 'NowFloats Onboarding Call - Customer - Video call')],
                limit=1)
            if template:
                mail_id = template.send_mail(self.id)

        if self.c_onboarding_type == 'Video Call with FOS':
            template = self.env['mail.template'].search([('name', '=', 'NowFloats Onboarding Call - Customer - Video call')],
                limit=1)
            if template:
                mail_id = template.send_mail(self.id)

        if self.c_onboarding_type == 'Audio Call without FOS':
            template = self.env['mail.template'].search([('name', '=', 'NowFloats Onboarding Call - Customer - Audio call')],limit=1)
            if template:
                mail_id = template.send_mail(self.id)

        if self.c_onboarding_type == 'Audio Call with FOS':
            template = self.env['mail.template'].search([('name', '=', 'NowFloats Onboarding Call - Customer - Audio call')],
                limit=1)
            if template:
                mail_id = template.send_mail(self.id)

        list_dates = []
        for line in self.recurring_invoice_line_ids:
            if line.c_invoice_date:
                a = line.c_validity * line.quantity
                dates = datetime.datetime.strptime(line.c_invoice_date, '%Y-%m-%d') + relativedelta(months=+int(a))
                list_dates.append(dates)
        if list_dates:
            self.recurring_next_date = min(list_dates)

        return self.action_subscription_invoice()

    def action_mlc_verification_done(self):
        self.update_verification_user()
        
        if self.c_sales_order_id.is_kitsune:
            self.action_verification_done()
        else:
            self.c_verification_call_status = True
            self.env.cr.execute("UPDATE sale_order "
                            "SET vc_status = 'Accepted with T&C' "
                            "WHERE id = {}"
                            .format(self.c_sales_order_id.id))

            template = self.env['mail.template'].search([('name', '=', 'NowFloats MLC Verfication')],
                                                    limit=1)
            if template:
                template.send_mail(self.id)
        return True
    
    def generate_invoice_and_pay(self):
        generated_invoice = self.recurring_invoice()
        self.c_invoice_id = generated_invoice
        # Register Payment
        self.register_payments_to_invoice(generated_invoice)

        self.env.cr.execute("UPDATE sale_order "
                            "SET vc_status = 'Accepted with T&C', "
                            "inv_status = 'Activation done & Invoice Created', "
                            "sub_inv_id = {} "
                            "WHERE id = {}"
                            .format(generated_invoice.id, self.c_sales_order_id.id))

        return True
    
    
    @api.multi
    def recurring_invoice(self):
        invoice_id = self._recurring_create_invoice()
        if self.c_tds_amount>0:
            self.c_tds_check = 'Yes'
        else:
            self.c_tds_check = 'No'
        if invoice_id:
            invoice = self.env['account.invoice'].search([('id', 'in', invoice_id)])
            
            values = {
                    'c_journal_id' : self.c_journal_id.id,
                    'c_payement_type' : self.c_payement_type,
                    'c_tds_check' : self.c_tds_check,
                    'c_paid_amount' : self.c_paid_amount,
                    'c_payment_ref' : self.c_payment_ref,
                    'c_payment_receive_date' : self.c_payment_receive_date,
                    'c_rta_hold_issue' : self.c_rta_hold_issue,
                    'c_rta_hold_description' : self.c_rta_hold_description,
                    'c_package_ext_req' : self.c_package_ext_req,
                    'c_rta_sent_status' : self.c_rta_sent_status,
                    'c_rta_status' : self.c_rta_status,
                    'c_phone_number' : self.c_phone_number,
                    'c_case_lh_mlc' : self.c_case_lh_mlc,
                    'c_case_mlc_mlc' : self.c_case_mlc_mlc,
                    'c_case_new_mlc' : self.c_case_new_mlc,
                    'c_case_renew_mlc' : self.c_case_renew_mlc,
                    'c_username' : self.c_username,
                    'c_primary_fp' : self.c_primary_fp,
                    'c_auto_create_fp': self.c_auto_create_fptag,
                    'c_verification_status' : 'Accepted with T&C',
                    'c_rta_done_date' : self.c_rta_done_date,
                    'c_verification_call_status' : True,
                    'c_reject_reason' : self.c_reject_reason,
                    'c_other_reject' : self.c_other_reject,
                    'c_verified_by_id' : self.c_verified_by_id.id,
                    'c_verification_remarks' : self.c_verification_remarks,
                    'c_rta_case0' : self.c_rta_case0,
                    'c_rta_case1' : self.c_rta_case1,
                    'c_rta_case2' : self.c_rta_case2,
                    'c_rta_case3' : self.c_rta_case3,
                    'c_call_links' : self.c_call_links,
                    'c_vc_cl1' : self.c_vc_cl1,
                    'c_vc_cl2' : self.c_vc_cl2,
                    'c_vc_cl3' : self.c_vc_cl3,
                    'c_vc_cl4' : self.c_vc_cl4,
                    'c_vc_cl5' : self.c_vc_cl5,
                    'c_vc_cl_all' : self.c_vc_cl_all,
                    'c_acc_mngr_email' : self.c_acc_mngr_email,
                    'c_acc_mngr' : self.c_acc_mngr,
                    'c_calendar_link' : self.c_calendar_link,
                    'c_acc_mngr_call_link' : self.c_acc_mngr_call_link,
                    'c_onboard_time' : self.c_onboard_time,
                    'c_onboarding_type' : self.c_onboarding_type,
                    'c_no_of_fps' : self.c_no_of_fps,
                    'c_call_hold_reason' : self.c_call_hold_reason,
                    'c_escalation_remarks' : self.c_escalation_remarks,
                    'c_dup_state' : self.c_dup_state,
                    'c_rta_hold_description' : self.c_rta_hold_description,
                    'c_sales_order_id' : self.c_sales_order_id.id,
                    'c_company_name': self.c_sales_order_id.c_company_name,
                    'c_sale_date': self.c_sales_order_id.confirmation_date,
                    'user_id': self.c_sales_order_id.user_id.id,
                    'date_invoice': datetime.date.today(),
                    'c_activation_date': datetime.date.today(),
                    'c_pkg_act_date':  datetime.date.today(),
                    'team_id': self.c_sales_order_id.team_id.id,
                    'welcome_call': self.welcome_call,
                    'c_sales_team_id': self.c_team_id.id,
                    'vc_followup_status':self.vc_followup_status,
                    'cfc_contract_id':  self.cfc_contract_id and self.cfc_contract_id.id or False,
                    'partner_username': self.partner_username,
                    'cfc_mlc_contract_id' : self.cfc_mlc_contract_id and self.cfc_mlc_contract_id.id or False,
                    'assigned_cfc_name': self.cfc_contract_id and self.cfc_contract_id.name and self.cfc_contract_id.name.name_related or False,
                    'c_gstn': self.partner_id.x_gstin or ''
                    }
            
            invoice.sudo().write(values)
            
            for payment_details in self.c_sales_order_id.c_add_payment_details:
                    payment_details.sudo().write({
                            'invoice_id' : invoice.id
                         })
        
        invoice.action_invoice_open()
#         invoice.action_invoice_paid()
        
#        invoice.action_invoice_paid()
        for lines in self.recurring_invoice_line_ids:
            if lines.c_sale_order_id == self.c_sales_order_id:
                lines.sudo().write({
                        'c_invoice_id': invoice.id,
                        'c_invoice_date': datetime.date.today()
                    })
                
        return invoice

    @api.multi
    def _prepare_invoice_lines(self, fiscal_position):
        self.ensure_one()
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position)
        
        all_lines = []
        
        for lines in self.recurring_invoice_line_ids:
            if (lines.c_sale_order_id == self.c_sales_order_id) and not lines.c_invoice_id:
                all_lines.append(lines)
#        all_lines = self.c_sales_order_id.order_line
        return [(0, 0, self._prepare_invoice_line(line, fiscal_position)) for line in all_lines]

    @api.multi
    def _prepare_invoice_line(self, line, fiscal_position):
        if 'force_company' in self.env.context:
            company = self.env['res.company'].browse(self.env.context['force_company'])
        else:
            company = line.analytic_account_id.company_id
            line = line.with_context(force_company=company.id, company_id=company.id)

        account = line.product_id.property_account_income_id
        if not account:
            account = line.product_id.categ_id.property_account_income_categ_id
        account_id = fiscal_position.map_account(account).id
        status = " "
        if line.c_status == 'renewalupsell':
            status = 'renewal'
        else:
            status = 'new'
        
        lc_branch_id = False
        lc_employee_id = False
        sp_employee_id = False
        lc_id = line.c_sale_order_id.c_lead_creator_id
        if lc_id:
            employee = self.env['hr.employee'].search([('user_id', '=', lc_id.id)])
            print "employee", employee
            if employee:
                lc_employee_id = employee[0].id
                lc_branch_id = employee[0].branch_id.id
          
        sp_employee = self.env['hr.employee'].search([('user_id', '=', line.c_sale_order_id.user_id.id)])
        if sp_employee:
            sp_employee_id = sp_employee[0].id
        
        print "lc_employee_id", lc_employee_id
        print "lc_branch_id", lc_branch_id
        print "sp_employee_id", sp_employee_id
        print "line.c_sale_order_id.c_sp_branch", line.c_sale_order_id.c_sp_branch
        
        invoice_line = {
            'name': line.name,
            'account_id': account_id,
            'account_analytic_id': line.c_cost_center.id,
            'price_unit': line.price_unit or 0.0,
            'discount': line.discount,
            'quantity': line.quantity,
            'uom_id': line.uom_id.id,
            'c_pkg_validity': line.c_validity,
            'c_status': status,
            'product_id': line.product_id.id,
            'c_fptags_id': line.c_fptags_id.id,
            'c_tc_branch': lc_branch_id,
            'c_tc_emp_id': lc_employee_id,
            'c_sp_branch': line.c_sale_order_id.c_sp_branch.id,
            'c_sp_emp_id': sp_employee_id,
            'invoice_line_tax_ids': [(6, 0, line.c_tax_ids.ids)]
        }
        print invoice_line
        
        if self.asset_category_id:
            asset_category = self.asset_category_id
        elif line.product_id:
            product_id = line.product_id
            asset_category = product_id.product_tmpl_id.deferred_revenue_category_id

            # Set corresponding account
        if asset_category:
            invoice_line['asset_category_id'] = asset_category.id
            account = fiscal_position.map_account(asset_category.account_asset_id)
            invoice_line['account_id'] = account.id
        
        return invoice_line
    
    def register_payments_to_invoice(self, invoice):   
        account_id = self._compute_destination_account_id(invoice)
        print ">>>>>>>>>>>>>", account_id
        
        for account_payment in self.c_account_payment_ids:
            currency_id = account_payment.journal_id.currency_id or self.company_id.currency_id
            # Set default payment method (we consider the first to be the default one)
            payment_methods = account_payment.journal_id.inbound_payment_method_ids or account_payment.journal_id.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            print ">>>>>", payment_methods
            print ">>>>>>>>>>>>", payment_method_id
            vals = {
                    'payment_method_id': payment_method_id.id,
                    'currency_id': currency_id.id,
                    'invoice_ids': (4, invoice.id, None),
                    'destination_account_id': account_id
                }
            account_payment.sudo().write(vals)
            print ">>>>>", account_payment
            if account_payment.state != 'posted':
                account_payment.post()
        
            for line in account_payment.move_line_ids:
                if line.debit == 0.0:
                    print ">>>>>>>>>>>", line
                    print ">>>>>>>>>>>>>", invoice.number
                    invoice.assign_outstanding_credit(line.id)

    def _compute_destination_account_id(self, invoice):
        if invoice:
            return invoice.account_id.id
        return self.partner_id.property_account_receivable_id.id

    @api.multi
    def activate_website_mlc(self):
        param = self.env['ir.config_parameter']
        activateWebsite = param.search([('key', '=', 'activateWebsiteMLC')])
        activateWebsite_url = activateWebsite.value
        authorize_createWebsite = param.search([('key', '=', 'authorizeCreateWebsite')])
        line_rec = self.env['sale.subscription.line'].sudo().search([('c_sale_order_id','=',self.c_sales_order_id.id)],limit=1)
        querystring = {"websiteid": line_rec.c_fptags_id.name
                       }

        headers = {
            'content-type': "application/json",
            'Authorization': authorize_createWebsite.value,
        }
        response = requests.request("GET", activateWebsite_url, headers=headers, params=querystring)
        response = json.loads(response.text)
        print "##################response",response
        return response
    
        
    def activate_all_packages(self):
        if self.c_auto_create_fptag:
            if self.c_sales_order_id.is_corporate_website:
                act_id = self.activate_website_mlc()
                self.env.cr.execute("UPDATE "
                                    "sale_subscription_line "
                                    "SET c_activation_id = {} "
                                    "WHERE c_sale_order_id = {}".format(act_id,self.c_sales_order_id.id))
                return True
            elif self.c_sales_order_id.is_kitsune:
                return True
            else:
                return self.generate_and_activate_fptags()
        
        print "Validate all packages"
        if not self.validate_all_fptags():
            return

        if self.c_sales_order_id.claim_id:
            self.env.cr.execute("UPDATE "
                                "sale_subscription_line "
                                "SET c_activation_id = 'Activated From Manage' "
                                "WHERE c_sale_order_id = {}".format(self.c_sales_order_id.id))
            return True

        lines_to_activate = [lines for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id and lines.c_activation_id == False]

        return self.activate_lines(lines_to_activate)
    

    def generate_and_activate_fptags(self):
        if self.c_case_renew_mlc:
            return self.renew_mlc_fps()
        
        print "AUTO GENERATE FPTAGs"
        address = "{} {}".format(self.partner_id.street, self.partner_id.street2)
        
        # to be replace by a new field
        username = self.c_username
        
        mobile = str(self.partner_id.mobile)
        if mobile and mobile[0] == '+':
            # making +91 12345 to +91
            mobile = mobile[3:].strip()
        
        lines_to_generate = [lines for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id and not lines.c_fptags_id and lines.c_activation_id == False]
        if len(lines_to_generate) == 0:
            self.c_is_invoiced = True
            self.c_invoice_status = 'no'
            print "INVOICE ALREADY DONE"
            return True
        total_lines = len(lines_to_generate)
        amount = self.c_sales_order_id.amount_total
        base_amount = self.c_sales_order_id.amount_untaxed
        tax_amount = self.c_sales_order_id.amount_tax
        discount = lines_to_generate[0].discount
        packageId = lines_to_generate[0].product_id.c_package_id
        
        param = self.env['ir.config_parameter']
        clientIdForActivatingPackage = param.search([('key', '=', 'clientIdForGeneratingFps')])
        createMultiFpUrl = param.search([('key', '=', 'createMultiFpUrl')])
        
        fptag = None
        if self.c_primary_fp:
            fptag = str(self.c_primary_fp).upper()
        
        data_dic = {
            "clientId": clientIdForActivatingPackage.value,
            "domainIntegrationType": 0,
            "orgAddress": address,
            "orgCity": str(self.partner_id.c_city_id.name) or "",
            "orgContactEmail": str(self.partner_id.email),
            "orgContactNumber": str(mobile),
            "orgCountry": str(self.partner_id.country_id.name) or "India",
            "orgDesc": "",
            "orgName": str(self.partner_id.name),
            "pwd": str(mobile),
            "rootCNAME": [
            ""
            ],
            "username": str(username),
            "BaseAmount": str(base_amount),
            "TaxAmount": str(tax_amount),
            "ExpectedAmount": str(amount),
            "IsPaid": True,
            "currencyCode": "INR",
            "customerSalesOrderRequest": {
                "_nfInternalERPId": str(self.c_sales_order_id.name),
                "customerEmailId": str(self.partner_id.email),
                "discountPercentageValue": float(discount),
                "invoiceStatus": 0,
                "paymentMode": 0,
                "paymentTransactionStatus": 0,
                "purchasedUnits": int(lines_to_generate[0].quantity),
                "sendEmail": True
            },
            "packageId": str(packageId),
            "totalFPs": str(int(self.c_no_of_fps)),
            "type": 0,
            "validityInMths": float(lines_to_generate[0].c_validity),
            "fpTag": fptag
        }
        
        data = json.dumps(data_dic)
        
        print ">>>>>>>>>>> ", data
        response = requests.put(createMultiFpUrl.value, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"})
        print ">>>>>>>>>", response.status_code
        
        if int(response.status_code) != 200:
            self.c_verification_status = 'Not able to generate FPTAGs'
            return False
        
        generated_fptags = json.loads(response.text)
        if generated_fptags['Tags']:
            generated_fptags = generated_fptags['Tags']
        counter = 0
        for tag_name in generated_fptags:
            vals = {
                'name': tag_name.upper(),
                'state': 'valid',
                'customer_id': self.partner_id.id
            }
            fptag_id = self.env['ouc.fptag'].create(vals)
            lines_to_generate[counter].sudo().write({'c_fptags_id': fptag_id.id,
                'c_activation_id': 'MLC_CASE'
            })
            counter = counter + 1
            if counter >= total_lines:
                break
        
        return self.activate_mlc_fps()
 
    
    def renew_mlc_fps(self):
        lines_without_fps = [lines for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id and not lines.c_fptags_id and lines.c_activation_id == False]
        
        if lines_without_fps:
            raise exceptions.ValidationError(_('It''s an MLC renewal case, Every activation line should have a FPTAG'))
        
        return self.activate_mlc_fps()
        
    def activate_mlc_fps(self):
        lines_to_activate = [lines for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id and lines.c_fptags_id and lines.c_activation_id == False]
        fptag_ids = [line.c_fptags_id for line in lines_to_activate]
        
        if not self.valifate_fptags(fptag_ids):
            return
          
        return self.activate_lines(lines_to_activate)
    
    def validate_all_fptags(self):
        fptag_ids = [lines.c_fptags_id for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id]
        return self.valifate_fptags(fptag_ids)
    
    def valifate_fptags(self,fptag_ids):
        for fptag in fptag_ids:
            print ">>>>>>>", fptag
            if not fptag.validate_fptag_from_api():
                self.c_verification_status = 'FPTAG \'{}\' is not valid '.format(fptag.name)
                return False
            if not fptag.get_fp_external_id():
                self.c_verification_status = 'Cannot get details for FPTAG \'{}\''.format(fptag.name)
                return False
        return True    
    
    def activate_lines(self, lines_to_activate):
        if not lines_to_activate or self.c_sales_order_id.claim_id:
            return True
        
        for line in lines_to_activate:
            numberOfActivation = int(line.product_id.c_activation_req * line.quantity)
            totalValidityInMths = int(line.c_validity) * line.quantity
            singleValidityInMths = int(totalValidityInMths/numberOfActivation)
            
            print "numberOfActivation", numberOfActivation
            print "totalValidityInMths", totalValidityInMths
            print "singleValidityInMths", singleValidityInMths
            
            packageSaleTransactionType = 1
            if line.c_status == 'new':
                packageSaleTransactionType = 0
            
            for activationCount in range(0,numberOfActivation):
                print "activationCount", activationCount
                self.activate_line(line, packageSaleTransactionType, singleValidityInMths, numberOfActivation)
                packageSaleTransactionType = 1

            
        return True
    
    def activate_line(self, line, packageSaleTransactionType, validityInMths, numberOfActivation):
        print "Activate packages"
        param = self.env['ir.config_parameter']
        markFloatingPointAsPaidUrl = param.search([('key', '=', 'markFloatingPointAsPaidUrl')])
        clientIdForActivatingPackage = param.search([('key', '=', 'clientIdForGeneratingFps')])
        
        if not self.c_auto_create_fptag:
            clientIdForActivatingPackage = param.search([('key', '=', 'clientIdForActivatingPackage')])

        activation_data = {
                                "BaseAmount": str(float(line.price_subtotal / numberOfActivation)),
                                "ClientId": clientIdForActivatingPackage.value,
                                "ExpectedAmount":str(line.c_price_total / numberOfActivation),
                                "ExternalSourceId":'',
                                "FpId":str(line.c_fptags_id.externalSourceId),
                                "FpTag":str(line.c_fptags_id.name),
                                "IsPaid":True,
                                "TaxAmount": str(line.c_price_tax / numberOfActivation),
                                "currencyCode":'INR',
                                "type":int(packageSaleTransactionType),
                                "packages":[{
                                    "packageId":str(line.product_id.c_package_id),
                                    "quantity": int(line.quantity)
                                    }],
                                "customerSalesOrderRequest":
                                    {
                                     "_nfInternalERPId":str(line.c_sale_order_id.name),
                                     "_nfInternalERPSaleDate":str(line.c_sale_date),
                                     "customerEmailId":self.partner_id.email,
                                     "discountPercentageValue":line.discount,
                                     "invoiceStatus":0,
                                     "paymentMode":0,
                                     "paymentTransactionStatus":0,
                                     "purchasedUnits":int(line.quantity),
                                     "sendEmail":False
                                    }
                            }
        data = json.dumps(activation_data)
            
        response = requests.post(markFloatingPointAsPaidUrl.value, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"})
        if int(response.status_code) != 200:
            self.c_verification_status = 'Package Activation unsuccessful'
            return False
        if not response.text:
            self.c_verification_status = 'Package Activation unsuccessful'
            return False    
        
        activ_id = json.loads(response.text)
        line.sudo().write({'c_activation_id' : activ_id})
        
        return True
    
    def verification_call_process(self):
        lines_to_activate = [lines for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id and not lines.c_activation_id]
        if self.c_auto_create_fptag:
            return True
        if not lines_to_activate:
            return True

        fptag = lines_to_activate[0].c_fptags_id.name
        
        param = self.env['ir.config_parameter']
        setMeetingOnTimeWithFpUrl = param.search([('key', '=', 'setMeetingOnTimeWithFpUrl')])
        setMeetingOnTimeWithFpClientId = param.search([('key', '=', 'setMeetingOnTimeWithFpClientId')])
        
        description = "Onboarding meeting has been scheduled for {}".format(fptag)
        onboard_time = datetime.datetime.strptime(self.c_onboard_time, '%Y-%m-%d %H:%M:%S') + relativedelta(minutes = 330)
        onboard_time = onboard_time.strftime("%Y-%m-%d %H:%M:%S")
        #ob_date = onboard_time.strftime("%b %d, %Y")
        #ob_time = onboard_time.strftime("%X")
        acc_mngr = self.c_acc_mngr
        acc_call_link = self.c_acc_mngr_call_link
        body = "Thank you for choosing NowFloats as your preferred business partner. \n\nAs an important first step please be informed of your training schedule with {} over https://appear.in \n\nPlease keep 1 hour for the training to ensure that we are able to take you through all components of the product.\n\nPlease click on the link to join the call {} \n\nAlso ensure that you have the following things with you during the call\n1- Head phones \n2- Laptop/Desktop \n3- Good Internet connectivity \n\nIf you need any further clarifications, talk to {}, your Account Manager.\n\n\n\n\n"
        body = body.format(acc_mngr, acc_call_link, acc_mngr)

        onboarding_type = self.c_onboarding_type
        partner_username = self.partner_username
        user_email = self.c_acc_mngr_email
        skip_calendar = False

        # https://ria.withfloats.com/api/RIASupportTeam/SetMeetingOnTimeWithFP
        # 5DD5965115884A2291B6A06C37B47F6AF0FAA628D40CD9814A794137F6A
        setMeeting_request_url = "{}?fpTag={}&clientId={}&meetingDateTime={}&summary={}&description={}&slotDurationMins=45&location={}&" \
                                 "meetingType=ONBOARDING&salesPersonName={}&salesPersonEmail={}&skipCalender={}&memType=TA"\
            .format(setMeetingOnTimeWithFpUrl.value, fptag, setMeetingOnTimeWithFpClientId.value,
                    onboard_time,description,body,onboarding_type,partner_username,user_email,skip_calendar)
        print "bom_url", setMeeting_request_url
        response_obj = urllib.urlopen(setMeeting_request_url) 
        obm_encoder = response_obj.read().decode('utf-8')
        print "=========obm_encoder==========a==",obm_encoder
        if not obm_encoder or not 'MeetingId' in obm_encoder:
            skip_calendar = True
            setMeeting_request_url = "{}?fpTag={}&clientId={}&meetingDateTime={}&summary={}&description={}&slotDurationMins=45&location={}&" \
                                     "meetingType=ONBOARDING&salesPersonName={}&salesPersonEmail={}&skipCalender={}&memType=TA" \
                .format(setMeetingOnTimeWithFpUrl.value, fptag, setMeetingOnTimeWithFpClientId.value,
                        onboard_time, description, body, onboarding_type, partner_username, user_email, skip_calendar)
            response_obj = urllib.urlopen(setMeeting_request_url)
            obm_encoder = response_obj.read().decode('utf-8')
            print "============obm_encoder======b===========", obm_encoder
            if not obm_encoder:
                return False
            template = self.env['mail.template'].search([('name', '=', 'Onboarding meeting scheduled')],
                                                        limit=1)
            if template:
                mail_id = template.send_mail(self.id)
                self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})
        meetingId = json.loads(obm_encoder).get('MeetingId', None)
        return meetingId

    @api.multi
    def get_mlc_chc_profile(self):

        param = self.env['ir.config_parameter']
        UpdateCHCDetailsUrl = param.search([('key', '=', 'getMlcChCProfileForBranchesUrl')])
        UpdateCHCDetailsClientId = param.search([('key', '=', 'clientIdForGeneratingFps')])
        type = 'MLC'

        url = UpdateCHCDetailsUrl.value

        querystring = {"clientId": UpdateCHCDetailsClientId.value,
                       "profileAccessType" : 3,
                       "parentProfileAccessType" : 1,
                       "offset" : 0,
                       "pageSize" : 1000000000
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        response = response.text
        if response:
            response = json.loads(response)
            if 'Result' in response and response['Result']:
                result = response['Result']
                cfc = [val['username'].encode('utf-8') for val in result['details']]

                self.env.cr.execute("SELECT emp.id, '{}' FROM hr_employee emp "
                                     "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                                     "WHERE res.active = True AND emp.c_nf_chc = ANY(ARRAY{}) "
                                     "AND emp.id NOT IN (SELECT name FROM cfc_contract WHERE type = 'MLC')"
                                    .format(type, cfc))
                qry_result = self.env.cr.fetchall()
                if qry_result:
                   self.env.cr.executemany("INSERT INTO cfc_contract(name, type) VALUES (%s, %s)", qry_result)

        return True

    @api.onchange('cfc_contract_id')
    def onchange_assigned_cfc(self):
        if self.cfc_contract_id:
            acc_mngr = ''
            fptag_name = ''
            fps = []
            param = self.env['ir.config_parameter']
            UpdateCHCDetailsUrl = param.search([('key', '=', 'getAssignedCHCForPartnerApiUrl')])
            UpdateCHCDetailsClientId = param.search([('key', '=', 'getChCProfileForBranchesClientId')])

            url = UpdateCHCDetailsUrl.value

            querystring = {"clientId": UpdateCHCDetailsClientId.value,
                           "offset" : 0
                           }

            so_id = self.c_sales_order_id and self.c_sales_order_id.id or False

            subscription = self.env['sale.subscription'].search([('partner_id', '=', self.partner_id.id),('c_sales_order_id', '=', so_id)], limit = 1)

            if not subscription:
                return {}

            subscription_id = subscription.id

            self.env.cr.execute("SELECT fp.name AS fptag "
                                "FROM sale_subscription_line ssl "
                                "INNER JOIN ouc_fptag fp ON ssl.c_fptags_id = fp.id "
                                "WHERE ssl.analytic_account_id = {} AND ssl.c_sale_order_id = {}"
                                .format(subscription_id, so_id))

            fptags_ids = self.env.cr.fetchall()

            fptags = map(lambda x : x[0], fptags_ids)

            payload = {
	                    "fptags": fptags,
	                    "usernames" : None,
	                    "branchIds": None
                        }

            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache",
            }

            data = json.dumps(payload)

            response = requests.request("POST", url, data=data, headers=headers, params=querystring)
            response = response.text
            if response:
                result = json.loads(response)['Result']
                if 'CustomerHappinessConsultants' in result and result['CustomerHappinessConsultants']:
                    for val in result['CustomerHappinessConsultants']:
                        fptag = val['FpTag']
                        fps.append(fptag)
                        username = val['username']
                        cfc_emp_id = self.env['hr.employee'].search([('c_nf_chc', '=', username)], limit=1)
                        if cfc_emp_id:
                            cfc = cfc_emp_id.name_related
                            if not acc_mngr:
                                acc_mngr = cfc
                            else:
                                acc_mngr = acc_mngr + ',' + cfc

                            if fptag_name:
                                fptag_name = fptag
                            else:
                                fptag_name = fptag_name + ',' + fptag

                    final_fptag = [fp for fp in fptags if fp not in fps]


                    if final_fptag:
                        msg = "Account manager {} is already assigned to {}. \n " \
                              "The new account manager will be assigned to {}"\
                            .format(acc_mngr, fps, final_fptag)

                        warning = {'title': _('Warning'), 'message': _(msg), }

                        return {'warning': warning}

                    else:
                        msg = "Account manager {} is already assigned to {}"\
                            .format(acc_mngr, fps)
                        warning = {'title': _('Warning'), 'message': _(msg), }

                        value = {'cfc_contract_id': False}

                        return {'warning': warning, 'value': value}

        return {}

    @api.multi
    def get_chc_profile(self):
        if self.c_auto_create_fptag:
            self.get_mlc_chc_profile()
            return True

        contract_id = self.id

        self.env.cr.execute("DELETE FROM cfc_contract WHERE contract_id = {}".format(contract_id))

        user_id = self.c_sales_order_id.user_id and self.c_sales_order_id.user_id.id or False

        emp_obj = self.env['hr.employee'].search([('user_id', '=', user_id)], limit = 1)

        server_branch_id = emp_obj.branch_id.server_branch_id

        param = self.env['ir.config_parameter']
        UpdateCHCDetailsUrl = param.search([('key', '=', 'getChCProfileForBranchesUrl')])
        UpdateCHCDetailsClientId = param.search([('key', '=', 'getChCProfileForBranchesClientId')])
        type = 'FOS'

        url = UpdateCHCDetailsUrl.value

        querystring = {"clientId": UpdateCHCDetailsClientId.value, 'profileType': 3}

        payload = [server_branch_id]
        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        data = json.dumps(payload)

        response = requests.request("POST", url, data=data, headers=headers, params=querystring)
        response = response.text
        if response:
            response = json.loads(response)
            if response:
                result = sorted(response, key=lambda user: (user['accountsAssignedCount']))
                for val in result:
                    cfc = val['username'].encode('utf-8')
                    accountsAssignedCount = val['accountsAssignedCount']
                    self.env.cr.execute("SELECT emp.id FROM hr_employee emp "
                                        "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                                    "WHERE res.active = True AND emp.c_nf_chc = '{}' "
                                    "AND emp.id NOT IN (SELECT name FROM cfc_contract WHERE contract_id = {})"
                                    .format(cfc, contract_id))
                    qry_result = self.env.cr.fetchall()
                    if qry_result:
                        map_result = map(lambda x: (x[0], accountsAssignedCount, contract_id, type), qry_result)
                        self.env.cr.executemany("INSERT INTO cfc_contract(name, account_assigned_count, contract_id, type) VALUES (%s, %s, %s, %s)", map_result)
                    else:
                        cfc_emp_id = self.env['hr.employee'].search([('c_nf_chc', '=', cfc)], limit = 1)
                        if cfc_emp_id:
                            self.env.cr.execute("UPDATE cfc_contract "
                                            "SET account_assigned_count = {} "
                                            "WHERE name = {} AND contract_id = {} AND type = '{}' "
                                                .format(accountsAssignedCount, cfc_emp_id.id, contract_id, type))
        return True

    @api.multi
    def update_chc_details_for_partner_by_fptag(self, fptags):

        if self.c_auto_create_fptag:
            cfc_obj = self.cfc_mlc_contract_id and self.cfc_mlc_contract_id.name or False
        else:
            cfc_obj = self.cfc_contract_id and self.cfc_contract_id.name or False
        if not cfc_obj:
            return False
        emp_email = cfc_obj.work_email
        emp_cfc = cfc_obj.c_nf_chc

        param = self.env['ir.config_parameter']
        UpdateCHCDetailsUrl = param.search([('key', '=', 'UpdateCHCDetailsForPartnerByFPTagUrl')])
        UpdateCHCDetailsClientId = param.search([('key', '=', 'getFpDetailsApiClientId')])
        if self.c_auto_create_fptag:
            UpdateCHCDetailsClientId = param.search([('key', '=', 'clientIdForGeneratingFps')])

        url = UpdateCHCDetailsUrl.value

        querystring = {"clientId": UpdateCHCDetailsClientId.value}

        payload = {"email": emp_email,
                   "floatingPointTags": fptags,
                   "userId": emp_cfc
                   }

        data = json.dumps(payload)

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"        }

        response = requests.request("POST", url, data=data, headers=headers, params=querystring)

        try:
            if not self.c_auto_create_fptag:
               self.assign_member_to_fp_manually(fptags[0], emp_cfc)
        except:
            pass
        return True

    @api.multi
    def assign_member_to_fp_manually(self, fptag, emp_cfc):

        param = self.env['ir.config_parameter']
        assignMemberToFPManualApiUrl = param.search([('key', '=', 'assignMemberToFPManualApiUrl')])
        UpdateCHCDetailsClientId = param.search([('key', '=', 'getFpDetailsApiClientId')])

        url = assignMemberToFPManualApiUrl.value

        self.env.cr.execute("SELECT (SELECT work_email FROM hr_employee WHERE id = emp.coach_id) AS reporting_head_email,"
                            "(SELECT work_email FROM hr_employee WHERE id = emp.parent_id) AS manager_email "
                            "FROM hr_employee emp "
                            "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                            "WHERE res.active = True AND emp.c_nf_chc = '{}'".format(emp_cfc))
        ccEmails = ";".join(val for val in self.env.cr.fetchone())

        bccEmails = 'verification@nowfloats.com;mohit.katiyar@nowfloats.com;nitin@nowfloats.com;rajeev.goyal@nowfloats.com;rajat.anand@nowfloats.com'

        querystring = {"clientId":  UpdateCHCDetailsClientId.value,
                       "fpTag": fptag,
                       "fpClientId": UpdateCHCDetailsClientId.value,
                       "memberPatnerUsername": emp_cfc,
                       "sendNotification": True,
                       "ccEmails": ccEmails,
                       "bccEmails": bccEmails
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"}

        response = requests.request("GET", url, headers=headers, params=querystring)

        self.create_zendesk_ticket({'fptag': fptag})
        return True

    def create_zendesk_ticket(self, data):

        fptag = data.get('fptag', '')
        if not fptag:
            return False

        param = self.env['ir.config_parameter']
        zendeskCreateTicketUrl = param.search([('key', '=', 'zendeskCreateTicketUrl')])
        url = zendeskCreateTicketUrl.value

        subject  = 'Critical : FP has been assigned to you for vidya session'
        comment = { "body": "Critical : FP has been assigned to you for vidya session"}
        assignee_email = 'resham.kathuria@nowfloats.com'

        payload =  {"tickets": [  {  "subject":  subject,
			                         "comment":  comment,
			                         "priority": "normal",
			                         "assignee_email": assignee_email,
			                         "external_id": fptag,
			                         #"collaborator_ids" :  []
				                    }
		   	                    ]
                    }

        data = json.dumps(payload)

        headers = {
            'content-type': "application/json",
            'authorization': "Basic Y3VzdG9tZXIuc3VwcG9ydEBub3dmbG9hdHMuY29tOm5vd2Zsb2F0c0BzdXBwb3J0"
        }

        response = requests.request("POST", url, data=data, headers=headers)
        return True

    def update_fps_in_invoice(self):
        if not self.c_invoice_id:
            return
        lines_to_activate = [lines for lines in self.recurring_invoice_line_ids if lines.c_sale_order_id == self.c_sales_order_id and lines.c_activation_id != False]

        fptags = []
        if not lines_to_activate:
            return
        ctr = 0
        for line in self.c_invoice_id.invoice_line_ids:
            if not lines_to_activate or not lines_to_activate[ctr]:
                continue
            
            if not lines_to_activate or not lines_to_activate[ctr].c_fptags_id:
                continue

            line.sudo().write({'c_fptags_id':lines_to_activate[ctr].c_fptags_id.id})
            fptags.append(lines_to_activate[ctr].c_fptags_id.name)
            ctr = ctr + 1
	try:
           self.update_chc_details_for_partner_by_fptag(fptags)
	except:
	   pass
        return True

    @api.multi
    def create_training_request(self, meetingId):
        if self.c_auto_create_fptag:
            return True

        param = self.env['ir.config_parameter']
        createTrainingRequestForCustomerApiUrl = param.search([('key', '=', 'createTrainingRequestForCustomerApiUrl')])
        UpdateCHCDetailsClientId = param.search([('key', '=', 'getFpDetailsApiClientId')])

        url = createTrainingRequestForCustomerApiUrl.value

        querystring = {"clientId": UpdateCHCDetailsClientId.value}

        self.env.cr.execute("""SELECT fp.name, fp."externalSourceId"
         FROM sale_subscription_line ssl
         LEFT JOIN ouc_fptag fp ON ssl.c_fptags_id = fp.id
         WHERE ssl.analytic_account_id = {} AND c_sale_order_id = {}
         AND ssl.c_fptags_id IS NOT NULL AND ssl.c_activation_id IS NULL LIMIT 1"""
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

        payload = { '_id' : None,
                    'clientId' : "A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E",
                    'username' : partner_username,
                    "customerDetails" : {"name" : customer_name,
                                         "address" : customer_address,
                                         "email" : customer_email,
                                         "phoneNumber" : customer_mobile,
                                         "businessName" : business_name,
                                         "alternatePhoneNumber" : None,
                                         "city" : customer_city,
                                         "state" : customer_state,
                                         "GSTN" : customer_gstn,
                                         "country" : customer_country,
                                         "enterpriseUsername" : None,
                                         "storeCount" : 1,
                                         "FpTags" : [fptag],
                                         "FpIds" : [fp_id],
                                         "ParentId" : None,
                                         "isEnterpriseCustomer" : False,
                                         "singleStoreSeedFpTagForEnterprise" : None,
                                         "isExistingSingleStoreCustomer" : False
                                         },
                     "latestMeetingScheduledDate" : "0001-01-01T00:00:00",
                     "transactionChannel" : 0,
                     "trainingStatus" : 0,
                     "trainingParameters" : None,
                     "isTrainingScheduled" : False,
                     "dispositionReason" : None,
                     "remarks" : None,
                     "callRecordingLink" : call_recording_links,
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
        
    
    def setting_rta_default(self):
        print "RTA RESET....."
        self.c_verification_status =False
        self.c_rta_sent_status = False
        self.c_rta_status = False
        self.c_phone_number = None
        self.c_rta_done_date = None
        self.c_verification_call_status = False
        self.c_reject_reason = None
        self.c_other_reject = None
        self.c_verified_by_id = None
        self.c_verification_remarks = None
        self.c_rta_case0 = False
        self.c_rta_case1 = True
        self.c_rta_case2 = False
        self.c_rta_case3 = False
        self.c_call_links = None
        self.c_vc_cl1 = False
        self.c_vc_cl2 = False
        self.c_vc_cl3 = False
        self.c_vc_cl4 = False
        self.c_vc_cl5 = False
        self.c_vc_cl_all = False
        self.c_acc_mngr_email = None
        self.c_acc_mngr = None
        self.c_calendar_link = None
        self.c_acc_mngr_call_link = None
        self.c_journal_id = None
        self.c_payement_type = None
        self.c_tds_check = 'No'
        self.c_paid_amount = None
        self.c_payment_ref = None
        self.c_payment_receive_date = None
        self.c_no_of_fps = None
        self.c_onboard_time = None
        self.c_onboarding_type = None
        
        self.c_reject_reason = None
        self.c_other_reject = None
        self.c_bank_account = None
        self.c_bank_ifsc = None
        self.c_bank_id = False
        self.c_bank_account_holder = None
        self.welcome_call = False
        self.vc_followup_status = False
        self.cfc_contract_id = False
        self.partner_username = False
        self.cfc_mlc_contract_id = False
        
        for account_payment in self.c_account_payment_ids:
            account_payment.sudo().write({
                'c_subscription_id': False,
                'c_from_subscription': True
                })
    
    @api.multi
    def action_subscription_invoice(self):
        analytic_ids = [line.c_cost_center.id for line in self.recurring_invoice_line_ids]
        analytic_ids.append(self.analytic_account_id.id)
        orders = self.env['sale.order'].search_read(domain=[('subscription_id', 'in', self.ids)], fields=['name'])
        order_names = [order['name'] for order in orders]
        invoices = self.env['account.invoice'].search([('invoice_line_ids.account_analytic_id', 'in', analytic_ids),
                                                       ('partner_id', '=', self.partner_id.id),
                                                       ('origin', 'in', self.mapped('code') + order_names)])
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.invoice",
            "views": [[self.env.ref('account.invoice_tree').id, "tree"],
                      [self.env.ref('account.invoice_form').id, "form"]],
            "domain": [["id", "in", invoices.ids]],
            "context": {"create": False},
            "name": "Invoices",
        }
        
    @api.multi
    def action_subscription_sale_order(self):

        analytic_ids = [line.c_cost_center.id for line in self.recurring_invoice_line_ids]
        analytic_ids.append(self.analytic_account_id.id)
        sale_orders = self.env['sale.order'].search([('project_id', 'in', analytic_ids),
                                                                    ('partner_id', '=', self.partner_id.id),
                                                                    ('subscription_management', '!=', False),
                                                                    ('state', 'in', ['draft', 'sent', 'sale', 'done'])])
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[self.env.ref('sale.view_order_tree').id, "tree"],
                      [self.env.ref('sale.view_order_form').id, "form"]],
            "domain": [["id", "in", sale_orders.ids]],
            "context": {"create": False},
            "name": "Sale Orders",
        }
        
    def action_esclation(self):
        # Email trigger
        
        self.c_sales_order_id.sudo().write({
                        'c_escalation_status': True,
                        'c_escalation_reason': self.c_call_hold_reason,
                        'c_escalation_remarks': self.c_escalation_remarks,
                        'vc_status': 'Escalated to Sales'
                    })
        
        self.c_verification_status = 'Escalated to Sales'
        self.c_rta_status = 'On Hold'
        self.c_verification_call_status = True
        self.update_verification_user()
        template = self.env['mail.template'].search([('name', '=','NowFloats Verification Call Mail On Hold')], limit=1)
        if template:
            template.send_mail(self.id)

    
    def action_rta_cancel(self):
        # Email trigger
        
        # Email Trigger to finance
        print"-----",self.c_bank_account
        
        reject_reason = self.c_reject_reason
        if reject_reason == "Others":
            reject_reason = self.c_other_reject
            
        self.c_verification_call_status = True
        self.c_bank_details=[(0,0,{'bankaccountnumber':self.c_bank_account,
                                  'bank_id':self.c_bank_id.id,
                                  'ifsccode':self.c_bank_ifsc,
                                  'accountholder':self.c_bank_account_holder,
                                  'reason_to_reject': reject_reason
                                  })]
        print "Resetting....."
        self.setting_rta_default()
        
        self.c_verification_status = 'VC Rejected'
        self.c_is_invoiced = True
        self.c_invoice_status = 'no'
        self.update_verification_user()

        self.env.cr.execute("UPDATE sale_order "
                            "SET vc_status = 'VC Rejected' "
                            "WHERE id = {}"
                            .format(self.c_sales_order_id.id))

        template = self.env['mail.template'].search([('name', '=', 'NowFloats Verification Call Mail Rejected')],
                                                    limit=1)
        if template:
            template.send_mail(self.id)

    @api.multi
    def name_get(self):
        res = []
        for sub in self:
            name = '%s - %s' % (sub.code, sub.partner_id.name) if sub.code else sub.partner_id.name
            if sub.c_sales_order_id and sub.c_sales_order_id.team_id:
                sales_team = sub.c_sales_order_id.team_id.name
                res.append((sub.id, '%s/%s' % (sales_team, name)))
            else:
                res.append((sub.id, '%s/%s' % (sub.template_id.code, name) if sub.template_id.code else name))
        return res


class ouc_subscription_template(models.Model):
    _inherit = 'sale.subscription.template'

    c_account_email = fields.Char(string='Account email')
    c_auto_create_fptag = fields.Boolean(string='Auto Create FPTAG')
    c_template_id = fields.Many2one('sale.quote.template', string='Quotation template')

    c_type = fields.Selection([('new', 'Only For New'), ('renewalupsell', 'Only for Renewal/Upsell'),('all','For All')], string='Template Type', default='all')
    presale = fields.Boolean('Presale')
    single_store = fields.Boolean('Single Store')
    
    def write(self, vals):
        res = super(ouc_subscription_template, self).write(vals)
        
        if self.c_template_id:
            qoute_name = "[{}] {}".format(self.code, self.name)
            self.c_template_id.sudo().write({'name': qoute_name, 'contract_template': self.id, 'c_type': self.c_type, 'active' : self.active,'single_store': self.single_store})
        
        return res
    
    @api.model
    def create(self, vals):
        rec = super(ouc_subscription_template, self).create(vals)
        
        subscription_template_lines = rec.subscription_template_line_ids
        order_lines = []
        for mand_line in subscription_template_lines:
            order_lines.append((0, 0, {
                                'product_id': mand_line.product_id.id,
                                'uom_id': mand_line.uom_id.id,
                                'name': mand_line.name,
                                'c_status':mand_line.c_status,
                                'discount': mand_line.c_default_discount,
                                'product_uom_qty': mand_line.quantity,
                                'product_uom_id': mand_line.uom_id.id,
                                'price_unit': mand_line.quantity,
                                
                                
                                }))
        
        qoute_name = "[{}] {}".format(rec.code, rec.name)
        quote_vals = {'name': qoute_name, 'contract_template': rec.id, 'c_type': rec.c_type, 'active': rec.active, 'quote_line': order_lines, 'single_store': self.single_store}
        print "=============vals======", quote_vals
        template_id = self.env['sale.quote.template'].create(quote_vals)
        rec.c_template_id = template_id
        a = self.env['res.groups'].search([('name', '=', 'Accountant')])
        emails = []
        for val in self.env['res.groups'].browse(a.id):
            if val.users:
                for s in val.users:
                    emails.append(s.partner_id.email)
        email_value = ''
        for email in emails:
            email_value += str(email) + ','
        rec['c_account_email'] = email_value
        template = self.env['mail.template'].search([('name', '=', 'subscription template accounts review')], limit=1)
        if template:
            template.send_mail(rec.id)

        return rec

class ouc_subscription_template_line(models.Model):
    _inherit = 'sale.subscription.template.line'
    
    c_product_template_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id')


    c_status = fields.Selection([('new', 'New'), ('renewalupsell', 'Renewal/Upsell')], string='Status', default='new')

    c_default_discount = fields.Float('Default Discount (%)')
    c_max_discount = fields.Float('Maximum Discount (%)')
    c_default_quantity = fields.Integer(string='Default Quantity',default= 1)
    c_maximum_quantity = fields.Integer(string='Maximum Quantity', default = 1)

    @api.onchange('c_product_template_id')
    def set_default_discount_values(self):
        if self.c_product_template_id:
            print ">>>>>>>>>>>>>>>>>", self.c_product_template_id.c_default_discount
            self.c_default_discount = self.c_product_template_id.c_default_discount
            print ">>>>>>>>>>>>>>>>>", self.c_product_template_id.c_max_discount
            self.c_max_discount = self.c_product_template_id.c_max_discount

    @api.onchange('c_default_quantity')
    def setting_def_qty(self):
        self.quantity = self.c_default_quantity
        if self.c_default_quantity <= 0:
            raise exceptions.ValidationError(_('Default quantity must be greater than zero.'))

class ouc_subscription_line(models.Model):
    _inherit = 'sale.subscription.line'

    @api.one
    @api.depends('c_sale_order_id')
    def _compute_amt_in_inr(self):
        company_currency = self.c_sale_order_id.company_id.currency_id
        currency_id = self.c_sale_order_id.currency_id
        if currency_id != company_currency:
            currency = currency_id.with_context(date=self.c_sale_date or fields.Date.context_today(self))
            self.amount_in_inr = currency.compute(self.price_subtotal, company_currency)
        else:
            self.amount_in_inr = self.price_subtotal
    
    c_product_template_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id')

    c_team_id = fields.Many2one('crm.team', string='Sales Team')

    c_fptags_id = fields.Many2one('ouc.fptag', string='FPTAGs')
    c_default_discount = fields.Float('Default Discount (%)')
    c_max_discount = fields.Float('Maximum Discount (%)')
    c_auto_create_fptag = fields.Boolean("Auto create FPs", related="analytic_account_id.c_auto_create_fptag")
    
    c_status = fields.Selection([('new', 'New'), ('renewalupsell', 'Renewal/Upsell')], string='Type', default='new')
    c_validity = fields.Float('Validity (in months)')
    c_sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    c_sale_date = fields.Date('Sale Date')
    c_sales_person_id = fields.Many2one('res.users', string='Sales Person')
    c_cost_center = fields.Many2one('account.analytic.account', string='Cost Centre', help='Sales Person Division')
    c_sp_branch = fields.Many2one('hr.branch', string='Branch', help='Sales Person Branch')
    c_invoice_id = fields.Many2one('account.invoice', string='Invoice No.')
    c_invoice_date = fields.Date('Invoice Date')
    currency_id = fields.Many2one(related='c_sale_order_id.currency_id', store=True, string='Currency', readonly=True)
    
    c_tax_ids = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    c_price_tax = fields.Monetary(string='Tax Amount', readonly=True, store=True)
    c_price_total = fields.Monetary(string='Amount with Tax', readonly=True, store=True)
    
    c_activation_id = fields.Char('Activation ID')
    c_inv_cancel_date = fields.Date(string='Invoice Cancel Date')
    price_subtotal = fields.Float(compute='_compute_price_subtotal', string='Sub Total',digits=dp.get_precision('Account'),store=True)
    amount_in_inr = fields.Float(compute='_compute_amt_in_inr', string = 'Amount in INR', store=True)
    inv_line_id = fields.Integer(string='Invoice Line')
    fptag_city = fields.Char('FPTag City')

class cfc_contract(models.Model):
    _name = 'cfc.contract'
    _order = 'account_assigned_count, name'

    @api.multi
    def name_get(self):
        result = []
        name = ''
        for record in self:
            account_assigned_count = record.account_assigned_count and str(record.account_assigned_count) or '0'
            name = ''
            if record.name:
                current_date = fields.Date.context_today(self)
                current_date = datetime.datetime.strptime(current_date, "%Y-%m-%d")
                join_date = datetime.datetime.strptime(record.name.join_date, "%Y-%m-%d")
                tenure_in_days = (current_date - join_date).days
                tenure = str(tenure_in_days / 30) + ' Months'
                if tenure_in_days < 31:
                    tenure = str(tenure_in_days) + ' Days'
                if record.type != 'MLC':
                    name = "{} ({}) (tenure : {})".format(record.name.name_related, account_assigned_count, tenure)
                else:
                    name = "{} (tenure : {})".format(record.name.name_related, tenure)
            result.append((record.id, name))
        return result

    name = fields.Many2one('hr.employee', 'CFC')
    contract_id = fields.Many2one('sale.subscription', 'Contract')
    account_assigned_count = fields.Integer('Account Assigned Count')
    active = fields.Boolean(related='name.active',string='Active')
    type = fields.Selection([('FOS', 'FOS'), ('MLC', 'MLC')], string='Type')

class SaleSubscriptionCloseReasonWizard(models.TransientModel):
    _inherit = "sale.subscription.close.reason.wizard"

    @api.multi
    def set_close_cancel(self):
        self.ensure_one()
        subscription = self.env['sale.subscription'].browse(self.env.context.get('active_id'))
        subscription.close_reason_id = self.close_reason_id
        if self.env.context.get('cancel'):
            subscription.set_cancel()
            if subscription.c_sales_order_id:
                subscription.c_sales_order_id.mib_status = 'MIB Not Required'
                #subscription.action_deactivate_package()
                #subscription.action_cancel_payment_by_sale_order()
        else:
            subscription.set_close()
  
    