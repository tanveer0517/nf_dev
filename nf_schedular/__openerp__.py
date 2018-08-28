{
    'name' : 'NF Cron Job',
    'version' : '1.1',
    'author' : 'OpenERP4You',
    'category' : 'NF Cron Job',
    'description' : """
This Module is for running cron job
====================================
""",
    'summary':"""NF Schedular""",
    'website': 'https://www.openerp4you.com',
    'depends' : [],
    'data': [
        'security/ir.model.access.csv',
        'nf_schedular_view.xml',
        
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