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

class hr_loan(osv.osv):
    _name = 'hr.loan'
    
    def default_company(self):
        return self.env['res.company']._company_default_get('hr.loan')
    
    name = fields.Char(string = 'Name')
    date = fields.Char(string = 'Date',default=fields.Datetime.now)
    type = fields.Many2one('hr.salary.rule',string = 'Loan Type')
    employee_id = fields.Many2one('hr.employee',string = 'Employee Name')
    loan_amt = fields.Float(string = 'Loan Amount')
    installment_amt = fields.Float(string = 'Installment Amount')
    recovery_from = fields.Date(string = 'Recovery Start Date')
    recovery_to = fields.Date(string = 'Recovery End Date')
    loan_payslip_appear = fields.Boolean(string = 'Loan On Payslip')
    recovery_line = fields.One2many('payment.recovery.line','loan_id',string = 'Payment/Recovery Lines')
    company_id = fields.Many2one('res.company',string = 'Zone',default=default_company)
    c_loan_duration = fields.Char(string='Loan Duration')
    

class payment_recovery_line(osv.osv):
    _name = 'payment.recovery.line'
    
    loan_id = fields.Many2one('hr.loan',string = 'Loan Id')
    name = fields.Char(string = 'Name')
    date_from = fields.Date(string = 'From Date')
    date_to = fields.Date(string = 'To Date')
    amount = fields.Float(string = 'Amount')
    