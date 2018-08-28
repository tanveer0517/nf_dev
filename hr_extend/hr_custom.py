from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import re
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from odoo import exceptions
from odoo.exceptions import ValidationError, Warning
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib2 import Request, urlopen
import json,urllib,urllib2

class hrr_rates(models.Model):
    _name = 'hrr.rates'
    
    name=fields.Char('Name')
    area_from=fields.Float('Area From')
    area_to=fields.Float('Area To')
    amount=fields.Float('Amount')
                
class fin_year_mst(models.Model):
    _name = 'fin.year.mst'
      
    name=fields.Char('Code')
    start_date=fields.Date('Start Date')
    end_date=fields.Date('End Date')
                
class bank_mst(models.Model):
    _name = 'bank.mst'
    
    name=fields.Char('Name')
    code=fields.Char('Code')
                
class con_recovery_rates(models.Model):
    _name = 'con.recovery.rates'
    
     
    name=fields.Char('Name')
    grade_id=fields.Many2one('hr.grade','Grade')
    max_journey=fields.Float('Maximum Journey')
    amount=fields.Float('Amount')
    pattern= fields.Selection([('IDA','IDA'),('CDA','CDA')],"Pattern")
                

class hr_grade(models.Model):
    _name = 'hr.grade'
    
    name=fields.Char('Grade',required='True')
    level=fields.Char('Level')
    cadre_id=fields.Many2one('emp.cadre','Cadre')
#     payscale_id=fields.Many2one('hr.payscale','Payscale')
#     new_payscale_id=fields.Many2one('hr.payscale','New Payscale')
                
    
class hr_professional_tax(models.Model):
    _name = 'hr.professional.tax'
     
    name=fields.Char('Name')
    state_id=fields.Many2one('res.country.state','State')
    amount_from=fields.Float('Amount From')
    amount_to=fields.Float('Amount To')
    pro_tax_amount=fields.Float('Tax Amount')
    month_from= fields.Selection([('1','JAN'),('2','FEB'),('3','MAR'),('4','APR'),('5','MAY'),('6','JUN'),('7','JUL'),('8','AUG'),('9','SEP'),('10','OCT'),('11','NOV'),('12','DEC')],'Month From')
    month_to= fields.Selection([('1','JAN'),('2','FEB'),('3','MAR'),('4','APR'),('5','MAY'),('6','JUN'),('7','JUL'),('8','AUG'),('9','SEP'),('10','OCT'),('11','NOV'),('12','DEC')],'Month To')
    half_yearly=fields.Boolean('Half Yearly')
    gross_annual=fields.Boolean('Gross Annual')
                

class da_rates(models.Model): 
    _name = 'da.rates'
      
    name=fields.Char('Description',required='True')
    effective_from=fields.Date('Effective From Date',required='True')
    effective_to=fields.Date('Effective End Date')
    pattern=fields.Selection([('IDA','IDA'),('CDA','CDA')],"DA Pattern",required='True')
    rate=fields.Float('Rate(%)',required='True')
    active=fields.Boolean('Active')
                
class hr_location(models.Model):
    _name = 'hr.location'
      
    code=fields.Char('Code')
    name=fields.Char('Name',required='True')
    state_id=fields.Many2one('res.country.state','State')
    type=fields.Selection([('X','X'),('Y','Y'),('Z','Z')],'Type')
    hra_rates=fields.Float('HRA Rates(%)')
    type_for_conveyance=fields.Selection([('X','X'),('Y','Y'),('Z','Z')],'Type For Conveyance')
    region_id=fields.Many2one('employee.region','Region')
    is_metro=fields.Selection([('Y','YES'),('N','NO')],'Is Metro' )
    professional_tax=fields.Boolean('Professional Tax')
    professional_tax_type=fields.Selection([('F','Fixed'),('V','Variable')],'Tax Type' )
    pro_tax_amount=fields.Float('Amount')
                
class emp_cadre(models.Model):
    _name = 'emp.cadre'
    
    name = fields.Char('Name',required='True')
                
class state_mst(models.Model):
    _name = 'state.mst'
    name= fields.Char('Name',required='True')
    code= fields.Char('Code',required='True')
                
    
class employee_unit(models.Model):
    _name = 'employee.unit'
      
    name= fields.Char('Name',required='True')
    code= fields.Char('Code',required='True')
    region_id=fields.Many2one('employee.region','Region')
                
class employee_region(models.Model):
    _name = 'employee.region'
      
    name=fields.Char('Name',required='True')
    code=fields.Char('Code',required='True')
    company_id=fields.Many2one('res.company','Zone')
                
class employee_type(models.Model):
    _name = 'employee.type'
    
      
    name=fields.Char('Name',required='True')

class nf_paathshala_feedback(models.Model):
    _name = 'nf.paathshala.feedback'
    _description = 'Paathshala Feedback'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char(string='Paathshala Batch',track_visibility='onchange')
    pathsala_city = fields.Many2one('ouc.city',string='Paathshala Hub',track_visibility='onchange')
    date_from = fields.Date('From',track_visibility='onchange')
    date_to = fields.Date('To',track_visibility='onchange')
    trainer_name = fields.Many2one('hr.employee','Trainer Name',track_visibility='onchange')
    no_attendees = fields.Char('No of Attendees',track_visibility='onchange')
    submit = fields.Boolean('Submit')
    feedback_line = fields.One2many('nf.paathshala.feedback.line','paathshala_feedback','Paathshala Feedback Line')

    @api.onchange('date_from','date_to')
    def onchange_date(self):
        date_to=self.date_to
        date_from=self.date_from
        if date_from and date_to:
            if date_to<date_from:
                raise exceptions.ValidationError(_('Sorry, Please check the Date From and Date To. Date To should not be smaller than Date From.'))

    @api.multi
    def send_email(self):
        cr = self.env.cr
        rec = """ """
        for obj in self.feedback_line:
            fnt_clr = "green"
            if obj.low_score:
                fnt_clr = "red"
            feedback = obj.feedback
            desc=""
            if feedback:
                feedback = feedback.encode('ascii', 'ignore').decode('ascii').splitlines()
                for feed in feedback:
                    desc+=str(feed)+"<br/>"
            rec = rec +  """<tr width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
                          <td width="15%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(obj.employee_id.name_related)+"""</font></td>
                          <td width="10%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(obj.emp_id)+"""</font></td>
                          <td width="15%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(obj.branch_id and obj.branch_id.name or '')+"""</font></td>
                          <td width="15%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(obj.designation or '')+"""</font></td>
                          <td width="15%" align="center" class="text-center"><font color="""+str(fnt_clr)+""">"""+str(obj.paathshala_score or '')+"""</font></td>
                          <td width="30%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(desc)+"""</font></td>
                    <tr>
                    <tr width="100%" colspan="6" height="5"></tr>
                    """

        from_date = (datetime.strptime(self.date_from, '%Y-%m-%d')).strftime('%d/%b/%Y')
        to_date = (datetime.strptime(self.date_to, '%Y-%m-%d')).strftime('%d/%b/%Y')
        mail_subject = "Paathshala Feedback :" + " " +str(from_date)+" to "+str(to_date)
        html = """<!DOCTYPE html>
                                 <html>

                                   <body>
                                     <table style="width:100%">
                                          <tr>
                                             <td width="25%" class="text-left"> <b>Paathshala Batch: </b> </td>
                                             <td width="25%" class="text-left">"""+str(self.name)+"""</td>
                                             <td width="25%" class="text-left"> <b>Paathshala Hub: </b> </td>
                                             <td width="25%" class="text-left">"""+str(self.pathsala_city and self.pathsala_city.name or '')+"""</td>
                                          </tr>
                                          <tr>
                                             <td width="25%" class="text-left"> <b>Date From: </b> </td>
                                             <td width="25%" class="text-left">"""+str(from_date)+"""</td>
                                             <td width="25%" class="text-left"> <b>Date To: </b> </td>
                                             <td width="25%" class="text-left">"""+str(to_date)+"""</td>
                                          </tr>
                                          <tr>
                                             <td width="25%" class="text-left"> <b>No of Attendees: </b> </td>
                                             <td width="25%" class="text-left">"""+str(self.no_attendees)+"""</td>
                                             <td width="25%" class="text-left"> <b>Trainer Name: </b> </td>
                                             <td width="25%" class="text-left">"""+str(self.trainer_name and self.trainer_name.name_related or '')+"""</td>
                                          </tr>

                                     </table>
                                          <br/>
                                     <table width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
                                     <tr width="100%" class="border-black">
                                          <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Employee</b> </td>
                                          <td width="10%"  class="text-left" style="border-bottom: 1px solid black;"> <b>Employee ID</b> </td>
                                          <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Branch</b> </td>
                                          <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Designation</b> </td>
                                          <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Paathshala Score</b> </td>
                                          <td width="30%" class="text-left" style="border-bottom: 1px solid black;"> <b>Feedback</b> </td>
                                      </tr>

                                          """+str(rec)+"""
                                    </table>
                                </body>

                        <div>
                            <p></p>
                        </div>
                <html>"""

        msg = MIMEMultipart()
        emailfrom = "erp@nowfloats.com"
        emailto = ['shiksha@nowfloats.com','hrdesk@nowfloats.com','satesh.kohli@nowfloats.com']
        msg['From'] = emailfrom
        msg['To'] = ", ".join(emailto)
        msg['Subject'] = mail_subject

        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
        mail_server = cr.fetchone()
        smtp_user = mail_server[0]
        smtp_pass = mail_server[1]
        server = smtplib.SMTP_SSL('smtp.gmail.com',465)
        server.login(smtp_user,smtp_pass)
        text = msg.as_string()
        try:
            server.sendmail(emailfrom, emailto , text)
        except:
          pass
        server.quit()
        return True

    @api.multi
    def submit_feedback(self):
        for rec in self:
            if rec.feedback_line:
                for line in rec.feedback_line:
                    if line.low_score:
                        review_day=8
                        curr_date=(datetime.now()).strftime('%Y-%m-%d')
                        curr_day=datetime.now().weekday()
                        if curr_day in (5,6):
                            review_day=9
                        review_date=(datetime.now()+relativedelta(days=review_day)).strftime('%Y-%m-%d')
                        holiday=self.env['hr.holidays.public.line'].sudo().search([('date','>=',curr_date),('date','<=',review_date)])
                        count=0
                        if holiday:
                            for holi in holiday:
                                holi_day=datetime.strptime(holi.date,'%Y-%m-%d').weekday()
                                if holi_day != 6:
                                    count+=1
                            review_day+=count
                            review_date=(datetime.now()+relativedelta(days=review_day)).strftime('%Y-%m-%d')

                            flag=1
                            while flag:
                                next_holiday=self.env['hr.holidays.public.line'].sudo().search([('date','=',review_date)])
                                next_count=0
                                if next_holiday:
                                    for next_holi in next_holiday:
                                        next_holi_day=datetime.strptime(next_holi.date,'%Y-%m-%d').weekday()
                                        if next_holi_day != 6:
                                            next_count+=1
                                    review_day+=next_count
                                    review_date=(datetime.now()+relativedelta(days=review_day)).strftime('%Y-%m-%d')
                                elif datetime.strptime(review_date,'%Y-%m-%d').weekday() == 6:
                                    review_day+=1
                                    review_date=(datetime.now()+relativedelta(days=review_day)).strftime('%Y-%m-%d')
                                else:
                                    flag=0

                        line.write({'review_date':review_date})
                    line.employee_id.sudo().write({'c_paathashala_score':line.paathshala_score,'c_pathsala_city':rec.pathsala_city.id,'c_pathsala_batch':rec.name,'c_pathsala_date':rec.date_from,'paathshala_feedback':rec.id})
            rec.write({'submit':True})
            rec.send_email()
        return True

class nf_paathshala_feedback_line(models.Model):
    _name = 'nf.paathshala.feedback.line'
    _description = 'Paathshala Feedback Line'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'employee_id'

    paathshala_feedback = fields.Many2one('nf.paathshala.feedback',string='Paathshala Hub')
    employee_id = fields.Many2one('hr.employee','Employee')
    emp_id = fields.Char('Employee ID')
    branch_id = fields.Many2one('hr.branch','Branch')
    designation = fields.Char('Designation')
    paathshala_score = fields.Char('Paathshala Score')
    feedback = fields.Text('Feedback')
    low_score = fields.Boolean('Low Score')
    final_score = fields.Char('Final Paathshala Score',track_visibility='onchange')
    review_date = fields.Date('Review Date',track_visibility='onchange')
    review_comment = fields.Text('Review Comment',track_visibility='onchange')
    review_status = fields.Selection([('Below Average','Below Average'),('Average','Average'),('Good','Good')],'Review Status',track_visibility='onchange')
    reviewed = fields.Boolean('Reviewed')

    @api.onchange('employee_id')
    def onchange_employee(self):
        emp=self.employee_id
        if emp:
            self.emp_id=emp.nf_emp
            self.branch_id=emp.branch_id and emp.branch_id.id or False
            self.designation=emp.intrnal_desig

    @api.onchange('paathshala_score')
    def onchange_paathshala_score(self):
        score=self.paathshala_score
        if score and int(score)<75:
            self.low_score = True
        else:
            self.low_score = False
            
    @api.multi
    def confirm(self):
        for rec in self:
            if rec.final_score and rec.review_status:
                rec.employee_id.sudo().write({'c_paathashala_score':rec.final_score})
                temp_id = self.env['mail.template'].search([('name','=','Paathshala Feedback Review')])
                if temp_id:
                    temp_id.send_mail(rec.id)
                self.write({'reviewed':True})
            else:
                raise exceptions.ValidationError(_('Please enter Final Score and Review Status before confirming it.'))
        return True

    @api.model
    def feedback_review_notification(self):
        curr_date=datetime.now().strftime('%Y-%m-%d')
        rec_ids = self.search([('review_date','=',curr_date)])
        for rec in rec_ids:
            temp_id = self.env['mail.template'].search([('name','=','Paathshala Feedback Notification')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True
    
class hr_employee(models.Model):
    _inherit = 'hr.employee'
    _order = 'employee_no'
    
    @api.multi
    def name_get(self):
        result = []
        name=''
        for record in self:
            if record.nf_emp:
                name =  "[%s] %s" % (record.nf_emp ,record.name)
            else:
                name =  "%s" % (record.name)
            result.append((record.id, name))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name_related', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('nf_emp', operator, name)] + args, limit=limit)
        return recs.name_get()

    
    @api.multi
    def _check_ifsc_code(self):
        str="^-?[a-zA-Z0-9]+$"
        obj=self.browse()[0]
        name=obj.ifsc_code
        if name and len(name) != 11:
            raise UserError(_('Invalid IFSC Code'), _('IFSC Code must contain 11 Alphanumeric only.'))
        if name and re.match(str,name) == None:
            return False
        else:
            return True
        
      
    def default_country(self):
        return self.env['res.country'].search([('name','=','India')])

    @api.onchange('user_id')
    def _onchange_user(self):
        self.work_email = self.user_id.email
        self.address_home_id = self.user_id.partner_id and self.user_id.partner_id.id or False
        #self.name = self.user_id.name
        #self.image = self.user_id.image
        if self.user_id:
            if self.bank_account_id:
                self.bank_account_id.partner_id = self.user_id.partner_id and self.user_id.partner_id.id or False
            self.address_home_id.name = self.candidate_id and self.candidate_id.account_holder_name or False
            emp_ids = self.env['hr.employee'].sudo().search([('user_id','=',self.user_id.id)])
            if emp_ids:
                raise UserError(_('This user is already assigned to an employee.'))
    
    company_id=fields.Many2one('res.company','Company')
    grade_id=fields.Many2one('hr.grade','Grade')
    benefits_grade_id=fields.Many2one('hr.grade','Benefits Grade')
    doj=fields.Date('Joining Date')
    employee_no=fields.Char('Employee No.')
    nf_emp=fields.Char('Employee ID', track_visibility='onchange')
    father_name= fields.Char('Father Name', size=32, )
    bank_account= fields.Char('Bank Account', size=32, )
    ifsc_code=fields.Char('IFSC Code', size=32,)
    Date_of_birth= fields.Date('Date of Birth')
    retire_date= fields.Date('Retirement Date')
    pf_account= fields.Char('PF Account No')
    pan_number= fields.Char('Pan Number')
    bank_name= fields.Char('Bank Name')
    bank_address= fields.Char('Bank Address')
    region_id= fields.Many2one('employee.region','Region')
    unit= fields.Char('Place Of Appointment')
    catering_unit= fields.Many2one('employee.unit','Catering Unit')
    pattern= fields.Selection([('IDA','IDA'),('CDA','CDA')],"DA Pattern")
    mode_of_pay= fields.Selection([('Bank','Bank'),('Cheque','Cheque'),('NEFT','NEFT'),('Cash','Cash')],'Mode of Pay')
    location_id=fields.Many2one('hr.location','Location')
    old_location_id=fields.Many2one('hr.location','Old Location')
    last_transfer_date=fields.Date('Last Transfer Date')
    last_promotion_date=fields.Date('Last Promotion Date')
    employee_type_id=fields.Many2one('employee.type','Employee Type')
    disability= fields.Selection([('P','YES-Partial Disable'),('F','YES-Fully Disable'),('N','No')],"Disability",default='N')
    desig_in_railway=fields.Char('Designation In Railway')
    gl_region=fields.Char('GL Region')
    lob=fields.Char('Line Of Bussiness')
    status=fields.Char('Status')
    from_date=fields.Date('From Date')
    to_date=fields.Date('To Date')
    uan=fields.Char('UAN', track_visibility='onchange')
    salary_done=fields.Boolean('Salary Done')
    
    empl_id=fields.Char('Employee ID')
    branch_id = fields.Many2one('hr.branch', 'Reporting Branch', track_visibility='onchange')
    division_id = fields.Many2one('hr.division','Divison')
    sub_dep = fields.Many2one('hr.department','Division', track_visibility='onchange')
    cost_centr = fields.Many2one('account.analytic.account','CC Control Code')
    coach_id = fields.Many2one('hr.employee', string='Reporting Manager', track_visibility='onchange')
    job_id= fields.Many2one('hr.job', 'Job Position', track_visibility='onchange')
    intrnl_desig = fields.Many2one('hr.job','Internal Designation', track_visibility='onchange')
    hr = fields.Many2one('hr.employee','HR')
    
    street = fields.Char(string='Branch Street Address')  
    street2 = fields.Char(string='Branch Street2 Address')
    #city = fields.Char(string='City')
    q_city_id= fields.Many2one('ouc.city', string='Branch City')

    city = fields.Char(string='Branch City', related='q_city_id.name')
    state_id = fields.Many2one('res.country.state', string='Branch State', related='q_city_id.state_id')
    country_id1 = fields.Many2one('res.country', string='Branch Country', related='q_city_id.country_id')

    # state_id = fields.Many2one('res.country.state',string='State')
    # country_id1 = fields.Many2one('res.country',string='Country',default=default_country)
    zip = fields.Char(string='Branch ZIP',related='branch_id.zip')
    anniversary = fields.Boolean('Anniversary')
    paternity = fields.Boolean('Paternity')
    maternity = fields.Boolean('Maternity')
    paathshala_feedback = fields.Many2one('nf.paathshala.feedback',string='Paathshala Feedback')
    probation_completed = fields.Boolean('Probation Completed')
    sub_division = fields.Many2one('hr.department','Sub Division')
    virtual_branch_id = fields.Many2one('hr.branch', 'Attendance Branch', track_visibility='onchange')
    
    def send_employee_creation_email(self):
        template1=self.env['mail.template'].search([('name', '=', 'Employee Creation Email')], limit = 1)
        if template1:
            template1.send_mail(self.id)
        template2=self.env['mail.template'].search([('name', '=', 'Employee Welcome Email')], limit = 1)
        if template2:
            template2.send_mail(self.id)
        return True
    
    @api.model
    def create(self, vals):
        user_id=vals.get('user_id',False)
        if user_id:
            emp_ids=self.env['hr.employee'].sudo().search([('user_id','=',user_id)])
            if emp_ids:
               raise UserError(_("The user mapped to this employee is already mapped with another employee.")) 
        res = super(hr_employee, self).create(vals)
        branch_id = 'branch_id' in vals and vals['branch_id'] or None
        sub_department_id = 'sub_dep' in vals and vals['sub_dep'] or None
        self.env.cr.execute("select id from account_analytic_account where branch_id = %s and sub_dep = %s",(branch_id,sub_department_id,))
        temp = self.env.cr.fetchall()
        analytic_account_id = None
        if temp:
            analytic_account_id = temp[0][0]
            
        elif 'branch_id' in vals and vals['branch_id'] and 'sub_dep' in vals and vals['sub_dep']:
            name = str(res.branch_id.name) + '/' + str(res.sub_dep.name)
            code = self.env['ir.sequence'].next_by_code('account.analytic.account')
            analytic_account  =self.env['account.analytic.account'].sudo().create({'name':name,'code':code,'branch_id':vals['branch_id'],'sub_dep':vals['sub_dep']})
            analytic_account_id = analytic_account.id
        #employee_no = self.env['ir.sequence'].next_by_code('hr.employee_no')
        seq = self.env['ir.sequence'].next_by_code('emp_num_seq')
        split_seq = seq.split('-')[1]
        company = self.env['res.company']._company_default_get()
        company_id = company and company.id or None
        self.env.cr.execute("update hr_employee set cost_centr = %s,employee_no = %s,company_id = %s where id = %s",(analytic_account_id,str(split_seq),company_id,res.id))
        res.send_employee_creation_email()
        return res
    
    
    @api.multi
    def write(self, vals):
        user_id=vals.get('user_id',False)
        if user_id:
            emp_ids=self.env['hr.employee'].sudo().search([('user_id','=',user_id)])
            if emp_ids:
               raise UserError(_("The user mapped to this employee is already mapped with another employee."))

        # if vals.get('job_id',False) or vals.get('intrnal_desig',False):
        #     vals.update({'cfc_created':True})
        if vals.get('exit_mode',False):
            exit_templ=self.env['mail.template'].search([('name', '=', 'Employee In Exit Mode')], limit = 1)
            if exit_templ:
                exit_templ.sudo().send_mail(self.id)
        if vals.get('appraisal_date') and fields.Date.from_string(vals.get('appraisal_date')) < date.today():
            raise UserError(_("The date of the next appraisal cannot be in the past"))
        else:
            res = super(hr_employee, self).write(vals)
            if 'branch_id' in vals or 'sub_dep' in vals:
                for record in self:
                    branch_id = record.branch_id and record.branch_id.id or None
                    sub_department_id = record.sub_dep and record.sub_dep.id or None
                    self.env.cr.execute("select id from account_analytic_account where branch_id = %s and sub_dep = %s",(branch_id,sub_department_id,))
                    temp = self.env.cr.fetchall()
                    analytic_account_id = None
                    if temp:
                        analytic_account_id = temp[0][0]
                        
                    elif branch_id and sub_department_id:
                        name = str(record.branch_id.name) + '/' + str(record.sub_dep.name)
                        code = self.env['ir.sequence'].next_by_code('account.analytic.account')
                        analytic_account  =self.env['account.analytic.account'].sudo().create({'name':name,'code':code,'branch_id':branch_id,'sub_dep':sub_department_id})
                        analytic_account_id = analytic_account.id
                    self.env.cr.execute("update hr_employee set cost_centr = %s where id = %s",(analytic_account_id,record.id,))
            if 'anniversary_date' in vals and vals['anniversary_date']:
                for rec in self:
                   if not rec.anniversary:
                      self.env.cr.execute("Insert INTO hr_holidays (holiday_status_id,employee_id,holiday_type,number_of_days_temp,state,type,department_id,name,number_of_days) values ((Select id from hr_holidays_status where name = 'Privilege leave' limit 1),%s,'employee',1,'validate','add',(select department_id from hr_employee where id = %s limit 1),'Privilege leave',1)",(rec.id,rec.id,))
                      self.env.cr.execute("update hr_employee set anniversary = True where id = %s",(rec.id,))
            return res
        
        
    @api.onchange('branch_id')
    def onchange_branch(self):
        for record in self:
            print "=========================",record.branch_id
            if record.branch_id:
               branch = record.branch_id
               print "================branch=========",branch
               record.street = branch.street
               record.street2 = branch.street2
               record.q_city_id = branch.c_city_id.id

               record.state_id = branch.state_id
               record.country_id1 = branch.country_id
               record.zip = branch.zip
               print "================branch=========", branch.c_city_id
               print "================branch=========", branch.country_id
               print "================branch=========", record.c_city_id
               
                    
    
class Branch(models.Model):
    _name="branch"
    _description="Branch"
    
    name = fields.Char('Name')
        
class hr_contract(models.Model):
    _inherit = 'hr.contract'
    
    
    @api.one
    @api.depends('wage')
    def get_new_wage(self):
        for record in self:
            record.new_wage = record.wage
        
    grade_pay=fields.Float('Grade Pay')
    old_wage=fields.Float('Old Basic')
    last_mth_wage=fields.Float('Last Month Wage')
    
    hra_hrr_lease= fields.Boolean('Lease')
    lease_type=fields.Selection([('1','Individual'),('2','Company'),('3','Partnership')],'Landlord Type')
    ownership_type= fields.Selection([('N','Self Lease'),('NR','Near Relative'),('C','Company Accomodation'),('Y','Company Lease')],'Ownership Type')
    flat_area=fields.Float('Flat Area')
    address=fields.Char('Address')
    lease_amount=fields.Float('Actual Rent Amount')
    lease_start_date=fields.Date('Lease Start Date')
    lease_end_date=fields.Date('Lease End Date')
    lease_notes=fields.Text('Notes')
    
    monthly_inc_amount= fields.Float('Monthly Increment Amount')
    ne_increment_month=fields.Date('Next Increment Date')
    increment_month= fields.Selection([('1','JAN'),('2','FEB'),('3','MAR'),('4','APR'),('5','MAY'),('6','JUN'),('7','JUL'),('8','AUG'),('9','SEP'),('10','OCT'),('11','NOV'),('12','DEC')],'Increment Month')
    increment_status=fields.Char('Increment Status')
    vpf_amount= fields.Float('VPF Amount')
    child_ed_allow=fields.Boolean('Child Education Allowance')
    electricity_allow=fields.Boolean('Electricity Allowance')
    entertain_allow=fields.Boolean('Entertainment Allowance')
    vehi_conveyence_allow=fields.Boolean('Vehicle Conveyance Allowance')
    hard_soft_fur=fields.Boolean('Hard And Soft Furnishing')
    lunch_dinner_coup=fields.Boolean('Lunch Dinner Coupon')
    prof_up_allow=fields.Boolean('Professional Updation Allowance')
    medical_allow=fields.Boolean('Medical Allowance')
    uniform_fit_allow=fields.Boolean('Uniform Allowance')
    meal_coupon_allow=fields.Boolean('Meal Coupon')
    washing_allow=fields.Boolean('Washing Allowance')
    nps=fields.Boolean('NPS')
    cafeteria_aggregate=fields.Float('Cafeteria Percentage Aggregate')
    deputed_from_same_station=fields.Boolean('Deputed From same Station')
    eligible_for_deputaion=fields.Boolean('Eligible For Deputation Allowance')
    eligible_for_conveyance=fields.Boolean('Eligible For Conveyance Allowance')
    eligible_for_hra=fields.Boolean('Eligible For HRA')
    opted_for_medical=fields.Boolean('Opted For Medical Allowance')
    opted_for_furnishing=fields.Boolean('Opted For Furnishing Allowance')
    opted_for_washing=fields.Boolean('Opted For Washing Allowance')              
    nha_worked=fields.Float('National Holiday Worked Days')
    nda_hours=fields.Integer('Night Duty Hours')
    monthly_rent_paid=fields.Float('Monthly Quarter Rent')
    spouse_opting_rly_medical=fields.Boolean('Spouse Opting Railway/PSU Medical Allowance')
    previous_railway_employee=fields.Boolean('Previous Railway Employee')
    special_pf_amount=fields.Float('Special PF Amount')
    pf_stop_flag=fields.Boolean('PF Stop')
    new_wage=fields.Float('New Basic(CDA)',compute='get_new_wage',store=True)
    trial_date_start= fields.Date('Trial Start Date')
    wage=fields.Float('Salary', digits=(16, 2), required=True, help="Basic Salary of the employee")
    division=fields.Many2one('hr.division','Division')
    job_id= fields.Many2one('hr.job', 'Designation')
    
class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    
    branch_id = fields.Many2one('hr.branch','Branch')
    sub_dep = fields.Many2one('hr.department','Sub Department')
    division_id=fields.Many2one('hr.division','Division')


# class railway_division(osv.Model):
#     _name = 'railway.division'
#     
#      = 
#                 'name':fields.Char('Name',required='True'),
#                 'code':fields.Char('Code',required='True'),
#                 
#     

class ouc_city(models.Model):
    _name = 'ouc.city'

    name = fields.Char(string='City Name', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    active = fields.Boolean(string='Active', default=True)

class nf_deputation_type(models.Model):
    _name = 'nf.deputation.type'

    code = fields.Char('Code')
    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)


class nf_deputation(models.Model):
    _name="nf.deputation"
    _description="Business Travel"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    

    name = fields.Many2one('hr.employee',string="Employee")
    emp_id = fields.Char('Employee ID')
    designation = fields.Char(string='Designation')
    work_mobile = fields.Char(string='Work Mobile')
    branch_id = fields.Many2one('hr.branch','Branch')
    travel_date = fields.Date('From Date')
    till_date = fields.Date('Till Date')
    reason_id = fields.Many2one('nf.deputation.type', string="Reason" , track_visibility='onchange')
    reject_date = fields.Date('Rejected Date')
    approve_date = fields.Date('Approved Date')
    state = fields.Selection([('Draft','Draft'),('Approve','Approve'),('Reject','Reject')],string="State",track_visibility='onchange')
    c_man_user_id = fields.Many2one('res.users','Manager')
    c_user_id = fields.Many2one('res.users','User Id',default=lambda self: self.env.uid)
    c_rep_mngr_user = fields.Many2one('res.users','Reporting Head')

    @api.model
    def default_get(self,fields):
        res=super(nf_deputation,self).default_get(fields)
        hr_obj=self.env['hr.employee']
        hr_id=hr_obj.search([('user_id','=',self.env.uid)])
        res.update({'name':hr_id.id,'state':'Draft'})

        return res

    @api.onchange('name')
    def onchange_employee(self):
        emp=self.name
        if emp:
            self.emp_id=emp.nf_emp
            self.work_mobile=emp.mobile_phone
            self.designation=emp.intrnal_desig
            self.branch_id=emp.branch_id and emp.branch_id.id or False
            self.c_man_user_id=emp.parent_id and emp.parent_id.user_id and emp.parent_id.user_id.id or False
            self.c_rep_mngr_user=emp.coach_id and emp.coach_id.user_id and emp.coach_id.user_id.id or False
            self.c_user_id=emp.user_id.id


    @api.multi
    def travel_email_notification(self,status):
        if status=='Draft':
            template=self.env['mail.template'].search([('name', '=', 'Work Travel Request')], limit = 1)
            if template:
                template.send_mail(self.id)
        elif status=='Reject':
            template=self.env['mail.template'].search([('name', '=', 'Work Travel Rejected')], limit = 1)
            if template:
                template.send_mail(self.id)
        elif status=='Approve':
            template=self.env['mail.template'].search([('name', '=', 'Work Travel Approved')], limit = 1)
            if template:
                template.send_mail(self.id)
        return True


    @api.model
    def create(self, vals):
        emp=self.env['hr.employee'].sudo().browse(vals.get('name'))
        if emp:
            emp=emp[0]
            vals.update({'emp_id':emp.nf_emp,'work_mobile':emp.mobile_phone,'designation':emp.intrnal_desig,'branch_id':emp.branch_id and emp.branch_id.id or False,'c_man_user_id':emp.parent_id and emp.parent_id.user_id and emp.parent_id.user_id.id or False,'c_rep_mngr_user':emp.coach_id and emp.coach_id.user_id and emp.coach_id.user_id.id or False,'c_user_id':emp.user_id and emp.user_id.id or False})
        rec = super(nf_deputation, self).create(vals)
        rec.travel_email_notification('Draft')
        return rec

    @api.multi
    def approve(self):
        uid = self.env.uid
        approve_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            man_user = rec.name.parent_id and rec.name.parent_id and rec.name.parent_id.user_id and rec.name.parent_id.user_id.id or False
            reporting_user =rec.name.coach_id and rec.name.coach_id and rec.name.coach_id.user_id and rec.name.coach_id.user_id.id or False
            man_user_ids = [man_user,reporting_user]
            if self.env.user.has_group('hr.group_hr_manager') or uid in man_user_ids:
                self.write({'state':'Approve','approve_date':approve_date})
                self.travel_email_notification('Approve')
            else:
                raise exceptions.ValidationError(_('Sorry, you can not approve this. Only your Manager or Reporting Head or HR can approve this.'))
                
        return True

    @api.multi
    def reject(self):
        uid = self.env.uid
        reject_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            man_user = rec.name.parent_id and rec.name.parent_id and rec.name.parent_id.user_id and rec.name.parent_id.user_id.id or False
            reporting_user =rec.name.coach_id and rec.name.coach_id and rec.name.coach_id.user_id and rec.name.coach_id.user_id.id or False
            man_user_ids = [man_user,reporting_user]
            if self.env.user.has_group('hr.group_hr_manager') or uid in man_user_ids:
                self.write({'state':'Reject','reject_date':reject_date})
                self.travel_email_notification('Reject')
            else:
                raise exceptions.ValidationError(_('Sorry, you can not reject this. Only your Manager or Reporting Head or HR can reject this.'))
        return True

    @api.multi
    def reset_to_draft(self):
        for rec in self:
            self.write({'state':'Draft'})
        return True

class nf_employee_probation(models.Model):
    _name="nf.employee.probation"
    _description="Employee Probation"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee','Employee',track_visibility='onchange')
    emp_id = fields.Char('Employee ID')
    doj = fields.Date('Date of Joining')
    extend_date = fields.Date('Extended Date',track_visibility='onchange')
    manager_id = fields.Many2one('hr.employee','Manager')
    reporting_manager = fields.Many2one('hr.employee','Reporting Manager')
    state = fields.Selection([('Draft','Draft'),('Confirm','Confirm'),('Extend','Extend'),('RM Approve','RM Approve'),('HR Approve','HR Approve'),('Reject','Reject')],'Status',track_visibility='onchange',default='Draft')
    comments_ids = fields.One2many('nf.employee.probation.comments','probation_id','Comments',track_visibility='onchange')
    probation_completed = fields.Boolean('Probation Completed')
    review_status = fields.Selection([('Below Average','Below Average'),('Average','Average'),('Good','Good')],'Review Status',track_visibility='onchange')
    first_month_revenue = fields.Char(string='First Month Net Revenue')
    second_month_revenue = fields.Char(string='Second Month Net Revenue')
    third_month_revenue = fields.Char(string='Third Month Net Revenue')

    @api.onchange('employee_id')
    def onchange_employee(self):
        emp=self.employee_id
        if emp:
            self.emp_id = emp.nf_emp
            self.doj = emp.join_date
            self.manager_id = emp.parent_id and emp.parent_id.id or False
            self.reporting_manager = emp.coach_id and emp.coach_id.id or False

    @api.model
    def create(self,vals):
        cr=self.env.cr
        emp=self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
        if emp:
            emp=emp[0]
            curr_date = (datetime.now())
            back_date = (curr_date-relativedelta(months=3))
            next_date = (back_date+relativedelta(months=1))
            first_revenue=0
            second_revenue=0
            last_revenue=0
            revenue=0
            if back_date and next_date:
                for j in range(0,3):
                    if emp.intrnal_desig in ('Associate - Tele Sales','Consultant - Tele Sales','Principal Consultant - Tele Sales','Senior Consultant - Tele Sales'):
                      cr.execute("SELECT get_tc_achievement_amt(%s, %s, %s)",(back_date.strftime("%Y-%m-%d"),next_date.strftime("%Y-%m-%d"),emp.id))
                      revenue=cr.fetchone()[0]
                    else:
                      cr.execute("SELECT get_sp_achievement_amt(%s, %s, %s)",(back_date.strftime("%Y-%m-%d"),next_date.strftime("%Y-%m-%d 23:59:59"),emp.id))
                      revenue=cr.fetchone()[0]
                    if j==0:
                        first_revenue=revenue
                    elif j==1:
                        second_revenue=revenue
                    elif j==2:
                        last_revenue=revenue
                    back_date=next_date+relativedelta(days=1)
                    next_date=(back_date+relativedelta(months=1))
            vals.update({'emp_id':emp.nf_emp,'doj':emp.join_date,'manager_id':emp.parent_id and emp.parent_id.id or False,'reporting_manager':emp.coach_id and emp.coach_id.id or False,'first_month_revenue':first_revenue,'second_month_revenue':second_revenue,'third_month_revenue':last_revenue})
        rec = super(nf_employee_probation, self).create(vals)
        temp_id = self.env['mail.template'].search([('name', '=', 'Probation Notification')])
        if temp_id:
            temp_id.send_mail(rec.id)
        return rec

    @api.multi
    def confirm(self):
        for rec in self:
            rep_manager_id = rec.employee_id.coach_id and rec.employee_id.coach_id.user_id and rec.employee_id.coach_id.user_id.id or False
            manager_id = rec.employee_id.parent_id and rec.employee_id.parent_id.user_id and rec.employee_id.parent_id.user_id.id or False
            if not self.env.user.has_group('hr.group_hr_manager'):
                if self.env.uid not in [rep_manager_id,manager_id]:
                    raise exceptions.ValidationError(_('Sorry, only manager or reporting manager of the employee can approve this.'))
            if rep_manager_id == manager_id:
                rec.write({'state':'RM Approve'})
                temp_id = self.env['mail.template'].search([('name', '=', 'Probation Manager Approve')])
                if temp_id:
                    temp_id.send_mail(rec.id)
            else:
                rec.write({'state':'Confirm'})
                temp_id = self.env['mail.template'].search([('name', '=', 'Probation Confirm')])
                if temp_id:
                    temp_id.send_mail(rec.id)
        return True

    @api.multi
    def extend(self):
        for rec in self:
            if not rec.extend_date:
                raise exceptions.ValidationError(_('Please add comment and Extended Date to extend the probation period.')) 
        self.write({'state':'Extend'})
        temp_id = self.env['mail.template'].search([('name', '=', 'Probation Extend')])
        if temp_id:
            temp_id.send_mail(self.id)
        temp_id1 = self.env['mail.template'].search([('name', '=', 'Probation Extend Employee')])
        if temp_id1:
            temp_id1.send_mail(self.id)
        return True

    @api.multi
    def manager_approve(self):
        for rec in self:
            manager_id = rec.employee_id.parent_id and rec.employee_id.parent_id.user_id and rec.employee_id.parent_id.user_id.id or False
            if not self.env.user.has_group('hr.group_hr_manager'):
                if self.env.uid != manager_id:
                    raise exceptions.ValidationError(_('Sorry, only manager of the employee can approve this.'))
            if not rec.review_status:
                raise exceptions.ValidationError(_('Please add comment and review status before confirming it.'))
        self.write({'state':'RM Approve'})
        temp_id = self.env['mail.template'].search([('name', '=', 'Probation Manager Approve')])
        if temp_id:
            temp_id.send_mail(self.id)
        return True

    @api.multi
    def hr_approve(self):
        for rec in self:
            rec.write({'state':'HR Approve','probation_completed':True})
            rec.employee_id.write({'c_empl_type':'permanent'})
            temp_id = self.env['mail.template'].search([('name', '=', 'Probation HR Approve')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True

    @api.multi
    def reject(self):
        for rec in self:
            manager_id=[]
            manager_id.append(rec.employee_id.parent_id and rec.employee_id.parent_id.user_id and rec.employee_id.parent_id.user_id.id or False)
            manager_id.append(rec.employee_id.coach_id and rec.employee_id.coach_id.user_id and rec.employee_id.coach_id.user_id.id or False)
            if not self.env.user.has_group('hr.group_hr_manager'):
                if self.env.uid not in manager_id:
                    raise exceptions.ValidationError(_('Sorry, you can not reject this, only reporting manager, manager of the employee or HR can reject this.'))
        self.write({'state':'Reject'})
        temp_id = self.env['mail.template'].search([('name', '=', 'Probation Reject')])
        if temp_id:
            temp_id.send_mail(self.id)
        return True

class nf_employee_probation_comments(models.Model):
    _name = "nf.employee.probation.comments"
    _description = 'Probation Comments'

    probation_id = fields.Many2one('nf.employee.probation','Probation')
    comments = fields.Text('Comment')
    comment_date = fields.Date('Comment Date')
    comment_by = fields.Many2one('res.users','Comment By')
    submit = fields.Boolean('Submit')

    @api.model
    def create(self,vals):
        rec=super(nf_employee_probation_comments,self).create(vals)
        rec.write({'comment_date':datetime.now().strftime('%Y-%m-%d'),'comment_by':self.env.uid,'submit':True})
        return rec


class nf_payroll_employee(models.Model):
    _name = 'nf.payroll.employee'
    _description = 'NF Payroll Employee'

    name = fields.Char('Name')
    payroll_date = fields.Date('Date',default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee','Employee')
    state = fields.Selection([('Draft','Draft'),('Submitted','Submitted'),('Cancel','Cancel')],'Status',default='Draft')
    employee_line = fields.One2many('nf.payroll.employee.line','payroll_employee_id','Payroll Employee Line')

    @api.model
    def default_get(self, fields):
        rec={}
        rec =  super(nf_payroll_employee, self).default_get(fields)
        man_obj = self.env['hr.employee'].sudo().search([('user_id','=',self.env.uid)])
        rec.update({'employee_id':man_obj.id})    
        return rec

    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id:
            vals=[]
            emp_ids = self.env['hr.employee'].sudo().search([('coach_id','=',self.employee_id.id)])
            if emp_ids:
                for emp in emp_ids:
                    vals.append((0,False,{'employee_id':emp.id,'submitted_by':self.employee_id.id}))
            self.employee_line = vals

    @api.model
    def create(self,vals):
        payroll_date=date.today().strftime('%b-%Y')
        vals.update({'name': 'Payroll for '+payroll_date})
        result = super(nf_payroll_employee, self).create(vals)
        return result

    @api.multi
    def submit(self):
        for rec in self:
            rec.write({'state':'Submitted'})
            temp_id = self.env['mail.template'].search([('name', '=', 'Payroll Employee Confirm')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True

    @api.multi
    def cancel(self):
        for rec in self:
            rec.write({'state':'Cancel'})
        return True

class nf_payroll_employee_line(models.Model):
    _name = 'nf.payroll.employee.line'
    _description = 'NF Payroll Employee Line'
    _rec_name = 'payroll_employee_id'

    employee_id = fields.Many2one('hr.employee','Employee')
    submitted_by = fields.Many2one('hr.employee','Submitted By')
    status = fields.Selection([('Process','Process'),('Hold','Hold')],'Status')
    reason = fields.Text('Reason')
    payroll_employee_id = fields.Many2one('nf.payroll.employee','Name')


class nf_pareeksha_score(models.Model):
    _name = 'nf.pareeksha.score'
    _description = 'NF Pareeksha Score'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char('Module Name',track_visibility='onchange')
    series_name = fields.Char('Series Name',track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee','Employee',track_visibility='onchange')
    employee_name = fields.Char('Employee Name',track_visibility='onchange')
    email_id = fields.Char('Email ID',track_visibility='onchange')
    score = fields.Integer('Score',track_visibility='onchange')
    max_score = fields.Integer('Max Score',track_visibility='onchange')
    percent_score = fields.Char('Percent Score',track_visibility='onchange')
    start_date = fields.Datetime('Start Date',track_visibility='onchange')
    end_date = fields.Datetime('End Date',track_visibility='onchange')

class nf_buddy_candidate_feedback(models.Model):
    _name = 'nf.buddy.candidate.feedback'
    _description = 'NF Buddy Candidate Feedback'
    _rec_name = 'employee_id'

    @api.depends('candidate_feedback.rating')
    def _get_candidate_score(self):
        for rec in self:
            total = 0.0
            count = 0
            for line in rec.candidate_feedback:
                total += line.rating
                count +=1
            if count:
                rec.candidate_score = float(total)/count

    @api.depends('buddy_feedback.rating')
    def _get_buddy_score(self):
        for rec in self:
            total = 0.0
            count = 0
            for line in rec.buddy_feedback:
                total += line.rating
                count += 1
            if count:
                rec.buddy_score = float(total)/count

    employee_id = fields.Many2one('hr.employee','Employee')
    buddy_id = fields.Many2one('hr.employee','Buddy')
    training_start_date = fields.Date('Start Date')
    training_end_date = fields.Date('End Date')
    buddy_submit = fields.Boolean('Buddy Submit')
    candidate_submit = fields.Boolean('Candidate Submit')
    candidate_feedback = fields.One2many('nf.buddy.candidate.line','buddy_feedback','Candidate Feedback')
    buddy_feedback = fields.One2many('nf.buddy.feedback','buddy_feedback','Buddy Feedback')
    check_access = fields.Char('Check Access', compute='_check_access')
    buddy_aware = fields.Selection([('Yes','Yes'),('No','No')],'Were you aware of the Buddy assigned to you? (Yes/No)')
    buddy_score = fields.Float(compute='_get_buddy_score', store='True', string='Buddy Score')
    candidate_score = fields.Float(compute='_get_candidate_score', store='True', string='Candidate Score')

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            cand_vals=[]
            buddy_vals=[]
            ques_rec=self.env['nf.buddy.feedback.question']
            candidate_question_ids = ques_rec.sudo().search([('type','=','Candidate')])
            buddy_question_ids = ques_rec.sudo().search([('type','=','Buddy')])
            for cand_res in candidate_question_ids:
                cand_vals.append((0,False,{'name':cand_res.name}))
            for buddy_res in buddy_question_ids:
                buddy_vals.append((0,False,{'name':buddy_res.name}))
            self.candidate_feedback = cand_vals
            self.buddy_feedback = buddy_vals

    @api.one
    @api.depends('employee_id')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        if self.employee_id:
            if self.buddy_id:
                if user == self.buddy_id.user_id.id:
                    emp = 'Buddy'
            if user == self.employee_id.user_id.id:
                emp = 'Candidate'
            if self.env.user.has_group('hr.group_hr_manager'):
                emp = 'HR'
        self.check_access = emp

    @api.multi
    def submit_candidate(self):
        for rec in self:
            rec.write({'candidate_submit':True})
            temp_id = self.env['mail.template'].search([('name', '=', 'Employee Training Feedback')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True

    @api.multi
    def submit_buddy(self):
        for rec in self:
            rec.write({'buddy_submit':True})
            temp_id = self.env['mail.template'].search([('name', '=', 'Buddy Training Feedback')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True

class nf_buddy_feedback_question(models.Model):
    _name = 'nf.buddy.feedback.question'
    _description = 'Nf Buddy Feedback Question'

    name = fields.Char('Question')
    type = fields.Selection([('Candidate','Candidate'),('Buddy','Buddy')],'Type')

class nf_buddy_candidate_line(models.Model):
    _name = 'nf.buddy.candidate.line'
    _description = 'NF Buddy Candidate Line'

    buddy_feedback = fields.Many2one('nf.buddy.candidate.feedback','Buddy Feedback')
    name = fields.Char('Question')
    rating = fields.Integer('Rating')

    @api.onchange('rating')
    def onchange_rating(self):
        if self.rating:
            if self.rating > 5 or self.rating < 0:
                self.rating = 0
                raise ValidationError('Rating should be in between 1 and 5.')

    @api.multi
    def write(self,vals):
        if vals.get('rating'):
            if vals.get('rating') < 1 or vals.get('rating') > 5:
                vals.update({'rating':0})

        result = super(nf_buddy_candidate_line, self).write(vals)
        return result

class nf_buddy_feedback(models.Model):
    _name = 'nf.buddy.feedback'
    _description = 'NF Buddy Feedback'

    buddy_feedback = fields.Many2one('nf.buddy.candidate.feedback','Buddy Feedback')
    name = fields.Char('Question')
    rating = fields.Integer('Rating')

    @api.onchange('rating')
    def onchange_rating(self):
        if self.rating:
            if self.rating > 5 or self.rating < 0:
                self.rating = 0
                raise ValidationError('Rating should be in between 1 and 5.')

    @api.multi
    def write(self,vals):
        if vals.get('rating'):
            if vals.get('rating') < 1 or vals.get('rating') > 5:
                vals.update({'rating':0})

        result = super(nf_buddy_feedback, self).write(vals)
        return result