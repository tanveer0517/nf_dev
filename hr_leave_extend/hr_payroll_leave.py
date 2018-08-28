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
from datetime import date
import dateutil.parser
from dateutil.parser import parse
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import math

from openerp import tools
from odoo import api, fields, models, _
from openerp.osv import osv
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError, AccessError, ValidationError

HOURS_PER_DAY = 8

class hr_payleave(osv.osv):
    _name = 'hr.payleave'
    
    name = fields.Char(string = 'Name')
    employee_id = fields.Many2one('hr.employee',string = 'Employee')
    employee_no = fields.Char(string = 'Employee Number')
    leave_type = fields.Many2one('hr.holidays.status',string = 'Leave Type')
    from_date = fields.Date(string = 'From Date')
    to_date = fields.Date(string = 'To Date')
    reason = fields.Char(string = 'Reason')
    approving_authority = fields.Char(string = 'Approving Authority')
    remarks = fields.Char(string = 'Remarks')
    contact_address = fields.Char(string = 'Contact Address')
    no_of_days = fields.Float(string = 'Number Of Days')
    txn_type = fields.Selection([('C','C'),('D','D')],string = 'Type')
    previous_balance = fields.Float(string = 'Previous Balance')
    new_balance = fields.Float(string = 'New Balance')
    record_type = fields.Selection([('L','L'),('E','E'),('C','C')],string = 'Record Type')
    payroll_month = fields.Date(string = 'Payroll Month')
                
    
class hr_leave_credit(models.Model):
    _name = 'hr.leave.credit'
    
    name = fields.Char('Name')
    filter = fields.Selection([('R','Region Wise'),('E','Employee Wise')],string = 'Filter' )
    region_id = fields.Many2one('employee.region',string = 'Region')
    employee_id = fields.Many2one('hr.employee',string = 'Employee')
    leave_type = fields.Selection([('EL','EL'),('HPL','HPL'),('CL','CL'),('RH','RH')],string = 'Leave Type')
    start_date = fields.Date(string = 'Start Date')
    end_date = fields.Date(string = 'End Date',readonly=True)
    data_generated = fields.Boolean(string = 'Data Generated')
    leave_credited = fields.Boolean(string = 'Leave Credited')
    credit_line = fields.One2many('hr.leave.credit.line','credit_id',string = 'Credit Line')
    user = fields.Many2one('res.users',string = 'USER',default=lambda self: self.env.user)
    
    @api.multi
    def unlink(self):
        for credit in self:
            if credit.leave_credited==True:
                raise osv.except_osv(_('Warning'), _('You can not delete record in leave credited state.'))
        return super(hr_leave_credit, self).unlink()
        
    @api.multi
    def generate_data(self):
        for record in self:
             record.data_generated = True
        return True     
    
    @api.multi
    def credit_leave(self):
        for record in self:
             record.leave_credited = True
        return True
            
        
    
class hr_leave_credit_line(osv.osv):
    _name = 'hr.leave.credit.line'
    
    name = fields.Char('Name')
    employee_id = fields.Many2one('hr.employee',string = 'Employee',readonly=True)
    leave_type = fields.Selection([('EL','EL'),('HPL','HPL'),('CL','CL'),('RH','RH')],string = 'Leave Type',readonly=True)
    prev_bal = fields.Float(string = 'Previous Balance',readonly=True)
    credit_days = fields.Float(string = 'Credit Days')
    new_bal = fields.Float(string = 'New Balance')
    credit_id = fields.Many2one('hr.leave.credit', string = 'Credit Id',readonly=True)
    
class hr_leave_balance_entry(models.Model):
    _name = 'hr.leave.balance.entry'
    
    name = fields.Char(string = 'Name')
    employee_id = fields.Many2one('hr.employee',string = 'Employee')
    leave_type = fields.Selection([('EL','EL'),('CL','CL'),('RH','RH'),('HPL','HPL')],string = 'Leave Type')
    remarks = fields.Char(string = 'Remarks')
    current_balance = fields.Float(string = 'Current Balance')
    new_balance = fields.Float(string = 'New Balance')
    done = fields.Boolean(string = 'Done')

    
    @api.multi
    def unlink(self):
        for encash in self:
            if encash.done==True:
                raise osv.except_osv(_('Warning'), _('You can not delete record in done state.'))
        return super(hr_leave_balance_entry, self).unlink()
        
    @api.multi
    def get_balance(self):
        self.current_balance = 1
        return True
    
    @api.multi
    def update_balance(self):
        self.done = True
        return True
        
        

class hr_payleave_encash(osv.osv):
    _name = 'hr.payleave.encash'
    
    name = fields.Char('Name')
    employee_id = fields.Many2one('hr.employee',string = 'Employee')
    encashment_days = fields.Float(string = 'Encashment Days')
    remarks = fields.Text(string = 'Remarks',required=True)
    tax_exempted = fields.Boolean(string = 'Tax Exempted?')
    done = fields.Boolean(string = 'Done')
    
    @api.multi
    def unlink(self):
        for encash in self:
            if encash.done==True:
                raise osv.except_osv(_('Warning'), _('You can not delete record in done state.'))
        return super(hr_payleave_encash).unlink()
    
    @api.multi
    def encash_leave(self):
        for record in self:
            record.done = True
        return True
    
class Holidays(models.Model):
    _inherit = "hr.holidays"

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
            help="The status is set to 'To Submit', when a holiday request is created." +
            "\nThe status is 'To Approve', when holiday request is confirmed by user." +
            "\nThe status is 'Refused', when holiday request is refused by manager." +
            "\nThe status is 'Approved', when holiday request is approved by manager.")

    day_type = fields.Selection([('Full Day','Full Day'),('First Half','First Half'),('Second Half','Second Half')],'Day Type',default='Full Day')

    @api.model
    def leave_balance_carry_forward(self):
        cr=self.env.cr
        holi_obj=self.env['hr.holidays']
        emp_obj=self.env['hr.employee']
        emp_ids=emp_obj.sudo().search([('active','=',True)])
        for emp_rec in emp_ids:
            cr.execute("SELECT sum(holi.number_of_days_temp) as days from hr_holidays holi INNER JOIN hr_holidays_status st on (st.id=holi.holiday_status_id) LEFT JOIN hr_employee emp ON holi.employee_id = emp.id  where holi.employee_id=%s and holi.state in ('draft','confirm','validate') and holi.type='add' and st.name='Earned Leaves' and emp.join_date < '2018-01-01'",(emp_rec.id,))
            earned_allocated=cr.dictfetchall()[0]['days'] or 0
            cr.execute("SELECT sum(holi.number_of_days_temp) as days from hr_holidays holi INNER JOIN hr_holidays_status st on (st.id=holi.holiday_status_id) where holi.employee_id=%s and holi.state in ('draft','confirm','validate') and holi.type='remove' and st.name='Earned Leaves' and (holi.date_to IS NULL OR holi.date_to::date < '2018-01-01')",(emp_rec.id,))
            earned_taken=cr.dictfetchall()[0]['days'] or 0
            tot_earn_balance=earned_allocated-earned_taken
            earn_balance=0
            if tot_earn_balance>6:
                earn_balance=6
            elif tot_earn_balance>0 and tot_earn_balance<=6:
                earn_balance=tot_earn_balance
            total_earn_allocate=earn_balance+earned_taken
            cr.execute("SELECT sum(holi.number_of_days_temp) as days from hr_holidays holi INNER JOIN hr_holidays_status st on (st.id=holi.holiday_status_id) LEFT JOIN hr_employee emp ON holi.employee_id = emp.id where holi.employee_id=%s and holi.state in ('draft','confirm','validate') and holi.type='add' and st.name='Casual / Sick Leave' and emp.join_date < '2018-01-01'",(emp_rec.id,))
            casual_allocated=cr.dictfetchall()[0]['days'] or 0
            cr.execute("SELECT sum(holi.number_of_days_temp) as days from hr_holidays holi INNER JOIN hr_holidays_status st on (st.id=holi.holiday_status_id) where holi.employee_id=%s and holi.state in ('draft','confirm','validate') and holi.type='remove' and st.name='Casual / Sick Leave' and (holi.date_to IS NULL OR holi.date_to::date < '2018-01-01')",(emp_rec.id,))
            casual_taken=cr.dictfetchall()[0]['days'] or 0
            tot_casual_balance=casual_allocated-casual_taken
            casual_balance=0
            total_casual_allocate=casual_taken
            if earned_allocated:
                cr.execute("delete from hr_holidays where employee_id=%s and type='add' and holiday_status_id=%s",(emp_rec.id,1,))
                notes = "Summary of Earned Leave in 2017 \nTotal Earned Leave = "+str(earned_allocated)+"\nTotal Earned Leave Taken = "+str(earned_taken)+"\nTotal Earned Balance = "+str(tot_earn_balance)+"\nTotal Earned Carry Forward = "+str(earn_balance)
                holi_rec=holi_obj.sudo().create({'employee_id':emp_rec.id,'type':'add','number_of_days_temp':total_earn_allocate,'holiday_status_id':1,'name':'Total Leave Allocated till Dec 2017','holiday_type':'employee','state':'validate','notes':notes})
                holi_rec.sudo().write({'number_of_days_temp':total_earn_allocate})
            if casual_allocated:
                cr.execute("delete from hr_holidays where employee_id=%s and type='add' and holiday_status_id=%s",(emp_rec.id,6,))
                notes = "Summary of Casual/Sick Leave in 2017 \nTotal Casual Leave = "+str(casual_allocated)+"\nTotal Casual Leave Taken = "+str(casual_taken)+"\nTotal Casual Balance = "+str(tot_casual_balance)+"\nTotal Casual Carry Forward = "+str(casual_balance)
                holi_rec=holi_obj.sudo().create({'employee_id':emp_rec.id,'type':'add','number_of_days_temp':total_casual_allocate,'holiday_status_id':6,'name':'Total Leave Allocated till Dec 2017','holiday_type':'employee','state':'validate','notes':notes})
                holi_rec.sudo().write({'number_of_days_temp':total_casual_allocate})

        return True
    
    def send_action_confirm_email(self,type):
        template = False
        if type == 'confirm':
           template=self.env['mail.template'].search([('name', '=', 'Leave Request Email')], limit = 1)
        
        elif type == 'approve':
           if self.holiday_status_id and self.holiday_status_id.double_validation: 
              template=self.env['mail.template'].search([('name', '=', 'Leave Validation Request Email')], limit = 1)
            
           else:
              template=self.env['mail.template'].search([('name', '=', 'Leave Approve Email')], limit = 1)
                  
        elif type == 'validate':
           template=self.env['mail.template'].search([('name', '=', 'Leave Validation Email')], limit = 1)
        
        elif type == 'refuse':
           template=self.env['mail.template'].search([('name', '=', 'Leave Refuse Email')], limit = 1)
        
        if template:
            template.send_mail(self.id)
            return True

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """ If there are no date set for date_to, automatically set one 8 hours later than
            the date_from. Also update the number_of_days.
        """
        date_from = self.date_from
        date_to = self.date_to
        #No date_to set so far: automatically compute one 8 hours later
        if date_from:
            if self.day_type == 'First Half':
                date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 04:30:01")
            elif self.day_type == 'Second Half':
                date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 09:00:01")
            elif self.day_type == 'Full Day':
                date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 04:30:01")
            self.date_from = date_from

        if date_from and not date_to:
            if self.day_type == 'First Half':
                date_to = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 09:00:00")
            elif self.day_type == 'Second Half':
                date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 09:00:01")
                date_to = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:00")
            elif self.day_type == 'Full Day':
                date_to = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:00")
            self.date_from = date_from
            self.date_to = date_to
                #self.date_to = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:01")
            # date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=HOURS_PER_DAY)
            # self.date_to = str(date_to_with_delta)

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.number_of_days_temp = self._get_number_of_days(date_from, date_to, self.employee_id.id)
        else:
            self.number_of_days_temp = 0

    @api.onchange('date_to')
    def _onchange_date_to(self):
        """ Update the number_of_days. """
        date_from = self.date_from
        date_to = self.date_to
        no_of_days = 0.0
        if date_to:
            if self.day_type == 'First Half':
                date_to = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 09:00:00")
            elif self.day_type == 'Second Half':
                date_to = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:00")
            else:
                date_to = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:00")
            #date_to = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:01")
            self.date_to = date_to

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            self.number_of_days_temp = self._get_number_of_days(date_from, date_to, self.employee_id.id)
        else:
            self.number_of_days_temp = 0

    @api.onchange('day_type')
    def onchange_daytype(self):
        if self.day_type:
            if self.date_from and self.date_to:
                if self.day_type == 'First Half':
                    self.date_from = datetime.strptime(self.date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 04:30:01")
                    self.date_to = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 09:00:00")
                elif self.day_type == 'Second Half':
                    self.date_from = datetime.strptime(self.date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 09:00:01")
                    self.date_to = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:00")
                else:
                    self.date_from = datetime.strptime(self.date_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 04:30:01")
                    self.date_to = datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d 13:30:00")

    @api.multi
    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
        self.send_action_confirm_email('confirm')
        return self.write({'state': 'confirm'})

    def _check_state_access_right(self, vals):
        # if vals.get('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] and not self.env['res.users'].has_group('hr_holidays.group_hr_holidays_user'):
        #     return False
        return True

    @api.multi
    def write(self, values):
        employee_id = values.get('employee_id', False)
        # if not self._check_state_access_right(values):
        #     raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        values.update({'number_of_days_temp':values.get('temp_no_leaves') or self.temp_no_leaves})
        result = super(Holidays, self).write(values)
        self.add_follower(employee_id)
        return True

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id', False)
        if not self._check_state_access_right(values):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        holiday = super(Holidays, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)
        holiday.add_follower(employee_id)
        holiday.action_confirm()
        return holiday

    @api.multi
    def action_approve(self):
        # if double_validation: this method is the first approval approval
        # if not double_validation: this method calls action_validate() below
        # if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
        #     raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

        manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state != 'confirm':
                raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

            if holiday.double_validation:
                holiday.send_action_confirm_email('approve')
                return holiday.write({'state': 'validate1', 'manager_id': manager.id if manager else False})
            else:
                holiday.action_validate()

    @api.multi
    def action_validate(self):
        # if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
        #     raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

        manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            holiday.send_action_confirm_email('validate')
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Leave request must be confirmed in order to approve it.'))
            # if holiday.state == 'validate1' and not holiday.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            #     raise UserError(_('Only an HR Manager can apply the second approval on leave requests.'))
            holiday.write({'state': 'validate'})
            if holiday.double_validation:
                holiday.write({'manager_id2': manager.id})
            else:
                holiday.write({'manager_id': manager.id})
            if holiday.holiday_type == 'employee' and holiday.type == 'remove':
                approval_list = []
                manager_id = holiday.employee_id.parent_id and holiday.employee_id.parent_id.user_id and holiday.employee_id.parent_id.user_id.id or False
                if manager_id:
                    approval_list.append(manager_id)
                rept_head_id = holiday.employee_id.coach_id and holiday.employee_id.coach_id.user_id and holiday.employee_id.coach_id.user_id.id or False
                if rept_head_id:
                    approval_list.append(rept_head_id)
                if self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.uid in list(set(approval_list)):
                    meeting_values = {
                        'name': holiday.display_name,
                        'categ_ids': [(6, 0, [holiday.holiday_status_id.categ_id.id])] if holiday.holiday_status_id.categ_id else [],
                        'duration': holiday.number_of_days_temp * HOURS_PER_DAY,
                        'description': holiday.notes,
                        'user_id': holiday.user_id.id,
                        'start': holiday.date_from,
                        'stop': holiday.date_to,
                        'allday': False,
                        'state': 'open',            # to block that meeting date in the calendar
                        'privacy': 'confidential'
                    }
                    #Add the partner_id (if exist) as an attendee
                    if holiday.user_id and holiday.user_id.partner_id:
                        meeting_values['partner_ids'] = [(4, holiday.user_id.partner_id.id)]

                    meeting = self.env['calendar.event'].with_context(no_mail_to_attendees=True).create(meeting_values)
                    holiday.sudo()._create_resource_leave()
                    holiday.write({'meeting_id': meeting.id})
                else:
                    raise UserError(_('Warning! Leave can be approved only by the HR, Manager or Reporting manager of the employee'))
            elif holiday.holiday_type == 'category':
                leaves = self.env['hr.holidays']
                for employee in holiday.category_id.employee_ids:
                    values = {
                        'name': holiday.name,
                        'type': holiday.type,
                        'holiday_type': 'employee',
                        'holiday_status_id': holiday.holiday_status_id.id,
                        'date_from': holiday.date_from,
                        'date_to': holiday.date_to,
                        'notes': holiday.notes,
                        'number_of_days_temp': holiday.number_of_days_temp,
                        'parent_id': holiday.id,
                        'employee_id': employee.id
                    }
                    leaves += self.with_context(mail_notify_force_send=False).create(values)
                # TODO is it necessary to interleave the calls?
                leaves.action_approve()
                if leaves[0].double_validation:
                    leaves.action_validate()
        return True   
    
    @api.multi
    def action_refuse(self):
        manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            approval_list = []
            manager_id = holiday.employee_id.parent_id and holiday.employee_id.parent_id.user_id and holiday.employee_id.parent_id.user_id.id or False
            if manager_id:
                approval_list.append(manager_id)
            rept_head_id = holiday.employee_id.coach_id and holiday.employee_id.coach_id.user_id and holiday.employee_id.coach_id.user_id.id or False
            if rept_head_id:
                approval_list.append(rept_head_id)

            if self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.uid in list(set(approval_list)):

                holiday.send_action_confirm_email('refuse')
                if not holiday.report_note:
                   raise ValidationError("Please mention reason of decline in comment!")

                if len(holiday.report_note) < 100:
                   raise ValidationError("Please mentioned atleast 100 letters remark")

                if self.state not in ['confirm', 'validate', 'validate1']:
                    raise UserError(_('Leave request must be confirmed or validated in order to refuse it.'))

                if holiday.state == 'validate1':
                    holiday.write({'state': 'refuse', 'manager_id': manager.id})
                else:
                    holiday.write({'state': 'refuse', 'manager_id2': manager.id})
                # Delete the meeting
                if holiday.meeting_id:
                    holiday.meeting_id.unlink()
                # If a category that created several holidays, cancel all related
                holiday.linked_request_ids.action_refuse()
            else:
                raise UserError(_('Only Manager, Reporting Manager or HR can refuse leave requests.'))
        self._remove_resource_leave()
        return True
    
    @api.onchange('holiday_type')
    def onchange_domain_hr_holidays(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user' or 'hr_holidays.group_hr_holidays_manager'):
            holidays_status_ids = [val.id for val in self.env['hr.holidays.status'].search([('name','not in',('Loss Of Pay','Bereavement Leave','Maternity Leave','Paternity Leave'))])]
            print holidays_status_ids
            domain = {'holiday_status_id':[('id','in',holidays_status_ids)]}
            return {'domain':domain}

    @api.onchange('employee_id')
    def onchange_domain_employee(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user' or 'hr_holidays.group_hr_holidays_manager'):
            if self.employee_id and self.employee_id.c_empl_type != 'permanent':
                holidays_status_ids = [val.id for val in self.env['hr.holidays.status'].search([('name','not in',('Loss Of Pay','Bereavement Leave','Maternity Leave','Paternity Leave','Earned Leaves'))])]
                domain = {'holiday_status_id':[('id','in',holidays_status_ids)]}
                return {'domain':domain}