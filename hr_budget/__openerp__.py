{
    'name' : 'Budget',
    'version' : '1.1',
    'author' : 'OpenERP4You',
    'category' : 'Human Resources',
    'description' : """
By using this application you can maintain Human Resource (HR) which includes HR Budgets and Requisition 
 i.e Number of Employees to onboard.
====================================
""",
    'summary':"""Budget and Requisition for Human Resource""",
    'website': 'https://www.openerp4you.com',
    'depends' : ['base_setup','hr','base','hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'security/sequence.xml',
        'security/security.xml',
        'wizard/wiz_resign_view.xml',
        'views/hr_budget_view.xml',
        'views/hr_job.xml',
        'views/doc_scheduler.xml',
        'views/sequence.xml',
        
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