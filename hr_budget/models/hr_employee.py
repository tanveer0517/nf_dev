from openerp import api, models, _
from openerp.osv import fields, osv

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _columns={
#               'budget_lines':fields.one2many('budget.lines','manager_id','Budget History'),
#               'requisition_lines':fields.one2many('requisition.line','manager_id','Requisition History'),
              }
