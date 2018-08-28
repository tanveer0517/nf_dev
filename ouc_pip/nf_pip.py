from odoo import api, fields, models, _, SUPERUSER_ID
import datetime
import calendar
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime
import mimetypes
import smtplib
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from odoo.exceptions import except_orm, Warning
from odoo import exceptions

class nf_pip_category(models.Model):
  _name = 'nf.pip.category'
  _description = 'PIP Category'

  name = fields.Char('Name')

class nf_pip(models.Model):
    _name = 'nf.pip'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'employee_id'
    
    def get_manager_name(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.user.id)],limit = 1)
    
    employee_id = fields.Many2one('hr.employee','Employee',track_visibility='onchange')
    name = fields.Char('Performance Improvement Plan For')
    emp_id = fields.Char(string='Employee ID')
    join_date = fields.Date(string='DOJ')
    designation = fields.Char(string='Designation')
    department_id = fields.Many2one('hr.department',string='Department')
    branch_id = fields.Many2one('hr.branch',string='Branch')
    city_id = fields.Many2one('ouc.city',string='City')
    manager_id = fields.Many2one('hr.employee',string='Department Manager',default=get_manager_name)
    reporting_manager = fields.Many2one('hr.employee',string='Reporting Manager')
    start_date = fields.Date(track_visibility='onchange',string='PIP Start Date',default=datetime.now().strftime('%Y-%m-%d'))
    end_date = fields.Date(track_visibility='onchange',string='PIP End Date')
    state = fields.Selection([('Draft','Draft'),('Confirm','Confirm'),('Extended','Extended'),('Approved','Approved'),('Rejected','Rejected')],string='State',track_visibility='onchange',default='Draft')
    current_position = fields.Text(track_visibility='onchange',string='Current Position of Employee')
    final_recommendation = fields.Text(track_visibility='onchange',string='Final Recommendation')
    hr_comment = fields.Text(track_visibility='onchange',string='HR Comment')
    employee_comment = fields.Text(track_visibility='onchange',string='Manager Comment')
    pip_improvement = fields.One2many('nf.pip.improvement','pip_id',string='Improvement Opportunity',track_visibility='onchange')
    leaves = fields.Char('Last 3 Months Leaves')
    meetings = fields.Char('Last 3 Months Meetings')
    first_month_revenue = fields.Char(string='First Month Net Revenue')
    second_month_revenue = fields.Char(string='Second Month Net Revenue')
    third_month_revenue = fields.Char(string='Third Month Net Revenue')
    current_month_revenue = fields.Char(string='Current Month Net Revenue')
    category = fields.Many2many('nf.pip.category','pip_improvement_category','pip_id','category_id', track_visibility='onchange')
    category_comment = fields.Text('Category Comment')
    disciplinary_issue = fields.Selection([('Yes','Yes'),('No','No')],'Are there any disciplinary issues with the employee?')
    disciplinary_comment =  fields.Text('Disciplinary Comment')
    pip_aim = fields.Text('Aim of the PIP')
    improvement_opp = fields.One2many('nf.pip.improvement.opp','pip_id',string='Performance Improvement Opportunity',track_visibility='onchange')
    final_decision = fields.Selection([('Extend PIP','Extend PIP'),('Resume Employment','Resume Employment'),('Terminate Employment','Terminate Employment')],'Final Decision')
    extend_date = fields.Date('PIP Extend Date')
    new_pip = fields.Boolean('New PIP')
    check_access = fields.Char('Check Access', compute='_check_access')
    sales = fields.Boolean('Is Sales?')
    show_pip_outcome = fields.Boolean('Show PIP Outcome')

    @api.onchange('category')
    def onchange_category(self):
      if self.category:
        vals = []
        for rec in self.category:
          vals.append((0,False,{'objective':rec.id}))
        self.improvement_opp = vals

    @api.one
    @api.depends('employee_id')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        if self.employee_id:
            if self.reporting_manager:
                if user == self.reporting_manager.user_id.id:
                    emp = 'RepMan'
            if self.manager_id:
                if user == self.manager_id.user_id.id:
                    emp = 'Man'
            if self.manager_id and self.reporting_manager:
                if user == self.reporting_manager.user_id.id and self.reporting_manager.id == self.manager_id.id:
                    emp = 'RepandMan'
            if user == self.employee_id.user_id.id:
                emp = 'Emp'
            elif self.env.user.has_group('hr.group_hr_manager'):
                if emp == 'Man':
                    emp = 'ManHR'
                elif emp == 'RepMan':
                    emp = 'RepManHR'
                elif emp == 'RepandMan':
                    emp = 'RepandManHR'
                else:
                    emp = 'HR'
        self.check_access = emp

    @api.onchange('end_date')
    def onchange_end_date(self):
      if self.end_date:
        if self.start_date:
          end_date = (datetime.strptime(self.start_date,'%Y-%m-%d')+relativedelta(months=1)).strftime('%Y-%m-%d')
          if self.end_date < end_date:
            raise exceptions.ValidationError(_('End Date must be after 1 month from Start Date'))
        curr_date=(datetime.now()).strftime("%Y-%m-%d")
        if self.end_date and self.end_date <= curr_date:
          self.show_pip_outcome = True

    @api.onchange('extend_date')
    def onchange_extend_date(self):
      if self.extend_date:
        if self.start_date:
          extend_date = (datetime.strptime(self.start_date,'%Y-%m-%d')+relativedelta(months=3)).strftime('%Y-%m-%d')
          if self.extend_date > extend_date:
            raise exceptions.ValidationError(_('Extend Date should not be after 3 months from Start Date'))

    @api.onchange('start_date')
    def onchange_start_date(self):
      if self.start_date:
        if self.end_date:
          start_date = (datetime.strptime(self.end_date,'%Y-%m-%d')-relativedelta(months=1)).strftime('%Y-%m-%d')
          if self.start_date > start_date:
            raise exceptions.ValidationError(_('Start Date must be before 1 month from End Date'))

    @api.multi
    def write(self,vals):
        if vals.get('end_date',False):
          start_date = vals.get('start_date',False) or self.start_date
          if start_date:
            end_date = (datetime.strptime(start_date,'%Y-%m-%d')+relativedelta(months=1)).strftime('%Y-%m-%d')
            if vals.get('end_date',False) < end_date:
              raise exceptions.ValidationError(_('End Date must be after 1 month from Start Date'))
        if vals.get('start_date',False):
          end_date = vals.get('end_date',False) or self.end_date
          if end_date:
            start_date = (datetime.strptime(end_date,'%Y-%m-%d')-relativedelta(months=1)).strftime('%Y-%m-%d')
            if vals.get('start_date',False) > start_date:
              raise exceptions.ValidationError(_('Start Date must be before 1 month from End Date'))
        if vals.get('extend_date',False):
          start_date = vals.get('start_date',False) or self.end_date
          if start_date:
            extend_date = (datetime.strptime(start_date,'%Y-%m-%d')+relativedelta(months=3)).strftime('%Y-%m-%d')
            if vals.get('extend_date',False) > extend_date:
              raise exceptions.ValidationError(_('Extend Date should not be after 3 months from Start Date'))
          vals.update({'state':'Extended'})
          self.send_email_notification('Extend')
        if vals.get('final_decision',False):
          if vals.get('final_decision',False) == 'Resume Employment':
            temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Resume Employment')])
            if temp_id:
              temp_id.send_mail(self.id)
          elif vals.get('final_decision',False) and vals.get('final_decision',False) == 'Terminate Employment':
            temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Terminate Employment')])
            if temp_id:
              temp_id.send_mail(self.id)
        super(nf_pip,self).write(vals)
        return True

    @api.onchange('manager_id')
    def onchange_manager(self):
      man_id=self.manager_id
      if man_id:
        employees=[]
        self.new_pip=True
        emp_obj=self.env['hr.employee']
        if not self.env.user.has_group('hr.group_hr_manager'):
          emp_ids=emp_obj.sudo().search(['|',('parent_id','=',man_id.id),('coach_id','=',man_id.id)])
          for emp in emp_ids:
            employees.append(emp.id)
        else:
          emp_ids=emp_obj.sudo().search([])
          for emp in emp_ids:
            employees.append(emp.id)
        return {'domain':{'employee_id':[('id','in',employees)]}}


    @api.onchange('employee_id','start_date')
    def onchange_employee(self):
      if self.employee_id:
        cr=self.env.cr
        emp = self.employee_id
        self.name = emp.name_related
        self.emp_id = emp.nf_emp
        self.join_date = emp.join_date
        self.department_id = emp.sub_dep and emp.sub_dep.id or False
        self.designation = emp.intrnal_desig or ''
        self.branch_id = emp.branch_id and emp.branch_id.id or False
        self.city_id = emp.q_city_id and emp.q_city_id.id or False
        self.manager_id = emp.parent_id and emp.parent_id.id or False
        self.reporting_manager = emp.coach_id and emp.coach_id.id or False
        if self.employee_id.sub_dep and self.employee_id.sub_dep.parent_id and self.employee_id.sub_dep.parent_id.name == 'Sales':
          self.sales = True
        if self.start_date:
          curr_date = datetime.strptime(self.start_date,'%Y-%m-%d')
          back_date = (curr_date-relativedelta(months=3))
          cr.execute("SELECT sum(number_of_days_temp) from hr_holidays WHERE type='remove' and employee_id=%s and date_from>=%s and date_to<=%s",(emp.id,back_date.strftime("%Y-%m-%d 00:00:01"),curr_date.strftime("%Y-%m-%d 23:59:59")))
          no_leaves=cr.fetchone()[0] or 0
          cr.execute("SELECT count(*) from crm_meeting_view WHERE sp_id=%s and date_of_meeting>=%s and date_of_meeting<=%s",(emp.user_id.id,back_date.strftime("%Y-%m-%d 00:00:01"),curr_date.strftime("%Y-%m-%d 23:59:59")))
          no_meetings=cr.fetchone()[0] or 0
          self.leaves=no_leaves
          self.meetings=no_meetings
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
          self.first_month_revenue=first_revenue
          self.second_month_revenue=second_revenue
          self.third_month_revenue=last_revenue

    @api.model
    def create(self,vals):
      cr=self.env.cr
      if vals.get('end_date',False):
          if vals.get('start_date',False):
            end_date = (datetime.strptime(vals.get('start_date',False),'%Y-%m-%d')+relativedelta(months=1)).strftime('%Y-%m-%d')
            if vals.get('end_date',False) < end_date:
              raise exceptions.ValidationError(_('End Date must be after 1 month from Start Date'))

      if vals.get('start_date',False):
        if vals.get('end_date',False):
          start_date = (datetime.strptime(vals.get('end_date',False),'%Y-%m-%d')-relativedelta(months=1)).strftime('%Y-%m-%d')
          if vals.get('start_date',False) > start_date:
            raise exceptions.ValidationError(_('Start Date must be before 1 month from End Date'))
      emp=self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
      if emp:
        emp=emp[0]
        curr_date = datetime.strptime(vals.get('start_date'),'%Y-%m-%d')
        back_date = (curr_date-relativedelta(months=3))
        cr.execute("SELECT sum(number_of_days_temp) from hr_holidays WHERE type='remove' and employee_id=%s and date_from>=%s and date_to<=%s",(emp.id,back_date.strftime("%Y-%m-%d 00:00:01"),curr_date.strftime("%Y-%m-%d 23:59:59")))
        no_leaves=cr.fetchone()[0] or 0
        cr.execute("SELECT count(*) from crm_meeting_view WHERE sp_id=%s and date_of_meeting>=%s and date_of_meeting<=%s",(emp.user_id.id,back_date.strftime("%Y-%m-%d 00:00:01"),curr_date.strftime("%Y-%m-%d 23:59:59")))
        no_meetings=cr.fetchone()[0] or 0
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
        vals.update({'name':emp.name_related,'emp_id':emp.nf_emp,'join_date':emp.join_date,'department_id':emp.sub_dep and emp.sub_dep.id or False,'designation':emp.intrnal_desig,'branch_id':emp.branch_id and emp.branch_id.id,'manager_id':emp.parent_id and emp.parent_id.id,'reporting_manager':emp.coach_id and emp.coach_id.id or False,'city_id':emp.q_city_id and emp.q_city_id.id or False,'leaves':no_leaves,'meetings':no_meetings,'start_date': datetime.now().strftime("%Y-%m-%d"),'first_month_revenue':first_revenue,'second_month_revenue':second_revenue,'third_month_revenue':last_revenue})
      rec = super(nf_pip, self).create(vals)
      rec.send_email_notification('Draft')
      return rec
    
    @api.multi
    def send_email_notification(self,status):
      temp_id=False
      if status=='Draft':
        temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Request')])
      elif status=='Confirm':
        temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Confirm')])
      elif status=='Draft':
        temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Extend')])
      elif status=='Approved':
        temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Approved')])
      elif status=='Rejected':
        temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Rejected')])
      if temp_id:
        temp_id.send_mail(self.id)
      return True

    @api.multi
    def confirm(self):
      manager_ids=[]
      if self.manager_id:
        manager_ids.append(self.manager_id.user_id and self.manager_id.user_id.id)
      if self.reporting_manager:
        manager_ids.append(self.reporting_manager.user_id and self.reporting_manager.user_id.id)

      if self.env.user.has_group('hr.group_hr_manager') or self.env.uid in manager_ids:
        if self.final_decision:
          self.write({'state':'Confirm'})
          self.send_email_notification('Confirm')
        else:
          raise exceptions.ValidationError(_('Sorry, you can not submit this, please add Final Decision and Manager Comment before submitting this.'))
      else:
        raise exceptions.ValidationError(_('Sorry, you can not submit this, only the manager or reporting manager of the employee can submit this.'))
      return True

    @api.multi
    def approved(self):
      if self.hr_comment:
        self.write({'state':'Approved'})
        self.send_email_notification('Approved')
      else:
        raise exceptions.ValidationError(_('Please add comment before approving it.'))
      return True
     
    @api.multi 
    def rejected(self):
      if self.hr_comment:
        self.write({'state':'Rejected'})
        self.send_email_notification('Rejected')
      else:
          raise exceptions.ValidationError(_('Please add comment before rejecting it.'))
      return True
     
    @api.multi
    def reset_to_draft(self):
      self.write({'state':'Draft'})
      return True

    @api.model
    def send_pip_notification(self):
      curr_date=(datetime.now()).strftime("%Y-%m-%d")
      for rec in self.sudo().search([('end_date','=',curr_date)]):
        rec.sudo().write({'show_pip_outcome':True})
        temp_id=self.env['mail.template'].sudo().search([('name','=','PIP Notification')])
        if temp_id:
          temp_id.send_mail(rec.id)
      return True

class nf_pip_improvement(models.Model):
    _name = 'nf.pip.improvement'

    pip_id = fields.Many2one('nf.pip', string='PIP')
    improvement_needs = fields.Text(string='Improvement/Development Needs')
    action_steps = fields.Text(string='Action Steps')
    target_date = fields.Date(string='Target Date')
    progress_reviews = fields.Text(string='Progress Reviews')

class nf_pip_improvement_opp(models.Model):
    _name = 'nf.pip.improvement.opp'

    pip_id = fields.Many2one('nf.pip', string='PIP')
    objective = fields.Many2one('nf.pip.category','Improvement Objective')
    action_steps = fields.Text(string='Corrective Action')
    review_interval = fields.Selection([('Every 10th Day','Every 10th Day'),('Every 20th Day','Every 20th Day'),('Every 30th Day','Every 30th Day')],string='Review Interval')
    frequency = fields.Selection([('Once a week','Once a week'),('Twice a week','Twice a week'),('Once in 15 days','Once in 15 days')],string='Frequency')
    feedback = fields.Text('Feedback')
