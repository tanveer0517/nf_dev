from odoo import api, fields, models, _
from email import _name

class hr_division(models.Model):
    _name="hr.division"
    _description = "HR Division"
    
    name = fields.Char(string='Division')
    dept_id = fields.Many2one('hr.department','Departments')
    
    
class HrBranch(models.Model):
    _name="hr.branch"
    
    def default_country(self):
        return self.env['res.country'].search([('name','=','India')])
    
    name=fields.Char(string='Branch')
    street = fields.Char(string='Address')  
    street2 = fields.Char(string='Address')
    zip = fields.Char(string='ZIP')
    c_city_id= fields.Many2one('ouc.city', string='City')
    city = fields.Char(string='City', related='c_city_id.name')
    state_id = fields.Many2one('res.country.state', string='State', related='c_city_id.state_id')
    country_id = fields.Many2one('res.country', string='Country', related='c_city_id.country_id')

    phone = fields.Char(string='Phone')
    fax = fields.Char(string='Fax')
    email = fields.Char(string='Email')   
    website = fields.Char(string='Website')
    manager_id = fields.Many2one('hr.employee','Manager')
    tl_manager_id = fields.Many2one('res.users','TL Manager')
    branch_hr_id = fields.Many2one('hr.employee','HR')
    active_branch_id = fields.Many2one('hr.branch', 'Active or Replaced Branch')
    server_branch_id = fields.Char('Server Branch ID')
    rm_id = fields.Many2one('hr.employee','Regional Manager')
    virtual_branch_id = fields.Many2one('hr.branch', string='Virtual Branch')

    @api.multi
    def write(self,vals):
        street=vals.get('street',False) or self.street
        street2=vals.get('street2',False) or self.street2
        city=vals.get('c_city_id',False) or self.c_city_id.id
        zip=vals.get('zip',False) or self.zip
        self.env.cr.execute('UPDATE hr_employee SET street=%s,street2=%s,q_city_id=%s,zip=%s where branch_id=%s',(street,street2,city,zip,self.id,))
        res = super(HrBranch, self).write(vals)
        return True
    
class CountryCode(models.Model):
    _name='country.code'      
    
    country_id = fields.Many2one('res.country',string='Country')
    name = fields.Char(string='Code')


class ouc_city(models.Model):
    _name = 'ouc.city'

    name = fields.Char(string='City Name', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    active = fields.Boolean(string='Active', default=True)

    
    
    