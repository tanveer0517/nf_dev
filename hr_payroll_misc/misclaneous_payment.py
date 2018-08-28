#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import tools
from odoo import api, fields, models, _
from openerp.osv import osv
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval

class hr_misc_payment(models.Model):
    _name = 'hr.misc.payment'
    
    def default_company(self):
        return self.env['res.company']._company_default_get('hr.misc.payment')
    
    name = fields.Char(string = 'Name')
    pay_mode = fields.Selection([('1','1-Current Payment'),('2','2-Arrear Payment'),('4','4-Current Recovery'),('5','5-Arrear Recovery')],string = 'Payment Mode',required="True")
    salary_rule_id = fields.Many2one('hr.salary.rule',string = 'Payment/Recovery')
    employee_id = fields.Many2one('hr.employee',string = 'Employee')
    doc_no = fields.Char(string = 'Reference Number')
    amount = fields.Float(string = 'Amount',required="True")
    date = fields.Date(string = 'Date',default=fields.Datetime.now)
    date_from = fields.Date(string = 'From Date')
    date_to = fields.Date(string = 'To Date',required="True")
    company_id = fields.Many2one('res.company',string = 'Zone',default = default_company)
    active = fields.Boolean(string = 'Active',default=True)
    payslip_id = fields.Many2one('hr.payslip',string = 'Payslip Reference',ondelete='cascade')
    misc_pay_employee_id = fields.Many2one('hr.misc.payment.employee',string = 'Pay Employee Wise')
    misc_pay_head_id = fields.Many2one('hr.misc.payment.head',string = 'Pay Head Wise')

    @api.onchange('amount')
    def onchange_amount(self):
        for val in self:
            if val.amount > 5000:
               raise osv.except_osv(_('Warning!'), _('Are you Sure to enter amount more than 5000.'))
        
class hr_misc_payment_employee(models.Model):
    _name = 'hr.misc.payment.employee'
    
    name = fields.Char(string = 'Name')
    employee_id = fields.Many2one('hr.employee',string = 'Employee',required="True")
    misc_payment_line = fields.One2many('hr.misc.payment','misc_pay_employee_id',string = 'Misc Pay/Rec Lines')
    
    @api.multi
    def write(self, vals):
        res = super(hr_misc_payment_employee, self).write(vals)
        if 'employee_id' in vals and vals['employee_id']:
            self.env.cr.execute("update hr_misc_payment set employee_id= %d where misc_pay_employee_id=%d" % (self.employee_id.id,self.id))
        return res
        
class hr_misc_payment_head(models.Model):
    _name = 'hr.misc.payment.head'
    
    name = fields.Char(string = 'Name')
    salary_rule_id = fields.Many2one('hr.salary.rule',string = 'Payment/Recovery',required="True")
    misc_payment_line = fields.One2many('hr.misc.payment','misc_pay_head_id',string = 'Misc Pay/Rec Lines')
        
    
    



