# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PayrollFinanceRejectWizard(models.TransientModel):
    _name = "nf.payroll.finance.reject.wizard"

    finance_reject_reason = fields.Char('finance_reject_reason')

    @api.multi
    def set_close_cancel(self):
        self.ensure_one()
        payroll_component = self.env['nf.payslip.components'].browse(self.env.context.get('active_id'))
        payroll_component.finance_remarks = self.finance_reject_reason
        final_remarks = payroll_component.c_final_remarks
        if final_remarks:
            raise ValidationError("Cannot Reject this entry. Please check the final remarks for clarification")
        payroll_component.status = 'Rejected'
        # Trigger email to Payroll Team
        return True

class ApprovePayrollFinance(models.TransientModel):
    _name = "payroll.finance.approve"
    _description = "Bulk Approve Payslip Components By Finance"

    @api.multi
    def bulk_approve_by_finance(self):
        context = dict(self._context or {})
        payrolls = self.env['nf.payslip.components'].browse(context.get('active_ids'))
        payroll_to_approve = self.env['nf.payslip.components']
        for payroll_ids in payrolls:
            if payroll_ids.status == 'Approved By Payroll':
                payroll_ids.status = 'Approved'
                payroll_to_approve += payroll_ids
        return {'type': 'ir.actions.act_window_close'}
