from odoo import api, fields, models, _
from odoo import exceptions
from odoo.exceptions import ValidationError
import time
from odoo.fields import Date
import collections
import datetime
from datetime import timedelta,datetime,date
import requests
import json
import base64
import smtplib
from dateutil import relativedelta


Grade_Selection = [('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')]
Years = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11'),('12','12'),('13','13'),('14','14'),('15','15'),('16','16'),('17','17'),('18','18'),('19','19'),('20','20'),('21','21'),('22','22'),('23','23'),('24','24'),('25','25')]
Months = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11')]

class hr_contract(models.Model):
    
    _inherit = "hr.contract"
    
    name=fields.Char('Name')
    old_basic=fields.Float(string='Old Basic')
    grade_pay=fields.Float(string='Grade Pay')
    last_wage=fields.Float(string='Last Month Wage')
    new_basic=fields.Float('New Basic (CDA)')
       
    driver_salary=fields.Boolean(string='Driver Salary')
    house_rent_all=fields.Float('House Rent Allowance(%)')
    supplementary_allowance=fields.Float('Supplementary Allowance')
        
    tds=fields.Float('TDS')
    voluntary_provident_fund=fields.Float('Voluntary Provident Fund')
    medical_insurance=fields.Float(string="Medical Insurance(Self)")
    deputed_from_same_station=fields.Boolean(string='Deputed From Same Station')
    deputation_allowance=fields.Boolean('Eligible For Deputation Allowance')
    conveyance_allowance=fields.Boolean('Eligible For Conveyance Allowance')
    hra=fields.Boolean('Eligible For HRA')
    medical_all=fields.Boolean('Opted For Medical Allowance')
    furnishing_all=fields.Boolean('Opted For Furnishing Allowance')
    pf_stop=fields.Boolean('PF Stop')
    spouse_railway=fields.Boolean('Spouse Opting Railway/PSU Medical Allowance')
    previous_railway_empl=fields.Boolean('Previous Railway Employee')
    washing_allowance=fields.Boolean('Opted For Washing Allowance')
    holiday_worked_Day=fields.Integer('National Holiday Worked Days')
    night_duty_hr=fields.Float('Night Duty Hours',widget='Float_time')
    monthly_rent=fields.Float('Monthly Quarter Rent')
    pf_amt=fields.Float('Special PF Amounts')
    actual_ctc=fields.Float(string="Actual CTC")
    byod_allowance=fields.Float(string="BYOD Allowance")
    pf_not_applicable=fields.Boolean('PF Not Applicable')
    lop=fields.Float(string="LOP")
    arre_id=fields.Float(string="Arrears")
    variable_pay=fields.Float(string="Variable Pay")
    amt_adv=fields.Float(string="Advance Amount")
    analytic_account_id = fields.Many2one('account.analytic.account',string='Cost Centre',readonly=1)
    c_active = fields.Boolean(string='Active')
    c_hra_metro_nonmetro = fields.Float(string='Hra Metro Nonmetro')
    c_fine_id = fields.Integer(string='Fine Id')
    c_inctax_id = fields.Integer(string='Income Tax Is')
    c_nf_tab = fields.Integer(string='Tab')
    c_nf_donation = fields.Integer(string='Donation')
    c_nf_pf_refund = fields.Integer(string='PF Refund')
    c_nf_pf_deduction = fields.Integer(string='Pf Deduction')
    c_nf_incentive = fields.Integer(string='Incentive')
    c_nf_byod_deduction = fields.Integer(string='Byod Deduction')
    c_nf_gratuity = fields.Integer(string='Gratuity')
    general_recovery=fields.Float('General Recovery')
    incentive_recovery=fields.Float('Incentive Recovery')
    special_incentive=fields.Float('Special Incentive')
    c_lop_days = fields.Float('LOP Days')
    perquisits_allowance = fields.Float('Perquisites Allowance')
    perquisits_deduction = fields.Float('Perquisites Deduction')
    lieu_allowance = fields.Float('Lieu Allowance')
    lieu_deduction = fields.Float('Lieu Deduction')
    date_end = fields.Date('End Date',required=True)
    bonus = fields.Float('Bonus')
    medical_insurance_parents = fields.Float("Medical Insurance (Parents)")
    is_smi  = fields.Boolean('Medical Insurance (Self) - Opted')
    is_pmi = fields.Boolean('Medical Insurance (Parents) - Opted')
    no_of_days_selected = fields.Float(compute='_get_days',store=True,string='No of days based on start date and end date')
    no_of_days_for_employee = fields.Float(compute='_get_days',store=True,string='No of days for contract based on joining date of employee')

    @api.depends('date_start','date_end','employee_id')
    def _get_days(self):
        date_start = self.date_start
        date_end = self.date_end
        employee_id = self.employee_id
        if not date_end or date_end == False:
            no_of_days_selected = 0
            no_of_days_for_employee = 0
        else:
            record = self.env['hr.employee'].sudo().search([('id', '=', self.employee_id.id)], limit = 1)
            if not record:
                no_of_days_selected = 0
                no_of_days_for_employee = 0
            else:
                joining_date = record.join_date
                if joining_date <= date_start:
                    no_of_days_selected = (datetime.strptime(date_end,'%Y-%m-%d') - datetime.strptime(date_start,'%Y-%m-%d')).days  + 1
                    no_of_days_for_employee = (datetime.strptime(date_end,'%Y-%m-%d') - datetime.strptime(date_start,'%Y-%m-%d')).days  + 1
                else:
                    no_of_days_selected = (datetime.strptime(date_end,'%Y-%m-%d') - datetime.strptime(date_start,'%Y-%m-%d')).days + 1
                    no_of_days_for_employee = (datetime.strptime(date_end,'%Y-%m-%d') - datetime.strptime(joining_date,'%Y-%m-%d')).days + 1
        self.no_of_days_selected = no_of_days_selected
        self.no_of_days_for_employee = no_of_days_for_employee


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.sub_dep.id
            self.analytic_account_id=self.employee_id.cost_centr.id

class hr_employee(models.Model):
    _inherit="hr.employee"
    
    def default_country(self):
        return self.env['res.country'].search([('name','=','India')])
    
#         'name=fields.Char('Name')
    empl_unique_id=fields.Char('Employee Unique ID')
    virtual_mob_no=fields.Char('Sales Virtual Number', track_visibility='onchange')
    pf_id=fields.Char('Nowfloats PF Number', track_visibility='onchange')
    uan=fields.Char('Nowfloats UAN Number', track_visibility='onchange')
    empl_type=fields.Char('Employee Type')
    emp_id=fields.Char('Employee ID')
    join_date=fields.Date('Date Of Joining', track_visibility='onchange')
    visibility=fields.Char('Visibility')
    c_depart = fields.Selection([('Business Support','Business Support'),('CHAPS','CHAPS'),('Corp HQ - Biz Mgmt','Corp HQ - Biz Mgmt'),('Design','Design'),('Digital Desh','Digital Desh'),('Digital Dukan','Digital Dukan'),('Finance','Finance'),('Human Resources','Human Resources'),('Legal','Legal'),('Marketing','Marketing'),('Product Development','Product Development'),('Sales','Sales'),('FOS', 'FOS'), ('Alliance', 'Alliance'), ('Development', 'Development'), ('HQ', 'HQ'), ('Growth Team', 'Growth Team'),('MLC','MLC'),('Local Alliance','Local Alliance'),('National Alliance','National Alliance'),('Look Up','Look Up'),('Renewals','Renewals'),('Inside Sales','Inside Sales'),('Strategic Alliances','Strategic Alliances'),('Orion','Orion'),('Kitsune-BU','Kitsune-BU')], 'NF Department')
    
    display_name=fields.Char('NF Display Name')
    state=fields.Char('State')

    sales_chanel=fields.Char('sales_chanel')
    nf_dept=fields.Many2one('hr.department','NF Department', track_visibility='onchange')
    intrnal_desig=fields.Char('Internal Profile', track_visibility='onchange')
    high_edu_qual=fields.Char('Highest Education Qualification', track_visibility='onchange')
    hr_name=fields.Char('HR Name', track_visibility='onchange')
    reporting_head=fields.Many2one('hr.employee','Reporting Head', track_visibility='onchange')
    grade=fields.Selection(Grade_Selection,string='Grade', track_visibility='onchange')
    level=fields.Selection(Grade_Selection,string='Level', track_visibility='onchange')
    aadhar_no=fields.Char('Aadhaar Number')

    emp_father=fields.Char(string="Father's Name as per Aadhaar Card", track_visibility='onchange') 
    data_form=fields.Binary('Data Form')
    emp_size=fields.Char('Employee Shirt Size', track_visibility='onchange')
    pan=fields.Char('PAN', track_visibility='onchange')
    currnt_addr=fields.Char('Current Address')
    alternate_contact=fields.Char('Alternate Contact Number', track_visibility='onchange')
    permanent_addr=fields.Char('Permanent Address')
    personal_email=fields.Char('Personal Email')
    
    offer_letter=fields.Binary('Offer Letter', track_visibility='onchange')
    nda=fields.Binary('NDA', track_visibility='onchange')
    oppointment_letter = fields.Binary('Appointment Letter', track_visibility='onchange')
    oppointment_filename = fields.Char('File Name')
    current_addr_proof=fields.Binary('Current Address Proof', track_visibility='onchange')
    permanent_addr_proof=fields.Binary('Permanent Address Proof', track_visibility='onchange')
    id_proof=fields.Binary('Adhar Proof', track_visibility='onchange')
    c_pan_proof = fields.Binary('PAN Proof', track_visibility='onchange')
    c_voter_proof = fields.Binary('Voter ID Proof', track_visibility='onchange')
    c_pass_proof = fields.Binary('Passport Proof', track_visibility='onchange')
    id_proof_name = fields.Char('Adhar Proof Name')
    c_pan_proof_name = fields.Char('PAN Proof Name')
    c_pass_proof_name = fields.Char('Passport Proof Name')
    c_voter_proof_name = fields.Char('Voter Proof Name')
    certif_12=fields.Binary('High Degree', track_visibility='onchange')
    ug_certifcate=fields.Binary('Other Certificate', track_visibility='onchange')
    previous_pay_slip=fields.Binary("Previous Company's Pay Slip - 1", track_visibility='onchange')
    previous_pay_slip2=fields.Binary("Previous Company's Pay Slip - 2", track_visibility='onchange')
    previous_pay_slip3=fields.Binary("Previous Company's Pay Slip - 3", track_visibility='onchange')
    prev_reliving_lttr=fields.Binary("Previous Company's Relieving Letter", track_visibility='onchange')
    
    payslip_filename1 = fields.Char('File Name')
    payslip_filename2 = fields.Char('File Name')
    payslip_filename3 = fields.Char('File Name')
    prev_reliving_lttr_filename = fields.Char('File Name')

    reliving_leter=fields.Binary('Relieving Letter', track_visibility='onchange')
    othr_docs=fields.Binary('Any Other Document', track_visibility='onchange')
    last_working_date=fields.Date('Last Working Date', track_visibility='onchange')
    empl_status=fields.Selection([('Medical Leave','Medical Leave'),('Maternity Leave','Maternity Leave'),('Post Maternity Leave','Post Maternity Leave'),('Sabbatical Leave','Sabbatical Leave'),('Resigned','Resigned'),('Absconded','Absconded'),('Hold','Hold'),('LOP','LOP'),('Demise','Demise'),('Terminated','Terminated')], string='Employee Status', track_visibility='onchange')
    reason_for_leaving=fields.Char('Reason For Leaving NowFloats', track_visibility='onchange')
    nodues = fields.Binary('Nodues Attachment')
    nodues_filename = fields.Char('File Name')
    empl_attrtion=fields.Binary('Employee Attrition', track_visibility='onchange')
    rehiring_status = fields.Selection([('yes','Yes'),('no','No')],string='Eligible to Rehire', track_visibility='onchange')
    rehiring_comment = fields.Text('Rehiring Comment', track_visibility='onchange')
    resignation_type = fields.Selection([('Voluntary','Voluntary'),('Involuntary','Involuntary')],string='Resignation Type', track_visibility='onchange')
    voluntary = fields.Selection([('Better Opportunity','Better Opportunity'),('Personal Reason','Personal Reason'),('Compensation','Compensation'),('Interpersonal Relationship','Interpersonal Relationship'),('Location','Location')],string='Voluntary', track_visibility='onchange')
    involuntary = fields.Selection([('Non Performance','Non Performance'),('Disciplinary','Disciplinary'),('Absconding','Absconding')],string='Involuntary', track_visibility='onchange')
    rt_comment = fields.Text('Resignation/Termination Comment', track_visibility='onchange')     
    ifsc_Code = fields.Char('IFSC Code')
    
    idcard_type_id = fields.Many2one('id.card',string='Type', track_visibility='onchange')
    idcard_no = fields.Char('Identification No.',help="Identification No.", track_visibility='onchange')
    tax_idcard_id = fields.Many2one('id.card',string='Type', track_visibility='onchange')
    tax_idcard_no = fields.Char('Tax ID',help="Tax ID", track_visibility='onchange')
    other_idcard_id =  fields.Many2one('id.card',string='Type',help="Type", track_visibility='onchange')
    other_idcard_no = fields.Char('Other ID', track_visibility='onchange')
    c_voter_id = fields.Char('Voter ID', track_visibility='onchange')
    c_dl_id = fields.Char('Driving Licence ID', track_visibility='onchange')

    
    family_details = fields.One2many('emp.family.detail','employee_id',string='Family Details')
    c_city_id = fields.Many2one('ouc.city', string='Current City', track_visibility='onchange')
    p_city_id = fields.Many2one('ouc.city', string='Permanent City', track_visibility='onchange')
    
    c_street = fields.Char(string='Current Street Address', track_visibility='onchange')
    c_street2 = fields.Char(string='Current Street2 Address', track_visibility='onchange')
    c_zip = fields.Char(string='Current ZIP', track_visibility='onchange')
    c_city = fields.Char(string='Current City', related='c_city_id.name')
    c_state_id = fields.Many2one('res.country.state', string='Current State', related='c_city_id.state_id')
    c_country_id = fields.Many2one('res.country', string='Current Country', related='c_city_id.country_id')

    p_street = fields.Char(string='Permanent Street Address', track_visibility='onchange')
    p_street2 = fields.Char(string='Permanent Street2 Address', track_visibility='onchange')
    p_zip = fields.Char(string='Permanent ZIP', track_visibility='onchange')
    p_city = fields.Char(string='Permanent City', related='p_city_id.name')
    p_state_id = fields.Many2one('res.country.state', string='Permanent State', related='p_city_id.state_id')
    p_country_id = fields.Many2one('res.country', string='Permanent Country', related='p_city_id.country_id')

    #exit process replacer employee
    c_emp_replacer = fields.Many2one('hr.employee',string='Active Employee Replacer', track_visibility='onchange')
    c_replacer_state = fields.Many2one('res.country.state',string='Employee Replacer State', track_visibility='onchange')
    c_replacer_city = fields.Many2one('ouc.city',string='Replacer City', track_visibility='onchange')
    c_replacer_branch = fields.Many2one('hr.branch',string='Replacer Branch', track_visibility='onchange')
    is_address = fields.Boolean('Is Permanent Address Same as Current Address?',help="Is permanent address same as current address ?", track_visibility='onchange')
    anniversary_date = fields.Date("Date of Marriage", track_visibility='onchange')
    probation_date = fields.Date('Probation Date', track_visibility='onchange')
    c_rem_count = fields.Integer(string='Reminder Count')
    c_ldt = fields.Date(string='Last date of Training', track_visibility='onchange')
    c_nf_buddy = fields.Many2one('hr.employee',string='Buddy', track_visibility='onchange')
    c_nf_trainee = fields.Many2one('hr.employee',string='Trainee Name', track_visibility='onchange')
    c_pathsala_batch=fields.Char(string='Paathsala Batch', track_visibility='onchange')
    c_pathsala_date = fields.Date(string='Paathsala Date', track_visibility='onchange')
    c_pathsala_city = fields.Many2one('ouc.city',string='Paathsala Hub', track_visibility='onchange')
    c_paathashala_score = fields.Float('Paathashala Score', track_visibility='onchange')
    c_nf_chc = fields.Char(string='NF CFT', track_visibility='onchange')
    c_erp_last_date = fields.Date(string='ERP Deactivation Date', track_visibility='onchange')
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status',default='single', track_visibility='onchange')
    info_updated = fields.Boolean('Info Updated')
    c_empl_type=fields.Selection([('contract','Contract'),('intern','Intern'),('permanent','Permanent'),('probation','Probation')],string="Employee Type", track_visibility='onchange')
    c_esi_num=fields.Char('ESI Number', track_visibility='onchange')
    c_pf_num=fields.Char('Previous PF Number', track_visibility='onchange')
    c_fos_handle=fields.Many2one('ouc.fos.handle' ,string='FOS Handle ID')
    c_recruiter_name=fields.Many2one('hr.employee',string='Recruiter Name', track_visibility='onchange')
    c_hr_name=fields.Many2one('hr.employee',string='HR Name', track_visibility='onchange')
    c_pre_uan = fields.Char('Previous UAN Number', track_visibility='onchange')

    hr_process_fnf = fields.Selection([('No', 'No'),('Yes', 'Yes'),('Pending', 'Pending')], 'Process F&F', track_visibility='onchange')
    hr_reason_fnf = fields.Text('Reason for F&F process', track_visibility='onchange')
    fnf_date = fields.Date('F&F Processed Date', track_visibility='onchange')
    relieving_letter = fields.Selection([('No', 'No'),('Yes', 'Yes'),('Pending', 'Pending')], 'Relieving Letter Issued', track_visibility='onchange')
    rl_date = fields.Date('Relieving Letter Issued Date', track_visibility='onchange')
    rl_comment = fields.Text('Relieving Letter Comment', track_visibility='onchange')
    email_link = fields.Char('Email Link', track_visibility='onchange')
    exit_done_date = fields.Date('Exit Formalities Date', track_visibility='onchange')
    exit_done_by = fields.Many2one('res.users','Exit Formalities By', track_visibility='onchange')
    hr_notice_served = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Notice Period Served', track_visibility='onchange')
    hr_np_waived = fields.Selection([('No', 'No'), ('Yes', 'Yes')], string='Notice Period Waived Off', track_visibility='onchange')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], groups='base.group_user', track_visibility='onchange')
    birthday = fields.Date('Date of Birth', groups='base.group_user', track_visibility='onchange')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account Number',
        domain="[('partner_id', '=', address_home_id)]", help='Employee bank salary account', groups='base.group_user', track_visibility='onchange')
    passport_id = fields.Char('Passport No', groups='base.group_user', track_visibility='onchange')
    date_resign = fields.Date(string='Resignation Raised Date', track_visibility='onchange')
    rehire = fields.Selection([('Yes','Yes'),('No','No')],string='Is Rehired',default='No', track_visibility='onchange')
    disp_name = fields.Char(string='Display Name', track_visibility='onchange')
    cfc_created = fields.Boolean('CFC Created', track_visibility='onchange')
    parent_id = fields.Many2one('hr.employee', string='Manager', track_visibility='onchange')
    coach_id = fields.Many2one('hr.employee', string='Reporting Manager', track_visibility='onchange')
    job_id = fields.Many2one('hr.job', string='Job Position', track_visibility='onchange')
    buddy_assign_date = fields.Date('Buddy Assigned Date')
    idcard_status = fields.Selection([('Uploaded By Employee','Uploaded By Employee'),('Approved','Approved'),('Rejected','Rejected')],'ID Card Status')
    reason = fields.Selection([('Selfie / Whatsapp Image','Selfie / Whatsapp Image'),('Looking upside / downside / leftside','Looking upside / downside / leftside'),('Shadow falling across the face','Shadow falling across the face'),('Size / Blurred / Unfocused','Size / Blurred / Unfocused'),('Other','Other')],'Reason')
    reject_reason = fields.Text('Reject Reason')
    photo_idcard = fields.Char('ID Card Photo')
    candidate_id = fields.Many2one('nf.joining.candidate','Candidate')
    previous_employment = fields.One2many('emp.previous.employment','employee_id','Previous Employment')
    resume_link = fields.Char('Resume')
    education_certificate_link = fields.Char('Highest Educational Certificate')
    pan_card_link = fields.Char('PAN Card')
    aadhar_card_link = fields.Char('Aadhaar Card')
    cancel_cheque_link = fields.Char('Cancelled Cheque/Passbook')
    salary_slip_link = fields.Char("Previous Company's Payslip - 1")
    salary_slip_link1 = fields.Char("Previous Company's Payslip - 2")
    salary_slip_link2 = fields.Char("Previous Company's Payslip - 3")
    resignation_acceptance_link = fields.Char('Resignation Acceptance or Resignation Mail of current/last organization or Relieving Letter')
    religion = fields.Selection([('Hindu','Hindu'),('Muslim','Muslim'),('Christian','Christian'),('Sikh','Sikh'),('Buddhist','Buddhist'),('Jain','Jain'),('Other','Other')],'Religion')
    blood_group = fields.Selection([('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')],'Blood Group')
    other_religion = fields.Char('Other Religion')
    degree_id = fields.Many2one('hr.recruitment.degree','Degree')
    other_degree = fields.Char('Other Degree')
    college_name = fields.Char('Name of College')
    university_name = fields.Char('Board/University Name')
    unviversity_city = fields.Char('University City')
    graduation_year = fields.Char('Year of Graduation')
    total_experience_years = fields.Selection(Years,'Total Experience Years',default='0')
    total_experience_months = fields.Selection(Months,'Total Experience Months',default='0')
    relevant_experience_years = fields.Selection(Years,'Relevant Experience Years',default='0')
    relevant_experience_months = fields.Selection(Months,'Relevant Experience Months',default='0')
    emergency_contact_no = fields.Char('Emergency Contact Number')
    emegency_person_name = fields.Char('Emergency Contact Person')
    emergency_contact_relation = fields.Char('Emergency Contact Relation')
    highest_education = fields.Selection([('SSC','SSC'),('12th','12th'),('Diploma','Diploma'),('Graduation','Graduation'),('Post Graduation','Post Graduation'),('Doctorate','Doctorate')],'Highest Educational Qualification')
    exit_mode = fields.Boolean('In Exit Mode')
    exit_mode_status = fields.Selection([('Yet to Connect','Yet to Connect'),('Trying to Connect But Unable to Reach','Trying to Connect But Unable to Reach'),('Trying to Retain','Trying to Retain'),('Tried to Retain But Unable to Retain','Tried to Retain But Unable to Retain'),('Not a Performer No Need to Retain','Not a Performer No Need to Retain'),('Able to Retain','Able to Retain'),('No need to Retain','No need to Retain'),('Got Better Opportunity/Family Business','Got Better Opportunity/Family Business')],'Final Status',track_visibility='onchange')
    engagement_team_submit = fields.Boolean('Engagement Team Submit')
    engagement_team_comment = fields.Text('People Engagement Team Comment')
    manager_comment = fields.Text('Manager Comment')
    employee_comment = fields.Text('Employee Comment')

    _sql_constraints = [(
                        'unique_employee_no','unique(employee_no)','Employee No. Must be Unique per Employee'
                        ),
                        (
                        'unique_employee_id','unique(nf_emp)','Employee ID Must be Unique per Employee'
                        ),
                        (
                        'unique_bank_account_id','unique(bank_account_id)','Bank Account No Must be Unique per Employee'
                        )]

    @api.onchange('exit_mode')
    def onchange_exit_mode(self):
        if self.exit_mode:
            self.exit_mode_status = 'Yet to Connect'

    @api.multi
    def submit_engagement_team(self):
        for rec in self:
            rec.sudo().write({'engagement_team_submit':True})
            temp_id=self.env['mail.template'].search([('name','=','People Engagement Team Submit')])
            if temp_id:
                temp_id.sudo().send_mail(rec.id)
        return True

    def emp_deactivate(self):
        resource_id = self.resource_id and self.resource_id.id
        last_date = datetime.now().strftime("%Y-%m-%d")
        self.c_erp_last_date = last_date
        print "#################",self.c_erp_last_date
        print "resource_id", resource_id
        if not self.c_emp_replacer:
            raise exceptions.ValidationError(_('Please enter the Active Employee replacer before deactivating the Employee'))
        if not self.last_working_date:
            raise exceptions.ValidationError(_('Please enter the Last Working Date of the Employee'))
        if self.c_nf_chc:
            self.deactivate_cf_dashboard()
        if resource_id:
            self.env.cr.execute("update resource_resource set active='f' where id=%s", (resource_id,))
            print "resource deactivated"

        emp_user = self.user_id and self.user_id.id
        print "emp_user", emp_user
        if emp_user:
            print "user exists with id", emp_user
            self.env.cr.execute("update res_users set active='f' where id=%s", (emp_user,))
            print "user deactivated"

        self.env.cr.execute("select id from hr_contract where employee_id=%s", (self.id,))
        contract_ids = self.env.cr.dictfetchall()
        i = 0
        while i < len(contract_ids):
            contract_id = contract_ids[i]['id']
            self.env.cr.execute("update hr_contract set c_active='f' where id=%s", (contract_id,))
            print "contract updated", contract_id
            i = i + 1
        self.env.cr.execute("update hr_employee set exit_mode='f',exit_done_by=%s,exit_done_date=%s where id=%s", (self.env.uid,last_date,self.id,))
        temp_id=self.env['mail.template'].search([('name','=','Employee Deactivate Notification')])
        if temp_id:
            temp_id.send_mail(self.id)
        return True

    @api.multi
    def deactivate_cf_dashboard(self):
        param = self.env['ir.config_parameter']
        deactivateCFUrl = param.search([('key', '=', 'DeactivateCFUrl')])
        clientIdForOTP = param.search([('key', '=', 'clientIdForOTP')])
        url = deactivateCFUrl.value
        querystring = {"partnerUsername": 'fosindia',
                       "clientId": clientIdForOTP.value,
                       "partnerChildUsername":self.c_nf_chc
                       }
        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }
        response = requests.request("GET", url, headers=headers, params=querystring)
        if response.status_code == 200:
            temp_id=self.env['mail.template'].search([('name','=','Account manager dashboard deactivated')])
            if temp_id:
                temp_id.send_mail(self.id)
        else:
            temp_id=self.env['mail.template'].search([('name','=','Account manager deactivate  API fails')])
            if temp_id:
                temp_id.send_mail(self.id)
        return True

    def emp_reactivate(self):
        cr = self.env.cr
        resource = self.resource_id and self.resource_id.id or False
        emp_user = self.user_id and self.user_id.id or False
        if resource:
            cr.execute("update resource_resource set active='t' where id=%s", (resource,))

        if emp_user:
            cr.execute("update res_users set active='t' where id=%s", (emp_user,))

        cr.execute(
            "update hr_employee set c_emp_replacer=Null, c_replacer_state=Null, c_replacer_city=Null, c_replacer_branch=Null where id=%s",
            (self.id,))

        return True

    @api.onchange('sub_dep')
    def auto_fill_parent_id(self):
        if self.sub_dep.manager_id:
            self.parent_id = self.sub_dep.manager_id


    @api.onchange('c_emp_replacer')
    def auto_filling_replacer_details(self):
        if self.c_emp_replacer:
            self.c_replacer_state = self.c_emp_replacer.state_id.id
            self.c_replacer_city = self.c_emp_replacer.q_city_id.id
            self.c_replacer_branch = self.c_emp_replacer.branch_id.id


    @api.multi
    def create_cf_ria(self,cfc):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for rec in self:
            city=rec.branch_id.c_city_id and rec.branch_id.c_city_id.name or False
            email=rec.work_email
            phone=(rec.mobile_phone).strip()
            if phone and phone[0] == '+':
                phone = phone[3:].strip()
            name=rec.name_related
            video_call_link = "https://appear.in/"+cfc
            param = self.env['ir.config_parameter']
            ria_url = param.sudo().search([('key', '=', 'CreateCFRiaUrl')])
            url = ria_url.value
            client_id = param.sudo().search([('key', '=', 'CreateCFRiaClientId')])
            auth_client_id = param.sudo().search([('key', '=', 'CreateCFRiaAuthClientId')])
            querystring = {'authClientId':auth_client_id.value}
            payload = {
                        "_id": None,
                        "Name": name,
                        "Gender": 0,
                        "Email": email,
                        "PhoneNumber": phone,
                        "ClientId": client_id.value,
                        "IsActive": True,
                        "ActiveHours": [
                          {
                            "From": "06:00:00",
                            "To": "22:00:00",
                            "WeekDay": 1
                          },
                          {
                            "From": "06:00:00",
                            "To": "22:00:00",
                            "WeekDay": 2
                          },
                          {
                            "From": "06:00:00",
                            "To": "22:00:00",
                            "WeekDay": 3
                          },
                          {
                            "From": "06:00:00",
                            "To": "22:00:00",
                            "WeekDay": 4
                          },
                          {
                            "From": "06:00:00",
                            "To": "22:00:00",
                            "WeekDay": 5
                          },
                          {
                            "From": "06:00:00",
                            "To": "22:00:00",
                            "WeekDay": 6
                          }
                        ],
                        "VideoCallLink": video_call_link,
                        "ConcurrentMeetingsCount": 1,
                        "PartnerUsername": cfc,
                        "SupportTicketConfig": None,
                        "CreatedOn": current_time,
                        "UpdatedOn": current_time,
                        "Type": "CHC",
                        "City": city
                      }
            data = json.dumps(payload)
            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache",
            }
            response = requests.request("POST", url, data=data, headers=headers, params=querystring)
            if response:
                response = json.loads(response.text)
                print "ria response ########################",response
                temp_id=self.env['mail.template'].search([('name','=','Account manager dashboard created')])
                if temp_id:
                    temp_id.send_mail(self.id)
            else:
                temp_id=self.env['mail.template'].search([('name','=','CF profile creation in RIA fails')])
                if temp_id:
                    temp_id.send_mail(self.id)

        return True

    @api.multi
    def create_cf_dashboard(self):
        cfc=''
        for rec in self:
            address=rec.branch_id.street or ''
            city=rec.branch_id.c_city_id and rec.branch_id.c_city_id.name or False
            company=rec.company_id and rec.company_id.name or False
            email=rec.work_email
            phone=(rec.mobile_phone).strip()
            if phone and phone[0] == '+':
                phone = phone[3:].strip()
            name=rec.name_related
            branch_server_id=rec.branch_id.server_branch_id or None
            param = self.env['ir.config_parameter']
            cf_url = param.sudo().search([('key', '=', 'CreateCFUrl')])
            url = cf_url.value
            client_id = param.sudo().search([('key', '=', 'CreateCFClientId')])
            identifier = param.sudo().search([('key', '=', 'CreateCFIdentifier')])
            querystring = {'clientId':client_id.value}
            payload = {
                        "address":address,
                        "city":city,
                        "companyName":company,
                        "identifier":identifier.value,
                        "primaryEmail":email,
                        "primaryName":name,
                        "primaryPhone":phone,
                        "type":0,
                        "username":None,
                        "profileAccessType": 3,
                        "profileRoleType": 2,
                        "AssignedBranchId":branch_server_id
                        }

            data = json.dumps(payload)
                            
            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache",
            }
            response = requests.request("POST", url, data=data, headers=headers, params=querystring)
            if response:
                response = json.loads(response.text)
                cfc = response['Result']
                print "##############cfc",cfc
            else:
                raise exceptions.ValidationError(_("CF creation on Dashboard fails."))
            
        return cfc

    @api.multi
    def create_cf_employee(self):
        cr=self.env.cr
        for rec in self:
            cfc=self.create_cf_dashboard()
            if cfc:
                cr.execute("update hr_employee set c_nf_chc=%s where id=%s", (cfc,rec.id,))
                self.create_cf_ria(cfc)
            else:
                raise exceptions.ValidationError(_("CF creation on Dashboard fails."))
        return True

    @api.multi
    def approve_photo_idcard(self):
        for rec in self:
            temp_id=self.env['mail.template'].search([('name','=','Employee Photo ID Card Approved')])
            if temp_id:
                temp_id.send_mail(rec.id)
            self.env.cr.execute("UPDATE hr_employee SET idcard_status = 'Approved', reason = NULL, reject_reason = NULL WHERE id = %s", (rec.id,))
        return True

    @api.multi
    def reject_photo_idcard(self):
        for i in self:
            emp_id = self.env['wiz.reject.photo.idcard'].create({'employee_id':i.id})
            #display wizard
            return {
                'name':_("Reject Photo for ID Card"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'wiz.reject.photo.idcard',
                'res_id': emp_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new'
            }

    @api.multi
    def upload_image(self):
        for i in self:
            emp_id = self.env['wiz.upload.image'].create({'employee_id':i.id})
            #display wizard
            return {
                'name':_("Upload Image"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'wiz.upload.image',
                'res_id': emp_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new'
            }

    @api.multi
    def upload_photo_idcard(self):
        for i in self:
            user=i.user_id.id
            if user:
                if user == self.env.uid:
                    emp_id = self.env['wiz.upload.photo.idcard'].create({'employee_id':i.id})
                    #display wizard
                    return {
                        'name':_("Upload Photo for ID Card"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'wiz.upload.photo.idcard',
                        'res_id': emp_id.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new'
                    }

                else:
                    raise exceptions.ValidationError(_("Sorry, you can not update other employee's photo."))
            else:
                raise exceptions.ValidationError(_("Sorry, you can not upload your photo as your user is not mapped to employee. Please contact HR."))


    @api.multi
    def update_information(self):
        for rec in self:
            user=rec.user_id.id
            if user:
                if user == self.env.uid:
                    family_details=[]
                    family_details = [(0,0,{'name':j.name,'dob':j.dob,'relation':j.relation,'gender':j.gender,'c_cont_num':j.c_cont_num}) for j in rec.family_details if rec.family_details]
                    previous_employment = [(0,0,{'name':j.name,'designation':j.designation,'doj':j.doj,'dol':j.dol,'currently_working':j.currently_working,'ctc':j.ctc,'reason_leaving':j.reason_leaving}) for j in rec.previous_employment if rec.previous_employment]
                    resume=False
                    education_certificate=False
                    pan_card=False
                    aadhar_card=False
                    cancel_cheque=False
                    salary_slip=False
                    salary_slip1=False
                    salary_slip2=False
                    resignation_acceptance=False
                    if rec.resume_link:
                        resume=True
                    if rec.education_certificate_link:
                        education_certificate=True
                    if rec.pan_card_link:
                        pan_card=True
                    if rec.aadhar_card_link:
                        aadhar_card=True
                    if rec.cancel_cheque_link:
                        cancel_cheque=True
                    if rec.salary_slip_link:
                        salary_slip=True
                    if rec.salary_slip_link1:
                        salary_slip1=True
                    if rec.salary_slip_link2:
                        salary_slip2=True
                    if rec.resignation_acceptance_link:
                        resignation_acceptance=True

                    values={'name':rec.name,
                    'full_name':rec.disp_name,
                    'gender':rec.gender,
                    'date_join':rec.join_date,
                    'contact_no':rec.mobile_phone,
                    'alternate_contact':rec.alternate_contact,
                    'personal_email':rec.personal_email,
                    'highest_education':rec.highest_education,
                    'father_name':rec.emp_father,
                    'nationality':rec.country_id and rec.country_id.id or False,
                    'voter_id':rec.c_voter_id,
                    'pan_no':rec.pan,
                    'aadhar_no':rec.aadhar_no,
                    'passport_no':rec.passport_id,
                    'previous_uan':rec.c_pre_uan,
                    'previous_pf':rec.c_pf_num,
                    'current_street1':rec.c_street,
                    'current_street2':rec.c_street2,
                    'current_city':rec.c_city_id and rec.c_city_id.id or False,
                    'current_state':rec.c_state_id and rec.c_state_id.id or False,
                    'current_country':rec.c_country_id and rec.c_country_id.id or False,
                    'current_zip':rec.c_zip,
                    'is_address_same':rec.is_address,
                    'permanent_street1':rec.p_street,
                    'permanent_street2':rec.p_street2,
                    'permanent_city':rec.p_city_id and rec.p_city_id.id or False,
                    'permanent_state':rec.p_state_id and rec.p_state_id.id or False,
                    'permanent_country':rec.p_country_id and rec.p_country_id.id or False,
                    'permanent_zip':rec.p_zip,
                    'birth_date':rec.birthday,
                    'marital_status':rec.marital,
                    'anniversary_date':rec.anniversary_date,
                    'disability':rec.disability,
                    'driving_license_no':rec.c_dl_id,
                    'family_details':family_details,
                    'previous_employment':previous_employment,
                    'pan_updated':pan_card,
                    'resume_updated':resume,
                    'aadhar_updated':aadhar_card,
                    'cheque_updated':cancel_cheque,
                    'salary_slip_updated':salary_slip,
                    'salary_slip1_updated':salary_slip1,
                    'salary_slip2_updated':salary_slip2,
                    'certificate_updated':education_certificate,
                    'resignation_updated':resignation_acceptance,
                    'religion':rec.religion,
                    'other_religion':rec.other_religion,
                    'blood_group':rec.blood_group,
                    'degree_id':rec.degree_id and rec.degree_id.id or False,
                    'other_degree':rec.other_degree,
                    'college_name':rec.college_name,
                    'university_name':rec.university_name,
                    'unviversity_city':rec.unviversity_city,
                    'graduation_year':rec.graduation_year,
                    'total_experience_years':rec.total_experience_years,
                    'total_experience_months':rec.total_experience_months,
                    'relevant_experience_years':rec.relevant_experience_years,
                    'relevant_experience_months':rec.relevant_experience_months,
                    'emegency_person_name':rec.emegency_person_name,
                    'emergency_contact_no':rec.emergency_contact_no,
                    'emergency_contact_relation':rec.emergency_contact_relation,
                    'employee_id':rec.id,
                    'emp_size':rec.emp_size
                    }

                    emp_info_id = self.env['wiz.employee.information'].create(values)
                    #display wizard
                    return {
                        'name':_("Update Information"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'wiz.employee.information',
                        'res_id': emp_info_id.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new'
                    }
                else:
                    raise exceptions.ValidationError(_("Sorry, you can not update other employee's information."))
            else:
                raise exceptions.ValidationError(_("Sorry, you can not update your information as your user is not mapped to employee. Please contact HR."))

    @api.multi
    def close_update(self):
        for i in self:
            i.write({'info_updated': True})
            # info_obj = self.env['wiz.employee.information']
            # info_id = info_obj.search([('employee_id', '=', i.id)])
            # info_id.unlink()
        return True

    @api.multi
    def open_update(self):
        for i in self:
            i.write({'info_updated':False})
        return True
    
    @api.onchange('is_address')
    def onchange_address(self):
        if self.is_address:
            self.p_street = self.c_street
            self.p_street2 = self.c_street2
            self.p_city_id= self.c_city_id.id
            self.p_state_id = self.c_state_id
            self.p_country_id = self.c_country_id
            self.p_zip = self.c_zip
            
        else:
            self.p_street = ''
            self.p_street2 = ''
            self.p_city = ''
            self.p_state_id = False
            self.p_zip = ''
            
    @api.onchange('resignation_type')
    def onchange_resignation_type(self):
        if not self.resignation_type  == 'Voluntary':
            self.voluntary = False
        
        if not self.resignation_type  == 'Involuntary':
            self.involuntary = False           
                


class IdCard(models.Model):
    _name = 'id.card'
    
    name = fields.Char('Name')
    code = fields.Char('code')
    
    
class emp_family_detail(models.Model):
    _name = 'emp.family.detail'
    
    name = fields.Char('Name')
    dob = fields.Date('Date of Birth')
    relation = fields.Selection([('Self','Self'),('Spouse','Spouse'),('Father','Father'),('Mother','Mother'),('Brother','Brother'),('Sister','Sister'),('Son','Son'),('Daughter','Daughter')],'Relation')
    gender = fields.Selection([('male','Male'),('female','Female'),('other','Other')],string="Gender")
    employee_id = fields.Many2one('hr.employee','Employee')
    c_cont_num = fields.Char('Contact Number')

class emp_previous_employment(models.Model):
    _name = 'emp.previous.employment'
    _description = 'Employee Previous Employment'

    name = fields.Char('Organization Name')
    designation = fields.Char('Designation')
    doj = fields.Date('Date of Joining')
    dol = fields.Date('Date of Leaving')
    currently_working = fields.Boolean('Currently Working')
    ctc = fields.Char('CTC(Per Annum)')
    reason_leaving = fields.Text('Reason For Leaving')
    employee_id = fields.Many2one('hr.employee','Employee')

class ouc_city(models.Model):
    _name = 'ouc.city'

    name = fields.Char(string='City Name', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    active = fields.Boolean(string='Active', default=True)

class ouc_fos_handle(models.Model):
    _name='ouc.fos.handle'
    _rec_name='name'

    name=fields.Char(string="name",required=True)


    _sql_constraints = [(
    'unique_fos_name', 'unique(name)', 'name should be unique'
     )]


class ouc_res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    branch_name = fields.Char('Branch Name')
    c_bank_name = fields.Char('Bank Name')
    ifsc_code = fields.Char('IFSC Code')
    logs = fields.One2many('res.partner.bank.log','bank_id','Logs')

    @api.model
    def create(self,vals):
        res=super(ouc_res_partner_bank,self).create(vals)
        log=self.env['res.partner.bank.log']
        logs=repr(vals)+' fields edited On '+(datetime.now() + timedelta(seconds=19800)).strftime('%d-%m-%Y %H:%M:%S')
        log.create({'user_id':self.env.user.id,'name':logs,'bank_id':res.id})           
        return res

    @api.multi
    def write(self,vals):
        res=super(ouc_res_partner_bank,self).write(vals)
        log=self.env['res.partner.bank.log']
        for i in self:
            logs=repr(vals)+' fields edited On '+(datetime.now() + timedelta(seconds=19800)).strftime('%d-%m-%Y %H:%M:%S')
            log.create({'user_id':self.env.user.id,'name':logs,'bank_id':i.id})           
        return True

class res_partner_bank_log(models.Model):
    _name = 'res.partner.bank.log'

    name = fields.Char('Description')
    bank_id = fields.Many2one('res.partner.bank','Bank')
    user_id = fields.Many2one('res.users','User')
