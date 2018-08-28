import math
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import os
from odoo import api, fields, models
from odoo import tools, _
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval

from openerp.osv import osv
import openerp.addons.decimal_precision as dp

class IncomeTax(models.Model):
    _name = "income.tax"

    name = fields.Char(string="Name")
    fin_year_id= fields.Many2one('fin.year.mst', string = 'Financial Year', required=True)
    tax_slabs= fields.One2many('income.tax.line' ,'tax_id',string = 'tax_id')
                
class IncomeTaxLine(models.Model):
    _name = "income.tax.line"
    
    tax_id= fields.Many2one('income.tax',string = "Income Tax")
    name=  fields.Char(string = 'Name')
    amount_from= fields.Float(string = 'Amount From')
    amount_to=  fields.Float(string = 'Amount To')
    income_tax=  fields.Float(string = 'Income Tax(%)')
    minimum_tax= fields.Float(string = 'Minimum Tax(Rs.)')
    surcharge= fields.Float(string = 'Surcharge on IT(%)')
    education_cess= fields.Float(string = 'Education Cess(%)')
                
# income_tax_line()

class employee_tds(models.Model):
    _name = 'employee.tds'
    
    name=fields.Char(string = 'Name')
    fin_year_id=fields.Many2one('fin.year.mst',string = 'Financial Year')
    employee_id=fields.Many2one('hr.employee',string = 'Employee')
    tds_run_id=fields.Many2one('employee.tds.run',string = 'Run Id',copy=False)
    region_id=fields.Many2one('employee.region',string = 'Region')
    tds_basic_amount=fields.Float(string = 'Basic Amount')
    tds_allowance_amount=fields.Float(string = 'Allowance Amount')
    tds_gross_amount=fields.Float(string = 'Gross Amount')
    tds_deduction_amount=fields.Float(string = 'Deduction Amount')
    tds_rebate_amount=fields.Float(string = 'Rebate Amount')
    tds_net_salary_taxable=fields.Float(string = 'Net Taxable Amount')
    net_tds_amount=fields.Float(string = 'Net Income Tax Amount')
    net_tds_paid=fields.Float(string = 'Income Tax Amount Paid')
    professional_tax_paid=fields.Float(string = 'Professional Tax Paid')
    cpf_paid=fields.Float(string = 'CPF Paid')
    gis_paid=fields.Float(string = 'GIS Paid')
    eps_paid=fields.Float(string = 'EPS Paid')
    lic_paid=fields.Float(string = 'LIC Paid')
    vpf_paid=fields.Float(string = 'VPF Paid')
    company_id=fields.Many2one('res.company',string = 'Zone')
    tds_line_ids=fields.One2many('employee.tds.line','employee_tds_id',string = 'Income Tax Lines')
    date_from=fields.Date(string = 'Date From')
    date_to=fields.Date(string = 'Date To')
    professional_tax_monthly=fields.Float(string = 'Professional Tax Monthly')
    cpf_monthly=fields.Float(string = 'CPF Monthly')
    gis_monthly=fields.Float(string = 'GIS Monthly')
    lic_monthly=fields.Float(string = 'LIC Monthly')
    vpf_monthly=fields.Float(string = 'VPF Monthly')
    medical_expense_monthly=fields.Float(string = 'Medical Expense Monthly')
    medical_expense_paid=fields.Float(string = 'Medical Expense Paid')
    total_taxable_amount=fields.Float(string = 'Total Taxable Amount')
    unit_id=fields.Many2one('employee.unit',string = 'Unit')
    state= fields.Selection([
    ('draft', 'Draft'),
    ('done', 'Done'),
     ], string = 'Status', readonly=True, copy=False)
                
class EmployeeTdsLine(models.Model):
    _name = 'employee.tds.line'
    
    name=fields.Char(string = 'Name')
    employee_tds_id=fields.Many2one('employee.tds',string = 'Employee Income Tax',ondelete='cascade')
    total_amount=fields.Float(string = 'Total Amount')
    exempted_amount=fields.Float(string = 'Exempted Amount')
    taxable_amount=fields.Float(string = 'Taxable Amount')
    employee_no=fields.Char(string = 'Employee No')
                
                
class EmployeeTdsRun(models.Model):
    _name = 'employee.tds.run'
    
    @api.multi
    def create(self, vals):
        if 'date_from' in vals and vals['date_from']:
            date_from = vals['date_from']
        if 'company_id' in vals and vals['company_id']:
            company_id = vals['company_id']
            employee = self.search([('company_id', '=', company_id),('date_from', '=', date_from)])
            if employee:
                raise osv.except_osv(_('Warning'), _('Employee Income Tax Batch record already exists! Please update Or Delete the existing record.'))
        return super(employee_tds_run, self).create(vals)
    
    @api.multi
    def compute_tax(self):
        for tds in self:
            a = int(tds.company_id)
            
            date_from = "'"+ tds.date_from +"'"
            date_to = "'"+ tds.date_to +"'"
            self.env.cr.execute("SELECT(c_tds(%s,%s,%s,%s,%s))",(date_from,date_to,a,'',2));
            res = self.env.cr.fetchall()
            tds.write({'message': 'Income Tax computed successfully!'})
        return res
    
    
    name=fields.Char(string = 'Name',required='True')
    tds_ids=fields.One2many('employee.tds','tds_run_id',string = 'Income Tax')
    state= fields.Selection([
    ('draft', 'Draft'),
    ('done', 'Done'),
     ], string = 'Status', default="draft" , readonly=True, copy=False)
    date_from=fields.Date(string = 'Date From',required='True')
    date_to=fields.Date(string = 'Date To',required='True')
    company_id=fields.Many2one('res.company',string = 'Zone')
    message=fields.Char(string = 'Message',readonly='True')
                
    _defaults = {
                'state': 'draft',
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'date_to': lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                 }
    
    @api.multi
    def confirm_sheet(self, cr, uid, ids, context=None):
        for tds in self:
            if not tds.message:
                raise osv.except_osv(_('Invalid Action!'), _('Please Compute Income Tax First'))
        return self.write({'state': 'done'})
    
    @api.multi
    def unlink(self):
        for tds_run in self:
            if tds_run.state not in  ['draft']:
                raise osv.except_osv(_('Warning!'),_('You cannot delete a income tax batch which is not draft!'))
        return super(employee_tds_run, self).unlink()  

