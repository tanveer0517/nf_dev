{
    'name' : 'Employee MASTER',
    'version' : '1.1',
    'author' : 'OpenERP4You',
    'category' : 'Human Resource',
    'description' : """
By using this application you can maintain Human Resource (HR) which includes HR Employee Contracts .
====================================
""",
    'website': 'https://openerp4you.in',
    'depends' : ['base_setup','hr','hr_contract'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/wiz_emp_joindate_view.xml',
        'views/employee_master.xml',
        'wizard/wiz_employee_information.xml',
        
    ],
    'qweb' : [
       
    ],
    'demo': [
       
    ],
    'test': [
       ],
    'installable': True,
    'auto_install': False,
    'application':True,
}