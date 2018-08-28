{
    'name': 'NF Helpdesk',
    'version': '1.1',
    'author': 'NowFloats',
    'category': 'custom',
    'website': 'https:/nowfloats.com',
    'summary': 'NF Helpdesk',
    'description': """
    NF Helpdesk
    """,
    'images': [],
    'depends': ['helpdesk'],
    'data': [
	     'security/security.xml',
	     'security/ir.model.access.csv',
         'nf_helpdesk_view.xml',
         'sequence.xml',
             ],
    'demo': [],
    'test': [
        
    ],
    'installable': True,
    'application': True,
    'auto_install': False,

}
