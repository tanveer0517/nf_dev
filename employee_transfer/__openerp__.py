{
    'name' : 'Employee Transfer',
    'version' : '1.1',
    'author' : 'Tanveer',
    'category' : 'Human Resource',
    'description' : """
By using this application you can maintain Human Resource (HR) which includes HR Employee Contracts .
====================================
""",
    'website': 'https://testdemo.in',
    'depends' : ['base_setup','hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/employee_transfer_view.xml'        
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