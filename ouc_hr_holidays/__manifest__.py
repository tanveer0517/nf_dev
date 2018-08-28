# -*- coding: utf-8 -*-
# ©  2015 2011,2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'HR Public Holidays',
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'category': 'hr holidays',
    'author': "Openerp4you",
    'summary': "Manage Public and Rest days Holidays",
    'website': 'http://miketelahun.wordpress.com',
    'depends': [
        'hr',
        'hr_holidays',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_public_holidays_view.xml',
        'views/rest_days_view.xml'
    ],
    'installable': True,
}
