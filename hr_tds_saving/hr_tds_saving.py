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
from odoo.exceptions import UserError, ValidationError
import calendar
from calendar import monthrange


class EmployeeSaving(models.Model):
    _name = 'employee.saving'
    _description = 'Employee Savings'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        for record in self:
            emp=record.employee_id
            if emp:
                employee = self.search([('employee_id', '=', emp.id)])
                if employee:
                    raise ValidationError('Employee saving record already exists! Please update the existing record.')
                else:
                    saving_lines = self.get_default_savings()
                    medical_lines = self.get_default_medical_bills()
                    hra_lines = self.get_default_hra()
                    other_income = self.get_default_other_income()
                    house_property = self.get_default_house_property()
                    deduction_sec80c = self.get_default_deduction_section80()
                    param = self.env['ir.config_parameter']
                    fy_year = param.search([('key', '=', 'PayrollFinancialYear')])
                    self.emp_id=emp.nf_emp
                    self.join_date=emp.join_date
                    self.pan_no=emp.pan
                    self.current_city=emp.q_city_id and emp.q_city_id.id or False
                    self.hra_line_ids=hra_lines
                    self.medical_line_ids=medical_lines
                    self.other_income_ids=other_income
                    self.saving_line_ids=saving_lines
                    self.house_property_ids=house_property
                    self.ded_sec80c_ids=deduction_sec80c

    @api.onchange('current_city')
    def onchange_current_city(self):
        if self.current_city:
            if self.current_city.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                self.resident = 'Metro'
            else:
                self.resident = 'Non Metro'

    @api.model
    def default_get(self, fields):
        rec={}
        rec =  super(EmployeeSaving, self).default_get(fields)
        param = self.env['ir.config_parameter']
        fy_year = param.search([('key', '=', 'PayrollFinancialYear')])
        hr_obj = self.env['hr.employee'].sudo().search([('user_id','=',self.env.uid)])
        rec.update({'employee_id':hr_obj.id,'emp_id':hr_obj.nf_emp,'join_date':hr_obj.join_date,'pan_no':hr_obj.pan,'current_city':hr_obj.q_city_id and hr_obj.q_city_id.id or False,'fin_year_id':int(fy_year.value)})    
        return rec


    @api.multi
    def _get_amount(self):
        for each in self:
            total =0.0
            for line in each.saving_line_ids:
                total += line.amount
            each.proposed_amount = total

            
    def get_default_hra(self):
        vals=[]       
        month = time.strftime("%m")
        year = time.strftime("%Y")
        
        if int(month) < 4:
            date4 = time.strftime("%s-01-01"%(year))
            year = int(year) - 1
            date1 = time.strftime("%s-04-01"%(year))
            date2 = time.strftime("%s-07-01"%(year))
            date3 = time.strftime("%s-10-01"%(year))
            
        else:
            date1 = time.strftime("%s-04-01"%(year))
            date2 = time.strftime("%s-07-01"%(year))
            date3 = time.strftime("%s-10-01"%(year))
            year = int(year) + 1
            date4 = time.strftime("%s-01-01"%(year))
            
        hra1 = 'Apr - June'
        hra2 = 'July - Sept'
        hra3 = 'Oct - Dec'
        hra4 = 'Jan - Mar'
        
        type = 'P'
        
        vals = [(0,False,{'reference':hra1,'date':date1,'type':'P','amount':0.0,}),
                (0,False,{'reference':hra2,'date':date2,'type':'P','amount':0.0,}),
                (0,False,{'reference':hra3,'date':date3,'type':'P','amount':0.0,}),
                (0,False,{'reference':hra4,'date':date4,'type':'P','amount':0.0,})
                ]
        return vals
    
    def get_default_medical_bills(self):
        vals=[]
        month = time.strftime("%m")
        year = time.strftime("%Y")
        
        if int(month) < 4:
            date6 = time.strftime("%s-01-01"%(year))
            year = int(year) - 1
            date1 = time.strftime("%s-04-01"%(year))
            date2 = time.strftime("%s-05-01"%(year))
            date3 = time.strftime("%s-07-01"%(year))
            date4 = time.strftime("%s-08-01"%(year))
            date5 = time.strftime("%s-10-01"%(year))
            
        else:
            date1 = time.strftime("%s-04-01"%(year))
            date2 = time.strftime("%s-05-01"%(year))
            date3 = time.strftime("%s-07-01"%(year))
            date4 = time.strftime("%s-08-01"%(year))
            date5 = time.strftime("%s-10-01"%(year))
            year = int(year) + 1
            date6 = time.strftime("%s-01-01"%(year))
            
        med1 = '80D (Mediclaim- upto Rs. 25000 for Self, Spouse and Children)'
        med2 = '80D (Mediclaim- upto Rs. 25000 for dependent Parents)'
        med3 = '80D (Mediclaim- upto Rs. 50000 for Senior Citizen Parents(above 60 years of age))'
        med4 = '80D (Preventive Health Check-ups - upto Rs. 5000)'
        med5 = '80DD - Medical treatment for handicapped dependent'
        med6 = '(with < 80% disability - Rs 75000 or > 80% disability - Rs 1,25000, pl. specify)'
        
        type = 'P'
        
        vals = [(0,False,{'reference':med1,'date':date1,'type':'P','amount':0.0,}),
                (0,False,{'reference':med2,'date':date1,'type':'P','amount':0.0,}),
                (0,False,{'reference':med3,'date':date1,'type':'P','amount':0.0,}),
                (0,False,{'reference':med4,'date':date1,'type':'P','amount':0.0,}),
                (0,False,{'reference':med5+' '+med6,'date':date1,'type':'P','amount':0.0,})
                ]
        
        return vals
    
    def get_default_other_income(self):
        vals=[]
        month = time.strftime("%m")
        year = time.strftime("%Y")
        
        if int(month) < 4:
            date4 = time.strftime("%s-01-01"%(year))
            year = int(year) - 1
            date1 = time.strftime("%s-04-01"%(year))
            date2 = time.strftime("%s-07-01"%(year))
            date3 = time.strftime("%s-10-01"%(year))
            
        else:
            date1 = time.strftime("%s-04-01"%(year))
            date2 = time.strftime("%s-07-01"%(year))
            date3 = time.strftime("%s-10-01"%(year))
            year = int(year) + 1
            date4 = time.strftime("%s-01-01"%(year))
            
        oth1 = 'Income From House Property'
        oth2 = 'Interest On FD' 
        oth3 = 'Saving Interest Income'
        oth4 = 'Other'
        
        vals = [(0,False,{'reference':oth1,'date':date1,'income_source':'1','amount':0.0,}),
                (0,False,{'reference':oth2,'date':date2,'income_source':'2','amount':0.0,}),
                (0,False,{'reference':oth3,'date':date3,'income_source':'3','amount':0.0,}),
                (0,False,{'reference':oth4,'date':date4,'income_source':'4','amount':0.0,})
                ]
        
        return vals
    
    def get_default_savings(self):
#         housing_loan = '324'
#         interest_on_housing_loan = '344'
#         education_loan = '345'
#         NPS = '508'
#         LIC = '554'
#         Pension_Plans_80CCC = '585'
#         PPF = '555'
#         NSC = '551'
#         interest_on_nsc = '552'
#         employee_pf_contribution = '901'
#         mutual_fund = '553'
#         FD = '559'
#         children_educational_expenses = '557'
        
        prop_type = 'S'
        type = 'P'
        code = ['324','344','345','508','554','585','555','551','552','901','553','559','557']
        saving_name = self.env['hr.salary.rule'].search([('code','in',code)])
        vals = [(0,False,{'salary_rule_id':rule.id,'type':type,'prop_type':prop_type,'amount':0.0,}) for rule in saving_name if rule]
        return vals

    def get_default_deduction_section80(self):
        vals=[]          
        desc1 = 'Life Insurance Premim ( LIC )'
        desc2 = 'Pension Plans u/s 80CCC (Jeevan Suraksha / Pension schemes of any other insurer)' 
        desc3 = 'Public Provident Fund ( PPF ) & Employee Provident Fund (EPF)'
        desc4 = 'Equity Linked Saving Scheme (ELSS)'
        desc5 = 'Housing Loan Principal Repayment/Stamp Duty & Reg. Charges'
        desc6 = 'Deposit in NSC'
        desc7 = 'Interest on NSC - Accrued'
        desc8 = 'Deposit in ULIP of UTI/LIC'
        desc9 = 'Tax Saving Mutual Funds eligible for deduction u/s 80 C'
        desc10 = 'Tax saving bonds'
        desc11 = 'Fixed Deposit in Banks eligible for Tax Saving u/s 80C'
        desc12 = 'Children Education expenditure  - Pl.mention number of children studying in School/College'
        desc13 = 'Sukanya Samriddhi Yojana'
        desc14 = ' Tax Saving Systematic Investment Plan (SIP)'
        
        vals = [(0,False,{'name':desc1,'type':'Proposed'}),
                (0,False,{'name':desc2,'type':'Proposed'}),
                (0,False,{'name':desc3,'type':'Proposed'}),
                (0,False,{'name':desc4,'type':'Proposed'}),
                (0,False,{'name':desc5,'type':'Proposed'}),
                (0,False,{'name':desc6,'type':'Proposed'}),
                (0,False,{'name':desc7,'type':'Proposed'}),
                (0,False,{'name':desc8,'type':'Proposed'}),
                (0,False,{'name':desc9,'type':'Proposed'}),
                (0,False,{'name':desc10,'type':'Proposed'}),
                (0,False,{'name':desc11,'type':'Proposed'}),
                (0,False,{'name':desc12,'type':'Proposed'}),
                (0,False,{'name':desc13,'type':'Proposed'}),
                (0,False,{'name':desc14,'type':'Proposed'})
                ]
        
        return vals
       
    def get_default_house_property(self):
        vals=[]          
        oth1 = 'Housing Loan Interest Amount'
        oth2 = 'Completion certificate or Occupancy Certificate' 
        oth3 = 'Self declaration whether this House is Self occupied or Let out'
        oth4 = 'Pl. mention whether loan was taken  before 01/04/99 or after 01/04/99'
        
        vals = [(0,False,{'name':oth1,'type':'Proposed'}),
                (0,False,{'name':oth2,'type':'Proposed'}),
                (0,False,{'name':oth3,'type':'Proposed'}),
                (0,False,{'name':oth4,'type':'Proposed'})
                ]
        
        return vals

    @api.depends('house_property_ids.amount')
    def _get_amount_income_house(self):
        for each in self:
            total =0.0
            for line in each.house_property_ids:
                total += line.amount
            if total > 200000:
                each.income_house_amount = 200000
            else:
                each.income_house_amount = total

    @api.depends('house_property_ids.description')
    def _get_description_income_house(self):
        for each in self:
            description=''
            n=1
            for line in each.house_property_ids:
                if n==3:
                    description = line.description
                n+=1
            each.house_property = description

    @api.depends('ded_sec80c_ids.amount')
    def _get_amount_ded80c_amount(self):
        for each in self:
            total =0.0
            for line in each.ded_sec80c_ids:
                total += line.amount
            if total > 150000:
                each.ded80c_amount = 150000
            else:
                each.ded80c_amount = total

    @api.depends('medical_line_ids.amount')
    def _get_amount_receipt(self):
        for each in self:
            total =0.0
            for line in each.medical_line_ids:
                total += line.amount
            each.bill_amount = total    
    
    @api.depends('hra_line_ids.amount')
    def _get_amount_receipt_hra(self):
        for each in self:
            total =0.0
            for line in each.hra_line_ids:
                total += line.amount
            if total > 100000:
                if not each.landlord_pan_no or not each.landlord_pan_attachment:
                    raise ValidationError(_("Please provide Landlord's PAN no and attach the file.")) 
            each.hra_receipt_amount = total    
    
    @api.depends('other_income_ids.amount')
    def _get_amount_other(self):
        for each in self:
            total =0.0
            for line in each.other_income_ids:
                total += line.amount
            each.other_income_amount = total       
    
    name=fields.Char('Name')
    fin_year_id = fields.Many2one('fin.year.mst','Financial Year')
    company_id=fields.Many2one('res.company','Company',default=lambda self: self.env['res.company']._company_default_get('employee.saving'))

    employee_id=fields.Many2one('hr.employee','Employee Name')
    proposed_amount=fields.Float(compute='_get_amount', string='Saving Amount',digits=dp.get_precision('Account'))
    saving_line_ids=fields.One2many('saving.line','saving_id','Saving Line')
    medical_line_ids=fields.One2many('medical.bill.line','bill_id','Medical Bill', track_visibility='onchange')
    hra_line_ids=fields.One2many('hra.receipt.line','hra_receipt_id','HRA Receipt', track_visibility='onchange')
    other_income_ids=fields.One2many('other.source.income','income_id','Other Income', track_visibility='onchange')                                                                
    bill_amount=fields.Float(compute='_get_amount_receipt', store='True', string='Medical Insurance Section 80D & 80DD',digits=dp.get_precision('Account'))
    hra_receipt_amount=fields.Float(compute='_get_amount_receipt_hra', store='True', string='HRA Section 10(13A)',digits=dp.get_precision('Account'))
    other_income_amount=fields.Float(compute='_get_amount_other', store='True', string='Income from Other Sources',digits=dp.get_precision('Account'))

    income_house_amount=fields.Float(compute='_get_amount_income_house', store='True', string='Home Loan Interest Section 24b',digits=dp.get_precision('Account'))
    ded80c_amount=fields.Float(compute='_get_amount_ded80c_amount', store='True', string='Deduction under section 80C',digits=dp.get_precision('Account'))

    state = fields.Selection([('Draft','Draft'),('Submit','Submit'),('Confirm','Confirm'),('Close','Close'),('Reject','Reject')],'Status',default='Draft', track_visibility='onchange')

    gross_income_previous=fields.Float('Earned Gross Income till DOJ', track_visibility='onchange')
    professional_tax_previous=fields.Float('Professional Tax', track_visibility='onchange')
    ded_previous_emp=fields.Float('Previous Total PF Deduction', track_visibility='onchange')
    income_tax_paid=fields.Float('Income Tax Deduction for current FY till DOJ', track_visibility='onchange')
    car_perks=fields.Float('Car Perks')
    lease_perks=fields.Float('Lease Perks')
    hard_furnishing_perks=fields.Float('Hard Furnishing Perks')
    other_perks=fields.Float('Other Perks')
    entertainment_allowance=fields.Float('Entertainment Allowance')
    lease_exemption=fields.Float('Lease Exemption')
    furniture_rent_recovery=fields.Float('Furniture Rent Recovery')
    actual_lease_rent_paid=fields.Float('Actual Lease Rent Paid')
    furnishing_allowance=fields.Float('Furnishing Allowance')
    conveyance_recovery=fields.Float('Trans Monthly Exempt')
    Date=fields.Date('Date')
    medical_exp_reimbursement=fields.Float('Medical Expense Reimbursement')
    prp_amount=fields.Float('PRP Amount')
    preconstruction_interest=fields.Float('Preconstruction Interest')
    prof_updation_exempt=fields.Float('Professional Updation Exempt')
    uniform_fitment_exempt=fields.Float('Uniform Fitment Exempt')
    property_type=fields.Selection([('S','Self Occupied'),('R','Rent Out')],"Property Type")
    house_income_sl=fields.Float('HP Income (Self Lease)',readonly=True)
    uniform_amount=fields.Float('Uniform Fitment Amount')

    emp_id = fields.Char('Employee ID')
    join_date = fields.Date('Date of Joining')
    current_city = fields.Many2one('ouc.city','Current City', track_visibility='onchange')
    resident = fields.Selection([('Metro','Metro'),('Non Metro','Non Metro')],'Resident', track_visibility='onchange')
    pan_no = fields.Char('PAN No')
    no_children = fields.Integer('No of Children', track_visibility='onchange')
    house_property_ids = fields.One2many('income.house.property','saving_id','Loss / Income from House Property', track_visibility='onchange')
    interest_education_loan = fields.Float('80 E - Repayment of Interest on Education loan', track_visibility='onchange')
    interest_resident_loan = fields.Float('Interest on Loan taken for New Residential House U/s 80EE', track_visibility='onchange')
    nps_passbook = fields.Float('80CCD(1B) NPS Passbook', track_visibility='onchange')
    donation_ded = fields.Float('Section 80G: Deductions on Donation to Charitable Institutions', track_visibility='onchange')
    ded_sec80c_ids = fields.One2many('deduction.section','saving_id','Deduction under section 80C', track_visibility='onchange')
    leave_travel_allowance = fields.Float('Leave Travel Allowance', track_visibility='onchange')
    leave_travel_attachment = fields.Binary('Leave Travel Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    leave_travel_filename = fields.Char('Leave Travel Filename', track_visibility='onchange')
    donation_ded_attachment = fields.Binary('Leave Travel Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    donation_ded_filename = fields.Char('Leave Travel Filename', track_visibility='onchange')
    nps_passbook_attachment = fields.Binary('Leave Travel Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    nps_passbook_filename = fields.Char('Leave Travel Filename', track_visibility='onchange')
    interest_resident_attachment = fields.Binary('Leave Travel Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    interest_resident_filename = fields.Char('Leave Travel Filename', track_visibility='onchange')
    interest_education_attachment = fields.Binary('Leave Travel Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    interest_education_filename = fields.Char('Leave Travel Filename', track_visibility='onchange')
    previous_payslip_attachment = fields.Binary('Previous Payslip Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    previous_payslip_filename = fields.Char('Previous Payslip Filename', track_visibility='onchange')
    previous_form16_attachment = fields.Binary('Previous Form16/Form12BA Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    previous_form16_filename = fields.Char('Previous Form16 Filename', track_visibility='onchange')
    house_property = fields.Char(compute='_get_description_income_house',store=True,string='Self declaration whether this House is Self occupied or Let out: ')
    landlord_pan_no = fields.Char('Landlord Pan No', track_visibility='onchange')
    landlord_pan_attachment = fields.Binary('Landlord PAN Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    landlord_pan_filename = fields.Char('Landlord PAN Filename', track_visibility='onchange')
    emp_pan_attachment = fields.Binary('Employee PAN Attachment',help="Upload Proof/Doc", track_visibility='onchange')
    emp_pan_filename = fields.Char('Employee PAN Filename', track_visibility='onchange')

    @api.multi
    def submit(self):
        self.write({'state': 'Submit'})
        return True

    @api.multi
    def close(self):
        self.write({'state': 'Close'})
        return True

    @api.multi
    def reject(self):
        self.write({'state': 'Reject'})
        return True

    @api.multi
    def confirm(self):
        self.write({'state': 'Confirm'})
        return True

    @api.multi
    def reset_draft(self):
        self.write({'state': 'Draft'})
        return True

    @api.model
    def create(self,vals):
        emp=self.env['hr.employee'].sudo().browse(vals.get('employee_id'))
        if emp:
            vals.update({'emp_id':emp.nf_emp,'join_date':emp.join_date,'pan_no':emp.pan})
        if vals.get('gross_income_previous')>0:
            if not vals.get('previous_payslip_attachment'):
                raise ValidationError("Please attach previous employment payslip.")
        res = super(EmployeeSaving,self).create(vals)
        return res
    
    @api.multi
    def write(self,vals):
        if vals.get('gross_income_previous')>0:
            if not vals.get('previous_payslip_attachment'):
                if not self.previous_payslip_attachment:
                    raise ValidationError("Please attach previous employment payslip.")
        res = super(EmployeeSaving,self).write(vals)
            
        return res
    
class SavingLine(models.Model):
    _name = 'saving.line'
    

    name=fields.Char('Name')
    saving_id=fields.Many2one('employee.saving','Saving Id')
    salary_rule_id=fields.Many2one('hr.salary.rule','Saving Name')
    type= fields.Selection([('P', 'Proposed'),('C', 'Confirmed')], "Saving Type")
    prop_type= fields.Selection([('S', 'Self Occupied'),('R', 'Rented Out')], "Property Type")
    amount=fields.Float('Amount')
    saving_no=fields.Char('Saving Number')
    fin_year_id=fields.Many2one('fin.year.mst','Financial Year')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    
    @api.model
    def create(self,vals):
        res = super(SavingLine,self).create(vals)
        if 'type' in vals and vals['type'] == 'C':
            if not res.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
    
    @api.multi
    def write(self,vals):
        res = super(SavingLine,self).write(vals)
        if 'type' in vals and vals['type'] == 'C':
            if not self.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
        return res    
            
            
    
    def get_confirm(self):
        self.type = 'C'
                
class MedicalBillLine(models.Model):
    _name = 'medical.bill.line'
    
   
    name=fields.Char('Name')
    bill_id=fields.Many2one('employee.saving','Bill Id')
    amount=fields.Float('Amount')
    date=fields.Date('Date')
    type= fields.Selection([('P', 'Proposed'),('C', 'Confirmed')], "Type")
    reference=fields.Char('Reference')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    #'fin_year_id':fields.Many2one('fin.year.mst','Financial Year'),
    
    @api.model
    def create(self,vals):
        res = super(MedicalBillLine,self).create(vals)
        if 'type' in vals and vals['type'] == 'C':
            if not res.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
    
    @api.multi
    def write(self,vals):
        res = super(MedicalBillLine,self).write(vals)
        if 'type' in vals and vals['type'] == 'C':
            if not self.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
        return res
    
    def get_confirm(self):
        self.type = 'C'
                
class HraReceiptLine(models.Model):
    _name = 'hra.receipt.line'
    
    
    name=fields.Char('Name')
    hra_receipt_id=fields.Many2one('employee.saving','HRA Receipt Id')
    amount=fields.Float('Amount')
    date=fields.Date('Date')
    type= fields.Selection([('P', 'Proposed'),('C', 'Confirmed')], "Type")
    reference=fields.Char('Reference')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    #'fin_year_id':fields.Many2one('fin.year.mst','Financial Year'),
    
    @api.model
    def create(self,vals):
        res = super(HraReceiptLine,self).create(vals)
        if 'type' in vals and vals['type'] == 'C':
            if not res.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
    
    @api.multi
    def write(self,vals):
        res = super(HraReceiptLine,self).write(vals)
        if 'type' in vals and vals['type'] == 'C':
            if not self.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
        return res
    
    def get_confirm(self):
        self.type = 'C'
                
class OtherSourceIncome(models.Model):
    _name = 'other.source.income'
    
    
    name=fields.Char('Name')
    income_source=fields.Selection([('1','Income From House Property'),('2','Interest On FD'),('3','Saving Interest Income'),('4','Other')],'Income Source',required='True')
    income_id=fields.Many2one('employee.saving','Income Id')
    amount=fields.Float('Amount')
    date=fields.Date('Date')
    reference=fields.Char('Reference')
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    #SS'fin_year_id':fields.Many2one('fin.year.mst','Financial Year'),
                    
    
class EmployeeInternalSaving(models.Model):
    _name = 'employee.internal.saving'
    
    name=fields.Char('Name')
    employee_id=fields.Many2one('hr.employee','Employee Name')
    salary_rule_id=fields.Many2one('hr.salary.rule','Saving Name')
    amount=fields.Float('Amount')
    saving_no=fields.Char('Saving Number')
    date_to=fields.Date('End Date')
    company_id=fields.Many2one('res.company','Zone',default=lambda self: self.env['res.company']._company_default_get('employee.internal.saving'))
    date=fields.Date('Date',default=fields.Date.context_today)
               
    

class SavingCategory(models.Model):
    _name = 'saving.category'
    
    name=fields.Char('Name')
    exempted_amount=fields.Float('Exempted Amount')
                
class IncomeHouseProperty(models.Model):
    _name = 'income.house.property'
    _description = 'Income House Property'
    
    name=fields.Char('Name')
    saving_id=fields.Many2one('employee.saving','Saving Id')
    amount=fields.Float('Amount', track_visibility='onchange')
    type= fields.Selection([('Proposed', 'Proposed'),('Confirmed', 'Confirmed')], "Type")
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    description=fields.Char('Description', track_visibility='onchange')
    
    @api.model
    def create(self,vals):
        res = super(IncomeHouseProperty,self).create(vals)
        if 'type' in vals and vals['type'] == 'Confirmed':
            if not res.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
    
    @api.multi
    def write(self,vals):
        res = super(IncomeHouseProperty,self).write(vals)
        if 'type' in vals and vals['type'] == 'Confirmed':
            if not self.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
        return res
    
    def get_confirm(self):
        self.type = 'Confirmed'

class DeductionSection(models.Model):
    _name = 'deduction.section'
    _description = 'Deduction under section 80C'
    
    name=fields.Char('Name')
    saving_id=fields.Many2one('employee.saving','Saving Id')
    amount=fields.Float('Amount')
    type= fields.Selection([('Proposed', 'Proposed'),('Confirmed', 'Confirmed')], "Type")
    attach_doc = fields.Binary('Attachment')
    filename = fields.Char('File Name')
    description=fields.Char('Description')
    
    @api.model
    def create(self,vals):
        res = super(DeductionSection,self).create(vals)
        if 'type' in vals and vals['type'] == 'Confirmed':
            if not res.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
    
    @api.multi
    def write(self,vals):
        res = super(DeductionSection,self).write(vals)
        if 'type' in vals and vals['type'] == 'Confirmed':
            if not self.attach_doc:
                raise ValidationError("Please Attach Documents Before Confirming")
        return res
    
    def get_confirm(self):
        self.type = 'Confirmed'


class nf_payslip_components(models.Model):
    _name = 'nf.payslip.components'
    _description = 'Payslip Components'

    name = fields.Char('Name')
    date = fields.Date('Date')
    employee_id = fields.Many2one('hr.employee','Employee')
    emp_id = fields.Char('Employee ID')
    join_date = fields.Date('Date of Joining')
    ctc = fields.Float('Actual CTC')
    wage = fields.Float('Earned CTC')
    basic = fields.Float('Basic')
    hra = fields.Float('HRA')
    medical_conveyance = fields.Float('Medical and Conveyance')
    lt_allowance = fields.Float('Leave Travel Allowance')
    professional_tax = fields.Float('Professional Tax')
    absent_days = fields.Float('Absent Days')
    lop = fields.Float('Loss of Pay')
    special_allowance = fields.Float('Special Allowance')
    esic_employee = fields.Float('ESIC Employee')
    esic_employer = fields.Float('ESIC Employer')
    pf_employee = fields.Float('PF Employee')
    pf_employer = fields.Float('PF Employer')
    tds = fields.Float('TDS')
    variable_pay = fields.Float('Variable Pay')
    bonus = fields.Float('Bonus')
    byod = fields.Float('BYOD Allowance')
    arrears = fields.Float('Arrears')
    advance = fields.Float('Advance Recovery')
    medical_insurance = fields.Float('Medical Insurance (Self)')
    general_recovery=fields.Float('General Recovery')
    incentive_recovery=fields.Float('Incentive Recovery')
    special_incentive=fields.Float('Special Incentive')
    gross = fields.Float('Gross')
    # net = fields.Float('Net')
    taxable_income=fields.Float('Taxable Income')
    cess=fields.Float('Cess')
    surcharge = fields.Float('Surcharge')
    annual_tax = fields.Float('Annual Tax')
    rebate = fields.Float('Rebate')
    saving_hra = fields.Float('Saving HRA')
    saving_lta = fields.Float('Saving LTA')
    saving_80c = fields.Float('Saving 80C')
    saving_80d = fields.Float('Saving 80D & 80DD')
    saving_24b = fields.Float('Saving 24b')
    saving_80e = fields.Float('Saving 80E')
    saving_80ee = fields.Float('Saving 80EE')
    saving_80ccd = fields.Float('Saving 80CCD')
    saving_80g = fields.Float('Saving 80G')
    total_savings = fields.Float('Total Savings')
    total_pf = fields.Float('Total PF')
    total_pt = fields.Float('Total PT')
    f16_pre_basic = fields.Float('Previous Months Basic')
    f16_pre_hra = fields.Float('Previous Months HRA')
    f16_pre_med_conv = fields.Float('Previous Months Medical and Conveyance')
    f16_pre_lta = fields.Float('Previous Months LTA')
    f16_pre_special_allowance= fields.Float('Previous Months Special Allownace')
    f16_pre_earned_gross = fields.Float('Previous Months Earned Gross')
    f16_curr_basic=fields.Float('Current Month Earned Basic')
    f16_curr_hra = fields.Float('Current Month HRA')
    f16_curr_med_conv = fields.Float('Current Month Medical and Conveyance')
    f16_curr_lta = fields.Float('Current Month LTA')
    f16_curr_special_allowance= fields.Float('Current Month Special Allownace')
    f16_curr_earned_gross = fields.Float('Current Month Earned Gross')
    f16_estm_basic=fields.Float('Estimated Months Earned Basic')
    f16_estm_hra = fields.Float('Estimated Months HRA')
    f16_estm_med_conv = fields.Float('Estimated Months Medical and Conveyance')
    f16_estm_lta = fields.Float('Estimated Months LTA')
    f16_estm_special_allowance= fields.Float('Estimated Months Special Allownace')
    f16_estm_earned_gross = fields.Float('Estimated Months Earned Gross')
    f16_1_a_b = fields.Float('1. a)Salary as per provisions contained in sec. 17')
    f16_1_b_b = fields.Float('b)Value of perquisites u/s 17(2)')
    f16_1_b_c = fields.Float('b)Value of perquisites u/s 17(2) Deductible')
    f16_1_c_b = fields.Float('C)Profits in lieu of salary under section 17(3)')
    f16_1_c_c = fields.Float('C)Profits in lieu of salary under section 17(3) Deductible')
    f16_2_a_c = fields.Float('A) HRA Exemption')
    f16_2_1_a = fields.Float('i)Actual HRA received')
    f16_2_2_a = fields.Float('ii) Rent paid - (10% on Basic)')
    f16_2_3_a = fields.Float('iii) 40 % or 50 % on Basic')
    f16_2_b_a = fields.Float('B) Leave Travel Allowance')
    f16_2_b_c = fields.Float('B) Leave Travel Allowance Deductible')
    f16_2_c_a = fields.Float('C)Standard Deductions (max -40000)')
    f16_2_c_c = fields.Float('C)Standard Deductions (max -40000) Deductible')
    f16_3_a_a = fields.Float('(a) Entertainment allowance')
    f16_3_a_c = fields.Float('(a) Entertainment allowance Deductible')
    f16_3_b_a = fields.Float('(b) Tax on employment (PT)')
    f16_3_b_c = fields.Float('(b) Tax on employment (PT) Deductible')
    f16_3_c_a = fields.Float('(C) Tax on employment (PT - Previous Employer)')
    f16_3_c_c = fields.Float('(C) Tax on employment (PT - Previous Employer) Deductible')
    f16_4_a_a = fields.Float('4.Home Loan Interest Section 24b (Max 200000)')
    f16_4_a_c = fields.Float('4.Home Loan Interest Section 24b (Max 200000) Deductible')
    f16_5_a_a = fields.Float('a) Income from Previous Employment')
    f16_5_b_a = fields.Float('b) Income from House Property')
    f16_5_c_a = fields.Float('c) Income from Other Sources')
    f16_5_d_b = fields.Float('Total F16-5')
    f16_6_a_b = fields.Float('6. Gross Total income (1+5) -(2+3+4)')
    f16_7_a_1_a = fields.Float('i) PF Contribution (80C)')
    f16_7_a_2_a = fields.Float('i) PF Contribution (80C- Previous employer)')
    f16_7_a_3_a = fields.Float('ii) Other Deductions under 80C, 80CCC& 80CCD')
    f16_7_a_4_a = fields.Float('Sec 80C Total amount')
    f16_7_a_4_c = fields.Float('Sec 80C Total amount Deductible')
    f16_7_b_1_a = fields.Float('80CCD (1b) (Contribution to NPS)')
    f16_7_b_2_a = fields.Float('80D (Medical Insurance)')
    f16_7_b_3_a = fields.Float('80DD (Rehabilitation of Handicapped Dependent)')
    f16_7_b_4_a = fields.Float('80DDB (Medical Expenditure on Self or Dependent)')
    f16_7_b_5_a = fields.Float('80E (Interest on Loan for Higher Studies)')
    f16_7_b_6_a = fields.Float('80EE (Interest on Loan taken for New Residential House )')
    f16_7_b_7_a = fields.Float('80TTA (Interest on Savings account)')
    f16_7_b_8_a = fields.Float('80G(Deductions on Donation to Charitable Institutions)')
    f16_7_b_9_a = fields.Float('Total amount  other sections under Chapter VI-A')
    f16_7_b_9_c = fields.Float('Total amount  other sections under Chapter VI-A Deductible')
    f16_8_a = fields.Float('8. Aggregate of deductible amount under Chapter VI A(A+B)')
    f16_9_b = fields.Float('9. Total Income (8-10)')
    f16_10_b = fields.Float('10. Tax on total income')
    f16_11_b = fields.Float('11. Tax on total income previous employer')
    f16_12_b = fields.Float('12. Rebate U/S 87A')
    f16_13_b = fields.Float('13. Tax Payable after rebate')
    f16_14_b = fields.Float('14. Surcharge ')
    f16_15_b = fields.Float('15. Cess @4%')
    f16_16_b = fields.Float('16. Tax Payable')
    working_days = fields.Float('No.of working Days')
    status = fields.Selection([('Draft','Draft'),('Approved By Payroll','Approved By Payroll'),('Approved',('Approved By Finance')),('Rejected','Rejected'),('On Hold','On Hold')],'Status',default='Draft')
    c_emp_branch = fields.Many2one('hr.branch','Branch')
    c_emp_department = fields.Many2one('hr.department','Department')
    c_employee_email = fields.Char('Email')
    c_employee_pf_id = fields.Char('PF Number')
    c_employee_uan = fields.Char('UAN')
    c_employee_account = fields.Char('Account Number')
    c_bank_name = fields.Char('Bank Name')
    c_ifsc = fields.Char('IFSC Code')
    c_bank_branch = fields.Char('Bank Branch Name')
    finance_remarks = fields.Char('Finance Remarks')
    c_internal_desig = fields.Char('Internal Designation')
    c_work_location = fields.Char('Work Location')
    c_branch_state = fields.Many2one('res.country.state','Branch State')
    c_work_mobile = fields.Char('Work Mobile')
    c_emp_pan = fields.Char('PAN')
    c_emp_aadhar = fields.Char('Aadhar Number')
    c_esi_number = fields.Char('ESI Number')
    c_pf_applicability = fields.Selection([('Yes','Yes'),('No','No')],'PF Applicable')
    c_esi_applicability = fields.Selection([('Yes','Yes'),('No','No')],'ESI Applicable')
    c_per_day_sal = fields.Float('Per Day Salary')
    c_total_deductions = fields.Float('Total Deductions')
    c_net_salary = fields.Float('Net Salary')
    medical_insurance_parents = fields.Float('Medical Insurance (Parents)')
    is_smi = fields.Boolean('Medical Insurance (Self) - Opted')
    is_pmi = fields.Boolean('Medical Insurance (Parents) - Opted')
    c_payroll_remarks = fields.Char('Payroll Remarks')
    c_final_remarks = fields.Char('Final Remarks')
    c_approved_payroll = fields.Boolean('Is Approved By Payroll')
    c_contract_id = fields.Many2one('hr.contract','Employee Contract')
    c_division = fields.Char('Division')
    c_pf_wage = fields.Float('PF Wage')
    c_esi_wage = fields.Float('ESI Wage')
    no_of_days_month = fields.Float('No of days for contract based on Employee Joining Date')
    approval_attachment = fields.Binary("Approval Attachment")


    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            emp_id = self.employee_id.id
            contract_rec = self.env['hr.contract'].sudo().search([('employee_id','=',emp_id),('c_active','=',True)],limit=1)
            if contract_rec:
                c_contract_id = contract_rec.id
                given_date = self.date
                year = datetime.strptime(given_date,'%Y-%m-%d').strftime('%Y')
                month = datetime.strptime(given_date,'%Y-%m-%d').strftime('%m')
                contract_start_date = contract_rec.date_start
                if not contract_start_date:
                    raise ValidationError("Contract start date is not given")
                contract_end_date = contract_rec.date_end
                if not contract_end_date:
                    raise ValidationError("Contract end date is not given")
                # no_of_days_month = relativedelta.relativedelta(datetime.strptime((contract_end_date), '%Y-%m-%d'),datetime.strptime(contract_start_date, '%Y-%m-%d')).days + 1
                no_of_contract_days = (datetime.strptime(contract_end_date,'%Y-%m-%d') - datetime.strptime(contract_start_date,'%Y-%m-%d')).days  + 1

                start_date = str(year) + '-04-01'
                end_date = str(int(year)+1) + '-03-31'
                no_of_months = relativedelta.relativedelta(datetime.strptime((end_date), '%Y-%m-%d'),datetime.strptime(given_date, '%Y-%m-%d')).months
                total_annual_days = (datetime.strptime(end_date,'%Y-%m-%d') - datetime.strptime(start_date,'%Y-%m-%d')).days  + 1

                join_date = self.employee_id.join_date
                if join_date <=start_date:
                    total_no_of_months = 12
                    total_emp_annual_days = total_annual_days
                else:
                    total_no_of_months = relativedelta.relativedelta(datetime.strptime((end_date), '%Y-%m-%d'),datetime.strptime(join_date, '%Y-%m-%d')).months
                    total_emp_annual_days = (datetime.strptime(end_date,'%Y-%m-%d') - datetime.strptime(join_date,'%Y-%m-%d')).days  + 1

                if join_date <= contract_start_date:
                    no_of_days_month = (datetime.strptime(contract_end_date,'%Y-%m-%d') - datetime.strptime(contract_start_date,'%Y-%m-%d')).days  + 1
                else:
                    no_of_days_month = (datetime.strptime(contract_end_date,'%Y-%m-%d') - datetime.strptime(join_date,'%Y-%m-%d')).days  + 1
                c_emp_branch = self.employee_id.branch_id and self.employee_id.branch_id.id or False
                c_emp_department = self.employee_id.sub_dep and self.employee_id.sub_dep.id
                c_division = self.employee_id.sub_dep and self.employee_id.sub_dep.name
                c_employee_email = self.employee_id.work_email
                c_employee_uan = self.employee_id.uan
                c_employee_account = self.employee_id.bank_account_id and self.employee_id.bank_account_id.acc_number
                c_bank_name = self.employee_id.bank_account_id and self.employee_id.bank_account_id.c_bank_name
                c_ifsc = self.employee_id.bank_account_id and self.employee_id.bank_account_id.ifsc_code
                c_bank_branch = self.employee_id.bank_account_id and self.employee_id.bank_account_id.branch_name
                c_internal_desig = self.employee_id.intrnal_desig
                c_work_location = self.employee_id.work_location
                c_branch_state = self.employee_id.branch_id and self.employee_id.branch_id.state_id and self.employee_id.branch_id.state_id.id
                c_work_mobile = self.employee_id.mobile_phone
                c_emp_pan = self.employee_id.pan
                c_emp_aadhar = self.employee_id.aadhar_no or ''            

                #Previous Months Components
                self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='BASIC' and pl.employee_id=%s",(start_date,given_date,emp_id,))
                pre_basic = self.env.cr.fetchone()[0]
                if not pre_basic:
                    pre_basic = 0
                self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='LTA' and pl.employee_id=%s",(start_date,given_date,emp_id,))
                pre_lta = self.env.cr.fetchone()[0]
                if not pre_lta:
                    pre_lta = 0
                self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('MEDA','CNV') and pl.employee_id=%s",(start_date,given_date,emp_id,))
                pre_med_cnv = self.env.cr.fetchone()[0]
                if not pre_med_cnv:
                    pre_med_cnv = 0
                self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('PTD') and pl.employee_id=%s",(start_date,given_date,emp_id,))
                previous_pt = self.env.cr.fetchone()[0]
                if not previous_pt:
                    previous_pt=0

                #Previous Gross Value
                self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('GROSS') and pl.employee_id=%s",(start_date,given_date,emp_id,))
                pre_earned_gross = self.env.cr.fetchone()[0]
                if not pre_earned_gross:
                    pre_earned_gross=0

                # self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='HRAMN' and pl.employee_id=%s",(start_date,given_date,emp_id,))
                # pre_hra = self.env.cr.fetchone()[0]
                # if not pre_hra:
                #     pre_hra = 0
                # self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='SA' and pl.employee_id=%s",(start_date,given_date,emp_id,))
                # pre_sa = self.env.cr.fetchone()[0]
                # if not pre_sa:
                #     pre_sa = 0

                #Previous Months HRA, we are not taking from payslips as in payslips it is calculated as 50% basic irrespective of the city of employee
                if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                    pre_hra = pre_basic*0.5
                else:
                    pre_hra = pre_basic*0.4

                #based on HRA, Special Allowance will change, so we are not taking previous special allownace from payslips
                pre_sa = pre_earned_gross - pre_basic - pre_lta - pre_hra - pre_med_cnv
                # pre_earned_gross = pre_med_cnv + pre_sa + pre_lta + pre_hra + pre_basic
                

            #CURRENT MONTH AND ESTIMATED MONTHS COMPONENTS

                ctc = contract_rec.actual_ctc
                bonus = contract_rec.bonus

                #LOP Calculations
                lop = contract_rec.lop
                lop_days = contract_rec.c_lop_days
                earned_wage = contract_rec.wage

                working_days = no_of_days_month - lop_days
                lop_days_amount = earned_wage*lop_days/no_of_days_month
                total_lop = lop + lop_days_amount
                c_per_day_sal = earned_wage/no_of_days_month                
                
                #PF Calculations Current Month and Estimated Months
                if contract_rec.pf_not_applicable == True:
                    current_pf = 0
                    estimated_pf = 0
                    c_pf_applicability = 'No'
                    c_employee_pf_id = ''
                    c_pf_wage=0
                else:
                    c_pf_wage=earned_wage*0.8
                    if c_pf_wage <=15000:
                        current_pf = earned_wage*0.8*0.12
                        c_pf_applicability = 'Yes'
                        c_employee_pf_id = self.employee_id.pf_id
                    else:
                        current_pf = 1800
                        c_pf_applicability = 'Yes'
                        c_employee_pf_id = self.employee_id.pf_id

                    if ctc*0.8 <= 15000:
                        estimated_pf = ctc*0.8*0.12*no_of_months
                    else:
                        estimated_pf = 1800*no_of_months

                #ESI Calculations
                esi_wage = earned_wage - current_pf
                if (esi_wage/1.0475) <= 21000:
                    current_esi_employer=(esi_wage*4.75)/104.75
                    current_esi_employee=(esi_wage*1.75)/104.75
                    c_esi_applicability = 'Yes'
                    c_esi_number = self.employee_id.c_esi_num
                else:
                    current_esi_employer = 0
                    current_esi_employee = 0
                    c_esi_applicability = 'No'
                    c_esi_number = ''

                earned_gross = earned_wage - current_pf - current_esi_employer
                earned_basic = earned_wage*0.4*working_days/no_of_days_month

                #PT Calculations Current Month and Estimated Months                
                if contract_rec.actual_ctc >= 20001:
                    final_current_pt = 200
                elif (contract_rec.actual_ctc <=20000 and contract_rec.actual_ctc >=15001):
                    final_current_pt = 150
                else:
                    final_current_pt = 0
                estimated_pt = final_current_pt*no_of_months
                final_pt = previous_pt + final_current_pt + estimated_pt

                #HRA Calculations Current Month
                if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                    earned_hra = earned_basic*0.5*working_days/no_of_days_month
                else:
                    earned_hra = earned_basic*0.4*working_days/no_of_days_month

                #Medical And Conveyance Current Month
                earned_med_con = 3333*working_days/no_of_days_month

                #LTA Current Month
                if (ctc*12 > 250000) and (ctc*12 <= 500000):
                    lta = 3000
                elif (ctc*12 > 500000) and (ctc*12 <= 1000000):
                    lta = 5000
                elif (ctc*12 > 1000000) and (ctc*12 <= 2000000):
                    lta = 7000
                elif (ctc*12 > 2000000):
                    lta = 8000
                else:
                    lta = 0
                earned_lta = lta*(working_days)/no_of_days_month

                #Special Allowance Current Month
                earned_sa = earned_gross - earned_basic - earned_lta - earned_hra - earned_med_con

                #Other Allowances and Deductions from Contracts Current Month
                arrears = contract_rec.arre_id
                byod_allowance = contract_rec.byod_allowance
                variable_pay = contract_rec.variable_pay
                special_incentive = contract_rec.special_incentive
                general_recovery = contract_rec.general_recovery
                incentive_recovery = contract_rec.incentive_recovery
                advance = contract_rec.amt_adv
                medical_insurance = contract_rec.medical_insurance
                medical_insurance_parents = contract_rec.medical_insurance_parents or 0
                is_smi = contract_rec.is_smi or False
                is_pmi = contract_rec.is_pmi or False
                perquisites_allowance = contract_rec.perquisits_allowance
                perquisites_deduction = contract_rec.perquisits_deduction
                lieu_allowance = contract_rec.lieu_allowance
                lieu_deduction = contract_rec.lieu_deduction
                current_tds = contract_rec.tds

                c_total_deductions = general_recovery + incentive_recovery + advance + medical_insurance + medical_insurance_parents + final_pt + total_lop + current_esi_employee + current_pf + current_tds
                c_net_salary = earned_gross - c_total_deductions


                #ESTIMATED COMPONENTS
                estimated_gross = ctc*no_of_months
                estimated_basic = ctc*0.4*no_of_months
                if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                    estimated_hra = estimated_basic*0.5
                else:
                    estimated_hra = estimated_basic*0.4

                estimated_med_con = 3333*no_of_months
                estimated_lta = lta*no_of_months
                estimated_sa = estimated_gross - estimated_basic - estimated_lta - estimated_hra - estimated_med_con

                #HRA CAlculations 1
                if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                    hra_basic_cal= (pre_basic + estimated_basic + earned_basic)*0.5
                else:
                    hra_basic_cal=(pre_basic + estimated_basic + earned_basic)*0.4

                actual_hra=pre_hra + earned_hra + estimated_hra 
                
            else:
                raise ValidationError("There is no contract for the Employee selected")

            f16_1_a_b = pre_earned_gross + earned_gross + estimated_gross

            #SAVINGS COMPONENTS
            saving_ids = self.env['employee.saving'].search([('employee_id','=',emp_id)])


            if saving_ids:
                saving_ids=saving_ids[0]
                pre_earning=saving_ids.gross_income_previous
                other_income=saving_ids.other_income_amount
                sec24=saving_ids.income_house_amount
                sav_80c=saving_ids.ded80c_amount
                sav_80d=saving_ids.bill_amount
                sav_80e=saving_ids.interest_education_loan
                sav_80g=saving_ids.donation_ded
                sav_80ee=saving_ids.interest_resident_loan
                sav_80ccd=saving_ids.nps_passbook
                hra_dec=saving_ids.hra_receipt_amount
                resident=saving_ids.resident
                lta_dec=saving_ids.leave_travel_allowance
                pre_pf=saving_ids.ded_previous_emp
                pre_tds=saving_ids.income_tax_paid
                pre_pt=saving_ids.professional_tax_previous
                self.env.cr.execute("select amount from other_source_income where income_source='2' and income_id=%s",(saving_ids.id,))
                tot_80tta_cal = self.env.cr.fetchone()[0]
                tot_80tta = min(tot_80tta_cal,10000)
                self.env.cr.execute("select sum(amount) from medical_bill_line where bill_id=%s and reference not in ('80D (Mediclaim- upto Rs. 50000 for Senior Citizen Parents(above 60 years of age))','80DD - Medical treatment for handicapped dependent (with < 80%% disability - Rs 75000 or > 80%% disability - Rs 1,25000, pl. specify)') ",(saving_ids.id,))
                tot_80d_cal = self.env.cr.fetchone()[0]
                tot_80d = min(tot_80d_cal,55000)
                self.env.cr.execute("select sum(amount) from medical_bill_line where bill_id=%s and reference like '%%handicapped%%'",(saving_ids.id,))
                tot_80dd = self.env.cr.fetchone()[0]
                self.env.cr.execute("select sum(amount) from medical_bill_line where bill_id=%s and reference = '80D (Mediclaim- upto Rs. 50000 for Senior Citizen Parents(above 60 years of age))'",(saving_ids.id,))
                tot_80ddb_cal = self.env.cr.fetchone()[0]
                tot_80ddb = min(tot_80ddb_cal,50000)
                self.env.cr.execute("select sum(amount) from other_source_income where income_source !='1' and income_id=%s",(saving_ids.id,))
                tot_other_income = self.env.cr.fetchone()[0]
                self.env.cr.execute("select sum(amount) from other_source_income where income_source ='1' and income_id=%s",(saving_ids.id,))
                tot_house_rent_income = self.env.cr.fetchone()[0]
                final_other_income = pre_earning + tot_house_rent_income + tot_other_income

                hra_dec = hra_dec * total_emp_annual_days/total_annual_days
                rent_dec=hra_dec-((earned_basic + pre_basic + estimated_basic)*0.1)
                final_hra=min(hra_basic_cal,actual_hra,rent_dec)

            else:
                pre_earning=0
                other_income=0
                sec24=0
                sav_80c=0
                sav_80d=0
                sav_80e=0
                sav_80g=0
                sav_80ee=0
                sav_80ccd=0
                hra_dec=0
                resident=0
                lta_dec=0
                pre_pf=0
                pre_tds=0
                pre_pt=0
                tot_80tta = 0
                tot_80d = 0
                tot_80dd = 0
                tot_other_income = 0
                tot_house_rent_income = 0
                tot_80ddb = 0
                final_other_income = 0
                rent_dec = 0
                final_hra = 0            

            #LTA Calculations
            if lta_dec != 0:
                final_lta = min(lta_dec,(pre_lta + earned_lta + estimated_lta))
            else:
                final_lta = 0

            #Medical and Conveyance
            standard_deductions = pre_med_cnv + estimated_med_con + earned_med_con

            #HOME LOAN INTEREST
            final_sec24 = min(sec24,200000)

            #5. Add: Any other income reported by the employee

            #6. Gross Total income (1+5) -(2+3+4)
            gross_total_income = (f16_1_a_b + final_other_income) - (final_hra + final_lta + standard_deductions + pre_pt + final_pt + final_sec24) + perquisites_allowance + lieu_allowance - perquisites_deduction - lieu_deduction

            #(A) sections 80C, 80CCC and 80CCD
            self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('PF') and pl.employee_id=%s",(start_date,given_date,emp_id,))
            previous_pf = self.env.cr.fetchone()[0]
            if not previous_pf:
                previous_pf = 0

            employee_pf_contribution = previous_pf + current_pf + estimated_pf
            pf_comp = employee_pf_contribution + pre_pf + sav_80c
            sec_80c_total = min(pf_comp,150000)
            final_80ee = min(sav_80ee,50000)
            final_80g = sav_80g*0.5
            total_chapter_6_a = sav_80ccd + tot_80d + tot_80dd + tot_80ddb + final_80ee + tot_80tta + final_80g + sav_80e

            aggr_6a = sec_80c_total + total_chapter_6_a
            total_income = gross_total_income - aggr_6a
            total_savings = final_sec24 + sav_80e + final_80ee + sav_80ccd + final_80g + tot_80d + sec_80c_total

            if total_income<250000:
                tax_on_total_income = 0
            elif (total_income < 500000 and total_income>=250000):
                tax_on_total_income = (total_income-250000)*0.05
            elif (total_income < 1000000 and total_income >= 500000):
                tax_on_total_income = (total_income-500000)*0.2 + 12500
            else:
                tax_on_total_income = (total_income-1000000)*0.3 + 112500

            if total_income <= 350000:
                rebate = min(tax_on_total_income,2500)
            else:
                rebate = 0

            tax_payable_after_rebate = tax_on_total_income + pre_tds + rebate

            if (total_income>5000000 and total_income<=10000000):
                surcharge = tax_payable_after_rebate*0.1
            elif total_income >10000000:
                surcharge = tax_payable_after_rebate*0.15
            else:
                surcharge = 0
            cess = (tax_payable_after_rebate + surcharge)*0.04

            total_tax_payable = tax_payable_after_rebate + surcharge + cess
            tax_per_month = total_tax_payable/total_no_of_months

            self.emp_id = self.employee_id.nf_emp
            self.wage = earned_wage
            self.basic = earned_basic
            self.hra = earned_hra
            self.medical_conveyance = earned_med_con
            self.special_allowance = earned_sa
            self.lt_allowance = earned_lta
            self.gross = earned_gross
            self.join_date = join_date
            self.arrears = arrears
            self.byod = byod_allowance
            self.variable_pay = variable_pay
            self.special_incentive = special_incentive
            self.general_recovery = general_recovery
            self.incentive_recovery = incentive_recovery
            self.advance = advance
            self.pf_employee = current_pf
            self.pf_employer = current_pf
            self.esic_employee = current_esi_employee
            self.esic_employer = current_esi_employer
            self.professional_tax = final_current_pt
            self.lop = total_lop
            self.absent_days = lop_days
            self.medical_insurance = medical_insurance
            self.medical_insurance_parents = medical_insurance_parents
            self.is_smi = is_smi
            self.is_pmi = is_pmi
            self.saving_hra = final_hra
            self.saving_lta = final_lta
            self.total_savings = total_savings
            self.total_pf = employee_pf_contribution
            self.total_pt = final_pt
            self.taxable_income = total_income
            self.rebate = rebate
            self.surcharge = surcharge
            self.cess = cess
            self.annual_tax = total_tax_payable
            self.tds = tax_per_month
            self.f16_pre_basic = pre_basic
            self.f16_pre_hra = pre_hra
            self.f16_pre_lta = pre_lta
            self.f16_pre_special_allowance = pre_sa
            self.f16_pre_med_conv = pre_med_cnv
            self.f16_pre_earned_gross = pre_earned_gross
            self.f16_curr_earned_gross = earned_gross
            self.f16_curr_basic = earned_basic
            self.f16_curr_hra = earned_hra
            self.f16_curr_med_conv = earned_med_con
            self.f16_curr_lta = earned_lta
            self.f16_curr_special_allowance = earned_sa
            self.f16_estm_basic = estimated_basic
            self.f16_estm_hra = estimated_hra
            self.f16_estm_med_conv = estimated_med_con
            self.f16_estm_lta = estimated_lta
            self.f16_estm_special_allowance = estimated_sa
            self.f16_estm_earned_gross = estimated_gross
            self.working_days = working_days
            self.f16_1_a_b = f16_1_a_b
            self.f16_1_b_b = perquisites_allowance
            self.f16_1_b_c = perquisites_deduction
            self.f16_1_c_b = lieu_allowance
            self.f16_1_c_c = lieu_deduction
            self.f16_2_1_a = actual_hra
            self.f16_2_3_a = hra_basic_cal
            self.f16_2_a_c = final_hra
            self.f16_2_2_a = rent_dec
            self.f16_2_b_a = final_lta
            self.f16_2_b_c = final_lta
            self.f16_2_c_a = standard_deductions
            self.f16_2_c_c = standard_deductions
            self.f16_3_b_a = final_pt
            self.f16_3_b_c = final_pt
            self.f16_3_c_a = pre_pt
            self.f16_3_c_c = pre_pt
            self.f16_4_a_a = final_sec24
            self.f16_4_a_c = final_sec24
            self.f16_5_a_a = pre_earning
            self.f16_5_b_a = tot_house_rent_income
            self.f16_5_c_a = tot_other_income
            self.f16_5_d_b = final_other_income
            self.f16_6_a_b = gross_total_income
            self.f16_7_a_1_a = employee_pf_contribution
            self.f16_7_a_2_a = pre_pf
            self.f16_7_a_3_a = sav_80c
            self.f16_7_a_4_a = pf_comp
            self.f16_7_a_4_c = sec_80c_total
            self.f16_7_b_1_a = sav_80ccd
            self.f16_7_b_2_a = tot_80d
            self.f16_7_b_3_a = tot_80dd
            self.f16_7_b_4_a = tot_80ddb
            self.f16_7_b_5_a = sav_80e
            self.f16_7_b_6_a = final_80ee
            self.f16_7_b_7_a = tot_80tta
            self.f16_7_b_8_a = final_80g
            self.f16_7_b_9_a = total_chapter_6_a
            self.f16_7_b_9_c = total_chapter_6_a
            self.f16_8_a = aggr_6a
            self.f16_9_b = total_income
            self.f16_10_b = tax_on_total_income
            self.f16_11_b = pre_tds
            self.f16_12_b = rebate
            self.f16_13_b = tax_payable_after_rebate
            self.f16_14_b = surcharge
            self.f16_15_b = cess
            self.f16_16_b = total_tax_payable
            self.c_emp_branch = c_emp_branch
            self.c_emp_department = c_emp_department
            self.c_employee_email = c_employee_email
            self.c_employee_pf_id = c_employee_pf_id
            self.c_employee_uan = c_employee_uan
            self.c_employee_account = c_employee_account
            self.c_bank_name = c_bank_name
            self.c_ifsc = c_ifsc
            self.c_bank_branch = c_bank_branch
            self.bonus = bonus
            self.c_internal_desig = c_internal_desig
            self.c_work_location = c_work_location
            self.c_branch_state = c_branch_state
            self.c_work_mobile = c_work_mobile
            self.c_emp_pan = c_emp_pan
            self.c_emp_aadhar = c_emp_aadhar
            self.c_esi_number = c_esi_number
            self.c_pf_applicability = c_pf_applicability
            self.c_esi_applicability = c_esi_applicability
            self.c_per_day_sal = c_per_day_sal
            self.c_total_deductions = c_total_deductions
            self.c_net_salary = c_net_salary
            self.status = 'Draft'
            self.c_contract_id = c_contract_id
            self.ctc = ctc
            self.c_division = c_division
            self.c_pf_wage = c_pf_wage
            self.c_esi_wage = esi_wage
            self.no_of_days_month = no_of_days_month
            


#AUTOMATION SCRIPT TO CREATE PAYSLIP COMPONENTS AND FORM16
    @api.model
    def nf_generate_payslip_components(self):
        print "nf_generate_payslip_components"
        nf_payslip_components = self.env['nf.payslip.components']
        self.env.cr.execute("select id from hr_contract where c_active='t'")
        contract_list = self.env.cr.dictfetchall()
        i=0
        while i<len(contract_list):
	    print "i",i,len(contract_list)
            c_contract_id = contract_list[i]['id']
            print "c_contract_id",c_contract_id

            #CURRENT MONTH AND ESTIMATED MONTHS COMPONENTS
            contract_rec = self.env['hr.contract'].sudo().search([('id','=',c_contract_id),('c_active','=',True)],limit=1)
            given_date = str(datetime.now().date())
            year = datetime.strptime(given_date,'%Y-%m-%d').strftime('%Y')
            month = datetime.strptime(given_date,'%Y-%m-%d').strftime('%m')
            month_name = datetime.strptime(given_date,'%Y-%m-%d').strftime('%B')
            name = "Payroll Components and Form16 for " + str(contract_rec.employee_id.name) + " - " + str(month_name) + " - " + str(year)
            contract_start_date = contract_rec.date_start
            if not contract_start_date:
                contract_start_date = given_date
            contract_end_date = contract_rec.date_end
            if not contract_end_date:
                contract_end_date = contract_start_date
            no_of_contract_days = (datetime.strptime(contract_end_date,'%Y-%m-%d') - datetime.strptime(contract_start_date,'%Y-%m-%d')).days  + 1
            # no_of_days_month = relativedelta.relativedelta(datetime.strptime((contract_end_date), '%Y-%m-%d'),datetime.strptime(contract_start_date, '%Y-%m-%d')).days + 1
            # no_of_days_month = calendar.monthrange(int(year),int(month))[1]
            start_date = str(year) + '-04-01'
            end_date = str(int(year)+1) + '-03-31'
            no_of_months = relativedelta.relativedelta(datetime.strptime((end_date), '%Y-%m-%d'),datetime.strptime(given_date, '%Y-%m-%d')).months

            total_annual_days = (datetime.strptime(end_date,'%Y-%m-%d') - datetime.strptime(start_date,'%Y-%m-%d')).days  + 1
            emp_id = contract_rec.employee_id.id
            nf_emp = contract_rec.employee_id.nf_emp
            c_emp_branch = contract_rec.employee_id.branch_id and contract_rec.employee_id.branch_id.id or False
            c_emp_department = contract_rec.employee_id.sub_dep and contract_rec.employee_id.sub_dep.id or False
            c_division = contract_rec.employee_id.sub_dep and contract_rec.employee_id.sub_dep.name or False
            c_employee_email = contract_rec.employee_id.work_email or "NA"
            c_employee_uan = contract_rec.employee_id.uan or "NA"
            c_employee_account = contract_rec.employee_id.bank_account_id and contract_rec.employee_id.bank_account_id.acc_number or "NA"
            c_bank_name = contract_rec.employee_id.bank_account_id and contract_rec.employee_id.bank_account_id.c_bank_name or "NA"
            c_ifsc = contract_rec.employee_id.bank_account_id and contract_rec.employee_id.bank_account_id.ifsc_code or "NA"
            c_bank_branch = contract_rec.employee_id.bank_account_id and contract_rec.employee_id.bank_account_id.branch_name or "NA"
            bonus = contract_rec.bonus
            c_internal_desig = contract_rec.employee_id.intrnal_desig
            c_work_location = contract_rec.employee_id.work_location
            c_branch_state = contract_rec.employee_id.branch_id and contract_rec.employee_id.branch_id.state_id and contract_rec.employee_id.branch_id.state_id.id
            c_internal_desig = contract_rec.employee_id.intrnal_desig
            c_work_location = contract_rec.employee_id.work_location
            c_work_mobile = contract_rec.employee_id.mobile_phone
            c_emp_pan = contract_rec.employee_id.pan
            c_emp_aadhar = contract_rec.employee_id.aadhar_no
            
            join_date = contract_rec.employee_id.join_date
            if join_date<=start_date:
                total_no_of_months = 12
                total_emp_annual_days = total_annual_days
            else:
                total_no_of_months = relativedelta.relativedelta(datetime.strptime((end_date), '%Y-%m-%d'),datetime.strptime(join_date, '%Y-%m-%d')).months
                total_emp_annual_days = (datetime.strptime(end_date,'%Y-%m-%d') - datetime.strptime(join_date,'%Y-%m-%d')).days  + 1

            if join_date <= contract_start_date:
                no_of_days_month = (datetime.strptime(contract_end_date,'%Y-%m-%d') - datetime.strptime(contract_start_date,'%Y-%m-%d')).days  + 1
            else:
                no_of_days_month = (datetime.strptime(contract_end_date,'%Y-%m-%d') - datetime.strptime(join_date,'%Y-%m-%d')).days  + 1            

            #Previous Months Components
            self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='BASIC' and pl.employee_id=%s",(start_date,given_date,emp_id,))
            pre_basic = self.env.cr.fetchone()[0]
            if not pre_basic:
                pre_basic = 0
            self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='LTA' and pl.employee_id=%s",(start_date,given_date,emp_id,))
            pre_lta = self.env.cr.fetchone()[0]
            if not pre_lta:
                pre_lta = 0
            self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('MEDA','CNV') and pl.employee_id=%s",(start_date,given_date,emp_id,))
            pre_med_cnv = self.env.cr.fetchone()[0]
            if not pre_med_cnv:
                pre_med_cnv = 0
            self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('PTD') and pl.employee_id=%s",(start_date,given_date,emp_id,))
            previous_pt = self.env.cr.fetchone()[0]
            if not previous_pt:
                previous_pt=0


            #Previous Gross Value
            self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('GROSS') and pl.employee_id=%s",(start_date,given_date,emp_id,))
            pre_earned_gross = self.env.cr.fetchone()[0]
            if not pre_earned_gross:
                pre_earned_gross=0

            # self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='HRAMN' and pl.employee_id=%s",(start_date,given_date,emp_id,))
            # pre_hra = self.env.cr.fetchone()[0]
            # if not pre_hra:
            #     pre_hra = 0
            # self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code='SA' and pl.employee_id=%s",(start_date,given_date,emp_id,))
            # pre_sa = self.env.cr.fetchone()[0]
            # if not pre_sa:
            #     pre_sa = 0

            #Previous Months HRA, we are not taking from payslips as in payslips it is calculated as 50% basic irrespective of the city of employee
            if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                pre_hra = pre_basic*0.5
            else:
                pre_hra = pre_basic*0.4

            #based on HRA, Special Allowance will change, so we are not taking previous special allownace from payslips
            pre_sa = pre_earned_gross - pre_basic - pre_lta - pre_hra - pre_med_cnv
            # pre_earned_gross = pre_med_cnv + pre_sa + pre_lta + pre_hra + pre_basic


            ctc = contract_rec.actual_ctc

            #LOP Calculations
            lop = contract_rec.lop
            lop_days = contract_rec.c_lop_days
            working_days = no_of_days_month - lop_days
            earned_wage = contract_rec.wage
            lop_days_amount = earned_wage*lop_days/no_of_days_month
            total_lop = lop + lop_days_amount

            c_per_day_sal = earned_wage/no_of_days_month
            
            #PF Calculations Current Month and Estimated Months
            if contract_rec.pf_not_applicable == True:
                current_pf = 0
                estimated_pf = 0
                c_pf_applicability = 'No'
                c_pf_wage = 0
                c_employee_pf_id = ''
            else:
                c_pf_wage = earned_wage*0.8
                if c_pf_wage <=15000:
                    current_pf = c_pf_wage*0.12
                    c_pf_applicability = 'Yes'
                    c_employee_pf_id = contract_rec.employee_id.pf_id or "NA"
                else:
                    current_pf = 1800*no_of_days_month/no_of_contract_days
                    c_pf_applicability = 'Yes'
                    c_employee_pf_id = contract_rec.employee_id.pf_id or "NA"
                if ctc*0.8 <= 15000:
                    estimated_pf = ctc*0.8*0.12*no_of_months
                else:
                    estimated_pf = 1800*no_of_months


            #ESI Calculations
            esi_wage = earned_wage - current_pf
            if (esi_wage/1.0475) <= 21000:
                current_esi_employer=(esi_wage*4.75)/104.75
                current_esi_employee=(esi_wage*1.75)/104.75
                c_esi_applicability = 'Yes'
                c_esi_number = contract_rec.employee_id.c_esi_num
            else:
                current_esi_employer = 0
                current_esi_employee = 0
                c_esi_applicability = 'No'
                c_esi_number = ''

            earned_gross = earned_wage - current_pf - current_esi_employer
            earned_basic = earned_wage*0.4*working_days/no_of_days_month

            #PT Calculations Current Month and Estimated Months                
            if contract_rec.actual_ctc >= 20001:
                final_current_pt = 200
            elif (contract_rec.actual_ctc <=20000 and contract_rec.actual_ctc >=15001):
                final_current_pt = 150
            else:
                final_current_pt = 0
            estimated_pt = final_current_pt*no_of_months
            final_pt = previous_pt + final_current_pt + estimated_pt

            #HRA Calculations Current Month
            if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                earned_hra = earned_basic*0.5*working_days/no_of_days_month
            else:
                earned_hra = earned_basic*0.4*working_days/no_of_days_month

            #Medical And Conveyance Current Month
            earned_med_con = 3333*working_days/no_of_days_month

            #LTA Current Month
            if (ctc*12 > 250000) and (ctc*12 <= 500000):
                lta = 3000
            elif (ctc*12 > 500000) and (ctc*12 <= 1000000):
                lta = 5000
            elif (ctc*12 > 1000000) and (ctc*12 <= 2000000):
                lta = 7000
            elif (ctc*12 > 2000000):
                lta = 8000
            else:
                lta = 0
            earned_lta = lta*(working_days)/no_of_days_month

            #Special Allowance Current Month
            earned_sa = earned_gross - earned_basic - earned_lta - earned_hra - earned_med_con

            #Other Allowances and Deductions from Contracts Current Month
            arrears = contract_rec.arre_id
            byod_allowance = contract_rec.byod_allowance
            variable_pay = contract_rec.variable_pay
            special_incentive = contract_rec.special_incentive
            general_recovery = contract_rec.general_recovery
            incentive_recovery = contract_rec.incentive_recovery
            advance = contract_rec.amt_adv
            medical_insurance = contract_rec.medical_insurance
            medical_insurance_parents = contract_rec.medical_insurance_parents
            is_smi = contract_rec.is_smi
            is_pmi = contract_rec.is_pmi
            perquisites_allowance = contract_rec.perquisits_allowance
            perquisites_deduction = contract_rec.perquisits_deduction
            lieu_allowance = contract_rec.lieu_allowance
            lieu_deduction = contract_rec.lieu_deduction
            current_tds = contract_rec.tds
            c_total_deductions = general_recovery + incentive_recovery + advance + medical_insurance + medical_insurance_parents + final_pt + total_lop + current_esi_employee + current_pf + current_tds
            c_net_salary = earned_gross - c_total_deductions

            #ESTIMATED COMPONENTS
            estimated_gross = ctc*no_of_months
            estimated_basic = ctc*0.4*no_of_months
            if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                estimated_hra = estimated_basic*0.5
            else:
                estimated_hra = estimated_basic*0.4

            estimated_med_con = 3333*no_of_months
            estimated_lta = lta*no_of_months
            estimated_sa = estimated_gross - estimated_basic - estimated_lta - estimated_hra - estimated_med_con

            #HRA CAlculations 1
            if contract_rec.employee_id.q_city_id and contract_rec.employee_id.q_city_id.name in ['New Delhi','Mumbai','Chennai','Kolkata']:
                hra_basic_cal= (pre_basic + estimated_basic + earned_basic)*0.5
            else:
                hra_basic_cal=(pre_basic + estimated_basic + earned_basic)*0.4

            actual_hra=pre_hra + earned_hra + estimated_hra 
            
            f16_1_a_b = pre_earned_gross + earned_gross + estimated_gross

        #SAVINGS COMPONENTS
            saving_ids = self.env['employee.saving'].search([('employee_id','=',emp_id)])

            if saving_ids:
                saving_ids=saving_ids[0]
                pre_earning=saving_ids.gross_income_previous
                other_income=saving_ids.other_income_amount
                sec24=saving_ids.income_house_amount
                sav_80c=saving_ids.ded80c_amount
                sav_80d=saving_ids.bill_amount
                sav_80e=saving_ids.interest_education_loan
                sav_80g=saving_ids.donation_ded
                sav_80ee=saving_ids.interest_resident_loan
                sav_80ccd=saving_ids.nps_passbook
                hra_dec=saving_ids.hra_receipt_amount
                resident=saving_ids.resident
                lta_dec=saving_ids.leave_travel_allowance
                pre_pf=saving_ids.ded_previous_emp
                pre_tds=saving_ids.income_tax_paid
                pre_pt=saving_ids.professional_tax_previous
                self.env.cr.execute("select amount from other_source_income where income_source='2' and income_id=%s",(saving_ids.id,))
                tot_80tta_cal = self.env.cr.fetchone()
                if tot_80tta_cal:
                    tot_80tta_cal = tot_80tta_cal[0]
                    if tot_80tta_cal == None:
                        tot_80tta_cal = 0
                else:
                    tot_80tta_cal = 0
                tot_80tta = min(tot_80tta_cal,10000)
                self.env.cr.execute("select sum(amount) from medical_bill_line where bill_id=%s and reference not in ('80D (Mediclaim- upto Rs. 50000 for Senior Citizen Parents(above 60 years of age))','80DD - Medical treatment for handicapped dependent (with < 80%% disability - Rs 75000 or > 80%% disability - Rs 1,25000, pl. specify)') ",(saving_ids.id,))
                tot_80d_cal = self.env.cr.fetchone()
                if tot_80d_cal:
                    tot_80d_cal = tot_80d_cal[0]
                    if tot_80d_cal == None:
                        tot_80d_cal = 0
                else:
                    tot_80d_cal = 0
                tot_80d = min(tot_80d_cal,55000)
                self.env.cr.execute("select sum(amount) from medical_bill_line where bill_id=%s and reference like '%%handicapped%%'",(saving_ids.id,))
                tot_80dd = self.env.cr.fetchone()
                if tot_80dd:
                    tot_80dd = tot_80dd[0]
                    if tot_80dd == None:
                        tot_80dd = 0
                else:
                    tot_80dd=0
                self.env.cr.execute("select sum(amount) from medical_bill_line where bill_id=%s and reference = '80D (Mediclaim- upto Rs. 50000 for Senior Citizen Parents(above 60 years of age))'",(saving_ids.id,))
                tot_80ddb_cal = self.env.cr.fetchone()
                if tot_80ddb_cal:
                    tot_80ddb_cal = tot_80ddb_cal[0]
                    if tot_80ddb_cal == None:
                        tot_80ddb_cal = 0
                else:
                    tot_80ddb_cal = 0
                tot_80ddb = min(tot_80ddb_cal,50000)
                self.env.cr.execute("select sum(amount) from other_source_income where income_source !='1' and income_id=%s",(saving_ids.id,))
                tot_other_income = self.env.cr.fetchone()
                if tot_other_income:
                    tot_other_income = tot_other_income[0]
                    if tot_other_income == None:
                        tot_other_income = 0
                else:
                    tot_other_income = 0
                self.env.cr.execute("select sum(amount) from other_source_income where income_source ='1' and income_id=%s",(saving_ids.id,))
                tot_house_rent_income = self.env.cr.fetchone()
                if tot_house_rent_income:
                    tot_house_rent_income = tot_house_rent_income[0]
                    if tot_house_rent_income == None:
                        tot_house_rent_income = 0
                else:
                    tot_house_rent_income = 0
                print "pre_earning + tot_house_rent_income + tot_other_income",pre_earning,tot_house_rent_income,tot_other_income
                final_other_income = pre_earning + tot_house_rent_income + tot_other_income

                hra_dec = hra_dec*total_emp_annual_days/total_annual_days
                rent_dec=hra_dec-((earned_basic + pre_basic + estimated_basic)*0.1)
                final_hra=min(hra_basic_cal,actual_hra,rent_dec)

            else:
                pre_earning=0
                other_income=0
                sec24=0
                sav_80c=0
                sav_80d=0
                sav_80e=0
                sav_80g=0
                sav_80ee=0
                sav_80ccd=0
                hra_dec=0
                resident=0
                lta_dec=0
                pre_pf=0
                pre_tds=0
                pre_pt=0
                tot_80tta = 0
                tot_80d = 0
                tot_80dd = 0
                tot_other_income = 0
                tot_house_rent_income = 0
                tot_80ddb = 0
                final_other_income = 0
                rent_dec = 0
                final_hra = 0            


            #LTA Calculations
            if lta_dec != 0:
                final_lta = min(lta_dec,(pre_lta + earned_lta + estimated_lta))
            else:
                final_lta = 0

            #Medical and Conveyance
            standard_deductions = pre_med_cnv + estimated_med_con + earned_med_con

            #HOME LOAN INTEREST
            final_sec24 = min(sec24,200000)

            #5. Add: Any other income reported by the employee

            #6. Gross Total income (1+5) -(2+3+4)
            gross_total_income = (f16_1_a_b + final_other_income) - (final_hra + final_lta + standard_deductions + pre_pt + final_pt + final_sec24) + perquisites_allowance + lieu_allowance - perquisites_deduction - lieu_deduction

            #(A) sections 80C, 80CCC and 80CCD
            self.env.cr.execute("select sum(pl.total) from hr_payslip_line pl,hr_payslip py where pl.slip_id=py.id and py.date_from >=%s and py.date_from <%s and pl.code in ('PF') and pl.employee_id=%s",(start_date,given_date,emp_id,))
            previous_pf = self.env.cr.fetchone()[0]
            if not previous_pf:
                previous_pf = 0

            employee_pf_contribution = previous_pf + current_pf + estimated_pf
            pf_comp = employee_pf_contribution + pre_pf + sav_80c
            sec_80c_total = min(pf_comp,150000)
            final_80ee = min(sav_80ee,50000)
            final_80g = sav_80g*0.5
            total_chapter_6_a = sav_80ccd + tot_80d + tot_80dd + tot_80ddb + final_80ee + tot_80tta + final_80g + sav_80e

            aggr_6a = sec_80c_total + total_chapter_6_a
            total_income = gross_total_income - aggr_6a
            total_savings = final_sec24 + sav_80e + final_80ee + sav_80ccd + final_80g + tot_80d + sec_80c_total

            if total_income<250000:
                tax_on_total_income = 0
            elif (total_income < 500000 and total_income>=250000):
                tax_on_total_income = (total_income-250000)*0.05
            elif (total_income < 1000000 and total_income >= 500000):
                tax_on_total_income = (total_income-500000)*0.2 + 12500
            else:
                tax_on_total_income = (total_income-1000000)*0.3 + 112500

            if total_income <= 350000:
                rebate = min(tax_on_total_income,2500)
            else:
                rebate = 0

            tax_payable_after_rebate = tax_on_total_income + pre_tds + rebate

            if (total_income>5000000 and total_income<=10000000):
                surcharge = tax_payable_after_rebate*0.1
            elif total_income >10000000:
                surcharge = tax_payable_after_rebate*0.15
            else:
                surcharge = 0
            cess = (tax_payable_after_rebate + surcharge)*0.04

            total_tax_payable = tax_payable_after_rebate + surcharge + cess
            tax_per_month = total_tax_payable/total_no_of_months

            self.env.cr.execute("insert into nf_payslip_components (name,date,employee_id,emp_id,wage,basic,hra,medical_conveyance,special_allowance,lt_allowance,gross,join_date,arrears,byod,variable_pay,special_incentive,general_recovery,incentive_recovery,advance,pf_employee,pf_employer,esic_employee,esic_employer,professional_tax,lop,absent_days,medical_insurance,saving_hra,saving_lta,total_savings,total_pf,total_pt,taxable_income,rebate,surcharge,cess,annual_tax,tds,f16_pre_basic,f16_pre_hra,f16_pre_lta,f16_pre_special_allowance,f16_pre_med_conv,f16_pre_earned_gross,f16_curr_earned_gross,f16_curr_basic,f16_curr_hra,f16_curr_med_conv,f16_curr_lta,f16_curr_special_allowance,f16_estm_basic,f16_estm_hra,f16_estm_med_conv,f16_estm_lta,f16_estm_special_allowance,f16_estm_earned_gross,working_days,f16_1_a_b,f16_1_b_b,f16_1_b_c,f16_1_c_b,f16_1_c_c,f16_2_1_a,f16_2_3_a,f16_2_a_c,f16_2_2_a,f16_2_b_a,f16_2_b_c,f16_2_c_a,f16_2_c_c,f16_3_b_a,f16_3_b_c,f16_3_c_a,f16_3_c_c,f16_4_a_a,f16_4_a_c,f16_5_a_a,f16_5_b_a,f16_5_c_a,f16_5_d_b,f16_6_a_b,f16_7_a_1_a,f16_7_a_2_a,f16_7_a_3_a,f16_7_a_4_a,f16_7_a_4_c,f16_7_b_1_a,f16_7_b_2_a,f16_7_b_3_a,f16_7_b_4_a,f16_7_b_5_a,f16_7_b_6_a,f16_7_b_7_a,f16_7_b_8_a,f16_7_b_9_a,f16_7_b_9_c,f16_8_a,f16_9_b,f16_10_b,f16_11_b,f16_12_b,f16_13_b,f16_14_b,f16_15_b,f16_16_b,c_emp_branch,c_emp_department,c_employee_email,c_employee_pf_id,c_employee_uan,c_employee_account,c_bank_name,c_bank_branch,bonus,c_internal_desig,c_work_location,c_branch_state,c_work_mobile,c_emp_pan,c_emp_aadhar,c_esi_number,c_pf_applicability,c_esi_applicability,c_per_day_sal,c_ifsc,c_total_deductions,c_net_salary,medical_insurance_parents,is_smi,is_pmi,c_contract_id,ctc,c_division,c_pf_wage,c_esi_wage,no_of_days_month,status) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Draft')",(name,given_date,emp_id,nf_emp,earned_wage,earned_basic,earned_hra,earned_med_con,earned_sa,earned_lta,earned_gross,join_date,arrears,byod_allowance,variable_pay,special_incentive,general_recovery,incentive_recovery,advance,current_pf,current_pf,current_esi_employee,current_esi_employer,final_current_pt,total_lop,lop_days,medical_insurance,final_hra,final_lta,total_savings,employee_pf_contribution,final_pt,total_income,rebate,surcharge,cess,total_tax_payable,tax_per_month,pre_basic,pre_hra,pre_lta,pre_sa,pre_med_cnv,pre_earned_gross,earned_gross,earned_basic,earned_hra,earned_med_con,earned_lta,earned_sa,estimated_basic,estimated_hra,estimated_med_con,estimated_lta,estimated_sa,estimated_gross,working_days,f16_1_a_b,perquisites_allowance,perquisites_deduction,lieu_allowance,lieu_deduction,actual_hra,hra_basic_cal,final_hra,rent_dec,final_lta,final_lta,standard_deductions,standard_deductions,final_pt,final_pt,pre_pt,pre_pt,final_sec24,final_sec24,pre_earning,tot_house_rent_income,tot_other_income,final_other_income,gross_total_income,employee_pf_contribution,pre_pf,sav_80c,pf_comp,sec_80c_total,sav_80ccd,tot_80d,tot_80dd,tot_80ddb,sav_80e,final_80ee,tot_80tta,final_80g,total_chapter_6_a,total_chapter_6_a,aggr_6a,total_income,tax_on_total_income,pre_tds,rebate,tax_payable_after_rebate,surcharge,cess,total_tax_payable,c_emp_branch,c_emp_department,c_employee_email,c_employee_pf_id,c_employee_uan,c_employee_account,c_bank_name,c_bank_branch,bonus,c_internal_desig,c_work_location,c_branch_state,c_work_mobile,c_emp_pan,c_emp_aadhar,c_esi_number,c_pf_applicability,c_esi_applicability,c_per_day_sal,c_ifsc,c_total_deductions,c_net_salary,medical_insurance_parents,is_smi,is_pmi,c_contract_id,ctc,c_division,c_pf_wage,esi_wage,no_of_days_month,))
	    print "payslip component created for:",i
            i = i+1
        return True

    @api.multi
    def payroll_approve(self):
        print "self.status",self.status
        if self.status == 'Rejected':
            if not self.c_final_remarks:
                raise ValidationError("Please update the Final Remarks for Approving a Rejected Entry")
            #trigger email to finance
        self.status = 'Approved By Payroll'
        self.c_approved_payroll = True
        return True

    @api.multi
    def payroll_hold(self):
        if self.c_payroll_remarks:
            #Trigger email to finance
            self.status = 'On Hold'
            return True
        else:
            raise ValidationError("Please update the Payroll Remarks for keeping on hold")

    @api.multi
    def hold_to_reset(self):
        self.status = 'Draft'
        return True

    @api.multi
    def finance_approve(self):
        self.status = 'Approved'
        return True

class nf_fnf_settlement(models.Model):
    _name = 'nf.fnf.settlement'
    _description = 'Full and Final settlement'

    name = fields.Char('Name')
    employee_id = fields.Many2one('hr.employee','Employee')
    emp_id = fields.Char('Employee Id')
    doj = fields.Date('Date of Joining')
    department_id = fields.Many2one('hr.department','Department/Division')
    designation = fields.Char('Internal Designation')
    branch_id = fields.Many2one('hr.branch','Location')
    payable_month = fields.Date('Payable Month')
    resignation_date = fields.Date('Date of Resignation')
    relieving_date = fields.Date('Relieving Date')
    last_working_day = fields.Date('Last working Day')
    notice_period = fields.Integer('Notice Period (In Days)')
    notice_period_served = fields.Integer('Notice Period Served (No.of Days)')
    shortfall = fields.Integer('Shortfall')
    ctc_per_month = fields.Float('CTC Per Month')
    total_working_days = fields.Integer('No.of Working Days')

    actual_basic = fields.Float('Actual Basic')
    actual_hra = fields.Float('Actual HRA')
    actual_med_conv = fields.Float('Actual Medical and Conveyance')
    actual_lta_allowance = fields.Float('Actual LTA Allowance')
    actual_spl_allowance = fields.Float('Actual Special Allownace')
    actual_total_gross = fields.Float('Actual Total Gross')
    actual_epf = fields.Float('Actual Employee Provident Fund')
    actual_erpf = fields.Float('Actual Employer Provident Fund')
    actual_esi = fields.Float('Actual Employee ESIC')
    actual_ersi = fields.Float('Actual Employer ESIC')
    actual_pt = fields.Float('Actual Professional Tax')
    actual_tds = fields.Float('Actual TDS')
    actual_advance = fields.Float('Actual Salary Advance')
    actual_others = fields.Float('Actual Others')
    earned_basic = fields.Float('Earned Basic')
    earned_hra = fields.Float('Earned HRA')
    earned_med_conv = fields.Float('Earned Medical and Conveyance')
    earned_lta_allowance = fields.Float('Earned LTA Allowance')
    earned_spl_allowance = fields.Float('Earned Special Allownace')
    earned_total_gross = fields.Float('Earned Total Gross')
    earned_epf = fields.Float('Earned Employee Provident Fund')
    earned_erpf = fields.Float('Earned Employer Provident Fund')
    earned_esi = fields.Float('Earned Employee ESIC')
    earned_ersi = fields.Float('Earned Employer ESIC')
    earned_pt = fields.Float('Earned Professional Tax')
    earned_tds = fields.Float('Earned TDS')
    earned_advance = fields.Float('Earned Salary Advance')
    earned_others = fields.Float('Earned Others')
    total_deductions = fields.Float('Total Deductions')
    total_additions = fields.Float('Total Additions')





