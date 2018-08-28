from openerp import api, fields, models, _
import time
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import calendar
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib2 import Request, urlopen
import json,urllib,urllib2
import smtplib
import functools
import xmlrpclib
import psycopg2
import base64
import csv
from email.mime.application import MIMEApplication
import StringIO

FOS_Desig = ('Associate - FOS','Consultant - FOS','Principal Consultant - FOS','Senior Consultant - FOS','Associate Product Specialist','Principal Product Specialist','Product Specialist','Senior Product Specialist','Associate - Customer First','Consultant - Customer First','Principal Consultant - Customer First','Senior Consultant - Customer First','Associate - Verticals','Consultant - Verticals','Principal Consultant - Verticals','Senior Consultant - Verticals')

Tele_Desig = ('Associate - Tele Sales','Consultant - Tele Sales','Principal Consultant - Tele Sales','Senior Consultant - Tele Sales')

only_fos_desig = ('Associate - FOS','Consultant - FOS','Principal Consultant - FOS','Senior Consultant - FOS','Associate Product Specialist',
'Principal Product Specialist','Product Specialist','Senior Product Specialist','Associate - Verticals','Consultant - Verticals',
'Principal Consultant - Verticals','Senior Consultant - Verticals')

team_lead_desig = ('Assistant Team Leader', 'Assistant Team Lead - FOS', 'Associate Team Lead', 'Team Lead - FOS', 'Team Leader - Rest Of State', 'Team Leader', 'Team Lead - Product Specialist')

class nf_schedular(models.Model):
    _name = "nf.schedular"
    
    @api.model
    def allocation_leave(self):
        self.env.cr.execute("select leave_allocation(Null)")
        return True

    @api.model
    def send_lop_email(self):
        ROOT = 'http://erp.nowfloats.com/xmlrpc/'
        uid = 7976
        database = 'NowFloatsV10'
        PASS = 'ERPapi123'
        call = functools.partial(xmlrpclib.ServerProxy(ROOT + 'object').execute, database, uid, PASS)
        temp = call('nf.biometric', 'sync_biometric_data')
        if not temp:
            return False
        new_cn = psycopg2.connect("dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()
        new_cr.execute("SELECT * FROM update_swipe_leave_attendance()")
        temp1 = new_cr.fetchall()
        new_cn.commit()
        new_cr.execute("SELECT max(date) FROM nf_leave_swipe")
        max_date = new_cr.fetchone()[0]

        new_cr.execute("SELECT value FROM ir_config_parameter WHERE key = 'LOPEmailExceptionEmployeeId'")
        lop_exception_emp = new_cr.fetchone()[0]
        lop_exception_emp = tuple(map(int, lop_exception_emp.split(',')))

        new_cr.execute("SELECT name FROM nf_deputation WHERE travel_date <= '{}' AND till_date >= '{}' AND state = 'Approve'".format(max_date, max_date))
        deputation_emp = new_cr.fetchall()
        deputation_emp = tuple(int(dep_emp[0]) for dep_emp in deputation_emp)

        exception_emp = lop_exception_emp + deputation_emp

        new_cr.execute("SELECT "
                       "emp.work_email, "
                       "emp.name_related, "
                       "(SELECT count(*) FROM nf_leave_swipe WHERE attendance_status = 'A' "
                       "AND hr_emp_id = lv_swp.hr_emp_id AND date >= (DATE_TRUNC('month', lv_swp.date))::date) "
                       "AS lop_count,"
                       "(SELECT COALESCE(work_email,'') FROM hr_employee WHERE id = emp.coach_id) AS reporting_head_email,"
                       "(SELECT COALESCE(work_email,'') FROM hr_employee WHERE id = emp.parent_id) AS manager_email,"
                       "emp.intrnal_desig AS internal_desig, "
		       "emp.nf_emp AS emp_id "
                       "FROM nf_leave_swipe lv_swp "
                       "INNER JOIN hr_employee emp ON lv_swp.hr_emp_id = emp.id "
                       "LEFT JOIN hr_department dept ON emp.sub_dep = dept.id "
                       "WHERE lv_swp.date = '{}' AND lv_swp.attendance_status = 'A' "
                       "AND emp.id NOT IN {} AND ((SELECT name FROM hr_department WHERE id = dept.parent_id) NOT IN ('Product Development', 'KIT-Product', 'Design', 'Kitsune-BU', 'Development', 'Content')) AND (SELECT COALESCE(work_email,'') FROM hr_employee WHERE id = emp.coach_id) != '	neeraj@nowfloats.com' AND (SELECT COALESCE(work_email,'') FROM hr_employee WHERE id = emp.parent_id) != 'neeraj@nowfloats.com' "
                       "ORDER BY emp.name_related"
                       .format(max_date, exception_emp))
        lop_emp = new_cr.fetchall()
        lop_date = datetime.strptime(max_date, '%Y-%m-%d')
        lop_day, lop_month, lop_month_abbr, lop_wday, lop_wday_abbr, year = lop_date.strftime('%d/%B/%b/%A/%a/%Y').split('/')
        lop_day = int(lop_day)
        ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])
        bcc_id = ['nitin@nowfloats.com']
        Desig = FOS_Desig + Tele_Desig
        for val in lop_emp:
            emp_email = val[0]
            emp_name = val[1]
            lop_count = val[2]
            reporting_head_email = val[3]
            manager_email = val[4]
            internal_desig = val[5]
	    emp_id = val[6]
            cc_id = ['leaves@nowfloats.com', 'shaikmahaboob.basha@nowfloats.com']
            
	    lop_reason  = 'Since there is no swipe or approved leave in erp, LOP has been marked.'
	    if reporting_head_email:
                cc_id.append(reporting_head_email)
            if manager_email:
                cc_id.append(manager_email)
            if internal_desig in Desig:
                cc_id.append('salesaudit@nowfloats.com')
	    if internal_desig in FOS_Desig:
	        lop_reason  = 'Since there is no swipe or approved leave or required Meeting in erp, LOP has been marked.'
            mail_subject = "LOP for {} | {}, {} {}".format(emp_name, lop_wday_abbr, lop_month_abbr, lop_day)
            html = """<!DOCTYPE html>
                						 <html>
                						   <body>
                							 <p> [{}] {},</p></br>
					                         <p>Yesterday, <i>{}, {} {}, {}</i>, has been marked as loss of pay (LOP) for you. This is your {} LOP this month.</p></br>
                							 <p>{}</p></br>
                							 <p>For any query, contact HR <b>@Helpdesk Ticket</b></p></br>
                							 <p>-HR</p>
                						   </body>
                						  <html>"""\
                .format(emp_id, emp_name, lop_wday, lop_month, lop_day, year, ordinal(lop_count), lop_reason)

            toaddr = [emp_email]
            msg = MIMEMultipart('alternative')
            text = "plaintext"
            part1 = MIMEText(text, 'plain')
            html = html
            part2 = MIMEText(html, 'html')

            emailfrom = "erpnotification@nowfloats.com"
            toaddr = [emp_email]
            msg['From'] = emailfrom
            msg['To'] = ", ".join(toaddr)
            msg['CC'] = ", ".join(cc_id)
            msg['BCC'] = ", ".join(bcc_id)
            msg['Subject'] = mail_subject

            emailto = toaddr + cc_id + bcc_id

            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            new_cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
            mail_server = new_cr.fetchone()
            smtp_user = mail_server[0]
            smtp_pass = mail_server[1]
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            try:
                server.sendmail(emailfrom, emailto, text)
            except:
                pass
            server.quit()

        new_cn.close()
        return True

    @api.model
    def send_non_swipe_bm(self):
        cr = self.env.cr
        synq_bmtc = self.env['nf.biometric'].sync_biometric_data()
        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        if current_day != 'Sunday':
            date = date.strftime('%d-%b-%Y')
            rec = """ """
            cc = []

            str_sql = "SELECT " \
                      "DISTINCT COALESCE(emp.nf_emp,'')," \
                      "emp.name_related AS name," \
                      "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch," \
                      "emp.branch_id AS branch_id," \
                      "COALESCE(emp.work_email,'') AS bm_email," \
                      "COALESCE((SELECT work_email FROM hr_employee where id = emp.parent_id),'') AS bm_manager_email " \
                      "FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True " \
                      "AND emp.intrnal_desig = 'Branch Manager' " \
                      "AND emp.nf_emp NOT IN (SELECT emp_id FROM nf_biometric WHERE attendance_date::date = 'now'::date) " \
                      "ORDER BY emp.name_related"

            cr.execute(str_sql)
            temp = cr.fetchall()

            param = self.env['ir.config_parameter']
            BranchWithoutBiometric = param.search([('key', '=', 'BranchWithoutBiometric')])
            BranchWithoutBiometric = map(int, BranchWithoutBiometric.value.split(','))

            for val in temp:
                emp_id = val[0]
                name = val[1]
                branch = val[2]
                if val[3] in BranchWithoutBiometric:
                    fnt_clr = "grey"
                    bmtc_sts = 'NA'
                else:
                    fnt_clr = "red"
                    bmtc_sts = 'Working'
                    cc.extend((val[4], val[5]))

                rec = rec + """<tr width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
    										  <td width="20% class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(emp_id) + """</font></td>
    										  <td width="30%" class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(name) + """</font></td>
    										  <td width="30%" class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(branch) + """</font></td>
    										  <td width="20%" class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(bmtc_sts or '') + """</font></td>

    					<tr>
    					<tr width="100%" colspan="6" height="5"></tr>"""

            mail_subject = "Details of BM not in Office/Absent on %s, TIME STAMP : 11 AM" % date

            heading = "Please find details of BM not in Office/Absent on %s, TIME STAMP : 11 AM" % date

            html = """<!DOCTYPE html>
    						 <html>

    						   <body>
    							 <p style="color:#4E0879">  <b>Dear Team,</b></p>
    							 <table style="width:100%">
    								  <tr>
    									 <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></center></td>
    								  </tr>
    							 </table>
    								  <br/>
    							 <table width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
    							 <tr width="100%" class="border-black">
    								  <td width="20%" class="text-left" style="border-bottom: 1px solid black;"> <b>Emp ID</b> </td>
    								  <td width="30%"  class="text-left" style="border-bottom: 1px solid black;"> <b>Name</b> </td>
    								  <td width="30%" class="text-left" style="border-bottom: 1px solid black;"> <b>Branch</b> </td>
    								  <td width="20%" class="text-left" style="border-bottom: 1px solid black;"> <b>Att Machine Status</b> </td>
    							  </tr>

    								  """ + str(rec) + """
    							</table>
    						</body>

    						<div>
    							<p></p>
    						</div>
    							<html>"""

            msg = MIMEMultipart()
            emailfrom = "erpnotification@nowfloats.com"
            toaddr = ['raunak.ansari@nowfloats.com', 'satesh.kohli@nowfloats.com', 'anurupa.singh@nowfloats.com',
                      'nitin@nowfloats.com', 'richa.gaur@nowfloats.com', 'vivek.naithani@nowfloats.com',
                      'mohit.katiyar@nowfloats.com']
            msg['From'] = emailfrom
            msg['To'] = ", ".join(toaddr)
            msg['CC'] = ", ".join(cc)
            msg['Subject'] = mail_subject
            emailto = toaddr + cc

            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
            mail_server = cr.fetchone()
            smtp_user = mail_server[0]
            smtp_pass = mail_server[1]
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            try:
                server.sendmail(emailfrom, emailto, text)
            except:
                pass
            server.quit()
        return True

    @api.model
    def birthday_notification(self):
        curr_date = datetime.now().strftime("%m-%d")
        for rec in self.env['hr.employee'].sudo().search([('active','=',True)]):
            birthday = rec.birthday
            if birthday:
                birthday = birthday[5:10]
                if birthday == curr_date:
                    temp_id = self.env['mail.template'].search([('name', '=', 'Birthday Notification')])
                    if temp_id:
                        temp_id.send_mail(rec.id)

        return True

    @api.model
    def work_anniversary_notification(self):
        current_date = datetime.now()
        curr_date = current_date.strftime("%m-%d")
        curr_year = current_date.year
        for rec in self.env['hr.employee'].sudo().search([('active','=',True)]):
            joining_date = rec.join_date
            if joining_date:
                join_date = joining_date[5:10]
                join_year = joining_date[0:4]
                duration = curr_year - int(join_year)
                if join_date == curr_date:
                    if rec.gender == 'male':
                        if duration == 1:
                            temp_id1 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 1 Year')])
                            if temp_id1:
                                temp_id1.send_mail(rec.id)
                        elif duration == 2:
                            temp_id2 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 2 Years')])
                            if temp_id2:
                                temp_id2.send_mail(rec.id)
                        elif duration == 3:
                            temp_id3 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 3 Years')])
                            if temp_id3:
                                temp_id3.send_mail(rec.id)
                        elif duration == 4:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 4 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)
                    elif rec.gender == 'female':
                        if duration == 1:
                            temp_id1 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 1 Year')])
                            if temp_id1:
                                temp_id1.send_mail(rec.id)
                        elif duration == 2:
                            temp_id2 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 2 Years')])
                            if temp_id2:
                                temp_id2.send_mail(rec.id)
                        elif duration == 3:
                            temp_id3 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 3 Years')])
                            if temp_id3:
                                temp_id3.send_mail(rec.id)
                        elif duration == 4:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 4 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)

        return True

    #============================FOS Meeting Email==============================================

    @api.model
    def get_tele_lop_count(self, number, branch_ids, attendance_status):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND res.user_id NOT IN (SELECT sp_id FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) " \
                .format(Tele_Desig, branch_ids, attendance_status)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(Tele_Desig, branch_ids, attendance_status, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(Tele_Desig, branch_ids, attendance_status)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp

    @api.model
    def get_tele_meeting_count(self, number, branch_ids):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND res.user_id NOT IN (SELECT sp_id FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)" \
                .format(Tele_Desig, branch_ids)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{})) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(Tele_Desig, branch_ids, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{})) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(Tele_Desig, branch_ids)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp


    @api.model
    def get_fos_lop_count(self, number, branch_ids, attendance_status, type='FOS'):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        internal_desig = only_fos_desig
        if type == 'team_lead':
            internal_desig = team_lead_desig

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) " \
                .format(internal_desig, branch_ids, attendance_status)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(internal_desig, branch_ids, attendance_status, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(internal_desig, branch_ids, attendance_status)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp

    @api.model
    def get_fos_meeting_count(self, number, branch_ids, type='FOS'):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        internal_desig = only_fos_desig
        if type == 'team_lead':
            internal_desig = team_lead_desig

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND emp.branch_id = ANY(ARRAY{}) " \
                      "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)" \
                .format(internal_desig, branch_ids)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{})) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(internal_desig, branch_ids, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 AND emp.branch_id = ANY(ARRAY{})) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(internal_desig, branch_ids)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp

    @api.model
    def get_meeting_count_file(self, branch_ids):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()
        fp = StringIO.StringIO()
        writer = csv.writer(fp)
        new_cr.execute("SELECT "
                   "cm.date::date AS date, "
                   "emp.name_related AS employee, "
                   "emp.work_email AS email, "
                   "COUNT(cm.id) AS Yesterday_meeting_count,"
                   "(SELECT count(id) FROM crm_phonecall "
                   "WHERE user_id = cm.user_id "
                       "AND date::date BETWEEN DATE_TRUNC('month', now() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                   "AND (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)  AS MTD_meeting_count, "
                   "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch,"
                   "emp.intrnal_desig AS emp_designation,"
                   "(SELECT static_attendance FROM nf_leave_swipe "
                       "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) AS swipe_status,"
                   "CASE WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'L' "
                        "THEN 'Legal Leaves' "
                        "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'A' "
                   "THEN 'LOP(No-Swipe)' "
                   "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'P' "
                       "THEN 'Present' "
                   "ELSE (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) END AS final_attendance, "
                       "emp.join_date AS date_of_join,"
                       "(NOW() AT TIME ZONE 'UTC')::date - emp.join_date AS  tenure_in_days "
                   "FROM crm_phonecall cm LEFT JOIN resource_resource res ON cm.user_id = res.user_id "
                   "LEFT JOIN hr_employee emp ON emp.resource_id = res.id "
                   "WHERE cm.date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                   "AND res.active = True AND emp.intrnal_desig IN {} AND emp.branch_id = ANY(ARRAY{}) "
                   "GROUP BY cm.date::date, emp.name_related, emp.work_email, "
                       "(SELECT name FROM hr_branch WHERE id = emp.branch_id), emp.intrnal_desig, "
                       "(SELECT static_attendance FROM nf_leave_swipe "
                       "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1), cm.user_id, "
                       "emp.join_date, (NOW() AT TIME ZONE 'UTC')::date - emp.join_date "
                   "ORDER BY emp.name_related".format(only_fos_desig + team_lead_desig, branch_ids))
        writer.writerow([i[0] for i in new_cr.description])
        temp1 = new_cr.fetchall()
        for val in temp1:
            writer.writerow(val)

        new_cr.execute("SELECT (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date AS date, "
                   "emp.name_related AS employee, "
                   "emp.work_email AS email, "
                   " 0 AS Yesterday_meeting_count, "
                   "(SELECT count(id) FROM crm_phonecall "
                   "WHERE user_id = res.user_id "
                       "AND date::date BETWEEN DATE_TRUNC('month', now() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                   "AND (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)  AS MTD_meeting_count, "
                   "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch,"
                   "emp.intrnal_desig AS emp_designation,"
                   "(SELECT static_attendance FROM nf_leave_swipe "
                       "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) AS swipe_status,"
                  "CASE WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'L' "
                       "THEN 'Legal Leaves' "
                       "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'A' "
                      "THEN 'LOP(No-Swipe)' "
                       "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'P' "
                      "THEN 'LOP(0-M)' "
                      "ELSE (SELECT static_attendance FROM nf_leave_swipe "
                            "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) "
                   "END AS final_attendance,"
                   "emp.join_date AS date_of_join,"
                   "(NOW() AT TIME ZONE 'UTC')::date - emp.join_date AS  tenure_in_days  " \
                   "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                   "WHERE res.active = True AND " \
                   "emp.intrnal_desig IN {} AND emp.branch_id = ANY(ARRAY{}) " \
                   "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                   "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)" \
                   .format(only_fos_desig + team_lead_desig, branch_ids))
        temp2 = new_cr.fetchall()
        for val in temp2:
            writer.writerow(val)

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    @api.model
    def get_meeting_details_file(self, branch_ids):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        fp = StringIO.StringIO()
        writer = csv.writer(fp)

        new_cr.execute("SELECT * FROM crm_fos_meeting_view "
                       "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date AND sp_designation IN {} "
                       "AND sp_branch_id = ANY(ARRAY{})"
                       .format(only_fos_desig + team_lead_desig, branch_ids))

        writer.writerow([i[0] for i in new_cr.description])

        temp = new_cr.fetchall()
        for val in temp:
            try:
                val = map(lambda x: x.encode('utf-8') if x and type(x) is not int else x, val)
                writer.writerow(val)
            except:
                pass

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    def get_total_number_of_new_fos_tele(self, branch_ids):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        new_cr.execute("SELECT COALESCE(count(emp.id),0) FROM "
                       "hr_employee emp "
                       "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                       "WHERE res.active = True AND emp.intrnal_desig IN {} "
                       "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) <= 10 "
                       "AND emp.branch_id = ANY(ARRAY{})"
                       .format(only_fos_desig, branch_ids))
        total_new_fos = new_cr.fetchone()[0]

        new_cr.execute("SELECT COALESCE(count(emp.id),0) FROM "
                       "hr_employee emp "
                       "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                       "WHERE res.active = True AND emp.intrnal_desig IN {} "
                       "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) <= 10 "
                       "AND emp.branch_id = ANY(ARRAY{})"
                       .format(team_lead_desig, branch_ids))
        total_new_team_lead = new_cr.fetchone()[0]

        new_cr.execute("SELECT COALESCE(count(emp.id),0) FROM "
                       "hr_employee emp "
                       "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                       "WHERE res.active = True AND emp.intrnal_desig IN {} "
                       "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) <= 10 "
                       "AND emp.branch_id = ANY(ARRAY{})"
                       .format(Tele_Desig, branch_ids))
        total_new_tele = new_cr.fetchone()[0]

        return [total_new_fos, total_new_team_lead, total_new_tele]

    @api.model
    def get_tele_meeting_count_file(self, branch_ids):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        fp = StringIO.StringIO()
        writer = csv.writer(fp)

        new_cr.execute("SELECT leave.date, "
                       "emp.name_related, "
                       "emp.work_email,"
                       "(SELECT COALESCE(count(sp_id), 0)::integer FROM crm_tele_meeting_view WHERE sp_id = leave.user_id "
                       "AND date_of_meeting::date = leave.date) AS meeting_count,"
                       "emp.intrnal_desig AS internal_desig,"
                       "branch.name AS branch,"
                       "leave.swipe_status,"
                       "leave.attendance_status,"
                       "emp.join_date AS date_of_join,"
                       "(NOW() AT TIME ZONE 'UTC')::date - emp.join_date AS  tenure_in_days "
                       "FROM nf_leave_swipe leave "
                       "LEFT JOIN hr_employee emp ON leave.hr_emp_id = emp.id "
                       "LEFT JOIN resource_resource res ON emp.resource_id = res.id "
                       "LEFT JOIN hr_branch branch ON emp.branch_id = branch.id "
                       "WHERE leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                       "AND emp.intrnal_desig IN {} AND emp.branch_id = ANY(ARRAY{}) AND res.active = True"
                       .format(Tele_Desig, branch_ids))

        writer.writerow([i[0] for i in new_cr.description])

        temp = new_cr.fetchall()
        for val in temp:
            try:
                val = map(lambda x: x.encode('utf-8') if x and type(x) is not int else x, val)
                writer.writerow(val)
            except:
                pass

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    @api.model
    def sync_biometric_data(self):
        ROOT = 'http://erp.nowfloats.com/xmlrpc/'
        uid = 7976
        database = 'NowFloatsV10'
        PASS = 'ERPapi123'
        call = functools.partial(xmlrpclib.ServerProxy(ROOT + 'object').execute, database, uid, PASS)
        temp = call('nf.biometric', 'sync_biometric_data')
        if not temp:
            return False
        return True

    @api.model
    def send_number_of_meeting_details_branch_wise(self):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        if not self.sync_biometric_data():
            return False
        new_cr.execute("SELECT * FROM update_swipe_leave_attendance()")

        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        if current_day != 'Monday':
            date = date - relativedelta(days=1)
            date = date.strftime('%d-%b-%Y')
            cc = ['nitin@nowfloats.com', 'satesh.kohli@nowfloats.com', 'salesaudit@nowfloats.com', 'richa.gaur@nowfloats.com']

            new_cr.execute("SELECT id, name, "
                       "COALESCE((SELECT work_email FROM hr_employee WHERE id = manager_id),'') AS bm_email, "
                       "COALESCE((SELECT work_email FROM hr_employee WHERE id = rm_id), '') AS rm_email "
                       "FROM hr_branch ORDER BY id")
            branch = new_cr.fetchall()

            for b in branch:
                branch_ids = [b[0]]
                branch_name = b[1]
                bm_email = b[2]
                rm_email = b[3]

                # FOS
                cn1 = self.get_fos_meeting_count(1, branch_ids)[0]
                cn2 = self.get_fos_meeting_count(2, branch_ids)[0]
                cn3 = self.get_fos_meeting_count(3, branch_ids)[0]
                cn4 = self.get_fos_meeting_count(4, branch_ids)[0]

                cn5 = self.get_fos_meeting_count(0, branch_ids)[0]

                total_fos = cn1 + cn2 + cn3 + cn4 + cn5

                acn1 = self.get_fos_lop_count(1, branch_ids, 'A')[0]
                acn2 = self.get_fos_lop_count(2, branch_ids, 'A')[0]
                acn3 = self.get_fos_lop_count(3, branch_ids, 'A')[0]
                acn4 = self.get_fos_lop_count(4, branch_ids, 'A')[0]

                acn5 = self.get_fos_lop_count(0, branch_ids, 'A')[0]

                total_absent_fos = acn1 + acn2 + acn3 + acn4 + acn5

                lcn1 = self.get_fos_lop_count(1, branch_ids, 'L')[0]
                lcn2 = self.get_fos_lop_count(2, branch_ids, 'L')[0]
                lcn3 = self.get_fos_lop_count(3, branch_ids, 'L')[0]
                lcn4 = self.get_fos_lop_count(4, branch_ids, 'L')[0]

                lcn5 = self.get_fos_lop_count(0, branch_ids, 'L')[0]

                total_leave_fos = lcn1 + lcn2 + lcn3 + lcn4 + lcn5

                fos_lop_0m = cn5 - acn5 - lcn5

                # Team Lead

                lead_cn1 = self.get_fos_meeting_count(1, branch_ids, 'team_lead')[0]
                lead_cn2 = self.get_fos_meeting_count(2, branch_ids, 'team_lead')[0]
                lead_cn3 = self.get_fos_meeting_count(3, branch_ids, 'team_lead')[0]
                lead_cn4 = self.get_fos_meeting_count(4, branch_ids, 'team_lead')[0]

                lead_cn5 = self.get_fos_meeting_count(0, branch_ids, 'team_lead')[0]

                total_team_lead = lead_cn1 + lead_cn2 + lead_cn3 + lead_cn4 + lead_cn5

                lead_acn1 = self.get_fos_lop_count(1, branch_ids, 'A', 'team_lead')[0]
                lead_acn2 = self.get_fos_lop_count(2, branch_ids, 'A', 'team_lead')[0]
                lead_acn3 = self.get_fos_lop_count(3, branch_ids, 'A', 'team_lead')[0]
                lead_acn4 = self.get_fos_lop_count(4, branch_ids, 'A', 'team_lead')[0]

                lead_acn5 = self.get_fos_lop_count(0, branch_ids, 'A', 'team_lead')[0]

                total_absent_team_lead = lead_acn1 + lead_acn2 + lead_acn3 + lead_acn4 + lead_acn5

                lead_lcn1 = self.get_fos_lop_count(1, branch_ids, 'L', 'team_lead')[0]
                lead_lcn2 = self.get_fos_lop_count(2, branch_ids, 'L', 'team_lead')[0]
                lead_lcn3 = self.get_fos_lop_count(3, branch_ids, 'L', 'team_lead')[0]
                lead_lcn4 = self.get_fos_lop_count(4, branch_ids, 'L', 'team_lead')[0]

                lead_lcn5 = self.get_fos_lop_count(0, branch_ids, 'L', 'team_lead')[0]

                total_leave_team_lead = lead_lcn1 + lead_lcn2 + lead_lcn3 + lead_lcn4 + lead_lcn5

                lead_lop_0m = lead_cn5 - lead_acn5 - lead_lcn5

                # Tele
                t_cn1 = self.get_tele_meeting_count(1, branch_ids)[0]
                t_cn2 = self.get_tele_meeting_count(2, branch_ids)[0]
                t_cn3 = self.get_tele_meeting_count(3, branch_ids)[0]
                t_cn4 = self.get_tele_meeting_count(4, branch_ids)[0]
                t_cn5 = self.get_tele_meeting_count(0, branch_ids)[0]

                total_tele = t_cn1 + t_cn2 + t_cn3 + t_cn4 + t_cn5

                t_acn1 = self.get_tele_lop_count(1, branch_ids, 'A')[0]
                t_acn2 = self.get_tele_lop_count(2, branch_ids, 'A')[0]
                t_acn3 = self.get_tele_lop_count(3, branch_ids, 'A')[0]
                t_acn4 = self.get_tele_lop_count(4, branch_ids, 'A')[0]
                t_acn5 = self.get_tele_lop_count(0, branch_ids, 'A')[0]

                total_absent_tele = t_acn1 + t_acn2 + t_acn3 + t_acn4 + t_acn5

                t_lcn1 = self.get_tele_lop_count(1, branch_ids, 'L')[0]
                t_lcn2 = self.get_tele_lop_count(2, branch_ids, 'L')[0]
                t_lcn3 = self.get_tele_lop_count(3, branch_ids, 'L')[0]
                t_lcn4 = self.get_tele_lop_count(4, branch_ids, 'L')[0]
                t_lcn5 = self.get_tele_lop_count(0, branch_ids, 'L')[0]

                total_leave_tele = t_lcn1 + t_lcn2 + t_lcn3 + t_lcn4 + t_lcn5

                tele_lop_0m = t_cn5 - t_acn5 - t_lcn5

                total_new_fos, total_new_team_lead, total_new_tele = self.get_total_number_of_new_fos_tele(branch_ids)

                #Meeting Count
                msg = MIMEMultipart()
                data = self.get_meeting_count_file(branch_ids)
                file_name = 'meeting_count_by_fos_for_{}.csv'.format(branch_name)

                data = base64.b64decode(data)
                part = MIMEApplication(
                    data,
                    Name=file_name
                )
                part['Content-Disposition'] = 'attachment; filename="{}"' \
                    .format(file_name)
                msg.attach(part)

                # Meeting Details
                data = self.get_meeting_details_file(branch_ids)
                file_name = 'meeting_details_by_fos_for_.csv'

                data = base64.b64decode(data)
                part = MIMEApplication(
                    data,
                    Name=file_name
                )
                part['Content-Disposition'] = 'attachment; filename="{}"' \
                    .format(file_name)
                msg.attach(part)

                # Tele Meeting Count
                data = self.get_tele_meeting_count_file(branch_ids)
                file_name = 'meeting_count_by_tele_for_{}.csv'.format(branch_name)

                data = base64.b64decode(data)
                part = MIMEApplication(
                    data,
                    Name=file_name
                )
                part['Content-Disposition'] = 'attachment; filename="{}"' \
                    .format(file_name)
                msg.attach(part)

                mail_subject = "FOS meeting count on %s || Branch - %s" % (date, branch_name)

                heading = "FOS meeting count on %s || Branch - %s" % (date, branch_name)

                tele_heading = "Tele meeting count on %s || Branch - %s" % (date, branch_name)

                team_lead_heading = "Team Lead meeting count on %s || Branch - %s" % (date, branch_name)

                description = "1. This report is showing employees having tenure greater than 10 days. <br/>" \
                              "2. Attached spreadsheet is containing complete data in details.<br/>" \
                              "3. Total number of FOS having tenure less than or equal to 10 days : {} <br/>" \
                              "4. Total number of Team Lead having tenure less than or equal to 10 days : {} <br/>" \
                              "5. Total number of Tele having tenure less than or equal to 10 days : {} <br/>" \
                    .format(total_new_fos, total_new_team_lead, total_new_tele)

                html = """<!DOCTYPE html>
                                         <html>

                                           <body>
                                             <table style="width:100%">
                                                  <tr>
                                                     <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></left></td>
                                                  </tr>
                                                  <tr>
                                                     <td><left><span>""" + str(description) + """</span></left></td>
                                                  </tr>
                                             </table>
                                                  <br/>
                                             <table style="width:100%">
                                                 <tr style="width:100%">
                                                     <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                     <td class="text-left" style="width:20%"><font color= "red"/>: <b>FOS-Headcount (<span>""" + str(
                    total_fos) + """<span>)</b></span></td>
                                                    <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS on Approved Leave (<span>""" + str(
                    total_leave_fos) + """<span>)</b></span></td>
                                                    <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS@LOP(No-Swipe) (<span>""" + str(
                    total_absent_fos) + """<span>)</b></span></td>

                                                    <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS@LOP(Swipe Done But 0-M) (<span>""" + str(
                    fos_lop_0m) + """<span>)</b></span></td>
                                                  </tr>
                                                  <tr style="width:100%">
                                                     <td style="width:20%"><b>0 Meeting</b></td>
                                                     <td class="text-left" style="width:20%">: <span>""" + str(cn5) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(lcn5) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(acn5) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(fos_lop_0m) + """</span></td>
                                                  </tr>
                                                  <tr style="width:100%">
                                                     <td style="width:20%"><b>1 Meeting</b></td>
                                                     <td class="text-left" style="width:20%">: <span>""" + str(cn1) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(lcn1) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(acn1) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                  </tr>
                                                  <tr style="width:100%">
                                                     <td style="width:20%"><b>2 Meeting</b></td>
                                                     <td class="text-left" style="width:20%">: <span>""" + str(cn2) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(lcn2) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(acn2) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                  </tr>
                                              <tr style="width:100%">
                                                     <td style="width:20%"><b>3 Meeting</b></td>
                                                     <td class="text-left" style="width:20%">: <span>""" + str(cn3) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(lcn3) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(acn3) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                  </tr>
                                              <tr style="width:100%">
                                                     <td style="width:20%"><b>3+ Meeting</b></td>
                                                     <td class="text-left" style="width:20%">: <span>""" + str(cn4) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(lcn4) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(acn4) + """</span></td>
                                                     <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                  </tr>
                                              <tr style="width:100%">
                                                     <td style="width:20%"></td>
                                                     <td style="width:20%"></td>
                                                     <td style="width:20%"></td>
                                                     <td style="width:20%"></td>
                                                     <td style="width:20%"></td>
                                                  </tr>
                                            </table>

                        <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>

                                        <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(team_lead_heading) + """</span></b></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table style="width:100%">
                                             <tr style="width:100%">
                                                 <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/>: <b>Team Lead-Headcount (<span>""" + str(
                total_team_lead) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead on Approved Leave (<span>""" + str(
                total_leave_team_lead) + """<span>)</b></span></td>
                                                        <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead@LOP(No-Swipe) (<span>""" + str(
                total_absent_team_lead) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead@LOP(Swipe Done But 0-M) (<span>""" + str(
                    lead_lop_0m) + """<span>)</b></span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>0 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lop_0m) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>1 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>2 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3+ Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                              </tr>
                                        </table>

                            <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>

                                        <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(tele_heading) + """</span></b></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table style="width:100%">
                                             <tr style="width:100%">
                                                 <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/>: <b>Tele-Headcount (<span>""" + str(
                total_tele) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele on Approved Leave (<span>""" + str(
                total_leave_tele) + """<span>)</b></span></td>
                                                        <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele@LOP(No-Swipe) (<span>""" + str(
                total_absent_tele) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele@LOP(Swipe Done But 0-M) (<span>""" + str(
                    tele_lop_0m) + """<span>)</b></span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>0 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(tele_lop_0m) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>1 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>2 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3+ Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                              </tr>
                                        </table>
                                        <p> <i> PFA for details </i> </p>
                        <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>
                                        </body>

                                    <html>"""

                emailfrom = "erpnotification@nowfloats.com"
                toaddr = [bm_email, rm_email]
                msg['From'] = emailfrom
                msg['To'] = ", ".join(toaddr)
                msg['CC'] = ", ".join(cc)
                msg['Subject'] = mail_subject
                emailto = toaddr + cc

                part1 = MIMEText(html, 'html')
                msg.attach(part1)
                self.env.cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
                mail_server = self.env.cr.fetchone()
                smtp_user = mail_server[0]
                smtp_pass = mail_server[1]
                server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                server.login(smtp_user, smtp_pass)
                text = msg.as_string()
                try:
                    server.sendmail(emailfrom, emailto, text)
                except:
                    pass
                server.quit()
        return True

    @api.model
    def send_number_of_meeting_details_rm_wise(self):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        if not self.sync_biometric_data():
            return False
        new_cr.execute("SELECT * FROM update_swipe_leave_attendance()")

        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        if current_day != 'Monday':
            date = date - relativedelta(days=1)
            date = date.strftime('%d-%b-%Y')
            cc = ['nitin@nowfloats.com', 'satesh.kohli@nowfloats.com', 'salesaudit@nowfloats.com', 'richa.gaur@nowfloats.com']

            new_cr.execute("SELECT distinct branch.rm_id, "
                           "emp.work_email, "
                           "emp.name_related "
                           "FROM hr_branch branch INNER JOIN hr_employee emp ON branch.rm_id = emp.id")

            rm_ids = new_cr.fetchall()

            for rm in rm_ids:
                rm_id = rm[0]
                rm_email = rm[1]
                rm_name = rm[2]
                new_cr.execute("SELECT id "
                                "FROM hr_branch WHERE rm_id = {}".format(rm_id))
                branch_details = new_cr.fetchall()
                branch_ids = map(lambda x : x[0], branch_details)

                # FOS
                cn1 = self.get_fos_meeting_count(1, branch_ids)[0]
                cn2 = self.get_fos_meeting_count(2, branch_ids)[0]
                cn3 = self.get_fos_meeting_count(3, branch_ids)[0]
                cn4 = self.get_fos_meeting_count(4, branch_ids)[0]

                cn5 = self.get_fos_meeting_count(0, branch_ids)[0]

                total_fos = cn1 + cn2 + cn3 + cn4 + cn5

                acn1 = self.get_fos_lop_count(1, branch_ids, 'A')[0]
                acn2 = self.get_fos_lop_count(2, branch_ids, 'A')[0]
                acn3 = self.get_fos_lop_count(3, branch_ids, 'A')[0]
                acn4 = self.get_fos_lop_count(4, branch_ids, 'A')[0]

                acn5 = self.get_fos_lop_count(0, branch_ids, 'A')[0]

                total_absent_fos = acn1 + acn2 + acn3 + acn4 + acn5

                lcn1 = self.get_fos_lop_count(1, branch_ids, 'L')[0]
                lcn2 = self.get_fos_lop_count(2, branch_ids, 'L')[0]
                lcn3 = self.get_fos_lop_count(3, branch_ids, 'L')[0]
                lcn4 = self.get_fos_lop_count(4, branch_ids, 'L')[0]

                lcn5 = self.get_fos_lop_count(0, branch_ids, 'L')[0]

                total_leave_fos = lcn1 + lcn2 + lcn3 + lcn4 + lcn5

                fos_lop_0m = cn5 - acn5 - lcn5

                # Team Lead
                lead_cn1 = self.get_fos_meeting_count(1, branch_ids, 'team_lead')[0]
                lead_cn2 = self.get_fos_meeting_count(2, branch_ids, 'team_lead')[0]
                lead_cn3 = self.get_fos_meeting_count(3, branch_ids, 'team_lead')[0]
                lead_cn4 = self.get_fos_meeting_count(4, branch_ids, 'team_lead')[0]

                lead_cn5 = self.get_fos_meeting_count(0, branch_ids, 'team_lead')[0]

                total_team_lead = lead_cn1 + lead_cn2 + lead_cn3 + lead_cn4 + lead_cn5

                lead_acn1 = self.get_fos_lop_count(1, branch_ids, 'A', 'team_lead')[0]
                lead_acn2 = self.get_fos_lop_count(2, branch_ids, 'A', 'team_lead')[0]
                lead_acn3 = self.get_fos_lop_count(3, branch_ids, 'A', 'team_lead')[0]
                lead_acn4 = self.get_fos_lop_count(4, branch_ids, 'A', 'team_lead')[0]

                lead_acn5 = self.get_fos_lop_count(0, branch_ids, 'A', 'team_lead')[0]

                total_absent_team_lead = lead_acn1 + lead_acn2 + lead_acn3 + lead_acn4 + lead_acn5

                lead_lcn1 = self.get_fos_lop_count(1, branch_ids, 'L', 'team_lead')[0]
                lead_lcn2 = self.get_fos_lop_count(2, branch_ids, 'L', 'team_lead')[0]
                lead_lcn3 = self.get_fos_lop_count(3, branch_ids, 'L', 'team_lead')[0]
                lead_lcn4 = self.get_fos_lop_count(4, branch_ids, 'L', 'team_lead')[0]

                lead_lcn5 = self.get_fos_lop_count(0, branch_ids, 'L', 'team_lead')[0]

                total_leave_team_lead = lead_lcn1 + lead_lcn2 + lead_lcn3 + lead_lcn4 + lead_lcn5

                lead_lop_0m = lead_cn5 - lead_acn5 - lead_lcn5

                # Tele
                t_cn1 = self.get_tele_meeting_count(1, branch_ids)[0]
                t_cn2 = self.get_tele_meeting_count(2, branch_ids)[0]
                t_cn3 = self.get_tele_meeting_count(3, branch_ids)[0]
                t_cn4 = self.get_tele_meeting_count(4, branch_ids)[0]
                t_cn5 = self.get_tele_meeting_count(0, branch_ids)[0]

                total_tele = t_cn1 + t_cn2 + t_cn3 + t_cn4 + t_cn5

                t_acn1 = self.get_tele_lop_count(1, branch_ids, 'A')[0]
                t_acn2 = self.get_tele_lop_count(2, branch_ids, 'A')[0]
                t_acn3 = self.get_tele_lop_count(3, branch_ids, 'A')[0]
                t_acn4 = self.get_tele_lop_count(4, branch_ids, 'A')[0]
                t_acn5 = self.get_tele_lop_count(0, branch_ids, 'A')[0]

                total_absent_tele = t_acn1 + t_acn2 + t_acn3 + t_acn4 + t_acn5

                t_lcn1 = self.get_tele_lop_count(1, branch_ids, 'L')[0]
                t_lcn2 = self.get_tele_lop_count(2, branch_ids, 'L')[0]
                t_lcn3 = self.get_tele_lop_count(3, branch_ids, 'L')[0]
                t_lcn4 = self.get_tele_lop_count(4, branch_ids, 'L')[0]
                t_lcn5 = self.get_tele_lop_count(0, branch_ids, 'L')[0]

                total_leave_tele = t_lcn1 + t_lcn2 + t_lcn3 + t_lcn4 + t_lcn5

                tele_lop_0m = t_cn5 - t_acn5 - t_lcn5

                total_new_fos, total_new_team_lead, total_new_tele = self.get_total_number_of_new_fos_tele(branch_ids)

                #Meeting Count
                msg = MIMEMultipart()
                data = self.get_meeting_count_file(branch_ids)
                file_name = 'meeting_count_by_fos_for_{}.csv'.format(rm_name)

                data = base64.b64decode(data)
                part = MIMEApplication(
                    data,
                    Name=file_name
                )
                part['Content-Disposition'] = 'attachment; filename="{}"' \
                    .format(file_name)
                msg.attach(part)

                #Meeting Details
                data = self.get_meeting_details_file(branch_ids)
                file_name = 'meeting_details_by_fos_for_{}.csv'.format(rm_name)

                data = base64.b64decode(data)
                part = MIMEApplication(
                    data,
                    Name=file_name
                )
                part['Content-Disposition'] = 'attachment; filename="{}"' \
                    .format(file_name)
                msg.attach(part)

                # Tele Meeting Count
                data = self.get_tele_meeting_count_file(branch_ids)
                file_name = 'meeting_count_by_tele_for_{}.csv'.format(rm_name)

                data = base64.b64decode(data)
                part = MIMEApplication(
                    data,
                    Name=file_name
                )
                part['Content-Disposition'] = 'attachment; filename="{}"' \
                    .format(file_name)
                msg.attach(part)

                mail_subject = "FOS meeting count on %s || RM - %s" % (date, rm_name)

                heading = "FOS meeting count on %s || RM - %s" % (date, rm_name)

                tele_heading = "Tele meeting count on %s || RM - %s" % (date, rm_name)

                team_lead_heading = "Team Lead meeting count on %s || RM - %s" % (date, rm_name)

                description = "1. This report is showing employees having tenure greater than 10 days. <br/>" \
                              "2. Attached spreadsheet is containing complete data in details.<br/>" \
                              "3. Total number of FOS having tenure less than or equal to 10 days : {} <br/>" \
                              "4. Total number of Team Lead having tenure less than or equal to 10 days : {} <br/>" \
                              "5. Total number of Tele having tenure less than or equal to 10 days : {} <br/>" \
                    .format(total_new_fos, total_new_team_lead, total_new_tele)

                html = """<!DOCTYPE html>
                                             <html>

                                               <body>
                                                 <table style="width:100%">
                                                      <tr>
                                                         <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></left></td>
                                                      </tr>
                                                      <tr>
                                                         <td><left><span>""" + str(description) + """</span></left></td>
                                                      </tr>
                                                 </table>
                                                      <br/>
                                                 <table style="width:100%">
                                                     <tr style="width:100%">
                                                         <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                         <td class="text-left" style="width:20%"><font color= "red"/>: <b>FOS-Headcount (<span>""" + str(
                    total_fos) + """<span>)</b></span></td>
                                                         <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS on Approved Leave (<span>""" + str(
                    total_leave_fos) + """<span>)</b></span></td>
                                                    <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS@LOP(No-Swipe) (<span>""" + str(
                    total_absent_fos) + """<span>)</b></span></td>
                                                         <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS@LOP(Swipe Done But 0-M) (<span>""" + str(
                    fos_lop_0m) + """<span>)</b></span></td>
                                                      </tr>
                                                      <tr style="width:100%">
                                                         <td style="width:20%"><b>0 Meeting</b></td>
                                                         <td class="text-left" style="width:20%">: <span>""" + str(
                    cn5) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(lcn5) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(acn5) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(fos_lop_0m) + """</span></td>
                                                      </tr>
                                                      <tr style="width:100%">
                                                         <td style="width:20%"><b>1 Meeting</b></td>
                                                         <td class="text-left" style="width:20%">: <span>""" + str(
                    cn1) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(lcn1) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(acn1) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                      </tr>
                                                      <tr style="width:100%">
                                                         <td style="width:20%"><b>2 Meeting</b></td>
                                                         <td class="text-left" style="width:20%">: <span>""" + str(
                    cn2) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(lcn2) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(acn2) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                      </tr>
                                                  <tr style="width:100%">
                                                         <td style="width:20%"><b>3 Meeting</b></td>
                                                         <td class="text-left" style="width:20%">: <span>""" + str(
                    cn3) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(lcn3) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(acn3) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                      </tr>
                                                  <tr style="width:100%">
                                                         <td style="width:20%"><b>3+ Meeting</b></td>
                                                         <td class="text-left" style="width:20%">: <span>""" + str(
                    cn4) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(lcn4) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(acn4) + """</span></td>
                                                         <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                                      </tr>
                                                  <tr style="width:100%">
                                                         <td style="width:20%"></td>
                                                         <td style="width:20%"></td>
                                                         <td style="width:20%"></td>
                                                         <td style="width:20%"></td>
                                                         <td style="width:20%"></td>
                                                      </tr>
                                                </table>

                     <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>

                                        <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(team_lead_heading) + """</span></b></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table style="width:100%">
                                             <tr style="width:100%">
                                                 <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/>: <b>Team Lead-Headcount (<span>""" + str(
                total_team_lead) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead on Approved Leave (<span>""" + str(
                total_leave_team_lead) + """<span>)</b></span></td>
                                                        <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead@LOP(No-Swipe) (<span>""" + str(
                total_absent_team_lead) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead@LOP(Swipe Done But 0-M) (<span>""" + str(
                    lead_lop_0m) + """<span>)</b></span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>0 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lop_0m) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>1 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>2 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3+ Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                              </tr>
                                        </table>

                     <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>

                                        <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(tele_heading) + """</span></b></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table style="width:100%">
                                             <tr style="width:100%">
                                                 <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/>: <b>Tele-Headcount (<span>""" + str(
                total_tele) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele on Approved Leave (<span>""" + str(
                total_leave_tele) + """<span>)</b></span></td>
                                                        <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele@LOP(No-Swipe) (<span>""" + str(
                total_absent_tele) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele@LOP(Swipe Done But 0-M) (<span>""" + str(
                    tele_lop_0m) + """<span>)</b></span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>0 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(tele_lop_0m) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>1 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>2 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3+ Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                              </tr>
                                        </table>
                                        <p> <i> PFA for details </i> </p>
                        <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>
                                            </body>

                                        <html>"""

                emailfrom = "erpnotification@nowfloats.com"
                toaddr = [rm_email]
                msg['From'] = emailfrom
                msg['To'] = ", ".join(toaddr)
                msg['CC'] = ", ".join(cc)
                msg['Subject'] = mail_subject
                emailto = toaddr + cc

                part1 = MIMEText(html, 'html')
                msg.attach(part1)
                self.env.cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
                mail_server = self.env.cr.fetchone()
                smtp_user = mail_server[0]
                smtp_pass = mail_server[1]
                server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                server.login(smtp_user, smtp_pass)
                text = msg.as_string()
                try:
                    server.sendmail(emailfrom, emailto, text)
                except:
                    pass
                server.quit()
        return True




    #==================Meeting Count to FOS India==========================================

    @api.model
    def get_tele_india_lop_count(self, number, attendance_status):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND res.user_id NOT IN (SELECT sp_id FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) " \
                .format(Tele_Desig, attendance_status)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(Tele_Desig, attendance_status, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(Tele_Desig, attendance_status)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp

    @api.model
    def get_tele_india_meeting_count(self, number):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND res.user_id NOT IN (SELECT sp_id FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)" \
                .format(Tele_Desig)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(Tele_Desig, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(sp_id) AS cn " \
                      "FROM crm_tele_meeting_view " \
                      "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND sp_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 ) GROUP BY sp_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(Tele_Desig)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp




    @api.model
    def get_fos_india_lop_count(self, number, attendance_status, type='FOS'):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        internal_desig = only_fos_desig
        if type == 'team_lead':
            internal_desig = team_lead_desig

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) " \
                .format(internal_desig, attendance_status)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(internal_desig, attendance_status, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND leave.static_attendance = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(internal_desig, attendance_status)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp

    @api.model
    def get_fos_india_meeting_count(self, number, type='FOS'):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        internal_desig = only_fos_desig
        if type == 'team_lead':
            internal_desig = team_lead_desig

        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10 " \
                      "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)" \
                .format(internal_desig)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(internal_desig, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) > 10) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(internal_desig)
        new_cr.execute(str_sql)
        temp = new_cr.fetchone()
        return temp

    @api.model
    def get_fos_india_meeting_count_file(self):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        fp = StringIO.StringIO()
        writer = csv.writer(fp)
        new_cr.execute("SELECT "
                   "cm.date::date AS date, "
                   "emp.name_related AS employee, "
                   "emp.work_email AS email, "
                   "COUNT(cm.id) AS Yesterday_meeting_count,"
                   "(SELECT count(id) FROM crm_phonecall "
                   "WHERE user_id = cm.user_id "
                       "AND date::date BETWEEN DATE_TRUNC('month', now() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                   "AND (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)  AS MTD_meeting_count, "
                   "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch,"
                   "emp.intrnal_desig AS emp_designation,"
                   "(SELECT static_attendance FROM nf_leave_swipe WHERE user_id = res.user_id "
                   "AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) AS swipe_status,"
                   "CASE WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'L' "
                        "THEN 'Legal Leaves' "
                        "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'A' "
                        "THEN 'LOP(No-Swipe)' "
                        "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'P' "
                        "THEN 'Present' "
                   "ELSE (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) "
                   "END AS final_attendance, "
                    "emp.join_date AS date_of_join,"
                       "(NOW() AT TIME ZONE 'UTC')::date - emp.join_date AS  tenure_in_days "
                   "FROM crm_phonecall cm LEFT JOIN resource_resource res ON cm.user_id = res.user_id "
                   "LEFT JOIN hr_employee emp ON emp.resource_id = res.id "
                   "WHERE cm.date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                   "AND res.active = True AND emp.intrnal_desig IN {} "
                   "GROUP BY cm.date::date, emp.name_related, emp.work_email, (SELECT name FROM hr_branch WHERE id = emp.branch_id), "
                   "emp.intrnal_desig, (SELECT static_attendance FROM nf_leave_swipe WHERE user_id = res.user_id "
                   "AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1), cm.user_id, emp.join_date, (NOW() AT TIME ZONE 'UTC')::date - emp.join_date  "
                   "ORDER BY emp.name_related".format(only_fos_desig + team_lead_desig))
        writer.writerow([i[0] for i in new_cr.description])
        temp1 = new_cr.fetchall()
        for val in temp1:
            writer.writerow(val)

        new_cr.execute("SELECT (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date AS date, "
                   "emp.name_related AS employee, "
                   "emp.work_email AS email, "
                   " 0 AS Yesterday_meeting_count, "
                   "(SELECT count(id) FROM crm_phonecall "
                   "WHERE user_id = res.user_id "
                       "AND date::date BETWEEN DATE_TRUNC('month', now() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                   "AND (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)  AS MTD_meeting_count, "
                   "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch,"
                   "emp.intrnal_desig AS emp_designation,"
                   "(SELECT static_attendance FROM nf_leave_swipe WHERE user_id = res.user_id "
                   "AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) AS swipe_status,"
                   "CASE WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'L' "
                       "THEN 'Legal Leaves' "
                       "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'A' "
                      "THEN 'LOP(No-Swipe)' "
                       "WHEN (SELECT static_attendance FROM nf_leave_swipe "
                              "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) = 'P' "
                      "THEN 'LOP(0-M)' "
                      "ELSE (SELECT static_attendance FROM nf_leave_swipe "
                            "WHERE user_id = res.user_id AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) "
                   "END AS final_attendance,"
                       "emp.join_date AS date_of_join,"
                       "(NOW() AT TIME ZONE 'UTC')::date - emp.join_date AS  tenure_in_days "
                   "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                   "WHERE res.active = True AND " \
                   "emp.intrnal_desig IN {} " \
                   "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                   "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)" \
                   .format(only_fos_desig + team_lead_desig))
        temp2 = new_cr.fetchall()
        for val in temp2:
            writer.writerow(val)

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    @api.model
    def get_fos_india_meeting_details_file(self):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        fp = StringIO.StringIO()
        writer = csv.writer(fp)

        new_cr.execute("SELECT * FROM crm_fos_meeting_view "
                       "WHERE date_of_meeting::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date AND sp_designation IN {}"
                       .format(only_fos_desig + team_lead_desig))

        writer.writerow([i[0] for i in new_cr.description])

        temp = new_cr.fetchall()
        for val in temp:
            try:
               val = map(lambda x: x.encode('utf-8') if x and type(x) is not int else x, val)
               writer.writerow(val)
            except:
                pass

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    def get_fos_india_total_number_of_new_fos_tele(self):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        new_cr.execute("SELECT COALESCE(count(emp.id),0) FROM "
                       "hr_employee emp "
                       "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                       "WHERE res.active = True AND emp.intrnal_desig IN {} "
                       "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) <= 10"
                       .format(only_fos_desig))
        total_new_fos = new_cr.fetchone()[0]

        new_cr.execute("SELECT COALESCE(count(emp.id),0) FROM "
                       "hr_employee emp "
                       "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                       "WHERE res.active = True AND emp.intrnal_desig IN {} "
                       "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) <= 10"
                       .format(team_lead_desig))
        total_new_team_lead = new_cr.fetchone()[0]

        new_cr.execute("SELECT COALESCE(count(emp.id),0) FROM "
                       "hr_employee emp "
                       "INNER JOIN resource_resource res ON emp.resource_id = res.id "
                       "WHERE res.active = True AND emp.intrnal_desig IN {} "
                       "AND ((NOW() AT TIME ZONE 'UTC')::date - emp.join_date) <= 10"
                       .format(Tele_Desig))
        total_new_tele = new_cr.fetchone()[0]

        return [total_new_fos, total_new_team_lead , total_new_tele]

    @api.model
    def get_tele_india_meeting_count_file(self):

        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        fp = StringIO.StringIO()
        writer = csv.writer(fp)

        new_cr.execute("SELECT leave.date, "
                       "emp.name_related, "
                       "emp.work_email,"
                       "(SELECT COALESCE(count(sp_id), 0)::integer FROM crm_tele_meeting_view WHERE sp_id = leave.user_id "
                       "AND date_of_meeting::date = leave.date) AS meeting_count,"
                       "emp.intrnal_desig AS internal_desig,"
                       "branch.name AS branch,"
                       "leave.swipe_status,"
                       "leave.attendance_status,"
                        "emp.join_date AS date_of_join,"
                       "(NOW() AT TIME ZONE 'UTC')::date - emp.join_date AS  tenure_in_days "
                       "FROM nf_leave_swipe leave "
                       "LEFT JOIN hr_employee emp ON leave.hr_emp_id = emp.id "
                       "LEFT JOIN resource_resource res ON emp.resource_id = res.id "
                       "LEFT JOIN hr_branch branch ON emp.branch_id = branch.id "
                       "WHERE leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                       "AND emp.intrnal_desig IN {} AND res.active = True"
                       .format(Tele_Desig))

        writer.writerow([i[0] for i in new_cr.description])

        temp = new_cr.fetchall()
        for val in temp:
            try:
                val = map(lambda x: x.encode('utf-8') if x and type(x) is not int else x, val)
                writer.writerow(val)
            except:
                pass

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    @api.model
    def send_number_of_fos_india_meeting_details(self):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()

        if not self.sync_biometric_data():
            return False
        new_cr.execute("SELECT * FROM update_swipe_leave_attendance()")

        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        if current_day != 'Monday':
            date = date - relativedelta(days=1)
            date = date.strftime('%d-%b-%Y')
            cc = ['mohit.katiyar@nowfloats.com']

            cn1 = self.get_fos_india_meeting_count(1)[0]
            cn2 = self.get_fos_india_meeting_count(2)[0]
            cn3 = self.get_fos_india_meeting_count(3)[0]
            cn4 = self.get_fos_india_meeting_count(4)[0]
            cn5 = self.get_fos_india_meeting_count(0)[0]

            total_fos = cn1 + cn2 + cn3 + cn4 + cn5

            acn1 = self.get_fos_india_lop_count(1, 'A')[0]
            acn2 = self.get_fos_india_lop_count(2, 'A')[0]
            acn3 = self.get_fos_india_lop_count(3, 'A')[0]
            acn4 = self.get_fos_india_lop_count(4, 'A')[0]
            acn5 = self.get_fos_india_lop_count(0, 'A')[0]

            total_absent_fos = acn1 + acn2 + acn3 + acn4 + acn5

            lcn1 = self.get_fos_india_lop_count(1, 'L')[0]
            lcn2 = self.get_fos_india_lop_count(2, 'L')[0]
            lcn3 = self.get_fos_india_lop_count(3, 'L')[0]
            lcn4 = self.get_fos_india_lop_count(4, 'L')[0]
            lcn5 = self.get_fos_india_lop_count(0, 'L')[0]

            total_leave_fos = lcn1 + lcn2 + lcn3 + lcn4 + lcn5

            fos_lop_0m = cn5 - acn5 - lcn5

            #Team Lead
            lead_cn1 = self.get_fos_india_meeting_count(1, 'team_lead')[0]
            lead_cn2 = self.get_fos_india_meeting_count(2, 'team_lead')[0]
            lead_cn3 = self.get_fos_india_meeting_count(3, 'team_lead')[0]
            lead_cn4 = self.get_fos_india_meeting_count(4, 'team_lead')[0]
            lead_cn5 = self.get_fos_india_meeting_count(0, 'team_lead')[0]

            total_team_lead = lead_cn1 + lead_cn2 + lead_cn3 + lead_cn4 + lead_cn5

            lead_acn1 = self.get_fos_india_lop_count(1, 'A', 'team_lead')[0]
            lead_acn2 = self.get_fos_india_lop_count(2, 'A', 'team_lead')[0]
            lead_acn3 = self.get_fos_india_lop_count(3, 'A', 'team_lead')[0]
            lead_acn4 = self.get_fos_india_lop_count(4, 'A', 'team_lead')[0]
            lead_acn5 = self.get_fos_india_lop_count(0, 'A', 'team_lead')[0]

            total_absent_team_lead = lead_acn1 + lead_acn2 + lead_acn3 + lead_acn4 + lead_acn5

            lead_lcn1 = self.get_fos_india_lop_count(1, 'L', 'team_lead')[0]
            lead_lcn2 = self.get_fos_india_lop_count(2, 'L', 'team_lead')[0]
            lead_lcn3 = self.get_fos_india_lop_count(3, 'L', 'team_lead')[0]
            lead_lcn4 = self.get_fos_india_lop_count(4, 'L', 'team_lead')[0]
            lead_lcn5 = self.get_fos_india_lop_count(0, 'L', 'team_lead')[0]

            total_leave_team_lead = lead_lcn1 + lead_lcn2 + lead_lcn3 + lead_lcn4 + lead_lcn5

            lead_lop_0m = lead_cn5 - lead_acn5 - lead_lcn5

            #Tele
            t_cn1 = self.get_tele_india_meeting_count(1)[0]
            t_cn2 = self.get_tele_india_meeting_count(2)[0]
            t_cn3 = self.get_tele_india_meeting_count(3)[0]
            t_cn4 = self.get_tele_india_meeting_count(4)[0]
            t_cn5 = self.get_tele_india_meeting_count(0)[0]

            total_tele = t_cn1 + t_cn2 + t_cn3 + t_cn4 + t_cn5

            t_acn1 = self.get_tele_india_lop_count(1, 'A')[0]
            t_acn2 = self.get_tele_india_lop_count(2, 'A')[0]
            t_acn3 = self.get_tele_india_lop_count(3, 'A')[0]
            t_acn4 = self.get_tele_india_lop_count(4, 'A')[0]
            t_acn5 = self.get_tele_india_lop_count(0, 'A')[0]

            total_absent_tele = t_acn1 + t_acn2 + t_acn3 + t_acn4 + t_acn5

            t_lcn1 = self.get_tele_india_lop_count(1, 'L')[0]
            t_lcn2 = self.get_tele_india_lop_count(2, 'L')[0]
            t_lcn3 = self.get_tele_india_lop_count(3, 'L')[0]
            t_lcn4 = self.get_tele_india_lop_count(4, 'L')[0]
            t_lcn5 = self.get_tele_india_lop_count(0, 'L')[0]

            total_leave_tele = t_lcn1 + t_lcn2 + t_lcn3 + t_lcn4 + t_lcn5

            tele_lop_0m = t_cn5 - t_acn5 - t_lcn5

            total_new_fos, total_new_team_lead, total_new_tele = self.get_fos_india_total_number_of_new_fos_tele()

            # Meeting Count
            msg = MIMEMultipart()
            data = self.get_fos_india_meeting_count_file()
            file_name = 'fos_india_meeting_count_by_fos.csv'

            data = base64.b64decode(data)
            part = MIMEApplication(
                data,
                Name=file_name
            )
            part['Content-Disposition'] = 'attachment; filename="{}"' \
                .format(file_name)
            msg.attach(part)

            #Meeting Details
            data = self.get_fos_india_meeting_details_file()
            file_name = 'fos_india_meeting_details_by_fos.csv'

            data = base64.b64decode(data)
            part = MIMEApplication(
                data,
                Name=file_name
            )
            part['Content-Disposition'] = 'attachment; filename="{}"' \
                .format(file_name)
            msg.attach(part)

            # Tele Meeting Count
            data = self.get_tele_india_meeting_count_file()
            file_name = 'tele_india_meeting_count.csv'

            data = base64.b64decode(data)
            part = MIMEApplication(
                data,
                Name=file_name
            )
            part['Content-Disposition'] = 'attachment; filename="{}"' \
                .format(file_name)
            msg.attach(part)

            mail_subject = "FOS-India Meeting Count On %s" % date

            heading = "FOS-India Meeting count on %s" % date

            tele_heading = "Tele-India Meeting count on %s" % date

            team_lead_heading = "Team Lead-India Meeting count on %s" % date

            description = "1. This report is showing employees having tenure greater than 10 days. <br/>" \
                          "2. Attached spreadsheet is containing complete data in details.<br/>" \
                          "3. Total number of FOS having tenure less than or equal to 10 days : {} <br/>" \
                          "4. Total number of Team Lead having tenure less than or equal to 10 days : {} <br/>" \
                          "5. Total number of Tele having tenure less than or equal to 10 days : {} <br/>" \
                .format(total_new_fos, total_new_team_lead, total_new_tele)

            html = """<!DOCTYPE html>
                                     <html>

                                       <body>
                                         <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></left></td>
                                              </tr>
                                              <tr>
                                                 <td><left><span>""" + str(description) + """</span></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table style="width:100%">
                                             <tr style="width:100%">
                                                 <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/>: <b>FOS-Headcount (<span>""" + str(
                total_fos) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS on Approved Leave (<span>""" + str(
                total_leave_fos) + """<span>)</b></span></td>
                                                        <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS@LOP(No-Swipe) (<span>""" + str(
                total_absent_fos) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS@LOP(Swipe Done But 0-M) (<span>""" + str(
                    fos_lop_0m) + """<span>)</b></span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>0 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(cn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lcn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(acn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(fos_lop_0m) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>1 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(cn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lcn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(acn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>2 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(cn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lcn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(acn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(cn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lcn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(acn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3+ Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(cn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lcn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(acn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                              </tr>
                                        </table>

                                        <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>

                                        <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(team_lead_heading) + """</span></b></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table style="width:100%">
                                             <tr style="width:100%">
                                                 <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/>: <b>Team Lead-Headcount (<span>""" + str(
                total_team_lead) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead on Approved Leave (<span>""" + str(
                total_leave_team_lead) + """<span>)</b></span></td>
                                                        <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead@LOP(No-Swipe) (<span>""" + str(
                total_absent_team_lead) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Team Lead@LOP(Swipe Done But 0-M) (<span>""" + str(
                    lead_lop_0m) + """<span>)</b></span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>0 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lop_0m) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>1 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>2 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3+ Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(lead_cn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_lcn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(lead_acn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                              </tr>
                                        </table>

                                       <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>

                                        <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(tele_heading) + """</span></b></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         <table style="width:100%">
                                             <tr style="width:100%">
                                                 <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/>: <b>Tele-Headcount (<span>""" + str(
                total_tele) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele on Approved Leave (<span>""" + str(
                total_leave_tele) + """<span>)</b></span></td>
                                                        <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele@LOP(No-Swipe) (<span>""" + str(
                total_absent_tele) + """<span>)</b></span></td>
                                                 <td class="text-left" style="width:20%"><font color= "red"/> <b>Tele@LOP(Swipe Done But 0-M) (<span>""" + str(
                    tele_lop_0m) + """<span>)</b></span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>0 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn5) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(tele_lop_0m) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>1 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn1) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                              <tr style="width:100%">
                                                 <td style="width:20%"><b>2 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn2) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3 Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn3) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"><b>3+ Meeting</b></td>
                                                 <td class="text-left" style="width:20%">: <span>""" + str(t_cn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_lcn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(t_acn4) + """</span></td>
                                                 <td class="text-left" style="width:20%"> <span>""" + str(0) + """</span></td>
                                              </tr>
                                          <tr style="width:100%">
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                                 <td style="width:20%"></td>
                                              </tr>
                                        </table>
                                        <p> <i> PFA for details </i> </p>

                                       <p>----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------</p>

                                    </body>

                                <html>"""

            emailfrom = "erpnotification@nowfloats.com"
            toaddr = ['nitin@nowfloats.com', 'salesaudit@nowfloats.com', 'satesh.kohli@nowfloats.com',
                      'richa.gaur@nowfloats.com', 'neha.shrikhande@nowfloats.com', 'anurupa.singh@nowfloats.com', 'madhujaya.das@nowfloats.com']
            msg['From'] = emailfrom
            msg['To'] = ", ".join(toaddr)
            msg['CC'] = ", ".join(cc)
            msg['Subject'] = mail_subject
            emailto = toaddr + cc

            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            new_cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
            mail_server = new_cr.fetchone()
            smtp_user = mail_server[0]
            smtp_pass = mail_server[1]
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            try:
                server.sendmail(emailfrom, emailto, text)
            except:
                pass
            server.quit()
        return True

    @api.model
    def get_last_date_mib_done_orders_file(self):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()
        fp = StringIO.StringIO()
        writer = csv.writer(fp)

        new_cr.execute("SELECT * FROM nf_mib_done_orders_view")
        writer.writerow([i[0] for i in new_cr.description])
        temp1 = new_cr.fetchall()
        for val in temp1:
            writer.writerow(val)

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    @api.model
    def send_last_date_mib_done_orders(self):

        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        #if current_day != 'Monday':
        date = date - relativedelta(days=1)
        date = date.strftime('%d-%b-%Y')
        cc = ['nitin@nowfloats.com', 'satesh.kohli@nowfloats.com', 'rajeev.goyal@nowfloats.com',
                  'richa.gaur@nowfloats.com', 'neha.shrikhande@nowfloats.com', 'findesk@nowfloats.com','mapping@nowfloats.com','mohit.katiyar@nowfloats.com']

        # MIB Done Orders
        msg = MIMEMultipart()
        data = self.get_last_date_mib_done_orders_file()
        file_name = "Mib_done_orders_on_'{}'.csv".format(date)

        data = base64.b64decode(data)
        part = MIMEApplication(
            data,
            Name=file_name
        )
        part['Content-Disposition'] = 'attachment; filename="{}"' \
            .format(file_name)
        msg.attach(part)

        mail_subject = "MIB done orders on %s" % date

        description = "PFA"

        html = """<!DOCTYPE html>
                                     <html>

                                       <body>
                                         <table style="width:100%">
                                              <tr>
                                                 <td style="color:#4E0879"><left><b><span>""" + str(description) + """</span></b></left></td>
                                              </tr>
                                         </table>
                                              <br/>
                                         
                                    </body>

                                <html>"""

        emailfrom = "erpnotification@nowfloats.com"
        toaddr = ['narmeta.sreekanth@nowfloats.com']
        msg['From'] = emailfrom
        msg['To'] = ", ".join(toaddr)
        msg['CC'] = ", ".join(cc)
        msg['Subject'] = mail_subject
        emailto = toaddr + cc

        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        self.env.cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
        mail_server =  self.env.cr.fetchone()
        smtp_user = mail_server[0]
        smtp_pass = mail_server[1]
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_pass)
        text = msg.as_string()
        try:
            server.sendmail(emailfrom, emailto, text)
        except:
            pass
        server.quit()
        return True

    @api.model
    def get_mtd_orders_file(self):
        new_cn = psycopg2.connect(
            "dbname='NowFloatsV10' user='nferp10' password='NFerpV10!.' host='wf-erp01-wr.withfloats.com'")
        new_cr = new_cn.cursor()
        fp = StringIO.StringIO()
        writer = csv.writer(fp)

        new_cr.execute("SELECT * FROM nf_mtd_orders_view")
        writer.writerow([i[0] for i in new_cr.description])
        temp1 = new_cr.fetchall()
        for val in temp1:
            writer.writerow(val)

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    @api.model
    def send_mtd_nc_ec_orders(self):

        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        #if current_day != 'Monday':
        date = date - relativedelta(days=1)
        date = date.strftime('%d-%b-%Y')
        cc = ['mohit.katiyar@nowfloats.com']

        # MIB Done Orders
        msg = MIMEMultipart()
        data = self.get_mtd_orders_file()
        file_name = "mtd_orders_date'{}'.csv".format(date)

        data = base64.b64decode(data)
        part = MIMEApplication(
            data,
            Name=file_name
        )
        part['Content-Disposition'] = 'attachment; filename="{}"' \
            .format(file_name)
        msg.attach(part)

        mail_subject = "MTD NC-EC Orders Count %s" % date

        description = "PFA"

        html = """<!DOCTYPE html>
                                         <html>

                                           <body>
                                             <table style="width:100%">
                                                  <tr>
                                                     <td style="color:#4E0879"><left><b><span>""" + str(
            description) + """</span></b></left></td>
                                                  </tr>
                                             </table>
                                                  <br/>

                                        </body>

                                    <html>"""

        emailfrom = "erpnotification@nowfloats.com"
        toaddr = ['salesaudit@nowfloats.com', 'nitin@nowfloats.com', 'rajeev.goyal@nowfloats.com', 'richa.gaur@nowfloats.com', 'satesh.kohli@nowfloats.com']
        msg['From'] = emailfrom
        msg['To'] = ", ".join(toaddr)
        msg['CC'] = ", ".join(cc)
        msg['Subject'] = mail_subject
        emailto = toaddr + cc

        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        self.env.cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
        mail_server = self.env.cr.fetchone()
        smtp_user = mail_server[0]
        smtp_pass = mail_server[1]
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_pass)
        text = msg.as_string()
        try:
            server.sendmail(emailfrom, emailto, text)
        except:
            pass
        server.quit()
        return True
    
    
