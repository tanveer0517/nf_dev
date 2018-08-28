from odoo import models, fields, api, _
from openerp.osv import osv
from datetime import datetime
import time
from odoo.exceptions import UserError, ValidationError
from openerp import SUPERUSER_ID
from odoo import exceptions

class nf_helpdesk(models.Model):
    _inherit = 'helpdesk.ticket'

    tkt_number = fields.Char('Ticket No')
    tkt_deadline = fields.Date('Deadline')
    comments_ids = fields.One2many('nf.helpdesk.comments','ticket_id','Comments')
    deadline_readonly = fields.Boolean('Deadline Readonly')

    @api.model
    def default_get(self,fields):
        res=super(nf_helpdesk,self).default_get(fields)
        user=self.env['res.users'].browse(self.env.uid)
        res.update({'partner_id':user.partner_id.id})

        return res

    @api.onchange('team_id')
    def _onchange_team_id(self):
        if self.team_id:
            udpate_vals = self._onchange_team_get_values(self.team_id)
            self.user_id = udpate_vals['user_id']
            if not self.stage_id or self.stage_id not in self.team_id.stage_ids:
                self.stage_id = udpate_vals['stage_id']
            users = map(lambda x: x.id, self.team_id.member_ids)
            return {'domain':{'user_id':[('id','in',users)]}}

    @api.model
    def create(self, vals):
    	user_id = vals.get('user_id', False)
        code = self.env['ir.sequence'].next_by_code('helpdesk_sequence_no')
        if code:
            vals.update({'tkt_number':code})
        res = super(nf_helpdesk, self).create(vals)
        res.write({'user_id':user_id})
        temp_id = self.env['mail.template'].search([('name','=','New Ticket Request')])
        if temp_id:
            temp_id.send_mail(res.id)
            
        return res

    @api.multi
    def write(self, vals):
        if not self.deadline_readonly:
            if vals.get('tkt_deadline'):
                vals.update({'deadline_readonly': True})
        res = super(nf_helpdesk, self).write(vals)
        if self.stage_id.name == 'Solved':
            temp_id = self.env['mail.template'].search([('name','=','Solved Ticket Request')])
            if temp_id:
                temp_id.send_mail(self.id)

        elif self.stage_id.name == 'Cancelled':
            temp_id = self.env['mail.template'].search([('name','=','Ticket Cancelled')])
            if temp_id:
                temp_id.send_mail(self.id)

        if vals.get('user_id'):
            temp_id = self.env['mail.template'].search([('name','=','Ticket Assigned')])
            if temp_id:
                temp_id.send_mail(self.id)
            
        return res

class nf_helpdesk_comments(models.Model):
    _name = "nf.helpdesk.comments"
    _description = 'Helpdesk Comments'

    ticket_id = fields.Many2one('helpdesk.ticket','Ticket')
    comments = fields.Text('Follow-up Comment')
    comment_date = fields.Date('Comment Date')
    comment_by = fields.Many2one('res.users','Comment By')
    submit = fields.Boolean('Submit')

    @api.model
    def create(self,vals):
    	vals.update({'submit':True})
        rec=super(nf_helpdesk_comments,self).create(vals)
        rec.write({'comment_date':datetime.now().strftime('%Y-%m-%d'),'comment_by':self.env.uid,'submit':True})
        temp_id = self.env['mail.template'].search([('name','=','Ticket Comments')])
        if temp_id:
            temp_id.send_mail(rec.id)
        return rec

class nf_helpdesk_team(models.Model):
    _inherit = 'helpdesk.team'

    team_email = fields.Char('Email ID')

class nf_helpdesk_team(models.Model):
    _inherit = 'helpdesk.tag'

    team_id = fields.Many2one('helpdesk.team','Team')