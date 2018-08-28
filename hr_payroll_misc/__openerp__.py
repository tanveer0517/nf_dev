#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'Payroll Misc Payment',
    'version': '1.0',
    'category': 'Payroll',
    'sequence': 38,
    'description': """
Generic Payroll system.
=======================

    * Payroll Misc Payment
    """,
    'author': 'OpenERP4You',
    'website': 'http://www.openerp4you.com',
    'images': [
    ],
    'depends': ['hr_payroll'],
    'data': [
       'security/ir.model.access.csv',      
       'misclaneous_payment_view.xml',        
    ],
    'test': [
    ],
    'demo': [
             ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
