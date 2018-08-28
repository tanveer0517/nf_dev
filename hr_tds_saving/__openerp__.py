# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'HR TDS Saving',
    'version': '1.1',
    'author': 'OpenERP4You',
    'category': 'Payroll',
    'sequence': 21,
    'website': 'https://www.openerp4you.com',
    'summary': 'Hr TDS Saving',
    'description': """
Tax Saving Declaration
==========================

This application enables you to manage employees tax and saving declaration for tds computation.
    """,
    
    'depends': ['hr','hr_payroll'],
    'data': [
            'security/ir.model.access.csv',
            'wizard/nf_payroll_finance_wizard_view.xml',
            'wizard/payroll_components_approve_view.xml',
            'hr_tds_saving_view.xml',            
               ],
    'demo': [],
    'test': [
        
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
