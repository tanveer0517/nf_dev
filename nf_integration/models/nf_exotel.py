from odoo import models, fields, api, _
from openerp.osv import osv
from datetime import datetime
import time
from odoo.exceptions import UserError, ValidationError
from openerp import SUPERUSER_ID

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib2 import Request, urlopen
import json,urllib,urllib2
from dateutil.relativedelta import relativedelta
import requests
from pprint import pprint
from lxml import etree

class crm_call_history(models.Model):
    _name = 'crm.call.history'

    call_sid = fields.Char('Call Sid')
    recording_url = fields.Char('Recoding Url')
    start_time = fields.Datetime('Start Time')
    end_time = fields.Datetime('End Time')
    from_number = fields.Char('From Number')
    to_number = fields.Char('To Number')


class ouc_crm_log_call(models.TransientModel):
    _inherit = 'crm.activity.log'

    c_subject = fields.Char(string='Summary/Subject')
    c_to = fields.Char(string='To')
    c_cc = fields.Char(string='CC')
    c_contact_mobile = fields.Char(string="Contact Mobile")
    c_phone =fields.Char(string="Company Landline #")
    c_mobile = fields.Char(string="Company Mobile")
    attachment_ids = fields.Many2many(
        'ir.attachment', 'mail_compose_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')
    customer_number = fields.Char('Calling...')
    call_sid = fields.Char('Call Sid')
    from_number = fields.Char('Dialer Number')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', 'crm.activity.log')]")


    def click_to_call(self, customer_num):
        return True


    def call_contact_mobile(self):
        self.ensure_one()
        #self.click_to_call(self.c_contact_mobile)
        compose_form = self.env.ref('crm.crm_activity_log_view_form', False)
        return {
            'name': _('Log a Call'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.activity.log',
            'res_id': self.id,
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': self.env.context
        }

    def call_company_mobile(self):
        self.ensure_one()
        #self.click_to_call(self.c_mobile)
        compose_form = self.env.ref('crm.crm_activity_log_view_form', False)
        return {
            'name': _('Log a Call'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.activity.log',
            'res_id': self.id,
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': self.env.context
        }

    def call_company_landline(self):
        self.ensure_one()
        #self.click_to_call(self.c_phone)
        compose_form = self.env.ref('crm.crm_activity_log_view_form', False)
        return {
            'name': _('Log a Call'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.activity.log',
            'res_id': self.id,
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': self.env.context
        }

    def log_call(self):
        return True

    def send_email(self):
        return True

    @api.model
    def default_get(self, fields):
        active_model = self.env.context.get('active_model')
        email = ''
        if active_model:
            obj_id = self.env[active_model].browse(self.env.context.get('active_id'))
            rec = super(ouc_crm_log_call, self).default_get(fields)
            if obj_id.c_contact_email == obj_id.email_from:
                email = obj_id.c_contact_email
            else:
                email = obj_id.c_contact_email + ',' +obj_id.email_from
            user_email = self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit=1)
            if not user_email:
                raise ValidationError("Employee is not linked with relative user. Kindly contact to HR.")
            rec.update({'c_contact_mobile': obj_id.c_contact_mobile,
                        'c_phone':obj_id.phone,
                        'c_mobile':obj_id.mobile,
                        'c_subject':obj_id.name,
                        'c_to':email,
                        'c_cc':user_email.work_email,
                        'from_number':user_email.work_phone
                        })
        return rec

    def send_email(self):
        template = self.env['mail.template'].search([('name', '=', self.template_id.name)], limit=1)
        if template:
            template.send_mail(self.id)

    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id:
            self.note = self.template_id.body_html
            object = self
            self.template_id.email_to = self.c_to


