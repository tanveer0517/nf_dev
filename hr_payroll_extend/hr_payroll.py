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
import os
import psycopg2
import calendar
from datetime import date
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

import time
import datetime
from datetime import datetime, timedelta, date
import dateutil.relativedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from odoo.addons import decimal_precision as dp
import csv

class HrPayscale(models.Model):
    _name = 'hr.payscale'
   
    name=fields.Char('Name')
    code=fields.Char('Code')
    amount_from=fields.Float('Pay Band From')
    amount_to=fields.Float('Pay Band To')
    grade_pay=fields.Float('Grade pay')
                
    
class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    
    rule_type=fields.Selection([('I', 'Internal Saving'),('S', 'Saving'),('L', 'Loan'),('D','IT Deduction')], "Rule Type")
    frequency=fields.Selection([('R','Regular'),('NR','Non Regular')], "Frequency")              
    saving_category_id=fields.Many2one('saving.category','Saving Category' )
    gl_code=fields.Char('GL Code')
    type= fields.Selection([('Y', 'Fully Taxable'),('N', 'Fully Non-Taxable'), ('P', 'Partly Taxable')], "Taxable Indicator")
    limit_based_on= fields.Selection([('Y', 'Yearly Amount'),('M', 'Monthly Amount'), ('Q', 'Quarterly Amount')], "Non Taxable Limit based on")
    limit=fields.Float("Non Taxable Limit(Rs.)")
    saving_rebate= fields.Selection([('I', 'Deductible from Income'),('T', 'Rebate on Tax')], "Saving Rebate")
    rebate_limit= fields.Float('Rebate Limit')
     
class hr_payslip_line(models.Model):
    _inherit = 'hr.payslip.line'
    
    pay_mode=fields.Selection([('1','1-Current Payment'),('2','2-Arrear Payment'),('4','4-Current Recovery'),('5','5-Arrear Recovery')],'Payment Mode')
                
                 

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
        
    region_id=fields.Many2one('employee.region','Region')
    unit_id=fields.Many2one('employee.unit','Unit')
    tds_id=fields.Many2one('employee.tds','Tax Reference')
    rate_of_pay=fields.Float('Monthly Salary')
    location_id=fields.Many2one('hr.location','Branch')
    department_id=fields.Many2one('hr.department','Department')
    job_title=fields.Many2one('hr.job','Designation')

    # line_ids=fields.One2many('hr.payslip.line', 'slip_id', 'Payslip Lines', readonly=True,
    #                           states={'draft': [('readonly', False)]}),

    #     _defaults = {
#         'date_from': lambda *a: time.strftime('%Y-%m-01'),
#         'date_to': lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
#         'state': 'draft',
#         'credit_note': False,
#                 'company_id': lambda self, cr, uid, context:
#                 self.pool.get('res.users').browse(cr, uid, uid,
#                     context=context).company_id.id,
#     }

    @api.model
    def nf_generate_payslips(self):
        value={}
        cr=self.env.cr
        empolyee_obj = self.env['hr.employee']
        contract_obj = self.env['hr.contract']
        nf_hr_pay = self.env['hr.payslip']
        # Getting all Active Employees
        cr.execute("select emp.id,emp.emp_id from hr_employee emp,resource_resource res where emp.resource_id=res.id and res.active='t'")
        emp_ids = cr.dictfetchall()
        # nf_curr_date = date.today()
        #Previous Month date
        # minus1month = nf_curr_date - dateutil.relativedelta.relativedelta(months=1)
        #End Date of Previous Month
        # end_date = minus1month - dateutil.relativedelta.relativedelta(day=1, months=-1, days=+1)
        #Start Date of Previous Month
        # start_date = minus1month -  dateutil.relativedelta.relativedelta(day=1)

        i=0
        while i<len(emp_ids):
            emp_id=emp_ids[i]['id']
            employee_id = empolyee_obj.browse(emp_id)
            emp_name = employee_id.name
            company_id =  employee_id.company_id.id
            # cr.execute("select id,struct_id,date_start,date_end from hr_contract where c_active='t' and employee_id=%s",(emp_id,))
            contract_det = contract_obj.search([('employee_id','=',emp_id),('c_active','=',True)],limit=1)
            if contract_det:
                contract_id=contract_det.id
                struct_id= contract_det.struct_id.id
                start_date = contract_det.date_start
                end_date = contract_det.date_end
                strin = datetime.strptime(end_date,'%Y-%m-%d').strftime('%B-%Y')
                name =  'Salary Slip of ' + emp_name + ' for ' + strin
                pay_details = nf_hr_pay.sudo().create({'employee_id':emp_id, 'contract_id':contract_id, 'struct_id':struct_id, 'date_from':start_date, 'date_to':end_date, 'name':str(name), 'company_id':company_id })
                pay_details.compute_sheet()
            else:
                print "no payroll"
            i=i+1
        return True

    @api.model
    def compute_current_payslips(self):
        value={}
        self.env.cr.execute("select pl.id from hr_payslip pl, hr_contract ct where pl.contract_id=ct.id and ct.c_active='t'")
        payslip_ids = self.env.cr.dictfetchall()
        i=0
        while i<len(payslip_ids):
            payslip_id = payslip_ids[i]['id']
            payslilp_det = self.env['hr.payslip'].browse(payslip_id)
            payslilp_det.compute_sheet()
            i=i+1
        return True

    
    @api.model
    def create(self, vals):
        if 'date_from' in vals and vals['date_from']:
            date_from = vals['date_from']
        if 'employee_id' in vals and vals['employee_id']:
            employee_id = vals['employee_id']
            employee = self.search([('employee_id', '=', employee_id),('date_from', '=', date_from)])
            if employee:
                raise UserError(_('Employee Payslip record already exists! Please update the existing record.'))
        return super(HrPayslip, self).create(vals)

    @api.model
    def compute_salary(self):
        leave_obj =self.env['hr.payleave']
        contract_obj =self.env['hr.contract']
        misc_pool =self.env['hr.misc.payment']
        days=0
        days1=0
        res1 = {}
        res2 = {}
        res3 = {}
        res4 = {}
        res5 = {}
        res6 = {}
        res7 = {}
        res8 = {}
        res9 = {}
        res10 = {}
        res11 = {}
        res12 = {}
        res13 = {}
        res14 = {}
        res15 = {}
        res16 = {}
        
        basic=0.0
        da=0.0
        hra=0.0
        child_ed_allowance=0.0
        vehi_conveyence_allow=0.0
        electricity_allow=0.0
        entertain_allow=0.0
        hard_soft_fur=0.0
        lunch_dinner_coup=0.0
        prof_up_allow=0.0
        medical_allow=0.0
        uniform_fit_allow=0.0
        meal_coupon_allow=0.0
        washing_allow=0.0
        spa=0.0
        days=0.0
        for payslip in self:
            days=0.0
            days1=0.0
            pay_start = datetime.strptime(payslip.date_from, '%Y-%m-%d').date()
            pay_end = datetime.strptime(payslip.date_to, '%Y-%m-%d').date()
            month = pay_start.month
            leave_start = (pay_start - relativedelta.relativedelta(months=2,days=-12))
            leave_end = (pay_start - relativedelta.relativedelta(months=1,days=-11))
            for leave in leave_obj.search([('from_date', '>=', leave_start),('from_date', '<=', leave_end),('employee_no', '=', payslip.employee_id.employee_no),('record_type', '=', 'C'),('txn_type', '=', 'C'),('leave_type', '=' , 'EOLN')]):
                for leave_pool in leave:
                    days += leave_pool.no_of_days
            for leave1 in leave_obj.search([('from_date', '>=', leave_start),('from_date', '<=', leave_end),('employee_no', '=', payslip.employee_id.employee_no),('record_type', '=', 'C'),('txn_type', '=', 'C'),('leave_type', '=' , 'HPL')]):
                for leave_pool1 in leave1:
                    days1 += leave_pool1.no_of_days/2
            for contract in contract_obj.search([('employee_id', '=', payslip.employee_id.id)]):
                for contract_pool in contract:
                    basic=((contract_pool.wage+contract_pool.grade_pay)/30)*(days+days1)
                    a=self._cr.execute("SELECT rate from da_rates WHERE effective_from = (SELECT MAX(effective_from) from da_rates)");
                    c = self._cr.fetchall()
                    list = [float(i[0]) for i in c]
                    data = 0.0
                    if list:
                        data = list[0]
                    da=basic*data/100
                    hra=basic*payslip.employee_id.location_id.hra_rates/100
                    res1={
                         'employee_id':payslip.employee_id.id,
                         'amount': round(basic),
                         'pay_mode':'2',
                         'doc_no':'Leave Conversion',
                         'salary_rule_id':'463',
                         'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                         'company_id':'1',
                         'payslip_id':payslip.id
                         }
                    res2={
                         'employee_id':payslip.employee_id.id,
                         'amount': round(da),
                         'pay_mode':'2',
                         'doc_no':'Leave Conversion',
                         'salary_rule_id':'464',
                         'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                         'company_id':'1',
                         'payslip_id':payslip.id
                         }
                   
                    if contract_pool.eligible_for_hra==True:
                        res3={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(hra),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'477',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.child_ed_allow==True:
                        if payslip.employee_id.benefits_grade_id.cadre_id.name=='S':
                            child_ed_allowance = basic*20/100
                        else:
                            child_ed_allowance = basic*10/100
                        res4={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(child_ed_allowance),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'512',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.vehi_conveyence_allow==True:
                        vehi_conveyence_allow = basic*20/100
                        res5={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(vehi_conveyence_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'494',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.electricity_allow==True:
                        if payslip.employee_id.benefits_grade_id.cadre_id.name in ('E','S','MD'):
                            electricity_allow = basic*10/100
                        res6={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(electricity_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'496',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.entertain_allow==True:
                        if payslip.employee_id.benefits_grade_id.cadre_id.name in ('E','MD'):
                            entertain_allow = basic*5/100
                        res7={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(entertain_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'469',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.hard_soft_fur==True:
                        if payslip.employee_id.benefits_grade_id.cadre_id.name in ('E','MD'):
                            hard_soft_fur = basic*10/100
                        res8={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(hard_soft_fur),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'495',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.lunch_dinner_coup==True:
                        lunch_dinner_coup = basic*5/100
                        res9={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(lunch_dinner_coup),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'498',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.prof_up_allow==True:
                        if payslip.employee_id.benefits_grade_id.cadre_id.name in ('E','S'):
                            prof_up_allow = basic*5/100
                        elif payslip.employee_id.benefits_grade_id.cadre_id.name == 'MD':
                            prof_up_allow = basic*10/100
                        res10={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(prof_up_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'493',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.medical_allow==True:
                        medical_allow = basic*10/100
                        res11={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(medical_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'513',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.uniform_fit_allow==True:
                        if payslip.employee_id.benefits_grade_id.cadre_id.name=='W':
                            uniform_fit_allow = basic*5/100
                        else:
                            uniform_fit_allow = basic*10/100
                        res12={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(uniform_fit_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'497',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.meal_coupon_allow==True:
                        meal_coupon_allow = basic*5/100
                        res13={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(meal_coupon_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'503',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.washing_allow==True:
                        if payslip.employee_id.benefits_grade_id.cadre_id.name == 'W':
                            washing_allow = basic*5/100
                        res14={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(washing_allow),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'510',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
                    if contract_pool.cafeteria_aggregate<50:
                        per = 50-contract_pool.cafeteria_aggregate
                        if payslip.employee_id.pattern == 'IDA':
                            spa = basic*per/100
                        res15={
                             'employee_id':payslip.employee_id.id,
                             'amount': round(spa),
                             'pay_mode':'2',
                             'doc_no':'Leave Conversion',
                             'salary_rule_id':'492',
                             'date_to':str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                             'company_id':'1',
                             'payslip_id':payslip.id
                              }
            if basic>0:
                misc_id=misc_pool.create(res1)
            if da>0:
                misc_id=misc_pool.create(res2)
            if hra>0:
                misc_id=misc_pool.create(res3)
            if child_ed_allowance>0:
                misc_id=misc_pool.create(res4)
            if vehi_conveyence_allow>0:
                misc_id=misc_pool.create(res5)
            if electricity_allow>0:
                misc_id=misc_pool.create(res6)
            if entertain_allow>0:
                misc_id=misc_pool.create(res7)
            if hard_soft_fur>0:
                misc_id=misc_pool.create(res8)
            if lunch_dinner_coup>0:
                misc_id=misc_pool.create(res9)
            if prof_up_allow>0:
                misc_id=misc_pool.create(res10)
            if medical_allow>0:
                misc_id=misc_pool.create(res11)
            if uniform_fit_allow>0:
                misc_id=misc_pool.create(res12)
            if meal_coupon_allow>0:
                misc_id=misc_pool.create(res13)
            if washing_allow>0:
                misc_id=misc_pool.create(res14)
            if spa>0:
                misc_id=misc_pool.create(res15)
        return True

    @api.multi          
    def compute_income_tax(self):
        for tds in self:
            if tds.tds_id:
                raise UserError(_('Please Compute Sheet First'))
            if not tds.line_ids:
                raise UserError(_('Please Compute Sheet First'))
            else:
                date_from = "'"+ tds.date_from +"'"
                print"date_from",date_from            
                date_to = "'"+ tds.date_to +"'"
                print"date_to",date_to
                if not tds.employee_id.employee_no:
                    raise ValidationError("Employee No. is Empty in Employee Record")
                self._cr.execute("SELECT(c_tds(%s,%s,%s,%s,%s))",(date_from,date_to,0,tds.employee_id.employee_no,1));
                res = self._cr.fetchall()
        return res
    

         
    @api.multi       
    def hr_verify_sheet(self):
        slip_line_pool = self.env['hr.payslip.line']
        saving_obj = self.env['employee.saving']
        med_amt_pay=0.0
        med_amt_ded=0.0
        med_amt_ytm=0.0
        total_med_amt=0.0
        for payslip in self:
            emp=int(payslip.employee_id.employee_no)
            if not payslip.line_ids:
                raise UserError(_('Please Compute Sheet And Compute Tax First'))
            for me in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=', '215'),('pay_mode', '=' , ('1','2'))]):
                for line_pool in me:
                    med_amt_pay +=line_pool.total
            for me_ded in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=', '215'),('pay_mode', '=' , ('4','5'))]):
                for line_pool_ded in me_ded:
                    med_amt_ded +=line_pool_ded.total
            for saving in saving_obj.search([('employee_id', '=', payslip.employee_id.id)]):
                for saving_pool in saving:
                    med_amt_ytm =saving_pool.medical_exp_reimbursement
                    total_med_amt=med_amt_ytm+med_amt_pay-med_amt_ded
                    saving_pool.write({'medical_exp_reimbursement': total_med_amt})

        #self.compute_sheet(cr, uid, ids, context)
        return self.write({'state': 'verify'})
    
    @api.multi
    def unlink(self):
        tds_pool = self.env['employee.tds']
        for payslip in self:
            emp=int(payslip.employee_id.employee_no)
            tds_id = tds_pool.search([('id', '=', payslip.tds_id.id)])
            if payslip.state in  ['draft','cancel']:
                if tds_id:
                    tds_id.unlink()
        if any(self.filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))
        return super(HrPayslip, self).unlink()
    

    
#     @api.multi
#     def compute_sheet(self):
#         slip_line_pool = self.env['hr.payslip.line']
#         tds_pool = self.env['employee.tds']
#         sequence_obj = self.env['ir.sequence']
#         payment_obj = self.env['hr.misc.payment']
#         input_obj = self.env['hr.payslip.input']
#         res={}
#         
#         for payslip in self:
#             pay_id=payment_obj.search([('payslip_id', '=', payslip.id)])
#             #delete old misslenous payment lines
#             pay_id.unlink()
#             emp=int(payslip.employee_id.employee_no)
#             compute_sal=self.compute_salary()
#             pay_date = datetime.strptime(payslip.date_from, '%Y-%m-%d').date()
#             month = pay_date.month
#             number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
#             #old income tax
#             tds_id = tds_pool.search([('id', '=', payslip.tds_id.id)])
#             if tds_id:
#                 tds_id.unlink()
#                 payslip.write({'tds_id': ''})
#             #delete old payslip lines
#             payslip.line_ids.unlink()
#             # set the list of contract for which the rules have to be applied
#             # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
#             contract_ids = payslip.contract_id.ids or \
#                 self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
#             lines = [(0, 0, line) for line in self.get_payslip_lines(contract_ids, payslip.id)]
#             misc_payment_lines = [(0,0,misc_payment_line) for misc_payment_line in self.get_misc_payment_lines(contract_ids, payslip.id)]
#             payslip.write({'line_ids': lines, 'number': number})
#             payslip.write({'line_ids': misc_payment_lines, 'number': number})
#             #calculate and update professional tax in payslip line
#             pro_obj=self.env['hr.professional.tax']
#             tax_amount = 0.0
#             #gross_amount = 0.0
#             basic_amount = 0.0
#             basic_amount1 = 0.0
#             basic_amount2 = 0.0
#             basic_amount3 = 0.0
#             basic_amount4 = 0.0
#             basic_amount_pf = 0.0
#             da_amount1 = 0.0
#             da_amount2 = 0.0
#             da_amount3 = 0.0
#             da_amount4 = 0.0
#             da_amount_pf = 0.0
#             #basic pay calculate            
#             for line_slip4 in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=','101')]):
#                 for line_pool4 in line_slip4:
#                     if line_pool4.code == '101' and line_pool4.pay_mode == '1':
#                         basic_amount1 += line_pool4.total
#                     if line_pool4.code == '101' and line_pool4.pay_mode == '2':
#                         basic_amount2 += line_pool4.total
#                     if line_pool4.code == '101' and line_pool4.pay_mode == '4':
#                         basic_amount3 += line_pool4.total
#                     if line_pool4.code == '101' and line_pool4.pay_mode == '5':
#                         basic_amount4 += line_pool4.total
#                     basic_amount_pf = (basic_amount1 + basic_amount2)-(basic_amount3 + basic_amount4)
#             
#             #Compute Dearness Allowance
#             for line_slip_da in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=','102')]):
#                 for line_pool_da in line_slip_da:
#                     if line_pool_da.code == '102' and line_pool_da.pay_mode == '1':
#                         da_amount1 += line_pool_da.total
#                     if line_pool_da.code == '102' and line_pool_da.pay_mode == '2':
#                         da_amount2 += line_pool_da.total
#                     if line_pool_da.code == '102' and line_pool_da.pay_mode == '4':
#                         da_amount3 += line_pool_da.total
#                     if line_pool_da.code == '102' and line_pool_da.pay_mode == '5':
#                         da_amount4 += line_pool_da.total
#                     da_amount_pf = (da_amount1 + da_amount2)-(da_amount3 + da_amount4)
#                     
#             #Compute Provident Fund=====>
#             for line_slip_pf in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=','501')]):
#                 for line_pool_pf in line_slip_pf:
#                     if payslip.contract_id.nps==False:
#                         if payslip.employee_id.pattern == 'IDA' and payslip.contract_id.special_pf_amount == 0 and payslip.contract_id.pf_stop_flag<>True:
#                             if payslip.employee_id.employee_type_id.name=='Employee':
#                                 result = round((basic_amount_pf+da_amount_pf)*0.12)
#                                 if line_pool_pf.code == '501' and line_pool_pf.pay_mode=='4': 
#                                     line_pool_pf.amount = result
#                             else:
#                                 if line_pool_pf.code == '501' and line_pool_pf.pay_mode=='4': 
#                                     line_pool_pf.amount = round((basic_amount_pf)*0.0833)
#                         elif payslip.employee_id.pattern == 'CDA' and payslip.contract_id.special_pf_amount == 0 and payslip.contract_id.pf_stop_flag<>True:
#                             if line_pool_pf.code == '501' and line_pool_pf.pay_mode=='4': 
#                                 line_pool_pf.amount = round((basic_amount_pf)*0.0833) 
#                         else:
#                             if line_pool_pf.code == '501' and line_pool_pf.pay_mode=='4': 
#                                 line_pool_pf.amount = round(payslip.contract_id.special_pf_amount)
#                     else:
#                         result = round((basic_amount_pf+da_amount_pf)*0.10)
#                         if line_pool_pf.code == '501' and line_pool_pf.pay_mode=='4':
#                             line_pool_pf.amount = result   
#                             
#             #Compute HRA
#             #compute IRCTC Standard rent recovery
#             for line_slip1 in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=','359')]):
#                 for line_pool1 in line_slip1:
#                     lease_obj = self.env['hr.lease']
#                     rate_obj = self.env['hrr.rates']
#                     res = 0.0
#                     extra_amt = 0.0
#                     sla = 0.0
#                     for lease_id in lease_obj.search([('employee_no','=',payslip.employee_id.employee_no)]):
#                         for lease in lease_id:
#                             if lease:
#                                 if payslip.employee_id.pattern=='IDA' and lease.owner == 'C' and lease.area>0 and lease.from_date <= payslip.date_from and lease.to_date >= payslip.date_from:
#                                         res = basic_amount*0.1
#                                         lease_limit_x = ((payslip.employee_id.benefits_grade_id.payscale_id.amount_from + payslip.employee_id.benefits_grade_id.payscale_id.amount_to)/2)*0.6
#                                         lease_limit_y = ((payslip.employee_id.benefits_grade_id.payscale_id.amount_from + payslip.employee_id.benefits_grade_id.payscale_id.amount_to)/2)*0.45
#                                         lease_limit_z = ((payslip.employee_id.benefits_grade_id.payscale_id.amount_from + payslip.employee_id.benefits_grade_id.payscale_id.amount_to)/2)*0.35
#                                         lease_limit1_x = lease_limit_x*0.1
#                                         lease_limit1_y = lease_limit_y*0.1
#                                         lease_limit1_z = lease_limit_z*0.1
#                                         lease_limit_final_x = lease_limit_x+lease_limit1_x
#                                         lease_limit_final_y = lease_limit_y+lease_limit1_y
#                                         lease_limit_final_z = lease_limit_y+lease_limit1_z
#                                         
#                                         if payslip.employee_id.benefits_grade_id.name not in ('E9','E10') and payslip.employee_id.location_id.type=='X':
#                                             if lease.rent > lease_limit_final_x:
#                                                 extra_amt = lease.rent - lease_limit_final_x
#                                             if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res + extra_amt)
#                                         elif payslip.employee_id.benefits_grade_id.name not in ('E9','E10') and payslip.employee_id.location_id.type=='Y':
#                                             if lease.rent > lease_limit_final_y:
#                                                 extra_amt = lease.rent - lease_limit_final_y
#                                             if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res + extra_amt)
#                                         elif payslip.employee_id.benefits_grade_id.name not in ('E9','E10') and payslip.employee_id.location_id.type=='Z':
#                                             if lease.rent > lease_limit_final_z:
#                                                 extra_amt = lease.rent - lease_limit_final_z
#                                             if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res + extra_amt)
#                                         elif payslip.employee_id.benefits_grade_id.name in ('E9','E10') and lease.special_lease_amount == 0.0:
#                                             if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res)
#                                         else:
#                                             if payslip.employee_id.benefits_grade_id.name in ('E9','E10') and lease.special_lease_amount > 0.0 and lease.special_lease_amount<lease.rent:
#                                                 sla = lease.rent - lease.special_lease_amount
#                                             if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res + sla)
#                                 elif payslip.employee_id.pattern=='CDA' and lease.owner == 'C' and lease.from_date <= payslip.date_from and lease.to_date >= payslip.date_from:
#                                     for rate_id in rate_obj.search([('area_from','<=',lease.area),('area_to','>=',lease.area)]):
#                                         for rate in rate_id:
#                                             res = rate.amount
#                                             lease_limit = ((payslip.employee_id.benefits_grade_id.payscale_id.amount_from + payslip.employee_id.benefits_grade_id.payscale_id.amount_to)/2)*0.6
#                                             lease_limit1 = lease_limit*0.1
#                                             lease_limit_final = lease_limit+lease_limit1
#                                             if lease.rent > lease_limit_final:
#                                                 extra_amt = lease.rent - lease_limit_final
#                                             if lease.special_lease_amount == 0:
#                                                 if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0: 
#                                                     line_pool1.amount = round(res + extra_amt)
#                                             else:
#                                                 if lease.special_lease_amount<lease.rent:
#                                                     sla = lease.rent - lease.special_lease_amount
#                                                 if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0: 
#                                                     line_pool1.amount = round(res + sla)
#                             else:
#                                 if line_pool1.code == '359' and line_pool1.pay_mode == '4' and line_pool1.amount == 0: 
#                                     line_pool1.amount = 0.0
#                                     print"NOIRCTCRECOVERY=====",line_pool1.amount
#                                     
#             #Compute House Rent Recovery=====>
#             for line_slip1 in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=','335')]):
#                 for line_pool1 in line_slip1:
#                     lease_obj = self.env['hr.lease']
#                     rate_obj = self.env['hrr.rates']
#                     res = 0.0
#                     extra_amt = 0.0
#                     sla = 0.0
#                     for lease_id in lease_obj.search([('employee_no','=',payslip.employee_id.employee_no)]):
#                         for lease in lease_id:
#                             if lease:
#                                 if payslip.employee_id.pattern=='IDA' and lease.owner<>'C' and lease.from_date <= payslip.date_from and lease.to_date >= payslip.date_from:
#                                         res = basic_amount*0.1
#                                         lease_limit_x = ((payslip.employee_id.grade_id.payscale_id.amount_from + payslip.employee_id.grade_id.payscale_id.amount_to)/2)*0.6
#                                         lease_limit_y = ((payslip.employee_id.grade_id.payscale_id.amount_from + payslip.employee_id.grade_id.payscale_id.amount_to)/2)*0.45
#                                         lease_limit_z = ((payslip.employee_id.grade_id.payscale_id.amount_from + payslip.employee_id.grade_id.payscale_id.amount_to)/2)*0.35
#                                         lease_limit1_x = lease_limit_x*0.1
#                                         lease_limit1_y = lease_limit_y*0.1
#                                         lease_limit1_z = lease_limit_z*0.1
#                                         lease_limit_final_x = lease_limit_x+lease_limit1_x
#                                         lease_limit_final_y = lease_limit_y+lease_limit1_y
#                                         lease_limit_final_z = lease_limit_y+lease_limit1_z
#                                         
#                                         if payslip.employee_id.grade_id.name not in ('E9','E10') and payslip.employee_id.location_id.type=='X':
#                                             if lease.rent > lease_limit_final_x:
#                                                 extra_amt = lease.rent - lease_limit_final_x
#                                             if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res + extra_amt)
#                                         elif payslip.employee_id.grade_id.name not in ('E9','E10') and payslip.employee_id.location_id.type=='Y':
#                                             if lease.rent > lease_limit_final_y:
#                                                 extra_amt = lease.rent - lease_limit_final_y
#                                             if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res + extra_amt)
#                                         elif payslip.employee_id.grade_id.name not in ('E9','E10') and payslip.employee_id.location_id.type=='Z':
#                                             if lease.rent > lease_limit_final_z:
#                                                 extra_amt = lease.rent - lease_limit_final_z
#                                             if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount =round( res + extra_amt)
#                                         elif payslip.employee_id.grade_id.name in ('E9','E10') and lease.special_lease_amount == 0.0:
#                                             if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res)
#                                         else:
#                                             if payslip.employee_id.grade_id.name in ('E9','E10') and lease.special_lease_amount > 0.0 and lease.special_lease_amount<lease.rent:
#                                                 sla = lease.rent - lease.special_lease_amount
#                                             if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0:
#                                                 line_pool1.amount = round(res + sla)
#                                 elif payslip.employee_id.pattern=='CDA' and lease.owner<>'C' and lease.from_date <= payslip.date_from and lease.to_date >= payslip.date_from:
#                                     for rate_id in rate_obj.search([('area_from','<=',lease.area),('area_to','>=',lease.area)]):
#                                         for rate in rate_id:
#                                             res = rate.amount
#                                             lease_limit = ((payslip.employee_id.benefits_grade_id.payscale_id.amount_from + payslip.employee_id.benefits_grade_id.payscale_id.amount_to)/2)*0.6
#                                             lease_limit1 = lease_limit*0.1
#                                             lease_limit_final = lease_limit+lease_limit1
#                                             if lease.rent > lease_limit_final:
#                                                 extra_amt = lease.rent - lease_limit_final
#                                             if lease.special_lease_amount == 0:
#                                                 if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0: 
#                                                     line_pool1.amount = round(res + extra_amt)
#                                             else:
#                                                 if lease.special_lease_amount<lease.rent:
#                                                     sla = lease.rent - lease.special_lease_amount
#                                                 if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0: 
#                                                     line_pool1.amount = round(res + sla)
#                             else:
#                                 if line_pool1.code == '335' and line_pool1.pay_mode == '4' and line_pool1.amount == 0: 
#                                     line_pool1.amount = 0.0
#                                     print"NOHRR=====",line_pool1.amount
#             
#             for each in self:
#                 total = 0.0
#                 total_ded = 0.0
#                 net = 0.0
# 		basic = 0.0
#                 for line in each.line_ids:
#                     if line.category_id.code == 'BASIC':
#                         basic = line.total
#                     if basic == 0.0:
#                        	line.amount = 0.0
#                     if line.category_id.code in ('BASIC','ALW'): 
#                         total += (line.amount*line.rate)/100
#                     if line.category_id.code == 'COMP':
#                         total += line.amount
#                     if line.category_id.code == 'GROSS':
#                         line.amount = total
#                 for line1 in each.line_ids:
#                     if line1.category_id.code == 'DED':
#                         total_ded += (line1.amount*line1.rate)/100
#                     if line1.category_id.code == 'GDED':
#                         line1.amount = total_ded
#                     if line1.category_id.code == 'NET':
#                         line1.amount = total - total_ded
#                         abc = total - total_ded
#                         line1.total = abc
#             #Compute Professional Tax
#             gross_amount = 0.0
#             for line_slip in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=','997')]):
#                 for line_pool in line_slip:
#                     if line_pool.code == '997':
#                         gross_amount = line_pool.total
#             if payslip.employee_id.disability not in ('F','P') :
#                 for line_slip2 in slip_line_pool.search([('slip_id', '=', payslip.id),('code', '=','401')]):
#                     for line_pool2 in line_slip2:
#                         for tax_ids in pro_obj.search([('state_id','=',payslip.employee_id.state_id.id)]):
#                             for tax in tax_ids:
#                                 if tax.half_yearly==True:
#                                     if month>=int(tax.month_from) and month<=int(tax.month_to) and gross_amount*6>=tax.amount_from and gross_amount*6<=tax.amount_to:
#                                         tax_amount = round(tax.pro_tax_amount/6)
#                                         if line_pool2.code == '401' and line_pool2.pay_mode=='4': 
#                                             line_pool2.amount = tax_amount
#                                     else:
#                                         tax_amount = 0.0
#                                 elif tax.gross_annual==True:
#                                     if month>=int(tax.month_from) and month<=int(tax.month_to) and gross_amount*12>=tax.amount_from and gross_amount*12<=tax.amount_to:
#                                         tax_amount = tax.pro_tax_amount
#                                         if line_pool2.code == '401' and line_pool2.pay_mode=='4': 
#                                             line_pool2.amount = tax_amount
#                                     else:
#                                         tax_amount = 0.0
#                                 else:
#                                     if month>=int(tax.month_from) and month<=int(tax.month_to) and gross_amount>=tax.amount_from and gross_amount<=tax.amount_to:
#                                         tax_amount = tax.pro_tax_amount
#                                         if line_pool2.code == '401' and line_pool2.pay_mode=='4': 
#                                             line_pool2.amount = tax_amount
#                                     else:
#                                         tax_amount = 0.0
#             
#             for each in self:
#                 total = 0.0
#                 total_ded = 0.0
#                 net = 0.0
# 		basic = 0.0
#                 for line in each.line_ids:
#                     if line.category_id.code == 'BASIC':
#                         basic = round(line.total)
#                     if basic == 0.0:
#                         line.amount = 0.0
#                     if line.category_id.code in ('BASIC','ALW'): 
#                         total += (line.amount*line.rate)/100
#                     if line.category_id.code == 'GROSS':
#                         line.amount = round(total)
#                     if line.category_id.code == 'COMP':
#                         total += line.amount
#                 for line1 in each.line_ids:
#                     if line1.category_id.code == 'DED':
#                         total_ded += round((line1.amount*line1.rate)/100)
#                     if line1.category_id.code == 'GDED':
#                         line1.amount = round(total_ded)
#                     if line1.category_id.code == 'NET':
#                         line1.amount = round(total - total_ded)
#             self._cr.execute("delete from hr_payslip_line where code not in ('101','381','997','998','999') and total=0.0")
# 
#         return True
    
    @api.model
    def get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                            (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        #we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days, 'inputs': inputs}
        #get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        structure_ids = contracts.get_all_structures()
        #get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                #check if the rule can be applied
                if rule.satisfy_condition(localdict) and rule.id not in blacklist:
                    #compute the amount of the rule
                    amount, qty, rate = rule.compute_rule(localdict)
                    #check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    #set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    #sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    #create/overwrite the rule in the temporary results
                    if rule.category_id.id in (1,2):
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'condition_select': rule.condition_select,
                            'condition_python': rule.condition_python,
                            'condition_range': rule.condition_range,
                            'condition_range_min': rule.condition_range_min,
                            'condition_range_max': rule.condition_range_max,
                            'amount_select': rule.amount_select,
                            'amount_fix': rule.amount_fix,
                            'amount_python_compute': rule.amount_python_compute,
                            'amount_percentage': rule.amount_percentage,
                            'amount_percentage_base': rule.amount_percentage_base,
                            'register_id': rule.register_id.id,
                            'amount': amount,
                            'employee_id': contract.employee_id.id,
                            'quantity': qty,
                            'rate': rate,
                            'pay_mode':'1',
                        }
                    elif rule.category_id.id == 4:
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'condition_select': rule.condition_select,
                            'condition_python': rule.condition_python,
                            'condition_range': rule.condition_range,
                            'condition_range_min': rule.condition_range_min,
                            'condition_range_max': rule.condition_range_max,
                            'amount_select': rule.amount_select,
                            'amount_fix': rule.amount_fix,
                            'amount_python_compute': rule.amount_python_compute,
                            'amount_percentage': rule.amount_percentage,
                            'amount_percentage_base': rule.amount_percentage_base,
                            'register_id': rule.register_id.id,
                            'amount': amount,
                            'employee_id': contract.employee_id.id,
                            'quantity': qty,
                            'rate': rate,
                            'pay_mode':'4',
                            }
                    else:
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'condition_select': rule.condition_select,
                            'condition_python': rule.condition_python,
                            'condition_range': rule.condition_range,
                            'condition_range_min': rule.condition_range_min,
                            'condition_range_max': rule.condition_range_max,
                            'amount_select': rule.amount_select,
                            'amount_fix': rule.amount_fix,
                            'amount_python_compute': rule.amount_python_compute,
                            'amount_percentage': rule.amount_percentage,
                            'amount_percentage_base': rule.amount_percentage_base,
                            'register_id': rule.register_id.id,
                            'amount': amount,
                            'employee_id': contract.employee_id.id,
                            'quantity': qty,
                            'rate': rate,
                        }
                else:
                    #blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return [value for code, value in result_dict.items()]
    
    @api.multi
    def get_misc_payment_lines(self,contract_ids, payslip_id):
        res = {}
        payment_obj = self.env['hr.misc.payment']
        for payslip in self.browse(payslip_id):
            for pay_ids in payment_obj.search([('employee_id','=',payslip.employee_id.id),('date_to','>',payslip.date_from)]):
                for payment in pay_ids:
                    key = str(payment.id) + '-' + str(8)
                    if payment.date_from<=payslip.date_from or payment.date_from is 'null':
                        if payment.pay_mode in ('1','2'):
                            res[key] = {
                                 'name':payment.salary_rule_id.name,
                                 'category_id':2,
                                 'code':payment.salary_rule_id.code,
                                 'pay_mode':payment.pay_mode,
                                 'amount':payment.amount,
                                 'employee_id':payslip.employee_id.id,
                                 'contract_id': payslip.contract_id.id,
                                 'salary_rule_id': payment.salary_rule_id.id,
                                 }
                        else:
                            res[key] = {
                                 'name':payment.salary_rule_id.name,
                                 'category_id':4,
                                 'code':payment.salary_rule_id.code,
                                 'pay_mode':payment.pay_mode,
                                 'amount':payment.amount,
                                 'employee_id':payslip.employee_id.id,
                                 'contract_id': payslip.contract_id.id,
                                 'salary_rule_id': payment.salary_rule_id.id,
                                 }
                        
#        result_misc = [v for a, v in res.items()]
        result_misc = [value for code, value in res.items()]
        return result_misc
        

#    
    @api.model
    def get_worked_day_lines(self, contract_ids, date_from, date_to):
        """
        @param contract_ids: list of contract id
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        def was_on_leave(employee_id, datetime_day):
            day = fields.Date.to_string(datetime_day)
            return self.env['hr.holidays'].search([
                ('state', '=', 'validate'),
                ('employee_id', '=', employee_id),
                ('type', '=', 'remove'),
                ('date_from', '<=', day),
                ('date_to', '>=', day)
            ], limit=1).holiday_status_id.name

        res = []
        # custome code start here
        count = 0.0
        count1 = 0.0
        count2 = 0.0
        count3 = 0.0
        count4 = 0.0
        count5 = 0.0
        count6 = 0.0
        
        count_eol = 0.0
        count1_eol = 0.0
        count2_eol = 0.0
        count3_eol = 0.0
        count4_eol = 0.0
        count5_eol = 0.0
        count6_eol = 0.0
        
        count_cl = 0.0
        count1_cl = 0.0
        count2_cl = 0.0
        count3_cl = 0.0
        count4_cl = 0.0
        count5_cl = 0.0
        count6_cl = 0.0
        
        count_el = 0.0
        count1_el = 0.0
        count2_el = 0.0
        count3_el = 0.0
        count4_el = 0.0
        count5_el = 0.0
        count6_el = 0.0
        
        count_scl = 0.0
        count1_scl = 0.0
        count2_scl = 0.0
        count3_scl = 0.0
        count4_scl = 0.0
        count5_scl = 0.0
        count6_scl = 0.0
        
        count_hl = 0.0
        count1_hl = 0.0
        count2_hl = 0.0
        count3_hl = 0.0
        count4_hl = 0.0
        count5_hl = 0.0
        count6_hl = 0.0
        
        count_com = 0.0
        count1_com = 0.0
        count2_com = 0.0
        count3_com = 0.0
        count4_com = 0.0
        count5_com = 0.0
        count6_com = 0.0
        
        count_sdl = 0.0
        count1_sdl = 0.0
        count2_sdl = 0.0
        count3_sdl = 0.0
        count4_sdl = 0.0
        count5_sdl = 0.0
        count6_sdl = 0.0
        
        count_pat = 0.0
        count1_pat = 0.0
        count2_pat = 0.0
        count3_pat = 0.0
        count4_pat = 0.0
        count5_pat = 0.0
        count6_pat = 0.0
        
        count_mat = 0.0
        count1_mat = 0.0
        count2_mat = 0.0
        count3_mat = 0.0
        count4_mat = 0.0
        count5_mat = 0.0
        count6_mat = 0.0
        
        count_hpl = 0.0
        count1_hpl = 0.0
        count2_hpl = 0.0
        count3_hpl = 0.0
        count4_hpl = 0.0
        count5_hpl = 0.0
        count6_hpl = 0.0
        pay_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        pay_date1 = datetime.strptime(date_to, '%Y-%m-%d').date()
        days_in_month=(pay_date1-pay_date).days + 1    #Total Days In Current Month 

        month = pay_date.month
        pay_date_year = pay_date.year
        day = pay_date1.day
        leave_end_pre = date.today().replace(day=12,month=month,year=pay_date_year)
        print"leave_end_pre",leave_end_pre
        leave_end= leave_end_pre.replace(month=month)
        print"leave_end",leave_end
        leave_start = (leave_end - relativedelta.relativedelta(months=1,days=-1))
        print"leave_start",leave_start
        month1 = leave_start.month
        year = leave_start.year
        if int(month1) in [1,3,5,7,8,10,12]:
                months = 31
        if int(month1) in [4,6,9,11]:
                months = 30
        if int(month1) in [2]:
            if int(year) % 4 == 0:
                months = 29
            else:
                months = 28
        leave_ded_amount = 0.0
        leave_ded_amount1 = 0.0
        leave_ded_amount2 = 0.0
        leave_ded_amount3 = 0.0
        leave_ded_amount4 = 0.0
        leave_ded_amount5 = 0.0 
        leave_ded_amount6 = 0.0
        leave_ded_amount7 = 0.0
        leave_ded_amount8 = 0.0
        leave_ded_amount9 = 0.0
        leave_ded_amount_hpl = 0.0
        leave_ded_amount1_hpl = 0.0
        leave_ded_amount2_hpl = 0.0
        leave_ded_amount3_hpl = 0.0
        leave_ded_amount4_hpl = 0.0
        leave_ded_amount5_hpl = 0.0 
        leave_ded_amount6_hpl = 0.0
        leave_ded_amount7_hpl = 0.0
        leave_ded_amount8_hpl = 0.0
        leave_ded_amount9_hpl = 0.0
        leave_ded_amount_eol = 0.0
        leave_ded_amount1_eol = 0.0
        leave_ded_amount2_eol = 0.0
        leave_ded_amount3_eol = 0.0
        leave_ded_amount4_eol = 0.0
        leave_ded_amount5_eol = 0.0 
        leave_ded_amount6_eol = 0.0
        leave_ded_amount7_eol = 0.0
        leave_ded_amount8_eol = 0.0
        leave_ded_amount9_eol = 0.0
        last_month_leave1=0
        cur_month_leave1=0
        last_month_leave2=0
        cur_month_leave2=0
        last_month_leave3=0
        cur_month_leave3=0
        last_month_leave4=0
        cur_month_leave4=0
        last_month_leave5=0
        cur_month_leave5=0 
        
        last_month_leave1_eol=0
        cur_month_leave1_eol=0
        last_month_leave2_eol=0
        cur_month_leave2_eol=0
        last_month_leave3_eol=0
        cur_month_leave3_eol=0
        last_month_leave4_eol=0
        cur_month_leave4_eol=0
        last_month_leave5_eol=0
        cur_month_leave5_eol=0
         
        last_month_leave1_hpl=0
        cur_month_leave1_hpl=0
        last_month_leave2_hpl=0
        cur_month_leave2_hpl=0
        last_month_leave3_hpl=0
        cur_month_leave3_hpl=0
        last_month_leave4_hpl=0
        cur_month_leave4_hpl=0
        last_month_leave5_hpl=0
        cur_month_leave5_hpl=0
        
        
        days_before = 0
        days_after = 0 
        days_before_tr = 0
        days_after_tr = 0 
        leave_end_previous = leave_start.replace(day=months)
        for contract in self.env['hr.contract'].browse(contract_ids):
            if contract.employee_id.last_promotion_date:
                pr_date = datetime.strptime(contract.employee_id.last_promotion_date, '%Y-%m-%d').date()
                if pr_date>=pay_date and pr_date<=pay_date1:
                    days_before = (pr_date - pay_date).days
                    days_after = (pay_date1 - pr_date).days + 1
            if contract.employee_id.last_transfer_date:
                tr_date = datetime.strptime(contract.employee_id.last_transfer_date, '%Y-%m-%d').date()
                if tr_date>=pay_date and tr_date<=pay_date1:
                    days_before_tr = (tr_date - pay_date).days
                    days_after_tr = (pay_date1 - tr_date).days + 1
            leave_ids = self.env['hr.payleave'].search([('employee_id','=',contract.employee_id.id),('txn_type','=','D'),('record_type','=','L')])
            if leave_ids:
                for leave in leave_ids:
                    from_date = datetime.strptime(leave.from_date, '%Y-%m-%d').date()
                    to_date = datetime.strptime(leave.to_date, '%Y-%m-%d').date()
                    if leave.leave_type.name in ('EOLN','LWP'):
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count += leave.no_of_days
                            if int(contract.increment_month)==month:
                                leave_ded_amount = round((contract.old_wage+contract.grade_pay)/months*count)
                            else:
                                leave_ded_amount = round((contract.wage+contract.grade_pay)/months*count)
                            last_month_leave1=count
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1 += no_days
                            cur_month_leave1=count1
                            leave_ded_amount1 = round((contract.wage+contract.grade_pay)/day*count1)
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            last_month_leave2=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount2 = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount2 = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = (to_date - leave_end_previous).days
                            cur_month_leave2=no_days2
                            leave_ded_amount3 = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count2 = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            last_month_leave3=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount4 = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount4 = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = (leave_end - leave_end_previous).days
                            cur_month_leave3=no_days2
                            leave_ded_amount5 = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count3 = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            last_month_leave4=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount6 = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount6 = round((contract.wage+contract.grade_pay)/months*no_days1)
                            count4 = no_days1
                        elif from_date<leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            last_month_leave4=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount6 = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount6 = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = (to_date - leave_end_previous).days
                            cur_month_leave3=no_days2
                            leave_ded_amount5 = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count3 = no_days1 + no_days2
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            cur_month_leave4=no_days1
                            leave_ded_amount7 = round((contract.wage+contract.grade_pay)/day*no_days1)
                            count5 = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            last_month_leave5=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount8 = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount8 = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = (leave_end - leave_end_previous).days
                            cur_month_leave5=no_days2
                            leave_ded_amount9 = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count6 = no_days1 + no_days2
                    elif leave.leave_type.name == 'EOL':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_eol += leave.no_of_days
                            if int(contract.increment_month)==month:
                                leave_ded_amount_eol = round((contract.old_wage+contract.grade_pay)/months*count_eol)
                            else:
                                leave_ded_amount_eol = round((contract.wage+contract.grade_pay)/months*count_eol)
                            last_month_leave1_eol=count_eol
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_eol += no_days
                            cur_month_leave1_eol=count1_eol
                            leave_ded_amount1_eol = round((contract.wage+contract.grade_pay)/day*count1_eol)
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            last_month_leave2_eol=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount2_eol = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount2_eol = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = (to_date - leave_end_previous).days
                            cur_month_leave2_eol=no_days2
                            leave_ded_amount3_eol = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count2_eol = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            last_month_leave3_eol=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount4_eol = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount4_eol = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = (leave_end - leave_end_previous).days
                            cur_month_leave3_eol=no_days2
                            leave_ded_amount5_eol = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count3_eol = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            last_month_leave4_eol=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount6_eol = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount6_eol = round((contract.wage+contract.grade_pay)/months*no_days1)
                            count4_eol = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            cur_month_leave4_eol=no_days1
                            leave_ded_amount7_eol = round((contract.wage+contract.grade_pay)/day*no_days1)
                            count5_eol = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            last_month_leave5_eol=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount8_eol = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount8_eol = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = (leave_end - leave_end_previous).days
                            cur_month_leave5_eol=no_days2
                            leave_ded_amount9_eol = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count6_eol = no_days1 + no_days2
                    elif leave.leave_type.name == 'HPL':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_hpl += float(leave.no_of_days)/float(2)
                            last_month_leave1_hpl=count_hpl
                            #print"last_month_leave_hpl---",last_month_leave_hpl
                            if int(contract.increment_month)==month:
                                leave_ded_amount_hpl = round((contract.old_wage+contract.grade_pay)/months*count_hpl)
                            else:
                                leave_ded_amount_hpl = round((contract.wage+contract.grade_pay)/months*count_hpl)
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = ((to_date - from_date).days + 1)
                            count1_hpl = float(no_days)/float(2)
                            cur_month_leave1_hpl=count1_hpl
                            print"cur_month_leave1_hpl",cur_month_leave1_hpl
                            leave_ded_amount1_hpl = round((contract.wage+contract.grade_pay)/day*count1_hpl)
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = float((leave_end_previous - from_date).days + 1)/float(2)
                            last_month_leave2_hpl=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount2_hpl = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount2_hpl = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = float((to_date - leave_end_previous).days)/float(2)
                            cur_month_leave2_hpl=no_days2
                            leave_ded_amount3_hpl = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count2_hpl = no_days1 + no_days2
                            print"count2_hpl",count2_hpl
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = float((leave_end_previous - leave_start).days + 1)/float(2)
                            last_month_leave3_hpl=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount4_hpl = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount4_hpl = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = float((leave_end - leave_end_previous).days)/float(2)
                            cur_month_leave3_hpl=no_days2
                            leave_ded_amount5_hpl = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count3_hpl = no_days1 + no_days2
                            print"count3_hpl",count3_hpl
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = float((to_date - leave_start).days + 1)/float(2)
                            last_month_leave4_hpl=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount6_hpl = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount6_hpl = round((contract.wage+contract.grade_pay)/months*no_days1)
                            count4_hpl = no_days1
                            print"count4_hpl",count4_hpl
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = float((leave_end - from_date).days + 1)/float(2)
                            cur_month_leave4_hpl=no_days1
                            leave_ded_amount7_hpl = round((contract.wage+contract.grade_pay)/day*no_days1)
                            count5_hpl = no_days1
                            print"count5_hpl",count5_hpl
                        elif from_date>=leave_start and from_date<=leave_end and to_date>=leave_end and to_date>leave_end_previous:
                            no_days1 = float((leave_end_previous - from_date).days + 1)/float(2)
                            last_month_leave5_hpl=no_days1
                            if int(contract.increment_month)==month:
                                leave_ded_amount8_hpl = round((contract.old_wage+contract.grade_pay)/months*no_days1)
                            else:
                                leave_ded_amount8_hpl = round((contract.wage+contract.grade_pay)/months*no_days1)
                            no_days2 = float((leave_end - leave_end_previous).days)/float(2)
                            cur_month_leave5_hpl=no_days2
                            leave_ded_amount9_hpl = round((contract.wage+contract.grade_pay)/day*no_days2)
                            count6_hpl = no_days1 + no_days2
                            print"count6_hpl",count6_hpl
                            
                            
                            
                            
                    elif leave.leave_type.name == 'CL':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_cl += leave.no_of_days
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_cl += no_days
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_cl = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_cl = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_cl = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_cl = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_cl = no_days1 + no_days2
                            
                            
                    elif leave.leave_type.name == 'EL':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_el += leave.no_of_days
                            print"count_el===",count_el
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_el += no_days
                            print"count1_el===",count1_el
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_el = no_days1 + no_days2
                            print"count2_el===",count2_el
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_el = no_days1 + no_days2
                            print"count3_el===",count3_el
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_el = no_days1
                            print"count4_el===",count4_el
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_el = no_days1
                            print"count5_el===",count5_el
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_el = no_days1 + no_days2
                            print"count6_el===",count6_el
                    elif leave.leave_type.name == 'SCL':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_scl += leave.no_of_days
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_scl += no_days
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_scl = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_scl = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_scl = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_scl = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_scl = no_days1 + no_days2
                    
                    elif leave.leave_type.name == 'HL':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_hl += leave.no_of_days
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_hl += no_days
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_hl = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_hl = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_hl = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_hl = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_hl = no_days1 + no_days2
                            
                    elif leave.leave_type.name == 'COM':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_com += leave.no_of_days
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_com += no_days
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_com = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_com = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_com = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_com = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_com = no_days1 + no_days2
                            
                    elif leave.leave_type.name == 'SDL':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_sdl += leave.no_of_days
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_sdl += no_days
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_sdl = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_sdl = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_sdl = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_sdl = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_sdl = no_days1 + no_days2
                            
                            
                    elif leave.leave_type.name == 'PAT':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_pat += leave.no_of_days
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_pat += no_days
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_pat = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_pat = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_pat = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_pat = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_pat = no_days1 + no_days2
                            
                    elif leave.leave_type.name == 'MAT':
                        if from_date>=leave_start and to_date<=leave_end_previous:
                            count_mat += leave.no_of_days
                        elif from_date>leave_end_previous and to_date<=leave_end:
                            no_days = (to_date - from_date).days + 1
                            count1_mat += no_days
                        elif from_date>=leave_start and to_date<=leave_end and to_date>leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (to_date - leave_end_previous).days
                            count2_mat = no_days1 + no_days2
                        elif from_date<leave_start and to_date>=leave_end:
                            no_days1 = (leave_end_previous - leave_start).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count3_mat = no_days1 + no_days2
                        elif from_date<leave_start and to_date<=leave_end_previous and to_date>=leave_start:
                            no_days1 = (to_date - leave_start).days + 1
                            count4_mat = no_days1
                        elif from_date>leave_end_previous and to_date>leave_end and from_date<leave_end:
                            no_days1 = (leave_end - from_date).days + 1
                            count5_mat = no_days1
                        elif from_date>=leave_start and to_date>=leave_end and from_date<leave_end_previous:
                            no_days1 = (leave_end_previous - from_date).days + 1
                            no_days2 = (leave_end - leave_end_previous).days
                            count6_mat = no_days1 + no_days2
                                
                        
                            
        days_before_promotion = days_before
        days_after_promotion = days_after 
        days_before_transfer = days_before_tr
        days_after_transfer = days_after_tr 
        last_month_leave=last_month_leave1_eol+last_month_leave2_eol+last_month_leave3_eol+last_month_leave4_eol+last_month_leave5_eol+last_month_leave1+last_month_leave2+last_month_leave3+last_month_leave4+last_month_leave5+last_month_leave1_hpl+last_month_leave2_hpl+last_month_leave3_hpl+last_month_leave4_hpl
        cur_month_leave=cur_month_leave1_eol+cur_month_leave2_eol+cur_month_leave3_eol+cur_month_leave4_eol+cur_month_leave5_eol+cur_month_leave1+cur_month_leave2+cur_month_leave3+cur_month_leave4+cur_month_leave5+cur_month_leave1_hpl+cur_month_leave2_hpl+cur_month_leave3_hpl+cur_month_leave4_hpl
        leave_ded_amounts1 = leave_ded_amount+leave_ded_amount2+leave_ded_amount4+leave_ded_amount6+leave_ded_amount8
        leave_ded_amounts2 = leave_ded_amount1+leave_ded_amount3+leave_ded_amount5+leave_ded_amount7+leave_ded_amount9
        leave_ded_amounts = round(leave_ded_amounts1+leave_ded_amounts2)
        
        count_cl = count_cl+count1_cl+count2_cl+count3_cl+count4_cl+count5_cl+count6_cl
        count_el = count_el+count1_el+count2_el+count3_el+count4_el+count5_el+count6_el
        count_scl = count_scl+count1_scl+count2_scl+count3_scl+count4_scl+count5_scl+count6_scl
        count_hl = count_hl+count1_hl+count2_hl+count3_hl+count4_hl+count5_hl+count6_hl
        count_com = count_com+count1_com+count2_com+count3_com+count4_com+count5_com+count6_com
        count_sdl = count_sdl+count1_sdl+count2_sdl+count3_sdl+count4_sdl+count5_sdl+count6_sdl
        count_pat = count_pat+count1_pat+count2_pat+count3_pat+count4_pat+count5_pat+count6_pat
        count_mat = count_mat+count1_mat+count2_mat+count3_mat+count4_mat+count5_mat+count6_mat
        count_abs = count+count1+count2+count3+count4+count5+count6
        counts_hpl = count_hpl+count1_hpl+count2_hpl+count3_hpl+count4_hpl+count5_hpl+count6_hpl
        counts_eol = count_eol+count1_eol+count2_eol+count3_eol+count4_eol+count5_eol+count6_eol
        counts = count+count1+count2+count3+count4+count5+count6+counts_eol
        leave_ded_amounts1_hpl = leave_ded_amount_hpl+leave_ded_amount2_hpl+leave_ded_amount4_hpl+leave_ded_amount6_hpl+leave_ded_amount8_hpl
        leave_ded_amounts2_hpl = leave_ded_amount1_hpl+leave_ded_amount3_hpl+leave_ded_amount5_hpl+leave_ded_amount7_hpl+leave_ded_amount9_hpl
        leave_ded_amounts_hpl = round(leave_ded_amounts1_hpl+leave_ded_amounts2_hpl)
        
        leave_ded_amounts1_eol = leave_ded_amount_eol+leave_ded_amount2_eol+leave_ded_amount4_eol+leave_ded_amount6_eol+leave_ded_amount8_eol
        leave_ded_amounts2_eol = leave_ded_amount1_eol+leave_ded_amount3_eol+leave_ded_amount5_eol+leave_ded_amount7_eol+leave_ded_amount9_eol
        leave_ded_amounts_eol = round(leave_ded_amounts1_eol+leave_ded_amounts2_eol)
        
        leave_ded_amounts_last=leave_ded_amounts1+leave_ded_amounts1_hpl+leave_ded_amounts1_eol
        leave_ded_amounts_cur=leave_ded_amounts2+leave_ded_amounts2_hpl+leave_ded_amounts2_eol
        leave_ded_amount_final = leave_ded_amounts+leave_ded_amounts_hpl+leave_ded_amounts_eol
        work_days=0.0
        #custome code end here!
        
        #fill only if the contract as a working schedule linked
        for contract in self.env['hr.contract'].browse(contract_ids).filtered(lambda contract: contract.working_hours):
            #custome code start here
            if contract.date_end:
                day_from = datetime.strptime(date_from,"%Y-%m-%d")
                day_to = datetime.strptime(contract.date_end,"%Y-%m-%d")
                nb_of_days = (day_to - day_from).days + 1
                working_days = nb_of_days-counts
                if working_days<=0:
                    work_days=0
                elif working_days==1:
                    work_days=0
                else:
                    work_days=working_days
                attendances = {
                     'name': _("Normal Working Days paid at 100%"),
                     'sequence': 1,
                     'code': 'WORK100',
                     'days_in_month': days_in_month, 
                     'number_of_days': work_days,
                     'leave_ded_amount': leave_ded_amount_final,
                     'last_month_leave_days': last_month_leave,
                     'cur_month_leave_days': cur_month_leave,
                     'last_month_leave_salary': leave_ded_amounts_last,
                     'cur_month_leave_salary': leave_ded_amounts_cur,
                     'days_before_promotion': days_before_promotion,
                     'days_after_promotion': days_after_promotion,

                     'days_before_transfer': days_before_transfer,
                     'days_after_transfer': days_after_transfer,
                     

                     'leave_ded_amount_eol': leave_ded_amounts_eol,
                     'leave_ded_amount_hpl': leave_ded_amounts_hpl,
                     'number_of_hours': 0.0,
                     
                        'cl_days': count_cl,
                        'el_days': count_el,
                        'scl_days': count_scl,
                        'hl_days': count_hl,
                        'com_days': count_com,
                        'sdl_days': count_sdl,
                        'pat_days': count_pat,
                        'mat_days': count_mat,
                        'abs_days': count_abs,
                     
                     'eol_days': counts_eol,
                     'hpl_days': counts_hpl,
                     'nh_days': contract.nha_worked,
                     'nd_hours': contract.nda_hours,
                     'contract_id': contract.id,
                     }
            elif contract.date_start>date_from:
                day_from = datetime.strptime(contract.date_start,"%Y-%m-%d")
                day_to = datetime.strptime(date_to,"%Y-%m-%d")
                nb_of_days = (day_to - day_from).days + 1
                working_days = nb_of_days-counts
                if working_days<=0:
                    work_days=0
                elif working_days==1:
                    work_days=0
                else:
                    work_days=working_days
                attendances = {
                     'name': _("Normal Working Days paid at 100%"),
                     'sequence': 1,
                     'code': 'WORK100',
                     'days_in_month': days_in_month,
                     'number_of_days': work_days,
                     'leave_ded_amount': leave_ded_amount_final,
                     'last_month_leave_days': last_month_leave,
                     'cur_month_leave_days': cur_month_leave,
                     'last_month_leave_salary': leave_ded_amounts_last,
                     'cur_month_leave_salary': leave_ded_amounts_cur,
                     'days_before_promotion': days_before_promotion,
                     'days_after_promotion': days_after_promotion,
                     
                     'days_before_transfer': days_before_transfer,
                     'days_after_transfer': days_after_transfer,

                     'eol_days': counts_eol,
                     'leave_ded_amount_eol': leave_ded_amounts_eol,
                     'leave_ded_amount_hpl': leave_ded_amounts_hpl,
                     'number_of_hours': 0.0,
                     
                      'cl_days': count_cl,
                        'el_days': count_el,
                        'scl_days': count_scl,
                        'hl_days': count_hl,
                        'com_days': count_com,
                        'sdl_days': count_sdl,
                        'pat_days': count_pat,
                        'mat_days': count_mat,
                     'abs_days': count_abs,
                     
                     'hpl_days': counts_hpl,
                     'nh_days': contract.nha_worked,
                     'nd_hours': contract.nda_hours,
                     'contract_id': contract.id,
                     }
            elif contract.date_start>date_from and contract.date_end<date_to:
                day_from = datetime.strptime(contract.date_start,"%Y-%m-%d")
                day_to = datetime.strptime(contract.date_end,"%Y-%m-%d")
                nb_of_days = (day_to - day_from).days + 1
                working_days = nb_of_days-counts
                if working_days<=0:
                    work_days=0
                elif working_days==1:
                    work_days=0
                else:
                    work_days=working_days
                attendances = {
                     'name': _("Normal Working Days paid at 100%"),
                     'sequence': 1,
                     'code': 'WORK100',
                     'days_in_month': days_in_month,
                     'number_of_days': work_days,
                     'leave_ded_amount': leave_ded_amount_final,
                     'last_month_leave_days': last_month_leave,
                     'cur_month_leave_days': cur_month_leave,
                     'last_month_leave_salary': leave_ded_amounts_last,
                     'cur_month_leave_salary': leave_ded_amounts_cur,
                     'days_before_promotion': days_before_promotion,
                     'days_after_promotion': days_after_promotion,
                     
                     'days_before_transfer': days_before_transfer,
                     'days_after_transfer': days_after_transfer,
                        
                         'cl_days': count_cl,
                        'el_days': count_el,
                        'scl_days': count_scl,
                        'hl_days': count_hl,
                        'com_days': count_com,
                        'sdl_days': count_sdl,
                        'pat_days': count_pat,
                        'mat_days': count_mat,
                       'abs_days': count_abs, 
                     'eol_days': counts_eol,
                     'leave_ded_amount_eol': leave_ded_amounts_eol,
                     'leave_ded_amount_hpl': leave_ded_amounts_hpl,
                     'number_of_hours': 0.0,
                     
                     'hpl_days': counts_hpl,
                     'nh_days': contract.nha_worked,
                     'nd_hours': contract.nda_hours,
                     'contract_id': contract.id,
                     }
            elif not contract.date_end:
                day_from = datetime.strptime(date_from,"%Y-%m-%d")
                day_to = datetime.strptime(date_to,"%Y-%m-%d")
                nb_of_days = (day_to - day_from).days + 1
                working_days = nb_of_days-counts
                if working_days<=0:
                    work_days=0
                elif working_days==1:
                    work_days=0
                else:
                    work_days=working_days
                attendances = {
                     'name': _("Normal Working Days paid at 100%"),
                     'sequence': 1,
                     'code': 'WORK100',
                     'days_in_month': days_in_month,
                     'number_of_days': work_days,
                     'leave_ded_amount': leave_ded_amount_final,
                     'last_month_leave_days': last_month_leave,
                     'cur_month_leave_days': cur_month_leave,
                     'last_month_leave_salary': leave_ded_amounts_last,
                     'cur_month_leave_salary': leave_ded_amounts_cur,
                     'days_before_promotion': days_before_promotion,
                     'days_after_promotion': days_after_promotion,
                     
                     'days_before_transfer': days_before_transfer,
                     'days_after_transfer': days_after_transfer,
                     
                      'cl_days': count_cl,
                        'el_days': count_el,
                        'scl_days': count_scl,
                        'hl_days': count_hl,
                        'com_days': count_com,
                        'sdl_days': count_sdl,
                        'pat_days': count_pat,
                        'mat_days': count_mat,
                     'abs_days': count_abs,
                     
                     'eol_days': counts_eol,
                     'leave_ded_amount_eol': leave_ded_amounts_eol,
                     'leave_ded_amount_hpl': leave_ded_amounts_hpl,
                     'number_of_hours': 0.0,
                     
                     'hpl_days': counts_hpl,
                     'nh_days': contract.nha_worked,
                     'nd_hours': contract.nda_hours,
                     'contract_id': contract.id,
                     }  # custome code end 
#             else:  
#                 #standard code       
#                 attendances = {
#                  'name': _("Normal Working Days paid at 100%"),
#                  'sequence': 1,
#                  'code': 'WORK100',
#                  'number_of_days': 0.0,
#                  'number_of_hours': 0.0,
#                  'contract_id': contract.id,
#             }
            leaves = {}
            day_from = fields.Datetime.from_string(date_from)
            day_to = fields.Datetime.from_string(date_to)
            nb_of_days = (day_to - day_from).days + 1
            for day in range(0, nb_of_days):
                working_hours_on_day = contract.working_hours.working_hours_on_day(day_from + timedelta(days=day))
                if working_hours_on_day:
                    #the employee had to work
                    leave_type = was_on_leave(contract.employee_id.id, day_from + timedelta(days=day))
                    if leave_type:
                        #if he was on leave, fill the leaves dict
                        if leave_type in leaves:
                            leaves[leave_type]['number_of_days'] += 1.0
                            leaves[leave_type]['number_of_hours'] += working_hours_on_day
                        else:
                            leaves[leave_type] = {
                                'name': leave_type,
                                'sequence': 5,
                                'code': leave_type,
                                'number_of_days': 1.0,
                                'number_of_hours': working_hours_on_day,
                                'contract_id': contract.id,
                            }
                    else:
                        #add the input vals to tmp (increment if existing)
                        attendances['number_of_days'] += 1.0
                        attendances['number_of_hours'] += working_hours_on_day
            leaves = [value for key, value in leaves.items()]
            res += [attendances] + leaves
        return res    
    # YTI TODO To rename. This method is not really an onchange, as it is not in any view
    # employee_id and contract_id could be browse records
    @api.multi
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False,region_id=False, unit_id=False,rate_of_pay=False,location_id=False,department_id=False,job_title=False):
        #defaults
        res = {
            'value': {
                'line_ids': [],
                #delete old input lines
                'input_line_ids': map(lambda x: (2, x,), self.input_line_ids.ids),
                #delete old worked days lines
                'worked_days_line_ids': map(lambda x: (2, x,), self.worked_days_line_ids.ids),
                #'details_by_salary_head':[], TODO put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
                'region_id': False,
                'unit_id': False,
                'rate_of_pay': False,
                'location_id': False,
                'department_id': False,
                'job_title': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        employee = self.env['hr.employee'].browse(employee_id)
        res['value'].update({
                    'name': _('Salary Slip of %s for %s') % (employee.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                    'company_id': employee.company_id.id,
                    'region_id': employee.region_id.id,
                    'unit_id': employee.catering_unit.id,
                    #'rate_of_pay': employee_id.contract_id.new_wage,
                    'location_id': employee.location_id.id, 
                    'department_id': employee.department_id.id,
                    'job_title' : employee.job_id.id,
        })

        if not self.env.context.get('contract'):
            #fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                #set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                #if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        #computation of the salary input
        worked_days_line_ids = self.get_worked_day_lines(contract_ids, date_from, date_to)
        input_line_ids = self.get_inputs(contract_ids, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res
    
    
    
class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'
    
    
    leave_ded_amount=fields.Float('Total Leave Salary')
    last_month_leave_days=fields.Float('Last Month Leave Days')
    cur_month_leave_days=fields.Float('Current Month Leave Days')
    last_month_leave_salary=fields.Float('Last Month Leave Salary')
    cur_month_leave_salary=fields.Float('Current Month Leave Salary')
    days_before_promotion=fields.Float('Days Before Promotion')
    days_after_promotion=fields.Float('Days After Promotion')

    days_before_transfer=fields.Float('Days Before Transfer')
    days_after_transfer=fields.Float('Days After transfer')
    days_in_month=fields.Float('Days In Month')
    
    eol_days=fields.Float('EOL Days')
    leave_ded_amount_eol=fields.Float('EOl Deduction Amount')
    leave_ded_amount_hpl=fields.Float('HPL Deduction Amount')
    
    #'eol_days':fields.Float('EOL Days'),
    hpl_days=fields.Float('HPL Days')
    cl_days=fields.Float('CL Days')
    el_days=fields.Float('EL Days')
    scl_days=fields.Float('SCL Days')
    hl_days=fields.Float('HL Days')
    com_days=fields.Float('COM Days')
#         'sdl_days':fields.Float('SDL Days'),
    pat_days=fields.Float('PAT Days')
    mat_days=fields.Float('MAT Days')
    abs_days=fields.Float('ABS Days')
    
    nh_days=fields.Float('National Holidays Days')
    nd_hours=fields.Float('Night Duty Hours')
        
        
class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    
    company_id=fields.Many2one('res.company','Zone',default=lambda self: self.env['res.company']._company_default_get('hr.payslip.run'))

    
    @api.model
    def create(self, vals):
        if 'date_start' in vals and vals['date_start']:
            date_start = vals['date_start']
            print"date_start====",date_start
        if 'company_id' in vals and vals['company_id']:
            company_id = vals['company_id']
            print"company_id====",company_id
            employee = self.env['hr.payslip.run'].search([('company_id', '=', company_id),('date_start', '=', date_start)])
            if employee:
                raise UserError(_('Employee Payslip Batch record already exists! Please update Or Delete the existing record.'))
        return super(HrPayslipRun, self).create(vals)

    
   
    @api.multi
    def unlink(self):
        for payslip_run in self:
            if payslip_run.state not in  ['draft']:
                raise UserError(_('You cannot delete a payslip batch which is not draft!'))
        return super(HrPayslipRun, self).unlink() 
    
    @api.multi
    def confirm(self):
        misc_payment = self.env['hr.misc.payment']
        slip_pool = self.env['hr.payslip']
        slip_ids = map(lambda x: x.id, self.slip_ids)
        slip_obj = slip_pool.browse(slip_ids)
        slip_obj.action_payslip_done()
        # for run in self:
        #     slip_ids = []
        #     for slip_id in run.slip_ids:
        #         # TODO is it necessary to intewerleave the calls ?
        #         slip_pool.signal_workflow([slip_id.id], 'hr_verify_sheet')
        #         slip_pool.signal_workflow([slip_id.id], 'process_sheet')
        #         slip_ids.append(slip_id.id)
        for each in self:
            for line in each.slip_ids:
                for pay_ids in misc_payment.search([('employee_id','=',line.employee_id.id),('date_to','<=',line.date_to)]):
                    for misc in pay_ids:
                        misc.write({'active': False})
        self.write({'state': 'close'})
    
        return True
    
    @api.model
    def import_open_csv(self):
        passe = 1
        c = 0
        print"==========import====",c
        reader = csv.reader(open('hr_salary_rule.csv','rb'))#place .csv file where openerp-server file 
        for row in reader:
            print "=====rowS===========",row
            c += 1
            if c == passe: #not take header of csv file
                pass
            else:
                if row[3] == 'Always True':
                    cond_select = 'none'
                elif row[3] == 'Python Expression':
                    cond_select = 'python'
                else:
                    cond_select = 'range'
                
                if row[0] == 'Percentage (%)':
                    amount_select = 'percentage'
                elif row[0] == 'Fixed Amount':
                    amount_select = 'fix'
                else:
                    amount_select = 'code'     
                
                print "=====category",row[1]
                self.env['hr.salary.rule'].create({
                                
                                'amount_select':amount_select,
                                
                                'category_id':row[1] or '',
                                
                                'code':row[2] or False,
                                
                                'condition_select':cond_select,
                                
                                'name':row[4] or '',
                                
                                'condition_python':row[5] or '',
                                
                              })   
        
        sechduled_id = self.env['ir.cron'].search([('name','=','Salary Rules')])   
        print"=====sechduled_id=====",sechduled_id
        sechduled_id.write({'active':False})
        #return True
    
    
    
class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    
    @api.multi
    def compute_sheet(self):
        context = self._context
        emp_pool = self.env['hr.employee']
        slip_pool = self.env['hr.payslip']
        run_pool = self.env['hr.payslip.run']
        slip_ids = []
        if context is None:
            context = {}
        data = self.read()[0]
        run_data = {}
        print"context====",context
        if context and context.get('active_id', False):
            print"====context['active_id']=====",context['active_id']
            run_data = run_pool.browse(context['active_id']).read(['date_start', 'date_end', 'credit_note'])[0]
            print"====run_data====",run_data
#             run_data = run_pool.read([context['active_id']], ['date_start', 'date_end', 'credit_note'])[0]
        from_date =  run_data.get('date_start', False)
        to_date = run_data.get('date_end', False)
        credit_note = run_data.get('credit_note', False)
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for emp in data['employee_ids']:
            print"emp=====",emp
            
            slip_data = slip_pool.onchange_employee_id(from_date, to_date, emp, contract_id=False, region_id=False, unit_id=False, rate_of_pay=False, location_id=False, department_id=False, job_title=False)
            res = {
                'employee_id': emp,
                'name': slip_data['value'].get('name', False),
                'region_id': slip_data['value'].get('region_id', False),
                'unit_id': slip_data['value'].get('unit_id', False),
                'rate_of_pay': slip_data['value'].get('rate_of_pay', False),
                'location_id': slip_data['value'].get('location_id', False),
                'department_id': slip_data['value'].get('department_id', False),
                'job_title': slip_data['value'].get('job_title', False),
                
                'struct_id': slip_data['value'].get('struct_id', False),
                'contract_id': slip_data['value'].get('contract_id', False),
                'payslip_run_id': context.get('active_id', False),
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': credit_note,
            }
            slip_ids.append(slip_pool.create(res))
        for slip in slip_ids:
            slip.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
    
    






