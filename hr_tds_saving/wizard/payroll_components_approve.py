from odoo import models, api, _
from odoo.exceptions import UserError


class ApprovePayrollComponents(models.TransientModel):
    _name = "payroll.components.approve"
    _description = "Bulk Approve Payslip Components By Payroll Team"

    @api.multi
    def bulk_approve_by_payroll(self):
        context = dict(self._context or {})
        payrolls = self.env['nf.payslip.components'].browse(context.get('active_ids'))
        payroll_to_approve = self.env['nf.payslip.components']
        for payroll_ids in payrolls:
            if payroll_ids.status == 'Draft':
                payroll_ids.status = 'Approved By Payroll'
            elif payroll_ids.status == 'Rejected' and payroll_ids.c_final_remarks:
                payroll_ids.status = 'Approved By Payroll'
            payroll_to_approve += payroll_ids
        # Trigger email to Finance
        return {'type': 'ir.actions.act_window_close'}
