import datetime
from datetime import date
import dateutil.parser
from dateutil.parser import parse
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from dateutil.relativedelta import relativedelta
import calendar


from openerp import tools
from odoo import api, fields, models, _
from openerp.osv import osv
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
from odoo import exceptions
from odoo.exceptions import UserError, AccessError, ValidationError
from collections import defaultdict

HOURS_PER_DAY = 8

class Holidays(models.Model):
    _inherit = "hr.holidays"

    temp_no_leaves = fields.Float('Temp Number Of leaves')

    @api.onchange('date_from','date_to','holiday_status_id','employee_id')
    def reseting_rest_days(self):

        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise exceptions.ValidationError(_('The start date must be anterior to the end date.'))

        employee_id = self.env['hr.employee'].search([('id','=',self.employee_id.id)])
        print ">>>>>employee_id>>",employee_id
        list = []
        if employee_id:
            for division in self.env['hr.employee'].browse(employee_id.id):
                obj = division.sub_dep.c_rest_day_type
                if self.employee_id and self.holiday_status_id and division.sub_dep:
                    if obj:
                        if obj.c_fri == True:
                            list.append(4)
                        if obj.c_sat == True:
                            list.append(5)
                        if obj.c_sun == True:
                            list.append(6)


                        if self.holiday_status_id.c_in_rest_days == True and self.holiday_status_id.c_in_pub_holidays == True:
                            print "==========No public holidays and rest days applicable==============="
                            self.number_of_days_temp = self.get_no_of_days()
                            self.temp_no_leaves = self.number_of_days_temp


                        else:
                            if len(list) == 2 and obj.c_sat == True and obj.c_sun == True:
                                print "-sat and sunday--"
                                self.get_holi_sat_sun()
                            elif len(list) == 2 and obj.c_sat == True and obj.c_fri == True:
                                print ">>friday and saturday >>"
                                self.get_holi_on_sat_fri()
                            elif len(list) == 2 and obj.c_fri == True and obj.c_sun == True:
                                print ">>friday and sunday >>"
                                self.get_holiday_on_fri_sun()
                            elif len(list) ==1 and obj.c_sun == True:
                                print "--sunday only----"
                                self.get_holi_sun()
                            elif len(list) == 1 and obj.c_fri == True:
                                print ">> friday only >>"
                                self.get_holi_on_friday()
                            elif len(list) == 1 and obj.c_sat == True:
                                print ">> saturday only >>"
                                self.get_holi_on_saturday()
                            else:
                                if obj.c_fri == False and obj.c_sat == False and obj.c_sun == False:
                                    print "==========All days are working days==============="
                                    self.number_of_days_temp = self.checking_public_holidays()
                                    self.temp_no_leaves = self.number_of_days_temp
                    else:
                        raise exceptions.ValidationError(_('Rest day Type is not mentioned in Department'))

                else:
                    self.number_of_days_temp = self.get_no_of_days()
                    self.temp_no_leaves = self.number_of_days_temp
                    if not division.sub_dep:
                        raise exceptions.ValidationError(_('Employee has not mention Department, Please Mentioned Department'))


    def get_holi_sat_sun(self):
        dates = []
        dates = self.geting_public_holidays()
        rest_days = 0
        public_days = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')


            for i in xrange(int((to_date - from_date).days)+1):
                nextDate = from_date + timedelta(i)
                next = str(nextDate)
                split_date = next.split()[0]
                if split_date in dates and nextDate.weekday() in (0,1,2,3,4):
                    public_days = public_days + 1
                # sales person for sunday holiday
                if nextDate.weekday() in (0,1,2,3,4):
                    rest_days += 1
        self.in_rest_public_days(rest_days,public_days)


    def get_holi_on_sat_fri(self):
        dates = []
        dates = self.geting_public_holidays()
        rest_days = 0
        public_days = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')


            for i in xrange(int((to_date - from_date).days) + 1):
                nextDate = from_date + timedelta(i)
                next = str(nextDate)
                split_date = next.split()[0]
                if split_date in dates and nextDate.weekday() in (0, 1, 2, 3, 6):
                    public_days = public_days + 1
                # developer person for saturday and sunday holiday
                if nextDate.weekday() in (0, 1, 2, 3, 6):
                    rest_days += 1
        self.in_rest_public_days(rest_days,public_days)


    def get_holiday_on_fri_sun(self):
        dates = []
        dates = self.geting_public_holidays()
        rest_days = 0
        public_days = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')


            for i in xrange(int((to_date - from_date).days) + 1):
                nextDate = from_date + timedelta(i)
                next = str(nextDate)
                split_date = next.split()[0]
                if split_date in dates and nextDate.weekday() in (0, 1, 2, 3, 5):
                    public_days = public_days + 1
                # developer person for saturday and sunday holiday
                if nextDate.weekday() in (0, 1, 2, 3, 5):
                    rest_days += 1
        self.in_rest_public_days(rest_days,public_days)


    def get_holi_sun(self):
        dates = []
        dates = self.geting_public_holidays()
        rest_days = 0
        public_days = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')


            for i in xrange(int((to_date - from_date).days) + 1):
                nextDate = from_date + timedelta(i)
                next = str(nextDate)
                split_date = next.split()[0]
                if split_date in dates and nextDate.weekday() in (0, 1, 2, 3, 4,5):
                    public_days = public_days + 1
                # developer person for saturday and sunday holiday
                if nextDate.weekday() in (0, 1, 2, 3, 4,5):
                    rest_days += 1
        self.in_rest_public_days(rest_days,public_days)


    def get_holi_on_friday(self):
        dates = []
        dates = self.geting_public_holidays()
        rest_days = 0
        public_days = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')


            for i in xrange(int((to_date - from_date).days) + 1):
                nextDate = from_date + timedelta(i)
                next = str(nextDate)
                split_date = next.split()[0]
                if split_date in dates and nextDate.weekday() in (0, 1, 2, 3, 5,6):
                    public_days = public_days + 1
                # developer person for saturday and sunday holiday
                if nextDate.weekday() in (0, 1, 2, 3, 5,6):
                    rest_days += 1
        self.in_rest_public_days(rest_days,public_days)


    def get_holi_on_saturday(self):
        dates = []
        dates = self.geting_public_holidays()
        rest_days = 0
        public_days = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')


            for i in xrange(int((to_date - from_date).days) + 1):
                nextDate = from_date + timedelta(i)
                next = str(nextDate)
                split_date = next.split()[0]
                if split_date in dates and nextDate.weekday() in (0, 1, 2, 3, 4,6):
                    public_days = public_days + 1
                # developer person for saturday and sunday holiday
                if nextDate.weekday() in (0, 1, 2, 3, 4,6):
                    rest_days += 1
        self.in_rest_public_days(rest_days,public_days)

    def geting_public_holidays(self):
        cr = self.env.cr
        today_date = str(datetime.now().date())
        year = today_date.split('-')[0]
        year = '2018'
        pub_holi = self.env['hr.holidays.public'].search([('year', '=', year)])
        print "#################", pub_holi
        dates = []
        state = self.employee_id.state_id
        if not state:
            raise exceptions.ValidationError(_('State of the employee is not mentioned'))
        if pub_holi and state:
            cr.execute(
                "SELECT hpl.date FROM hr_holidays_public_line hpl LEFT JOIN ouc_phl_state_rel psr ON psr.phl_id = hpl.id WHERE (psr.state_id = %s OR psr.state_id is NULL) and hpl.year_id = %s",
                (state.id, pub_holi.id))
            p_holidays = cr.fetchall()
            dates = [val[0] for val in p_holidays]
        print "####################", dates
        return dates

    def get_no_of_days(self):
        diff = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')
            diff = int((to_date - from_date).days) + 1
        return diff


    def in_rest_public_days(self,rest_days,public_days):
        print ">>rest days>>", rest_days
        print ">>public days>>", public_days

        if self.holiday_status_id.c_in_pub_holidays == True:
            total_leave_days = rest_days
        elif self.holiday_status_id.c_in_rest_days == True:
            total_leave_days = self.checking_public_holidays()
        else:
            total_leave_days = rest_days - public_days
        number_of_days_temp = total_leave_days
        if self.day_type in ['First Half','Second Half']:
            number_of_days_temp = number_of_days_temp - 0.5
        self.number_of_days_temp = number_of_days_temp
        self.temp_no_leaves = number_of_days_temp

    def checking_public_holidays(self):
        original_days = self.get_no_of_days()
        pub_days = self.geting_public_holidays()
        public_days = 0
        if self.date_from and self.date_to:
            from_date = datetime.strptime(self.date_from, '%Y-%m-%d %H:%M:%S')
            to_date = datetime.strptime(self.date_to, '%Y-%m-%d %H:%M:%S')
            for i in xrange(int((to_date - from_date).days) + 1):
                nextDate = from_date + timedelta(i)
                next = str(nextDate)
                split_date = next.split()[0]
                if split_date in pub_days and nextDate.weekday() in (0, 1, 2, 3, 4, 5, 6):
                    public_days = public_days + 1
        total_leave_days = original_days - public_days
        return total_leave_days

    @api.model
    def create(self,values):
        res = super(Holidays,self).create(values)
        res.write({'number_of_days_temp': res.temp_no_leaves})
        return res


