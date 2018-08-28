
{
    'name' : "NowFloats Integration",
    'version' : "1.0",
    'author' : "Mohit Kumar",
    'category' : "Integration",
    'depends' : ['crm'],
    'data' : [
                'security/security.xml',
                'security/ir.model.access.csv',
                'views/nf_biometric_view.xml',
                'views/nf_exotel_view.xml',
                'views/nf_tableau_view.xml'
             ],
    'installable': True,
}
