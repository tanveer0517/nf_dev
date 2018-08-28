from datetime import datetime

from openerp import api, fields, models, tools
from openerp.tools.translate import _
from openerp.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

Level_Selection = [('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')]
Priority_Selection = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5')]

class WizInterviewForm(models.TransientModel):
    _name='wiz.interview.form'
    
#     @api.multi
#     def default_get(self):
#         print"self======",self
#         context = self._context
#         print"====context====",context
#         parent_rec = self.env[context['active_model']].browse(context['active_id'])
#         print"=====parent_rec===",parent_rec,fields
#         if 'stage_id' in self:
#             res.update({'stage_id': parent_rec.stage_id.id})
#         return res

        
    
    user_id = fields.Many2one('res.users',string="User")
    survey_id = fields.Many2one('survey.survey',string="Interview Form")
    response_id = fields.Many2one('survey.user_input','Response')
    stage_id = fields.Many2one('hr.recruitment.stage','Stage')
    
    @api.multi
    def assign_interviewer(self):
        vals={}
        rec = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        response_id = []
        survey_id =[]
        vals.update({'survey_id':self.survey_id.id,'interviewer_id':self.user_id.id,'response_id':False,'title_action':'','date_action':False})
        if not rec.survey_id:
#             survey_id =rec.survey.id
              pass
        else:
            survey_id =rec.survey_id.id
            vals.update({'survey_id1':[(4,survey_id)]})
#         if rec.response_id:
#             response_id = rec.response_id.id
#             vals.update({'response_id1':[(4, response_id)]})
        sequence = 1
        if rec.interviewer_id:
            if rec.interviewer_hist_line:
                for line in rec.interviewer_hist_line:
                    sequence +=1
            vals.update({'interviewer_hist_line':[(0,False,{'sequence':sequence,'survey_id':survey_id,'response_id':response_id,'user_id':rec.interviewer_id.id,'title_action':rec.title_action,'date_action':rec.date_action})]})
#         if rec.interviewer_id:
        rec.write(vals)
        return True
    
#     def default_get(self, cr, uid, fields, context=None):
#         """ To get default values for the object.
#         @param self: The object pointer.
#         @param cr: A database cursor
#         @param uid: ID of the user currently logged in
#         @param fields: List of fields for which we want default values
#         @param context: A standard dictionary
#         @return: A dictionary which of fields with values.
#         """
#         print"=======",fields,context
#         res={}
#         parent_rec = self.pool.get(context.get('active_model')).browse(cr,uid,context.get('active_id'),context=context)
#         if 'stage_id' in fields:
#             res.update({'stage_id': parent_rec.stage_id.id})
#         return res
    
class TaskAssign(models.TransientModel):
    _name="task.assign"
    
    applicant_id = fields.Many2one('hr.applicant','Applicant')
    task_lines = fields.One2many('task.assign.lines','task_assign_id','Assign Tasks')
    
    @api.model
    def default_get(self,field):
        res={}
        parent_rec = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        parent_job_id = parent_rec.parent_job_id and parent_rec.parent_job_id.id or False
        lst = []
        if parent_job_id:
            self.env.cr.execute("select name,coalesce(expected_days,0) from task_onboarding_job where job_id = %s",(parent_job_id,))
            temp = self.env.cr.fetchall()
            date = datetime.strptime(fields.Date.context_today(self), "%Y-%m-%d")
            lst = [(0,False,{'name':val[0],'expected_date':(date + relativedelta(days=val[1])).strftime("%Y-%m-%d")}) for val in temp]
        res.update({'applicant_id': self._context.get('active_id'),
                    'task_lines':lst})
        return res
    
    def assign_task(self):
        return True
    
class taskAssignLines(models.TransientModel):
    _name="task.assign.lines"
    
    name=fields.Char('To Do')
    expected_date= fields.Date('Date')
    employee_id = fields.Many2one('res.users','Employee')
    task_assign_id = fields.Many2one('task.assign','Task')
    applicant_id = fields.Many2one('hr.applicant','Applicant')
                
class applicant_selection_note(models.TransientModel):
    _name = 'applicant.selection.note'
    
    @api.one
    @api.depends('communication_skill','resume_validation','jd_fitment','tech_competency')
    def compute_rating(self):
        com_remark = 0
        res_remark = 0
        jd_remark = 0
        tech_remark = 0
        attitude_remark = 0
        
        try:
          com_remark = int(self.communication_skill)
          res_remark = int(self.resume_validation)
          jd_remark = int(self.jd_fitment)
          tech_remark = int(self.tech_competency)
          attitude_remark = int(self.attitude)
        except ValueError:
             pass 
        self.rating = str(int(round((com_remark + res_remark + jd_remark + tech_remark + attitude_remark) / 5.0)))
            
    name=fields.Text('Summary')
    interview_type = fields.Selection([('Skype','Skype'),('Video Call','Video Call'),('Other','Other')],string='Interview Type')
    communication_skill = fields.Selection(Priority_Selection,'Communication Skill',default='0')
    communication_remark = fields.Text('Comment',size=100)
    resume_validation = fields.Selection(Priority_Selection,'Resume-Validation',default='0')
    resume_remark = fields.Text('Comment')
    jd_fitment = fields.Selection(Priority_Selection,'Jd Fitment',default='0')
    jd_fitment_remark = fields.Text('Comment')
    tech_competency = fields.Selection(Priority_Selection,string='Technical Competency',default='0')
    tech_remark = fields.Text('Comment')
    attitude = fields.Selection(Priority_Selection,string='Attitude/Cultural Fit',default='0')
    attitude_remark = fields.Text('Comment')
    rating = fields.Selection(Priority_Selection,string='Overall Rating',default='0',compute='compute_rating')
    stage_result = fields.Selection([('selected','Yes'),('rejected','No')],string='Recommended')
    level = fields.Selection([('Yes','Yes'),('No','No')],'Fit For the Role ?')
    fitc = fields.Selection([('Yes','Yes'),('No','No')],'Fit For the Company ?')
        
    def selection_note(self):
#         stage_result = self.env.context.get('stage_result','')
        active_id = self.env.context.get('active_id',False)
        applicant = self.env['hr.applicant'].browse(active_id)
        name = applicant.name
        stage_id = applicant.stage_id and applicant.stage_id.id or None
        if not applicant.interviewer_id:
            raise ValidationError("Select Interviewer")
        user_id = applicant.interviewer_id.id
        title_action = self.name
        date_action = fields.Date.context_today(self)
        
        interview_type = applicant.interview_type or 'Other'
        level = self.level
        communication_skill = self.communication_skill
        communication_remark = self.communication_remark
        resume_validation = self.resume_validation
        resume_remark = self.resume_remark
        jd_fitment = self.jd_fitment
        jd_fitment_remark = self.jd_fitment_remark
        tech_competency = self.tech_competency
        tech_remark = self.tech_remark
        rating = self.rating
        attitude = self.attitude
        attitude_remark = self.attitude_remark
        fitc = self.fitc
        
        if len(communication_remark) < 100:
            raise ValidationError("Current letters in Communication Remark are %s. Please fill atleast 100 letters."%(len(communication_remark,)))
        
        if len(resume_remark) < 100:
            raise ValidationError("Current letters in Resume Validation are %s. Please fill atleast 100 letters."%(len(resume_remark,)))
        
        if len(tech_remark) < 100:
            raise ValidationError("Current letters in Technical Competency are %s. Please fill atleast 100 letters."%(len(tech_remark,)))
        
        if len(attitude_remark) < 100:
            raise ValidationError("Current letters in Attitude Remark are %s. Please fill atleast 100 letters."%(len(attitude_remark,)))
        
#       If rating less than 3, candidate been rejected.
        stage_result = 'selected'
        if int(rating) < 3:
            stage_result = 'rejected'
        
        self.env.cr.execute("Insert INTO interviewer_hist_line (name,stage_id,user_id,title_action,date_action,applicant_id,stage_result,interview_type,level,communication_skill,communication_remark,resume_validation,resume_remark,jd_fitment,jd_fitment_remark,tech_competency,tech_remark,rating,attitude,attitude_remark,fitc) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (name,stage_id,user_id,title_action,date_action,active_id,stage_result,interview_type,level,communication_skill,communication_remark,resume_validation,resume_remark,jd_fitment,jd_fitment_remark,tech_competency,tech_remark,rating,attitude,attitude_remark,fitc))
        self.env.cr.execute("update hr_applicant set priority = coalesce(temp.avg_rating,'0') from (select applicant_id,cast(round(avg(cast(rating As float))) As char) As avg_rating from interviewer_hist_line group by applicant_id) temp where temp.applicant_id = hr_applicant.id and hr_applicant.id = %s",(active_id,))
        if stage_result == 'rejected':
           applicant.write({'interviewer_id':False,'select_note':False,'interview_time':False,'active':False})
        else:
           applicant.write({'interviewer_id':False,'select_note':False,'interview_time':False})    
                
class wiz_reject_onboarding_doc(models.TransientModel):
    _name = 'wiz.reject.onboarding.doc'
    _description = 'Reject Onboarding Documents'

    candidate_id = fields.Many2one('nf.joining.candidate','Candidate')
    onboarding_id = fields.Many2one('nf.candidate.onboarding','Onboarding')
    remarks = fields.Text('Remarks')

    @api.multi
    def reject_docs(self):
        if self.candidate_id and self.onboarding_id:
            self.candidate_id.write({'remarks':self.remarks,'doc_status':'Rejected'})
            self.onboarding_id.write({'state':'Rejected','accept': False,'date':False,'place':False})
            temp_id=self.env['mail.template'].sudo().search([('name','=','Candidate Doc Rejected')])
            if temp_id:
                temp_id.sudo().send_mail(self.candidate_id.id)
        return True