from odoo import api, fields, models, _
from email import _name

class hr_lease(models.Model):
    _name = 'hr.lease'
     
    name = fields.Char(string = 'Name')
    employee_no = fields.Char(string = 'Employee No.')
    employee_name = fields.Char(string = 'Employee Name')
    lease_type = fields.Selection([('1','Individual'),('2','Company'),('3','Partnership')],string = 'Landlord Type')
    owner = fields.Selection([('N','Self Lease'),('NR','Near Relative'),('C','Company Accomodation'),('Y','Company 	Lease')],string = 'Ownership Type')
    area = fields.Float(string = 'Flat Area')
    address = fields.Char(string = 'Address')
    rent = fields.Float(string = 'Actual Rent Amount')
    special_lease_amount = fields.Float(string = 'Special Lease Amount')
    from_date = fields.Date(string = 'Lease Start Date')
    to_date = fields.Date(string = 'Lease End Date')
    lease_share = fields.Float(string = 'Lease Share')
    lease_notes = fields.Text(string = 'Notes')
    brokerage_charge = fields.Float(string = 'Brokerage Charge')
    

