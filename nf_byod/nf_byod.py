from openerp.osv import osv
from odoo import api, fields, models, _, SUPERUSER_ID
import datetime
import calendar
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime

class nf_byod(models.Model):
    _name = 'nf.byod'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    def get_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)],limit = 1)
    
    @api.one
    @api.depends('employee_id')
    def _get_emp_user(self,context=None):
        env = api.Environment(self.env.cr, SUPERUSER_ID, {})
        for record in self:
           byod = env['nf.byod'].browse(record.id)
           if byod.employee_id:
                record.emp_user_id = byod.employee_id.user_id and byod.employee_id.user_id.id or False
    
    employee_id = fields.Many2one('hr.employee','Employee',track_visibility='onchange',default=get_employee)
    email = fields.Char(related='employee_id.work_email',string='Email')
    name = fields.Char(related = 'employee_id.employee_no',string='Name')
    byod_type = fields.Selection([('Own Device','Own Device'),('Device on EMI','Device on EMI'),('Provided By Company','Provided By Company')],'Byod Type',track_visibility='onchange')
    device = fields.Selection([('Laptop','Laptop'),('IPad','IPad')],'Device')
    state = fields.Selection([('Draft','Draft'),('Genuine','Genuine'),('Rejected','Rejected')],'Status',track_visibility='onchange',default='Draft')
    remark = fields.Text('Remark')
    date = fields.Date('Date',track_visibility='onchange',default=fields.Date.context_today)
    user_id = fields.Many2one('res.users','User',track_visibility='onchange',default=lambda self: self.env.user)
    mobile_phone = fields.Char(related = 'employee_id.mobile_phone',string='Work Mobile')
    #depart = fields.Many2one('employee_id.department_id',string='NF Department')
    depart = fields.Char(string='NF Department')

    sale_channel = fields.Char(string='Division')

    #nf_sale_channel = fields.Many2one('employee_id.sub_dep',string='Division')
    city = fields.Char(string='City')
    model = fields.Char('Model')
    serial_no = fields.Char('Serial No.',track_visibility='onchange')
    mac_address = fields.Char('Mac Address')
    sys_config = fields.Char('System Config',track_visibility='onchange')
    os = fields.Selection([('Windows','Windows'),('Linux/Ubuntu','Linux/Ubuntu'),('Mac','Mac'),('IOS','IOS')],string='OS',track_visibility='onchange')
    nf_soft = fields.Char('Software If Any',track_visibility='onchange')
    verified_date = fields.Date('Verified Date',track_visibility='onchange')
    next_verification_date = fields.Date('Next Verification Date',track_visibility='onchange')
    emp_user_id = fields.Many2one(compute = '_get_emp_user',string='Employee User',store=True)
    device_details = fields.Binary('Device Details')
    filename = fields.Char('File Name')
    active = fields.Boolean(related='employee_id.active',string='Active')
    job_id = fields.Many2one(related='employee_id.job_id',string='Job')
        
    _sql_constraints=[
                       ('unique_employee','UNIQUE(employee_id)','You already have done BYOD for corresponding employee')
                      ]

    @api.onchange('employee_id')
    def onchange_employee(self):
        for record in self:
            print "=========================", record.employee_id
            if record.employee_id:
                a = record.employee_id
                print "================branch=========", a
                self.emp_id = a.emp_id
                self.email = a.work_email
                self.mobile_phone = a.work_phone
                self.city = a.q_city_id.name
                self.sale_channel = a.sub_dep.parent_id.name+'/'+a.sub_dep.name
                self.depart = '['+a.cost_centr.code+']'+a.cost_centr.name

      # @api.onchange('employee_id')
      # def onchange_employee(self):
      #   self.env.cr.execute("select emp_id,work_email,work_phone,cost_centr,sub_dep from hr_employee where id = '"+str(record.employee_id.id)+"'")
      #   tmp = self.env.cr.fetchall()
      #   if tmp:
      #     record.emp_id = tmp[0][0]
      #     record.email = tmp[0][1]
      #     record.mobile_phone = tmp[0][2]
      #     record.nf_city=tmp[0][]
      #     record.depart = tmp[0][3]
      #     record.sale_channel= tmp[0][4]
      #    record.job_id = tmp[0][5]

    @api.onchange('device')
    def onchange_byod_device(self):
        for record in self:
            if record.device == 'IPad':
                record.os = 'IOS'    
    
    @api.multi
    def approved(self):
        if not self.remark or not self.sys_config or not self.serial_no:
            raise osv.except_osv(_('Alert!'), _('Please provide the remark/system config/serial no.'))
        date = fields.Date.context_today(self)
        date = datetime.strptime(date, "%Y-%m-%d")
        next_verification_date = date + relativedelta(months = 6)
        self.write({'state':'Genuine','verified_date':date,'next_verification_date':next_verification_date})
        return True
     
    @api.multi 
    def rejected(self):
        if not self.remark:
            raise osv.except_osv(_('Alert!'), _('Please provide the reason of reject in remark'))
        self.write({'state':'Rejected'})
        return True
     
    @api.multi
    def reset_to_draft(self):
        self.write({'state':'Draft'})
        return True
     
    @api.model
    def create(self, vals):
        res = super(nf_byod,self).create(vals)
        self.env.cr.execute("update nf_byod set date = now() at time zone 'utc' where id = '"+str(res.id)+"'")
        if 'employee_id' in vals and vals['employee_id']:
            self.env.cr.execute("update hr_employee set byod_id  = '"+str(res.id)+"' where id = '"+str(vals['employee_id'])+"'")
        return res
     
    @api.multi
    def write(self, vals):
        if 'employee_id' in vals and vals['employee_id']:
            self.env.cr.execute("update hr_employee set byod_id  = '"+str(self.id)+"' where id = '"+str(vals['employee_id'])+"'")
        res = super(nf_byod,self).write(vals)
        return res
    
class hr_employee(osv.osv):
    _inherit = 'hr.employee'
    
    byod_id = fields.Many2one('nf.byod','BYOD')
    byod_type = fields.Selection(related='byod_id.byod_type',string="Byod Type")
    byod_state = fields.Selection(related='byod_id.state',string="Status")
    byod_device = fields.Selection(related='byod_id.device',string="Device")
    
    
    