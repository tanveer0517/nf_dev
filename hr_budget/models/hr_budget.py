from openerp import api, fields, models, _
from email import _name
from datetime import datetime 
import time
import os
#from openerp.addons.web.http import request
import smtplib
import urlparse
import mimetypes
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from dateutil.relativedelta import relativedelta
from pygments.lexer import _inherit
from lib2to3.fixer_util import String
from datetime import date, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from reportlab.lib.pdfencrypt import computeO
from odoo import exceptions
from odoo.exceptions import ValidationError, Warning
from openerp.osv import osv
import json,urllib,urllib2
import pyPdf
import xml.dom.minidom
import zipfile
from StringIO import StringIO

FTYPES = ['docx', 'pptx', 'xlsx', 'opendoc', 'pdf']

def textToString(element):
    buff = u""
    for node in element.childNodes:
        if node.nodeType == xml.dom.Node.TEXT_NODE:
            buff += node.nodeValue
        elif node.nodeType == xml.dom.Node.ELEMENT_NODE:
            buff += textToString(node)
    return buff



class HrBudget(models.Model):
    _name = "hr.budget"
    _description = "HR Budget"
    
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    
    @api.model
    def _default_user(self):
        return self.env.user.id
    
    name = fields.Char(string="Serial Number")
    dept = fields.Many2one('hr.department',string="Division" , required=True)
    manager = fields.Many2one('hr.employee', string="Manager" )
    date = fields.Date(string='Date',default=fields.datetime.now())
#     branch = fields.Many2one('hr.department',string='Branch')
    branch_id =fields.Many2one('hr.branch','Branch')
    budget_lines = fields.One2many('budget.lines','budget_id',string='Budget Lines')    
    comments = fields.Text(string='Comments')
    user_id = fields.Many2one('res.users','User',default=_default_user)
    send_to = fields.Many2one('res.users',string='Send To')    
    review_by = fields.Many2one('res.users',string='Review By') 
    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('approve', 'Approved'),
            ], track_visibility='onchange' ,default='draft')
    budget_year = fields.Selection([(num, str(num) + '-' + str(num + 1)[2:]) for num in range(2012, (datetime.now().year)+5 )], 'Budget Year')
    
    @api.onchange('dept')
    def onchange_field(self):
        if self.dept :
            self.manager = self.dept.manager_id.id
         
    @api.multi
    def _get_sub_total(self):
            
            sum=0
            for lines in self.budget_lines:
                sum+=lines.total_cost
                
            self.sub_total=sum        
    sub_total = fields.Float(string="Budget Sub-Total", compute='_get_sub_total')
    
    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq = self.env['ir.sequence'].next_by_code('hr.budget')
            vals['name'] = seq
        return super(HrBudget, self).create(vals)
        
    @api.multi
    def send_email_confirm(self):
            
            et=[]
            et1=[]
            for lines in self.budget_lines:
                r = lines.job_id.name
                r1 = str(lines.new_res)
                et.append(r)
                et1.append(r1)
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            rec_id = self.id
            print"context====",self._context['params']['action']
#             model = self
            context = self._context
            context.get('active_model')
            action_id = self._context['params']['action']
            a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
            ef = """<a href="""+a+""">"""+self.name+"""</a>"""
            
            
            out_server = self.env['ir.mail_server'].search([])
            if out_server:
                out_server = out_server[0]
                emailfrom=''
                emailto = []
                if out_server.smtp_user:
                    emailfrom =out_server.smtp_user
                if self.send_to:
                    emailto = [self.send_to.login]
                msg = MIMEMultipart()
                if emailfrom and emailto:
                    msg['From'] = emailfrom
                    if emailto:
                        msg['To'] = ", ".join(emailto)
                    msg['Subject'] = 'Please Confirm Budget'
                    html = """<!DOCTYPE html>
                             <html>
                             <p>Dear HOD,</p>
                             <tr>
                                  <td ><left><p>Mr.<b> """+str(self.manager.name)+""" </b>From<b> """+str(self.dept.name)+"""</b> Department<b> """+str(self.branch_id.name)+""" </b>Branch has requested.</P></left></td>
                             </tr>
        
                               <body>
                            
                            <table>
        
                            <tbody>
                            
                            <tr>
                            
                            <td style="width:135px" ><b>Job Position</b></td>
                            
                            <td style="width: 85px;" ><b>New Employees</b></td>
                            
                                             
                            </tr>
                            
                            
                            
                            <tr >
                            
                            <td class="text-center" style="width:135px">"""+ "<br/>".join(et)+""" </td>
                            
                            
                            <td class="text-center" style="width: 85px;">"""+ "<br/>".join(et1)+"""</td>
                            
                            </tr>
                            
                            
                            <tbody>
                            
                            <table>
        
        
        
                           <p>Please Click Here  """+ef+""" to Approve  Budget.</p>
                                
                            
                           
                           <p>Regards</p>
                           <p>Admin</p>
                           </body>
                           
                           
            
                            </html>
                          """
            #        part1 = MIMEText(text, 'plain')
                    part1 = MIMEText(html, 'html')
                    msg.attach(part1)
            #        msg.attach(part2)
                    server = smtplib.SMTP_SSL(out_server.smtp_host,out_server.smtp_port)
            #        server.ehlo()
            #         server.starttls()
                    server.login(emailfrom,out_server.smtp_pass)
                    text = msg.as_string()
                    server.sendmail(emailfrom, emailto , text)
                    server.quit()
            return True
    
    
    @api.multi
    def send_email_revise(self):
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            rec_id = self.id
#             print"====self.env=====",self._model
            print"context====",self._context['params']['action']
#             model = self._model
            context = self._context
            context.get('active_model')
            action_id = self._context['params']['action']
            a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
            ef = """<a href="""+a+""">"""+self.name+"""</a>"""
            
            
            out_server = self.env['ir.mail_server'].search([])
            if out_server:
                out_server = out_server[0]
                emailto=[]
                emailfrom =out_server.smtp_user
                if self.user_id.login:
                    emailto.append(self.user_id.login)
                print"emailfrom==emailto==",emailfrom,emailto
                if emailfrom and emailto:
                    msg = MIMEMultipart()
                    msg['From'] = emailfrom
                    msg['To'] = ", ".join(emailto)
                    msg['Subject'] = 'Please Revise Budget'
            
                    html = """<!DOCTYPE html>
                             <html>
                             
                             <tr>
                                  <td style="color:#FF69B4"><left><h2><p>MR """+str(self.manager.name)+""" From """+str(self.dept.name)+""" Department """+str(self.branch_id.name)+""" Branch has requested  To review  Job Position .</P></h2></left></td>
                             </tr>
        
                               <body>
                           <p>Please Click Here """+ef+""" to Revise Budget.</p>      
                           <p>Regards</p>
                           <p>Admin</p>  
                           
                           </body>
                           
                               
                            </html>
                          """
                    #        part1 = MIMEText(text, 'plain')
                    part1 = MIMEText(html, 'html')
                    msg.attach(part1)
            #        msg.attach(part2)
                    server = smtplib.SMTP_SSL(out_server.smtp_host,out_server.smtp_port)
            #        server.ehlo()
            #         server.starttls()
                    server.login(emailfrom,out_server.smtp_pass)
                    text = msg.as_string()
                    server.sendmail(emailfrom, emailto , text)
                    server.quit()
            return True      
    
    
    @api.multi
    def send_email_approve(self):
            
            et=[]
            et1=[]
            for lines in self.budget_lines:
                r = lines.job_id.name
                r1 = str(lines.new_res)
                et.append(r)
                et1.append(r1)
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            rec_id = self.id
#             print"====self.env=====",self._model
            print"context====",self._context['params']['action']
#             model = self._model
            context = self._context

            context.get('active_model')
            action_id = self._context['params']['action']
            a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
            ef = """<a href="""+a+"""> """+self.name+"""</a>"""
            
            
            out_server = self.env['ir.mail_server'].search([])
            if out_server:
                out_server = out_server[0]
                emailfrom =out_server.smtp_user
                emailto = [self.manager.work_email]
                msg = MIMEMultipart()
                if emailfrom:
                    msg['From'] = emailfrom
                    if emailto:
                        msg['To'] = ", ".join(emailto)
                    msg['Subject'] = 'For Budget Approved '
                    html = """<!DOCTYPE html>
                             <html>
                             <p>Dear HOD,</p>
                             <tr>
                                  <td ><left><p>Mr.<b> """+str(self.manager.name)+""" </b>From<b> """+str(self.dept.name)+"""</b> Department<b> """+str(self.branch_id.name)+""" </b>Branch has requested.</P></left></td>
                             </tr>
        
                               <body>
                            
                            <table>
        
                            <tbody>
                            
                            <tr>
                            
                            <td style="width:135px" ><b>Job Position</b></td>
                            
                            <td style="width: 85px;" ><b>New Employees</b></td>
                            
                                             
                            </tr>
                            
                            
                            
                            <tr >
                            
                            <td class="text-center" style="width:135px">"""+ "<br/>".join(et)+""" </td>
                            
                            
                            <td class="text-center" style="width: 85px;">"""+ "<br/>".join(et1)+"""</td>
                            
                            </tr>
                            
                            
                            <tbody>
                            
                            <table>
        
        
        
                           <p>Here is your """+ef+"""  Approved  Budget.</p>
                                
                           <p>Keep up the Great Work of Now Floats.</p>  
                           
                           <p>Regards</p>
                           <p>Admin</p>
                           </body>
                           
                           
            
                            </html>
                          """
            #        part1 = MIMEText(text, 'plain')
                    part1 = MIMEText(html, 'html')
                    msg.attach(part1)
            #        msg.attach(part2)
                    server = smtplib.SMTP_SSL(out_server.smtp_host,out_server.smtp_port)
            #        server.ehlo()
            #         server.starttls()
                    server.login(emailfrom,out_server.smtp_pass)
                    text = msg.as_string()
                    server.sendmail(emailfrom, emailto , text)
                    server.quit()
            return True
    
    
    @api.multi
    def confirm_budget(self):
#         self.send_email_confirm()
        self.write({'state':'confirm'})
        
    @api.multi
    def approve_budget(self):
        for line in self.budget_lines:
            print'========position=====',line.job_id
            budgeted_emp = line.new_res #line.job_id.budgeted_emp +
            line.job_id.write({'budgeted_emp':budgeted_emp})
            print"========complete=========="
        self.write({'state':'approve'})
#         self.send_email_approve()
        return True
    
#             sql = """
#                 UPDATE public.hr_job
#                     SET budgeted_emp = (
#                         SELECT new_res
#                         FROM public.budget_lines
#                         WHERE public.budget_lines.id = public.hr_job.id
#         );
#     
#                 """
#         self.env.cr.execute(sql, (self.id, ))
        
         
      
    @api.multi
    def revise_budget(self):
#         self.send_email_revise()
        for line in self.budget_lines:
            if self.state == 'approve':
                budgeted_emp = line.job_id.budgeted_emp - line.new_res
                line.job_id.write({'budgeted_emp':budgeted_emp})
        self.write({'state':'draft'})
     
    
    
  
class budget_lines(models.Model):
    _name="budget.lines"
    _description="Budget Lines"
    
    @api.model
    def default_get(self, fields):
        rec =  super(budget_lines, self).default_get(fields)
        if 'budget_year' in self._context:
            year = self._context.get('budget_year')
            if not year:
                raise ValidationError("Please select budget year")
            date = str(year) + '04' + '01'
    #             date = time.strftime('%Y-04-01')
            self.env.cr.execute("select * from get_month(%s)",(date,))
            temp = [(0,False,{'date':val}) for val in self.env.cr.fetchone()]
            rec.update({'monthly_budget_line_ids':temp})
        return rec
    
    @api.multi
    def get_max_budget(self):
        for bl in self:
            self.env.cr.execute("select coalesce(max(headcount),0) from monthly_budget_line where budget_line_id = %s limit 1",(bl.id,))
            bl.budget_headcount = self.env.cr.fetchone()[0]  
            
    name = fields.Char(string='Position')
    budget_id = fields.Many2one('hr.budget',string="Budget",invisible=1)
    job_id = fields.Many2one('hr.job',string="Job Position")
    emp_total = fields.Integer(string='Existing Headcount', compute='onchange_emp_total')
    new_res = fields.Integer(string='New Resources')
    level = fields.Char(string='Level')
    avg_cost = fields.Float(string='Average Cost (Rs.)')
    year = fields.Selection([(num, str(num)) for num in range(2000, (datetime.now().year)+1 )], 'Year')
    total_cost = fields.Integer(string='Total Cost')
    manager_id = fields.Many2one('hr.employee', string="Manager" , domain="[('job_id','=',1)]")
    date = fields.Date('Create Date', default=fields.datetime.now())
    user_id = fields.Many2one('res.users','User')
    monthly_budget_line_ids = fields.One2many('monthly.budget.line','budget_line_id',string="Monthly Budget")
    budget_headcount = fields.Integer('Budgeted Headcount',compute='get_max_budget')
    
    @api.onchange('emp_total', 'avg_cost')
    def onchange_field(self):
        if self.emp_total or self.avg_cost:
            self.total_cost = self.emp_total * self.avg_cost
    
    @api.onchange('job_id')
    def onchange_emp_total(self):
        for line in self:
            budget_id = line.budget_id
            if budget_id:
                branch_id = budget_id.branch_id and budget_id.branch_id.id or None
                department_id = budget_id.dept and budget_id.dept.id or None
                job_id = line.job_id
                if job_id and department_id and branch_id:
                   self.env.cr.execute("select coalesce(count(emp.id),0) from hr_employee emp left join resource_resource AS res on emp.resource_id = res.id where emp.branch_id = %s and emp.sub_dep = %s and emp.job_id = %s and res.active = True",(branch_id,department_id,job_id.id))
                   line.emp_total = self.env.cr.fetchone()[0]
                else:
                    line.emp_total = 0
                       
                
class monthly_budget_line(models.Model):
    _name="monthly.budget.line"
    _order = 'date'
    
    date = fields.Date(string='Month',help="select first date or any date of the month")
    headcount = fields.Integer(string='Head Count')
    budget_line_id = fields.Many2one('budget.line',string='Budget Line')
    
class HrRequisition(models.Model):
    _name="hr.requisition"
    _description="Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.model
    def _default_user(self):
        return self.env.user.id
    
    @api.multi
    def _get_total(self):
            sum=0
            for lines in self.requisition_line:
                print "lines=====",lines
                sum+=lines.avail_budget
            self.total_avail_budget=sum
            
    def get_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit = 1)        
     
    name = fields.Char(string="Requisition Number")
    department = fields.Many2one('hr.department',string="Division")
    requested_by = fields.Many2one('hr.employee',string='Requested By',default=get_employee)
    requested_to = fields.Many2one('res.users',string='Requested To')
    allocated_to = fields.Many2one('res.users',string='Allocated To TL')
    user_id = fields.Many2one('res.users','Created By',default=_default_user)
    manager = fields.Many2one('hr.employee',string='Manager' , domain="[('job_id','=',1)]")
#     branch = fields.Many2one('hr.department',string='Branch')
    branch_id =fields.Many2one('hr.branch','Branch')
    date = fields.Date(string='Date',default=fields.datetime.now())
    replacement = fields.Selection([('yes', 'YES'), ('no', 'NO')], string="Replacement")
    replace_of = fields.Many2one('hr.employee',string='Replacement Of')
     
    requisition_line = fields.One2many('requisition.line','requisition_id',string='Requisition Lines')    
    comments = fields.Text(string='Comments')
    total_avail_budget = fields.Float(string="Total Available Budget", compute='_get_total')     
    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('approve', 'Approved'),
            ], track_visibility='onchange',default='draft')
    month = fields.Selection([(4,'Apr'),(5,'May'),(6,'June'),(7,'July'),(8,'Aug'),(9,'Sept'),(10,'Oct'),(11,'Nov'),(12,'Dec'),(1,'Jan'),(2,'Feb'),(3,'Mar')],string='Month')
    year = fields.Selection([(num, str(num)) for num in range(2015, (datetime.now().year)+5 )], string='Year')
    
    @api.onchange('branch_id')
    def onchange_field(self):
        if self.branch_id:
            self.manager = self.branch_id.manager_id
            self.allocated_to = self.branch_id.tl_manager_id
                
    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq = self.env['ir.sequence'].next_by_code('hr.requisition')
            vals['name'] = seq
        return super(HrRequisition, self).create(vals)
    
    
    @api.multi
    def send_email_to_hod(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        rec_id = self.id
#         print"====self.env=====",self._model
        print"context====",self._context['params']['action']
#         model = self._model
        context = self._context
        context.get('active_model')
        action_id = self._context['params']['action']
        a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
        ef = """<a href="""+a+""">Click Here """+self.name+"""</a>"""
    
        out_server = self.env['ir.mail_server'].search([])
        if out_server:
            out_server = out_server[0]
            
            emailfrom =out_server.smtp_user
            emailto =[]
            if self.requested_by and self.requested_by.work_email:
                emailto.append(self.requested_by.work_email)
            if self.manager and self.manager.work_email:
                emailto.append(self.manager.work_email)
                
            if emailfrom and emailto:
                
                msg = MIMEMultipart()
                msg['From'] = emailfrom
                msg['To'] = ", ".join(emailto)
                msg['Subject'] = 'Requisition Approved'
        
                html = """<!DOCTYPE html>
                         <html>
                         <p>Dear Sir,</p>
                         
                         <p>Your request has been approved and sent to Talent team. </p>
                         <p>You can expect interviews next week.</p>
                         <p>Please """+ef+""" to view requisition.</p>
                           <body>
                            
                       <p>Regards</p>
                       
                       <p>HR</p>  
                       </body>
                       
                           
                        </html>
                      """
        #        part1 = MIMEText(text, 'plain')
                part1 = MIMEText(html, 'html')
                msg.attach(part1)
        #        msg.attach(part2)
                server = smtplib.SMTP_SSL(out_server.smtp_host,out_server.smtp_port)
        #        server.ehlo()
        #         server.starttls()
                server.login(emailfrom,out_server.smtp_pass)
                text = msg.as_string()
                server.sendmail(emailfrom, emailto , text)
                server.quit()
        return True
    
    @api.multi
    def send_email_confirm_requisition(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        rec_id = self.id
#         print"====self.env=====",self._model
        print"context====",self._context['params']['action']
#         model = self._model
        context = self._context

        context.get('active_model')
        
        action_id = self._context['params']['action']
        a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
        ef = """<a href="""+a+"""> """+self.name+"""</a>"""
    
        out_server = self.env['ir.mail_server'].search([])
        if out_server:
            out_server = out_server[0]
            
            emailfrom =out_server.smtp_user
            emailto =[]
            if self.requested_to and self.requested_to.login:
                emailto.append(self.requested_to.login)
            if emailfrom and emailto:
                msg = MIMEMultipart()
                msg['From'] = emailfrom
                msg['To'] = ", ".join(emailto)
                msg['Subject'] = 'For Requisition Approval'
        
                html = """<!DOCTYPE html>
                         <html>
                         <p>Dear Sir,</p>
                         <br/>
                         <p>Your request has been Confirmed and sent to Talent team. </p>
                         <br></br>
                         <p>Please Click Here """+ef+""" to view requisition.</p>
                           <body>
                            
                       <p>Regards</p>
                       
                       <p>HR</p>  
                       </body>
                       
                           
                        </html>
                      """
        #        part1 = MIMEText(text, 'plain')
                part1 = MIMEText(html, 'html')
                msg.attach(part1)
        #        msg.attach(part2)
                server = smtplib.SMTP_SSL(out_server.smtp_host,out_server.smtp_port)
        #        server.ehlo()
        #         server.starttls()
                server.login(emailfrom,out_server.smtp_pass)
                text = msg.as_string()
                server.sendmail(emailfrom, emailto , text)
                server.quit()
        return True
    
    @api.multi
    def send_email_revise_req(self):
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            rec_id = self.id
#             print"====self.env=====",self._model
            print"context====",self._context['params']['action']
#             model = self._model
            context = self._context
            context.get('active_model')
            action_id = self._context['params']['action']
            a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
            ef = """<a href="""+a+""">"""+self.name+"""</a>"""
            
            
            out_server = self.env['ir.mail_server'].search([])
            if out_server:
                out_server = out_server[0]
                
                emailfrom =out_server.smtp_user
                emailto =[]
                if self.user_id and self.user_id.login:
                    emailto.append(self.user_id.login)
                if emailfrom and emailto:
            
                    msg = MIMEMultipart()
                    msg['From'] = emailfrom
                    msg['To'] = ", ".join(emailto)
                    msg['Subject'] = 'Please Revise Requisition'
            
                    html = """<!DOCTYPE html>
                             <html>
                             
                             Your Request has been Cancelled .
        
                               <body>
                           <p>Please Click Here """+ef+""" to Revise Requisition.</p>      
                           <p>Regards</p>
                           <p>Admin</p>  
                           
                           </body>
                           
                               
                            </html>
                          """
                    #        part1 = MIMEText(text, 'plain')
                    part1 = MIMEText(html, 'html')
                    msg.attach(part1)
            #        msg.attach(part2)
                    server = smtplib.SMTP_SSL(out_server.smtp_host,out_server.smtp_port)
            #        server.ehlo()
            #         server.starttls()
                    server.login(emailfrom,out_server.smtp_pass)
                    text = msg.as_string()
                    server.sendmail(emailfrom, emailto , text)
                    server.quit()
            return True  
    
    @api.multi
    def confirm_requisition(self):
        self.write({'state':'confirm'})
        self.send_email_confirm_requisition()
    
    @api.multi
    def approve_requisition(self):
        self.send_email_to_hod()
        
        for line in self.requisition_line:
            print"jbbbbb=====",line.job_id
            line.job_id.write({'no_of_recruitment':line.emp_total,'user_id':self.allocated_to.id,  'allocat_hr':self.requested_to.id,'branch_id':self.branch_id.id})
            line.job_id.set_recruit()
        self.write({'state':'approve'})

    @api.multi
    def revise_requisition(self):
#         self.send_email_revise_req()
        self.write({'state':'draft'})            
    
class requisition_line(models.Model):
    _name="requisition.line"
    _description="Requisition Line"
    
    @api.one
    @api.depends('requisition_id.month','requisition_id.year','requisition_id.department','requisition_id.branch_id','job_id')
    def get_available_budget(self):
        for line in self:
            month = line.requisition_id.month
            year = line.requisition_id.year
            department_id = line.requisition_id.department and line.requisition_id.department.id or False
            branch_id = line.requisition_id.branch_id and line.requisition_id.branch_id.id or False
            avail_budget = 0
            if line.job_id and month and department_id and branch_id and year:
                job_id = line.job_id.id
                self.env.cr.execute("select coalesce(sum(headcount),0) from monthly_budget_line_view where \
                department_id = %s and branch_id  = %s and job_id = %s and month = %s and year = %s",(department_id,branch_id,job_id,month,year))
                temp = self.env.cr.fetchall()
                if temp:
                    avail_budget = temp[0][0]
            line.avail_budget = avail_budget
        
    name = fields.Char(string='Requisition')
    requisition_id = fields.Many2one('hr.requisition',string='requisition')
    job_id = fields.Many2one('hr.job',string="Job Position")
    job_desc = fields.Char(string='Job Description')
    emp_total = fields.Integer(string='Required Number Of Employees')
    existing = fields.Integer(string='Existing Number Of Employees', compute='onchange_emp_total')
    avail_budget = fields.Integer(compute='get_available_budget',string='Available Budget',store=True)
    salary_range = fields.Float(string="Salary Range")  
    manager_id = fields.Many2one('hr.employee',string='Manager' , domain="[('job_id','=',1)]")
    date = fields.Date('Create Date', default=fields.datetime.now())
    requested_by = fields.Many2one('hr.employee',string='Requested By')
    user_id = fields.Many2one('res.users','User')
    
    @api.onchange('job_id')
    def onchange_job_id(self):
        for line in self:
            line.existing=line.job_id.no_of_employee
    
    @api.onchange('emp_total')
    def onchange_emp_total(self):
        for line in self:
            if line.emp_total:
                if line.avail_budget < line.emp_total:
                    warning = {
                                'title': _('Warning!'),
                                'message': _('Please Re-enter Values Current Budget Exceeded Available Budget !'),
                                }
                    return {'warning': warning}

                         
class hr_job(models.Model):
    _inherit="hr.job"

    index_content = fields.Text('Indexed Content', compute='_get_index_data', readonly=True, prefetch=False,store=True)

    
    @api.one
    def _compute_application_count(self):
        read_group_result = self.env['hr.applicant'].read_group([('job_id', '=', self.id)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            job.application_count = result.get(job.id, 0)
    
    @api.one
    @api.depends('department_id','branch_id','parent_id','requisition_date')
    def get_available_budget(self):
        for line in self:
            requisition_date = line.requisition_date 
            department_id = line.department_id and line.department_id.id or False
            branch_id = line.branch_id and line.branch_id.id or False
            avail_budget = 0
            if line.parent_id and requisition_date and department_id and branch_id:
                requisition_date = datetime.strptime(requisition_date,'%Y-%m-%d')
                month = requisition_date.strftime("%m")
                year = requisition_date.strftime("%Y")
                if int(month) < 4:
                    year = int(year) - 1
                parent_id = line.parent_id.id
                self.env.cr.execute("select coalesce(max(headcount),0) from monthly_budget_line_view where \
                department_id = %s and branch_id  = %s and job_id = %s and budget_year = %s",(department_id,branch_id,parent_id,year))
                temp = self.env.cr.fetchall()
                if temp:
                    avail_budget = temp[0][0]
            line.avail_budget = avail_budget
            
    @api.one
    @api.depends('department_id','branch_id','parent_id','avail_budget','requisition_date')
    def get_requisition_pipeline(self):
        for line in self:
            requisition_pipe = 0
            requisition_date = line.requisition_date
            if line.parent_id and requisition_date and line.department_id and line.branch_id:
                requisition_date = datetime.strptime(requisition_date,'%Y-%m-%d')     
                month = requisition_date.strftime("%m")
                year = requisition_date.strftime("%Y")
                
                if int(month) < 4:
                    year = int(year) - 1
                    from_date = requisition_date.strftime("%s-04-01"%(year))
                    till_date = requisition_date.strftime("%Y-03-31")
                else:
                    year = int(year) + 1
                    from_date = requisition_date.strftime("%Y-04-01")
                    till_date = requisition_date.strftime("%s-03-31"%year)
                        
                department_id = line.department_id and line.department_id.id
                branch_id = line.branch_id and line.branch_id.id
                parent_id = line.parent_id.id
                if line.id:
                   self.env.cr.execute("select coalesce(sum(expected_no_of_emp),0) from hr_job where department_id = %s and branch_id = %s and parent_id = %s and id != %s and requisition_date >= %s and requisition_date <= %s",(department_id,branch_id,parent_id,line.id,from_date,till_date))
                else:
                   self.env.cr.execute("select coalesce(sum(expected_no_of_emp),0) from hr_job where department_id = %s and branch_id = %s and parent_id = %s and requisition_date >= %s and requisition_date <= %s",(department_id,branch_id,parent_id,from_date,till_date)) 
                    
                temp = self.env.cr.fetchall()
                if temp:
                    requisition_pipe = line.avail_budget - temp[0][0]
            line.requisition_pipe = requisition_pipe       
            
#     @api.multi
#     def get_current_headcount(self):
#         for val in self:
#             department_id = val.department_id and val.department_id.id or None
#             job_id = val.id
#             current_headcount = 0
#             if job_id and department_id:
#                self.env.cr.execute("select coalesce(count(emp.id),0) from hr_employee emp left join resource_resource AS res on emp.resource_id = res.id where emp.sub_dep = %s and emp.job_id = %s and res.active = True",(department_id,job_id))
#                current_headcount = self.env.cr.fetchone()[0]
#             val.current_headcount = current_headcount
#                    
#                
#     @api.multi
#     def get_budgeted_headcount(self):
#         for val in self:
#             department_id = val.department_id and val.department_id.id or None
#             job_id = val.id
#             budgeted_headcount = 0
#             if job_id and department_id:
#                self.env.cr.execute("select * from get_budgeted_headcount(%s,%s)",(department_id,job_id,))
#                budgeted_headcount = self.env.cr.fetchone()[0]
#             val.budgeted_headcount = budgeted_headcount
#                    
#                
#     @api.multi
#     def get_open_headcount(self):
#         for val in self:
#             val.open_headcount = val.budgeted_headcount - val.current_headcount 
#             
#     @api.multi
#     def get_recruitment_pipeline(self):
#         for val in self:
#             department_id = val.department_id and val.department_id.id or None
#             job_id = val.id
#             recruitment_pipeline = 0
#             if job_id and department_id:
#                 self.env.cr.execute("select coalesce(sum(expected_no_of_emp),0) from hr_job where parent_id = %s and department_id = %s and state = 'recruit'",(job_id,department_id))
#                 recruitment_pipeline = self.env.cr.fetchone()[0]
#             val.recruitment_pipeline = recruitment_pipeline
#             
#     @api.multi
#     def get_applicant_pipeline(self):
#         for val in self:
#             department_id = val.department_id and val.department_id.id or None
#             job_id = val.id
#             applicant_pipline = 0
#             if job_id and department_id:
#                 self.env.cr.execute("select coalesce(count(id),0) from hr_applicant where parent_job_id = %s and department_id = %s and emp_id is null",(job_id,department_id))
#                 applicant_pipline = self.env.cr.fetchone()[0]
#             val.applicant_pipline = applicant_pipline 

    def get_current_year(self):
        year = datetime.now().year
        return year       
                    
    name = fields.Char(string='HR JOB')
    budgeted_emp = fields.Integer(string='Budgeted Employees')    
    budget_lines = fields.One2many('budget.lines','job_id','Budget History')
    requisition_lines = fields.One2many('requisition.line','job_id','Requisition History')
    branch_id =fields.Many2one('hr.branch','Branch')
    allocat_hr = fields.Many2one('res.users',string='H.R.')
    parent = fields.Boolean('Parent')
    avail_budget = fields.Integer(compute='get_available_budget',string='Total Budget',store=True)
    month = fields.Selection([(4,'Apr'),(5,'May'),(6,'June'),(7,'July'),(8,'Aug'),(9,'Sept'),(10,'Oct'),(11,'Nov'),(12,'Dec'),(1,'Jan'),(2,'Feb'),(3,'Mar')],string='Month')
    year = fields.Selection([(num, str(num)) for num in range(2015, (datetime.now().year)+5 )], string='Year', default=get_current_year)
    expected_no_of_emp = fields.Integer('Expected No. Of Employee')
    parent_id = fields.Many2one('hr.job','Job Position')
    onboarding_tasks = fields.One2many('task.onboarding.job','job_id','Onboarding Task')
    requisition_type = fields.Selection([('New','New'),('Replacement','Replacement')],string="Requisition Type",default="New")
    replace_employee_id = fields.Many2one('hr.employee','Replacement')
    priority = fields.Selection([('0','0'),('1','1'),('2','2'),('3','3')],string='Priority')
    attach_doc = fields.Binary('Job Description Attachment')
    filename = fields.Char('File Name')
    requisition_pipe = fields.Integer(compute='get_requisition_pipeline',string='Available Budget',store=True)
    requisition_date = fields.Date(string='Expected Date Of Requisition',help="Expected date of requisition",default=fields.Date.context_today)
    refferal = fields.Boolean('Referral')
    
#     current_headcount = fields.Integer(string='Current Headcount',compute='get_current_headcount')
#     budgeted_headcount = fields.Integer(string='Budgeted Headcount',compute='get_budgeted_headcount',help="For Current Financial Year")
#     open_headcount = fields.Integer(string='Open Headcount',compute = 'get_open_headcount')
#     recruitment_pipeline = fields.Integer(string='Recruitment Pipeline',compute='get_recruitment_pipeline')
#     applicant_pipline = fields.Integer(string='Application Pipeline',compute='get_applicant_pipeline')    
    
    @api.multi
    def send_email_launch_requisition(self,rec):
        #trigger an email to sales person
        msg = MIMEMultipart('alternative')
        mail_subject = "Requisition Created in ERP"
        msg['From'] = "hello@nowfloats.com"
        emailto =""
        if rec.branch_id and rec.branch_id.manager_id and rec.branch_id.manager_id.work_email:
            emailto=rec.branch_id.manager_id.work_email
        msg['To'] = emailto
        email_id = emailto
        text = "plaintext"
        part1 = MIMEText(text, 'plain')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        context = self._context
        context.get('active_model')
        action_id = self._context['params']['action']
        a = """ """+str(base_url)+"""/web#id="""+str(rec.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
        ef = """<a href="""+a+"""> """+str(rec.name)+"""</a>"""
        html = """<!DOCTYPE html>
                         <html>
                         <p>Dear Sir/ Mam,</p>
                         <br/>
                         <p>A requisition has been created for your Branch. </p>
                         <br></br>
                          <p>You can access document by clicking this button     
                            <a href="""+str(a)+""" target="_parent"><button style="background-color:#00bfff"><font color="#ffffff">View Requisition</font></button></a></p>
                           <body>
                       <p>Regards</p>
                       <p>HR</p>  
                       </body>
                        </html>"""
        part2 = MIMEText(html, 'html')
        url = 'https://api.withfloats.com/Internal/v1/PushEmailToQueue/A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E'
        values= {"ClientId":"A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E", "BCC":[], "EmailBody":html,"ReplyTo":"hello@nowfloats.com", "Subject":mail_subject, "To":[email_id], "Type":0}
        req = urllib2.Request(url)
        req.add_header('Content-Type','application/json')
        data = json.dumps(values)
        response = urllib2.urlopen(req,data)
        encoder = response.read().decode('utf-8')
        if encoder:
            json_response = json.loads(encoder)

        return True

    @api.multi
    def send_email_stop_requisition(self):
        #trigger an email to sales person
        msg = MIMEMultipart('alternative')
        mail_subject = "Requisition Stopped in ERP"
        msg['From'] = "hello@nowfloats.com"
        emailto =['mohit.katiyar@nowfloats.com']
        if self.branch_id and self.branch_id.manager_id and self.branch_id.manager_id.work_email:
            emailto.append(self.branch_id.manager_id.work_email)
        msg['To'] = emailto
        email_id = emailto
        text = "plaintext"
        part1 = MIMEText(text, 'plain')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        context = self._context
        context.get('active_model')
        action_id = self._context['params']['action']
        a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """
        ef = """<a href="""+a+"""> """+self.name+"""</a>"""
        html = """<!DOCTYPE html>
                         <html>
                         <p>Dear Sir/ Mam,</p>
                         <br/>
                         <p>A requisition has been stopped for your Branch. </p>
                         <br></br>
                         <p>You can access document by clicking this button   
                          <a href="""+str(a)+""" target="_parent"><button style="background-color:#00bfff"><font color="#ffffff">View Requisition</font></button></a></p>
                           <body>
                       <p>Regards</p>
                       <p>HR</p>  
                       </body>
                        </html>"""
        part2 = MIMEText(html, 'html')
        url = 'https://api.withfloats.com/Internal/v1/PushEmailToQueue/A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E'
        values= {"ClientId":"A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E", "BCC":[], "EmailBody":html,"ReplyTo":"hello@nowfloats.com", "Subject":mail_subject, "To":email_id, "Type":0}
        req = urllib2.Request(url)
        req.add_header('Content-Type','application/json')
        data = json.dumps(values)
        response = urllib2.urlopen(req,data)
        encoder = response.read().decode('utf-8')
        json_response = json.loads(encoder)

        return True

    @api.model
    def create(self, vals):
        if 'parent' in vals and not vals['parent']:
            if 'parent_id' in vals and vals['parent_id'] and 'branch_id' in vals and vals['branch_id']:
                job = self.env['hr.job'].browse(vals['parent_id']).name
                branch = self.env['hr.branch'].browse(vals['branch_id']).name
                sequence = self.env['ir.sequence'].next_by_code('job.position.requisition')
                vals['name'] = '[' + sequence + ']' + job + ' @ ' + branch
        res = super(hr_job, self.with_context(mail_create_nolog=True)).create(vals)
        
        self.send_email_launch_requisition(res)
        if res.expected_no_of_emp > res.requisition_pipe:
            raise ValidationError("Existing Budget Consumed - Requisition In Progress. Please Contact Budget Owner Or HR Manager.")
        return res
    
    @api.multi
    def write(self, vals):
        res = super(hr_job, self).write(vals)
        if 'expected_no_of_emp' in vals and vals['expected_no_of_emp']:
           for val in self: 
               if val.expected_no_of_emp > val.requisition_pipe:
                  raise ValidationError("Existing Budget Consumed - Requisition In Progress. Please Contact Budget Owner Or HR Manager.")
        return res

    @api.multi
    def set_open(self):
        self.send_email_stop_requisition()
        super(hr_job, self).set_open()
        return True

    @api.multi
    def set_recruit(self):
        self.send_email_launch_requisition(self)
        super(hr_job, self).set_recruit()
        return True
    
    @api.onchange('parent_id')
    def onchange_parent_job_id(self):
        self.department_id = self.parent_id.department_id
        self.attach_doc = self.parent_id.attach_doc
        self.filename = self.parent_id.filename



        # ============================Docx To String=========================================

    def _index_docx(self, bin_data):
        '''Index Microsoft .docx documents'''
        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("word/document.xml"))
                for val in ["w:p", "w:h", "text:list"]:
                    for element in content.getElementsByTagName(val):
                        buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_pptx(self, bin_data):
        '''Index Microsoft .pptx documents'''

        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                zf_filelist = [x for x in zf.namelist() if x.startswith('ppt/slides/slide')]
                for i in range(1, len(zf_filelist) + 1):
                    content = xml.dom.minidom.parseString(zf.read('ppt/slides/slide%s.xml' % i))
                    for val in ["a:t"]:
                        for element in content.getElementsByTagName(val):
                            buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_xlsx(self, bin_data):
        '''Index Microsoft .xlsx documents'''

        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("xl/sharedStrings.xml"))
                for val in ["t"]:
                    for element in content.getElementsByTagName(val):
                        buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_opendoc(self, bin_data):
        '''Index OpenDocument documents (.odt, .ods...)'''

        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("content.xml"))
                for val in ["text:p", "text:h", "text:list"]:
                    for element in content.getElementsByTagName(val):
                        buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_pdf(self, bin_data):
        '''Index PDF documents'''

        buf = u""
        if bin_data.startswith('%PDF-'):
            f = StringIO(bin_data)
            try:
                pdf = pyPdf.PdfFileReader(f)
                for page in pdf.pages:
                    buf += page.extractText()
            except Exception:
                pass
        return buf



    @api.one
    @api.depends('attach_doc')
    def _get_index_data(self):
        value = self.attach_doc
        bin_data = value and value.decode('base64') or ''
        for ftype in FTYPES:
            buf = getattr(self, '_index_%s' % ftype)(bin_data)
            if buf:
                self.index_content = buf
                return True




            
class task_onboarding_job(models.Model):
    _name = "task.onboarding.job"
    
    name = fields.Char('To Do')
    expected_days = fields.Integer('Expected Time(Days)')
    job_id = fields.Many2one('hr.job','Job')    
    
class upload_docs(models.Model):
    _name="upload.docs"
    _description="Upload Documents"
    
    name = fields.Many2one('hr.employee',string="Employee")
    docs_lines = fields.One2many('docs.lines','doc_id',string='Document Details')
    intimate_to = fields.Many2one('hr.employee',string="Intimate To")
    
    @api.model
    def send_inbox_message(self, ids=None):
#         parameter_ids = self.pool.get('ir.config_parameter').search([('key','=','doc_expiry_message_to')])
#         para_rec = self.pool.get('ir.config_parameter').browse(parameter_ids[0])
        line_ids= self.env['docs.lines'].search([])
        for val in line_ids:
            send_mail = False
            today_date=time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            today_date = datetime.strptime(today_date,"%Y-%m-%d")
            expiry_date=time.strftime(val.expiry_date)
            date1 = datetime.strptime(expiry_date,"%Y-%m-%d")
            two_days_before = date1 - timedelta(days=2)
            if val.alert_date == datetime.now().strftime('%Y-%m-%d'):
                send_mail = True
            elif two_days_before == today_date:
                send_mail = True
            elif expiry_date == today_date:
                send_mail = True
            if send_mail:
                partner_id = [self.intimate_to.user_id.partner_id.id]
                values = {
                      'subject':'Document Expire Soon',
                      'author_id':partner_id[0],
                      'notified_partner_ids':[(6,0,partner_id)],
                      'body':val.code + val.doc_no + val.description,
                      }
                val.write({'alert_check':True,'msg_send':True})
                self.env['mail.message'].create(values)
                
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
#             rec_id = self.id
#             print"====self.env=====",self._model
#             print"context====",self._context
#             model = self._model
#             action_id = self._context['params']['action']
#             a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(self._model)+"""&action="""+str(action_id)+""" """
                doc = val.code+ ' ' + str(val.doc_no) + ' ' + val.description
                a = """"""+str(base_url)+"""/web?#view_type=form&model=board.board&menu_id=1&action=187"""
                ef = """<a href="""+a+""">Click Here</a>"""
            
            
                out_server = self.env['ir.mail_server'].search([])[0]
                emailto = []
                emailfrom= ''
                if out_server:
                    if out_server.smtp_user:
                        emailfrom =out_server.smtp_user
                    if val.doc_id.intimate_to.work_email:
                        emailto.append(val.doc_id.intimate_to.work_email)
                    print"======emailto===",emailfrom,emailto
                    if emailfrom and len(emailto) >= 1:
                        msg = MIMEMultipart()
                        msg['From'] = emailfrom
                        msg['To'] = ", ".join(emailto)
                        msg['Subject'] = 'Please Revise Document'
                        
                        html = """<!DOCTYPE html>
                                 <html>
                                 
                                 Documents has been expired .
                                 <br/>
                                 Please """+ef+""" to revise documents.
                                   <body>
                                     
                               <p>Regards</p>
                               <p>Admin</p>  
                               
                               </body>
                               
                                   
                                </html>
                              """
                        #        part1 = MIMEText(text, 'plain')
                        part1 = MIMEText(html, 'html')
                        msg.attach(part1)
                #        msg.attach(part2)
                        server = smtplib.SMTP_SSL(out_server.smtp_host,out_server.smtp_port)
                #        server.ehlo()
                #         server.starttls()
                        server.login(emailfrom,out_server.smtp_pass)
                        text = msg.as_string()
                        server.sendmail(emailfrom, emailto , text)
                        server.quit()
                        print"sent===="
            
                
            
            
        return True
    
    
class docs_lines(models.Model):
    _name="docs.lines"
    _description="Document Line"
    
    @api.one
    @api.depends('alert_before','expiry_date')
    def _get_alert_date(self):
        for line in self:
            if line.expiry_date:
                expiry_date=time.strftime(line.expiry_date)
                date1 = datetime.strptime(expiry_date,"%Y-%m-%d")
                alert_date = date1 - timedelta(days=line.alert_before)
                line.alert_date = alert_date
        

    @api.multi
    @api.depends('alert_before','expiry_date')
    def _get_alert_check(self):
        if self.expiry_date:
            today_date=time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            today_date = datetime.strptime(today_date,"%Y-%m-%d")
            expiry_date=time.strftime(self.expiry_date)
            date1 = datetime.strptime(expiry_date,"%Y-%m-%d")
            alert_date = date1 - timedelta(days=self.alert_before)
            print"alert_date <= today_date===",alert_date, today_date
            if alert_date <= today_date:
                    self.alert_check = True
            else:
                self.alert_check = False
        
    
    name = fields.Char(string='Name')
    doc_id = fields.Many2one('upload.docs',string="Docs Details")
    emp_name= fields.Many2one('hr.employee',string="Employee Name")
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
    doc_no = fields.Char(string='Document Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    issue_phase = fields.Char(string='Issue Phase')
    status = fields.Selection([('normal', 'Active'), ('closed', 'Archived')], string="Status")
    alert_before = fields.Integer(string='Alert Before',default=7)
    attach = fields.Binary(string='Attachments')
    alert_check = fields.Boolean('Alert Check',compute='_get_alert_check',method=True,store=True)
    alert_date = fields.Date(string='Alert Date',compute='_get_alert_date',method=True,store=True)
    msg_send=fields.Boolean('Message Send')
    
    @api.onchange('expiry_date')
    def onchange_expiry_date(self):
        res={}
        if self.expiry_date >= self.alert_date:
            self.msg_send=False
    
    
    
class resign(models.Model):
    _name="resign"
    _description="Resignation"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    

    name = fields.Many2one('hr.employee',string="Employee")
    emp_id = fields.Char('Employee ID')
    work_location = fields.Char(string='Work Location')
    designation = fields.Char(string='Designation')
    work_mobile = fields.Char(string='Work Mobile')
    reason_for_leaving = fields.Char(string='Reason For Leaving', track_visibility='onchange')
    confirm_date = fields.Date('Confirm Date')
    approve_date = fields.Date('Approve Date')
    cancel_date = fields.Date('Cancel Date')
    date_resign = fields.Date(string='Resignation Raised Date')
    branch_id = fields.Many2one('hr.branch','Branch')
    doj = fields.Date('Date of Joining')
    date_of_leaving = fields.Date('Date of Leaving',track_visibility='onchange')
    state = fields.Selection([('Draft','Draft'),('Confirm','Confirm'),('Approve','Approve'),('Cancel','Cancel')],string="State",track_visibility='onchange')
    c_man_user_id = fields.Many2one('res.users','Manager')
    c_user_id = fields.Many2one('res.users','User Id',default=lambda self: self.env.uid)
    c_rep_mngr_user = fields.Many2one('res.users','Reporting Head')
    check_access = fields.Char('Check Access', compute='_check_access')
    readonly = fields.Boolean('Readonly')
    three_months_revenue = fields.Char(string='Last 3 Months Net Revenue')
    first_month_revenue = fields.Char(string='First Month Net Revenue')
    second_month_revenue = fields.Char(string='Second Month Net Revenue')
    third_month_revenue = fields.Char(string='Third Month Net Revenue')
    
    #manager filling data
    man_last_work_date = fields.Date('Last Working Date', track_visibility='onchange')
    man_rehire_eligibility = fields.Selection([('No','No'),('Yes','Yes')],string='Rehire Eligibility',track_visibility='onchange')
    man_reason_rehire = fields.Text('Reason for rehire ',track_visibility='onchange')
    man_notice_served = fields.Selection([('No','No'),('Yes','Yes')],'Notice period served',track_visibility='onchange')
    man_process_fnf = fields.Selection([('No','No'),('Yes','Yes')],'Process F&F',track_visibility='onchange')
    man_reason_fnf = fields.Text('Reason for F&F process',track_visibility='onchange')
    notes = fields.Text(string='Reporting Head/ Manager Comment:', track_visibility='onchange')
    man_np_waived = fields.Selection([('No', 'No'), ('Yes', 'Yes')], string='Notice Period Waived Off',track_visibility='onchange')

    #hr filing data
    hr_last_work_date = fields.Date('Last Working Date', track_visibility='onchange')
    hr_rehire_eligibility = fields.Selection([('no', 'No'), ('yes', 'Yes')], string='Rehire Eligibility',track_visibility='onchange')
    hr_reason_rehire = fields.Text('Reason for rehire ',track_visibility='onchange')
    hr_notice_served = fields.Selection([('No', 'No'), ('Yes', 'Yes')], 'Notice Period Served',track_visibility='onchange')
    c_hr_comments = fields.Text(string='HR Comments:', track_visibility='onchange')
    hr_np_waived = fields.Selection([('No', 'No'), ('Yes', 'Yes')], string='Notice Period Waived Off',track_visibility='onchange')
    mail_approve = fields.Boolean('Mail Approve',track_visibility='onchange')

    #nodues filling fields
    laptop_submit = fields.Boolean('Laptop/desktop Submitted',track_visibility='onchange')
    laptop_login = fields.Boolean('Laptop/desktop Login id & Password Collected',track_visibility='onchange')
    software_check = fields.Boolean('Software check',track_visibility='onchange')
    uber_ola_deactivate = fields.Boolean('Uber/Ola Deactivation or Any Recovery',track_visibility='onchange')
    income_tax = fields.Boolean('Income Tax Adjustment',track_visibility='onchange')
    advances = fields.Boolean('Advances',track_visibility='onchange')
    happay_card_deactivate = fields.Boolean('Happay Card Deactivated',track_visibility='onchange')
    cheque_bounce = fields.Boolean('Cheque Bounces',track_visibility='onchange')
    incentives = fields.Boolean('Incentive Cases',track_visibility='onchange')
    previous_cases = fields.Boolean('Previous Cases Audit',track_visibility='onchange')
    knowledge_transfer = fields.Boolean('Knowledge Transfer',track_visibility='onchange')
    data_collection = fields.Boolean('Data Collection',track_visibility='onchange')
    id_card = fields.Boolean('Id Card Submitted',track_visibility='onchange')
    visiting_card = fields.Boolean('Visiting Card Submitted',track_visibility='onchange')
    c_email_deactive = fields.Boolean('Email Deactivated',track_visibility='onchange')
    c_app_deactive = fields.Boolean('App Permission Deactivated',track_visibility='onchange')
    nodues_status = fields.Selection([('Pending','Pending'),('Done','Done')],string='NoDues Status',track_visibility='onchange',default='Pending')
    nodues_date = fields.Date('NoDues Date')
    nodues_by = fields.Many2one('res.users','NoDues By')

    #exit formalities
    hr_process_fnf = fields.Selection([('No', 'No'),('Yes', 'Yes'),('Pending', 'Pending')], 'Process F&F',track_visibility='onchange')
    hr_reason_fnf = fields.Text('Reason for F&F process',track_visibility='onchange')
    fnf_date = fields.Date('F&F Processed Date',track_visibility='onchange')
    relieving_letter = fields.Selection([('No', 'No'),('Yes', 'Yes'),('Pending', 'Pending')], 'Relieving Letter Issued',track_visibility='onchange')
    rl_date = fields.Date('Relieving Letter Issued Date',track_visibility='onchange')
    rl_comment = fields.Text('Comment',track_visibility='onchange')
    email_link = fields.Char('Email Link',track_visibility='onchange')
    exit_status = fields.Selection([('Pending','Pending'),('Done','Done')],string='Exit Status',track_visibility='onchange',default='Pending')
    exit_done_date = fields.Date('Exit Formalities Date')
    exit_done_by = fields.Many2one('res.users','Exit Formalities By')
    c_emp_replacer = fields.Many2one('hr.employee',string='Active Employee Replacer',track_visibility='onchange')

    @api.model
    def default_get(self,fields):
        res=super(resign,self).default_get(fields)
        hr_obj=self.env['hr.employee']
        date_resign=datetime.now().strftime('%Y-%m-%d')
        hr_id=hr_obj.search([('user_id','=',self.env.uid)])
        res.update({'name':hr_id.id,'date_resign':date_resign})

        return res

    @api.onchange('name')
    def onchange_employee(self):
        cr=self.env.cr
        emp=self.name
        if emp:
            self.emp_id=emp.nf_emp
            self.work_location=emp.work_location
            self.work_mobile=emp.mobile_phone
            self.designation=emp.intrnal_desig
            self.branch_id=emp.branch_id and emp.branch_id.id or False
            self.doj=emp.join_date
            self.c_man_user_id=emp.parent_id and emp.parent_id.user_id and emp.parent_id.user_id.id or False
            self.c_rep_mngr_user=emp.coach_id and emp.coach_id.user_id and emp.coach_id.user_id.id or False
            self.c_user_id=emp.user_id.id
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
            self.first_month_revenue=first_revenue
            self.second_month_revenue=second_revenue
            self.third_month_revenue=last_revenue
            #self.three_months_revenue=last_revenue

    @api.model
    def create(self, vals):
        cr=self.env.cr
        resign_id = self.search([('name', '=', vals['name']),('state', 'in', ['Draft', 'Confirm', 'Approve'])])
        if resign_id:
            raise exceptions.ValidationError(_('Resignation Request for this employee is already created.'))
        emp=self.env['hr.employee'].sudo().browse(vals.get('name'))
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
            vals.update({'state':'Draft','emp_id':emp.nf_emp,'work_location':emp.work_location,'work_mobile':emp.mobile_phone,'designation':emp.intrnal_desig,'branch_id':emp.branch_id and emp.branch_id.id or False,'doj':emp.join_date,'c_man_user_id':emp.parent_id and emp.parent_id.user_id and emp.parent_id.user_id.id or False,'c_rep_mngr_user':emp.coach_id and emp.coach_id.user_id and emp.coach_id.user_id.id or False,'c_user_id':emp.user_id and emp.user_id.id or False,'first_month_revenue':first_revenue,'second_month_revenue':second_revenue,'third_month_revenue':last_revenue})
        rec = super(resign, self).create(vals)
        rec.name.sudo().write({'exit_mode': True,'exit_mode_status':'Yet to Connect','exit_mode_date':datetime.now().strftime("%Y-%m-%d")})
        self.resign_email_notification(rec,'new')
        return rec


    @api.model
    def resign_email_notification(self,rec, status='new'):
        company = self.env['res.company'].sudo().browse(1)
        obj = self.browse(rec)
        mail_subject = "Resignation by "+ str(rec.name.name)
        heading = "Resignation Notification"

        email_id = []
        cc_id = []
        desc = ''
        confirm_desc = ''
        mngr_email = []
        date_leaving = ''
        doj = (datetime.strptime(str(rec.doj), '%Y-%m-%d')).strftime('%d/%b/%Y')
        date_resign = (datetime.strptime(str(rec.date_resign), '%Y-%m-%d')).strftime('%d/%b/%Y')
        if  rec.name:
            mngr_email.append(rec.name.work_email)
            if rec.name.parent_id:
                mngr_email.append(rec.name.parent_id.work_email)
            if rec.name.coach_id:
                mngr_email.append(rec.name.coach_id.work_email)
            if rec.name.c_recruiter_name:
                mngr_email.append(rec.name.c_recruiter_name.work_email)
            if rec.name.sub_dep and rec.name.sub_dep.name in ['FOS', 'FOS-CF']:
                mngr_email.append('kusum.panchal@nowfloats.com')
            if rec.name.sub_dep and rec.name.sub_dep.name in ['FOS', 'FOS-HQ']:
                mngr_email.append('satesh.kohli@nowfloats.com')
            elif rec.name.sub_dep and rec.name.sub_dep.name in ['FOS-CF', 'Renewals - FOS']:
                mngr_email.append('rajeev.goyal@nowfloats.com')
                mngr_email.append('rajat.anand@nowfloats.com')
            elif rec.name.sub_dep and rec.name.sub_dep.name in ['Channel', 'Channel-HQ']:
                mngr_email.append('dilep.singh@nowfloats.com')
        if status == 'new':
            date_leaving = (datetime.strptime(rec.date_of_leaving, '%Y-%m-%d')).strftime('%d/%b/%Y')
            desc = "This is to inform you that below mentioned person has resigned today."
            confirm_desc = "To confirm your reportee resignation and to complete exit formalities you are requested to login in ERP and follow the process."
        elif status == 'Confirm':
            if rec.man_last_work_date:
                date_leaving = (datetime.strptime(rec.man_last_work_date, '%Y-%m-%d')).strftime('%d/%b/%Y')
            else:
                date_leaving = (datetime.strptime(rec.date_of_leaving, '%Y-%m-%d')).strftime('%d/%b/%Y')
            desc = "This is to inform you that below mentioned person has resigned on " + str(
                date_resign) + ". It is approved by his/her Manager."
            confirm_desc = "@HR Team - Please complete the Exit fromalities as per the process."
        elif status == 'Approve':
            mngr_email=mngr_email + ['bizsupport@nowfloats.com','financefyi@nowfloats.com','mis@nowfloats.com','misdesk@nowfloats.com','ops@nowfloats.com','shiksha@nowfloats.com']
            date_leaving = (datetime.strptime(rec.hr_last_work_date, '%Y-%m-%d')).strftime('%d/%b/%Y')
            desc = "This is to inform you that below mentioned person has resigned on " + str(
                date_resign) + ". It is approved by HR."
        elif status == 'Cancel':
            desc = "This is to inform you that below mentioned person has resigned on " + str(
                date_resign) + ". It has been cancelled. Please have a look in ERP or contact HR."
        elif status == 'Reset':
            date_leaving = (datetime.strptime(rec.date_of_leaving, '%Y-%m-%d')).strftime('%d/%b/%Y')
            desc = "This is to inform you that below mentioned person has resigned on " + str(
                date_resign) + ". It has been reopen."

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        context = self._context
        context.get('active_model')
        action_id = self._context['params']['action']
        resign_url = """ """+str(base_url)+"""/web#id="""+str(rec.id)+"""&view_type=form&model="""+str(context.get('active_model'))+"""&action="""+str(action_id)+""" """

        html = """<!DOCTYPE html>
                             <html>
                               <body>
                                 <table style="width:50%">
                                      <tr>
                                         <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></center></td>
                                      </tr>
                                 </table>
                                      <br/>
                                <table style="width:100%">
                                      <tr style="width:100%">
                                      <td colspan="2"><span>""" + str(desc) + """</span></td>
                                      </tr>
                                 </table>
                                 <p><span>""" + str(confirm_desc) + """</span>
                                 <p>Please login in erp and click   
                                    <a href="""+str(resign_url)+""" target="_parent">here</a></p>
                                 <table style="width:100%">
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Name</b></td>
                                        <td style="width:75%">: <span>""" + str(rec.name.name or '') + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Emp ID</b></td>
                                        <td style="width:75%">: <span>""" + str(rec.emp_id or '') + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Manager</b></td>
                                        <td style="width:75%">: <span>""" + str(
            rec.name.parent_id and rec.name.parent_id.name or '') + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Branch</b></td>
                                        <td style="width:75%">: <span>""" + str(
            rec.branch_id and rec.branch_id.name or '') + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Designation</b></td>
                                        <td style="width:75%">: <span>""" + str(rec.designation or '') + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Work Phone</b></td>
                                        <td style="width:75%">: <span>""" + str(rec.work_mobile or '') + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Date of Joining</b></td>
                                        <td style="width:75%">: <span>""" + str(doj) + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Date of Leaving</b></td>
                                         <td style="width:75%">: <span>""" + str(date_leaving) + """</span></td>
                                      </tr>
                                      <tr style="width:100%">
                                         <td style="width:25%"><b>Reason for Leaving</b></td>
                                         <td style="width:75%">: <span>""" + str(rec.reason_for_leaving or '') + """</span></td>
                                      </tr>

                      <tr style="width:100%">
                                         <td style="width:25%"></td>
                                         <td style="width:75%"></td>
                                      </tr>
                                </table>
                                <br/>
                                <br/>   

                           <p>---------------------------------------------------------------------------------------------------------------------------------</p>
                            </body>
                           <p>If you have any question, do not hesitate to contact us.</p>
                           <p>Thank you for choosing """ + str(company.name or 'us') + """</p>
                      <br/>
                   <div style="width: 375px; margin: 0px; padding: 0px; background-color: #00bfff; border-top-left-radius: 5px 5px; border-top-right-radius: 5px 5px; background-repeat: repeat no-repeat;">
                        <h3 style="margin: 0px; padding: 2px 14px; font-size: 12px; color: #DDD;">
                            <strong style="text-transform:uppercase;">""" + str(company.name) + """</strong></h3>
                    </div>
                    <div style="width: 347px; margin: 0px; padding: 5px 14px; line-height: 16px; background-color: #F2F2F2;">
                        <span style="color: #222; margin-bottom: 5px; display: block;">
                   """ + str(company.street) + """<br/>
                   """ + str(company.street2) + """<br/>
                   """ + str(company.zip) + """ """ + str(company.city) + """<br/>
                   """ + str(company.state_id and company.state_id.name or '') + """  """ + str(
            company.country_id and company.country_id.name or '') + """ <br/>
            </span>
                            <div style="margin-top: 0px; margin-right: 0px; margin-bottom: 0px; margin-left: 0px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; ">
                                Web:&nbsp; """ + str(company.website or '') + """
                            </div>

                        <p></p>
                    </div>
            <html>"""
        email_id = ["separation@nowfloats.com"] + mngr_email
        # email trigger
        msg = MIMEMultipart()
        emailto = email_id
        emailcc = cc_id
        emailfrom = "erpnotification@nowfloats.com"
        msg['From'] = emailfrom
        msg['To'] = ", ".join(emailto)
        msg['CC'] = ", ".join(emailcc)
        msg['Subject'] = mail_subject

        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        self.env.cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
        mail_server = self.env.cr.fetchone()
        smtp_user = mail_server[0]
        smtp_pass = mail_server[1]
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_pass)
        text = msg.as_string()
        try:
            server.sendmail(emailfrom, emailto, text)
        except:
            pass
        server.quit()
        return True

    @api.one
    @api.depends('name')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        if self.name:
            group_obj = self.env["res.groups"]
            group_id = group_obj.sudo().search([('name', '=', 'Manager'), ('category_id.name', '=', 'Employees')])
            group_pet_id = group_obj.sudo().search([('name','=','People Engagement Team')])
            if self.name.parent_id:
                if user == self.name.parent_id.user_id.id:
                    emp = 'Man'
            if self.name.coach_id:
                if user == self.name.coach_id.user_id.id:
                    emp = 'Man'
            if user == self.name.user_id.id:
                emp = 'Emp'
            elif group_pet_id:
                for k in group_pet_id:
                    for j in k.users:
                        if user == j.id:
                            if emp == 'Man':
                                emp = 'ManPET'
                            else:
                                emp = 'PET'
            if group_id:
                for k in group_id:
                    for j in k.users:
                        if user == j.id:
                            if emp == 'Man':
                                emp = 'ManHR'
                            else:
                                emp = 'HR'
        self.check_access = emp

    @api.multi
    def approve(self):
        approve_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            if not rec.c_hr_comments or not rec.hr_last_work_date or not rec.hr_notice_served or not rec.hr_rehire_eligibility:
                raise exceptions.ValidationError(_('Please Provide HR Feedback Details before approving it.'))
            if rec.hr_last_work_date:
                self.env.cr.execute("UPDATE hr_employee set last_working_date = %s, date_resign=%s, resignation_id=%s where id=%s",(rec.hr_last_work_date, rec.date_resign, rec.id, rec.name.id,))
            self.write({'state':'Approve','approve_date':approve_date})
            if rec.mail_approve:
                temp_id = self.env['mail.template'].search([('name','=','Resignation Approval Mail')])
                if temp_id:
                    temp_id.send_mail(rec.id)
            else:
                self.resign_email_notification(rec,'Approve')
    
        return True


    @api.multi
    def confirm(self):
        uid = self.env.uid
        confirm_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            hr = self.env['hr.employee']
            man_user = rec.name.parent_id and rec.name.parent_id and rec.name.parent_id.user_id and rec.name.parent_id.user_id.id or False
            reporting_user =rec.name.coach_id and rec.name.coach_id and rec.name.coach_id.user_id and rec.name.coach_id.user_id.id or False
            man_user_ids = [man_user,reporting_user]
            if not self.env.user.has_group('hr.group_hr_manager'):
                if uid not in man_user_ids:
                    raise exceptions.ValidationError(_('Sorry, you can not confirm this. Only your Manager or Reporting Head can confirm this.'))
                if not rec.notes or not rec.man_last_work_date or not rec.man_notice_served or not rec.man_process_fnf or not rec.man_rehire_eligibility:
                    raise exceptions.ValidationError(_('Please provide Manager Feedback Details before confirming it.'))
            self.write({'state': 'Confirm','confirm_date':confirm_date})
            self.resign_email_notification(rec,'Confirm')
        return True

            
    @api.multi
    def cancel(self):
        cancel_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            if self.env.user.has_group('hr.group_hr_manager'):
                if not rec.c_hr_comments:
                    raise exceptions.ValidationError(_('Please add comments before cancelling it.'))
            else:
                if not rec.notes:
                    raise exceptions.ValidationError(_('Please add comments before cancelling it.'))
            self.write({'state':'Cancel','cancel_date':cancel_date})
            self.resign_email_notification(rec,'Cancel')
        return True

    @api.multi
    def confirm_nodues(self):
        nodues_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            self.write({'nodues_status':'Done','nodues_date':nodues_date,'nodues_by':self.env.uid})
        return True

    @api.multi
    def confirm_exit(self):
        exit_done_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            self.write({'exit_status':'Done','exit_done_date':exit_done_date,'exit_done_by':self.env.uid})
            rec.name.write({'hr_process_fnf':rec.hr_process_fnf,'hr_reason_fnf':rec.hr_reason_fnf,'fnf_date':rec.fnf_date,'relieving_letter':rec.relieving_letter,'rl_date':rec.rl_date,'rl_comment':rec.rl_comment,'email_link':rec.email_link,'exit_done_date':rec.exit_done_date,'exit_done_by':rec.exit_done_by.id or False,'c_emp_replacer':rec.c_emp_replacer.id or False,'empl_status':'Resigned','reason_for_leaving':rec.reason_for_leaving,'rehiring_status':rec.hr_rehire_eligibility,'rehiring_comment':rec.hr_reason_rehire,'hr_notice_served':rec.hr_notice_served,'hr_np_waived':rec.hr_np_waived,'c_replacer_state':rec.c_emp_replacer.state_id and rec.c_emp_replacer.state_id.id or False,'c_replacer_city':rec.c_emp_replacer.q_city_id and rec.c_emp_replacer.q_city_id.id or False,'c_replacer_branch':rec.c_emp_replacer.branch_id and rec.c_emp_replacer.branch_id.id or False,'rt_comment':rec.c_hr_comments})
        return True

    @api.multi
    def reset_to_draft(self):
        for rec in self:
            self.write({'state':'Draft'})
            self.resign_email_notification(rec,'Reset')
        return True

class termination_reason(models.Model):
    _name = 'termination.reason'
    
    name = fields.Char('Name')

class termination(models.Model):
    _name="termination"
    _description="Absconding"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
        
    name = fields.Many2one('hr.employee',string="Employee")
    emp_id = fields.Char('Employee ID')
    work_location = fields.Char(string='Work Location')
    designation = fields.Char(string='Designation')
    work_mobile = fields.Char(string='Work Mobile')
    reason_id = fields.Many2one('termination.reason',string='Reason for Absconding',track_visibility='onchange')
    confirm_date = fields.Date('Confirm Date')
    approve_date = fields.Date('Approve Date')
    cancel_date = fields.Date('Cancel Date')
    terminate_date = fields.Date(string='Create Date')
    branch_id = fields.Many2one('hr.branch','Branch')
    doj = fields.Date('Date of Joining')
    date_of_leaving = fields.Date('Date of Termination',track_visibility='onchange')
    state = fields.Selection([('Draft','Draft'),('Confirm','Confirm'),('Approve','Approve'),('Cancel','Cancel')],string="State",track_visibility='onchange')
    c_man_user_id = fields.Many2one('res.users','Manager User Id')
    c_user_id = fields.Many2one('res.users','User Id',default=lambda self: self.env.uid)
    c_rep_mngr_user = fields.Many2one('res.users','Reporting Head User')
    check_access = fields.Char('Check Access', compute='_check_access')
    readonly = fields.Boolean('Readonly')
    absconding_date = fields.Date(string='Date of Absconding')
    three_months_revenue = fields.Char(string='Last 3 Months Net Revenue')
    first_month_revenue = fields.Char(string='First Month Net Revenue')
    second_month_revenue = fields.Char(string='Second Month Net Revenue')
    third_month_revenue = fields.Char(string='Third Month Net Revenue')
    
    #manager filling data
    notes = fields.Text(string='Reporting Head/ Manager Comment:', track_visibility='onchange')

    #hr filing data
    c_hr_comments = fields.Text(string='HR Comments:', track_visibility='onchange')

    #nodues filling fields
    laptop_submit = fields.Boolean('Laptop/desktop Submitted',track_visibility='onchange')
    laptop_login = fields.Boolean('Laptop/desktop Login id & Password Collected',track_visibility='onchange')
    software_check = fields.Boolean('Software check',track_visibility='onchange')
    uber_ola_deactivate = fields.Boolean('Uber/Ola Deactivation or Any Recovery',track_visibility='onchange')
    income_tax = fields.Boolean('Income Tax Adjustment',track_visibility='onchange')
    advances = fields.Boolean('Advances',track_visibility='onchange')
    happay_card_deactivate = fields.Boolean('Happay Card Deactivated',track_visibility='onchange')
    cheque_bounce = fields.Boolean('Cheque Bounces',track_visibility='onchange')
    incentives = fields.Boolean('Incentive Cases',track_visibility='onchange')
    previous_cases = fields.Boolean('Previous Cases Audit',track_visibility='onchange')
    knowledge_transfer = fields.Boolean('Knowledge Transfer',track_visibility='onchange')
    data_collection = fields.Boolean('Data Collection',track_visibility='onchange')
    id_card = fields.Boolean('Id Card Submitted',track_visibility='onchange')
    visiting_card = fields.Boolean('Visiting Card Submitted',track_visibility='onchange')
    c_email_deactive = fields.Boolean('Email Deactivated',track_visibility='onchange')
    c_app_deactive = fields.Boolean('App Permission Deactivated',track_visibility='onchange')
    nodues_status = fields.Selection([('Pending','Pending'),('Done','Done')],string='NoDues Status',track_visibility='onchange',default='Pending')
    nodues_date = fields.Date('NoDues Date')
    nodues_by = fields.Many2one('res.users','NoDues By')

    #exit filling fields
    exit_status = fields.Selection([('Pending','Pending'),('Done','Done')],string='Exit Status',track_visibility='onchange',default='Pending')
    exit_done_date = fields.Date('Exit Formalities Date')
    exit_done_by = fields.Many2one('res.users','Exit Formalities By')
    c_emp_replacer = fields.Many2one('hr.employee',string='Active Employee Replacer',track_visibility='onchange')
    email_link = fields.Char('Email Link',track_visibility='onchange')

    @api.onchange('name')
    def onchange_employee(self):
        cr=self.env.cr
        emp=self.name
        if emp:
            self.emp_id=emp.nf_emp
            self.work_location=emp.work_location
            self.work_mobile=emp.mobile_phone
            self.designation=emp.intrnal_desig
            self.branch_id=emp.branch_id and emp.branch_id.id or False
            self.doj=emp.join_date
            self.c_man_user_id=emp.parent_id and emp.parent_id.user_id and emp.parent_id.user_id.id or False
            self.c_rep_mngr_user=emp.coach_id and emp.coach_id.user_id and emp.coach_id.user_id.id or False
            self.c_user_id=emp.user_id.id
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
            self.first_month_revenue=first_revenue
            self.second_month_revenue=second_revenue
            self.third_month_revenue=last_revenue

    @api.model
    def create(self, vals):
        cr=self.env.cr
        terminate_date=datetime.now().strftime('%Y-%m-%d')
        date_of_leaving=(datetime.now()+relativedelta(days=2))
        resign_id = self.search([('name', '=', vals['name']),('state', 'in', ['Draft', 'Confirm', 'Approve'])])
        if resign_id:
            raise exceptions.ValidationError(_('Termination Request for this employee is already created.'))
        emp=self.env['hr.employee'].sudo().browse(vals.get('name'))
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
            man_user=emp.parent_id and emp.parent_id.user_id and emp.parent_id.user_id.id or False
            reporting_user=emp.coach_id and emp.coach_id.user_id and emp.coach_id.user_id.id or False
            # if not self.env.user.has_group('hr.group_hr_manager') or self.env.uid not in [man_user,reporting_user]:
            #     raise exceptions.ValidationError(_('Termination Request for this employee can be created only by his/her Reporting Manager, Manager and HR Manager.'))
            vals.update({'state':'Draft','emp_id':emp.nf_emp,'work_location':emp.work_location,'work_mobile':emp.mobile_phone,'designation':emp.intrnal_desig,'branch_id':emp.branch_id and emp.branch_id.id or False,'doj':emp.join_date,'c_man_user_id':man_user,'c_rep_mngr_user':reporting_user,'c_user_id':emp.user_id and emp.user_id.id or False,'terminate_date':terminate_date,'date_of_leaving':date_of_leaving,'first_month_revenue':first_revenue,'second_month_revenue':second_revenue,'third_month_revenue':last_revenue})
        rec = super(termination, self).create(vals)
        rec.name.sudo().write({'exit_mode': True,'exit_mode_status':'Yet to Connect','exit_mode_date':datetime.now().strftime("%Y-%m-%d")})
        temp_id = self.env['mail.template'].search([('name','=','Absconding Request Notification')])
        if temp_id:
            temp_id.send_mail(rec.id)
        return rec

    @api.one
    @api.depends('name')
    def _check_access(self):
        user = self.env.uid
        emp = ''
        if self.name:
            group_obj = self.env["res.groups"]
            group_id = group_obj.sudo().search([('name', '=', 'Manager'), ('category_id.name', '=', 'Employees')])
            group_pet_id = group_obj.sudo().search([('name','=','People Engagement Team')])
            if self.name.parent_id:
                if user == self.name.parent_id.user_id.id:
                    emp = 'Man'
            if self.name.coach_id:
                if user == self.name.coach_id.user_id.id:
                    emp = 'Man'
            if user == self.name.user_id.id:
                emp = 'Emp'
            elif group_pet_id:
                for k in group_pet_id:
                    for j in k.users:
                        if user == j.id:
                            if emp == 'Man':
                                emp = 'ManPET'
                            else:
                                emp = 'PET'
            if group_id:
                for k in group_id:
                    for j in k.users:
                        if user == j.id:
                            if emp == 'Man':
                                emp = 'ManHR'
                            else:
                                emp = 'HR'
        self.check_access = emp

    @api.multi
    def approve(self):
        approve_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            if not rec.c_hr_comments:
                raise exceptions.ValidationError(_('Please Provide HR Comment before approving it.'))
            if rec.date_of_leaving:
                self.env.cr.execute("UPDATE hr_employee set last_working_date = %s,termination_id=%s where id=%s",(rec.date_of_leaving,rec.id,rec.name.id,))
            self.write({'state':'Approve','approve_date':approve_date})
            temp_id = self.env['mail.template'].search([('name','=','Absconding Approved')])
            if temp_id:
                temp_id.send_mail(rec.id)
    
        return True

    @api.multi
    def confirm(self):
        uid = self.env.uid
        confirm_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            hr = self.env['hr.employee']
            man_user = rec.name.parent_id and rec.name.parent_id and rec.name.parent_id.user_id and rec.name.parent_id.user_id.id or False
            #reporting_user =rec.name.coach_id and rec.name.coach_id and rec.name.coach_id.user_id and rec.name.coach_id.user_id.id or False
            man_user_ids = [man_user]
            if not self.env.user.has_group('hr.group_hr_manager'):
                if uid not in man_user_ids:
                    raise exceptions.ValidationError(_('Sorry, you can not confirm this. Only your Manager can confirm this.'))
                if not rec.notes:
                    raise exceptions.ValidationError(_('Please provide Manager Comment before confirming it.'))
            self.write({'state': 'Confirm','confirm_date':confirm_date})
            temp_id = self.env['mail.template'].search([('name','=','Absconding Confirm')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True
            
    @api.multi
    def cancel(self):
        cancel_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            if self.env.user.has_group('hr.group_hr_manager'):
                if not rec.c_hr_comments:
                    raise exceptions.ValidationError(_('Please add comments before cancelling it.'))
            else:
                if not rec.notes:
                    raise exceptions.ValidationError(_('Please add comments before cancelling it.'))
            if rec.state=='Approve':
                self.env.cr.execute("UPDATE hr_employee set exit_done_date=NULL,exit_done_by=NULL,c_emp_replacer=NULL,empl_status=NULL,c_replacer_state=NULL,c_replacer_city=NULL,c_replacer_branch=NULL,rt_comment=NULL,email_link=NULL,last_working_date = NULL,termination_id=NULL where id=%s",(rec.name.id,))
            self.write({'state':'Cancel','cancel_date':cancel_date})
            temp_id = self.env['mail.template'].search([('name','=','Absconding Cancel')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True

    @api.multi
    def confirm_nodues(self):
        nodues_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            self.write({'nodues_status':'Done','nodues_date':nodues_date,'nodues_by':self.env.uid})
        return True

    @api.multi
    def confirm_exit(self):
        exit_done_date=datetime.now().strftime('%Y-%m-%d')
        for rec in self:
            self.write({'exit_status':'Done','exit_done_date':exit_done_date,'exit_done_by':self.env.uid})
            rec.name.write({'exit_done_date':rec.exit_done_date,'exit_done_by':rec.exit_done_by.id or False,'c_emp_replacer':rec.c_emp_replacer.id or False,'empl_status':'Absconded','c_replacer_state':rec.c_emp_replacer.state_id and rec.c_emp_replacer.state_id.id or False,'c_replacer_city':rec.c_emp_replacer.q_city_id and rec.c_emp_replacer.q_city_id.id or False,'c_replacer_branch':rec.c_emp_replacer.branch_id and rec.c_emp_replacer.branch_id.id or False,'rt_comment':rec.c_hr_comments,'email_link':rec.email_link})
        return True

    @api.multi
    def reset_to_draft(self):
        for rec in self:
            self.write({'state':'Draft'})
            temp_id = self.env['mail.template'].search([('name','=','Absconding Request Notification')])
            if temp_id:
                temp_id.send_mail(rec.id)
        return True


class travel_details(models.Model):
    _name="travel.details"
    _description="Travel Details"
    
    def default_login_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit = 1)
    
    name = fields.Char(string='Refrence Number')
    emp_name= fields.Many2one('hr.employee',string="Employee",default=default_login_employee)
    designation = fields.Many2one('hr.job',string='Designation')   
    emp_id = fields.Char(string='ID')
    dob = fields.Date(string='Date Of Birth')
    contact_no = fields.Char(string='Contact Number')
    off_email = fields.Char(string='Office Email Id')
    
    travel_req_date = fields.Date(string='Travel Request Date')
    id_proof = fields.Char(string='Type Of Id Proof')
    travel_from = fields.Char(string='Travelling From')
    travel_to = fields.Char(string='Travelling To')
    return_to = fields.Date(string='Returning To')
    mode = fields.Selection([('public_transport', 'Public Transport'), ('own_vehicle', 'Own Vehicle'),('flight','By Flight')], string="Mode Of Travel")
    preffered_time = fields.Float(string='Preffered Time-If Any')
    preffered_return_time = fields.Float(string='Preffered Return Time - If Any')
    
    date_travel = fields.Date(string='Date Of Travel')
    reason_for_travel = fields.Char(string='Reason For Travel')
    return_date_travel = fields.Date(string='Return Date Of Travel')
    
    nf_dept = fields.Char('NF Department')
    nf_state = fields.Char(string='NF State')
    financial_approval = fields.Char(string='Financial Approval')
    
    accommodation_req = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Accommodation Required")
    
    
    @api.onchange('emp_name')
    def onchange_employee(self):
        for record in self:
            if record.emp_name:
                emp = record.emp_name
                record.designation = emp.intrnl_desig and emp.intrnl_desig.id or False
                record.emp_id = emp.employee_no
                record.dob = emp.birthday
                record.contact_no = emp.mobile_phone
                record.off_email = emp.work_email
                
            else:
                record.designation = False
                record.emp_id = ''
                record.dob = False
                record.contact_no = ''
                record.off_email = ''
                    
class medical_insurance(models.Model):
    _name="medical.insurance"
    _description = "Medical Insurance"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    def default_login_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit = 1)
    
    employee_id = fields.Many2one('hr.employee',string="Employee",default=default_login_employee,track_visibility="onchange")
    insurance_date = fields.Date('Insurance Date')
    emp_id = fields.Char('Employee ID')
    doj = fields.Date('Date of Joining')
    dob = fields.Date('Date of Birth')
    work_location = fields.Char('Work Location')
    work_mobile = fields.Char('Mobile No')
    gender = fields.Selection([('male', 'Male'),('female', 'Female'),('other', 'Other')],'Gender')
    name = fields.Char(string='Reference Number')
    marital = fields.Selection([('single', 'Single'),('married', 'Married'),('widower', 'Widower'),('divorced', 'Divorced')], string='Marital Status')
    plan = fields.Char('Plan',default='E+S+2C')
    sum_assured = fields.Char('Sum Insured',default='3 Lakhs')
    opt_out = fields.Boolean('Opt Out')
    attachment = fields.Binary('Attachment')
    filename = fields.Char('Filename')
    state = fields.Selection([('Draft','Draft'),('Closed','Closed')],string='Status',default='Draft')
    family_detail_lines = fields.One2many('family.lines','family_id',string='Family Floater')

    @api.onchange('employee_id')
    def onchange_employee(self):
        emp = self.employee_id
        if emp:
            user = self.env.user
            user_id = emp.user_id and emp.user_id.id or False
            if user.id != user_id:
                if not user.has_group('hr.group_hr_manager'):
                    raise exceptions.ValidationError(_("Sorry! You can not create other employee's Medical Insurance request."))
            self.emp_id = self.employee_id.nf_emp
            self.doj = self.employee_id.join_date
            self.dob = self.employee_id.birthday
            self.work_location = self.employee_id.work_location
            self.work_mobile = self.employee_id.mobile_phone
            self.gender = self.employee_id.gender
            self.marital = self.employee_id.marital

    @api.model
    def create(self, vals):
        ins_id = self.search([('employee_id', '=', vals['employee_id'])])
        if ins_id:
            raise exceptions.ValidationError(_('Medical Insurance for this employee is already created.'))
        if vals['opt_out'] != True:
            if not vals['family_detail_lines']:
                raise exceptions.ValidationError(_('Family Floater details cannot be empty'))
            elif len(vals['family_detail_lines']) == 0:
                raise exceptions.ValidationError(_('Pelase fill the family floater details properly'))
            no_of_children = 0
            for family_details in vals['family_detail_lines']:
                relation = family_details[2]['relation']
                if relation in ('Son','Daughter'):
                    no_of_children = no_of_children + 1
            if no_of_children >2:
                raise exceptions.ValidationError(_('Cannot add more than two children'))

        emp=self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
        if emp:
            emp=emp[0]
            user = self.env.user
            user_id = emp.user_id and emp.user_id.id or False
            if user.id != user_id:
                if not user.has_group('hr.group_hr_manager'):
                    raise exceptions.ValidationError(_("Sorry! You can not create other employee's Medical Insurance request."))
            name = self.env['ir.sequence'].next_by_code('medical.insurance') or '-'
            vals.update({'emp_id':emp.nf_emp,'work_location':emp.work_location,'work_mobile':emp.mobile_phone,'doj':emp.join_date,'dob':emp.birthday,'gender':emp.gender,'name':name,'marital':emp.marital})
        rec = super(medical_insurance, self).create(vals)
        return rec

    
class family_lines(models.Model):
    _name="family.lines"
    
    name=fields.Char('Name')
    family_id = fields.Many2one('medical.insurance',string='Family Id')  
    dob = fields.Date('Date Of Birth')
    gender = fields.Selection([('male','Male'), ('female','Female')])  
    relation = fields.Selection([('Self','Self'),('Spouse','Spouse'),('Son','Son'),('Daughter','Daughter')],'Relation')

    @api.onchange('relation','gender')
    def onchange_relation(self):
        if self.relation:
            if self.relation == 'Son':
                gender = 'male'
            elif self.relation == 'Daughter':
                gender = 'female'
            elif self.relation == 'Self':
                gender = self.family_id.employee_id.gender
                self.name = self.family_id.employee_id.name
                self.dob = self.family_id.employee_id.birthday
            else:
                gender=self.gender
        else:
            gender =self.gender
        self.gender = gender

#MEDICAL INSURANCE FOR PARENTS
class medical_insurance_parents(models.Model):
    _name="medical.insurance.parents"
    _description = "Medical Insurance Parents"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    def default_login_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit = 1)
    
    employee_id = fields.Many2one('hr.employee',string="Employee",default=default_login_employee,track_visibility="onchange")
    insurance_date = fields.Date('Insurance Date')
    emp_id = fields.Char('Employee ID')
    doj = fields.Date('Date of Joining')
    dob = fields.Date('Date of Birth')
    work_location = fields.Char('Work Location')
    work_mobile = fields.Char('Mobile No')
    gender = fields.Selection([('male', 'Male'),('female', 'Female'),('other', 'Other')],'Gender')
    name = fields.Char(string='Reference Number')
    marital = fields.Selection([('single', 'Single'),('married', 'Married'),('widower', 'Widower'),('divorced', 'Divorced')], string='Marital Status')
    plan = fields.Char('Plan',default='2P')
    sum_assured = fields.Char('Sum Insured',default='3 Lakhs')
    opt_in = fields.Boolean('Opt In',default=True)
    state = fields.Selection([('Draft','Draft'),('Closed','Closed')],string='Status',default='Draft')
    family_detail_lines = fields.One2many('family.lines.parents','family_id',string='Family Floater')

    @api.onchange('employee_id')
    def onchange_employee(self):
        emp = self.employee_id
        if emp:
            user = self.env.user
            user_id = emp.user_id and emp.user_id.id or False
            if user.id != user_id:
                if not user.has_group('hr.group_hr_manager'):
                    raise exceptions.ValidationError(_("Sorry! You can not create other employee's Medical Insurance request."))
            self.emp_id = self.employee_id.nf_emp
            self.doj = self.employee_id.join_date
            self.dob = self.employee_id.birthday
            self.work_location = self.employee_id.work_location
            self.work_mobile = self.employee_id.mobile_phone
            self.gender = self.employee_id.gender
            self.marital = self.employee_id.marital

    @api.model
    def create(self, vals):
        ins_id = self.search([('employee_id', '=', vals['employee_id'])])
        if ins_id:
            raise exceptions.ValidationError(_('Medical Insurance for this employee is already created.'))
        if vals['opt_in'] == True:
            if not vals['family_detail_lines']:
                raise exceptions.ValidationError(_('Parent details cannot be empty'))
            elif len(vals['family_detail_lines']) == 0:
                raise exceptions.ValidationError(_('Please fill the Parents details properly'))
            elif len(vals['family_detail_lines']) >2:
                raise exceptions.ValidationError('Only 2 members can be added in this policy')

        emp=self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
        if emp:
            emp=emp[0]
            user = self.env.user
            user_id = emp.user_id and emp.user_id.id or False
            if user.id != user_id:
                if not user.has_group('hr.group_hr_manager'):
                    raise exceptions.ValidationError(_("Sorry! You can not create other employee's Medical Insurance request."))
            name = self.env['ir.sequence'].next_by_code('medical.insurance.parents') or '-'
            vals.update({'emp_id':emp.nf_emp,'work_location':emp.work_location,'work_mobile':emp.mobile_phone,'doj':emp.join_date,'dob':emp.birthday,'gender':emp.gender,'name':name,'marital':emp.marital})
        rec = super(medical_insurance_parents, self).create(vals)
        return rec

    
class family_lines_parents(models.Model):
    _name="family.lines.parents"
    
    name=fields.Char('Name')
    family_id = fields.Many2one('medical.insurance.parents',string='Family Id')  
    dob = fields.Date('Date Of Birth')
    gender = fields.Selection([('male','Male'), ('female','Female')])  
    relation = fields.Selection([('Father','Father'),('Mother','Mother')],'Relation')

    @api.onchange('relation','gender')
    def onchange_relation(self):
        if self.relation:
            if self.relation == 'Father':
                gender = 'male'
            elif self.relation == 'Mother':
                gender = 'female'
            else:
                gender=self.gender
        else:
            gender =self.gender
        self.gender = gender


    
class purchase_request(models.Model):
    _name="purchase.request"
    
    def default_login_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit = 1) 
    
    name = fields.Many2one('hr.employee',string="Employee",default=default_login_employee)
    ref_no = fields.Char(string='Reference Number')
    des_of_purchase = fields.Char('Description Of Purchase')
    outline_purchase = fields.Char('Outline Of the Purchase')
    references = fields.Text('References (If Any)')
    expenditure = fields.Float('Estimated Expenditure')
    attachment = fields.Many2many('attachments','purchase_attachment_rel','purchase_attachment_id','attach_id',string='Attachment')
    
    
class  attachments(models.Model):
    _name="attachments"
    
    name=fields.Char('File Name')
    attach = fields.Binary(string='Attachments')


class hr_employee(models.Model):
    _inherit = 'hr.employee'
    
    resignation_id = fields.Many2one('resign','Exit Details(Resignation)')
    termination_id = fields.Many2one('termination','Exit Details(Termination)')