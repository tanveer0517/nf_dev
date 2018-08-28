from odoo import models, fields, api, _
from openerp.osv import osv
import pymssql
from datetime import datetime,date,timedelta
import base64, openpyxl
from tempfile import TemporaryFile
from odoo import exceptions
from StringIO import StringIO
import csv

class nf_meeting_swipe(models.Model):
	_name = 'nf.meeting.swipe'

        employee_id = fields.Char('Employee ID')
    	emp_db_id = fields.Integer('Employee DB ID')
    	date = fields.Date('Date')
    	user_id = fields.Many2one('res.users','User ID')
    	no_of_meeting = fields.Integer('No. of Meeting')
    	meeting_status = fields.Char('Meeting Status')
    	swipe_status = fields.Char('Swipe Status')
    	status = fields.Char('Status')

class nf_bm_attendance(models.Model):
	_name = 'nf.bm.attendance'

    	employee_id = fields.Char('Employee ID')
    	emp_db_id = fields.Integer('Employee DB ID')
    	date = fields.Date('Date')
    	user_id = fields.Many2one('res.users','User ID')
    	dincharya_time = fields.Datetime('Dincharya Timing')
    	dincharya_status = fields.Char('Meeting Status')
    	swipe_status = fields.Char('Swipe Status')
    	status = fields.Char('Status')

class nf_leave_swipe(models.Model):
	_name = 'nf.leave.swipe'
    	_rec_name = 'employee_id'
	_order = 'date desc'

        employee_id = fields.Char('Employee ID')
    	emp_db_id = fields.Integer('Employee')
    	date = fields.Date('Date')
    	user_id = fields.Many2one('res.users','Employee')
        swipe_status = fields.Char('Swipe Status')
    	attendance_status = fields.Char('Attendance Status')
        branch_id = fields.Many2one('hr.branch', 'Branch')
        division_id = fields.Many2one('hr.department', 'Division')
        internal_desig = fields.Char('Internal Designation')
	hr_emp_id = fields.Many2one('hr.employee', 'Employee')
	number_of_meeting = fields.Integer('Number of Meeting')
	designation_type = fields.Selection([('FOS', 'FOS'), ('Tele', 'Tele'), ('BM', 'BM'), ('Other', 'Other')], string='Type')
	meeting_reason = fields.Text('Reason')
	updated_on = fields.Datetime('Updated On')
	eligible_to_update = fields.Boolean('Eligible')
    	static_attendance = fields.Char('Static Attendance Status')


class nf_meeting_reason(models.TransientModel):
    _name = 'nf.meeting.reason'

    comment = fields.Text('Comment')

    @api.multi
    def submit_comment(self):
	active_id = self.env.context.get('active_id', False)
	if active_id:
	   reason = self.comment.replace("'", "''")
           self.env.cr.execute("UPDATE nf_leave_swipe SET meeting_reason = '{}', updated_on = NOW() AT TIME ZONE 'UTC' WHERE id = {}".format(reason, active_id))
        return True

class nf_biometric(models.Model):
    _name='nf.biometric'

    _order = 'attendance_date DESC,branch,name'

    name = fields.Char('Name')
    emp_id = fields.Char('Employee ID')
    bmtc_emp_id = fields.Char('Biometric Employee ID')
    attendance_date = fields.Datetime('Biometric Attendance Date')
    index_no = fields.Integer('Primary Index')
    io_type = fields.Integer('In/Out(0/1)')
    device_name = fields.Char('Device Name')
    branch = fields.Char('Branch')
    erp_att_date = fields.Datetime('ERP Attendance Date')

    @api.model
    def sync_biometric_data(self):
	cr = self.env.cr
	cr.execute("SELECT COALESCE(MAX(index_no),0) AS mx_index FROM nf_biometric")
	mx_index = cr.fetchone()[0]

	conn = pymssql.connect(host='14.142.119.126:1433\SQLEXPRESS', user='sa', password='matrix_1', database='COSEC')
	cursor = conn.cursor()
	str_sql = "SELECT " \
			  "IndexNo," \
			  "EntryExitType," \
			  "DeviceName," \
			  "EventDateTime," \
			  "REPLACE(UserId,'_',' - ') AS emp_id," \
			  "UserName," \
			  "UserId," \
			  "BrcName," \
			  "DATEADD(MINUTE, -330, EventDateTime)" \
			  "FROM Mx_VEW_UserAttendanceEvents " \
			  "WHERE CAST(EventDateTime AS DATE) >= '2017-04-01' " \
			  "AND IndexNo > {}" \
			  "ORDER BY EventDateTime DESC,BrcName,UserName" \
		.format(mx_index)
	cursor.execute(str_sql)
	swipe_data = cursor.fetchall()

	cr.executemany("INSERT " \
				   "INTO " \
				   "nf_biometric " \
				   "(index_no,io_type,device_name,attendance_date, emp_id, name, bmtc_emp_id, branch, erp_att_date, create_date) " \
				   "VALUES " \
				   "(%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)"
				   , swipe_data)

	return True

    @api.model
    def sync_biometric_update_ms_attendance(self):
        cr = self.env.cr
        cr.execute("SELECT COALESCE(MAX(index_no),0) AS mx_index FROM nf_biometric")
        mx_index = cr.fetchone()[0]

        conn = pymssql.connect(host='14.142.119.126:1433\SQLEXPRESS', user='sa', password='matrix_1', database='COSEC')
        cursor = conn.cursor()
        str_sql = "SELECT " \
                  "IndexNo," \
                  "EntryExitType," \
                  "DeviceName," \
                  "EventDateTime," \
                  "REPLACE(UserId,'_',' - ') AS emp_id," \
                  "UserName," \
                  "UserId," \
                  "BrcName," \
                  "DATEADD(MINUTE, -330, EventDateTime)" \
                  "FROM Mx_VEW_UserAttendanceEvents " \
                  "WHERE CAST(EventDateTime AS DATE) >= '2017-04-01' " \
                  "AND IndexNo > {}" \
                  "ORDER BY EventDateTime DESC,BrcName,UserName"\
            .format(mx_index)
        cursor.execute(str_sql)
        swipe_data = cursor.fetchall()

        cr.executemany("INSERT " \
                 "INTO " \
                 "nf_biometric " \
                 "(index_no,io_type,device_name,attendance_date, emp_id, name, bmtc_emp_id, branch, erp_att_date, create_date) " \
                 "VALUES " \
                 "(%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)"
                       ,swipe_data)
        cr.execute("SELECT * FROM update_ms_attendance()")
        cr.execute("SELECT * FROM update_bm_attendance()")
        return True

class nf_jibble_attendance(models.Model):
    _name = 'nf.jibble.attendance'
    _description = 'NF Jibble Attendance'

    name = fields.Char('Name')
    attendance_date = fields.Date('Date',default=date.today())
    attendance_line = fields.One2many('nf.jibble.attendance.line','attendance_id','Attendance Line')
    attendance_file = fields.Binary('Timesheet (.XLSX)')
    filename = fields.Char('Filename')
    synced = fields.Boolean('Synced')

    @api.onchange('attendance_date')
    def onchange_date(self):
      if self.attendance_date:
        attendance_date=datetime.strptime(self.attendance_date,'%Y-%m-%d').strftime('%d-%m-%Y')
        self.name = 'Attendance On '+attendance_date

    @api.model
    def create(self,vals):
      attendance_date=vals.get('attendance_date',False)
      if attendance_date:
        attendance_date=datetime.strptime(attendance_date,'%Y-%m-%d').strftime('%d-%m-%Y')
        vals.update({'name': 'Attendance On '+attendance_date})
      result = super(nf_jibble_attendance, self).create(vals)
      return result

    @api.multi
    def import_attendance(self):
        if self.synced:
            return True
        if not self.attendance_file:
            raise exceptions.ValidationError(_('Please insert file'))

         #CSV
#        csv_data = base64.b64decode(self.attendance_file)
 #       csv_data = csv_data.encode('utf-8')
  #      csv_iterator = csv.reader(
   #         StringIO(csv_data), delimiter=",", quotechar=" ")

#        for row in csv_iterator:
 #           print"=============row=============", row

        values = []
        file = self.attendance_file.decode('base64')
        excel_fileobj = TemporaryFile('wb+')
        excel_fileobj.write(file)
        excel_fileobj.seek(0)

        workbook = openpyxl.load_workbook(excel_fileobj, True)
        # Get the first sheet of excel file
        sheet = workbook[workbook.get_sheet_names()[0]]

        # Iteration on each rows in excel
        i = 0
        for row in sheet:
            i = i + 1
            if i <= 6:
                continue

            v1 = row[0].value
            if not v1:
                break
            try:
                emp_db_id = int(v1.split('/')[0])
            except:
                raise exceptions.ValidationError(_('Employee ID not updated! (ID/Name)'))
            # Get value
            v2 = row[1].value
            sts = 'A' if v2 == '0:00' else 'P'

            values.append((emp_db_id, sts))

        uid = self.env.uid
        self.env.cr.executemany("INSERT INTO nf_jibble_attendance_line "
                            "(employee_id, status, attendance_id, create_date, write_date, create_uid, write_uid) "
                            "VALUES "
                            "(%s, %s, {}, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', {}, {})".format(self.id, uid, uid),
                            values)
        self.synced = True
        return True

class nf_jibble_attendance_line(models.Model):
    _name = 'nf.jibble.attendance.line'
    _description = 'NF Jibble Attendance Line'

    employee_id = fields.Many2one('hr.employee','Employee')
    status = fields.Char('Status', default='P')
    attendance_id = fields.Many2one('nf.jibble.attendance','Attendance ID')
