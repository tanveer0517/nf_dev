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

from openerp.osv import osv
from openerp.report import report_sxw
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from datetime import datetime
from datetime import date, timedelta
from dateutil import rrule
from datetime import datetime
from dateutil.rrule import MONTHLY
from openerp.tools import amount_to_text
from openerp.tools import amount_to_text_en
import calendar
import psycopg2
from dateutil import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from num2words import num2words
from titlecase import titlecase


class payslip_custom_report(models.Model):
    _inherit = 'hr.payslip'
    
    def get_time(self):
        date=time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        date = datetime.strptime(date,"%Y-%m-%d %H:%M:%S")
        date = date + timedelta(hours=4)
        date = date.strftime("%d-%m-%Y %H:%M:%S")
        return date
    
    def get_user(self):
        temp = self.env['res.users'].browse(self.env.uid)
        return temp.name
    
    def get_tax_details(self):
        self.env.cr.execute("select etl.name,etl.total_amount,etl.exempted_amount,etl.taxable_amount from employee_tds_line etl left join employee_tds et on etl.employee_tds_id = et.id where et.employee_id = %s and et.date_from = %s  and et.date_to = %s",(self.employee_id.id,self.date_from,self.date_to,))
        temp = self.env.cr.fetchall()
        return temp
    
    def get_net_tax(self):
        self.env.cr.execute("select coalesce(tds_net_salary_taxable,0) from employee_tds where employee_id = %s and date_from = %s  and date_to = %s limit 1",(self.employee_id.id,self.date_from,self.date_to,))
        temp = self.env.cr.fetchone()
        if temp:
           return temp[0]
    
    def get_gross_tax(self):
        self.env.cr.execute("select coalesce(tds_gross_amount,0) from employee_tds where employee_id = %s and date_from = %s  and date_to = %s limit 1",(self.employee_id.id,self.date_from,self.date_to,))
        temp = self.env.cr.fetchone()
        if temp:
           return temp[0]
    
    def get_saving_details(self):
        self.env.cr.execute("select hsr.name,sl.amount from saving_line sl left join employee_saving es on sl.saving_id = es.id left join hr_salary_rule hsr on sl.salary_rule_id = hsr.id where es.employee_id = %s",(self.employee_id.id,))
        temp = self.env.cr.fetchall()
        return temp
    
    def get_medical_details(self):
        self.env.cr.execute("select mbl.reference,mbl.amount from medical_bill_line mbl left join employee_saving es on mbl.bill_id = es.id where es.employee_id = %s",(self.employee_id.id,))
        temp = self.env.cr.fetchall()
        return temp
    
    def get_hra_details(self):
        self.env.cr.execute("select hrl.reference,hrl.amount from hra_receipt_line hrl left join employee_saving es on hrl.hra_receipt_id = es.id where es.employee_id = %s",(self.employee_id.id,))
        temp = self.env.cr.fetchall()
        return temp
    
    def get_other_details(self):
        self.env.cr.execute("select osi.reference,osi.amount from other_source_income osi left join employee_saving es on osi.income_id = es.id where es.employee_id = %s",(self.employee_id.id,))
        temp = self.env.cr.fetchall()
        return temp
    
    def total_earnings(self):
        self.env.cr.execute("select coalesce(sum(hpl.total),0) from hr_payslip_line as hpl left join hr_payslip as hp on hpl.slip_id = hp.id left join hr_salary_rule_category as category on hpl.category_id = category.id where hp.id = %s and category.code in ('ALW','BASIC')",(self.id,))
        temp = self.env.cr.fetchone()
        if temp:
           return temp[0]
    
    def total_deductions(self):
        self.env.cr.execute("select coalesce(sum(hpl.amount),0) from hr_payslip_line as hpl left join hr_payslip as hp on hpl.slip_id = hp.id left join hr_salary_rule_category as category on hpl.category_id = category.id where hp.id = %s and category.code in ('DED')",(self.id,))
        temp = self.env.cr.fetchone()
        if temp:
           return temp[0]

    def total_net(self):
        self.env.cr.execute("select coalesce(sum(hpl.total),0) from hr_payslip_line as hpl left join hr_payslip as hp on hpl.slip_id = hp.id left join hr_salary_rule_category as category on hpl.category_id = category.id where hp.id = %s and category.code in ('NET')",(self.id,))
        net_value = self.env.cr.fetchone()
        return net_value[0]

    def net_words(self):
        net = self.total_net()
        no_of_lakhs = net/100000
        if int(no_of_lakhs) != 0:
            words_lakhs = num2words(int(no_of_lakhs)) + ' lakh '
        else:
            words_lakhs = ''

        no_of_thousands = (net - (int(no_of_lakhs)*100000))/1000
        if int(no_of_thousands) != 0:
            words_thousands = num2words(int(no_of_thousands)) + ' thousand '
        else:
            words_thousands = ''

        no_of_hundreds = (net - (int(no_of_lakhs)*100000) - (int(no_of_thousands)*1000))/100
        if int(no_of_hundreds) !=0:
            words_hundreds = num2words(int(no_of_hundreds)) + ' hundred '
        else:
            words_hundreds = ''

        no_of_units = net - (int(no_of_lakhs)*100000) - (int(no_of_thousands)*1000) - (int(no_of_hundreds)*100)
        if int(no_of_units) != 0:
            words_units = ' and ' + num2words(int(no_of_units))
        else:
            words_units = ''

        decimals = net - (int(no_of_lakhs)*100000) - (int(no_of_thousands)*1000) - (int(no_of_hundreds)*100) - (int(no_of_units))
        if decimals !=0:
            words_decimals = num2words(int(decimals*100)) + ' paise'
        else:
            words_decimals = ''

        net_words = titlecase(words_lakhs + words_thousands + words_hundreds + words_units + ' rupees ' + words_decimals)
        print "net_words",net_words
        return net_words

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
