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

class hr_employee_referral(models.Model):

    _name = "hr.employee.referral"
    _description="Employee Referral"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char("Reference Number")
    referred_by = fields.Many2one('hr.employee', string='Referred By')
    department = fields.Many2one('hr.department','Department',track_visibility='onchange')
    job_title = fields.Many2one('hr.job','Job Position',track_visibility='onchange')
    resume = fields.Binary("Resume")
    state = fields.Selection([('Draft','Draft'),
            ('Reference Sent','Reference Sent '),
            ('Selected','Selected'),
            ('Joined','Joined'),
            ('Did Not Join','Did Not Join'),
            ('Rejected','Rejected')],'Status',default='Draft',track_visibility='onchange')
    joining_date = fields.Date("Joining Date")
    approval_by = fields.Many2one('hr.employee', string='Approved/ Rejected By')
    candidate_name = fields.Char('Candidate Name*')
    candidate_contact_number = fields.Char('Candidate Contact Number*')
    candidate_email_id = fields.Char('Candidate Email*')
    candidate_experience = fields.Char('Candidate Experience* (in Years)')
    candidate_other = fields.Text("Candidate Other Info")
    nf_curr_ctc = fields.Float("Current CTC (Per Year)")
    nf_expected_ctc = fields.Float("Expected CTC (Per Year)")
    nf_curr_designation = fields.Char("Current Designation")
    employee_email = fields.Char("Employee Email",size=200)
    filename = fields.Char("Filename")
    assign_to = fields.Many2one('hr.employee','Assign To',track_visibility='onchange')
    referred_date = fields.Date('Referred Date',default=fields.datetime.now())
    selected_feedback = fields.Text('Selected Feedback',track_visibility='onchange')
    joined_feedback = fields.Text('Joined Feedback',track_visibility='onchange')
    not_joined_feedback = fields.Text('Not Joined Feedback',track_visibility='onchange')
    rejected_feedback = fields.Text('Rejected Feedback',track_visibility='onchange')
    ref_notification = fields.Selection([('3','3 Months'),('6','6 Months')],'Notification')
    payout_status = fields.Selection([('Yes','Yes'),('No','No')],'Payout Status',track_visibility='onchange')
    payout_date = fields.Date('Payout Date',track_visibility='onchange')
    payout_amount = fields.Float('Payout Amount',track_visibility='onchange')
    assign_date = fields.Date('Assign Date')
    payout = fields.Boolean('Payout Done')

    @api.multi
    def send_to_reference(self):
        current_date=time.strftime('%Y-%m-%d')
        for rec in self:
            #  trigger a mail
            temp1=self.env['mail.template'].search([('name', '=', 'Referral Request to Referrer')], limit = 1)
            if temp1:
                temp1.send_mail(rec.id)
            temp2=self.env['mail.template'].search([('name', '=', 'Referral Request to HR Team')], limit = 1)
            if temp2:
                temp2.send_mail(rec.id)
            rec.write({'state': 'Reference Sent','referred_date':current_date})
        return True

    @api.multi
    def joined_request(self):
        for rec in self:
            emp_ids = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)])
            if emp_ids:
                emp_ids = emp_ids[0]
            else:
                raise UserError(_('Your login is not in the Employee list. Please contact HR.'))
                
            if not rec.joining_date:
                raise UserError(_("Please add Joining Date before clicking on Joined."))
            if not rec.joined_feedback:
                raise UserError(_("Please add Joined Feedback before clicking on Joined."))
            #  trigger a mail
            temp=self.env['mail.template'].search([('name', '=', 'Referral Request Joined')], limit = 1)
            if temp:
                temp.send_mail(rec.id)

            rec.write({'state': 'Joined','approval_by':emp_ids.id})
        return True

    @api.multi
    def not_joined(self):
        for rec in self:
            if not rec.not_joined_feedback:
                raise UserError(_("Please add Not Joined Feedback before clicking on Not Joined."))
            rec.write({'state': 'Did Not Join'})
        return True

    @api.multi
    def selected_request(self):
        for rec in self:
            if not rec.job_title:
                raise UserError(_("Please add Job Position for which the candidate has been selected before clicking on Selected."))
            if not rec.selected_feedback:
                raise UserError(_("Please add Selected Feedback before clicking on Selected."))
            rec.write({'state': 'Selected'})
        return True

    @api.multi
    def reject_request(self):
        for rec in self:
            emp_ids = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)])
            if emp_ids:
                emp_ids = emp_ids[0]
            else:
                raise UserError(_("Your login is not in the Employee list. Please contact HR"))
            if not rec.rejected_feedback:
                raise UserError(_("Please add Rejected Feedback before clicking on Rejected."))
            rec.write({'state': 'Rejected','approval_by':emp_ids.id})
        return True

    @api.multi
    def payout_done(self):
        for rec in self:
            rec.write({'payout': True})
        return True

    @api.model
    def create(self,vals):
        fname=vals.get('filename')
        if fname:
            if '.doc' not in fname:
                if '.docx' not in fname:
                    if '.pdf' not in fname:
                        raise UserError('Please upload resume in doc, docx or pdf format only.')
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.referral') or '-'
        rec_id = super(hr_employee_referral,self).create(vals)
        rec_id.send_to_reference()
        return rec_id

    @api.multi
    def write(self,vals):
        for rec in self:
            temp=False
            filename=rec.filename
            fname=vals.get('filename') or filename
            if fname:
                if '.doc' not in fname:
                    if '.docx' not in fname:
                        if '.pdf' not in fname:
                            raise UserError('Please upload resume in doc, docx or pdf format only.')
            if vals.get('assign_to'):
                current_date=time.strftime('%Y-%m-%d')
                vals.update({'assign_date':current_date})
                temp=self.env['mail.template'].search([('name', '=', 'Referral Request to Assignee')], limit = 1)

            super(hr_employee_referral,self).write(vals)
            if temp:
                temp.send_mail(rec.id)
        
        return True

    @api.model
    def default_get(self,fields):
        res=super(hr_employee_referral,self).default_get(fields)
        hr_obj=self.env['hr.employee']
        hr_id=hr_obj.sudo().search([('user_id','=',self.env.uid)])
        res.update({'referred_by':hr_id.id,'employee_email':hr_id.work_email})

        return res

    @api.onchange('referred_by')
    def onchange_employee(self):
        value={}
        if self.referred_by:
            self.employee_email=self.referred_by.work_email or ''


    @api.model
    def automated_ref_notifications(self):
        curr_date = datetime.today().strftime("%Y-%m-%d")
        for rec in self.search([('state','=','Joined')]):
            if rec.joining_date and rec.ref_notification:
                ref_joining_date = datetime.strptime(rec.joining_date, '%Y-%m-%d')
                notification_date = ref_joining_date + relativedelta(months=int(rec.ref_notification))
                if str(notification_date)[0:10] == str(curr_date):
                    temp=self.env['mail.template'].search([('name','=','Referral Notification')])
                    temp.send_mail(rec.id)
        return True
