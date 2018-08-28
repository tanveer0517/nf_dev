from odoo import api, fields, models, _
from odoo import exceptions
from odoo.exceptions import ValidationError
import time
from odoo.fields import Date
import collections
import datetime
from datetime import timedelta,datetime,date
import requests
import json
import base64
import smtplib
from dateutil import relativedelta

class employee_transfer(models.Model):
    _name = 'employee.transfer'
    _description = 'Employee Transfer'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee','Employee')
    work_email = fields.Char('Work Email')
    manager_id = fields.Many2one('hr.employee','Current Manager')
    new_manager_id = fields.Many2one('hr.employee','New Manager')
    document_name = fields.Char('Document Name')
    document = fields.Binary('Approval Document',help="Attach needed document to support the request.")
    state = fields.Selection([('Draft','Draft'),('Submitted','Submitted'),('Approved By Manager','Approved By Manager'),('Approved By New Manager','Approved By New Manager'),('Rejected','Rejected')],'State',default='Draft')

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.work_email = self.employee_id.work_email
            self.manager_id = self.employee_id.parent_id and self.employee_id.parent_id.id or False

    @api.model
    def create(self,vals):
        if vals.get('employee_id',False):
            emp_rec = self.env['hr.employee'].sudo().search([('id','=',vals.get('employee_id',False))])
            if emp_rec:
                vals.update({'work_email':emp_rec.work_email,'manager_id':emp_rec.parent_id and emp_rec.parent_id.id or False})
        return super(employee_transfer,self).create(vals)

    @api.multi
    def submit_manager(self):
        for rec in self:
            rec.write({'state': 'Submitted'})
            temp_id=self.env['mail.template'].sudo().search([('name','=','Employee Transfer Submit')])
            if temp_id:
                temp_id.sudo().send_mail(rec.id)
        return True

    @api.multi
    def approve_manager(self):
        for rec in self:
            if rec.manager_id and rec.manager_id.user_id and rec.manager_id.user_id.id == self.env.uid:
                rec.write({'state': 'Approved By Manager'})
                temp_id=self.env['mail.template'].sudo().search([('name','=','Employee Transfer Approved By Manager')])
                if temp_id:
                    temp_id.sudo().send_mail(rec.id)
            else:
                raise ValidationError("Sorry, only the manager of this employee can approve it.")
        return True

    @api.multi
    def approve_new_manager(self):
        for rec in self:
            if rec.new_manager_id and rec.new_manager_id.user_id and rec.new_manager_id.user_id.id == self.env.uid:
                rec.write({'state': 'Approved By New Manager'})
                rec.employee_id.sudo().write({'parent_id':rec.new_manager_id and rec.new_manager_id.id or False})
                temp_id=self.env['mail.template'].sudo().search([('name','=','Employee Transfer Approved By New Manager')])
                if temp_id:
                    temp_id.sudo().send_mail(rec.id)
            else:
                raise ValidationError("Sorry, only the new manager of the employee can approve it.")
        return True

    @api.multi
    def reject_transfer(self):
        for rec in self:
            manager_ids=[]
            if rec.manager_id and rec.manager_id.user_id:
                manager_ids.append(rec.manager_id.user_id.id)
            if rec.new_manager_id and rec.new_manager_id.user_id:
                manager_ids.append(rec.new_manager_id.user_id.id)
            if self.env.uid in manager_ids:
                rec.write({'state': 'Rejected'})
                temp_id=self.env['mail.template'].sudo().search([('name','=','Employee Transfer Rejected')])
                if temp_id:
                    temp_id.sudo().send_mail(rec.id)
            else:
                raise ValidationError("Sorry, only the manager and the new manager of the employee can reject it.")
        return True