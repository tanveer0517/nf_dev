# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import time
from odoo import exceptions
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import api, fields, models, tools
from openerp.tools.translate import _
from openerp.exceptions import UserError
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import mimetypes
from email.mime.multipart import MIMEMultipart
import smtplib
import urlparse
from lxml import etree
from openerp.osv.orm import setup_modifiers
from odoo.exceptions import ValidationError
from openerp.osv import osv
import re
import mimetypes
from odoo.tools import config, human_size, ustr, html_escape
import pyPdf
import xml.dom.minidom
import zipfile
from StringIO import StringIO
import requests
import json
import base64

FTYPES = ['docx', 'pptx', 'xlsx', 'opendoc', 'pdf']
Level_Selection = [('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')]
Priority_Selection = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5')]
Grade_Selection = [('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')]
Years = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11'),('12','12'),('13','13'),('14','14'),('15','15'),('16','16'),('17','17'),('18','18'),('19','19'),('20','20'),('21','21'),('22','22'),('23','23'),('24','24'),('25','25')]
Months = [('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11')]

def textToString(element):
    buff = u""
    for node in element.childNodes:
        if node.nodeType == xml.dom.Node.TEXT_NODE:
            buff += node.nodeValue
        elif node.nodeType == xml.dom.Node.ELEMENT_NODE:
            buff += textToString(node)
    return buff

class Applicant(models.Model):
    _inherit = "hr.applicant"
    
    @api.one
    @api.depends('job_id')
    def get_parent_job(self):
        for record in self:
            record.parent_job_id = record.job_id.parent_id
            
    def _default_stage_id(self):
        if self._context.get('default_job_id'):
            parent_id = self.env['hr.job'].browse(self._context['default_job_id']).parent_id
            ids = self.env['hr.recruitment.stage'].search([
                '|',
                ('job_id', '=', False),
                ('job_id', '=', parent_id and parent_id.id or False),
                ('fold', '=', False)
            ], order='sequence asc', limit=1).ids
            if ids:
                return ids[0]
        return False
    
 #============================Docx To String=========================================   
    
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
 
 #============================Docx To String=========================================
 
    def default_country_code(self):
        temp = self.env['country.code'].search([('country_id.name','=','India')],limit = 1)
        return temp
                  
    survey_id = fields.Many2one('survey.survey','Survey')
    interviewer_id =fields.Many2one('res.users','Interviewer')
    branch_id =fields.Many2one('hr.branch','Branch')
    survey_id1 = fields.Many2many('survey.survey','survey_applicant_rel','applicant_id','survey_id',string="Interview Form")
    response_id1 = fields.Many2many('survey.user_input','response_applicant_rel','applicant_id','response_id','Response')
    interviewer_hist_line = fields.One2many('interviewer.hist.line','applicant_id',string="Interviewers")
    allocat_hr = fields.Many2one('res.users',string='H.R.')
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage', track_visibility='onchange',
                               domain="['|', ('job_id', '=', False), ('job_id', '=', parent_job_id)]",
                               copy=False, index=True,
                               group_expand='_read_group_stage_ids',
                               default=_default_stage_id)
    parent_job_id = fields.Many2one('hr.job',compute='get_parent_job',string='Job',store=True)
    start_interview = fields.Boolean('Start Interview')
    select_note = fields.Boolean('Selection Note')
    attach_doc = fields.Binary('Attach Resume')
    filename = fields.Char('File Name')
    interview_time = fields.Datetime('Interview Time')
    doj = fields.Date('Expected Date Of Joining')
    index_content = fields.Text('Indexed Content', compute='_get_index_data', readonly=True, prefetch=False,store=True)
    refferal_id = fields.Many2one('hr.employee','Referred by')
    refferal_date = fields.Date('Application Date',default=fields.Date.context_today)
    idcard_type_id = fields.Many2one('id.card',string='Type')
    idcard_no = fields.Char('Other ID',help="Other ID like Adhaar Card...")
    tax_idcard_id = fields.Many2one('id.card',string='Type')
    tax_idcard_no = fields.Char('Tax ID',help="Tax ID")
    country_code_id = fields.Many2one('country.code','Country Code',default=default_country_code)
    priority = fields.Selection(Priority_Selection, "Appreciation", default='0')
    interview_type = fields.Selection([('Face To Face','Face To Face'),('Telephonic','Telephonic'),('Skype','Skype'),('Video Call','Video Call'),('Other','Other')],string='Interview Type')
    coach_id = fields.Many2one('hr.employee','Reporting Manager')
    c_current_annual_ctc = fields.Float(string='Current Annual CTC')
    c_current_annual_extra = fields.Char(string='Annual Salary Extra', help="Annual Salary In the Current Organisation")
    
    _sql_constraints = [
        ('applicant_uniq_email', 'UNIQUE(email_from)', 'Application already exist!'),
        ('applicant_uniq_phone', 'UNIQUE(partner_mobile)', 'Application already exist!'),
        ('applicant_uniq_pan', 'UNIQUE(idcard_no)', 'Application already exist!'),
        ('applicant_uniq_aadhar', 'UNIQUE(tax_idcard_no)', 'Application already exist!')
    ]
    
    # def _check_digit(self):
    #     for record in self:
    #         mobile_no = record.partner_mobile
    #         if len(mobile_no)==10 and mobile_no.isdigit():
    #            return True
    #     return False
    #
    # _constraints = [
    #     (_check_digit, 'Please enter a valid Mobile', ['partner_mobile']),
    #           ]

    @api.onchange('partner_mobile')
    def onchange_phone(self):
        mob_no = self.partner_mobile
        if mob_no:
            if mob_no.isdigit() == False or len(mob_no) != 10:
                raise exceptions.ValidationError(_('Please enter valid mobile number.'))

    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(Applicant, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        application_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if self == 'hr.applicant' and application_id:
            application = self.env['hr.applicant'].browse(application_id)
            doc = etree.XML(result['arch'])
            if application.interviewer_id == self.env.user_id.id and doc.xpath("//button[@name='send_email_To_HR']"):
                node = doc.xpath("//button[@name='send_email_To_HR']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['button']['send_email_To_HR'])
            result['arch'] = etree.tostring(doc)
        return result
    
#     def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
#         journal_obj = self
#         if context is None:
#             context = {}
#         print"====contecxttt=====",context,view_type
#         if  view_type == 'form':
#             mmy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_recruitment_extend','hr_applicant_view_form')
#             print"view_id====",view_id
#         res = super(Applicant,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
#         doc = etree.XML(res['arch'])
#         if view_type == 'form':
#             for node in doc.xpath("//button[@name='send_email_To_HR']"):
#                 print"=============node=============",node
#                 if interviewer_id == uid:
#                     node.set('invisible', '1')
#         res['arch'] = etree.tostring(doc)
#         print"===res==",res
#         return res
    
    
    
    @api.multi
    def action_start_survey(self):
        self.ensure_one()
        # create a response and link it to this applicant
        if not self.response_id:
            if self.survey_id:
                response = self.env['survey.user_input'].create({'survey_id': self.survey_id.id, 'partner_id': self.partner_id.id})
            else:
                response = self.env['survey.user_input'].create({'survey_id': self.survey.id, 'partner_id': self.partner_id.id})
            self.response_id = response.id
        else:
            response = self.response_id
        # grab the token of the response and start surveying
        if self.survey_id:
            return self.survey_id.with_context(survey_token=response.token).action_start_survey()
        else:
            return self.survey.with_context(survey_token=response.token).action_start_survey()
    
#   
    @api.multi
    def send_email_To_TA(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        rec_id = self.id
        print"context====",self._context
        model = self
        action_id = self._context['params']['action']
        active_id =self._context['active_id']
        a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(model)+"""&action=150&active_id="""+str(active_id)+"""&menu_id=142 """
        
        ef = """<a href="""+a+""">Click Here """+self.name+"""</a>"""
        
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
                msg['Subject'] = 'For Next Schedule '
        
                html = """<!DOCTYPE html>
                         <html>
                         <p>Dear Sir,</p>
                         
                         <p>Interview has been completed. </p>
                         <p>You can hold next round of interviews .</p>
                         <p>Please """+ef+""" to perform next Step.</p>
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
    def send_email_To_HR(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        rec_id = self.id
        print"context====",self._context['params']['action']
        model = self
        action_id = self._context['params']['action']
        active_id =self._context['active_id']
        a = """ """+str(base_url)+"""/web#id="""+str(self.id)+"""&view_type=form&model="""+str(model)+"""&action=150&active_id="""+str(active_id)+"""&menu_id=142 """
        ef = """<a href="""+a+""">Click Here """+self.name+"""</a>"""
    
        out_server = self.env['ir.mail_server'].search([])
        if out_server:
            out_server = out_server[0]
            
            emailfrom =out_server.smtp_user
            emailto =[]
            if self.allocat_hr and self.allocat_hr.login:
                emailto.append(self.allocat_hr.login)
               
            if emailfrom and emailto:
                
                msg = MIMEMultipart()
                msg['From'] = emailfrom
                msg['To'] = ", ".join(emailto)
                msg['Subject'] = 'For Next Schedule'
        
                html = """<!DOCTYPE html>
                         <html>
                         <p>Dear Sir,</p>
                         
                         <p>Interview has been completed. </p>
                         <p>You can hold next round of interviews .</p>
                         <p>Please """+ef+""" to perform next Step.</p>
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
    
    @api.onchange('job_id')
    def onchange_job_id(self):
        vals = self._onchange_job_id_internal(self.job_id.id)
        self.department_id = vals['value']['department_id']
        self.user_id = vals['value']['user_id']
        self.stage_id = vals['value']['stage_id']
        self.allocat_hr = vals['value']['allocat_hr']
        self.branch_id = vals['value']['branch_id']
        self.filename = self.job_id.filename
        self.name = self.job_id.name
    
    def _onchange_job_id_internal(self, job_id):
        department_id = False
        allocat_hr=False
        user_id = False
        branch_id = False
        stage_id = self.stage_id.id
        if job_id:
            job = self.env['hr.job'].browse(job_id)
            department_id = job.department_id and job.department_id.id or False
            user_id = job.user_id.id
            allocat_hr = job.allocat_hr.id
            branch_id = job.branch_id and job.branch_id.id or False
            if not self.stage_id:
                stage_ids = self.env['hr.recruitment.stage'].search([
                    ('job_id', '=', job.parent_id and job.parent_id.id or job.id),
                    ('fold', '=', False)
                ], order='sequence asc', limit=1).ids
                stage_id = stage_ids[0] if stage_ids else False
        return {'value': {
            'department_id': department_id,
            'user_id': user_id,
            'allocat_hr':allocat_hr,
            'branch_id':branch_id,
            'stage_id': stage_id,
        }}
      
#     @api.multi
#     def write(self, vals):
#         # user_id change: update date_open
#         if vals.get('user_id'):
#             vals['date_open'] = fields.Datetime.now()
#         print"====vals and not self.survey_id====",vals ,self.survey,self.survey_id
#         if not self.survey_id:
#             print"44444"
#             if 'survey' in vals:
#                 print"2222"
#                 vals['survey_id'] = vals['survey']
#             else:
#                 print"1111"
#                 vals['survey_id'] = self.survey.id
#         
#         # stage_id: track last stage before update
#         if 'stage_id' in vals:
#             vals['date_last_stage_update'] = fields.Datetime.now()
#             vals.update(self._onchange_stage_id_internal(vals.get('stage_id'))['value'])
#             for applicant in self:
#                 vals['last_stage_id'] = applicant.stage_id.id
#                 res = super(Applicant, self).write(vals)
#         else:
#             res = super(Applicant, self).write(vals)
# 
#         # post processing: if stage changed, post a message in the chatter
#         if vals.get('stage_id'):
#             if self.stage_id.template_id:
#                 self.message_post_with_template(self.stage_id.template_id.id, notify=True, composition_mode='mass_mail')
#         return res

    @api.multi
    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            self.env.cr.execute("select count(id) from interviewer_hist_line where stage_result = 'rejected' and applicant_id = '"+str(applicant.id)+"'")
            temp = self.env.cr.fetchone()
            if len(temp) and temp[0] >= 2:
                raise osv.except_osv(_('Warning'), _('Applicant has been rejected %s times. You can not create employee if applicant has been rejected 2 times.')%(temp[0],))
            address_id = contact_name = False
            if not applicant.doj:
                raise osv.except_osv(_('Warning'), _('Please define Date Of Joining'))
            
            if not applicant.coach_id:
                raise osv.except_osv(_('Warning'), _('Please define Reporting Manager'))
            
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.name_get()[0][1]
            if applicant.job_id and (applicant.partner_name or contact_name):
                applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                employee = self.env['hr.employee'].create({'name': applicant.partner_name or contact_name,
                                               'job_id': applicant.job_id and applicant.job_id.parent_id and applicant.job_id.parent_id.id or False,
                                               'address_home_id': address_id,
                                               'department_id': applicant.department_id and applicant.department_id.parent_id and applicant.department_id.parent_id.id or False,
                                               'sub_dep':applicant.department_id and applicant.department_id.id or False,
                                               'branch_id':applicant.branch_id and applicant.branch_id.id or False,
                                               'street':applicant.branch_id and applicant.branch_id.street,
                                               'street2':applicant.branch_id and applicant.branch_id.street2,
                                               'city':applicant.branch_id and applicant.branch_id.city,
                                               'zip':applicant.branch_id and applicant.branch_id.zip,
                                               'state_id':applicant.branch_id and applicant.branch_id.state_id and applicant.branch_id.state_id.id or False,
                                               'country_id':applicant.branch_id and applicant.branch_id.country_id and applicant.branch_id.country_id.id or False,
                                               'address_id': applicant.company_id and applicant.company_id.partner_id and applicant.company_id.partner_id.id or False,
                                               'work_email': applicant.email_from,
                                               'work_phone': applicant.partner_mobile,
                                               'join_date':applicant.doj,
                                               'idcard_type_id':applicant.idcard_type_id and applicant.idcard_type_id.id or False,
                                               'idcard_no':applicant.idcard_no,
                                               'tax_idcard_id':applicant.tax_idcard_id and applicant.tax_idcard_id.id or False,
                                               'tax_idcard_no':applicant.tax_idcard_no,
                                               'coach_id':applicant.coach_id and applicant.coach_id.id or False,
                                               })
                applicant.write({'emp_id': employee.id})
                applicant.job_id.message_post(
                    body=_('New Employee %s Hired') % applicant.partner_name if applicant.partner_name else applicant.name,
                    subtype="hr_recruitment.mt_job_applicant_hired")
                employee._broadcast_welcome()
            else:
                raise UserError(_('You must define an Applied Job and a Contact Name for this applicant.'))

        employee_action = self.env.ref('hr.open_view_employee_list')
        dict_act_window = employee_action.read([])[0]
        if employee:
            dict_act_window['res_id'] = employee.id
        dict_act_window['view_mode'] = 'form,tree'
        
        return dict_act_window
    
    
    @api.multi
    def email_to_applicant(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env['mail.template'].search([('name','=','email to applicant')],limit=1)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='hr.applicant',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        
    @api.multi
    def email_to_interviewer(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env['mail.template'].search([('name','=','email to interviewer')],limit=1)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='hr.applicant',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        
    @api.multi
    def review_email(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env['mail.template'].search([('name','=','applicant review email')],limit=1)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='hr.applicant',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }        
        
    @api.model
    def create(self, vals):
        if vals.get('stage_id',False) and self.env['hr.recruitment.stage'].browse(vals['stage_id']).interview:
            if not vals.get('interviewer_id',False) or not vals.get('interview_time',False):
               raise ValidationError("Select Interviewer And Interview Time")
            vals.update({'select_note':True})
        return super(Applicant, self).create(vals)
    
    @api.multi
    def write(self,vals):
        if 'stage_id' in vals and vals['stage_id']:
            for record in self:
                if record.select_note:
                    raise osv.except_osv(_('Warning'), _('Kindly give interview feedback for %s')%(record.stage_id and record.stage_id.name or ''))
                self.env.cr.execute("select count(id) from interviewer_hist_line where stage_id = '"+str(vals['stage_id'])+"' and applicant_id = '"+str(record.id)+"'")
                temp = self.env.cr.fetchone()
                if len(temp) and temp[0] >= 1:
                    stage = self.env['hr.recruitment.stage'].browse(vals['stage_id']).name
                    raise osv.except_osv(_('Warning'), _('%s already been processed')%(stage,))
            if self.env['hr.recruitment.stage'].browse(vals['stage_id']).interview:
                vals.update({'select_note':True})
                res = super(Applicant,self).write(vals) 
                self.start_process()
                return res       
        return super(Applicant,self).write(vals)
    
    def start_process(self):
        name = self.name
#         stage_id = self.stage_id and self.stage_id.id or None
        if not self.interviewer_id or not self.interview_time:
            raise ValidationError("Select Interviewer And Interview Time")
        
#         user_id = self.interviewer_id.id
#         title_action = 'Start'
#         date_action = fields.Date.context_today(self)
#         self.env.cr.execute("Insert INTO interviewer_hist_line (name,stage_id,user_id,title_action,date_action,applicant_id,stage_result) values (%s,%s,%s,%s,%s,%s,%s)",
#                             (name,stage_id,user_id,title_action,date_action,self.id,'start'))
        
        category = self.env.ref('hr_recruitment.categ_meet_interview')
        calendar_alarm = self.env['calendar.alarm'].search([('name','=','interview')],limit = 1)
        partners = self.interviewer_id and self.interviewer_id.partner_id or False
        if partners:
            vals = {'name':self.name,
                    'partner_ids': [(6,0,partners.ids)],
                    'user_id': self.env.uid,
                    'categ_ids': [(6,0,category and [category.id] or [])],
                    'start_datetime':self.interview_time,
                    'alarm_ids':[(6,0,calendar_alarm.ids)],
                    'start':self.interview_time,
                    'stop':self.interview_time,
                    }
            self.env['calendar.event'].create(vals)
                

class InterviewerHistLine(models.Model):
    _name="interviewer.hist.line"
    
#     def default_get(self, cr, uid, ids, context=None):
#         res = {}
#         print"====default_get===",context
#         if context:
#             context_keys = context.keys()
#             next_sequence = 1
#             if 'sequence' in context_keys:
#                 print"context_keys===",context_keys
#                 if len(context.get('sequence')) > 0:
#                     next_sequence = len(context.get('sequence')) + 1
#                     print"next_sequence===",next_sequence
#         res.update({'sequence': next_sequence})
#         return res
    
    sequence = fields.Integer(string='Sequence',index=True, help="Gives the sequence order.")
    name = fields.Char('Name')
    stage_id = fields.Many2one('hr.recruitment.stage','Stage')
    survey_id = fields.Many2one('survey.survey','Survey')
    user_id =fields.Many2one('res.users','Interviewer')
    title_action = fields.Text('Summary')
    date_action = fields.Date('Date')
    response_id = fields.Many2one('survey.user_input','Response')
    applicant_id = fields.Many2one('hr.applicant','Applicant')
    stage_result = fields.Selection([('selected','Selected'),('rejected','Rejected')],string='Stage Result')
    
    interview_type = fields.Selection([('Skype','Skype'),('Video Call','Video Call'),('Other','Other')],string='Interview Type')
    communication_skill = fields.Selection(Priority_Selection,'Communication Skill')
    communication_remark = fields.Text('Comment')
    resume_validation = fields.Selection(Priority_Selection,'Resume-Validation')
    resume_remark = fields.Text('Comment')
    jd_fitment = fields.Selection(Priority_Selection,'Jd Fitment')
    jd_fitment_remark = fields.Text('Comment')
    tech_competency = fields.Selection(Priority_Selection,string='Technical Competency')
    tech_remark = fields.Text('Comment')
    rating = fields.Selection(Priority_Selection,string='Overall Rating')
    attitude = fields.Selection(Priority_Selection,string='Attitude/Cultural Fit',default='0')
    attitude_remark = fields.Text('Comment')
    level = fields.Selection([('Yes','Yes'),('No','No')],'Fit For the Role ?')
    fitc = fields.Selection([('Yes','Yes'),('No','No')],'Fit For the Company ?')
        
    @api.multi
    def action_start_survey(self):
        self.ensure_one()
        response = self.response_id
        if response:
            return self.survey_id.with_context(survey_token=response.token).action_start_survey()
        
class task_subject(models.Model):
    _name = 'task.subject'
    
    name=fields.Char('Subject')
    description= fields.Char('Content')
    alert_days =fields.Integer('Alert Before Days')
    

class Task(models.Model):
    _inherit = 'project.task'   
    
#     @api.multi
    @api.model
    def triger_task_email(self, ids=None):
        line_ids= self.env['project.task'].search([])
        print"lines=====",ids,line_ids
        for val in line_ids:
            send_mail = False
            print"val======",val,"----", datetime.now().strftime('%Y-%m-%d')
            today_date=time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            today_date = datetime.strptime(today_date,"%Y-%m-%d")
            if val.date_deadline:
                expiry_date=time.strftime(val.date_deadline)
                date1 = datetime.strptime(expiry_date,"%Y-%m-%d")
                before_day = date1 - timedelta(days=1)
                if before_day == today_date:
                    send_mail = True
            
            if send_mail:
#                 partner_id = [val.user_id.id]
#                 values = {
#                       'subject':'Document Expire Soon',
#                       'author_id':partner_id[0],
#                       'notified_partner_ids':[(6,0,partner_id)],
#                       'body':val.code + val.doc_no + val.description,
#                       }
#                 self.env['mail.message'].create(values)
                
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                rec_id = val.id
#                 print"====self.env=====",self.env.context
#                 print"context====",self._context['params']['action']
                model = self
#                 action_id = self._context['params']['action']
                a = """ """+str(base_url)+"""/web#id="""+str(val.id)+"""&view_type=form&model="""+str(model)+"""&action='"""+str(698)+"""' """
                ef = """<a href="""+a+""">"""+val.name+"""</a>"""
            
            
                out_server = self.env['ir.mail_server'].search([])
                emailto = []
                emailfrom= ''
                if out_server:
                    out_server = out_server[0]
                    if out_server.smtp_user:
                        emailfrom =out_server.smtp_user
                    if val.user_id and val.user_id.login:
                        emailto.append(val.user_id.login)
                    if emailfrom and len(emailto) >= 1:
                        msg = MIMEMultipart()
                        msg['From'] = emailfrom
                        msg['To'] = ", ".join(emailto)
                        msg['Subject'] = 'Your Task Has Been Created'
                        
                        html = """<!DOCTYPE html>
                                 <html>
                                 Dear Sir,
                                 <br/>
                                 Your Task has been Created and Assigned to you.
                                 <br/>
                                 Please """+ef+""" to revise Task.
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
    
class RecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"
    
    interview = fields.Boolean('Interview')
    
class task_onboarding_applicant(models.Model):
    _name = "task.onboarding.applicant"
    
    name = fields.Char('To Do')
    days = fields.Integer('Days')
    user_id = fields.Many2one('res.users','Responsible') 
    
    
class JobPositionView(models.Model):
    _name='job.position.view'
    
    _auto = False
    
    name = fields.Char('Name')
    department = fields.Char('Department')
    budgeted_headcount = fields.Integer('Budgeted Headcount')
    current_headcount = fields.Integer('Current Headcount')
    open_headcount = fields.Integer('Open Headcount')
    recruitment_pipeline = fields.Integer('Recruitment Pipeline')
    application_pipeline = fields.Integer('Application Pipeline')     
    

class nf_joining_candidate(models.Model):
    _name='nf.joining.candidate'
    _description='Candidate Joining Details'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

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
    bank_account_available = fields.Boolean('Bank Account Available')
    account_holder_name = fields.Char('Account Holder Name')
    account_number = fields.Char('Bank Account Number')
    bank_name = fields.Char('Bank Name')
    bank_branch_name = fields.Char('Branch Name')
    bank_ifsc_code = fields.Char('IFSC Code')
    highest_education = fields.Selection([('SSC','SSC'),('12th','12th'),('Diploma','Diploma'),('Graduation','Graduation'),('Post Graduation','Post Graduation'),('Doctorate','Doctorate')],'Highest Educational Qualification')
    degree_id = fields.Many2one('hr.recruitment.degree','Degree')
    other_degree = fields.Char('Other Degree')
    college_name = fields.Char('Name of College')
    university_name = fields.Char('Board/University Name')
    unviversity_city = fields.Char('University City')
    graduation_year = fields.Char('Year of Graduation')
    resume = fields.Char('Resume')
    education_certificate = fields.Char('Highest Educational Certificate')
    pan_card = fields.Char('PAN Card')
    aadhar_card = fields.Char('Aadhaar Card')
    cancel_cheque = fields.Char('Cancelled Cheque/Passbook')
    salary_slip = fields.Char("Previous Company's Payslip - 1")
    salary_slip1 = fields.Char("Previous Company's Payslip - 2")
    salary_slip2 = fields.Char("Previous Company's Payslip - 3")
    resignation_acceptance = fields.Char('Resignation Acceptance or Resignation Mail of current/last organization/Relieving Letter')
    total_experience_years = fields.Selection(Years,'Total Experience Years',default='0')
    total_experience_months = fields.Selection(Months,'Total Experience Months',default='0')
    relevant_experience_years = fields.Selection(Years,'Relevant Experience Years',default='0')
    relevant_experience_months = fields.Selection(Months,'Relevant Experience Months',default='0')
    family_details = fields.One2many('nf.candidate.onboarding.family','candidate_id','Family Details')
    previous_employment = fields.One2many('nf.previous.employment','candidate_id','Previous Employment')

    onboarding_id = fields.Many2one('nf.candidate.onboarding','Onboarding ID')
    date_join = fields.Date('Date of Joining', track_visibility='onchange')
    office_email = fields.Char('Official Email', track_visibility='onchange')
    internal_designation = fields.Char('Internal Designation', track_visibility='onchange')
    external_designation = fields.Many2one('hr.job','External Designation', track_visibility='onchange')
    division = fields.Many2one('hr.department','Division', track_visibility='onchange')
    reporting_manager = fields.Many2one('hr.employee','Reporting Manager', track_visibility='onchange')
    department_manager = fields.Many2one('hr.employee','Department Manager', track_visibility='onchange')
    esic_entitlement = fields.Selection([('Yes','Yes'),('No','No')],'ESIC Entitlement', track_visibility='onchange')
    state = fields.Selection([('Draft','Draft'),('Recruiter Submit','Recruiter Submit'),('Joined','Joined'),('Not Joined','Not Joined')],'Status',default='Draft', track_visibility='onchange')
    doc_status = fields.Selection([('Submitted','Submitted'),('Approved','Approved'),('Rejected','Rejected')],'Document Status', track_visibility='onchange')
    branch_id = fields.Many2one('hr.branch','Reporting Branch', track_visibility='onchange')
    virtual_branch_id = fields.Many2one('hr.branch', 'Attendance Branch', track_visibility='onchange')
    source = fields.Selection([('Direct','Direct'),('Employee Referral','Employee Referral'),('Vendor','Vendor'),('Campus','Campus'),('Others','Others')],'Source of Selection', track_visibility='onchange')
    source_name = fields.Char('Source Name', track_visibility='onchange')
    hire_status = fields.Selection([('New Hire','New Hire'),('Rehire','Rehire')],'Hiring Status',default='New Hire', track_visibility='onchange')
    hike = fields.Char('Hike', track_visibility='onchange')
    recruiter_name = fields.Many2one('hr.employee','Recruiter Name', track_visibility='onchange')
    office_location = fields.Char('Office Location', track_visibility='onchange')
    emp_id = fields.Char('Employee ID', track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee','Employee')
    c_empl_type=fields.Selection([('contract','Contract'),('intern','Intern'),('permanent','Permanent'),('probation','Probation')],string="Employee Type", track_visibility='onchange')
    level=fields.Selection(Grade_Selection,string='Level', track_visibility='onchange')
    remarks = fields.Text('Reject Reason')

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.branch_id:
            self.office_location = self.branch_id and self.branch_id.c_city_id and self.branch_id.c_city_id.name or False

    @api.multi
    def doc_reject(self):
        for i in self:
            rec_id = self.env['wiz.reject.onboarding.doc'].create({'onboarding_id':i.onboarding_id.id,'candidate_id':i.id})
            #display wizard
            return {
                'name':_("Document Reject Reason"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'wiz.reject.onboarding.doc',
                'res_id': rec_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new'
            }
        return True

    @api.multi
    def candidate_joined(self):
        for rec in self:
            rec.write({'state':'Joined'})
        return True

    @api.multi
    def candidate_not_joined(self):
        for rec in self:
            rec.write({'state':'Not Joined'})
        return True

    @api.multi
    def recruiter_submit(self):
        for rec in self:
            rec.write({'state':'Recruiter Submit'})
        return True

    @api.multi
    def doc_approve(self):
        for rec in self:
            if rec.onboarding_id:
                rec.onboarding_id.sudo().write({'state':'Approved'})
                rec.write({'doc_status':'Approved'})
                self.env.cr.execute("UPDATE res_users SET active = False where id = %s",(rec.onboarding_id.user_id.id,))
        return True

    @api.multi
    def create_employee(self):
        for rec in self:
            if not rec.emp_id or not rec.office_email or not rec.internal_designation:
                raise ValidationError('Please check Employee ID, Internal Designation and Office Email. It is required before creating employee.')

            if not rec.branch_id or not rec.virtual_branch_id:
                raise ValidationError('Please check Reporting Branch and Attendance Branch. It is required before creating employee.')

            hire_status = 'No'
            if rec.hire_status == 'Rehire':
                hire_status = 'Yes'

            family_details=[]
            pre_comp_details=[]
            if rec.family_details:
                for family in rec.family_details:
                    family_details.append((0,False,{'name':family.name,'dob':family.dob,'relation':family.relation,'gender':family.gender,'c_cont_num':family.contact_number}))
            if rec.previous_employment:
                for pre_emp in rec.previous_employment:
                    pre_comp_details.append((0,False,{'name':pre_emp.name,'designation':pre_emp.designation,'doj':pre_emp.doj,'dol':pre_emp.dol,'ctc':pre_emp.ctc,'reason_leaving':pre_emp.reason_leaving,'currently_working':pre_emp.currently_working}))
            bank_rec = False
            if rec.bank_account_available:
                bank_rec = self.env['res.partner.bank'].create({'acc_number':rec.account_number,'c_bank_name':rec.bank_name,'ifsc_code':rec.bank_ifsc_code,'branch_name':rec.bank_branch_name})
                rec.onboarding_id.user_id.partner_id.sudo().write({'name':rec.account_holder_name})

            values={'name':rec.name,
                    'disp_name':rec.full_name,
                    'gender':rec.gender,
                    'join_date':rec.date_join,
                    'mobile_phone':rec.contact_no,
                    'personal_email':rec.personal_email,
                    'work_email':rec.office_email,
                    'intrnal_desig':rec.internal_designation,
                    'job_id':rec.external_designation and rec.external_designation.id or False,
                    'sub_dep':rec.division and rec.division.id or False,
                    'coach_id':rec.reporting_manager and rec.reporting_manager.id or False,
                    'parent_id':rec.department_manager and rec.department_manager.id or False,
                    'high_edu_qual':rec.highest_education,
                    'nf_emp':rec.emp_id,
                    'c_recruiter_name':rec.recruiter_name and rec.recruiter_name.id or False,
                    'work_location':rec.office_location,
                    'rehire':hire_status,
                    'branch_id':rec.branch_id and rec.branch_id.id or False,
                    'virtual_branch_id':rec.virtual_branch_id and rec.virtual_branch_id.id or False,
                    'c_empl_type':rec.c_empl_type,
                    'level':rec.level,
                    'candidate_id':rec.id,
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
                    'previous_employment':pre_comp_details,
                    'bank_account_id':bank_rec and bank_rec.id or False,
                    'resume_link':rec.resume,
                    'education_certificate_link':rec.education_certificate,
                    'pan_card_link':rec.pan_card,
                    'aadhar_card_link':rec.aadhar_card,
                    'cancel_cheque_link':rec.cancel_cheque,
                    'salary_slip_link':rec.salary_slip,
                    'salary_slip_link1':rec.salary_slip1,
                    'salary_slip_link2':rec.salary_slip2,
                    'resignation_acceptance_link':rec.resignation_acceptance,
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
                    'emergency_contact_relation':rec.emergency_contact_relation
                    }
            emp_rec = self.env['hr.employee'].create(values)
            rec.write({'employee_id':emp_rec.id})
        return True

class nf_candidate_onboarding(models.Model):
    _name = 'nf.candidate.onboarding'
    _description = 'NF Candidate Onboarding'

    name = fields.Char('Name as Per PAN Card*')
    full_name = fields.Char('Full Name*')
    gender = fields.Selection([('male', 'Male'),('female', 'Female'),('other', 'Other')],'Gender*')
    birth_date = fields.Date('Date of Birth*')
    religion = fields.Selection([('Hindu','Hindu'),('Muslim','Muslim'),('Christian','Christian'),('Sikh','Sikh'),('Buddhist','Buddhist'),('Jain','Jain'),('Other','Other')],'Religion')
    other_religion = fields.Char('Other Religion')
    disability = fields.Selection([('P','Yes - Partially Disabled'),('F','Yes - Fully Disabled'),('N','No')],'Disability*')
    blood_group = fields.Selection([('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')],'Blood Group')
    marital_status = fields.Selection([('single', 'Single'),('married', 'Married'),('widower', 'Widower'),('divorced', 'Divorced')], string='Marital Status*',default='single')
    anniversary_date = fields.Date('Date of Marriage*')
    father_name = fields.Char("Father's Name as per Aadhaar Card*")
    nationality = fields.Many2one('res.country','Nationality(Country)*')
    aadhar_available = fields.Boolean('Is Aadhaar Available?')
    aadhar_no = fields.Char('Aadhaar Number*')
    pan_available = fields.Boolean('Is PAN Available?')
    pan_no = fields.Char('PAN Number*')
    voter_id = fields.Char('Voter ID')
    passport_no = fields.Char('Passport Number')
    driving_license_no = fields.Char('Driving Licence Number')
    previous_uan = fields.Char('Previous UAN')
    previous_pf = fields.Char('Previous PF Number')
    contact_no = fields.Char('Contact Number*')
    personal_email = fields.Char('Personal Email*')
    current_street1 = fields.Char('Current Street1*')
    current_street2 = fields.Char('Current Street2*')
    current_city = fields.Many2one('ouc.city','Current City*')
    current_state = fields.Many2one('res.country.state','Current State',related='current_city.state_id')
    current_country = fields.Many2one('res.country','Current Country',related='current_city.country_id')
    current_zip = fields.Char('Current Zip*')
    is_address_same = fields.Boolean('Is Permanent Address Same as Current Address')
    permanent_street1 = fields.Char('Permanent Street1*')
    permanent_street2 = fields.Char('Permanent Street2*')
    permanent_city = fields.Many2one('ouc.city','Permanent City*')
    permanent_state = fields.Many2one('res.country.state','Permanent State',related='permanent_city.state_id')
    permanent_country = fields.Many2one('res.country','Permanent Country',related='current_city.country_id')
    permanent_zip = fields.Char('Permanent Zip*')
    emergency_contact_no = fields.Char('Emergency Contact Number*')
    emegency_person_name = fields.Char('Emergency Contact Person*')
    emergency_contact_relation = fields.Char('Emergency Contact Relation*')
    bank_account_available = fields.Boolean('Bank Account Available')
    account_holder_name = fields.Char('Account Holder Name as per Bank Account')
    account_number = fields.Char('Bank Account Number')
    bank_name = fields.Char('Bank Name')
    bank_branch_name = fields.Char('Branch Name')
    bank_ifsc_code = fields.Char('IFSC Code')
    family_details = fields.One2many('nf.candidate.onboarding.family','onboarding_id','Family Details*')
    highest_education = fields.Selection([('SSC','SSC'),('12th','12th'),('Diploma','Diploma'),('Graduation','Graduation'),('Post Graduation','Post Graduation'),('Doctorate','Doctorate')],'Highest Educational Qualification*')
    degree_id = fields.Many2one('hr.recruitment.degree','Degree*')
    other_degree = fields.Char('Other Degree*')
    college_name = fields.Char('Name of College*')
    university_name = fields.Char('Board/University Name*')
    unviversity_city = fields.Char('University City*')
    graduation_year = fields.Char('Year of Graduation*')
    resume_filename = fields.Char('Resume Filename')
    resume = fields.Binary('Resume*')
    education_certificate_filename = fields.Char('Highest Educational Filename')
    education_certificate = fields.Binary('Highest Educational Certificate*')
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
    previous_employment = fields.One2many('nf.previous.employment','onboarding_id','Previous Employment')
    accept = fields.Boolean('Accept')
    date = fields.Date('Date*')
    place = fields.Char('Place*')
    state = fields.Selection([('Draft','Draft'),('Submitted','Submitted'),('Rejected','Rejected'),('Approved','Approved')],'Status',default='Draft')
    recruiter_email = fields.Char('Recruiter Email*')
    recruiter_id = fields.Integer('Recruiter ID')
    user_id = fields.Many2one('res.users','User')
    candidate_id = fields.Many2one('nf.joining.candidate','Candidate')

    @api.onchange('name')
    def onchange_name(self):
        name=self.name
        if name:
            self.name = name.title()

    @api.onchange('full_name')
    def onchange_full_name(self):
        full_name=self.full_name
        if full_name:
            self.full_name = full_name.title()

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


    @api.model
    def default_get(self, fields):
        rec={}
        rec = super(nf_candidate_onboarding, self).default_get(fields)
        rec.update({'user_id':self.env.uid})    
        return rec

    @api.onchange('user_id')
    def onchange_user(self):
        if self.user_id:
            onboard_rec = self.sudo().search([('user_id','=',self.user_id.id)])
            if onboard_rec:
                raise exceptions.ValidationError(_('You have already filled onboarding form. Please contact HR.'))

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

    @api.onchange('recruiter_email')
    def onchange_recruiter_email(self):
        if self.recruiter_email:
            recruiter_email = self.recruiter_email.strip()
            recruiter_id = self.env['hr.employee'].sudo().search([('work_email','=',recruiter_email)])
            if recruiter_id:
                self.recruiter_id = recruiter_id.id
            else:
                self.recruiter_email = False
                raise exceptions.ValidationError(_('Recruiter Email ID is invalid. Please check it again.'))

    @api.multi
    def write(self,vals):
        cr=self.env.cr
        pan_no = vals.get('pan_no',False)
        if pan_no and len(pan_no) != 10:
            raise exceptions.ValidationError(_('Please enter valid PAN Number. It should be of 10 characters.'))
        aadhar_no = vals.get('aadhar_no',False)
        if aadhar_no:
            try:
                aadhar = int(aadhar_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should not contain characters.'))
            if len(aadhar_no) != 12:
                raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should be of 12 digits.'))
        contact_no = vals.get('contact_no',False)
        if contact_no:
            try:
                contact = int(contact_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should not contain characters.'))
            if len(contact_no) != 10:
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should be of 10 digits.'))
        emergency_contact_no = vals.get('emergency_contact_no',False)
        if emergency_contact_no:
            try:
                emergency_contact = int(emergency_contact_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Emergency Contact Number. It should not contain characters.'))
            if len(emergency_contact_no) != 10:
                raise exceptions.ValidationError(_('Please enter valid Emergency Contact Number. It should be of 10 digits.'))
        personal_email = vals.get('personal_email',False)
        if personal_email and '@' not in personal_email:
            raise exceptions.ValidationError(_('Please enter valid Email ID.'))
        if vals.get('recruiter_email',False):
            recruiter_email = (vals.get('recruiter_email',False)).strip()
            recruiter_id = self.env['hr.employee'].sudo().search([('work_email','=',recruiter_email)])
            if recruiter_id:
                vals.update({'recruiter_id':recruiter_id.id})
            else:
                vals.update({'recruiter_email':False})
                raise exceptions.ValidationError(_('Recruiter Email ID is invalid. Please check it again.'))
        if self.candidate_id:
            if vals.get('resume',False):
                resume=self.get_doc_link(vals.get('resume_filename',False),vals.get('resume',False))
                cr.execute("UPDATE nf_joining_candidate SET resume = %s where id = %s",(resume,self.candidate_id.id,))

            if vals.get('education_certificate',False):
                education_certificate=self.get_doc_link(vals.get('education_certificate_filename',False),vals.get('education_certificate',False))
                cr.execute("UPDATE nf_joining_candidate SET education_certificate = %s where id = %s",(education_certificate,self.candidate_id.id,))

            if vals.get('pan_card',False):
                pan_card=self.get_doc_link(vals.get('pan_card_filename',False),vals.get('pan_card',False))
                cr.execute("UPDATE nf_joining_candidate SET pan_card = %s where id = %s",(pan_card,self.candidate_id.id,))

            if vals.get('aadhar_card',False):
                aadhar_card=self.get_doc_link(vals.get('aadhar_card_filename',False),vals.get('aadhar_card',False))
                cr.execute("UPDATE nf_joining_candidate SET aadhar_card = %s where id = %s",(aadhar_card,self.candidate_id.id,))

            if vals.get('cancel_cheque',False):
                cancel_cheque=self.get_doc_link(vals.get('cancel_cheque_filename',False),vals.get('cancel_cheque',False))
                cr.execute("UPDATE nf_joining_candidate SET cancel_cheque = %s where id = %s",(cancel_cheque,self.candidate_id.id,))

            if vals.get('salary_slip',False):
                salary_slip=self.get_doc_link(vals.get('salary_slip_filename',False),vals.get('salary_slip',False))
                cr.execute("UPDATE nf_joining_candidate SET salary_slip = %s where id = %s",(salary_slip,self.candidate_id.id,))

            if vals.get('salary_slip1',False):
                salary_slip1=self.get_doc_link(vals.get('salary_slip_filename1',False),vals.get('salary_slip1',False))
                cr.execute("UPDATE nf_joining_candidate SET salary_slip1 = %s where id = %s",(salary_slip1,self.candidate_id.id,))

            if vals.get('salary_slip2',False):
                salary_slip2=self.get_doc_link(vals.get('salary_slip_filename2',False),vals.get('salary_slip2',False))
                cr.execute("UPDATE nf_joining_candidate SET salary_slip2 = %s where id = %s",(salary_slip2,self.candidate_id.id,))

            if vals.get('resignation_acceptance',False):
                resignation_acceptance=self.get_doc_link(vals.get('resignation_acceptance_filename',False),vals.get('resignation_acceptance',False))
                cr.execute("UPDATE nf_joining_candidate SET resignation_acceptance = %s where id = %s",(resignation_acceptance,self.candidate_id.id,))

        if vals.get('is_address_same',False):
            if vals.get('current_street1',False):
                vals.update({'permanent_street1':vals.get('current_street1',False)})

            if vals.get('current_street2',False):
                vals.update({'permanent_street2':vals.get('current_street2',False)})

            if vals.get('current_city',False):
                vals.update({'permanent_city':vals.get('current_city',False)})

            if vals.get('current_state',False):
                vals.update({'permanent_state':vals.get('current_state',False)})

            if vals.get('current_country',False):
                vals.update({'permanent_country':vals.get('current_country',False)})

            if vals.get('current_zip',False):
                vals.update({'permanent_zip':vals.get('current_zip',False)})

        if vals.get('total_experience_months',False) and vals.get('total_experience_months',False) != '0' or vals.get('total_experience_years',False) and vals.get('total_experience_years',False) != '0':
            if not vals.get('previous_employment',False) and not self.previous_employment:
                raise exceptions.ValidationError(_('Please enter previous employment details.'))

        if not vals.get('family_details',False) and not self.family_details:
            raise exceptions.ValidationError(_('Please enter family details.'))

        super(nf_candidate_onboarding,self).write(vals)
        return True

    @api.model
    def create(self,vals):
        onboard_rec = self.search([('create_uid','=',self.env.uid)])
        if onboard_rec:
            raise exceptions.ValidationError(_('You have already filled onboarding form. Please contact HR.'))
        if vals.get('recruiter_email',False):
            recruiter_email = (vals.get('recruiter_email',False)).strip()
            recruiter_id = self.env['hr.employee'].sudo().search([('work_email','=',recruiter_email)])
            if recruiter_id:
                vals.update({'recruiter_id':recruiter_id.id})
            else:
                vals.update({'recruiter_email':False})
                raise exceptions.ValidationError(_('Recruiter Email ID is invalid. Please check it again.'))

        pan_no = vals.get('pan_no',False)
        if pan_no and len(pan_no) != 10:
            raise exceptions.ValidationError(_('Please enter valid PAN Number. It should be of 10 characters.'))
        aadhar_no = vals.get('aadhar_no',False)
        if aadhar_no:
            try:
                aadhar = int(aadhar_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should not contain characters.'))
            if len(aadhar_no) != 12:
                raise exceptions.ValidationError(_('Please enter valid Aadhaar Number. It should be of 12 digits.'))
        contact_no = vals.get('contact_no',False)
        if contact_no:
            try:
                contact = int(contact_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should not contain characters.'))
            if len(contact_no) != 10:
                raise exceptions.ValidationError(_('Please enter valid Contact Number. It should be of 10 digits.'))
        emergency_contact_no = vals.get('emergency_contact_no',False)
        if emergency_contact_no:
            try:
                emergency_contact = int(emergency_contact_no)
            except ValueError:
                raise exceptions.ValidationError(_('Please enter valid Emergency Contact Number. It should not contain characters.'))
            if len(emergency_contact_no) != 10:
                raise exceptions.ValidationError(_('Please enter valid Emergency Contact Number. It should be of 10 digits.'))

        personal_email = vals.get('personal_email',False)
        if personal_email and '@' not in personal_email:
            raise exceptions.ValidationError(_('Please enter valid Email ID.'))

        if vals.get('is_address_same',False):
            if vals.get('current_street1',False):
                vals.update({'permanent_street1':vals.get('current_street1',False)})

            if vals.get('current_street2',False):
                vals.update({'permanent_street2':vals.get('current_street2',False)})

            if vals.get('current_city',False):
                vals.update({'permanent_city':vals.get('current_city',False)})

            if vals.get('current_state',False):
                vals.update({'permanent_state':vals.get('current_state',False)})

            if vals.get('current_country',False):
                vals.update({'permanent_country':vals.get('current_country',False)})

            if vals.get('current_zip',False):
                vals.update({'permanent_zip':vals.get('current_zip',False)})

        if vals.get('total_experience_months',False) != '0' or vals.get('total_experience_years',False) != '0':
            if not vals.get('previous_employment',False):
                raise exceptions.ValidationError(_('Please enter previous employment details.'))

        if not vals.get('family_details',False):
            raise exceptions.ValidationError(_('Please enter family details.'))

        return super(nf_candidate_onboarding,self).create(vals)

    @api.multi
    def sumit_details(self):
        for rec in self:
            family_details=[]
            pre_comp_details=[]
            resume=''
            education_certificate=''
            pan_card=''
            aadhar_card=''
            cancel_cheque=''
            salary_slip=''
            salary_slip1=''
            salary_slip2=''
            resignation_acceptance=''
            if rec.family_details:
                for family in rec.family_details:
                    family_details.append((0,False,{'name':family.name,'dob':family.dob,'relation':family.relation,'gender':family.gender,'contact_number':family.contact_number}))
            if rec.previous_employment:
                for pre_emp in rec.previous_employment:
                    pre_comp_details.append((0,False,{'name':pre_emp.name,'designation':pre_emp.designation,'doj':pre_emp.doj,'dol':pre_emp.dol,'ctc':pre_emp.ctc,'reason_leaving':pre_emp.reason_leaving,'currently_working':pre_emp.currently_working}))
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

            values = {'name':rec.name,'full_name':rec.full_name,'gender':rec.gender,'birth_date':rec.birth_date,'religion':rec.religion,'other_religion':rec.other_religion,'disability':rec.disability,'blood_group':rec.blood_group,'marital_status':rec.marital_status,'anniversary_date':rec.anniversary_date,'father_name':rec.father_name,'nationality':rec.nationality and rec.nationality.id,'aadhar_no':rec.aadhar_no,'pan_no':rec.pan_no,'voter_id':rec.voter_id,'passport_no':rec.passport_no,'driving_license_no':rec.driving_license_no,'previous_uan':rec.previous_uan,'previous_pf':rec.previous_pf,'contact_no':rec.contact_no,'personal_email':rec.personal_email,'current_street1':rec.current_street1,'current_street2':rec.current_street2,'current_city':rec.current_city and rec.current_city.id,'current_state':rec.current_state and rec.current_state.id,'current_country':rec.current_country and rec.current_country.id,'current_zip':rec.current_zip,'is_address_same':rec.is_address_same,'permanent_street1':rec.permanent_street1,'permanent_street2':rec.permanent_street2,'permanent_city':rec.permanent_city and rec.permanent_city.id,'permanent_state':rec.permanent_state and rec.permanent_state.id,'permanent_country':rec.permanent_country and rec.permanent_country.id,'permanent_zip':rec.permanent_zip,'emegency_person_name':rec.emegency_person_name,'emergency_contact_no':rec.emergency_contact_no,'emergency_contact_relation':rec.emergency_contact_relation,'bank_account_available':rec.bank_account_available,'account_holder_name':rec.account_holder_name,'account_number':rec.account_number,'bank_name':rec.bank_name,'bank_branch_name':rec.bank_branch_name,'bank_ifsc_code':rec.bank_ifsc_code,'family_details':family_details,'previous_employment':pre_comp_details,'highest_education':rec.highest_education,'degree_id':rec.degree_id and rec.degree_id.id,'college_name':rec.college_name,'university_name':rec.university_name,'unviversity_city':rec.unviversity_city,'graduation_year':rec.graduation_year,'total_experience_years':rec.total_experience_years,'total_experience_months':rec.total_experience_months,'relevant_experience_years':rec.relevant_experience_years,'relevant_experience_months':rec.relevant_experience_months,'resume':resume,'education_certificate':education_certificate,'pan_card':pan_card,'aadhar_card':aadhar_card,'cancel_cheque':cancel_cheque,'salary_slip':salary_slip,'salary_slip1':salary_slip1,'salary_slip2':salary_slip2,'resignation_acceptance':resignation_acceptance,'recruiter_name':rec.recruiter_id,'onboarding_id':rec.id,'state':'Draft','doc_status':'Submitted','other_degree':rec.other_degree}

            cand_rec = self.env['nf.joining.candidate'].sudo().create(values)
            rec.sudo().write({'candidate_id':cand_rec.id,'state':'Submitted'})
            temp_id=self.env['mail.template'].sudo().search([('name','=','Candidate Onboarding')])
            if temp_id:
                temp_id.sudo().send_mail(cand_rec.id)
        return True

    @api.multi
    def update_docs(self):
        for rec in self:
            rec.sudo().write({'state':'Submitted'})
            rec.candidate_id.sudo().write({'doc_status':'Submitted'})
            temp_id=self.env['mail.template'].sudo().search([('name','=','Candidate Doc Submitted')])
            if temp_id:
                temp_id.sudo().send_mail(rec.id)
        return True

    @api.onchange('is_address_same')
    def onchange_address(self):
        if self.is_address_same:
            self.permanent_street1 = self.current_street1
            self.permanent_street2 = self.current_street2
            self.permanent_city= self.current_city.id
            self.permanent_state = self.current_state.id
            self.permanent_country = self.current_country.id
            self.permanent_zip = self.current_zip
            

class nf_candidate_onboarding_family(models.Model):
    _name = 'nf.candidate.onboarding.family'
    _description = 'NF Onboarding Family Details'

    name = fields.Char('Name')
    dob = fields.Date('Date of Birth')
    relation = fields.Selection([('Self','Self'),('Spouse','Spouse'),('Father','Father'),('Mother','Mother'),('Brother','Brother'),('Sister','Sister'),('Son','Son'),('Daughter','Daughter')],'Relation')
    gender = fields.Selection([('male','Male'),('female','Female'),('other','Other')],string="Gender")
    onboarding_id = fields.Many2one('nf.candidate.onboarding','Onboarding')
    contact_number = fields.Char('Contact Number')
    candidate_id = fields.Many2one('nf.joining.candidate','Candidate')

class nf_previous_employment(models.Model):
    _name = 'nf.previous.employment'
    _description = 'NF Previous Employment'

    name = fields.Char('Organization Name')
    designation = fields.Char('Designation')
    doj = fields.Date('Date of Joining')
    dol = fields.Date('Date of Leaving')
    currently_working = fields.Boolean('Currently Working')
    onboarding_id = fields.Many2one('nf.candidate.onboarding','Onboarding')
    ctc = fields.Char('CTC(Per Annum)')
    reason_leaving = fields.Text('Reason For Leaving')
    candidate_id = fields.Many2one('nf.joining.candidate','Candidate')