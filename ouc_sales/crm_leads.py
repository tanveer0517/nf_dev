from __future__ import division
from odoo import fields, models, api, _
import re
from odoo import exceptions
from datetime import datetime
from datetime import date
from odoo.exceptions import ValidationError
import requests
import os.path
import urllib, json
import time
from openerp.osv import osv



class ouc_crm_lead(models.Model):
    _inherit = 'crm.lead'
    _order = "create_date desc"

    @api.one
    @api.depends('c_lc_division_id')
    def _compute_lead_type(self):
        if not self.c_lc_division_id:
            return True

        type = self.c_lc_division_id.c_type

        self.is_mlc_lead = False
        self.is_la_lead = False

        if type=="mlc":
            self.is_mlc_lead = True
            return True

        if type=="la":
            self.is_la_lead = True
            return True
        
    
    @api.multi
    def _compute_meeting_count(self):
        meeting_data = self.env['crm.phonecall'].sudo().read_group([('opportunity_id', 'in', self.ids)], ['opportunity_id'],
                                                             ['opportunity_id'])
        mapped_data = {m['opportunity_id'][0]: m['opportunity_id_count'] for m in meeting_data}
        for lead in self:
            lead.meeting_count = mapped_data.get(lead.id, 0)

    @api.one
    @api.depends('c_lead_creator_id')
    def autofill_lc_division(self):
        for val in self:
            record = self.env['hr.employee'].search([('user_id', '=', val.c_lead_creator_id.id )])
            if not record:
                return True
            employee = record[0]
            division = employee.sub_dep
            self.c_lc_division_id = division
            self.c_lead_creator_emp = employee

            managers_id = []
            self.get_manager(employee, employee.parent_id, managers_id)
            email_values = ''
            for val in managers_id:
                email_values += str(val) + ','
            self.c_tc_manager_hierarchy = email_values

    @api.one
    @api.depends('user_id')
    def autofill_department(self):
        if not self.user_id:
            return
        record = self.env['hr.employee'].sudo().search([('user_id', '=', self.user_id.id)])
        if record:
            employee = record[0]
            self.c_cost_center = employee.cost_centr
            self.c_sp_emp = employee
            if record.coach_id.work_email != record.parent_id.work_email:
                self.c_dept_manager = str(record.coach_id.work_email) + ',' + str(record.parent_id.work_email)
            if record.coach_id.work_email == record.parent_id.work_email:
                self.c_dept_manager = record.coach_id.work_email

            managers_id = []
            self.get_manager(record, record.parent_id, managers_id)
            email_values = ''
            for val in managers_id:
                email_values += str(val) + ','
            self.c_managers_hierarchy = email_values

    def get_manager(self, user, dep_manager, managers_id):
        if user.coach_id:
            if user.coach_id != dep_manager:
                managers_id.append(user.work_email)
                self.get_manager(user.coach_id, dep_manager, managers_id)
            else:
                managers_id.append(user.work_email)
        else:
            managers_id.append(user.work_email)


    # Compute Method is
    # differences of last update date and current date
    @api.depends('c_last_updated_in_month')
    def _compute_day_write(self):
        c_date = datetime.today()
        w_date = datetime.strptime(self.write_date, '%Y-%m-%d %H:%M:%S')
        diff_year = c_date.year - w_date.year
        diff_month = c_date.month - w_date.month
        if diff_year == 0:
            self.c_last_updated_in_month = str(diff_month)
        if diff_year != 0:
            self.c_last_updated_in_month = str((diff_year * 12) + diff_month)
        
    #FIELDS
    
    c_customer_fname = fields.Char(string='Customer First Name')
    c_customer_lname = fields.Char(string='Customer Last Name')
    c_city_id = fields.Many2one('ouc.city', string='City')
    c_existing_website = fields.Char(string='Existing website (if any)')
    c_vis_card_front_name = fields.Char(string='Visiting Card Front Image Name')
    c_visiting_card_front = fields.Binary(string='Visiting Card Front Image')
    c_vis_card_back = fields.Char(string='Visiting Card Back Image Name')
    c_visiting_card_back = fields.Binary(string='Visiting Card Back Image')
    c_contact_id = fields.Many2one('res.partner', string='Contact Person')
    
    # MLC Case
    is_mlc_lead = fields.Boolean('MLC Lead', compute='_compute_lead_type')
    
    # LA case
    is_la_lead = fields.Boolean('LA Lead', compute='_compute_lead_type')
    is_la_req_state = fields.Selection(
        [('draft', 'Draft'), ('request', 'Request'), ('approve', 'Approve'), ('reject', 'Reject')],
        string='LA REQ STATE', default='draft')
    
    # overriding standard fields
    city = fields.Char(string='City', related='c_city_id.name')
    state_id = fields.Many2one('res.country.state', string='State', related='c_city_id.state_id')
    country_id = fields.Many2one('res.country', string='Country', related='c_city_id.country_id')

    c_lead_creator_id = fields.Many2one('res.users', string='Lead Creator Name', default=lambda self: self.env.uid, track_visibility='onchange')
    c_lead_creator_emp = fields.Many2one('hr.employee',string='Lead Creator Employee',compute='autofill_lc_division')
    c_lead_source_id = fields.Many2one('ouc.lead.source', 'Lead Source')
    c_sales_support_id = fields.Many2one('hr.employee', string='Sales Support')
    c_lost_reason_id = fields.Many2one('ouc.lost.reason', string='Reasons (If Lost)')
    c_lost_description = fields.Text(string='Description')
    c_dept_manager = fields.Char('Dept manager email')
    c_managers_hierarchy = fields.Char('Manager email',store=True)
    c_lc_division_id = fields.Many2one('hr.department', string='Lead Creator Division', related='c_lead_creator_emp.sub_dep')
    c_cost_center = fields.Many2one('account.analytic.account', string='Cost Center', related='c_sp_emp.cost_centr')
    c_sp_emp = fields.Many2one('hr.employee', string='Salesperson Employee',store=True, compute='autofill_department')
    c_partner_ref_id = fields.Many2one('res.partner', string='Partner Reference')
    # user_id = fields.Many2one('hr.department',string='Salesperson')
    c_request_approval = fields.Boolean(string='Request for Approval Status')
    c_approval_status = fields.Selection(
        [('Not Applicable', 'Not Applicable'), ('Request sent for approval', 'Request sent for approval'),
         ('Approved', 'Approved'), ('Rejected', 'Rejected')], string='Lead Approval status')
    c_state = fields.Selection(
        [('cancel', 'Cancel'), ('progress', 'Progress'), ('manual', 'Manual'), ('done', 'Done'), ('draft', 'Draft')],
        string='State', invisible=True)
    c_stage = fields.Selection([('Stage1', 'Stage1'), ('Stage2', 'Stage2'), ('Stage3', 'Stage3')], string='Stage')
    
    c_quotation_created = fields.Boolean('Is Quotation Created?', default=False)
    #    c_categ_ids = fields.Many2many('ouc.crm.case.categ', 'ouc_crm_case_categ_rel' 'categ_id', 'sale_order_id', string='Categories')
    #    c_date_action=fields.Date('Next Meeting Date')
    c_subscribed_customer = fields.Boolean(string="Only Paid Customer", default=True)
    c_last_updated_in_month = fields.Char(compute='_compute_day_write', string='Date Difference in Months')

    c_addr_landmark = fields.Char(string='Landmark')

    meeting_count = fields.Integer('# Meetings', compute='_compute_meeting_count')
    c_created_from_lead = fields.Boolean(string='Is this opportunity from Lead')

    # for fptags
    c_fptags_ids = fields.One2many('ouc.fptag', 'lead_id', string='FPTAG details')
    c_contact_email = fields.Char(string='Contact Email')
    c_contact_mobile = fields.Char(string='Contact Mobile', track_visibility='onchange')
    mobile = fields.Char('Mobile', track_visibility='onchange')
    
    c_country_1 = fields.Many2one('res.country', string="Country Mobile 1", default=105)
    c_country_2 = fields.Many2one('res.country', string="Country Mobile 2", default=105)
    c_country_3 = fields.Many2one('res.country',string="Country Landline #",default=105)
    c_country_code_1 = fields.Integer(string='Country Code', related="c_country_1.phone_code", default=91)
    c_country_code_2 = fields.Integer(string='Country Code', related="c_country_2.phone_code", default=91)
    c_country_code_3 = fields.Integer(string='Country Code', related="c_country_3.phone_code", default=91)
    c_tc_manager_hierarchy = fields.Char(string='Telecaller Mngr Hierarchy',store=True)
    slab_id = fields.Many2one('nf.la.slab', 'Partner Slab')
    claim_id = fields.Char('Claim ID')
    is_claim = fields.Boolean('Claimed ?')
    is_mlc = fields.Selection([('Yes','Yes'), ('No', 'No')], 'Add-ons/ Combos/ MLC* ?')
    quotation_created = fields.Boolean('Quotation Created')
    fp_date_validation = fields.Boolean('Fp Date Validation',track_visibility='onchange')
    fpv_crr = fields.Boolean('FPV_Count', track_visibility='onchange')
    custom_quotation = fields.Many2one('nf.custom.quotation','Custom Quotation')
    receipt_pic = fields.Binary('Cheque/Cash Receipt')
    receipt_file_name = fields.Char('Receipt file name')


    _sql_constraints = [
        ('cust_contact_name_check',
         'UNIQUE(contact_name, mobile, partner_name)',
         "Sorry! Don't try to cheat, we already have the information about this Customer's lead")
    ]

    @api.multi
    def create_custom_quotation(self):
        curr_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        param = self.env['ir.config_parameter']
        currency = param.search([('key', '=', 'CustomQuotationCurrency')])
        fiscal_position = param.search([('key', '=', 'CustomQuotationFiscalPosition')])
        pricelist = param.search([('key', '=', 'CustomQuotationPricelist')])

        for rec in self:
            company_name=rec.partner_id.parent_id and rec.partner_id.parent_id.name or rec.partner_id.name
            partial_id = self.env['nf.custom.quotation'].create({'opportunity_id':rec.id,'sales_person_id':rec.user_id.id,'partner_id':rec.partner_id.id,'company_name':company_name,'date_order':curr_date,'currency_id':int(currency.value),'name':'Quotation for '+company_name,'pricelist_id':int(pricelist.value),'team_id':rec.team_id.id or False,'fiscal_position_id':int(fiscal_position.value)})
            rec.write({'quotation_created':True,'custom_quotation':partial_id.id})
            rec.action_set_won()
            #open register note wizard 
            return {
                'name':_("Create Quotation"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'nf.custom.quotation',
                'res_id': partial_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy': True,
                'domain': '[]'
                }

    @api.multi
    def open_custom_quotation(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "nf.custom.quotation",
            "views": [[self.env.ref('ouc_sales.nf_custom_quotation_form_view').id, "form"]],
            "domain": [],
            'res_id': self.custom_quotation and self.custom_quotation.id or False,
            "context": {},
            'view_mode':'form',
            'target': 'new',
            "name": "Quotation",
            'flags': {'initial_mode': 'view'}
               }

    @api.multi
    def claim_order(self):
        if not self.claim_id:
            raise ValidationError("No Claim ID! Please Enter Claim ID and claim the sale")

        vals = {"claimId": self.claim_id,
                "emailId": self.user_id.login,
                "hotProspect": self.name
                }
        cr = self.env.cr
        cr.execute("SELECT id from sale_order where claim_id = '{}'".format(self.claim_id))
        sale_order = cr.fetchone()

        if not sale_order:
            raise exceptions.ValidationError(
                _('Sales Order still pending for approval'))

        so_id = sale_order[0]

        if self.receipt_pic:
            data = {"claimId" : self.claim_id,
                    "emailId": self.user_id.login,
                    "receiptPicBin": self.receipt_pic,
                    "receiptPicName": self.receipt_file_name
                    }
            self.env['nf.api'].sudo().UpdateReceiptInSO(data)

        self.env['nf.api'].with_context(default_type = 'binary').sudo().claimOrder(vals)
        return True

    @api.model
    def update_managers_email(self):
        lead_ids=self.sudo().search([])
        for rec in lead_ids:
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
            self.env.cr.execute("update crm_lead set c_managers_hierarchy=%s where id = %s",(managers_email,rec.id,))
        return True

    @api.onchange('c_visiting_card_back')
    def checking_vImage_back(self):
        if self.c_visiting_card_back:
            b_name, b_ext = os.path.splitext(self.c_vis_card_back)
            if b_ext not in['.png', '.jpg', '.jpeg']:
                raise exceptions.ValidationError(_('Extension should be jpg,jpeg or png'))
    @api.onchange('c_visiting_card_front')
    def checking_vImage_front(self):
        if self.c_visiting_card_front:
            f_name, f_ext = os.path.splitext(self.c_vis_card_front_name)
            if f_ext not in ['.png', '.jpg', '.jpeg']:
                raise exceptions.ValidationError(_('Extension should be jpg,jpeg or png'))

    @api.onchange('c_customer_fname', 'c_customer_lname', 'contact_name', 'partner_name', 'street', 'street2', 'c_addr_landmark')
    def change_to_camel_case(self):
        if self.c_customer_fname:
            fname = self.c_customer_fname[0].upper() + self.c_customer_fname[1:]
            self.c_customer_fname = fname

        if self.c_customer_lname:
            lname = self.c_customer_lname[0].upper() + self.c_customer_lname[1:]
            self.c_customer_lname = lname

        if self.partner_name:
            pname = self.partner_name[0].upper() + self.partner_name[1:]
            self.partner_name = pname

        if self.c_customer_fname and self.c_customer_lname:
            fullname = "{} {}".format(self.c_customer_fname, self.c_customer_lname)
            self.contact_name = fullname

        if self.street:
            s1 = self.street[0].upper() + self.street[1:]
            self.street = s1

        if self.street2:
            s2 = self.street2[0].upper() + self.street2[1:]
            self.street2 = s2

        if self.c_addr_landmark:
            land = self.c_addr_landmark[0].upper() + self.c_addr_landmark[1:]
            self.c_addr_landmark = land
            
    
    # validation check for proper email,mobile ,zip code and phone number
    @api.constrains('email_from', 'mobile', 'zip', 'phone')
    def _validate_email(self):
        if self.email_from:
            self.email_from.replace(" ", "")
            if not re.match(r"[^@]+@[^@]+\.[^@]+", self.email_from):
                raise exceptions.ValidationError(_('Please submit.... valid email address'))

        if self.c_contact_mobile:
            self.c_contact_mobile.replace(" ", "")
            if self.c_country_1.id == 105:
                if len(self.c_contact_mobile) != 10 or not re.match(r"[0-9]{10}", self.c_contact_mobile):
                    raise exceptions.ValidationError(
                        _('Mobile number contain 10 digits only... It contain More than 10 numbers'))
            else:
                if not re.match(r"[0-9]", self.c_contact_mobile):
                    raise exceptions.ValidationError(_('Please submit.... valid mobile number '))
                elif re.search(r"[a-z]", self.c_contact_mobile):
                    raise exceptions.ValidationError(_('Please submit.... valid mobile number '))
        
        if self.type == 'opportunity':
            return
        if self.mobile:
            self.mobile.replace(" ", "")
            if self.c_country_1.id == 105:
                if len(self.mobile) != 10 or not re.match(r"[0-9]{10}", self.mobile):
                    raise exceptions.ValidationError(
                        _('Mobile number contain 10 digits only... It contain More than 10 numbers'))
            else:
                if not re.match(r"[0-9]", self.mobile):
                    raise exceptions.ValidationError(_('Please submit.... valid mobile number '))
                elif re.search(r"[a-z]", self.mobile):
                    raise exceptions.ValidationError(_('Please submit.... valid mobile number '))

        if self.phone:
            self.phone.replace(" ", "")
            if self.c_country_1.id == 105:
                if not re.match(r"[0-9]", self.phone):
                    raise exceptions.ValidationError(_('Please submit.... valid phone number '))
    
    @api.onchange('c_contact_email', 'c_contact_mobile','c_country_1')
    def onchange_mobile_email(self):
        if self.c_contact_email:
            self.email_from = self.c_contact_email

        if self.c_contact_mobile:
            self.mobile = self.c_contact_mobile

        if self.c_country_1:
            self.c_country_2 = self.c_country_1
    
    @api.multi
    def claim_fptag(self):
        #claim Fptag API
        for rec in self:
            if rec.c_fptags_ids and 'FOS' in rec.c_lc_division_id.name:
                branch_server_id = rec.c_sp_emp and rec.c_sp_emp.branch_id and rec.c_sp_emp.branch_id.server_branch_id or False
                fos_id = rec.c_sp_emp.c_fos_handle and rec.c_sp_emp.c_fos_handle.name or False
                for fp_id in rec.c_fptags_ids:
                    self.check_demo_fp(fp_id.name)
                    if not fp_id.claimed:
                        param = self.env['ir.config_parameter']
                        claimfp_url = param.search([('key', '=', 'ClaimFPURL')])
                        clientId = param.search([('key', '=', 'clientIdForOTP')])
                        url = claimfp_url.value
                        querystring = {"clientId": clientId.value,
                                       "username": fos_id,
                                       "fpTag": fp_id.name,
                                       "locationId": branch_server_id
                                       }
                        headers = {
                            'content-type': "application/json",
                            'cache-control': "no-cache",
                        }
                        response = requests.request("GET", url, headers=headers, params=querystring)
                        if response.status_code == 200:
                            fp_id.sudo().write({'claimed': True})
                        else:
                            raise exceptions.ValidationError(_('You cannot proceed with this sale. This FPTag is belong to different partner.'))
            return True

    # for generating sequence for the lead
    @api.model
    def create(self, create_values):
        seq = self.env['ir.sequence'].next_by_code('sequence')
        create_values["name"] = seq
        res = super(ouc_crm_lead, self).create(create_values)
	try:
         res.claim_fptag()
	except:
	  pass
        return res

    @api.multi
    def write(self, vals):
        if 'claim_id' in vals and vals['claim_id']:
            vals['claim_id'] = vals['claim_id'].strip()
        res = super(ouc_crm_lead, self).write(vals)
        if vals.get('c_fptags_ids',False):
	    try:
              self.claim_fptag()
	    except:
		pass
        if 'user_id' in vals:
            template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats Lead Assigned to Sales Person')],
                                                        limit=1)
            if template:
                template.send_mail(self.id)
        return res

    # LA case
    def req_for_approval(self):
        print "======req for approval========="
        self.is_la_req_state = 'request'
        template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats Lead Request for approval for LA')], limit=1)
        if template:
            template.send_mail(self.id)


    def action_approval(self):
        uid = self.env.uid
        print "uid", uid
        record = self.env['hr.employee'].sudo().search([('user_id', '=', uid )])
        if not record:
            raise exceptions.ValidationError(_('You have to be Channel Sales Head to approve this'))
        
        # employee = record[0]
        # position = employee.job_id
        # if not position:
        #     raise exceptions.ValidationError(_('You have to be Channel Sales Head to approve this'))
        
        # if not position.name == 'Channel Sales Head':
        #     raise exceptions.ValidationError(_('You have to be Channel Sales Head to approve this'))

        if not self.env.user.has_group('ouc_sales.group_la_approval'):
            raise exceptions.ValidationError(_('Sorry, you do not have access to approve this lead. Please contact to HR to get access.'))
        
        self.is_la_req_state = 'approve'
        print "======= Approval ============"
        self.c_approval_status ='Approved'
        template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats Status of Lead Approval Request')],
                                                    limit=1)
        if template:
            template.send_mail(self.id)

    def action_reject(self):
        print "===========reject ==========="
        return self.action_set_lost()

    def redirect_to_support_dashboard(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "nf.support.dashboard",
            "views": [[self.env.ref('ouc_sales.nf_support_dashboard_form').id, "form"]],
            "domain": [],
            "context": {"partner_id": self.partner_id and self.partner_id.id or ''},
            "name": "Partner Dashboard"
        }
    
    # over riding the meeting method when email is not there it raise exception
    def action_schedule_meeting(self):
        if self.email_from:
            self.ensure_one()
            action = self.env.ref('calendar.action_calendar_event').sudo().read()[0]
            partner_ids = self.env.user.partner_id.ids
            if self.partner_id:
                partner_ids.append(self.partner_id.id)

            action['context'] = {
                'search_default_opportunity_id': self.id if self.type == 'opportunity' else self.id if self.type == 'lead' else False,
                'default_opportunity_id': self.id if self.type == 'opportunity' else self.id if self.type == 'lead' else False,
                'default_partner_id': self.partner_id.id,
                'default_partner_ids': partner_ids,
                'default_c_cost_center': self.c_cost_center.id,
                'default_name': self.name
            }
            return action
        else:
            raise exceptions.ValidationError(_('Please.... mention Email id! Unless we can\'t Provide Meeting'))

    def check_demo_fp(self, fptag):

        # Validation only for FOS non renewal sales

        param = self.env['ir.config_parameter']
        fpNfWebUrl = param.search([('key', '=', 'fpNfWebUrl')])
        fpNfWebClient = param.search([('key', '=', 'CreateCFClientId')])

        lead_id = self.id

        url = '%s{}?clientId=%s' % (fpNfWebUrl.value, fpNfWebClient.value)
        url = url.format(fptag)
        response = urllib.urlopen(url)
        encoder = response.read().decode('utf-8')
        json_response = json.loads(encoder)
        if json_response:
            fp_create_date = json_response.get('CreatedOn', '')
            if fp_create_date:
                fp_create_date = re.sub(r"\D", "", fp_create_date)
                fp_create_date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(fp_create_date) / 1000))
                self.env.cr.execute("UPDATE ouc_fptag "
                                    "SET fp_creation_date = '{}' "
                                    "WHERE name = '{}'"
                                    .format(fp_create_date, fptag))
                str_sql = "SELECT * FROM check_demo_fp({}, '{}')".format(lead_id, fp_create_date)
                self.env.cr.execute(str_sql)
                temp = self.env.cr.fetchone()[0]
                if temp:
                    self.env.cr.execute("UPDATE crm_lead "
                                        "SET fp_date_validation = True, fpv_crr = True "
                                        "WHERE id = {}"
                                        .format(lead_id))

        return True

    
    def convert_to_opportunity(self):
        if not self.c_fptags_ids and not self.is_la_lead and not self.is_mlc_lead and self.is_mlc != 'Yes':
            raise exceptions.ValidationError(_('FPTAGs are mandatory for converting to opportunity'))

        self.c_created_from_lead = True

        if self.is_la_lead:
            template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats Opportunity created for LA notification')],
                                                    limit=1)
            if template:
                template.send_mail(self.id)
        elif self.fp_date_validation:
                raise osv.except_osv(_("This is a direct FOS lead!"),
                                     _(
                                         "To proceed further, Lead Creator should be same as Salesperson(FOS). Please click on UPDATE LC Button."))
        
        return {
            'name': _('Convert to Opportunity'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'crm.lead2opportunity.partner',
            'type': 'ir.actions.act_window',
            'nondestroy': True,
            'target': 'new'
        }

    @api.multi
    def update_lc(self):
        self.write({'fp_date_validation' : False, 'c_lead_creator_id': self.user_id and self.user_id.id or False})
        return True
    
    @api.onchange('c_subscribed_customer')
    def apply_domain_on_customer(self):
        if self.c_subscribed_customer:
            return {'domain': {'partner_id': [('c_alliance_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('is_company', '=', True)]}}

    @api.onchange('partner_id')
    def fill_opportunity_values(self):
        if not self.partner_id:
            return
        
        self.c_city_id = self.partner_id.c_city_id.id
        
        if not self.partner_id.child_ids:
            return
        
        self.c_contact_id = self.partner_id.child_ids[0].id
        self.contact_name = self.c_contact_id.name
        self.title = self.c_contact_id.title
        
        if self.c_contact_id.mobile and self.c_contact_id.mobile[0] == '+':
            self.c_contact_mobile = self.c_contact_id.mobile[4:]
        else:
            self.c_contact_mobile = self.c_contact_id.mobile
    
    
    def action_new_quotation(self):
        if not self.partner_id:
            raise exceptions.ValidationError(_('No Partner is defind on Hot Prospect'))

        partner_id = self.partner_id
        obj_id = self.env['sale.subscription'].sudo().search([('partner_id', '=', partner_id.id)],limit=1)

        if obj_id and not self.c_created_from_lead: #Renewal Case
            values = self._prepare_renewal_order_values(obj_id)
            order = self.env['sale.order'].sudo().create(values[obj_id.id])

            fp_ids = map(lambda x : x.id, self.c_fptags_ids)
            if fp_ids:
                fp_ids.append(1.5)
                self.env.cr.execute("UPDATE "
                            "ouc_fptag "
                            "SET customer_id = {}, state = 'valid' "
                            "WHERE id IN {}"
                            .format(self.partner_id.id, tuple(fp_ids)))

        else: #New Case
            values = self._prepare_new_order_values()
            order = self.env['sale.order'].sudo().create(values)

        self.c_quotation_created = True
        self.action_set_won()

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": order.id,
            }

    def _prepare_renewal_order_values(self, subscription_id):
        res = dict()
        
        quote_type = 'renewalupsell'
        
        order_lines = []
        fpos_id = self.env['account.fiscal.position'].sudo().get_fiscal_position(subscription_id.partner_id.id)
        addr = subscription_id.partner_id.address_get(['delivery', 'invoice'])
        res[subscription_id.id] = {
            'pricelist_id': subscription_id.pricelist_id.id,
            'partner_id': subscription_id.partner_id.id,
            'c_company_name': subscription_id.partner_id.name,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'c_quotation_type': quote_type,
            'currency_id': subscription_id.pricelist_id.currency_id.id,
            'c_cost_center': self.c_cost_center.id,
            'order_line': order_lines,
            'project_id': subscription_id.analytic_account_id.id,
            'subscription_management': 'upsell',
            'note': subscription_id.description,
            'fiscal_position_id': fpos_id,
            'user_id': self.user_id.id,
            'payment_term_id': subscription_id.partner_id.property_payment_term_id.id,
            'c_lead_source_id': self.c_lead_source_id.id,
            'c_lead_creator_id': self.c_lead_creator_id.id,
            'c_partner_ref_id': self.c_partner_ref_id.id,
            'opportunity_id': self.id
        }
        return res

    def _prepare_new_order_values(self):
        res = dict()
        quote_type = 'new'

        order_lines = []
        partner = self.partner_id
        fpos_id = self.env['account.fiscal.position'].sudo().get_fiscal_position(partner.id, partner.id)
        addr = partner.address_get(['delivery', 'invoice'])

        res = {
            'pricelist_id': partner.property_product_pricelist and self.partner_id.property_product_pricelist.id or 1,
            'partner_id': partner.id,
            'c_company_name': partner.name,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'c_quotation_type': quote_type,
            'order_line': order_lines,
            'fiscal_position_id': fpos_id,
            'user_id': self.user_id.id,
            'payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
            'c_lead_source_id': self.c_lead_source_id.id,
            'c_lead_creator_id': self.c_lead_creator_id.id,
            'c_partner_ref_id': self.c_partner_ref_id.id,
            'opportunity_id': self.id
        }
        return res


    
class ouc_crm_lost_reason(models.TransientModel):
    _inherit = 'crm.lead.lost'

    c_lost_description = fields.Text('Lost Description')
    c_lead_id = fields.Many2one('crm.lead','Lead Id')

    @api.model
    def default_get(self, fields):
        active_model = self.env.context.get('active_model')
        if active_model:
            obj_id = self.env[active_model].sudo().browse(self.env.context.get('active_id'))
            rec = super(ouc_crm_lost_reason, self).default_get(fields)
            rec.update({'c_lead_id': obj_id.id})
        return rec

    @api.multi
    def action_lost_reason_apply(self):
        if len(self.c_lost_description) < 100:
            raise exceptions.ValidationError(_('Description is too short.... It should be more than 100 character'))
        else:
            lead = self.env['crm.lead'].sudo().browse(self.env.context.get('active_ids'))
            lead.sudo().write({'lost_reason': self.lost_reason_id.id,
                        'c_lost_description': self.c_lost_description
                        })

        template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats Mark As Lost Template')],
                                                        limit=1)
        if template:
            template.send_mail(self.id)

        return lead.action_set_lost()

class nf_la_slab(models.Model):
    _name = 'nf.la.slab'

    code = fields.Char('Code')
    name = fields.Char('Name')

class ouc_crm_team(models.Model):
    _inherit = 'crm.team'

    c_cus_footer = fields.Text(string='Custom Footer')

