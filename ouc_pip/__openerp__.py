{
    'name': 'PIP Process',
    'version': '1.1',
    'author': 'OpenERP4You',
    'category': 'custom',
    'website': 'https://www.openerp4you.com',
    'summary': 'PIP process',
    'description': """
    PIP process in NowFloats
    """,
    'depends': ['hr','employee_master'],
    'data': [
             'nf_pip_view.xml',
             'security/ir.model.access.csv',
             'security/security.xml'
             ],
    'demo': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}