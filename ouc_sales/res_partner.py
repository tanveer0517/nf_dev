from odoo import api, models, fields, _, SUPERUSER_ID

class ouc_sales_res_partner(models.Model):
    _inherit = 'res.partner'
    
    c_alliance_id = fields.Char('Alliance Id')
    c_is_partner = fields.Boolean('Is a Partner')
    c_city_id = fields.Many2one('ouc.city', string = 'City')
    
    state_id = fields.Many2one('res.country.state', string="State", related='c_city_id.state_id')
    country_id = fields.Many2one('res.country', string="State", related='c_city_id.country_id')
    
    c_gstn_num = fields.Char('GSTN')

    # FOR NF PARTNER TYPE
    c_company_desc = fields.Char(string='Company Description')
    c_company_type = fields.Char(string='Company Type')
    c_existing_customers = fields.Integer(string='Existing Customers')
    c_account_no = fields.Char(string='Account Number')
    c_bank_name = fields.Char(string='Bank Name')
    c_branch_address = fields.Char(string='Branch Address')
    c_cin_number = fields.Char(string='Cin Number')
    c_ifsc_code = fields.Char(string='IFSC Code')
    c_micr_code = fields.Char(string='Micr Code')
    c_pan_number = fields.Char(string='Pan Number')
    c_payee_name = fields.Char(string='Payee Name')
    c_service_tax_no = fields.Char(string='Service Tax Number')
    c_tan_number = fields.Char(string='Tan Number')
    c_int_lead_ref_id = fields.Many2one('crm.lead', string='Internal Lead Ref Id')
    c_licenses = fields.Integer(string='Licenses')
    c_package_id = fields.Char(string='Package Id')
    c_tds_in_percentage = fields.Float(string='Tds In Percentage')
    c_yearly_subscription = fields.Integer(string='Yearly Subscription')
    c_composition_taxable = fields.Selection([('Yes','Yes'),('No','No')],string='Composition Taxable')
    c_gstn_registered = fields.Selection([('Yes','Yes'),('No','No')],string='GSTIN Registered')
    slab_id = fields.Many2one('nf.la.slab', 'Partner Slab')

    @api.onchange('parent_id')
    def getting_city(self):
        if self.parent_id:
            self.c_city_id = self.parent_id.c_city_id.id
    
    def redirect_to_support_dashboard(self):
	return {
            "type": "ir.actions.act_window",
            "res_model": "nf.support.dashboard",
            "views": [[self.env.ref('ouc_sales.nf_support_dashboard_form').id, "form"]],
            "domain": [],
            "context": {"partner_id": self.id},
            "name": "Partner Dashboard"
        }
        
        #param = self.env['ir.config_parameter']
        #support_dashboard_url = param.search([('key', '=', 'support_dashboard_url')])
        #support_dashboard_url = "http://support.nowfloatsdev.com/Home/InitiateOnboarding?redirectParams=%s" 
        #support_dashboard_url = support_dashboard_url.value% str(self.id)
        #print "support_dashboard_url",support_dashboard_url
        #return {
        #'type': 'ir.actions.act_url',
        #'url': support_dashboard_url,
        #'target': 'blank',
        #}
    
    
    @api.multi
    def _invoice_total(self):
        account_invoice_report = self.env['account.invoice.report']
        if not self.ids:
            self.total_invoiced = 0.0
            return True

        user_currency_id = self.env.user.company_id.currency_id.id
        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self:
            # price_total is in the company currency
            all_partners_and_children[partner] = self.search([('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        # searching account.invoice.report via the orm is comparatively expensive
        # (generates queries "id in []" forcing to build the full table).
        # In simple cases where all invoices are in the same currency than the user's company
        # access directly these elements

        # generate where clause to include multicompany rules
        where_query = account_invoice_report._where_calc([
            ('partner_id', 'in', all_partner_ids), ('state', 'not in', ['draft', 'cancel']), ('company_id', '=', self.env.user.company_id.id),
            ('type', 'in', ('out_invoice', 'out_refund'))
        ])
        account_invoice_report._apply_ir_rules(where_query, 'read')
        from_clause, where_clause, where_clause_params = where_query.get_sql()

        # price_total is in the company currency
        query = """
                  SELECT SUM(price_total) as total, partner_id
                    FROM account_invoice_report account_invoice_report
                   WHERE %s
                   GROUP BY partner_id
                """ % where_clause
        self.env.cr.execute(query, where_clause_params)
        price_totals = self.env.cr.dictfetchall()
        for partner, child_ids in all_partners_and_children.items():
            partner.total_invoiced = sum(price['total'] if price['total'] else 0 for price in price_totals if price['partner_id'] in child_ids)

    
    # FOR LA PARTNER
    @api.multi
    def getPartner(self):
        street1 = self.street or ""
        street2 = self.street2 or ""
        filtered_details = {
                                "address": street1 + " " + street2,
                                "city": self.c_city_id.name or "",
                                "companyDesc": self.c_company_desc or "",
                                "companyName": self.name or "",
                                "companyType": self.c_company_type or "",
                                "companyUrl": self.website or "",
                                "existingCustomers": self.c_existing_customers or 0,
                                "financialProfile":{
                                    "accountNumber": self.c_account_no or "",
                                    "bankName": self.c_bank_name or "",
                                    "branchAddress": self.c_branch_address or "",
                                    "cinNumber": self.c_cin_number or "",
                                    "ifscCode": self.c_ifsc_code or "",
                                    "micrCode": self.c_micr_code or "",
                                    "panNumber": self.c_pan_number or "",
                                    "payeeName": self.c_payee_name or "",
                                    "serviceTaxNumber": self.c_service_tax_no or "",
                                    "tanNumber": self.c_tan_number or ""
                                },
                                "internalLeadReferenceId": self.c_int_lead_ref_id.name or "",
                                "pincode": self.zip or "",
                                "primaryEmail": self.email or "",
                                "primaryName": self.name or "",
                                "primaryPhone": self.mobile or "",
                                "state": self.state_id.name or "",
                                "tdsInPercentage": self.c_tds_in_percentage or 0,
                                "selectedPackages":[{
                                    "Licenses": self.c_licenses or 0,
                                    "PackageId": self.c_package_id or ""
                                }],
                                "yearlySubscription": self.c_yearly_subscription or 0
                            }
        return filtered_details
    
    
class ouc_sales_res_bank(models.Model):
    _inherit = 'res.bank'
    c_city_id = fields.Many2one('ouc.city')
    city = fields.Char(string='City', related='c_city_id.name')
    state_id = fields.Many2one('res.country.state', string='State', related='c_city_id.state_id')
    country_id = fields.Many2one('res.country', string='Country', related='c_city_id.country_id')

class res_currency(models.Model):
    _inherit = "res.currency"

    @api.multi
    def compute(self, from_amount, to_currency, round=True):
        """ Convert `from_amount` from currency `self` to `to_currency`. """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "compute from unknown currency"
        assert to_currency, "compute to unknown currency"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount or 0
        else:
            to_amount = from_amount * self._get_conversion_rate(self, to_currency)
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount
