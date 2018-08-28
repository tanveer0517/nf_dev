from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ouc_account_payment(models.Model):
    _inherit = "account.payment"
    
    c_subscription_id = fields.Many2one('sale.subscription', string='Subscription ID')
    c_payment_ref = fields.Char(string = 'Payment Reference Number')
    c_from_subscription = fields.Boolean('Is created from subscription', default=False)
    c_sale_order_id = fields.Many2one('sale.order',string='Sal order ref')
    c_type_of_pay = fields.Selection([('Full Payment','Full Payment'),('Partial Payment','Partial Payment')],string='Type of Payment')
    c_transaction_type =  fields.Selection([('Cash','Cash'),('Cheque','Cheque'),('Online','Online')],string='Transaction Type')

    @api.onchange('journal_id')
    def set_account_value(self):
        if self.c_subscription_id:
            self.partner_type = 'customer'
            self.payment_type = 'inbound'
            self.partner_id = self.c_subscription_id.partner_id.id
            self.amount = self.c_subscription_id.c_amount_to_be_paid
            self.c_from_subscription = True
            
    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
            if not rec.name:
                rec.name = "CUST/INV/"+str(self.id)
            print rec.name
            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            move.payment_ref = rec.c_payment_ref

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'posted', 'move_name': move.name})

