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
    'name': 'Hr Leave Extend',
    'version': '1.0',
    'category': 'Human Resource',
    'sequence': 38,
    'description': """
Human Resource Management system.
=======================

    * Employee Leave Request
    * Employee Leave Allocation
    * Employee Leave Credit
    * Employee Leave Balance Update
    * Employee Leave Encashment
    """,
    'author': 'OpenERP4You',
    'website': 'http://www.openerp4you.com',
    'images': [
    ],
    'depends': [
        'hr','hr_holidays','hr_extend'
    ],
    'data': [
        'security/ir.model.access.csv',     
        'hr_payroll_leave.xml',
        'data/mail_template_data.xml',
        'report/nf_hr_leave_report.xml'     
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
