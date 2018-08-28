from openerp import api, fields, models, _
from odoo.exceptions import ValidationError,Warning
import time
from odoo.fields import Date
import collections

class ou_wiz_resign(models.TransientModel):
    _name = 'wiz.resign'

    c_last_wor_date = fields.Date('Last Working Date')

    def update_last_date(self):
        active_model = self.env.context.get('active_model')
        if active_model:
            obj_id = self.env[active_model].browse(self.env.context.get('active_id'))
            if self.c_last_wor_date:
                obj_id.hr_last_work_date = self.c_last_wor_date
                self.env.cr.execute("UPDATE hr_employee set last_working_date = %s where id=%s",(self.c_last_wor_date, obj_id.name.id,))


class ou_wiz_termination(models.TransientModel):
    _name = 'wiz.termination'

    c_last_wor_date = fields.Date('Last Working Date')

    def update_last_date(self):
        active_model = self.env.context.get('active_model')
        if active_model:
            obj_id = self.env[active_model].browse(self.env.context.get('active_id'))
            if self.c_last_wor_date:
                obj_id.hr_last_work_date = self.c_last_wor_date
                self.env.cr.execute("UPDATE hr_employee set last_working_date = %s where id=%s",(self.c_last_wor_date, obj_id.name.id,))


