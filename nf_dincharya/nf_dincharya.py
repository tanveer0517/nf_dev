from odoo import models, fields, api, _
from openerp.osv import osv
from datetime import datetime
import time
from odoo.exceptions import UserError, ValidationError
from openerp import SUPERUSER_ID

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib2 import Request, urlopen
import json,urllib,urllib2
from dateutil.relativedelta import relativedelta

FOS_Desig = ('Associate - FOS','Consultant - FOS','Principal Consultant - FOS','Senior Consultant - FOS','Associate Product Specialist','Principal Product Specialist','Product Specialist','Senior Product Specialist','Associate - Customer First','Consultant - Customer First','Principal Consultant - Customer First','Senior Consultant - Customer First','Associate - Verticals','Consultant - Verticals','Principal Consultant - Verticals','Senior Consultant - Verticals')

Tele_Desig = ('Associate - Tele Sales','Consultant - Tele Sales','Principal Consultant - Tele Sales','Senior Consultant - Tele Sales')

class nf_biz(models.Model):
    _name = 'nf.biz'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'employee_id'
    _order = 'date desc'

    followup_meeting_num = 0
    meeting_date = '2017-08-22'

    def get_employee(self):
        emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return emp_id

    @api.one
    @api.depends('employee_id')
    def _get_emp_user(self, context=None):
        env = api.Environment(self.env.cr, SUPERUSER_ID, {})
        for record in self:
            dch = env['nf.biz'].browse(record.id)
            if dch.employee_id:
                record.user_id = dch.employee_id.user_id and dch.employee_id.user_id.id or False

    @api.multi
    def get_meeting(self,emp_usr_id, emp_desig):
        counter = 0
        date = fields.Date.context_today(self)
        date = datetime.strptime(date, "%Y-%m-%d")
        date = date - relativedelta(days=1)
        self.followup_meeting_num = 0
        self.meeting_date = date
        meeting_num = 0
        new_meeting_num = 0
        followup_meeting_num = 0
        cr = self.env.cr
        while True:
            if (counter > 2): return
            elif (meeting_num > 0): return

            if emp_desig in Tele_Desig:
                str_sql =  "WITH meeting AS (SELECT " \
                           "SUM(COALESCE(number_of_meeting,0)) AS num_of_meeting," \
                           "CASE " \
                           "WHEN meeting_type = 'new' " \
                           "THEN SUM(COALESCE(number_of_meeting,0)) " \
                           "ELSE 0 " \
                           "END AS num_of_new_meeting," \
                           "CASE " \
                           "WHEN meeting_type = 'Follow up' " \
                           "THEN SUM(COALESCE(number_of_meeting,0)) " \
                           "ELSE 0 " \
                           "END AS num_of_followup_meeting " \
                           "FROM " \
                           "crm_meeting_view " \
                           "WHERE sp_id = {} AND date_of_meeting::date = '{}' " \
                           "GROUP BY meeting_type) " \
                           "SELECT SUM(COALESCE(num_of_meeting,0))," \
                           "SUM(COALESCE(num_of_new_meeting,0))," \
                           "SUM(COALESCE(num_of_followup_meeting,0)) " \
                           "FROM meeting" \
                          .format(emp_usr_id,date)
            else:
                str_sql = "WITH meeting AS (SELECT " \
                          "SUM(1) AS num_of_meeting," \
                          "CASE " \
                          "WHEN c_meeting_type = 'new' " \
                          "THEN SUM(1) " \
                          "ELSE 0 " \
                          "END AS num_of_new_meeting," \
                          "CASE " \
                          "WHEN c_meeting_type = 'Follow up' " \
                          "THEN SUM(1) " \
                          "ELSE 0 " \
                          "END AS num_of_followup_meeting " \
                          "FROM " \
                          "crm_phonecall " \
                          "WHERE user_id = {} AND date::date = '{}' " \
                          "GROUP BY c_meeting_type) " \
                          "SELECT SUM(COALESCE(num_of_meeting,0))," \
                          "SUM(COALESCE(num_of_new_meeting,0))," \
                          "SUM(COALESCE(num_of_followup_meeting,0)) " \
                          "FROM meeting" \
                    .format(emp_usr_id, date)

            cr.execute(str_sql)
            temp = cr.fetchall()[0]
            if temp and temp[0] > 0:
                meeting_num = temp[0]
                new_meeting_num = temp[1]
                followup_meeting_num = temp[2]

            yield (new_meeting_num,followup_meeting_num,date)
            date = date - relativedelta(days=1)
            counter += 1

    def get_meeting_num(self, emp_usr_id, emp_desig):
        for meeting in self.get_meeting(emp_usr_id, emp_desig):
            pass
        self.followup_meeting_num = meeting[1]
        self.meeting_date = datetime.strftime(meeting[2],'%Y-%m-%d')
        return meeting[0]

    employee_id = fields.Many2one('hr.employee', 'Employee', track_visibility='always', default=get_employee)
    branch_id = fields.Many2one('hr.branch', relative='employee_id.branch_id', string='Branch')
    user_id = fields.Many2one(compute = '_get_emp_user', string='Employee User', default = lambda self : self.env.user,
                               store=True, track_visibility='onchange')
    date = fields.Date('Date',track_visibility='always', default=fields.Date.context_today)
    nf_biz_lines = fields.One2many('nf.biz.line', 'biz_id', 'Team',
                                          on_delete="cascade")
    state = fields.Selection([('Draft','Draft'),('Posted','Posted')],'Status',track_visibility='onchange', default='Draft')

    @api.onchange('employee_id')
    def onchange_emp(self):
        if self.employee_id:
            cr = self.env.cr
            empl_id = self.employee_id.id
            cr.execute("SELECT intrnal_desig FROM hr_employee WHERE id = %s",(empl_id,))
            designation = cr.fetchone()[0]

            param = self.env['ir.config_parameter']
            channelSalesDincharyaConfig = param.search([('key', '=', 'channelSalesDincharyaConfig')])
            if not channelSalesDincharyaConfig:
                raise osv.except_osv(_('Warning!'), _('Please contact to Admin for Dincharya Configuration'))
            channelSalesDincharyaConfig = tuple(map(str, channelSalesDincharyaConfig.value.split(',')))

            if designation in channelSalesDincharyaConfig:
                str_sql = "SELECT " \
                              "emp.id," \
                              "emp.nf_emp," \
                              "emp.intrnal_desig," \
                              "emp.work_email, " \
                              "res.user_id " \
                              "FROM hr_employee emp " \
                              "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                              "WHERE res.active = True AND emp.work_email IS NOT NULL " \
                              "AND emp.coach_id = {} AND res.user_id IS NOT NULL " \
                              "AND emp.intrnal_desig IN ('Channel Sales Manager','Partner Development Consultant')"\
                    .format(empl_id)
            else:
                str_sql = "SELECT " \
                          "emp.id," \
                          "emp.nf_emp," \
                          "emp.intrnal_desig," \
                          "emp.work_email, " \
                          "res.user_id " \
                          "FROM hr_employee emp " \
                          "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                          "WHERE res.active = True AND emp.work_email IS NOT NULL " \
                          "AND emp.virtual_branch_id IN (SELECT id FROM hr_branch WHERE manager_id = {}) " \
                          "AND res.user_id IS NOT NULL AND emp.intrnal_desig IN {}" \
                    .format(empl_id, FOS_Desig + Tele_Desig)

            cr.execute(str_sql)
            emp_ids = cr.fetchall()
            tmp = [(0, False, {'employee_id': val[0],
                               'emp_id':val[1],
                               'desig':val[2],
                               'email':val[3],
                               'new_meeting_num':self.get_meeting_num(val[4], val[2]),
                               'followup_meeting_num':self.followup_meeting_num,
                               'meeting_date':self.meeting_date,
                               })
                   for val in emp_ids]
            self.nf_biz_lines = tmp

    @api.multi
    def submit(self):
        cr = self.env.cr
        str_sql = "SELECT " \
                    "emp_id," \
                    "performance " \
                    "FROM nf_biz_line " \
                    "WHERE biz_id = {} AND performance is null"\
            .format(self.id)
        cr.execute(str_sql)
        tmp = cr.fetchall()
        for val in tmp:
            if not val[1]:
                raise osv.except_osv(_('Alert!'), _('Please define performance of your team member "%s"') % val[0])
        self.write({'state':'Posted'})
        self.send_email()
        self.send_individual_email()
        return True

    @api.multi
    def reset(self,cr,uid,ids,context=None):
        self.write({'state': 'Draft'})
        return True

    @api.multi
    def send_email(self):
        company = self.env['res.company'].browse(1)
        obj = self
        cr = self.env.cr
        team_email = ['mohit.katiyar@nowfloats.com']
        mgnr_parent_email = obj.employee_id.coach_id and obj.employee_id.coach_id.work_email.strip() or False
        if mgnr_parent_email:
            team_email.append(mgnr_parent_email)

        rec = """ """
        fnt_clr = "blue"
        meeting_num = ''
        for val in obj.nf_biz_lines:
            if val.meeting_date:
                meeting_date = datetime.strptime(val.meeting_date, "%Y-%m-%d")
                meeting_date = datetime.strftime(meeting_date, '%d-%m-%Y')
                meeting_num = str(meeting_date or '') + ': ' + str(val.new_meeting_num or '0') + '/' + str(val.followup_meeting_num or '0')
            if val.performance == 'GOOD':
                remark = val.good_remark
                fnt_clr = "green"

            elif val.performance == 'AVERAGE':
                remark = val.average_remark
                fnt_clr = "brown"

            elif val.performance == 'BAD':
                remark = val.bad_remark
                fnt_clr = "red"

            elif val.performance == 'ABSENT':
                remark = ''
                fnt_clr = "grey"

	    manager_suggestion = val.manager_suggestion
	    plan_of_action = val.plan_of_action
	    
 	    if manager_suggestion:
	       manager_suggestion = manager_suggestion.encode('ascii', 'ignore').decode('ascii')

	    if plan_of_action:
	       plan_of_action = plan_of_action.encode('ascii', 'ignore').decode('ascii')

	    if remark:
	       remark = remark.encode('ascii', 'ignore').decode('ascii')

            rec = rec +  """<tr width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
                          <td width="15% class="text-left"><font color="""+str(fnt_clr)+""">"""+str(val.employee_id.name_related)+"""</font></td>
                          <td width="11%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(val.performance)+"""</font></td>
                          <td width="15%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(remark)+"""</font></td>
                          <td width="27%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(plan_of_action or '')+"""</font></td>
                          <td width="27%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(manager_suggestion or '')+"""</font></td>
                          <td width="5%"  align="center" class="text-center"><font color="""+str(fnt_clr)+""">"""+str(meeting_num)+"""</font></td>
                    <tr>
                    <tr width="100%" colspan="6" height="5"></tr>
                    """

        date = datetime.strptime(obj.date, '%Y-%m-%d')
        date = date.strftime('%d-%b-%Y')
        heading = "NowFloats Dincharya for "+str(date)+""

        branch_name = obj.employee_id.branch_id.name
        i = 0
        cr.execute("SELECT name FROM hr_branch WHERE manager_id = %s ORDER BY name",(obj.employee_id.id,))
        branches = cr.fetchall()

        if branches:
            for b in branches:
                if i == 0:
                    branch_name = b[0]
                else:
                    branch_name += ' & ' + b[0]
                i = i + 1

        mail_subject = branch_name + " " + "Dincharya Review by" + " " +str(obj.employee_id.name_related)+ " : " + date
        html = """<!DOCTYPE html>
                                 <html>

                                   <body>
                                     <table style="width:100%">
                                          <tr>
                                             <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></center></td>
                                          </tr>
                                     </table>
                                          <br/>
                                     <table width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
                                     <tr width="100%" class="border-black">
                                          <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Employee</b> </td>
                                          <td width="11%"  class="text-left" style="border-bottom: 1px solid black;"> <b>Yesterday's Performace</b> </td>
                                          <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Remark</b> </td>
                                          <td width="27%" class="text-left" style="border-bottom: 1px solid black;"> <b>Plan of Action</b> </td>
                                          <td width="27%" class="text-left" style="border-bottom: 1px solid black;"> <b>Manager's Suggestion</b> </td>
                                          <td width="5%" class="text-left" style="border-bottom: 1px solid black;"> <b>Meetings (new/follow-up)</b> </td>
                                      </tr>

                                          """+str(rec)+"""
                                    </table>
                                </body>

                        <div>
                            <p></p>
                        </div>
                <html>"""

        msg = MIMEMultipart()
        emailfrom = "erp@nowfloats.com"
        emailto = [obj.employee_id.work_email.strip(),'dincharya@nowfloats.com']+team_email
        msg['From'] = emailfrom
        msg['To'] = ", ".join(emailto)
        msg['Subject'] = mail_subject

        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'NowFloats Dincharya'")
        mail_server = cr.fetchone()
        smtp_user = mail_server[0]
        smtp_pass = mail_server[1]
        server = smtplib.SMTP_SSL('smtp.gmail.com',465)
        server.login(smtp_user,smtp_pass)
        text = msg.as_string()
        try:
            server.sendmail(emailfrom, emailto , text)
        except:
          pass
        server.quit()
        return True

    @api.multi
    def send_individual_email(self):
        company = self.env['res.company'].browse(1)
        obj = self
        cr = self.env.cr
        manager_email = obj.employee_id.work_email.strip()

        rec = """ """
        fnt_clr = "blue"
        meeting_num = ''
        for val in obj.nf_biz_lines:
            if val.meeting_date:
                meeting_date = datetime.strptime(val.meeting_date, "%Y-%m-%d")
                meeting_date = datetime.strftime(meeting_date, '%d-%m-%Y')
            meeting_num = str(meeting_date or '') + ': ' + str(val.new_meeting_num or '0') + '/' + str(val.followup_meeting_num or '0')
            if val.performance == 'GOOD':
                remark = val.good_remark
                fnt_clr = "green"

            elif val.performance == 'AVERAGE':
                remark = val.average_remark
                fnt_clr = "brown"

            elif val.performance == 'BAD':
                remark = val.bad_remark
                fnt_clr = "red"

            elif val.performance == 'ABSENT':
                remark = ''
                fnt_clr = "grey"

	    manager_suggestion = val.manager_suggestion
	    plan_of_action = val.plan_of_action
	    
 	    if manager_suggestion:
	       manager_suggestion = manager_suggestion.encode('ascii', 'ignore').decode('ascii')

	    if plan_of_action:
	       plan_of_action = plan_of_action.encode('ascii', 'ignore').decode('ascii')

	    if remark:
	       remark = remark.encode('ascii', 'ignore').decode('ascii')

            rec = """<tr width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
                          <td width="15%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(val.employee_id.name_related)+"""</font></td>
                          <td width="11%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(val.performance)+"""</font></td>
                          <td width="15%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(remark)+"""</font></td>
                          <td width="27%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(plan_of_action or '')+"""</font></td>
                          <td width="27%" class="text-left"><font color="""+str(fnt_clr)+""">"""+str(manager_suggestion or '')+"""</font></td>
                          <td width="5%"  align="center" class="text-center"><font color="""+str(fnt_clr)+""">"""+str(meeting_num)+"""</font></td>
                    <tr>"""

            date = datetime.strptime(obj.date, '%Y-%m-%d')
            date = date.strftime('%d-%b-%Y')
            heading = "NowFloats Dincharya for "+str(date)+""

            branch_name = obj.employee_id.branch_id.name
            i = 0
            cr.execute("SELECT name FROM hr_branch WHERE manager_id = %s ORDER BY name", (obj.employee_id.id,))
            branches = cr.fetchall()

            if branches:
                for b in branches:
                    if i == 0:
                        branch_name = b[0]
                    else:
                        branch_name += ' & ' + b[0]
                    i = i + 1

            mail_subject = branch_name + " " + "Dincharya Review by" + " " +str(obj.employee_id.name_related)+ " : " + date
            html = """<!DOCTYPE html>
                                     <html>

                                       <body>
                                         <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></center></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table width="100%" style="border-top: 1px solid black;">
                                         <tr width="100%" class="border-black">
                                              <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Employee</b> </td>
                                              <td width="11%" class="text-left" style="border-bottom: 1px solid black;"> <b>Yesterday's Performace</b> </td>
                                              <td width="15%" class="text-left" style="border-bottom: 1px solid black;"> <b>Remark</b> </td>
                                              <td width="27%" class="text-left" style="border-bottom: 1px solid black;"> <b>Plan of Action</b> </td>
                                              <td width="27%" class="text-left" style="border-bottom: 1px solid black;"> <b>Manager's Suggestion</b> </td>
                                              <td width="5%" class="text-left" style="border-bottom: 1px solid black;"> <b>Meetings (new/follow-up)</b> </td>
                                          </tr>

                                              """+str(rec)+"""
                                        </table>
                                    </body>

                            <div>
                                <p></p>
                                <p></p>
                                <p></p>
                                <p></p>
                                <p></p>
                                <p></p>
                                <p></p>
                                <p></p>
                                <p></p>
                            </div>
                    <html>"""

            msg = MIMEMultipart()
            emailfrom = "erp@nowfloats.com"
            emailto = [val.email.strip()]+[manager_email]
            msg['From'] = emailfrom
            msg['To'] = ", ".join(emailto)
            msg['Subject'] = mail_subject

            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'NowFloats Dincharya'")
            mail_server = cr.fetchone()
            smtp_user = mail_server[0]
            smtp_pass = mail_server[1]
            server = smtplib.SMTP_SSL('smtp.gmail.com',465)
            server.login(smtp_user,smtp_pass)
            text = msg.as_string()
            try:
                server.sendmail(emailfrom, emailto , text)
            except:
              pass
            server.quit()
        return True


class nf_biz_line(models.Model):
    _name = 'nf.biz.line'

    employee_id = fields.Many2one('hr.employee', 'Employee', track_visibility='onchange')
    emp_id = fields.Char('Employee ID')
    desig = fields.Char('Designation')
    email = fields.Char('Email')
    performance = fields.Selection([('GOOD','GOOD'),('AVERAGE','AVERAGE'),('BAD','BAD'),('ABSENT','ABSENT')],string="How was yesterday's performance?")
    plan_of_action = fields.Text("What is the action plan for today?")
    manager_suggestion = fields.Text("Branch Manager's advice to FOS/Tele")
    biz_id = fields.Many2one('nf.biz','Biz')
    good_remark = fields.Text("What went well?")
    average_remark = fields.Text("why was the day average?")
    bad_remark = fields.Text("why was the day bad?")
    new_meeting_num = fields.Integer('What were the number of new meetings?')
    followup_meeting_num = fields.Integer('What were the number of follow-up meetings?')
    meeting_date = fields.Date('Last meeting date')
    num_of_order = fields.Integer('How many orders logged in the ERP till date?')
    net_revenue = fields.Integer('What is the net revenue achieved till date?')

    @api.model
    def create(self, vals):
        if 'plan_of_action' in vals and vals['plan_of_action'] and len(vals['plan_of_action']) < 50:
            raise osv.except_osv(_('Alert!'), _('There must be 50 characters at least in Plan Of Action for "%s"' % vals['emp_id']))

        if 'manager_suggestion' in vals and vals['manager_suggestion'] and len(vals['manager_suggestion']) < 50:
            raise osv.except_osv(_('Alert!'), _("There must be 50 characters at least in Manager's Suggestion for '%s'" % vals['emp_id']))

        res = super(nf_biz_line,self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if 'plan_of_action' in vals and vals['plan_of_action'] and len(vals['plan_of_action']) < 50:
            raise osv.except_osv(_('Alert!'), _('There must be 50 characters at least in Plan Of Action for "%s"' % self.emp_id))

        if 'manager_suggestion' in vals and vals['manager_suggestion'] and len(vals['manager_suggestion']) < 50:
            raise osv.except_osv(_('Alert!'), _("There must be 50 characters at least in Manager's Suggestion for '%s'" % self.emp_id))

        res = super(nf_biz_line,self).write(vals)
        return res


