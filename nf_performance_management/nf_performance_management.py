from odoo import models, fields, api, _
from openerp.osv import osv
from datetime import datetime,date,timedelta
from odoo.exceptions import UserError, ValidationError, Warning, except_orm
from openerp import SUPERUSER_ID
from odoo import exceptions
from dateutil import relativedelta

rating = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')]

class nf_hr_appraisal(models.Model):
    _inherit = "hr.appraisal"

    APPRAISAL_STATES = [
        ('new', 'To Start'),
        ('pending', 'Sent'),
        ('RepMan Confirm','RepMan Confirm'),
        ('DeptMan Confirm','DeptMan Confirm'),
        ('done', 'Done'),
        ('cancel', "Cancelled"),
    ]

    state = fields.Selection(APPRAISAL_STATES, string='Status', track_visibility='onchange', required=True, readonly=True, copy=False, default='new', index=True)
    sub_dep = fields.Many2one('hr.department','Division')
    department_id = fields.Many2one('hr.department', string='Department')
    intrnal_desig=fields.Char('Internal Designation')
    join_date=fields.Date('Date of Joining')
    parent_id=fields.Many2one('hr.employee','Manager')
    reporting_manager_id=fields.Many2one('hr.employee','Reporting Manager')
    emp_id=fields.Char('Employee ID')
    employee_assessment = fields.One2many('nf.employee.assessment','appraisal_id','Employee Assessment', track_visibility='onchange')
    manager_assessment = fields.One2many('nf.manager.assessment','appraisal_id','Manager Assessment', track_visibility='onchange')
    reporting_manager_assessment = fields.One2many('nf.reporting.manager.assessment','appraisal_id','Reporting Manager Assessment', track_visibility='onchange')
    hr_assessment = fields.One2many('nf.hr.assessment','appraisal_id','HR Assessment', track_visibility='onchange')
    employee_remarks = fields.Text('Employee Comments', track_visibility='onchange')
    manager_remarks = fields.Text('Manager Remarks', track_visibility='onchange')
    reporting_manager_remarks = fields.Text('Reporting Manager Remarks', track_visibility='onchange')
    check_access = fields.Char('Check Access', compute='_check_access')
    branch_id = fields.Many2one('hr.branch','Branch')
    state_id = fields.Many2one('res.country.state','State')
    review_date = fields.Date('Date of Review', track_visibility='onchange')
    experience = fields.Char('Experience in NowFloats', compute='get_experience')
    job_id = fields.Many2one('hr.job','Designation')
    rating_criteria = fields.One2many('nf.employee.rating.criteria','appraisal_id','Rating Criteria')
    emp_total_score = fields.Char('Employee Total Score',compute='get_emp_total_score',store=True)
    rm_total_score = fields.Char('Reporting Manager Total Score',compute='get_rm_total_score',store=True)
    man_total_score = fields.Char('Manager Total Score',compute='get_man_total_score',store=True)
    hr_total_score = fields.Char('HR Total Score',compute='get_hr_total_score',store=True)
    appraisal_score = fields.Char('Appraisal Score')
    appraisal_rating_scale = fields.Many2one('nf.appraisal.rating.criteria','Appraisal Rating Scale')
    emp_submit = fields.Boolean('Employee Submit')
    rm_submit = fields.Boolean('Rep Man Submit')
    man_submit = fields.Boolean('Manager Submit')
    hr_submit = fields.Boolean('HR Submit')

    @api.model
    def default_get(self, fields):
        rec={}
        rec =  super(nf_hr_appraisal, self).default_get(fields)
        hr_obj = self.env['hr.employee'].sudo().search([('user_id','=',self.env.uid)])
        current_date = (date.today())
        final_interview = current_date+relativedelta.relativedelta(days=14)
        deadline = current_date+relativedelta.relativedelta(days=15)
        rec.update({'employee_id':hr_obj.id,'review_date':current_date.strftime('%Y-%m-%d'),'date_close':deadline.strftime('%Y-%m-%d'),'date_final_interview':final_interview.strftime('%Y-%m-%d')})    
        return rec

    @api.depends('reporting_manager_assessment.rating')
    def get_rm_total_score(self):
        for rec in self:
            total =0.0
            final_score=0.0
            for line in rec.reporting_manager_assessment:
                if line.rating:
                    final_score=(float(line.rating)*float(line.weightage))/10
                    total += final_score
            rec.rm_total_score = str(total)

    @api.depends('manager_assessment.rating')
    def get_man_total_score(self):
        for rec in self:
            total =0.0
            final_score=0.0
            for line in rec.manager_assessment:
                if line.rating:
                    final_score=(float(line.rating)*float(line.weightage))/10
                    total += final_score
            rec.man_total_score = str(total)

    @api.depends('employee_assessment.rating')
    def get_emp_total_score(self):
        for rec in self:
            total =0.0
            final_score=0.0
            for line in rec.employee_assessment:
                if line.rating:
                    final_score=(float(line.rating)*float(line.weightage))/10
                    total += final_score
            rec.emp_total_score = str(total)

    @api.depends('hr_assessment.rating')
    def get_hr_total_score(self):
        for rec in self:
            total =0.0
            final_score=0.0
            for line in rec.hr_assessment:
                if line.rating:
                    final_score=(float(line.rating)*float(line.weightage))/10
                    total += final_score
            rec.hr_total_score = str(total)


    #method to calculate total work experience
    @api.one
    @api.depends('join_date')
    def get_experience(self):
        if self.join_date:
            current_date = date.today()
            join_date = datetime.strptime(self.join_date,'%Y-%m-%d')
            self.experience =  "{0.years} year(s) , {0.months} month(s) and {0.days} day(s)".format(relativedelta.relativedelta(current_date,join_date))

    @api.onchange('job_id')
    def onchange_job_id(self):
        if self.job_id:
            emp_vals=[]
            rm_vals=[]
            man_vals=[]
            question_ids = self.env['nf.appraisal.question'].search([],order='sequence asc')
            for rec in question_ids:
                if self.job_id in rec.job_ids:
                    emp_vals.append((0,False,{'name':rec.name,'weightage':rec.weightage}))
                    rm_vals.append((0,False,{'name':rec.name,'weightage':rec.weightage}))

            self.employee_assessment = emp_vals
            self.reporting_manager_assessment = rm_vals
    
    @api.one
    @api.depends('employee_id')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        if self.employee_id:
            if self.reporting_manager_id:
                if user == self.reporting_manager_id.user_id.id:
                    emp = 'RepMan'
            if self.parent_id:
                if user == self.parent_id.user_id.id:
                    emp = 'Man'
            if self.parent_id and self.reporting_manager_id:
                if user == self.reporting_manager_id.user_id.id and self.reporting_manager_id.id == self.parent_id.id:
                    emp = 'RepandMan'
            if user == self.employee_id.user_id.id:
                emp = 'Emp'
            elif self.env.user.has_group('hr_appraisal.group_hr_appraisal_manager'):
                if emp == 'Man':
                    emp = 'ManHR'
                elif emp == 'RepMan':
                    emp = 'RepManHR'
                elif emp == 'RepandMan':
                    emp = 'RepandManHR'
                else:
                    emp = 'HR'
        self.check_access = emp

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            criteria_vals=[]
            weighatge_vals=[]
            criteria_ids = self.env['nf.appraisal.rating.criteria'].search([])
            for rec in criteria_ids:
                criteria_vals.append((0,False,{'rating':rec.rating,'rating_scale':rec.rating_scale,'criteria':rec.criteria}))
            self.rating_criteria = criteria_vals
            self.final_weightage = weighatge_vals
            self.department_id = self.employee_id.department_id
            self.manager_appraisal = self.employee_id.appraisal_by_manager
            self.manager_ids = self.employee_id.appraisal_manager_ids
            self.manager_survey_id = self.employee_id.appraisal_manager_survey_id
            self.colleagues_appraisal = self.employee_id.appraisal_by_colleagues
            self.colleagues_ids = self.employee_id.appraisal_colleagues_ids
            self.colleagues_survey_id = self.employee_id.appraisal_colleagues_survey_id
            self.employee_appraisal = self.employee_id.appraisal_self
            self.employee_survey_id = self.employee_id.appraisal_self_survey_id
            self.collaborators_appraisal = self.employee_id.appraisal_by_collaborators
            self.collaborators_ids = self.employee_id.appraisal_collaborators_ids
            self.collaborators_survey_id = self.employee_id.appraisal_collaborators_survey_id
            self.sub_dep = self.employee_id.sub_dep and self.employee_id.sub_dep.id
            self.intrnal_desig = self.employee_id.intrnal_desig
            self.join_date = self.employee_id.join_date
            self.parent_id = self.employee_id.parent_id and self.employee_id.parent_id.id or False
            self.reporting_manager_id = self.employee_id.coach_id and self.employee_id.coach_id.id or False
            self.emp_id = self.employee_id.emp_id
            self.branch_id = self.employee_id.branch_id and self.employee_id.branch_id.id or False
            self.state_id = self.employee_id.branch_id.state_id and self.employee_id.branch_id.state_id.id or False
            self.job_id = self.employee_id.job_id and self.employee_id.job_id.id or False

    @api.onchange('join_date')
    def onchange_join_date(self):
        if self.join_date:
            appraisal_date=(date.today()).strftime('%Y-03-31')
            back_app_date=(datetime.strptime(appraisal_date,'%Y-%m-%d')-relativedelta.relativedelta(months=3)).strftime('%Y-%m-%d')
            if self.join_date and self.join_date>back_app_date:
                raise ValidationError('Sorry, you are not eligible for appraisal.')

    @api.model
    def create(self, vals):
        emp=vals.get('employee_id',False)
        if emp:
            emp_rec=self.env['hr.employee'].browse(emp)
            vals.update({'sub_dep':emp_rec.sub_dep and emp_rec.sub_dep.id,'intrnal_desig':emp_rec.intrnal_desig,'join_date':emp_rec.join_date,'parent_id':emp_rec.parent_id and emp_rec.parent_id.id or False,'reporting_manager_id':emp_rec.coach_id and emp_rec.coach_id.id or False,'emp_id':emp_rec.nf_emp,'branch_id':emp_rec.branch_id and emp_rec.branch_id.id or False,'state_id':emp_rec.branch_id.state_id and emp_rec.branch_id.state_id.id or False,'job_id':emp_rec.job_id and emp_rec.job_id.id or False})
            join_date=vals.get('join_date',False)
            appraisal_date=(date.today()).strftime('%Y-03-31')
            back_app_date=(datetime.strptime(appraisal_date,'%Y-%m-%d')-relativedelta.relativedelta(months=3)).strftime('%Y-%m-%d')
            if join_date and join_date>back_app_date:
                raise ValidationError('Sorry, you are not eligible for appraisal.')

        result = super(nf_hr_appraisal, self).create(vals)
        return result

    @api.multi
    def submit_employee(self):
        for rec in self:
            rec.write({'state':'pending','emp_submit':True})
            template=self.env['mail.template'].search([('name', '=', 'Appraisal Employee Submit')], limit = 1)
            if template:
                template.send_mail(self.id)
        return True

    @api.multi
    def submit_reportig_manager(self):
        for rec in self:
            if not rec.reporting_manager_remarks or len(rec.reporting_manager_remarks) < 140:
                raise ValidationError(_("Please give remarks before submitting. It should be of 140 characters minimum."))
            if rec.reporting_manager_assessment:
                man_values=[]
                hr_values=[]
                for res in rec.reporting_manager_assessment:
                    man_values.append((0,False,{'name':res.name,'weightage':res.weightage,'rating':res.rating}))
                    hr_values.append((0,False,{'name':res.name,'weightage':res.weightage,'rating':res.rating}))
            rec.write({'state':'RepMan Confirm','rm_submit':True,'manager_assessment':man_values,'hr_assessment':hr_values})
            template=self.env['mail.template'].search([('name', '=', 'Appraisal Reporting Manager Submit')], limit = 1)
            if template:
                template.send_mail(self.id)
        return True

    @api.multi
    def submit_manager(self):
        for rec in self:
            hr_values=[]
            if not rec.manager_remarks:
                raise ValidationError(_("Please give remarks before submitting."))
            if rec.manager_assessment:
                for res in rec.manager_assessment:
                    self.env.cr.execute("DELETE FROM nf_hr_assessment WHERE appraisal_id = {}".format(rec.id))
                    hr_values.append((0,False,{'name':res.name,'weightage':res.weightage,'rating':res.rating}))
            rec.write({'state':'DeptMan Confirm','man_submit':True,'hr_assessment':hr_values})
            template=self.env['mail.template'].search([('name', '=', 'Appraisal Manager Submit')], limit = 1)
            if template:
                template.send_mail(self.id)
        return True

    @api.multi
    def submit_hr(self):
        for rec in self:
            if not rec.action_plan or len(rec.action_plan) < 140:
                raise ValidationError(_("Please give remarks before submitting. It should be of 140 characters minimum."))
            rating_score=float(rec.hr_total_score)/10
            rating_scale=''
            rating_scale_rec=self.env['nf.appraisal.rating.criteria'].sudo().search([('min_rate','<=',rating_score),('max_rate','>=',rating_score)])
            if rating_scale_rec:
                rating_scale=rating_scale_rec.id
            rec.write({'state':'done','appraisal_score':rec.hr_total_score,'appraisal_rating_scale':rating_scale,'hr_submit':True})
            template=self.env['mail.template'].search([('name', '=', 'Apprisal HR Submit')], limit = 1)
            if template:
                template.send_mail(self.id)
        return True

class nf_employee_assessment(models.Model):
    _name = 'nf.employee.assessment'
    _description = 'Employee Assessment'

    name = fields.Char('Name')
    rating = fields.Integer('Rating')
    rating_scale = fields.Char('Rating Scale',compute='get_rating_scale',store=True)
    weightage = fields.Char('Weightage')
    comment = fields.Text('Comment',help='Provide details to support your self assessment rating. It should be more than 140 characters')
    final_score = fields.Char('Final Score',compute='get_final_score',store=True)
    appraisal_id = fields.Many2one('hr.appraisal','Appraisal ID')

    @api.depends('rating')
    def get_rating_scale(self):
        for rec in self:
            if rec.rating:
                rating_scale_rec=self.env['nf.appraisal.rating.criteria'].sudo().search([('min_rate','<=',rec.rating),('max_rate','>=',rec.rating)])
                if rating_scale_rec:
                    rec.rating_scale=rating_scale_rec.rating_scale
                else:
                    raise Warning("Rating should be in between 1 to 10.")

    @api.depends('rating')
    def get_final_score(self):
        for rec in self:
            if rec.rating and rec.weightage:
                final_score=round((float(rec.rating*float(rec.weightage))/10),2)
                rec.final_score=str(final_score)

    @api.onchange('comment')
    def onchange_comment(self):
        if not self.comment or len(self.comment) < 140:
            raise exceptions.ValidationError(_('Comment is too short. It should be of 140 characters minimum.'))

    @api.model
    def create(self,vals):
        if vals.get('comment') and len(vals.get('comment')) < 140:
            raise exceptions.ValidationError(_('Comment is too short. It should be of 140 characters minimum.'))

        result = super(nf_employee_assessment, self).create(vals)
        return result

    @api.multi
    def write(self,vals):
        if vals.get('comment') and len(vals.get('comment')) < 140:
            raise exceptions.ValidationError(_('Comment is too short. It should be of 140 characters minimum.'))

        result = super(nf_employee_assessment, self).write(vals)
        return result

class nf_manager_assessment(models.Model):
    _name = 'nf.manager.assessment'
    _description = 'Manager Assessment'

    name = fields.Char('Name')
    #rating = fields.Integer('Rating')
    rating = fields.Selection(rating,'Rating')
    rating_scale = fields.Char('Rating Scale',compute='get_rating_scale',store=True)
    weightage = fields.Char('Weightage')
    comment = fields.Text('Comment')
    final_score = fields.Char('Final Score',compute='get_final_score',store=True)
    appraisal_id = fields.Many2one('hr.appraisal','Appraisal ID')
    check_access = fields.Char('Check Access', compute='_check_access')

    @api.depends('rating')
    def get_rating_scale(self):
        for rec in self:
            if rec.rating:
                rating=float(rec.rating)
                rating_scale_rec=self.env['nf.appraisal.rating.criteria'].sudo().search([('min_rate','<=',rating),('max_rate','>=',rating)])
                if rating_scale_rec:
                    rec.rating_scale=rating_scale_rec.rating_scale
                else:
                    raise ValidationError(_("Rating should be in between 1 to 10."))

    @api.depends('rating')
    def get_final_score(self):
        for rec in self:
            if rec.rating and rec.weightage:
                final_score=round(((float(rec.rating)*float(rec.weightage))/10),2)
                rec.final_score=str(final_score)

    @api.one
    @api.depends('appraisal_id')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        app_rec=self.appraisal_id
        if app_rec:
            if app_rec.reporting_manager_id:
                if user == app_rec.reporting_manager_id.user_id.id:
                    emp = 'RepMan'
            if app_rec.parent_id:
                if user == app_rec.parent_id.user_id.id:
                    emp = 'Man'
            if app_rec.parent_id and app_rec.reporting_manager_id:
                if user == app_rec.reporting_manager_id.user_id.id and app_rec.reporting_manager_id.id == app_rec.parent_id.id:
                    emp = 'RepandMan'
            if user == app_rec.employee_id.user_id.id:
                emp = 'Emp'
            elif self.env.user.has_group('hr_appraisal.group_hr_appraisal_manager'):
                if emp == 'Man':
                    emp = 'ManHR'
                elif emp == 'RepMan':
                    emp = 'RepManHR'
                elif emp == 'RepandMan':
                    emp = 'RepandManHR'
                else:
                    emp = 'HR'
        self.check_access = emp

class nf_reporting_manager_assessment(models.Model):
    _name = 'nf.reporting.manager.assessment'
    _description = 'Reporting Manager Assessment'

    name = fields.Char('Name')
    #rating = fields.Integer('Rating')
    rating = fields.Selection(rating,'Rating')
    rating_scale = fields.Char('Rating Scale',compute='get_rating_scale',store=True)
    weightage = fields.Char('Weightage')
    comment = fields.Text('Comment')
    final_score = fields.Char('Final Score',compute='get_final_score',store=True)
    appraisal_id = fields.Many2one('hr.appraisal','Appraisal ID')
    check_access = fields.Char('Check Access', compute='_check_access')

    @api.depends('rating')
    def get_rating_scale(self):
        for rec in self:
            if rec.rating:
                rating=float(rec.rating)
                rating_scale_rec=self.env['nf.appraisal.rating.criteria'].sudo().search([('min_rate','<=',rating),('max_rate','>=',rating)])
                if rating_scale_rec:
                    rec.rating_scale=rating_scale_rec.rating_scale
                else:
                    raise ValidationError(_("Rating should be in between 1 to 10."))

    @api.depends('rating')
    def get_final_score(self):
        for rec in self:
            if rec.rating and rec.weightage:
                final_score=round(((float(rec.rating)*float(rec.weightage))/10),2)
                rec.final_score=str(final_score)

    @api.one
    @api.depends('appraisal_id')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        app_rec=self.appraisal_id
        if app_rec:
            if app_rec.reporting_manager_id:
                if user == app_rec.reporting_manager_id.user_id.id:
                    emp = 'RepMan'
            if app_rec.parent_id:
                if user == app_rec.parent_id.user_id.id:
                    emp = 'Man'
            if app_rec.parent_id and app_rec.reporting_manager_id:
                if user == app_rec.reporting_manager_id.user_id.id and app_rec.reporting_manager_id.id == app_rec.parent_id.id:
                    emp = 'RepandMan'
            if user == app_rec.employee_id.user_id.id:
                emp = 'Emp'
            elif self.env.user.has_group('hr_appraisal.group_hr_appraisal_manager'):
                if emp == 'Man':
                    emp = 'ManHR'
                elif emp == 'RepMan':
                    emp = 'RepManHR'
                elif emp == 'RepandMan':
                    emp = 'RepandManHR'
                else:
                    emp = 'HR'
        self.check_access = emp

class nf_hr_assessment(models.Model):
    _name = 'nf.hr.assessment'
    _description = 'HR Assessment'

    name = fields.Char('Name')
    #rating = fields.Integer('Rating')
    rating = fields.Selection(rating,'Rating')
    rating_scale = fields.Char('Rating Scale',compute='get_rating_scale',store=True)
    weightage = fields.Char('Weightage')
    comment = fields.Text('Comment')
    final_score = fields.Char('Final Score',compute='get_final_score',store=True)
    appraisal_id = fields.Many2one('hr.appraisal','Appraisal ID')
    check_access = fields.Char('Check Access', compute='_check_access')

    @api.depends('rating')
    def get_rating_scale(self):
        for rec in self:
            if rec.rating:
                rating=float(rec.rating)
                rating_scale_rec=self.env['nf.appraisal.rating.criteria'].sudo().search([('min_rate','<=',rating),('max_rate','>=',rating)])
                if rating_scale_rec:
                    rec.rating_scale=rating_scale_rec.rating_scale
                else:
                    raise ValidationError(_("Rating should be in between 1 to 10."))

    @api.depends('rating')
    def get_final_score(self):
        for rec in self:
            if rec.rating and rec.weightage:
                final_score=round(((float(rec.rating)*float(rec.weightage))/10),2)
                rec.final_score=str(final_score)

    @api.one
    @api.depends('appraisal_id')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        app_rec=self.appraisal_id
        if app_rec:
            if app_rec.reporting_manager_id:
                if user == app_rec.reporting_manager_id.user_id.id:
                    emp = 'RepMan'
            if app_rec.parent_id:
                if user == app_rec.parent_id.user_id.id:
                    emp = 'Man'
            if app_rec.parent_id and app_rec.reporting_manager_id:
                if user == app_rec.reporting_manager_id.user_id.id and app_rec.reporting_manager_id.id == app_rec.parent_id.id:
                    emp = 'RepandMan'
            if user == app_rec.employee_id.user_id.id:
                emp = 'Emp'
            elif self.env.user.has_group('hr_appraisal.group_hr_appraisal_manager'):
                if emp == 'Man':
                    emp = 'ManHR'
                elif emp == 'RepMan':
                    emp = 'RepManHR'
                elif emp == 'RepandMan':
                    emp = 'RepandManHR'
                else:
                    emp = 'HR'
        self.check_access = emp

class nf_appraisal_question(models.Model):
    _name = 'nf.appraisal.question'
    _description = 'Appraisal Questions'

    name = fields.Char('Questions')
    weightage = fields.Char('Weightage(%)')
    sequence = fields.Integer('Sequence')
    job = fields.Char('Job')
    job_ids = fields.Many2many('hr.job','nf_appraisal_job_rel','appraisal_id','job_id','Designation')

class nf_employee_rating_criteria(models.Model):
    _name = 'nf.employee.rating.criteria'
    _description = 'Employee Rating Criteria'
    _rec_name = 'rating'

    appraisal_id = fields.Many2one('hr.appraisal','Appraisal ID')
    rating = fields.Char('Rating')
    min_rate = fields.Integer('Minimum')
    max_rate = fields.Integer('Maximum')
    rating_scale = fields.Char('Rating Scale')
    criteria = fields.Char('Criteria')

class nf_appraisal_rating_criteria(models.Model):
    _name = 'nf.appraisal.rating.criteria'
    _description = 'Appraisal Rating Criteria'
    _rec_name = 'rating_scale'

    rating = fields.Char('Rating')
    min_rate = fields.Integer('Minimum')
    max_rate = fields.Integer('Maximum')
    rating_scale = fields.Char('Rating Scale')
    criteria = fields.Char('Criteria')