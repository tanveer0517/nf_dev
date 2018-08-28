from openerp import api, fields, models, _
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib2 import Request, urlopen
import json, urllib, urllib2
import smtplib
from odoo import exceptions
import uuid
import requests

mib_enum = {0 :'Not Done Yet', 1 :'Hold', 2 :'Yes'}

class nf_api(models.Model):
    _name = "nf.api"

    # API
    @api.model
    def generateInvSalesOrder(self, data):
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))

        tdsPercentage = float(data["tdsPercentage"])

        packages = []
        for val in data["packages"]:
            prod_id = self.env['product.product'].browse(val["ProductId"])
            packages.append({
                "product_id": prod_id,
                "discount": val["discount"],
                "quantity": val["quantity"]
            })

        return self.create_sales_order(partner, packages, tdsPercentage)

    #API 1
    @api.model
    def generatePackagesAndSalesOrder(self, data):
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))

        tdsPercentage = float(data["tdsPercentage"])

        mibStatus = data.get("mibStatus", 0)
        mib_status = mib_enum[mibStatus]

        packages = []
        for val in data["packages"]:
            package_id = val["packageId"]
            prod_id = self.env['product.product'].search([('c_package_id', '=', package_id)], limit=1)
            if not prod_id:
                product_data = {
                    "name": val["productName"],
                    "list_price": val["price"],
                    "partner_id": partner.id,
                    "c_package_id": val["packageId"],
                    "c_validity": val["validity"]
                }
                product_id = self.env['product.template'].create(product_data)
                product_id.create_variant_ids()
                prod_id = self.env['product.product'].search([('product_tmpl_id', '=', product_id.id)], limit=1)

            packages.append({
                "product_id": prod_id,
                "discount": val["discount"],
                "quantity": val["quantity"]
            })

        return self.create_sales_order(partner, packages, tdsPercentage, mib_status)

    # API 2
    @api.model
    def generateSalesOrder(self, data):
        packages = []
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))

        tdsPercentage = float(data["tdsPercentage"])

        for val in data['packages']:
            package_id = val["packageId"]
            product_id = self.env['product.product'].search([('c_package_id', '=', package_id)])
            if not product_id:
                raise exceptions.ValidationError(
                    _('No Product found for this partner, please call createProductAndInvoice method'))
            packages.append({
                "product_id": product_id[0],
                "discount": val["discount"],
                "quantity": val["quantity"]
            })

        return self.create_sales_order(partner, packages, tdsPercentage)

    #Create Sales Order
    @api.model
    def create_sales_order(self, partner, packages, tdsPercentage, mib_status = 'Not Done Yet'):
        user_id = self.env.uid
        lc_id = self.env.uid
        lead = partner.c_int_lead_ref_id
        if lead:
            user_id = lead.user_id and lead.user_id.id or self.env.uid
            lc_id = lead.c_lead_creator_id and lead.c_lead_creator_id.id or self.env.uid

        team_id = self.env['crm.team'].search([('name', '=', 'LA')], limit=1)
        team_id = team_id and team_id.id or False

        note = ''
        if tdsPercentage:
            note = 'TDS - ' + str(tdsPercentage) + '%'

        mib_hold_issue = ''
        if mib_status == 'Hold':
            mib_hold_issue = 'S.O. Without Attachment'
        elif mib_status == 'Yes':
            mib_hold_issue = 'No Issue'

        pricelist_id = partner.property_product_pricelist and partner.property_product_pricelist.id or 1

        quote_type = 'new'
        subscription_id = False
        subscription = self.env['sale.subscription'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if subscription:
            quote_type = 'new'
            subscription_id = subscription.id

        addr = partner.address_get(['delivery', 'invoice'])
        fpos_ids = self.env['account.fiscal.position'].get_fiscal_position(partner.id, partner.id)
        order_lines = [(0, False, {'product_id': rec['product_id'].id,
                                   'name': rec['product_id'].name,
                                   'price_unit': rec['product_id'].list_price or 0.0,
                                   'product_uom_qty': rec['quantity'] or 1.0,
                                   'c_pkg_validity': rec['product_id'].c_validity,
                                   'c_max_discount': rec['discount'] or 0.0,
                                   'discount': rec['discount'] or 0.0,
                                   'c_status': quote_type
                                   }) for rec in packages]

        vals = {
            'pricelist_id': pricelist_id,
            'partner_id': partner.id,
            'c_company_name': partner.name,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'c_quotation_type': quote_type,
            'order_line': order_lines,
            'fiscal_position_id': fpos_ids,
            'user_id': user_id,
            'team_id': team_id,
            'payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
            'c_lead_source_id': lead.c_lead_source_id and lead.c_lead_source_id.id or False,
            'c_lead_creator_id': lc_id,
            'opportunity_id': lead and lead.id or False,
            'template_id': 1,
            'c_gstin_reg': 'No',
            'state': 'done',
            'confirmation_date': fields.Date.context_today(self),
            'note': note,
            'mib_status': mib_status,
            'mib_hold_issue': mib_hold_issue
        }
        order = self.env['sale.order'].create(vals)
        order._compute_tax_id()
        contract_id = self.create_subscription(order.id, partner.id, pricelist_id, user_id,
                                               order.project_id and order.project_id.id or None,
                                               team_id, quote_type, subscription_id, mib_hold_issue)

        template = self.env['mail.template'].search([('name', '=', 'NowFloats LA Sale Order')], limit=1)
        if template:
            mail_id = template.send_mail(order.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})

        return {'SalesOrderId': order.id, 'SalesOrder': order.name, 'SubscriptionId': contract_id}

    #Create Contract
    @api.model
    def create_subscription(self, order_id, partner_id, pricelist_id, user_id, analytic_account_id, team_id,
                            c_quotation_type, subscription_id=None, mib_hold_issue = 'No Issue'):
        if not subscription_id:
            uuid_temp = uuid.uuid4()
            self.env.cr.execute("INSERT "  # Create Contract
                                "INTO "
                                "sale_subscription "
                                "(partner_id, pricelist_id, create_date, write_date, create_uid, write_uid, user_id, date, "
                                "template_id, analytic_account_id, state, uuid, c_rta_hold_issue, c_sales_order_id, date_start, c_team_id) "
                                "VALUES "
                                "({}, {}, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', {}, {}, {}, "
                                "'now'::date, 1, {}, 'open', '{}', 'No Issue', {}, 'now'::date, {}) RETURNING id"
                                .format(partner_id, pricelist_id, self.env.uid, self.env.uid, user_id,
                                        analytic_account_id, 'API-' + str(uuid_temp), order_id, team_id))
            subscription_id = self.env.cr.fetchone()[0]

        self.env.cr.execute("SELECT "  # Compute tax ids
                            "account_tax_id "
                            "FROM "
                            "account_tax_sale_order_line_rel "
                            "WHERE sale_order_line_id = (SELECT id FROM sale_order_line WHERE order_id = {} LIMIT 1)"
                            .format(order_id))
        tax_ids = self.env.cr.fetchall()

        tax_sql = "sol.price_subtotal * " \
                  "(( SELECT COALESCE(sum(tax.amount), 0::numeric) " \
                  "FROM account_tax tax " \
                  "INNER JOIN account_tax_sale_order_line_rel atsol ON atsol.account_tax_id = tax.id " \
                  "WHERE atsol.sale_order_line_id = sol.id) / 100::numeric)"

        self.env.cr.execute("SELECT "  # Fetch Sales Order Lines
                            "NOW() AT TIME ZONE 'UTC', "
                            "sol.create_date, "
                            "sol.write_date, "
                            "sol.create_uid, "
                            "sol.write_uid, "
                            "sol.product_id, "
                            "sol.name, "
                            "sol.price_unit, "
                            "sol.price_subtotal, "
                            "sol.discount, "
                            "sol.product_uom_qty, {}, "
                            "sol.price_subtotal, "
                            "sol.currency_id, "
                            "sol.c_status, "
                            "prod_tmp.c_validity, "
                            "sol.order_id, "
                            "so.user_id, "
                            "so.c_sp_branch, "
                            "so.project_id,"
                            "so.team_id, {} "
                            "FROM "
                            "sale_order_line sol LEFT JOIN sale_order so ON sol.order_id = so.id "
                            "LEFT JOIN product_product prod ON sol.product_id = prod.id "
                            "LEFT JOIN product_template prod_tmp ON prod.product_tmpl_id = prod_tmp.id "
                            "WHERE order_id = {}"
                            .format(tax_sql, subscription_id, order_id))

        sol_details = self.env.cr.fetchall()

        for sol in sol_details:
            self.env.cr.execute("INSERT "  # Create Contract Lines
                                "INTO "
                                "sale_subscription_line "
                                "(c_sale_date, create_date, write_date, create_uid, write_uid, "
                                "product_id, name, price_unit, price_subtotal, discount, quantity,"
                                "c_price_tax, amount_in_inr, currency_id,  c_status, c_validity, "
                                "c_sale_order_id, c_sales_person_id, c_sp_branch, c_cost_center, "
                                "c_team_id, analytic_account_id, uom_id, sold_quantity ) "
                                "VALUES "
                                "(%s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, "
                                " 1, 1) RETURNING id", sol)

            subscription_line_id = self.env.cr.fetchone()[0]

            tax_details = [(subscription_line_id, t_id[0]) for t_id in tax_ids]
            self.env.cr.executemany("INSERT "  # Update Tax Lines
                                    "INTO "
                                    "account_tax_sale_subscription_line_rel "
                                    "(sale_subscription_line_id, account_tax_id) "
                                    "VALUES "
                                    "(%s, %s)", tax_details)

        # Update SO In Contract
        c_rta_hold_description = ''
        if mib_hold_issue == 'S.O. Without Attachment':
            c_rta_hold_description = 'S.O. Without Attachment'
        self.env.cr.execute(
            "UPDATE sale_subscription SET c_sales_order_id = {}, "
            "c_rta_hold_issue = '{}', c_rta_hold_description = '{}' "
            "WHERE id = {}"
                .format(order_id, mib_hold_issue, c_rta_hold_description, subscription_id))

        return subscription_id




    #======================================MarketPlace API=================================

    # API 3
    @api.model
    def getMarketPlaceCostCenter(self):
        param = self.env['ir.config_parameter']
        param_obj = param.search([('key', '=', 'getMarketPlaceCostCenter')])
        cost_center_id = int(param_obj.value)
        return cost_center_id

    @api.model
    def generateErpMarketPlaceOrder(self, data):
        cr = self.env.cr
        packages = []
        customerName = data["customerName"]
        customerGSTN = data.get("customerGSTN", '')
        customerCity = data.get("customerCity", '')
        customerAdd1 = data.get("customerAdd1", '')
        customerAdd2 = data.get("customerAdd2", '')
        customerEmail = data.get("customerEmail", '')
        customerMobile = data.get("customerMobile", '')
        customerPin = data.get("customerPin", '')
        fpTag = data.get("fpTag", '')
        clientId = data.get("clientId", '')
        transactionId = data.get("transactionId", "Missed")
        paidAmount = data.get("paidAmount", 0)
        cost_center_id = self.getMarketPlaceCostCenter()
        claim_id = data.get("claimId", "Missed")
        is_marketplace = 1

        cr.execute("SELECT "
                   "res.id,"
                   "fp.id "
                   "FROM ouc_fptag fp "
                   "INNER JOIN res_partner res ON fp.customer_id = res.id "
                   "WHERE fp.name ilike '{}' AND res.name ilike '{}'"
                   .format(fpTag, customerName))
        fptag_details = cr.fetchone()
        if fptag_details:
            fptag_id = fptag_details[1]
            partner = self.env['res.partner'].browse(fptag_details[0])
            if customerGSTN:
                partner.x_gstin = customerGSTN
        else:
            customer_city_id = False
            state_id = False
            country_id = 105
            cr.execute("SELECT id, state_id, country_id FROM ouc_city WHERE name ilike '{}'".format(customerCity))
            city_data = cr.fetchone()
            if city_data:
                customer_city_id = city_data[0]
                state_id = city_data[1]
                country_id = city_data[2]

            values = {'name': customerName,
                      'c_city_id':customer_city_id,
                      'state_id': state_id,
                      'country_id':country_id,
                      'customer': True,
                      'company': True,
                      'x_gstin': customerGSTN,
                      'street': customerAdd1,
                      'street2': customerAdd2,
                      'email': customerEmail,
                      'mobile': customerMobile,
                      'zip' : customerPin
                      }
            partner = self.env['res.partner'].create(values)
            if fpTag:
                cr.execute("INSERT INTO ouc_fptag (name, customer_id, state) VALUES ('{}', {}, 'valid') RETURNING ID".format(fpTag, partner.id))
                fptag_id = cr.fetchone()[0]

        if not partner:
            raise exceptions.ValidationError(_('No Partner found'))

        for val in data['packages']:
            package_id = val["packageId"]
            pkg_validity = val.get('pkgValidity', 0)
            unit_price = val.get("unit_price", 1)
            product_id = self.env['product.product'].search([('c_package_id', '=', package_id)], limit = 1)
            if product_id:
               prod_temp_id = product_id.product_tmpl_id.id
               cr.execute("UPDATE product_template SET list_price = {} WHERE id = {}".format(unit_price, prod_temp_id))
            else:
                product_data = {
                    "name": val["productName"],
                    "list_price": unit_price,
                    "c_package_id": package_id,
                    "property_account_income_id": self.get_generic_income_account_id(is_marketplace)
                }
                product_tmpl_id = self.env['product.template'].create(product_data)
                product_tmpl_id.create_variant_ids()
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)

            packages.append({
                "product_id": product_id[0],
                "quantity": val["quantity"],
                "c_fptags_id": fptag_id,
                "discount": val.get('discount', 0),
                "c_validity": pkg_validity
            })
        result = self.create_ErpMarketPlace_sales_order(partner, cost_center_id, packages, claim_id)

        inv_vals = {'partnerErpId': partner.id,
                    'packages': packages,
                    'cost_center_id': cost_center_id,
                    'SalesOrderId': result['SalesOrderId'],
                    'SalesOrder': result['SalesOrder'],
                    'SubscriptionId' : result['SubscriptionId'],
                    'transactionId' : transactionId,
                    'paidAmount': paidAmount,
                    'marketplace_server_id': claim_id
                    }

        inv_result = self.generateErpMarketPlaceInvoice(inv_vals)
        result.update(inv_result)
        return result

    # Create Sales Order
    @api.model
    def create_ErpMarketPlace_sales_order(self, partner, cost_center_id, packages, claim_id):
        user_id = self.env.uid
        lc_id = self.env.uid
        cost_center_id = cost_center_id
        team_id = self.env['crm.team'].search([('name', '=', 'MarketPlace')], limit=1)
        team_id = team_id and team_id.id or False

        note = ''

        pricelist_id = partner.property_product_pricelist and partner.property_product_pricelist.id or 1

        quote_type = 'new'
        subscription_id = False
        subscription = self.env['sale.subscription'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if subscription:
            quote_type = 'renewalupsell'
            subscription_id = subscription.id

        addr = partner.address_get(['delivery', 'invoice'])
        fpos_ids = self.env['account.fiscal.position'].get_fiscal_position(partner.id, partner.id)
        order_lines = [(0, False, {'product_id': rec['product_id'].id,
                                   'name': rec['product_id'].name,
                                   'price_unit': rec['product_id'].list_price or 0.0,
                                   'product_uom_qty': rec['quantity'] or 1.0,
                                   'c_pkg_validity': rec['product_id'].c_validity,
                                   'c_max_discount': rec['discount'],
                                   'discount': rec['discount'],
                                   'c_status': quote_type,
                                   'c_fptag_not_required': True,
                                   'c_fptags_id': rec['c_fptags_id']
                                   }) for rec in packages]

        vals = {
            'pricelist_id': pricelist_id,
            'partner_id': partner.id,
            'c_company_name': partner.name,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'c_quotation_type': quote_type,
            'order_line': order_lines,
            'fiscal_position_id': fpos_ids,
            'user_id': user_id,
            'team_id': team_id,
            'payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
            'c_lead_creator_id': lc_id,
            'template_id': 1,
            'c_gstin_reg': 'No',
            'state': 'done',
            'confirmation_date': fields.Date.context_today(self),
            'project_id':cost_center_id,
            #'c_branch_id': branch_id,
            'note': note,
            'mib_status': 'Yes',
            'mib_hold_issue': 'No Issue',
            'claim_id': claim_id
        }
        order = self.env['sale.order'].create(vals)
        order._compute_tax_id()
        self.env.cr.execute("UPDATE sale_order SET project_id = {} WHERE id = {}".format(cost_center_id, order.id))
        contract_id = self.create_ErpMarketPlace_subscription(order.id, partner.id, pricelist_id, user_id,
                                               order.project_id and order.project_id.id or None,
                                               team_id, quote_type, subscription_id)

        template = self.env['mail.template'].search([('name', '=', 'NowFloats MarketPlace Sale Order')], limit=1)
        if template:
            mail_id = template.send_mail(order.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})

        return {'SalesOrderId': order.id, 'SalesOrder': order.name, 'SubscriptionId': contract_id}

    # Create Contract
    @api.model
    def create_ErpMarketPlace_subscription(self, order_id, partner_id, pricelist_id, user_id, analytic_account_id, team_id,
                            c_quotation_type, subscription_id=None):
        if not subscription_id:
            uuid_temp = uuid.uuid4()
            self.env.cr.execute("INSERT "  # Create Contract
                                "INTO "
                                "sale_subscription "
                                "(partner_id, pricelist_id, create_date, write_date, create_uid, write_uid, user_id, date, "
                                "template_id, analytic_account_id, state, uuid, c_rta_hold_issue, c_sales_order_id, date_start, c_team_id) "
                                "VALUES "
                                "({}, {}, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', {}, {}, {}, "
                                "'now'::date, 1, {}, 'open', '{}', 'No Issue', {}, 'now'::date, {}) RETURNING id"
                                .format(partner_id, pricelist_id, self.env.uid, self.env.uid, user_id,
                                        analytic_account_id, 'API-' + str(uuid_temp), order_id, team_id))
            subscription_id = self.env.cr.fetchone()[0]

        self.env.cr.execute("SELECT "  # Compute tax ids
                            "account_tax_id "
                            "FROM "
                            "account_tax_sale_order_line_rel "
                            "WHERE sale_order_line_id = (SELECT id FROM sale_order_line WHERE order_id = {} LIMIT 1)"
                            .format(order_id))
        tax_ids = self.env.cr.fetchall()

        tax_sql = "sol.price_subtotal * " \
                  "(( SELECT COALESCE(sum(tax.amount), 0::numeric) " \
                  "FROM account_tax tax " \
                  "INNER JOIN account_tax_sale_order_line_rel atsol ON atsol.account_tax_id = tax.id " \
                  "WHERE atsol.sale_order_line_id = sol.id) / 100::numeric)"

        self.env.cr.execute("SELECT "  # Fetch Sales Order Lines
                            "NOW() AT TIME ZONE 'UTC', "
                            "sol.create_date, "
                            "sol.write_date, "
                            "sol.create_uid, "
                            "sol.write_uid, "
                            "sol.product_id, "
                            "sol.name, "
                            "sol.price_unit, "
                            "sol.price_subtotal, "
                            "sol.discount, "
                            "sol.product_uom_qty, {}, "
                            "sol.price_subtotal, "
                            "sol.currency_id, "
                            "sol.c_status, "
                            "prod_tmp.c_validity, "
                            "sol.order_id, "
                            "so.user_id, "
                            "so.c_sp_branch, "
                            "so.project_id,"
                            "so.team_id, c_fptags_id, {} "
                            "FROM "
                            "sale_order_line sol LEFT JOIN sale_order so ON sol.order_id = so.id "
                            "LEFT JOIN product_product prod ON sol.product_id = prod.id "
                            "LEFT JOIN product_template prod_tmp ON prod.product_tmpl_id = prod_tmp.id "
                            "WHERE order_id = {}"
                            .format(tax_sql, subscription_id, order_id))

        sol_details = self.env.cr.fetchall()

        for sol in sol_details:
            self.env.cr.execute("INSERT "  # Create Contract Lines
                                "INTO "
                                "sale_subscription_line "
                                "(c_sale_date, create_date, write_date, create_uid, write_uid, "
                                "product_id, name, price_unit, price_subtotal, discount, quantity,"
                                "c_price_tax, amount_in_inr, currency_id,  c_status, c_validity, "
                                "c_sale_order_id, c_sales_person_id, c_sp_branch, c_cost_center, "
                                "c_team_id, c_fptags_id, analytic_account_id, uom_id, sold_quantity ) "
                                "VALUES "
                                "(%s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s,"
                                " 1, 1) RETURNING id", sol)

            subscription_line_id = self.env.cr.fetchone()[0]

            tax_details = [(subscription_line_id, t_id[0]) for t_id in tax_ids]
            self.env.cr.executemany("INSERT "  # Update Tax Lines
                                    "INTO "
                                    "account_tax_sale_subscription_line_rel "
                                    "(sale_subscription_line_id, account_tax_id) "
                                    "VALUES "
                                    "(%s, %s)", tax_details)

        # Update SO In Contract
        self.env.cr.execute(
            "UPDATE sale_subscription SET c_sales_order_id = {}, c_rta_hold_issue = 'No Issue' WHERE id = {}".format(order_id, subscription_id))

        return subscription_id


    #Invoice API

    @api.model
    def get_sale_journal_id(self):
        param = self.env['ir.config_parameter']
        param_obj = param.search([('key', '=', 'sale_journal_code')])
        sj = self.env['account.journal'].search([('code', '=', param_obj.value), ('type', '=', 'sale')], limit=1)
        return sj.id

    @api.model
    def getMarketPlaceAccount(self):
        param = self.env['ir.config_parameter']
        param_obj = param.search([('key', '=', 'marketplace_income_account_code')])
        account_ids = self.env['account.account'].search([('code', '=', param_obj.value)], limit=1)
        return account_ids

    @api.model
    def generateErpMarketPlaceInvoice(self, data):
        packages = []
        partner = self.env['res.partner'].browse(data["partnerErpId"])
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))

        packages = data['packages']
        cost_center_id = data.get('cost_center_id', False)
        SalesOrderId = data.get('SalesOrderId', False)
        SalesOrder = data.get('SalesOrder', '')
        SubscriptionId = data.get('SubscriptionId', False)
        transactionId = data.get('transactionId', None)
        paidAmount = data.get('paidAmount', None)
        marketplace_server_id = data.get('marketplace_server_id', None)

        return self.generate_invoice_and_lines(partner, packages, cost_center_id, SalesOrderId, SalesOrder,
                                               SubscriptionId, transactionId, paidAmount, marketplace_server_id)

    def generate_invoice_and_lines(self, partner, packages, cost_center_id = False, SalesOrderId=False, SalesOrder=False,
                                   SubscriptionId=False, transactionId = False, paidAmount = 0, marketplace_server_id='Missed'):

        user_id = self.env.uid
        team_id = self.env['crm.team'].search([('name', '=', 'MarketPlace')], limit=1)
        team_id = team_id and team_id.id or False

        invoice_data = {
            "partner_id": partner.id,
            "type": 'out_invoice',
            "c_company_name": partner.name,
            "date_invoice": fields.Date.context_today(self),
            "c_sale_date": fields.Date.context_today(self),
            "journal_id": self.get_sale_journal_id(),
            "user_id": user_id,
            "team_id": team_id,
            'c_sales_order_id': SalesOrderId,
            'origin': SalesOrder,
            'marketplace_transaction_id': transactionId,
            'c_gstn': partner.x_gstin or '',
            'marketplace_server_id': marketplace_server_id
        }
        #c_sp_branch = False
        #c_sp_emp_id = False
        invoice_id = self.env['account.invoice'].create(invoice_data)
        emp_obj = self.env['hr.employee'].search([('user_id', '=', user_id)])
        if emp_obj:
            #cost_centr = emp_obj.cost_centr and emp_obj.cost_centr.id or False
            c_sp_branch = emp_obj.branch_id and emp_obj.branch_id.id or False
            c_sp_emp_id = emp_obj.id

        for rec in packages:
            account = self.getMarketPlaceAccount()
            if not account:
                account = rec['product_id'].categ_id.property_account_income_categ_id
            account_id = invoice_id.fiscal_position_id.map_account(account).id

            invoice_line_data = {
                'product_id': rec['product_id'].id,
                'account_id': account_id,
                'name': rec['product_id'].name,
                'price_unit': rec['product_id'].list_price or 0.0,
                'discount': rec['discount'],
                'quantity': rec['quantity'] or 1.0,
                'c_pkg_validity': rec['product_id'].c_validity,
                'c_status': 'new',
                'account_analytic_id': cost_center_id,
                'c_sp_branch': c_sp_branch,
                'c_sp_emp_id': c_sp_emp_id,
                'invoice_id': invoice_id.id,
                'c_fptags_id': rec['c_fptags_id']
            }
            invoice_line = self.env['account.invoice.line'].create(invoice_line_data)
            invoice_line._set_taxes()

        invoice_id._onchange_invoice_line_ids()
        invoice_id.calculate_tds_amount()
        invoice_id.action_invoice_open()

        if SalesOrderId and SubscriptionId:
            self.env.cr.execute("UPDATE "
                                "sale_subscription_line "
                                "SET c_invoice_id = {}, c_invoice_date = 'now'::date "
                                "WHERE c_sale_order_id = {} AND analytic_account_id = {}".format(invoice_id.id,
                                                                                                 SalesOrderId,
                                                                                                 SubscriptionId))

            self.env.cr.execute("UPDATE "
                                "sale_order "
                                "SET inv_status = 'Activation done & Invoice Created', "
                                "sub_inv_id = {} "
                                "WHERE id = {}".format(invoice_id.id, SalesOrderId))

        self.env.cr.execute("INSERT "
                            "INTO "
                            "ouc_additional_payment_details "
                            "(downpay_type, payment_method, transfer_ref_number, amount, sale_order_id, subscription_id, invoice_id) "
                            "VALUES ('not_emi', 'online_transfer', '{}', {}, {}, {}, {})"
                            .format(transactionId, paidAmount, SalesOrderId, SubscriptionId, invoice_id.id))

        template = self.env['mail.template'].search([('name', '=', 'NowFloats MarketPlace Verification Call Mail Success')],
                                                    limit=1)
        if template:
            mail_id = template.send_mail(invoice_id.id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})
        return {'InvoiceNumber':invoice_id.number or "", 'InvoiceId':invoice_id.id}



    #==========================SO Generice API=========================================

    # API 3
    @api.model
    def getGenericCostCenter(self):
        param = self.env['ir.config_parameter']
        param_obj = param.search([('key', '=', 'getMarketPlaceCostCenter')])
        cost_center_id = int(param_obj.value)
        return cost_center_id

    @api.model
    def getFpId(self, Fptag, partner):
        cr = self.env.cr
        cr.execute("SELECT "
                   "id "
                   "FROM ouc_fptag fp "
                   "WHERE fp.name ilike '{}'"
                   .format(Fptag))

        fp = cr.fetchone()
        if fp:
            fpid = fp[0]
        else:
            cr.execute(
                "INSERT INTO ouc_fptag (name, customer_id, state) VALUES ('{}', {}, 'valid') RETURNING ID".format(Fptag,
                                                                                                     partner.id))
            fpid = cr.fetchone()[0]
        return fpid

    @api.model
    def get_fptag_city(self, fptag):
        res = ''
        try:
            param = self.env['ir.config_parameter']
            param_obj = param.search([('key', '=', 'getFpTagCityUrl')])
            url = param_obj.value

            payload = {"FPTags": [fptag]}

            data = json.dumps(payload)

            headers = {
                'Content-Type': "application/json"
            }
            response = requests.request("POST", url, data=data, headers=headers)

            response = json.loads(response.text)

            result = response['result']
            for val in result:
                city = val['City'].encode('utf-8') if val['City'] else val['City']
                return city
        except:
            pass
        return res

    @api.model
    def get_generic_income_account_id(self, isMarketPlaceOrder):
        param = self.env['ir.config_parameter']
        if isMarketPlaceOrder:
            param_obj = param.search([('key', '=', 'marketplace_income_account_code')])
            account_obj = self.env['account.account'].sudo().search([('code', '=', param_obj.value)])
            if not account_obj:
                raise exceptions.ValidationError(_('MarketPlace incmoe account not defined.'))
            account_id = account_obj.id
        else:
            param_obj = param.search([('key', '=', 'fos_income_account_code')])
            account_obj = self.env['account.account'].sudo().search([('code', '=', param_obj.value)])
            if not account_obj:
                raise exceptions.ValidationError(_('FOS incmoe account not defined.'))
            account_id = account_obj.id
        return account_id

    @api.model
    def generateGenericSalesOrder(self, data):
        cr = self.env.cr
        packages = []
        clientId = data.get("clientId", '')
        claim_id = data.get("claimId", "Missed")
        paidAmount = data.get("paidAmount", 0)
        tdsPercentage = data.get("tdsPercentage", 0)
        customerGSTN = data.get('customerGSTN', '')
        sales_assistant_id = data.get('salesAssistId', False)
        is_marketplace = data.get('isMarketplaceOrder', 0)
        division = 'FOS'
        if is_marketplace:
            division = 'MarketPlace'
        sp_emp_id = 9685

        param = self.env['ir.config_parameter']
        clientIdForDivision = param.search([('key', '=', str(clientId))], limit = 1)
        if clientIdForDivision:
            division = clientIdForDivision.value

        spId = param.search([('key', '=', 'spIdForGenericAPI')], limit = 1)
        if spId:
            sp_emp_id = int(spId.value)

        cr.execute("SELECT emp.cost_centr, res.user_id, emp.branch_id "
                   "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id "
                   "WHERE emp.id = {} AND res.active = True".format(sp_emp_id))

        emp_details = cr.fetchone()

        if not emp_details:
            raise exceptions.ValidationError(
                _('No Sales Person Found'))

        cost_center_id = emp_details[0]
        user_id = emp_details[1]
        branch_id = emp_details[2]

        partner  = self.env['res.partner'].browse(1)
        if not partner:
            raise exceptions.ValidationError(_('No Partner found'))

        for val in data['packages']:
            package_id = val["packageId"]
            pkg_validity = val['pkgValidity']
            product_id = self.env['product.product'].search([('c_package_id', '=', package_id),('c_validity', '=', pkg_validity)], limit=1)
            discount = val.get("discount", 0)
            fptag = val.get("Fptag", '')
            fptag_id = self.getFpId(fptag, partner)
            if not product_id:
                product_data = {
                    "name": val["productName"],
                    "list_price": val["price"],
                    "c_package_id": package_id,
                    "c_validity": pkg_validity,
                    "property_account_income_id": self.get_generic_income_account_id(is_marketplace)
                }
                product_tmpl_id = self.env['product.template'].create(product_data)
                product_tmpl_id.create_variant_ids()
                product_id = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl_id.id)], limit=1)

            packages.append({
                "product_id": product_id[0],
                "quantity": val["quantity"],
                "discount": discount,
                "fptag": fptag_id,
                "pkg_validity" : pkg_validity,
                "fptag_name": fptag
            })

        result = self.create_generic_sales_order(partner, cost_center_id, user_id, branch_id,
                                                 division, claim_id, tdsPercentage, customerGSTN, packages, sales_assistant_id)

        return result

    # Create Sales Order
    @api.model
    def create_generic_sales_order(self, partner, cost_center_id, user_id, branch_id,
                                   division, claim_id, tdsPercentage, customerGSTN, packages, sales_assistant_id):
        lc_id = user_id
        team_id = self.env['crm.team'].search([('name', '=', division)], limit=1)
        team_id = team_id and team_id.id or False

        note = ''
        c_gstin_reg = 'No'
        x_gstin = ''
        if tdsPercentage:
            note = 'TDS - ' + str(tdsPercentage) + '%'
        if customerGSTN:
            c_gstin_reg = 'Yes'
            x_gstin = customerGSTN

        sales_assist_db_id = False
        sales_assist_branch_id = False
        if sales_assistant_id:
            sales_assist = self.env['hr.employee'].sudo().search([('nf_emp', '=', sales_assistant_id)], limit = 1)
            if sales_assist:
                sales_assist_db_id = sales_assist.id
                sales_assist_branch_id = sales_assist.branch_id and sales_assist.branch_id.id or False

        pricelist_id = partner.property_product_pricelist and partner.property_product_pricelist.id or 1

        quote_type = 'new'
        subscription_id = False
        subscription = self.env['sale.subscription'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if subscription:
            quote_type = 'renewalupsell'
            subscription_id = subscription.id

        addr = partner.address_get(['delivery', 'invoice'])
        fpos_ids = self.env['account.fiscal.position'].get_fiscal_position(partner.id, partner.id)
        order_lines = [(0, False, {'product_id': rec['product_id'].id,
                                   'name': rec['product_id'].name,
                                   'price_unit': rec['product_id'].list_price or 0.0,
                                   'product_uom_qty': rec['quantity'] or 1.0,
                                   'c_pkg_validity': rec['pkg_validity'],
                                   'c_max_discount': rec['discount'],
                                   'discount': rec['discount'],
                                   'c_status': quote_type,
                                   'c_fptag_not_required': True,
                                   'c_fptags_id': rec['fptag'],
                                   'fptag_city': self.get_fptag_city(rec['fptag_name'])
                                   }) for rec in packages]

        vals = {
            'pricelist_id': pricelist_id,
            'partner_id': partner.id,
            'c_company_name': partner.name,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'c_quotation_type': quote_type,
            'order_line': order_lines,
            'fiscal_position_id': fpos_ids,
            'user_id': user_id,
            'team_id': team_id,
            'payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
            'c_lead_creator_id': lc_id,
            'template_id': 1,
            'c_gstin_reg': c_gstin_reg,
            'x_gstin': x_gstin,
            'state': 'done',
            'confirmation_date': fields.Date.context_today(self),
            'project_id': cost_center_id,
            'c_sp_branch': branch_id,
            'note': note,
            'claim_id': claim_id,
            'mib_status': 'S.O. Not Claimed',
            'sales_assist_id': sales_assist_db_id,
            'sales_assist_branch_id': sales_assist_branch_id

        }
        order = self.env['sale.order'].create(vals)
        order._compute_tax_id()
        self.env.cr.execute("UPDATE sale_order SET project_id = {}, user_id = {}, c_sp_branch = {} WHERE id = {}".format(cost_center_id, user_id, branch_id, order.id))
        contract_id = self.create_ErpGeneric_subscription(order.id, partner.id, pricelist_id, user_id,
                                                              order.project_id and order.project_id.id or None,
                                                              team_id, quote_type, subscription_id)

        try:
            template = self.env['mail.template'].search([('name', '=', 'NowFloats Generic Sale Order')], limit=1)
            if template:
                template.send_mail(order.id)
        except:
            pass

        try:
            for line in order.order_line:
                if line.c_fptags_id:
                    city = self.get_fptag_city(line.c_fptags_id.name)
                    if city:
                        self.env.cr.execute("UPDATE sale_order SET fptag_city = '{}' WHERE id = {}"
                                            .format(city, order.id))
                        break
        except:
            pass


        return {'SalesOrderId': order.id, 'SalesOrder': order.name, 'SubscriptionId': contract_id}

    # Create Contract
    @api.model
    def create_ErpGeneric_subscription(self, order_id, partner_id, pricelist_id, user_id, analytic_account_id,
                                           team_id,
                                           c_quotation_type, subscription_id=None):
        if not subscription_id:
            uuid_temp = uuid.uuid4()
            self.env.cr.execute("INSERT "  # Create Contract
                                "INTO "
                                "sale_subscription "
                                "(partner_id, pricelist_id, create_date, write_date, create_uid, write_uid, user_id, date, "
                                "template_id, analytic_account_id, state, uuid, c_rta_hold_issue, c_sales_order_id, date_start, c_team_id, recurring_next_date) "
                                "VALUES "
                                "({}, {}, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', {}, {}, {}, "
                                "'now'::date, 1, {}, 'open', '{}', 'No Issue', {}, 'now'::date, {}, 'now'::date) RETURNING id"
                                .format(partner_id, pricelist_id, self.env.uid, self.env.uid, user_id,
                                        analytic_account_id, 'API-' + str(uuid_temp), order_id, team_id))
            subscription_id = self.env.cr.fetchone()[0]

        self.env.cr.execute("SELECT "  # Compute tax ids
                            "account_tax_id "
                            "FROM "
                            "account_tax_sale_order_line_rel "
                            "WHERE sale_order_line_id = (SELECT id FROM sale_order_line WHERE order_id = {} LIMIT 1)"
                            .format(order_id))
        tax_ids = self.env.cr.fetchall()

        tax_sql = "sol.price_subtotal * " \
                  "(( SELECT COALESCE(sum(tax.amount), 0::numeric) " \
                  "FROM account_tax tax " \
                  "INNER JOIN account_tax_sale_order_line_rel atsol ON atsol.account_tax_id = tax.id " \
                  "WHERE atsol.sale_order_line_id = sol.id) / 100::numeric)"

        self.env.cr.execute("SELECT "  # Fetch Sales Order Lines
                            "NOW() AT TIME ZONE 'UTC', "
                            "sol.create_date, "
                            "sol.write_date, "
                            "sol.create_uid, "
                            "sol.write_uid, "
                            "sol.product_id, "
                            "sol.name, "
                            "sol.price_unit, "
                            "sol.price_subtotal, "
                            "sol.discount, "
                            "sol.product_uom_qty, {}, "
                            "sol.price_subtotal, "
                            "sol.currency_id, "
                            "sol.c_status, "
                            "prod_tmp.c_validity, "
                            "sol.order_id, "
                            "so.user_id, "
                            "so.c_sp_branch, "
                            "so.project_id,"
                            "so.team_id, {}, "
                            "sol.c_fptags_id,"
                            "sol.fptag_city "
                            "FROM "
                            "sale_order_line sol LEFT JOIN sale_order so ON sol.order_id = so.id "
                            "LEFT JOIN product_product prod ON sol.product_id = prod.id "
                            "LEFT JOIN product_template prod_tmp ON prod.product_tmpl_id = prod_tmp.id "
                            "WHERE order_id = {}"
                            .format(tax_sql, subscription_id, order_id))

        sol_details = self.env.cr.fetchall()

        for sol in sol_details:
            self.env.cr.execute("INSERT "  # Create Contract Lines
                                "INTO "
                                "sale_subscription_line "
                                "(c_sale_date, create_date, write_date, create_uid, write_uid, "
                                "product_id, name, price_unit, price_subtotal, discount, quantity,"
                                "c_price_tax, amount_in_inr, currency_id,  c_status, c_validity, "
                                "c_sale_order_id, c_sales_person_id, c_sp_branch, c_cost_center, "
                                "c_team_id, analytic_account_id, c_fptags_id, fptag_city, uom_id, sold_quantity ) "
                                "VALUES "
                                "(%s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s, "
                                "%s, %s, %s, %s, %s, %s, %s, "
                                " 1, 1) RETURNING id", sol)

            subscription_line_id = self.env.cr.fetchone()[0]

            tax_details = [(subscription_line_id, t_id[0]) for t_id in tax_ids]
            self.env.cr.executemany("INSERT "  # Update Tax Lines
                                    "INTO "
                                    "account_tax_sale_subscription_line_rel "
                                    "(sale_subscription_line_id, account_tax_id) "
                                    "VALUES "
                                    "(%s, %s)", tax_details)

        # Update SO In Contract
        self.env.cr.execute(
            "UPDATE sale_subscription SET c_sales_order_id = {} WHERE id = {}".format(order_id, subscription_id))

        return subscription_id


    #==================================Claim ID=========================================

    @api.multi
    def _compute_tax_id(self, so_obj, contract_line):
        fpos = so_obj.fiscal_position_id or so_obj.partner_id.property_account_position_id
        taxes = contract_line.product_id.taxes_id
        contract_line.c_tax_ids = fpos.map_tax(taxes, contract_line.product_id, so_obj.partner_shipping_id) if fpos else taxes

    @api.model
    def claimOrder(self, data):
        cr = self.env.cr
        claim_id = data["claimId"]
        email_id = data.get("emailId", '')
        hotProspect = data['hotProspect']

        cr.execute("SELECT emp.cost_centr, res.user_id, emp.branch_id "
                   "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id "
                   "WHERE emp.work_email = '{}' AND res.active = True".format(email_id))

        emp_details = cr.fetchone()

        if not emp_details:
            raise exceptions.ValidationError(
                _('No Sales Person Found'))

        cost_center_id = emp_details[0]
        user_id = emp_details[1]
        branch_id = emp_details[2]

        cr.execute("SELECT partner_id, c_lead_creator_id, id FROM crm_lead WHERE name = '{}'".format(hotProspect))
        hp_details = cr.fetchone()
        if not hp_details:
            raise exceptions.ValidationError(
                _('No Hot Prospect Found'))

        partner_id = hp_details[0]
        lc_id = hp_details[1]
        lead_id = hp_details[2]

        partner = self.env['res.partner'].browse(partner_id)
        pricelist_id = partner.property_product_pricelist and partner.property_product_pricelist.id or 1

        cr.execute("SELECT id, team_id, x_gstin FROM sale_order WHERE claim_id = '{}' AND is_claim IS NOT TRUE".format(claim_id))
        sale_order = cr.fetchone()

        if not sale_order:
            cr.execute(
                "SELECT id FROM sale_order WHERE claim_id = '{}'".format(
                    claim_id))
            generated_so = cr.fetchone()
            if not generated_so:
                raise exceptions.ValidationError(
                    _('Sales Order still pending for approval'))
            else:
                raise exceptions.ValidationError(
                    _('Sales Order already claimed'))

        so_id = sale_order[0]
        team_id = sale_order[1]
        gstn = sale_order[2]

        #Check whether receipt updated
        cr.execute("SELECT id FROM ouc_additional_payment_details "
                   "WHERE sale_order_id = {} "
                   "AND (COALESCE(receipt_pic_name, '') != '' OR COALESCE(receipt_pic, '') != '') "
                   "AND payment_method IN ('cash', 'cheque') "
                   "UNION "
                   "SELECT id FROM ouc_additional_payment_details "
                   "WHERE sale_order_id = {} "
                   "AND payment_method = 'online_transfer'".format(so_id, so_id))

        payment_ids = cr.fetchall()

        if not payment_ids:
            raise exceptions.ValidationError(
                _('You cannot claim sales order without attaching deposite slip'))

        so_obj =  self.env['sale.order'].sudo().browse(so_id)
        fpos_ids = self.env['account.fiscal.position'].get_fiscal_position(partner.id, partner.id)
        so_obj.fiscal_position_id = fpos_ids
        so_obj._compute_tax_id()

        if gstn:
            cr.execute("UPDATE res_partner SET x_gstin = '{}', c_gstn_registered = 'Yes' WHERE id = {}".format(gstn, partner_id))

        #Checking whether invoice is already created (Marketplace online payment case)
        cr.execute("SELECT id FROM sale_subscription_line WHERE c_sale_order_id = {} AND c_invoice_id IS NOT NULL".format(so_id))
        inv_contract_id = cr.fetchone()
        if inv_contract_id:
            param = self.env['ir.config_parameter']
            marketPlaceClaimApiUrl = param.search([('key', '=', 'marketPlaceClaimApiUrl')])

            url = marketPlaceClaimApiUrl.value
            payload = {"clientId":"ERPWE0892F2F45388F439BDE9F6F3FB5C31F0FAA628D40CD2920A79D8841597B",
                       "transactionId": claim_id,
                       "email": email_id
                       }

            headers = {
                'Content-Type': "application/json",
                'Cache-Control': "no-cache",
            }

            data = json.dumps(payload)
            response = requests.request("POST", url, data=data, headers=headers)
            response = json.loads(response.text)
            if response == 'Success':
                cr.execute("UPDATE "
                           "crm_lead SET c_quotation_created = True, "
                           "is_claim = True , claim_id = '{}' "
                           "WHERE id = {}"
                           .format(claim_id, lead_id))
                return True
            else:
                raise exceptions.ValidationError(
                    _('NO INVOICE EXISTING FOR GIVEN CLAIM ID OR SALE ALREADY CLAIMED'))

        cr.execute("SELECT id FROM sale_subscription WHERE partner_id = {}".format(partner_id))
        contract_details = cr.fetchone()
        if contract_details:
            status = 'renewalupsell'
            contract_id = contract_details[0]
            cr.execute("UPDATE sale_subscription SET c_sales_order_id = {}, c_invoice_status = 'yes', c_is_invoiced = False WHERE id = {}".format(so_id, contract_id))
        else:
            status = 'new'
            uuid_temp = uuid.uuid4()
            self.env.cr.execute("INSERT "  # Create Contract
                                "INTO "
                                "sale_subscription "
                                "(partner_id, pricelist_id, create_date, write_date, create_uid, write_uid, user_id, date, "
                                "template_id, analytic_account_id, state, uuid, c_rta_hold_issue, c_sales_order_id, date_start, c_team_id, recurring_next_date, c_invoice_status, c_is_invoiced) "
                                "VALUES "
                                "({}, {}, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC', {}, {}, {}, "
                                "'now'::date, 1, {}, 'open', '{}', 'No Issue', {}, 'now'::date, {}, 'now'::date, 'yes', False) RETURNING id"
                                .format(partner_id, pricelist_id, self.env.uid, self.env.uid, user_id,
                                        cost_center_id, 'API-' + str(uuid_temp), so_id, team_id))
            contract_id = cr.fetchone()[0]

        cr.execute("UPDATE sale_subscription_line SET c_cost_center = {}, c_sales_person_id = {}, "
                   "c_sp_branch = {}, analytic_account_id = {}, c_price_total = (price_subtotal + c_price_tax), c_status = '{}'"
                   "WHERE c_sale_order_id = {}"
                   .format(cost_center_id, user_id, branch_id, contract_id, status, so_id))

        cr.execute("UPDATE sale_order "
                   "SET partner_id = {}, project_id = {}, user_id = {}, "
                   "c_sp_branch = {}, c_lead_creator_id = {}, is_claim = True, opportunity_id = {}, c_quotation_type = '{}', mib_status = 'Not Done Yet' "
                   "WHERE id = {}".format(partner_id, cost_center_id, user_id, branch_id, lc_id, lead_id, status, so_id))

        cr.execute("UPDATE sale_order_line SET c_status = '{}' WHERE order_id = {}".format(status, so_id))

        for contract_line in self.env['sale.subscription.line'].sudo().search([('c_sale_order_id','=',so_id)]):
            self._compute_tax_id(so_obj, contract_line)

        try:
          template = self.env['mail.template'].search([('name', '=', 'NowFloats Sale Order')], limit=1)
          if template:
             mail_id = template.send_mail(so_id)
             self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})
        except:
            pass

        try:
            so_obj.sudo().so_confirmation_email()
        except:
            pass

        cr.execute("UPDATE "
                   "crm_lead SET c_quotation_created = True, "
                   "is_claim = True , claim_id = '{}' "
                   "WHERE id = {}"
                   .format(claim_id, lead_id))

        cr.execute("UPDATE "
                   "ouc_additional_payment_details SET subscription_id = {} "
                   "WHERE sale_order_id = {}"
                   .format(contract_id, so_id))

        return True

    @api.model
    def UpdateReceiptInSO(self, data):
        cr = self.env.cr
        claim_id = data.get("claimId", False)
        email_id = data.get("emailId", '')
        so_id = data.get('salesOrderId', False)
        receipt_pic = data['receiptPicBin']
        receipt_pic_name = data['receiptPicName']


        cr.execute("SELECT res.user_id "
                   "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id "
                   "WHERE emp.work_email = '{}' AND res.active = True".format(email_id))

        emp_user_id = cr.fetchone()

        if not emp_user_id:
            raise exceptions.ValidationError(
                _('No Sales Person Found'))


        if claim_id:
            cr.execute("SELECT id, team_id FROM sale_order WHERE claim_id = '{}'".format(claim_id))
            sale_order = cr.fetchone()

            if not sale_order:
                raise exceptions.ValidationError(
                _('Sales Order still pending for approval'))

            so_id = sale_order[0]

        if not so_id:
            raise exceptions.ValidationError(
                _('Sales Order not found'))

        so_obj = self.env['sale.order'].browse(so_id)

        for payment_line in so_obj.c_add_payment_details:
            if not payment_line.receipt_pic:
                payment_line.write({'receipt_pic': receipt_pic, 'receipt_pic_name': receipt_pic_name})
                break

        return True

    @api.model
    def updatePaymentDetails(self, data):
        transactionId = data.get('transactionId', '')
        paidAmount = data.get('paidAmount', 0)
        SalesOrderId = data.get('SalesOrderId', 0)
        SubscriptionId = data.get('SubscriptionId', 'Null')
        paymentType = data.get('paymentType', 'online_transfer')
        chequePic = data.get('chequePic', '')
        receiptPic = data.get('receiptPic', '')
        chequeNum = data.get('chequeNum', '')
        receiptNum = data.get('receiptNum', '')
        onlineTransactionType = data.get('onlineTransactionType', '')
        bankName = data.get('bankName', '')
        chequeDate = data.get('paymentDate', '')
        bank_id = 'Null'

        self.env.cr.execute("SELECT id FROM res_bank WHERE name = '{}' LIMIT 1".format(bankName))
        bank = self.env.cr.fetchone()
        if bank:
            bank_id = bank[0]

        self.env.cr.execute("INSERT "
                            "INTO "
                            "ouc_additional_payment_details "
                            "(downpay_type, payment_status, payment_method, transfer_ref_number, amount, "
                            "sale_order_id, subscription_id, cheque_pic_name, receipt_pic_name, cheque_number, "
                            "receipt_number, bifurcation, bank_id, cheque_date) "
                            "VALUES ('not_emi', True, '{}', '{}', {}, {}, {}, '{}', '{}', '{}', '{}', '{}', {}, '{}')"
                            .format(paymentType, transactionId, paidAmount, SalesOrderId, SubscriptionId,
                                    chequePic, receiptPic, chequeNum, receiptNum, onlineTransactionType, bank_id, chequeDate))
        return True

    #=================================getLeadDetails======================================

    @api.model
    def getLeadDetails(self, data):
        cr = self.env.cr
        emailId = data.get('emailId', '')
        cr.execute("SELECT id FROM res_users WHERE login = '{}'".format(emailId))
        user = cr.fetchone()
        if not user:
            raise exceptions.ValidationError(
                _('No Sales Person Found'))
        user_id = user[0]

        cr.execute("SELECT cm.name, "
                   "cm.partner_name AS company_name, "
                   "cm.email_from AS company_email, "
                   "cm.mobile, "
                   "cm.street, "
                   "cm.street2,"
                   "cm.zip AS pincode, "
                   "(SELECT name FROM ouc_city WHERE id = cm.c_city_id) AS city,"
                   "(SELECT name FROM res_country_state WHERE id = cm.state_id) AS state,"
                   "(SELECT name FROM res_country WHERE id = cm.country_id) AS country,"
                   "(SELECT name FROM crm_lead_tag tag "
                   "INNER JOIN crm_lead_tag_rel tag_rel ON tag_rel.tag_id = tag.id "
                   "WHERE tag_rel.lead_id = cm.id LIMIT 1) AS business_category,"
                   "(SELECT name FROM ouc_fptag WHERE lead_id = cm.id LIMIT 1) AS fptag,"
                   "cm.type,"
                   "cm.c_quotation_created,"
                   "cm.id AS opp_id "
                   "FROM crm_lead cm "
                   "WHERE user_id = {}".format(user_id))
        lead_details = cr.dictfetchall()
        return lead_details

    @api.model
    def scheduleMeetingInERP(self, data):
        cr = self.env.cr
        opportunityRef = data.get('opportunityRef', '')
        subject = data.get('subject', opportunityRef)
        startDateTime = data['startDateTime']
        stopDatetime = data['stopDatetime']


        cr.execute("SELECT id, user_id FROM crm_lead WHERE name = '{}'".format(opportunityRef))
        opp = cr.fetchone()
        if not opp:
            raise exceptions.ValidationError(
                _('No Lead/HotProspect Found'))
        opportunity_id = opp[0]
        user_id = opp[1]

        values = {'opportunity_id': opportunity_id,
                  'name': subject,
                  'start_datetime': startDateTime,
                  'stop_datetime': stopDatetime,
                  'start': startDateTime,
                  'stop': stopDatetime,
                  'user_id': user_id
                  }

        calendar_id = self.env['calendar.event'].create(values)
        return calendar_id.id

    @api.model
    def getAllScheduleMeeting(self, data):
        cr = self.env.cr
        opportunityRef = data.get('opportunityRef', '')

        cr.execute("SELECT id FROM crm_lead WHERE name = '{}'".format(opportunityRef))
        opp = cr.fetchone()
        if not opp:
            raise exceptions.ValidationError(
                _('No Lead/HotProspect Found'))
        opportunity_id = opp[0]

        cr.execute("SELECT id, name AS subject, "
                   "c_is_meeting_done AS loggedStatus, "
                   "start, "
                   "stop, "
                   "duration,"
                   "c_demo_type AS demo_type, "
                   "c_contact_status AS contact_status, "
                   "c_meeting_type AS meeting_type, "
                   "c_meeting_status AS status_after_meeting, "
                   "meeting_done AS meeting_with_bm, "
                   "(SELECT name FROM ouc_fptag WHERE id = c_fptag) AS fptag, "
                   "description FROM calendar_event WHERE opportunity_id = {}".format(opportunity_id))

        scheduleMeetingDetails = cr.dictfetchall()
        return scheduleMeetingDetails

    @api.model
    def rescheduleMeetingInERP(self, data):
        cr = self.env.cr
        startDateTime = data['startDateTime']
        stopDatetime = data['stopDatetime']
        scheduleMeetingId = data['scheduleMeetingId']

        values = {
                  'start_datetime': startDateTime,
                  'stop_datetime': stopDatetime,
                  'start': startDateTime,
                  'stop': stopDatetime
                  }

        calendar_id = self.env['calendar.event'].browse(scheduleMeetingId)
        res = calendar_id.write(values)
        return res

    @api.model
    def log_a_meeting(self, data):
        cr = self.env.cr
        calendar_id = data['calendar_id']
        demo_type = data['demo_type']
        contact_status = data['contact_status']
        status_after_meeting = data['status_after_meeting']
        meeting_with_bm = data['meeting_with_bm']
        fptag = data['fptag']
        description = data['description']

        fp_id = False

        calendar_obj = self.env['calendar.event'].browse(calendar_id)

        if calendar_obj.c_is_meeting_done:
            raise exceptions.ValidationError(_('Meeting Already Logged'))

        opp = calendar_obj.opportunity_id
        opp_id = opp.id
        if opp.meeting_count == 1:
            meeting_type =  'new'
        else:
            meeting_type = 'Follow up'

        if fptag:
            self.env.cr.execute("SELECT id FROM ouc_fptag WHERE name = '{}' AND lead_id = {}".format(fptag, opp_id))
            fp_id = self.env.cr.fetchone()
            if fp_id:
                fp_id = fp_id[0]
            else:
                self.env.cr.execute("SELECT id FROM ouc_fptag WHERE name = '{}'".format(fptag))
                fp_id = self.env.cr.fetchone()
                if fp_id:
                    fp_id = fp_id[0]

        values = {
            'c_is_meeting_done': True,
            'demo_type': demo_type,
            'contact_status': contact_status,
            'c_meeting_status': status_after_meeting,
            'meeting_done': meeting_with_bm,
            'c_fptag': fp_id,
            'meeting_description': description,
            'c_meeting_type': meeting_type,
            'no_otp': True
        }

        wiz_meeting_id = self.env['ouc.meeting.wizard'].\
            with_context(active_model =  'calendar.event', active_id = calendar_id).create(values)
        wiz_meeting_id.creating_meeting_button()
        return True


    #generate quotation API
    @api.model
    def generateQuotation(self, data):
        packages = []

        opp_id = self.env['crm.lead'].browse(data["hotProspectId"])

        if opp_id.type != 'opportunity':
            raise exceptions.ValidationError(_('Quotation can be created only from hotprosepct'))

        if opp_id.c_quotation_created:
            raise exceptions.ValidationError(_('Quotation already created!'))

        partner = opp_id.partner_id
        if not partner.id:
            raise exceptions.ValidationError(_('No Partner found'))

        tdsPercentage = data.get("tdsPercentage", 0)
        gstn = data.get("gstn", False)
        template_id = data.get("template_id", 1)

        for val in data['packages']:
            prod_id = val["product_id"]
            product_id = self.env['product.product'].search([('id', '=', prod_id)])
            if not product_id:
                raise exceptions.ValidationError(
                    _('No Product found!'))
            if val["discount"] > 10:
                raise exceptions.ValidationError(
                    _('Default discount cannot be greater than 10%'))
            packages.append({
                "product_id": product_id[0],
                "discount": val["discount"],
                "quantity": val["quantity"],
                "fptag_id": val['fptag_id']
            })

        opp_id.c_quotation_created = True
        opp_id.action_set_won()

        return self.create_quotation(partner, opp_id, packages, tdsPercentage, gstn, template_id)

    # Create Quotation
    @api.model
    def create_quotation(self, partner, opp_id, packages, tdsPercentage, gstn, template_id):

        user_id = opp_id.user_id and opp_id.user_id.id or self.env.uid
        lc_id = opp_id.c_lead_creator_id and opp_id.c_lead_creator_id.id or self.env.uid

        team_id = self.env['crm.team'].search([('name', '=', 'FOS')], limit=1)
        team_id = team_id and team_id.id or False

        note = ''
        if tdsPercentage:
            note = 'TDS - ' + str(tdsPercentage) + '%'

        pricelist_id = partner.property_product_pricelist and partner.property_product_pricelist.id or 1

        quote_type = 'new'
        subscription_id = False
        subscription = self.env['sale.subscription'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if subscription:
            quote_type = 'new'
            subscription_id = subscription.id

        template = self.env['sale.subscription.template'].browse(template_id)
        auto_create_fptag = template.c_auto_create_fptag

        addr = partner.address_get(['delivery', 'invoice'])
        fpos_ids = self.env['account.fiscal.position'].get_fiscal_position(partner.id, partner.id)
        order_lines = [(0, False, {'product_id': rec['product_id'].id,
                                   'name': rec['product_id'].name,
                                   'c_fptags_id': rec['fptag_id'] if not auto_create_fptag else False,
                                   'price_unit': rec['product_id'].list_price or 0.0,
                                   'product_uom_qty': rec['quantity'] or 1.0,
                                   'c_pkg_validity': rec['product_id'].c_validity,
                                   'c_max_discount': rec['discount'] or 0.0,
                                   'discount': rec['discount'] or 0.0,
                                   'c_status': quote_type,
                                   'c_fptag_not_required': True if auto_create_fptag else False
                                   }) for rec in packages]

        vals = {
            'pricelist_id': pricelist_id,
            'partner_id': partner.id,
            'c_company_name': partner.name,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'c_quotation_type': quote_type,
            'order_line': order_lines,
            'fiscal_position_id': fpos_ids,
            'user_id': user_id,
            'team_id': team_id,
            'payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
            'c_lead_source_id': opp_id.c_lead_source_id and opp_id.c_lead_source_id.id or False,
            'c_lead_creator_id': lc_id,
            'opportunity_id': opp_id and opp_id.id or False,
            'template_id': template_id,
            'c_gstin_reg': 'Yes' if gstn else 'No',
            'x_gstin': gstn,
            'state': 'draft',
            'confirmation_date': fields.Date.context_today(self),
            'note': note,
            'c_auto_create_fptag': auto_create_fptag
        }
        order = self.env['sale.order'].create(vals)
        order._compute_tax_id()

        return {'QuotationId': order.id, 'Quotation': order.name, 'taxAmount': order.amount_tax,
                'unaxAmount': order.amount_untaxed,'totalAmount': order.amount_total}

    @api.model
    def sendQuotation(self, data):

        order_id = data.get("orderId", False)
	if not order_id:
	   return False
        so_obj = self.env['sale.order'].browse(order_id)
        template = so_obj.contract_template
        auto_create_fptag = template.c_auto_create_fptag
        so_obj.state = 'sent'

        template_name = 'MLC Sales Order - Send by Email' if auto_create_fptag else 'Sales Order - Send by Email'
        template = self.env['mail.template'].search([('name', '=', template_name)], limit=1)
        if template:
            mail_id = template.send_mail(order_id)
            self.env['nf.ria.email'].send_exteral_email({'mail_ids': [mail_id]})
        return True

    @api.model
    def getSubcriptionTemplate(self):
        template = self.env['sale.subscription.template'].search_read([('presale', '!=', True)], ['code','name', 'c_auto_create_fptag'], order='name')
        return template

    @api.model
    def getTemplateProduct(self, data):
        template_id = data.get('template_id', False)
        template = self.env['sale.subscription.template'].browse(template_id)
        if not template:
            raise exceptions.ValidationError(_('Please select template'))

        result = [{'product':val.product_id.name,
                   'product_id': val.product_id.id,
                   'unitPrice': val.product_id.list_price,
                   'max_default_discount': val.c_max_discount,
                   'default_minimum_qty': val.quantity
                   } for val in template.subscription_template_line_ids]
        return result

    @api.model
    def getFptags(self, data):
        result = []
        res = {}
        opp_id = data.get('hotProspectId', False)
        opp = self.env['crm.lead'].browse(opp_id)
        partner_id = opp.partner_id and opp.partner_id.id or False
        if not partner_id:
            raise exceptions.ValidationError(_('Partner does not exist for HotProspect %s'%(opp.name)))

        fp_ids = map(lambda x: x.id, opp.c_fptags_ids)
        if fp_ids:
            self.env.cr.execute("UPDATE "
                                "ouc_fptag "
                                "SET customer_id = {}, state = 'valid' "
                                "WHERE id = ANY(ARRAY{})"
                                .format(partner_id, fp_ids))

        self.env.cr.execute("SELECT "
                            "name, "
                            "id "
                            "FROM ouc_fptag "
                            "WHERE customer_id = {} AND name IS NOT NULL"
                            .format(partner_id))
        fptags = self.env.cr.fetchall()

        for val in fptags:
            res.update({str(val[0]): val[1]})
        result.append(res)
        return result

    @api.model
    def markSalesOrderCancel(self, data):
        so_numbers = data.get('SalesOrderRef', [])

        cr = self.env.cr

        so_numbers = map(lambda x: x.encode('utf-8'), so_numbers)

        cr.execute("SELECT id FROM sale_order WHERE name = ANY(ARRAY{})".format(so_numbers))
        so_ids = cr.fetchall()

        if not so_ids:
            raise exceptions.ValidationError(_('Sales Order Not Found'))

        so_ids = map(lambda x: x[0], so_ids)

        cr.execute("SELECT id FROM sale_subscription_line WHERE c_sale_order_id = ANY(ARRAY{}) AND c_invoice_id IS NOT NULL".format(so_ids))
        contract_line_ids = cr.fetchall()
        if contract_line_ids:
            raise exceptions.ValidationError(_('Tax invoice been raised for S.O.'))

        str_sql1 = "DELETE " \
                  "FROM " \
                  "sale_subscription_line " \
                  "WHERE c_sale_order_id = ANY(ARRAY{}) " \
                  "AND c_invoice_id IS NULL AND c_sale_order_id IS NOT NULL"\
            .format(so_ids)

        cr.execute(str_sql1)

        str_sql2  = "UPDATE " \
                    "sale_order " \
                    "SET state = 'cancel' " \
                    "WHERE id = ANY(ARRAY{})"\
            .format(so_ids)

        cr.execute(str_sql2)

        return True

    @api.model
    def update_mib_status(self, data):
        cr = self.env.cr

        so_id = data.get('SalesOrderId', False)
        mibStatus = data.get("mibStatus", 0)
        invoice_id = data.get('invoiceId', False)

        mib_status = mib_enum[mibStatus]

        if not so_id:
            raise exceptions.ValidationError(_('Sales Order ID Not Found'))

        cr.execute(
            "SELECT id, analytic_account_id FROM sale_subscription_line WHERE c_sale_order_id = {}"
                .format(so_id))
        contract_line_ids = cr.fetchone()
        if not contract_line_ids:
            raise exceptions.ValidationError(_('No Sales Order found'))

        contract_id = contract_line_ids[1]

        mib_hold_issue = ''
        if mib_status == 'Hold':
            mib_hold_issue = 'S.O. Without Attachment'
        elif mib_status == 'Yes':
            mib_hold_issue = 'No Issue'

        c_rta_hold_description = ''
        if mib_hold_issue == 'S.O. Without Attachment':
            c_rta_hold_description = 'S.O. Without Attachment'

        cr.execute(
            "UPDATE sale_subscription SET c_sales_order_id = {}, "
            "c_rta_hold_issue = '{}', c_rta_hold_description = '{}' "
            "WHERE id = {}"
                .format(so_id, mib_hold_issue, c_rta_hold_description, contract_id))


        str_sql = "UPDATE sale_order SET mib_status = '{}', mib_hold_issue = '{}' "\
            .format(mib_status, mib_hold_issue)
        where_clause = "WHERE id = {}".format(so_id)

        if invoice_id:
            if mibStatus in (0, 1):
                raise exceptions.ValidationError(_('Invoice Already Created'))

            str_sql = str_sql + ",inv_status = 'Activation done & Invoice Created', sub_inv_id = {} "\
                .format(invoice_id)

        str_sql = "{} {}".format(str_sql, where_clause)

        cr.execute(str_sql)
        return True