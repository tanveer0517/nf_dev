from openerp import api, models, fields, _, SUPERUSER_ID
from openerp.exceptions import except_orm, Warning
import time
from odoo import exceptions
from odoo.exceptions import ValidationError
from datetime import datetime
import requests
import json
import base64
import datetime
import logging
import psycopg2
import threading
from email.utils import formataddr
from odoo import tools
from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval
import json,urllib,urllib2
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

_logger = logging.getLogger(__name__)


class ouc_meeting_wizard(models.TransientModel):
    _name = 'ouc.meeting.wizard'

    meeting_type = fields.Selection([('new', 'New'), ('Follow up', 'Follow Up')], string='Meeting Type', default='new')
    contact_status = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Were you able to Meet the Concerned Person?')
    meeting_status = fields.Selection([('Interested', 'Interested'), ('Not Interested', 'Not Interested'),
                                       ('Follow up required', 'Follow Up Required')], 'Status after the Meeting')
    meeting_description = fields.Text('Meeting description')
    c_follow_date = fields.Date(string='Follow Date')
    c_customer_count = fields.Char(string='Customer Count')
    c_fptag = fields.Many2one('ouc.fptag', string='FPTAG')
    c_demo_type = fields.Selection([('Demo', 'Demo Meeting'), ('Normal', 'Normal Meeting')],
                                   string='Demo/Normal Meeting')
    c_demo_status = fields.Boolean(string='Demo Meeting Status')
    c_lead_id = fields.Many2one('crm.lead', string='Lead Id')
    meeting_done = fields.Selection([('No','No'),('Yes','Yes')],'Meeting Done with Branch Manager?',default='No')

    otp = fields.Char('Meeting ID', size=4)
    contact_mobile = fields.Char('Contact Mobile')
    company_mobile = fields.Char('Company Mobile')
    no_otp = fields.Boolean('Meeting Without Meeting ID')
    otp_number_type = fields.Selection([('Contact Mobile', 'Contact Mobile'), ('Company Mobile', 'Company Mobile')], string='Meeting ID Number', default='Contact Mobile')
    otp_received = fields.Boolean('Meeting ID Received')        

    @api.multi
    def generate_otp(self):
        self.otp_received = True

        if self.otp_number_type == 'Contact Mobile':
            mobile_num = self.contact_mobile.strip()
        else:
            mobile_num = self.company_mobile.strip()

        param = self.env['ir.config_parameter']
        sendOTPIndiaUrl = param.search([('key', '=', 'sendOTPIndiaUrl')])
        clientIdForOTP = param.search([('key', '=', 'clientIdForOTP')])

        url = sendOTPIndiaUrl.value
        otp_msg = "Greetings from NowFloats. Hope your meeting with our sales consultant went well. The Meeting ID is [OTP]",

        querystring = {"mobileNumber": mobile_num,
                       "messageTemplate": otp_msg,
                       "clientId": clientIdForOTP.value
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        response = json.loads(response.text)
        return {
            'name': _("Meeting ID Verification"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'ouc.meeting.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': self.env.context
        }

    @api.multi
    def generate_otp_oncall(self):
        if self.otp_number_type == 'Contact Mobile':
            mobile_num = self.contact_mobile.strip()
        else:
            mobile_num = self.company_mobile.strip()

        param = self.env['ir.config_parameter']
        generateOTPOnCallUrl = param.search([('key', '=', 'generateOTPOnCallUrl')])
        clientIdForOTP = param.search([('key', '=', 'clientIdForOTP')])
        url = generateOTPOnCallUrl.value

        querystring = {"mobileNumber": mobile_num,
                       "clientId": clientIdForOTP.value
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        response = json.loads(response.text)
        if response:
            meeting_id=response['Result']
            if meeting_id:
                self.get_otp_oncall(meeting_id)
            else:
                raise ValidationError("Invalid Mobile Number !")

        return {
            'name': _("Meeting ID On Call"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'ouc.meeting.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': self.env.context
        }

    @api.multi
    def get_otp_oncall(self,meeting_id):
        self.otp_received = True

        if self.otp_number_type == 'Contact Mobile':
            mobile_num = self.contact_mobile.strip()
        else:
            mobile_num = self.company_mobile.strip()

        param = self.env['ir.config_parameter']
        sendOTPOnCallUrl = param.search([('key', '=', 'sendOTPOnCallUrl')])
        clientIdForOTP = param.search([('key', '=', 'clientIdForOTP')])
        url = sendOTPOnCallUrl.value
        otp_word = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 0: "zero"}
        meeting_id_word=''
        for num in str(meeting_id):
            meeting_id_word+=otp_word[int(num)]+' '
        meeting_id_word=meeting_id_word.strip()
        otp_msg = "Greetings from NowFloats. The Meeting ID for the meeting with our Sales Consultant is "+meeting_id_word

        querystring = {"mobileNumber": mobile_num,
                       "message": otp_msg,
                       "clientId": clientIdForOTP.value
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        response = json.loads(response.text)
        return True

    @api.multi
    def verify_meeting_id(self):
        if self.no_otp:
            return True

        if self.otp_number_type == 'Contact Mobile':
            mobile_num = self.contact_mobile.strip()
        else:
            mobile_num = self.company_mobile.strip()

        param = self.env['ir.config_parameter']
        verifyOTP = param.search([('key', '=', 'verifyOTPUrl')])
        clientIdForOTP = param.search([('key', '=', 'clientIdForOTP')])

        url = verifyOTP.value
        otp = self.otp
        querystring = {"mobileNumber": mobile_num,
                       "otp": otp,
                       "clientId": clientIdForOTP.value
                       }

        headers = {
            'content-type': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        response = json.loads(response.text)

        if not response:
            raise ValidationError("Invalid Meeting ID !")

        return True

    def creating_meeting_button(self):
        active_model = self.env.context.get('active_model')
        
        self.verify_meeting_id()
        
        if not self.meeting_description or len(self.meeting_description) < 100:
            raise exceptions.ValidationError(_('No Meeting Description or Meeting Description is too short. It should be more than 100 character'))
        
        if active_model:
            obj_id = self.env[active_model].browse(self.env.context.get('active_id'))
            obj_id.c_is_meeting_done = False
            obj_id.description = self.meeting_description
            obj_id.c_meeting_type = self.meeting_type
            obj_id.c_is_meeting_done = True
            obj_id.c_contact_status = self.contact_status
            obj_id.c_meeting_status = self.meeting_status
            obj_id.c_demo_status = self.c_demo_status
            obj_id.c_demo_type = self.c_demo_type
            obj_id.c_fptag = self.c_fptag
            obj_id.c_customer_count = self.c_customer_count
            obj_id.c_follow_date = self.c_follow_date
            obj_id.meeting_done = self.meeting_done
            template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats CRM - Customer Log')], limit=1)
            if template:
                template.send_mail(obj_id.id)

            template = self.env['mail.template'].sudo().search([('name', '=', 'NowFloats CRM - Customer Rating')], limit=1)
            if template:
                template.send_mail(obj_id.id)

            if obj_id:
                hr_obj=self.env['hr.employee'].sudo().search([('user_id','=',obj_id.user_id.id)])
                if hr_obj:
                    branh_manager_id = hr_obj.branch_id and hr_obj.branch_id.manager_id or False
                    bm_empl_id = branh_manager_id and branh_manager_id.id or False
                    bm_user_id = branh_manager_id and branh_manager_id.user_id and branh_manager_id.user_id.id or False
                
                meeting_id=self.env['crm.phonecall'].sudo().create({'name':obj_id.name,'date':fields.Datetime.now(),'user_id':obj_id.user_id.id,'state':'done','opportunity_id':obj_id.opportunity_id and obj_id.opportunity_id.id or False,'c_demo_type':obj_id.c_demo_type,'description':obj_id.description,'c_meeting_type':obj_id.c_meeting_type,'c_contact_status':obj_id.c_contact_status,'c_meeting_status':obj_id.c_meeting_status,'meeting_done':obj_id.meeting_done,'bm_empl_id':bm_empl_id,'bm_user_id':bm_user_id})
                
                #self.env.cr.execute("SELECT id FROM crm_phonecall WHERE otp = '{}'".format(self.otp))
                #otp_phone_id = self.env.cr.fetchone()

                #if otp_phone_id:
                 #   raise ValidationError("Meeting ID already been used!")
                if not self.no_otp:
                    self.env.cr.execute("UPDATE crm_phonecall SET otp = '{}' WHERE id = {}".format(self.otp, meeting_id.id))

                if meeting_id.meeting_done=='Yes':
                    template = self.env['mail.template'].sudo().search([('name', '=', 'BM Meeting Notification')], limit=1)
                    if template:
                        template.send_mail(meeting_id.id)

        return {
            'name': _("Meeting Logged"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'nf.meeting.logged',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': self.env.context
        }
    
    @api.model
    def default_get(self,fields):
        active_model = self.env.context.get('active_model')
        if active_model:
            obj_id = self.env[active_model].browse(self.env.context.get('active_id'))
            rec = super(ouc_meeting_wizard,self).default_get(fields)
            demo_id = self.env['calendar.event'].sudo().search([('c_demo_type', '=', 'Demo')])
            value = obj_id.opportunity_id
            fptag = []
            list = []
            for val in demo_id:
                list.append(val.opportunity_id.id)
            for fp in value.c_fptags_ids:
                fptag.append(fp.id)
            rec.update({'c_lead_id': value.id})
            if value.id in list:
                if len(fptag) == 0:
                    rec.update({'c_demo_type': 'Normal', 'c_demo_status': True})
                elif len(fptag) == 1:
                    rec.update({'c_demo_type': 'Normal', 'c_demo_status': True})
                else:
                    rec.update({'c_demo_type': 'Normal', 'c_demo_status': True})
            else:
                if len(fptag) == 0:
                    rec.update({'c_demo_type': 'Normal', 'c_demo_status': True})
                elif len(fptag) == 1:
                    rec.update({'c_demo_type': 'Normal'})
                else:
                    rec.update({'c_demo_type': 'Normal'})

            if not value.meeting_count:
                rec.update({'meeting_type': 'new'})
            else:
                rec.update({'meeting_type': 'Follow up'})

            rec.update({'contact_mobile': value.c_contact_mobile, 'company_mobile': value.mobile})

        return rec

class nf_meeting_logged(models.TransientModel):
    _name = 'nf.meeting.logged'


class bm_meeting_comment(models.TransientModel):
    _name = 'bm.meeting.comment'

    bm_comment = fields.Text('BM Comment')
    meeting_id = fields.Many2one('crm.phonecall','Meeting ID')

    @api.multi
    def submit_comment(self):
        for rec in self:
            rec.meeting_id.write({'bm_comment':rec.bm_comment,'bm_update':'Done','comment_date':datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return True

class wiz_mlc_onboarding(models.TransientModel):
    _name = 'wiz.mlc.onboarding'
    _description = 'Wizard MLC Onboarding'

    partner_id = fields.Many2one('res.partner','Customer')
    partner_email = fields.Char('Partner Email')
    partner_contact = fields.Char('Partner Contact')
    company_name = fields.Char('Business Name')
    so_id = fields.Many2one('sale.order','Sale Order')
    sales_person_id = fields.Many2one('res.users','Sales Person')
    contract_id = fields.Many2one('sale.subscription','Contract')
    onboarding_line = fields.One2many('wiz.mlc.onboarding.line','onboarding_id','Onboarding Line')
    existing_domain = fields.Selection([('Yes','Yes'),('No','No')],'Existing Domain*',default='Yes')
    domain_url = fields.Char('Domain URL')
    cpanel_user = fields.Char('CPanel Username')
    cpanel_pwd = fields.Char('CPanel Password')

    @api.multi
    def submit_info(self):
        for rec in self:
            line_vals=[]
            if rec.onboarding_line:
                for rec_onboard in rec.onboarding_line:
                    line_vals.append((0,False,{'country_id':rec_onboard.country_id and rec_onboard.country_id.id or False,'city_id':rec_onboard.city_id and rec_onboard.city_id.id or False,'address':rec_onboard.address,'contact_no':rec_onboard.contact_no,'email_id':rec_onboard.email_id,'url':rec_onboard.url,'location_type':rec_onboard.location_type,'city':rec_onboard.city}))
            values={'name':'Onboarding details for '+rec.partner_id.name,'so_id':rec.so_id.id,'sales_person_id':rec.sales_person_id.id,'partner_id':rec.partner_id.id,'company_name':rec.company_name,'partner_email':rec.partner_email,'partner_contact':rec.partner_contact,'contract_id':rec.contract_id and rec.contract_id.id or False,'onboarding_line':line_vals,'existing_domain':rec.existing_domain,'domain_url':rec.domain_url,'cpanel_user':rec.cpanel_user,'cpanel_pwd':rec.cpanel_pwd}
            mlc_onboard=self.env['nf.mlc.onboarding'].create(values)
            rec.so_id.sudo().write({'mlc_onboarding_form':mlc_onboard.id,'onboarding_done': True})
            rec.contract_id.sudo().write({'mlc_onboarding_form':mlc_onboard.id})
            template = self.env['mail.template'].sudo().search([('name', '=', 'MLC Onboarding')], limit=1)
            if template:
                template.send_mail(mlc_onboard.id)
        return True


class wiz_mlc_onboarding_line(models.TransientModel):
    _name = 'wiz.mlc.onboarding.line'
    _description = 'Wizard MLC Onboarding Line'

    onboarding_id = fields.Many2one('wiz.mlc.onboarding','Onboarding ID')
    country_id = fields.Many2one('res.country','Country')
    city_id = fields.Many2one('ouc.city','City')
    city = fields.Char('City')
    address = fields.Char('Address')
    contact_no = fields.Char('Contact No')
    email_id = fields.Char('Email ID')
    url = fields.Char('URL')
    location_type = fields.Selection([('Physical','Physical'),('Virtual','Virtual')],'Location Type')


class wiz_presale_order(models.TransientModel):
    _name = 'wiz.presale.order'

    @api.model
    def default_get(self, fields):
        res = {}
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id', False)
        if active_model == 'sale.order' and active_id:
            param = self.env['ir.config_parameter']
            presale_product = param.search([('key', '=', 'presale_product_price_revision')])
            obj_id = self.env[active_model].browse(active_id)
            self.env.cr.execute("SELECT sol.product_id, "
                                "sol.price_unit, sol.id "
                                "FROM sale_order_line sol LEFT JOIN product_product prod ON sol.product_id = prod.id "
                                "LEFT JOIN product_template prod_temp ON prod.product_tmpl_id = prod_temp.id "
                                "WHERE sol.order_id = {} AND prod_temp.name ilike '%{}%' ORDER BY sol.id".format(active_id, presale_product.value))
            lines = self.env.cr.fetchall()
            lines = map(lambda x: (0, False, {'product_id': x[0], 'price_unit': x[1], 'sol_id': x[2]}), lines)
            res['presale_lines'] = lines
        return res

    presale_lines = fields.One2many('wiz.presale.order.line', 'presale_order_id', string='Presale Lines')

    @api.multi
    def update_price(self):
        sol_obj = self.env['sale.order.line']
        for val in self.presale_lines:
            sol = sol_obj.browse(val.sol_id.id)
            if val.price_unit < sol.price_unit:
                raise exceptions.ValidationError(_(
                    'Unit price cannot be updated less than %s' % (sol.price_unit)))
            sol.sudo().write({'price_unit': val.price_unit})
            template = self.env['mail.template'].sudo().search([('name', '=', 'Presale Update Price Email')], limit=1)
            so_id = self.env.context.get('active_id', False)
            if template and so_id:
                self.env.cr.execute("UPDATE sale_order SET presale  = False, presale_status = True WHERE id = {}".format(so_id))
                template.send_mail(so_id)
        return True

class wiz_presale_order_line(models.TransientModel):
    _name = 'wiz.presale.order.line'

    product_id = fields.Many2one('product.product', 'Product')
    price_unit = fields.Float('Unit Price')
    presale_order_id = fields.Many2one('wiz.presale.order', 'Presale Order')
    sol_id = fields.Many2one('sale.order.line', 'Order Line ID')


class nf_ria_email(models.TransientModel):
    _name = 'nf.ria.email'

    @api.model
    def send_exteral_email(self, data):
        IrMailServer = self.env['ir.mail_server']

        for mail_id in data['mail_ids']:
            try:
                mail = self.env['mail.mail'].browse(mail_id)
                # TDE note: remove me when model_id field is present on mail.message - done here to avoid doing it multiple times in the sub method
                if mail.model:
                    model = self.env['ir.model'].sudo().search([('model', '=', mail.model)])[0]
                else:
                    model = None
                if model:
                    mail = mail.with_context(model_name=model.name)

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['datas_fname'], (a['datas'])) #base64.b64encode(a['datas']))
                               for a in mail.attachment_ids.sudo().read(['datas_fname', 'datas'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(mail.send_get_email_dict())
                for partner in mail.recipient_ids:
                    email_list.append(mail.send_get_email_dict(partner=partner))

                # headers
                headers = {}
                bounce_alias = self.env['ir.config_parameter'].get_param("mail.bounce.alias")
                catchall_domain = self.env['ir.config_parameter'].get_param("mail.catchall.domain")
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s+%d-%s-%d@%s' % (
                        bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s+%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(safe_eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _(
                        'Error without exception. Probably due do sending an email without computed recipients.'),
                })
                mail_sent = False

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                for email in email_list:
                    email_from=mail.email_from
                    email_to=email.get('email_to')
                    subject=mail.subject
                    body=email.get('body')
                    body_alternative=email.get('body_alternative')
                    email_cc=tools.email_split(mail.email_cc)
                    reply_to=mail.reply_to
                    attachments=attachments
                    message_id=mail.message_id
                    references=mail.references
                    object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model))
                    subtype='html'
                    subtype_alternative='plain'
                    headers=headers

            except:
                break

            i = 0
            attachement_links = []

            param = self.env['ir.config_parameter']
            #SavePartnerDashboardFilesUrl = param.search([('key', '=', 'SavePartnerDashboardFilesUrl')])
            #clientIdForS3Link = param.search([('key', '=', 'clientIdForS3Link')])

            s2LinkUrlAws = param.search([('key', '=', 's2LinkUrlAws')])

            emailApiUrl = param.search([('key', '=', 'emailApiUrl')])
            emailApiClientId = param.search([('key', '=', 'emailApiClientId')])

            s3_link_url = s2LinkUrlAws.value

            for v in attachments:
                file_name = v[0] or ''
                file_body = v[1]

                payload = {"fileData": file_body,
                           "fileName": file_name,
                           "fileCategory": 1
                           }

                data = json.dumps(payload)

                headers = {
                    'content-type': "application/json"
                }

                response = requests.request("POST", s3_link_url, data=data, headers=headers)
                response = json.loads(response.text)

                if response.get('body', ''):
                    attachement_links.append(response.get('body')['result'])

                #base_url = "{0}?clientId={1}&requestIdentifierType={2}&fileType={3}" #""https://api.withfloats.com/Support/v1/FloatingPoint/SavePartnerDashboardFiles?" \
                #url = base_url.format(SavePartnerDashboardFilesUrl.value, clientIdForS3Link.value, 3, 'pdf')
                #response = requests.put(url, data=file_body)
                #link = json.loads(response.text)['Result']

                i = i + 1

            print"========attachement_links======", attachement_links
            url = emailApiUrl.value #'https://api.withfloats.com/Internal/v1/PushEmailToQueue/A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E'
            vals = {"ClientId": emailApiClientId.value, #"A91B82DE3E93446A8141A52F288F69EFA1B09B1D13BB4E55BE743AB547B3489E",
                    "EmailBody": body,
                    "ReplyTo": 'alerts@nowfloats.com', #'alerts@nowfloats.com', #"hello@nowfloats.com",
                    "Subject": subject,
                    "To": email_to,
                    "Type": 0,
                    "CC": email_cc,
                    #"BCC": ['mohit.katiyar@nowfloats.com']
                    "Attachments": attachement_links,
                    }

            req = urllib2.Request(url)
            req.add_header('Content-Type', 'application/json')
            data = json.dumps(vals)
            response = urllib2.urlopen(req, data)
            encoder = response.read().decode('utf-8')
            print"======encoder====", encoder

        return True

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail_action(self):
        context = self.env.context
        if (context.get('active_model', '') == 'sale.order' or context.get('active_model', '') == 'nf.custom.quotation')\
                and context.get('active_id', False):
            active_id = context.get('active_id', False)
            template_id = context.get('default_template_id', False)
            if template_id:
                mail_id = self.env['mail.template'].browse(template_id).send_mail(active_id)
                res = self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})
        # TDE/ ???
        return self.send_mail()




