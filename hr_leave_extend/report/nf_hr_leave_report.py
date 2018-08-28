
from odoo import fields, models, tools

class nf_hr_leave_report(models.Model):

    _name = "nf.hr.leave.report"
    _auto = False
    _description = "NF HR Leave Report"

    employee_id = fields.Many2one('hr.employee', "Employee")
    holiday_status_id = fields.Many2one("hr.holidays.status", "Leave Type")
    no_of_leaves = fields.Float('No of leaves', readonly=True)
    type = fields.Selection([('remove', 'Leave Taken'),('add', 'Leave Added')], string='Request Type')

    def init(self):
      cr=self.env.cr
      tools.drop_view_if_exists(cr, 'nf_hr_leave_report')
      cr.execute("""
          CREATE or REPLACE view nf_hr_leave_report as
            SELECT
              id as id,
              employee_id,
              holiday_status_id,
              type,
              sum(number_of_days) as no_of_leaves

            FROM hr_holidays
            WHERE state != 'refuse'
            GROUP BY id
                  
      """)
