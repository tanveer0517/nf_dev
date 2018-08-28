from openerp import api, fields, models, _
from email import _name
from datetime import datetime 
import time

Grade_Selection = [('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')]

class employee_revision(models.Model):
    _name="employee.revision"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description="Employee Revision"
    
    def get_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit=1)
    
    name = fields.Char(string="Employee Revision")
    info_type = fields.Selection([('Designation Change', 'Designation Change'),('Internal Designation Change', 'Internal Designation Change'), ('Status Change','Status Change'),('Branch Change','Branch Change'),('Division Change','Division Change'),('Grade Change','Grade Change'),('Level Change','Level Change'),('Reporting Manager Change','Reporting Manager Change')], string="Information Type",track_visibility='onchange')
    current_status = fields.Selection([('active','Active'),('inactive','Inactive')], string='Current Status') 
    effective_start_date = fields.Date(string='Effective Date',default=fields.Date.context_today)
    emp_name= fields.Many2one('hr.employee',string="Employee",default=get_employee,track_visibility='always')
    new_status = fields.Selection([('active','Active'),('inactive','Inactive')],'New Status') 
    current_dept = fields.Many2one('hr.department',string="Current Division" )
    current_branch = fields.Many2one('hr.branch',string="Current Branch" )
    new_branch = fields.Many2one('hr.branch',string="New Branch",track_visibility='onchange')
    
    new_dept = fields.Many2one('hr.department',string=" New Division" )
    current_position = fields.Many2one('hr.job',string='Current Designation')
    new_designation = fields.Many2one('hr.job',string='New Designation')
    
    current_division = fields.Many2one('hr.division',string='Current Division')
    new_division = fields.Many2one('hr.division',string='New Division')
    
    current_grade=fields.Selection(Grade_Selection,string='Current Grade')
    new_grade=fields.Selection(Grade_Selection,string='New Grade')
    
    current_level=fields.Selection(Grade_Selection,string='Current Level')
    new_level=fields.Selection(Grade_Selection,string='New Level')
    
    current_reporting_head = fields.Many2one('hr.employee','Current Reporting Manager')
    new_reporting_head = fields.Many2one('hr.employee','New Reporting Manager',track_visibility='onchange')
    
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    state = fields.Selection([('Draft','Draft'),('Confirm','Confirm'),('Rejected','Rejected'),('Approved','Approved')],'Status',track_visibility='onchange',default='Draft')
    remark = fields.Text('Remark')
    user_id = fields.Many2one('res.users','User',track_visibility='onchange',default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company',string = 'Company',default=lambda self : self.env['res.company']._company_default_get('employee.revision'))
    current_internal_desig = fields.Char(string='Current Internal Designation',track_visibility='onchange')
    new_internal_desig = fields.Char(string='New Internal Designation',track_visibility='onchange')
    
    @api.onchange('emp_name','info_type')    
    def onchange_field(self):
        if self.emp_name:
            if self.info_type == 'Division Change':
                self.current_dept=self.emp_name.sub_dep and self.emp_name.sub_dep.id or False
                
            if self.info_type == 'Status Change':
                if self.emp_name.active:
                    self.current_status = 'active'
                else:
                    self.current_status = 'inactive'
            if self.info_type == 'Designation Change':
                self.current_position=self.emp_name.job_id and self.emp_name.job_id.id or False

            if self.info_type == 'Internal Designation Change':
                self.current_internal_desig=self.emp_name.intrnal_desig

            if self.info_type == 'Branch Change':
                self.current_branch=self.emp_name.branch_id and self.emp_name.branch_id.id or False
                
            if self.info_type == 'Grade Change':
                self.current_grade=self.emp_name.grade
                
            if self.info_type == 'Level Change':
                self.current_level=self.emp_name.level       
                
            if self.info_type == 'Reporting Manager Change':
                self.current_reporting_head = self.emp_name.coach_id and self.emp_name.coach_id.id or False    
        else:
            self.current_dept=False
            self.current_status=False
            self.current_position=False
            self.current_branch=False
            self.current_division=False
            self.current_grade=False
            self.current_level=False
            self.current_reporting_head = False
            self.current_internal_desig=False
            
    def send_employee_revision_email(self,status):
        if status=='draft':
            template=self.env['mail.template'].search([('name', '=', 'Employee Revision Request')], limit = 1)
            if template:
                template.send_mail(self.id)
        elif status=='reject':
            template=self.env['mail.template'].search([('name', '=', 'Employee Revision Rejected')], limit = 1)
            if template:
                template.send_mail(self.id)
        elif status=='approve':
            template=self.env['mail.template'].search([('name', '=', 'Employee Revision Approved')], limit = 1)
            if template:
                template.send_mail(self.id)
        return True        
            
    @api.multi
    def confirm(self):
        for rec in self:
            rec.write({'state':'Confirm'})
            #rec.send_employee_revision_email('confirm')    
        return True
    
    @api.multi 
    def rejected(self):
        for rec in self:
            self.send_employee_revision_email('reject')
            self.write({'state':'Rejected'})
        return True

    @api.model
    def create(self,vals):
        seq = self.env['ir.sequence'].next_by_code('emp.revision')
        vals.update({'name':seq})
        res = super(employee_revision, self).create(vals)
        res.send_employee_revision_email('draft')
        res.confirm()
        return res
     
    @api.multi
    def reset_to_draft(self):
        self.write({'state':'Draft'})
        return True        
            
    @api.multi
    def update_info(self):
        self.send_employee_revision_email('approve')
        if self.info_type=='Division Change':
            if self.new_dept.parent_id and self.new_dept.parent_id.manager_id:
               self.emp_name.write({'sub_dep':self.new_dept.id,'department_id':self.new_dept.parent_id.id,'parent_id':self.new_dept.parent_id.manager_id.id,'dept_date':self.effective_start_date,'department_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.dept_date,'department_id':self.current_dept.id,'attach_doc':self.attach_doc,'filename':self.filename})],})
            else:
               self.emp_name.write({'sub_dep':self.new_dept.id,'dept_date':self.effective_start_date,'department_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.dept_date,'department_id':self.current_dept.id,'attach_doc':self.attach_doc,'filename':self.filename})],}) 
                
        elif self.info_type=='Status Change':
            if self.new_status == 'active':
                state = True
            else:
                state = False
            self.emp_name.write({'active':state,'state_date':self.effective_start_date,'states_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.state_date,'states':self.current_status,'attach_doc':self.attach_doc,'filename':self.filename})]})
    
        elif self.info_type=='Designation Change':
            self.emp_name.write({'job_id':self.new_designation.id,'desig_date':self.effective_start_date,'designation_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.desig_date,'desig_id':self.current_position.id,'attach_doc':self.attach_doc,'filename':self.filename})],})

        elif self.info_type=='Internal Designation Change':
            self.emp_name.write({'intrnal_desig':self.new_internal_desig,'inter_desig_date':self.effective_start_date,'inter_desig_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.inter_desig_date,'internal_desig':self.current_internal_desig,'attach_doc':self.attach_doc,'filename':self.filename})],})   
    
        
        elif self.info_type=='Branch Change':
            self.emp_name.write({'branch_id':self.new_branch.id,
                                 'street'   : self.new_branch.street,
                                 'street2'  : self.new_branch.street2,
                                 'city'     : self.new_branch.city,
                                 'state_id' : self.new_branch.state_id and self.new_branch.state_id.id or False,
                                 'country_id1' : self.new_branch.country_id and self.new_branch.country_id.id or False,
                                 'zip' : self.new_branch.zip,
                                 'branch_date':self.effective_start_date,'branch_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.branch_date,'branch_id':self.current_branch.id,'attach_doc':self.attach_doc,'filename':self.filename})],})
                        
        elif self.info_type=='Grade Change':
            self.emp_name.write({'grade':self.new_grade,'grade_date':self.effective_start_date,'grade_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.grade_date,'grade':self.current_grade,'attach_doc':self.attach_doc,'filename':self.filename})],})
            
        elif self.info_type=='Level Change':
            self.emp_name.write({'level':self.new_level,'level_date':self.effective_start_date,'level_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.level_date,'level':self.current_level,'attach_doc':self.attach_doc,'filename':self.filename})],})
            
        elif self.info_type=='Reporting Manager Change':
            self.emp_name.write({'coach_id':self.new_reporting_head and self.new_reporting_head.id or False,'reporting_head_date':self.effective_start_date,'reporting_head_lines':[(0,False,{'name':self.emp_name.id,'till_date':self.effective_start_date,'start_date':self.emp_name.reporting_head_date,'reporting_head':self.current_reporting_head and self.current_reporting_head.id or False,'attach_doc':self.attach_doc,'filename':self.filename})],})

        self.write({'state':'Approved'})
        return True       
        
    
    
    