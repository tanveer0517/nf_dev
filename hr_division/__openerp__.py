{
    'name' : 'HR Division',
    'version' : '1.1',
    'author' : 'OpenERP4You',
    'category' : 'Human Resources',
    'description' : """
By using this application you can maintain Human Resource (HR) which includes HR Division
====================================
""",
    'summary':"""Division for Human Resource""",
    'website': 'https://www.openerp4you.com',
    'depends' : ['hr'],
    'data': [
        
        'security/ir.model.access.csv',
        'division.xml',
        
    ],
    'qweb' : [
       
    ],
    'demo': [
       
    ],
    'test': [
       ],
    'installable': True,
    'auto_install': False,
    'application':True
}