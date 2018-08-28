from odoo import api, fields, models, _
from odoo import exceptions
from odoo.exceptions import ValidationError,Warning
import time
from odoo.fields import Date
import collections
import requests
import json
import base64

Years = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11'),('12','12'),('13','13'),('14','14'),('15','15'),('16','16'),('17','17'),('18','18'),('19','19'),('20','20'),('21','21'),('22','22'),('23','23'),('24','24'),('25','25')]
Months = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11')]

class wiz_employee_information(models.TransientModel):
    _name="wiz.employee.information"

    def default_country(self):
        return self.env['res.country'].search([('name','=','India')])
    
    name = fields.Char('Name as Per PAN Card')
    full_name = fields.Char('Full Name')
    gender = fields.Selection([('male', 'Male'),('female', 'Female'),('other', 'Other')],'Gender')
    birth_date = fields.Date('Date of Birth')
    religion = fields.Selection([('Hindu','Hindu'),('Muslim','Muslim'),('Christian','Christian'),('Sikh','Sikh'),('Buddhist','Buddhist'),('Jain','Jain'),('Other','Other')],'Religion')
    other_religion = fields.Char('Other Religion')
    disability = fields.Selection([('P','Yes - Partially Disabled'),('F','Yes - Fully Disabled'),('N','No')],'Disability')
    blood_group = fields.Selection([('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')],'Blood Group')
    marital_status = fields.Selection([('single', 'Single'),('married', 'Married'),('widower', 'Widower'),('divorced', 'Divorced')], string='Marital Status',default='single')
    anniversary_date = fields.Date('Date of Marriage')
    father_name = fields.Char("Father's Name as per Aadhaar Card")
    nationality = fields.Many2one('res.country','Nationality(Country)')
    aadhar_no = fields.Char('Aadhaar Number')
    pan_no = fields.Char('PAN Number')
    voter_id = fields.Char('Voter ID')
    passport_no = fields.Char('Passport Number')
    driving_license_no = fields.Char('Driving Licence Number')
    previous_uan = fields.Char('Previous UAN')
    previous_pf = fields.Char('Previous PF Number')
    contact_no = fields.Char('Contact Number')
    personal_email = fields.Char('Personal Email')
    current_street1 = fields.Char('Current Street1')
    current_street2 = fields.Char('Current Street2')
    current_city = fields.Many2one('ouc.city','Current City')
    current_state = fields.Many2one('res.country.state','Current State',related='current_city.state_id')
    current_country = fields.Many2one('res.country','Current Country',related='current_city.country_id')
    current_zip = fields.Char('Current Zip')
    is_address_same = fields.Boolean('Is Permanent Address Same as Current Address')
    permanent_street1 = fields.Char('Permanent Street1')
    permanent_street2 = fields.Char('Permanent Street2')
    permanent_city = fields.Many2one('ouc.city','Permanent City')
    permanent_state = fields.Many2one('res.country.state','Permanent State',related='permanent_city.state_id')
    permanent_country = fields.Many2one('res.country','Permanent Country',related='current_city.country_id')
    permanent_zip = fields.Char('Permanent Zip')
    emergency_contact_no = fields.Char('Emergency Contact Number')
    emegency_person_name = fields.Char('Emergency Contact Person')
    emergency_contact_relation = fields.Char('Emergency Contact Relation')
    family_details = fields.One2many('wiz.family.detail','wiz_emp_id','Family Details')
    highest_education = fields.Selection([('SSC','SSC'),('12th','12th'),('Diploma','Diploma'),('Graduation','Graduation'),('Post Graduation','Post Graduation'),('Doctorate','Doctorate')],'Highest Educational Qualification')
    degree_id = fields.Many2one('hr.recruitment.degree','Degree')
    other_degree = fields.Char('Other Degree')
    college_name = fields.Char('Name of College')
    university_name = fields.Char('Board/University Name')
    unviversity_city = fields.Char('University City')
    graduation_year = fields.Char('Year of Graduation')
    resume_filename = fields.Char('Resume Filename')
    resume = fields.Binary('Resume')
    education_certificate_filename = fields.Char('Highest Educational Filename')
    education_certificate = fields.Binary('Highest Educational Certificate')
    pan_card_filename = fields.Char('PAN Card Filename')
    pan_card = fields.Binary('PAN Card')
    aadhar_card_filename = fields.Char('Aadhaar Card Filename')
    aadhar_card = fields.Binary('Aadhaar Card')
    cancel_cheque_filename = fields.Char('Cancelled Cheque/Passbook Filename')
    cancel_cheque = fields.Binary('Cancelled Cheque/Passbook')
    salary_slip_filename = fields.Char("Previous Company's Payslip - 1 Filename")
    salary_slip = fields.Binary("Previous Company's Payslip - 1")
    salary_slip_filename1 = fields.Char("Previous Company's Payslip - 2 Filename")
    salary_slip1 = fields.Binary("Previous Company's Payslip - 2")
    salary_slip_filename2 = fields.Char("Previous Company's Payslip - 3 Filename")
    salary_slip2 = fields.Binary("Previous Company's Payslip - 3")
    resignation_acceptance_filename = fields.Char('Resignation Acceptance Filename')
    resignation_acceptance = fields.Binary('Resignation Acceptance or Resignation Mail of current/last organization/Relieving Letter')
    total_experience_years = fields.Selection(Years,'Total Experience Years',default='0')
    total_experience_months = fields.Selection(Months,'Total Experience Months',default='0')
    relevant_experience_years = fields.Selection(Years,'Relevant Experience Years',default='0')
    relevant_experience_months = fields.Selection(Months,'Relevant Experience Months',default='0')
    previous_employment = fields.One2many('wiz.previous.employment','wiz_emp_id','Previous Employment')
    pan_updated = fields.Boolean('PAN Updated')
    resume_updated = fields.Boolean('Resume Updated')
    aadhar_updated = fields.Boolean('Aadhaar Updated')
    cheque_updated = fields.Boolean('Cheque Updated')
    salary_slip_updated = fields.Boolean('Salary Slip Updated')
    salary_slip1_updated = fields.Boolean('Salary Slip1 Updated')
    salary_slip2_updated = fields.Boolean('Salary Slip2 Updated')
    certificate_updated = fields.Boolean('Certificate Updated')
    resignation_updated = fields.Boolean('Resignation Updated')
    employee_id = fields.Many2one('hr.employee','Employee')
    emp_size=fields.Char('Employee Shirt Size')
    alternate_contact=fields.Char('Alternate Contact Number')

    @api.onchange('aadhar_no')
    def onchange_aadhar_no(self):
        if self.aadhar_no:
            try:
                aadhar_no = int(self.aadhar_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should not contain characters.'))
            if len(self.aadhar_no) != 12:
                self.aadhar_no = False
                raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should be of 12 digits.'))

    @api.onchange('contact_no')
    def onchange_contact_no(self):
        if self.contact_no:
            try:
                contact_no = int(self.contact_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should not contain characters.'))
            if len(self.contact_no) != 10:
                self.contact_no = False
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should be of 10 digits.'))

    @api.onchange('alternate_contact')
    def onchange_alternate_contact(self):
        if self.alternate_contact:
            try:
                alternate_contact = int(self.alternate_contact)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should not contain characters.'))
            if len(self.alternate_contact) != 10:
                self.alternate_contact = False
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should be of 10 digits.'))

    @api.onchange('emergency_contact_no')
    def onchange_emergency_contact_no(self):
        if self.emergency_contact_no:
            try:
                emergency_contact_no = int(self.emergency_contact_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Emegerncy Contact Number. It should not contain characters.'))
            if len(self.emergency_contact_no) != 10:
                self.emergency_contact_no = False
                raise exceptions.ValidationError(_('Please enter valid Emergency Contact Number. It should be of 10 digits.'))

    @api.onchange('pan_no')
    def onchange_pan_no(self):
        if self.pan_no and len(self.pan_no) != 10:
            self.pan_no = False
            raise exceptions.ValidationError(_('Please enter valid PAN Number. It should be of 10 characters.'))

    @api.onchange('personal_email')
    def onchange_personal_email(self):
        if self.personal_email and '@' not in self.personal_email:
            self.personal_email = False
            raise exceptions.ValidationError(_('Please enter valid Email ID.'))

    def get_doc_link(self,file_name,file_body):
        file_ext = 'jpeg'
        param = self.env['ir.config_parameter']
        filename = file_name
        if filename:
            filename = file_name.split('.')
            if filename and len(filename) > 1:
                file_ext = filename[-1].lower()
                if file_ext == 'jpg':
                    file_ext = 'jpeg'
                elif file_ext == 'doc':
                    file_ext = 'docx'
            else:
                raise ValidationError("Please check your file that you are uploading. It should be with proper extension.")
        param = self.env['ir.config_parameter']
        s2LinkUrlAws = param.search([('key', '=', 's2LinkUrlAws')])
        s3_link_url = s2LinkUrlAws.value
        payload = {
                   "fileData": file_body,
                   "fileName": file_name,
                   "fileCategory": 2,
                   "fileType": file_ext
                   }
        data = json.dumps(payload)
        headers = {
            'content-type': "application/json"
        }
        response = requests.request("POST", s3_link_url, data=data, headers=headers)
        response = json.loads(response.text)
        if response.get('body', ''):
            link = response.get('body')['result']
        return link

    @api.onchange('is_address_same')
    def onchange_address(self):
        if self.is_address_same:
            self.permanent_street1 = self.current_street1
            self.permanent_street2 = self.current_street2
            self.permanent_city= self.current_city.id
            self.permanent_state = self.current_state.id
            self.permanent_country = self.current_country.id
            self.permanent_zip = self.current_zip

    @api.multi
    def update_info(self):
        for rec in self:
            if rec.employee_id:
                family_details=[]
                previous_employment=[]
                resume=''
                education_certificate=''
                pan_card=''
                aadhar_card=''
                cancel_cheque=''
                salary_slip=''
                salary_slip1=''
                salary_slip2=''
                resignation_acceptance=''
                self.env.cr.execute("DELETE FROM emp_family_detail WHERE employee_id = {}".format(rec.employee_id.id))
                family_details = [(0,0,{'name':j.name,'dob':j.dob,'relation':j.relation,'gender':j.gender,'c_cont_num':j.c_cont_num}) for j in rec.family_details if rec.family_details]
                self.env.cr.execute("DELETE FROM emp_previous_employment WHERE employee_id = {}".format(rec.employee_id.id))
                previous_employment = [(0,0,{'name':j.name,'designation':j.designation,'doj':j.doj,'dol':j.dol,'currently_working':j.currently_working,'ctc':j.ctc,'reason_leaving':j.reason_leaving}) for j in rec.previous_employment if rec.previous_employment]
                if rec.resume_filename and rec.resume:
                    resume=rec.get_doc_link(rec.resume_filename,rec.resume)
                if rec.education_certificate_filename and rec.education_certificate:
                    education_certificate=rec.get_doc_link(rec.education_certificate_filename,rec.education_certificate)
                if rec.pan_card_filename and rec.pan_card:
                    pan_card=rec.get_doc_link(rec.pan_card_filename,rec.pan_card)
                if rec.aadhar_card_filename and rec.aadhar_card:
                    aadhar_card=rec.get_doc_link(rec.aadhar_card_filename,rec.aadhar_card)
                if rec.cancel_cheque_filename and rec.cancel_cheque:
                    cancel_cheque=rec.get_doc_link(rec.cancel_cheque_filename,rec.cancel_cheque)
                if rec.salary_slip_filename and rec.salary_slip:
                    salary_slip=rec.get_doc_link(rec.salary_slip_filename,rec.salary_slip)
                if rec.salary_slip_filename1 and rec.salary_slip1:
                    salary_slip1=rec.get_doc_link(rec.salary_slip_filename1,rec.salary_slip1)
                if rec.salary_slip_filename2 and rec.salary_slip2:
                    salary_slip2=rec.get_doc_link(rec.salary_slip_filename2,rec.salary_slip2)
                if rec.resignation_acceptance_filename and rec.resignation_acceptance:
                    resignation_acceptance=rec.get_doc_link(rec.resignation_acceptance_filename,rec.resignation_acceptance)
                if rec.pan_no and len(rec.pan_no) != 10:
                    raise exceptions.ValidationError(_('Please enter valid PAN Number. It should be of 10 characters.'))
                if rec.aadhar_no:
                    try:
                        aadhar = int(rec.aadhar_no)
                    except ValueError:
                        raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should not contain characters.'))
                    if len(rec.aadhar_no) != 12:
                        raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should be of 12 digits.'))
                if rec.contact_no:
                    try:
                        contact = int(rec.contact_no)
                    except ValueError:
                        raise exceptions.ValidationError(_('Please enter valid Contact Number. It should not contain characters.'))
                    if len(rec.contact_no) != 10:
                        raise exceptions.ValidationError(_('Please enter valid Contact Number. It should be of 10 digits.'))
                if rec.alternate_contact:
                    try:
                        alternate_contact = int(rec.alternate_contact)
                    except ValueError:
                        raise exceptions.ValidationError(_('Please enter valid Contact Number. It should not contain characters.'))
                    if len(rec.alternate_contact) != 10:
                        rec.alternate_contact = False
                        raise exceptions.ValidationError(_('Please enter valid Contact Number. It should be of 10 digits.'))
                if rec.emergency_contact_no:
                    try:
                        emergency_contact = int(rec.emergency_contact_no)
                    except ValueError:
                        raise exceptions.ValidationError(_('Please enter valid Emergency Contact Number. It should not contain characters.'))
                    if len(rec.emergency_contact_no) != 10:
                        raise exceptions.ValidationError(_('Please enter valid Emergency Contact Number. It should be of 10 digits.'))
                if rec.personal_email and '@' not in rec.personal_email:
                    raise exceptions.ValidationError(_('Please enter valid Email ID.'))
                if rec.total_experience_months != '0' or rec.total_experience_years != '0':
                    if not rec.previous_employment:
                        raise exceptions.ValidationError(_('Please enter previous employment details.'))
                if not rec.family_details:
                    raise exceptions.ValidationError(_('Please enter family details.'))
                vals = {'name':rec.name,
                    'disp_name':rec.full_name,
                    'gender':rec.gender,
                    'mobile_phone':rec.contact_no,
                    'personal_email':rec.personal_email,
                    'alternate_contact':rec.alternate_contact,
                    'highest_education':rec.highest_education,
                    'pan':rec.pan_no,
                    'emp_father':rec.father_name,
                    'country_id':rec.nationality and rec.nationality.id or False,
                    'aadhar_no':rec.aadhar_no,
                    'c_voter_id':rec.voter_id,
                    'passport_id':rec.passport_no,
                    'c_pre_uan':rec.previous_uan,
                    'c_pf_num':rec.previous_pf,
                    'c_street':rec.current_street1,
                    'c_street2':rec.current_street2,
                    'c_city_id':rec.current_city and rec.current_city.id or False,
                    'c_state_id':rec.current_state and rec.current_state.id or False,
                    'c_country_id':rec.current_country and rec.current_country.id or False,
                    'c_zip':rec.current_zip,
                    'is_address':rec.is_address_same,
                    'p_street':rec.permanent_street1,
                    'p_street2':rec.permanent_street2,
                    'p_city_id':rec.permanent_city and rec.permanent_city.id or False,
                    'p_state_id':rec.permanent_state and rec.permanent_state.id or False,
                    'p_country_id':rec.permanent_country and rec.permanent_country.id or False,
                    'p_zip':rec.permanent_zip,
                    'birthday':rec.birth_date,
                    'marital':rec.marital_status,
                    'anniversary_date':rec.anniversary_date,
                    'disability':rec.disability,
                    'c_dl_id':rec.driving_license_no,
                    'family_details':family_details,
                    'previous_employment':previous_employment,
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
                    'emp_size':rec.emp_size
                    }

                if not rec.pan_updated:
                    vals.update({'pan_card_link':pan_card})
                if not rec.aadhar_updated:
                    vals.update({'aadhar_card_link':aadhar_card})
                if not rec.cheque_updated:
                    vals.update({'cancel_cheque_link':cancel_cheque})
                if not rec.salary_slip_updated:
                    vals.update({'salary_slip_link':salary_slip})
                if not rec.salary_slip1_updated:
                    vals.update({'salary_slip_link1':salary_slip1})
                if not rec.salary_slip2_updated:
                    vals.update({'salary_slip_link2':salary_slip2})
                if not rec.resignation_updated:
                    vals.update({'resignation_acceptance_link':resignation_acceptance})
                if not rec.certificate_updated:
                    vals.update({'education_certificate_link':education_certificate})
                if not rec.resume_updated:
                    vals.update({'resume_link':resume,})
                
                rec.employee_id.sudo().write(vals)

        return {'type':'ir.actions.act_window_close'}


class wiz_family_detail(models.TransientModel):
    _name = 'wiz.family.detail'
    
    name = fields.Char('Name')
    dob = fields.Date('Date of Birth')
    relation = fields.Selection([('Self','Self'),('Spouse','Spouse'),('Father','Father'),('Mother','Mother'),('Brother','Brother'),('Sister','Sister'),('Son','Son'),('Daughter','Daughter')],'Relation')
    gender = fields.Selection([('male','Male'),('female','Female'),('other','Other')],string="Gender")
    employee_id = fields.Many2one('hr.employee','Employee')
    wiz_emp_id = fields.Many2one('wiz.employee.information','Wiz Employee')
    c_cont_num = fields.Char('Contact Number')

class wiz_previous_employment(models.TransientModel):
    _name = 'wiz.previous.employment'
    _description = 'Wizard for Previous Employment'

    name = fields.Char('Organization Name')
    designation = fields.Char('Designation')
    doj = fields.Date('Date of Joining')
    dol = fields.Date('Date of Leaving')
    currently_working = fields.Boolean('Currently Working')
    ctc = fields.Char('CTC(Per Annum)')
    reason_leaving = fields.Text('Reason For Leaving')
    wiz_emp_id = fields.Many2one('wiz.employee.information','Wiz Employee')

    
class ouc_city(models.Model):
    _name = 'ouc.city'

    name = fields.Char(string='City Name', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    active = fields.Boolean(string='Active', default=True)

class wiz_emp_join_date(models.TransientModel):
    _name = 'wiz.emp.join'

    join_date = fields.Date('Date Of Joining')

    def update_join_date(self):
        active_model = self.env.context.get('active_model')
        if active_model:
            obj_id = self.env[active_model].browse(self.env.context.get('active_id'))
            if self.join_date:
                self.env.cr.execute("select leave_allocation (%s)", (obj_id.id,))
                obj_id.join_date = self.join_date


class wiz_upload_image(models.TransientModel):
    _name = 'wiz.upload.image'

    employee_id = fields.Many2one('hr.employee','Employee')
    image = fields.Binary('Image')

    @api.multi
    def upload_image(self):
        emp=self.employee_id
        for rec in self:
            if emp:
                emp.sudo().write({'image':rec.image})

        return True

class wiz_upload_photo_idcard(models.TransientModel):
    _name = 'wiz.upload.photo.idcard'

    employee_id = fields.Many2one('hr.employee','Employee')
    photo = fields.Binary('Photo')
    photo_filename = fields.Char('Filename')

    @api.multi
    def upload_photo(self):
        emp=self.employee_id
        link = ''
        for rec in self:
            if emp:
                file_ext = 'jpeg'
                param = self.env['ir.config_parameter']
                file_name = rec.photo_filename
                if file_name:
                    filename = file_name.split('.')
                    if filename and len(filename) > 1:
                        file_ext = filename[-1].lower()
                        if file_ext == 'jpg':
                            file_ext = 'jpeg'
                    else:
                        raise ValidationError("Please check your file that you are uploading. It should be with proper extension.")
                file_body = rec.photo
                s2LinkUrlAws = param.search([('key', '=', 's2LinkUrlAws')])
                s3_link_url = s2LinkUrlAws.value
                payload = {
                           "fileData": file_body,
                           "fileName": file_name,
                           "fileCategory": 2,
                           "fileType": file_ext
                           }
                data = json.dumps(payload)
                headers = {
                    'content-type': "application/json"
                }
                response = requests.request("POST", s3_link_url, data=data, headers=headers)
                response = json.loads(response.text)
                if response.get('body', ''):
                    link = response.get('body')['result']
                emp.sudo().write({'idcard_status':'Uploaded By Employee','photo_idcard':link})

        return True

class wiz_reject_photo_idcard(models.TransientModel):
    _name = 'wiz.reject.photo.idcard'

    employee_id = fields.Many2one('hr.employee','Employee')
    reason = fields.Selection([('Selfie / Whatsapp Image','Selfie / Whatsapp Image'),('Looking upside / downside / leftside','Looking upside / downside / leftside'),('Shadow falling across the face','Shadow falling across the face'),('Size / Blurred / Unfocused','Size / Blurred / Unfocused'),('Other','Other')],'Reason')
    reject_reason = fields.Text('Reject Reason')

    @api.multi
    def reject_photo(self):
        emp=self.employee_id
        for rec in self:
            if emp:
                emp.sudo().write({'idcard_status':'Rejected','reason':rec.reason,'reject_reason':rec.reject_reason})
                temp_id=self.env['mail.template'].search([('name','=','Reject Employee Photo')])
                if temp_id:
                    temp_id.send_mail(rec.employee_id.id)

        return True