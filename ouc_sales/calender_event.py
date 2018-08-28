from odoo import fields,models,api, _,SUPERUSER_ID
import re
from openerp.exceptions import except_orm, Warning  
from datetime import datetime
from datetime import timedelta

class calendar_event(models.Model):
    _inherit = 'calendar.event'
    c_is_meeting_done = fields.Boolean(string='Checking Meeting status')
    c_meeting_type = fields.Selection([('new', 'New'), ('Follow up', 'Follow Up')], string='Meeting Type')
    c_contact_status = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Were you able to Meet the Concerned Person?')
    c_meeting_status = fields.Selection([('Interested', 'Interested'), ('Not Interested', 'Not Interested'),
                                       ('Follow up required', 'Follow Up Required')], 'Status after the Meeting')
    c_sale_order_id = fields.Many2one('sale.order', string='Quotation')
    c_follow_date = fields.Date(string='Follow Date')
    c_customer_count = fields.Char(string='Customer Count')
    c_fptag = fields.Many2one('ouc.fptag',string='FPTAG')
    c_demo_type = fields.Selection([('Demo', 'Demo'), ('Normal', 'Normal')], string='Demo/Normal Meeting')
    c_demo_status = fields.Boolean(string='Demo Meeting Status')
    c_meetingdate = fields.Datetime('MeetingDate',compute='compute_time',store=True)
    meeting_done = fields.Selection([('No','No'),('Yes','Yes')],'Meeting Done with Branch Manager?',default='No')
    
    @api.model
    def create(self, values):
        meeting = super(calendar_event, self).create(values)
        users = [1, 7976]
        opp_rec = meeting.opportunity_id or False
        if opp_rec:
            users.append(opp_rec.c_lead_creator_id and opp_rec.c_lead_creator_id.id or False)
            users.append(opp_rec.user_id and opp_rec.user_id.id or False)
            if self.env.uid not in users:
                raise Warning('Sorry, you cannot Log a Meeting for this lead. Only corresponding Sales Person can Log a Meeting.')
        self.update_created_junk_partner(meeting)                
        return meeting
    
    @api.multi
    def write(self, values):
        meeting = super(calendar_event, self).write(values)
        self.update_created_junk_partner(self)                
        return meeting
        
    def update_created_junk_partner(self, meeting):
        if not meeting.opportunity_id:
            return
        if meeting.opportunity_id.type != 'lead':
            return
        for partner in meeting.partner_ids:
            if partner == self.env.user.partner_id:
                continue
            if not partner.mobile:
                partner.sudo().write({'customer': False})

    @api.depends('start_datetime')
    def compute_time(self):
        for val in self:
            if val.start_datetime:
                time1 = datetime.strptime(val.start_datetime, "%Y-%m-%d %H:%M:%S")
                time_added = time1 + timedelta(hours=5, minutes=30)
                val.c_meetingdate = time_added


class CrmPhonecall(models.Model):
    _inherit = "crm.phonecall"
    _description = "Inheriting crm phonecall to add fields"

    _order = 'date desc, opportunity_id desc'

    c_demo_type = fields.Selection([('Demo', 'Demo'), ('Normal', 'Normal')], string='Demo/Normal Meeting')
    c_meeting_type = fields.Selection([('new', 'New'), ('Follow up', 'Follow Up')], string='Meeting Type')
    c_contact_status = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Were you able to Meet the Concerned Person?')
    c_meeting_status = fields.Selection([('Interested', 'Interested'), ('Not Interested', 'Not Interested'),
                                       ('Follow up required', 'Follow Up Required')], 'Status after the Meeting')
    c_customer_count = fields.Char(string="Customer Count")
    lc_id_rel = fields.Many2one('res.users',related='opportunity_id.c_lead_creator_id', string='Lead Creator')
    sp_id_rel = fields.Many2one('res.users', related='opportunity_id.user_id', string='Sales Person')
    meeting_done = fields.Selection([('No','No'),('Yes','Yes')],'Meeting Done with Branch Manager',default='No')
    bm_user_id = fields.Many2one('res.users','BM User')
    bm_empl_id = fields.Many2one('hr.employee','BM Employee')
    bm_comment = fields.Text('BM Comment')
    bm_update = fields.Selection([('Done','Done'),('Pending','Pending')],'BM Update',default='Pending')
    comment_date = fields.Datetime('Comment Date')
    otp = fields.Char('OTP')

    @api.multi
    def comment_update(self):
        for rec in self:
            wiz_id = self.env['bm.meeting.comment'].create({'meeting_id':rec.id})
            #opening wizard form
            return {
                'name':_("Add your Comment"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'bm.meeting.comment',
                'res_id': wiz_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                }


    def open_lead_opportunity(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "views": [[self.env.ref('ouc_sales.nf_lead_opp_form_view').id, "form"]],
            "domain": [],
            'res_id': self.opportunity_id and self.opportunity_id.id or False,
            "context": {},
            'view_mode':'form',
            'target': 'new',
            "name": "Lead/Opportunity",
            'flags': {'initial_mode': 'view'}
               }
