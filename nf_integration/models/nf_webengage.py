from odoo import models, fields, api, _
from openerp.osv import osv
import json,urllib,urllib2
from dateutil.relativedelta import relativedelta
import requests

class crm_lead(models.Model):
    _inherit = 'crm.lead'

    call_sid = fields.Char('Call Sid')
    recording_url = fields.Char('Call Recording Url',track_visibility='onchange')

    def sync_to_webenage(self):
        url = "https://api.webengage.com/v1/accounts/14507d748/users"
        data = {
            "userId": self.email_from.strip(),
            "firstName": self.c_customer_fname.strip(),
            "email": self.email_from.strip(),
            "phone": self.mobile.strip(),
            "company": self.partner_name.strip(),
            "attributes": {'sales_email': self.user_id and self.user_id.login or ''}
        }
        data = json.dumps(data)

        headers = {
            'content-type': "application/json",
            'authorization': "bearer 58923c1e-6d37-4f47-b139-b13b8f4e6022",
            'cache-control': "no-cache",
        }

        response = requests.request("POST", url, data=data, headers=headers)
        return True

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        # context: no_log, because subtype already handle this
        res = super(crm_lead, self.with_context(context, mail_create_nolog=True)).create(vals)
        try:
            res.sync_to_webenage()
        except:
            pass
        return res