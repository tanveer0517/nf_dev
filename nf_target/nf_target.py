from odoo import models, fields, api, _
from openerp.osv import osv
from datetime import datetime
import time
from odoo.exceptions import UserError, ValidationError
from openerp import SUPERUSER_ID
from odoo import exceptions


get_fy = [(num, str(num) + '-' + str(num + 1)[2:]) for num in range(2012, (datetime.now().year)+5 )]

InternalDesig = [('Associate - FOS','Associate - FOS'),
                 ('Consultant - FOS','Consultant - FOS'),
                 ('Principal Consultant - FOS','Principal Consultant - FOS'),
                 ('Senior Consultant - FOS','Senior Consultant - FOS'),
                 ('Associate Product Specialist','Associate Product Specialist'),
                 ('Principal Product Specialist','Principal Product Specialist'),
                 ('Product Specialist','Product Specialist'),
                 ('Senior Product Specialist','Senior Product Specialist'),
                 ('Associate - Tele Sales','Associate - Tele Sales'),
                 ('Consultant - Tele Sales','Consultant - Tele Sales'),
                 ('Principal Consultant - Tele Sales','Principal Consultant - Tele Sales'),
                 ('Senior Consultant - Tele Sales','Senior Consultant - Tele Sales'),
                 ('Associate - Customer First','Associate Consultant - Customer First'),
                 ('Consultant - Customer First','Consultant - Customer First'),
                 ('Principal Consultant - Customer First','Principal Consultant - Customer First'),
                 ('Senior Consultant - Customer First','Senior Consultant - Customer First'),
                 ('Team Lead - Customer First','Team Lead - Customer First'),
                 ('Associate - Verticals','Associate Consultant - Verticals'),
                 ('Consultant - Verticals','Consultant - Verticals'),
                 ('Principal Consultant - Verticals','Principal Consultant - Verticals'),
                 ('Senior Consultant - Verticals','Senior Consultant - Verticals'),
                  ]

class nf_sale_target(models.Model):
    _name = 'nf.sale.target'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'nf_fy'

    def get_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.one
    @api.depends('employee_id')
    def _get_emp_user(self, context=None):
        env = api.Environment(self.env.cr, SUPERUSER_ID, {})
        for record in self:
            thd = env['nf.sale.target'].browse(record.id)
            if thd.employee_id:
                record.user_id = thd.employee_id.user_id and thd.employee_id.user_id.id or False

    @api.constrains('nf_fy','employee_id')
    def _unique_emp_fy(self):
        for record in self:
            target_ids = self.search([('nf_fy', '=', record.nf_fy), ('employee_id', '=', record.employee_id.id)])
	    if len(target_ids) > 1:
                raise exceptions.ValidationError(_('This Employee Target & Achievement already been created'))
        return True

    nf_fy = fields.Selection(get_fy,string='FY',track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee','Employee',default=get_employee,track_visibility='onchange')
    user_id = fields.Many2one(compute='_get_emp_user',string='Employee User',track_visibility='onchange',default=lambda self : self.env.user)
    doc  = fields.Boolean('Doc')
    suppress = fields.Boolean('Suppress',track_visibility='onchange')
    nf_sale_trgt_lines  = fields.One2many('nf.sale.target.line','nf_trgt_id','NF Sale Target Lines',on_delete="cascade")

    @api.onchange('nf_fy')
    def onchange_fy(self):
	nf_fy = self.nf_fy
        if nf_fy:
            date = str(nf_fy) + '04' + '01'
            self.env.cr.execute("select * from get_month('{}')".format(date))
            tmp = [(0,False,{'date':val,'nf_fy':nf_fy}) for val in self.env.cr.fetchone()]
            self.nf_sale_trgt_lines = tmp
    
    @api.model
    def create(self,vals):
        res = super(nf_sale_target,self).create(vals)
        if not res.user_id:
            raise osv.except_osv(_('Warning'), _('Relative user not defined for this user'))
        self.env.cr.execute("UPDATE nf_sale_target SET doc = True,suppress = False WHERE id = {}".format(res.id))
        self.env.cr.execute("UPDATE nf_sale_target_line SET employee_id = {},user_id = {} WHERE nf_trgt_id = {}".format(res.employee_id.id,res.user_id,res.id))
        return res

class nf_sale_target_line(models.Model):
    _name = 'nf.sale.target.line'

    date = fields.Date('Date')
    target = fields.Float('Target')
    monthly_thd = fields.Float('Monthly Threshold')
    crr_frwd_thd = fields.Float('Carry Forward')
    ytd = fields.Float('YTD')
    achievment = fields.Float('Achievement')
    nf_fy = fields.Selection(get_fy, string='FY')
    nf_trgt_id = fields.Many2one('nf.sale.target','Target')
    employee_id = fields.Many2one('hr.employee','Employee')
    user_id = fields.Many2one('res.users', 'User')
    suppress = fields.Boolean('Suppress')

class nf_thd_log(models.Model):
    _name = 'nf.thd.log'

    designation = fields.Selection(InternalDesig, string='Internal Designation')
    from_date = fields.Date('From Date')
    till_date = fields.Date('Till Date')
    monthly_thd = fields.Float('Monthly Threshold')



