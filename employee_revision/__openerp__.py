{
    'name' : 'Employee Revision',
    'version' : '1.1',
    'author' : 'OpenERP4You',
    'category' : 'Human Resource',
    'description' : """
By using this application you can maintain Human Resource (HR) which includes HR Employee Revision .
====================================
""",
    'website': 'https://openerp4you.in',
    'depends' : ['base_setup','hr','hr_division'],
    'data': [
        'security/ir.model.access.csv',
        'views/employee_revision.xml',
        'views/hr_employee.xml',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
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