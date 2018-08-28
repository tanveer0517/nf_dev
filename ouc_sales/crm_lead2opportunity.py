from odoo import fields,models,api, _,SUPERUSER_ID
import re
from odoo import exceptions
from odoo.exceptions import ValidationError
from lxml import etree

class ouc_lead2oppurtunity_partner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    
    # overriding
    name = fields.Selection([('convert', 'Convert to opportunity')], 'Conversion Action', default='convert')
    action = fields.Selection([('exist', 'Link to an existing customer'), ('create', 'Create a new customer')], string='Customers', required=True)    
    
    c_allow_to_create = fields.Boolean('Is Allow to create customer', default=True)
    c_matched_customers = fields.Boolean('Is matching customer exists', default = False)
    
    c_company_name = fields.Char('Name', related='partner_id.name')
    c_company_email = fields.Char('Email', related='partner_id.email')
    c_company_mobile = fields.Char('Mobile', related='partner_id.mobile')
    c_company_city = fields.Char('City', related='partner_id.city')
    
    c_mismatch = fields.Boolean('Mismatch Details', default=False)
    c_mismatch_message = fields.Char('[WARNING]')
    
    @api.multi
    def action_apply(self):
        if not self.partner_id and not self.c_allow_to_create:
            raise exceptions.ValidationError(_('Please select a customer first')) 
        
        # adding contact in company
        if self.partner_id:
            #for existing customer, create a new contact
            active_model = self.env.context.get('active_model')
            obj_id = self.env[active_model].browse(self.env.context.get('active_id'))
            name = obj_id.contact_name
            email = obj_id.c_contact_email
            mobile = obj_id.c_contact_mobile
            parent_id = self.partner_id
            
            if parent_id.parent_id:
                parent_id = parent_id.parent_id
            
            vals = {
                    'name': name,
                    'mobile': mobile,
                    'email': email,
                    'parent_id': parent_id.id,
                    'company_type': 'person',
                    'city': obj_id.c_city_id.name,
                    'mobile': "+{} {}".format(obj_id.c_country_code_2, obj_id.mobile),
                    'state_id': obj_id.city,
                    'country_id': obj_id.country_id,
                    'c_city': obj_id.c_city_id.id
                   }
            res = self.env['res.partner'].create(vals)
            print ">>>>>>>>>>>>>", res
            obj_id.sudo().write({'c_contact_id': res.id})
        
        
        res = super(ouc_lead2oppurtunity_partner, self).action_apply()
        leads = self.env['crm.lead'].sudo().browse(self._context.get('active_ids', []))
        for lead in leads:
            if lead.partner_id:
                print ">????????????????????????????",lead.partner_id.id
                
                # for new making company as a partner and contact person as contact ID
                print "<<<<<<<<<Updating Partner>>>>>>"
                partner_id = lead.partner_id
                parent_partner = partner_id.parent_id
                ph = ''
                if lead.phone:
                    ph = "+{} {}".format(lead.c_country_code_3, lead.phone)
                else:
                    ph = ''
                if parent_partner:
                    parent_partner.sudo().write({
                        'c_city_id' :  lead.c_city_id.id,
                        'mobile': "+{} {}".format(lead.c_country_code_2, lead.mobile),
                        'phone': ph,

                    })
                    lead.sudo().write({
                        'partner_id': parent_partner.id
                    })
                    
                partner_id.sudo().write({
                    'c_city_id' :  lead.c_city_id.id,
                    'mobile': "+{} {}".format(lead.c_country_code_1, lead.c_contact_mobile),
                    'phone': ph,

                })
                
                for fptag in lead.c_fptags_ids:
                    print ">>>>>>>>>>>>>>>", fptag.name
                    fptag.sudo().write({
                        'customer_id': lead.partner_id.id,
                        'state': 'valid'
                    })
                    
                if lead.is_la_lead:
                    lead.partner_id.sudo().write({
                            'c_is_partner': True,
                            'supplier': True,
                            'customer': True,
                            'c_int_lead_ref_id': lead.id
                        })
                    
        return res
      
    @api.onchange('partner_id')
    def matching_customer_name(self):
        leads = self.env['crm.lead'].browse(self._context.get('active_ids', []))
        for lead in leads:
            if not self.c_company_name:
                break;
            
            partner_name = self.c_company_name.lower()
            if self.partner_id.commercial_partner_id:
                self.c_company_name = self.partner_id.commercial_partner_id.name
                if self.partner_id.commercial_partner_id.name:
                    partner_name = self.partner_id.commercial_partner_id.name.lower()
            
            partner_name = partner_name.strip()
            if not lead.partner_name:
                break;
            if lead.partner_name.lower().strip() != partner_name:
                print "Mismatch"
                self.c_mismatch = True
                self.c_mismatch_message = "<h3>[WARNING]</h3><b>Customer name is not matching!!</b><br/>Customer name from lead: <b>'{}'</b><br/>Customer name from selection: <b>'{}'</b>.<br/><br/>Selecting this customer will change the Customer to: <b>'{}'</b>".format(lead.partner_name, self.c_company_name, self.c_company_name)
                return
        self.c_mismatch_message = ""
        self.c_mismatch = False
        
    @api.onchange('c_matched_customers', 'partner_id', 'name')
    def apply_domain_on_partner(self):
        self.name = 'convert'
        if self.c_matched_customers:
            # If already checked once
            return
        print ">>>>>>>>>>>>>>>>>>>>>>>>DOMAIN"
        parent_id = self._context["active_id"]
        parent_model = self.env[self._context["active_model"]].browse(parent_id)
        
        existing_customer = self.existing_customer(parent_model)
        if existing_customer:
            print "?>>>>>>>SURE EXISTING>>>>",existing_customer
            self.c_allow_to_create = False
            self.action = 'exist'
            self.c_matched_customers = True
            return {'domain': {'partner_id': [('id', 'in', existing_customer)]}}
        
        matching_customer = self.matching_customer(parent_model)
        if matching_customer:
            print ">>>>>MAYBE>>>>>"
            self.action = 'exist'
            self.c_matched_customers = True
            self.partner_id = False
            return {'domain': {'partner_id': ['&', ('id', 'in', matching_customer), ('company_type','=','company')]}}
        
        self.partner_id = False
        
    def existing_customer(self, customer_lead):
        company_email = customer_lead.email_from
        company_mobile = customer_lead.mobile
        email = customer_lead.c_contact_email
        mobile = customer_lead.c_contact_mobile
        a=[]
        if customer_lead.email_from and customer_lead.c_contact_email :
            print "=========================1====================="
            self.env.cr.execute("select id from res_partner where customer='t' and (email = %s or mobile = %s or email = %s or mobile = %s) ", [company_email, company_mobile, email, mobile])
            matching_customer = self.env.cr.fetchall()
            a.append(matching_customer)
        if not(customer_lead.email_from and customer_lead.c_contact_email):
            print "=========================12====================="
            self.env.cr.execute("select id from res_partner where customer='t' and (mobile = %s or mobile = %s) ",[company_mobile,mobile])
            matching_customers = self.env.cr.fetchall()
            a.append(matching_customers)
        if customer_lead.email_from and not customer_lead.c_contact_email :
            self.env.cr.execute("select id from res_partner where customer='t' and (email = %s or mobile = %s or mobile = %s) ",[company_email, company_mobile, mobile])
            matching_customers1 = self.env.cr.fetchall()
            a.append(matching_customers1)
        if not customer_lead.email_from and customer_lead.c_contact_email :
            print "=========================1====================="
            self.env.cr.execute("select id from res_partner where customer='t' and ( mobile = %s or email = %s or mobile = %s) ", [ company_mobile, email, mobile])
            matching_customer = self.env.cr.fetchall()
            a.append(matching_customer)
        if a:
            return a[0]
        return False

    def matching_customer(self, customer_lead):
        matching_customers = []
        print "=========================1====================="
        self.env.cr.execute("select id from res_partner where customer='t' and name = %s",[customer_lead.contact_name])
        matching_customer = self.env.cr.fetchall()
        if matching_customer:
            matching_customers.append(matching_customer[0])
            
        print "=========================1====================="
        self.env.cr.execute("select id from res_partner where customer='t' and name = %s",[customer_lead.partner_name])
        matching_company = self.env.cr.fetchall()
        if matching_company:
            matching_customers.append(matching_company[0])

        if matching_customers:
            print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",matching_customers
            list_of_matched = [ids[0] for ids in matching_customers]
            return list_of_matched
        return False


    def action_new_customer(self):
        self.action = 'create'
        return self.action_apply()

    def _find_matching_partner(self):
        return False
     
