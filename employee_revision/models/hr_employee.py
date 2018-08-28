from openerp import api, fields, models, _
from email import _name
from datetime import datetime 
import time
from openerp.osv import osv
from odoo.exceptions import ValidationError

Grade_Selection = [('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')]

class hr_employee(osv.osv):
    _inherit="hr.employee"
    
    dept_date = fields.Date(string='Department Date')
    desig_date = fields.Date(string='Designation Date')
    inter_desig_date = fields.Date(string='Internal Designation Date')
    state_date = fields.Date(string='States Date')
    branch_date = fields.Date(string='Branch Date')
    division_date = fields.Date(string='Division Date')
    grade_date = fields.Date(string='Grade Date')
    level_date = fields.Date(string='Level Date')
    reporting_head_date = fields.Date(string='Reporting Head Date')
    designation_lines = fields.One2many('designation.lines','name',string='Designation Lines')
    inter_desig_lines = fields.One2many('inter.designation.lines','name',string='Internal Designation Lines')
    states_lines = fields.One2many('states.lines','name',string='Status Lines')
    department_lines = fields.One2many('department.lines','name',string='Division Lines')
    branch_lines = fields.One2many('branch.lines','name',string='Branch Lines')
    grade_lines = fields.One2many('grade.line','name',string='Grade Lines')
    level_lines = fields.One2many('level.line','name',string='Level Lines') 
    reporting_head_lines = fields.One2many('reporting.head.line','name',string='Reporting Head Lines')
    
    @api.model
    def create(self,vals):
        vals['dept_date'] = fields.Datetime.now()
        vals['desig_date'] = fields.Datetime.now()
        vals['inter_desig_date'] = fields.Datetime.now()
        vals['state_date'] = fields.Datetime.now()
        vals['branch_date'] = fields.Datetime.now()
        res = super(hr_employee,self).create(vals)
        if not res.join_date:
            raise ValidationError("Kindly provide date of joining")
        self.env.cr.execute("select leave_allocation(%s)",(res.id,))
        return res
    
class designation_lines(osv.osv):
    _name='designation.lines'
    _description='Designation Lines'
    
    name = fields.Many2one('hr.employee',string='Name')
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date('Till Date')
    desig_id = fields.Many2one('hr.job',string='Previous  Designation')  
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')  

class inter_designation_lines(osv.osv):
    _name='inter.designation.lines'
    _description='Internal Designation Lines'
    
    name = fields.Many2one('hr.employee',string='Name')
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date('Till Date')
    internal_desig = fields.Char(string='Previous Internal Designation')  
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    
class states_lines(osv.Model):
    _name='states.lines'
    _description='States Lines'
    
    name = fields.Many2one('hr.employee',string='Name')
    states = fields.Selection([('active', 'ACTIVE'), ('inactive', 'INACTIVE')], string=" Previous Status")
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date('Till Date')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')

class department_lines(osv.osv):
    _name='department.lines'
    
    name = fields.Many2one('hr.employee',string='Name')
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date(string='Till Date')
    department_id = fields.Many2one('hr.department',string=" Previous Division")
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    
   
    
class Branch_lines(osv.osv):
    _name='branch.lines'
    
    name = fields.Many2one('hr.employee',string='Name')
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date(string='Till Date')
    branch_id = fields.Many2one('hr.branch',string=" Previous Branch")
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
        

class grade_line(models.Model):
    _name='grade.line'    
    
    name = fields.Many2one('hr.employee',string='Name')
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date(string='Till Date')
    grade=fields.Selection(Grade_Selection,string='Previous Grade')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    
class level_line(models.Model):
    _name='level.line'    
    
    name = fields.Many2one('hr.employee',string='Name')
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date(string='Till Date')
    level=fields.Selection(Grade_Selection,string='Previous Level')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    
    
class reporting_head_line(models.Model):
    _name='reporting.head.line'    
    
    name = fields.Many2one('hr.employee',string='Name')
    start_date = fields.Date(string='Start Date')
    till_date = fields.Date(string='Till Date')
    reporting_head=fields.Many2one('hr.employee',string='Reporting manager')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')   
            
    
