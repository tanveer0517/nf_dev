from datetime import date
import dateutil.parser
from dateutil.parser import parse
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta


from openerp import tools
from odoo import api, fields, models, _
from openerp.osv import osv
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError, AccessError, ValidationError


class hr_rest_days(models.Model):
    _name = 'hr.rest.days'
    _rec_name = 'c_rest_day_type'

    c_rest_day_type = fields.Char(string='Rest day Type')

    c_fri = fields.Boolean(string='Friday')
    c_sat = fields.Boolean(string='Saturday')
    c_sun = fields.Boolean(string='Sunday')

    @api.onchange('c_fri','c_sat','c_sun')
    def auto_filling_rest_days(self):
        list = []
        if self.c_fri == True:
            list.append('Friday')
        if self.c_sat == True:
            list.append('Saturday')
        if self.c_sun == True:
            list.append('Sunday')
        print ">>>>>>>>>>>list>>>>>>>>>",list
        print " ".join(list)
        self.c_rest_day_type = list
        print ">>>>>>>>>>self.c_rest_day_type >>>>>>>>>>",self.c_rest_day_type

class hr_department(models.Model):
    _inherit = 'hr.department'

    c_rest_day_type = fields.Many2one('hr.rest.days',string='Rest day Type')
    name = fields.Char('Name', required=True)

class hr_holidays_status(models.Model):
    _inherit = 'hr.holidays.status'

    c_in_rest_days = fields.Boolean(string='Include Rest Days')
    c_in_pub_holidays = fields.Boolean(string='Include Public Holidays')


