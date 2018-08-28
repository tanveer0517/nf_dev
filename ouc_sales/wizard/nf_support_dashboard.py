from openerp import api, models, fields, _, SUPERUSER_ID
from openerp.exceptions import except_orm, Warning
import time
from odoo import exceptions
from odoo.exceptions import ValidationError

class nf_support_dashboard(models.TransientModel):
	_name= 'nf.support.dashboard'

	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False,
						):
		res = {}
		id = False

		if self._context is None: self._context = {}

		res = super(nf_support_dashboard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)

		if view_type == 'form':
			partner_id = self.env.context.get('partner_id','')
			param = self.env['ir.config_parameter']
			support_dashboard_url = param.search([('key', '=', 'support_dashboard_url')])
			support_dashboard_url = support_dashboard_url.value % str(partner_id)
			res['arch'] = """<form string="Partner Dashboard" create="false" edit="false">
                                       <iframe src="{}" width="1250" height="1250"/>
                                     </form>""".format(support_dashboard_url)
		return res
