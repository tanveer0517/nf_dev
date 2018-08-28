import psycopg2
import StringIO
import cStringIO
import os
import functools
import xmlrpclib
from openerp import api,exceptions
from datetime import datetime
import csv
import math
from openerp.osv import osv
from odoo import api, fields, models, _, SUPERUSER_ID
import datetime
import calendar
import json
import random
import urllib2

class nf_import(models.Model):
    _name='nf.import'
    
    def import_hr_employee(self):
        
#         def json_rpc(url, method, params):
#             data = {
#                 "jsonrpc": "2.0",
#                 "method": method,
#                 "params": params,
#                 "id": random.randint(0, 1000000000),
#             }
#             req = urllib2.Request(url=url, data=json.dumps(data), headers={
#                 "Content-Type":"application/json",
#             })
#             reply = json.load(urllib2.urlopen(req))
#             if reply.get("error"):
#                 raise Exception(reply["error"])
#             return reply["result"]
#         
#         def call(url, service, method, *args):
#              return json_rpc(url, "call", {"service": service, "method": method, "args": args})
#             
#         HOST = "erp.nowfloats.com"
#         url = "http://%s/jsonrpc" % (HOST)
#         DB = "NowFloats"
#         USER = "erp"
#         PASS = "erp"
#             
#         uid = call(url, "common", "login", DB, USER, PASS)
#         print"==========uid========",uid
#         
#         nf_users = call(url, "object", "execute", DB, uid, PASS, 'res.users', 'search_read',[])
#         print"====nf_users====",nf_users
        
#         name_related,work_email,user_id,work_phone,date_of_join,emp_id,nf_branch_address,nf_sale_channel,job_id
#         inter_desig,nf_emp_father,nf_emp_sht,gender,marital,birthday,pers_email,currnt_addr,permt_addr
#         identification_id,otherid,pan,alt_cont
        
        cursor.execute("select emp.work_email,emp.mobile_phone,emp.emp_id,(select emp_id from hr_employee where id = emp.parent_id) As manager,\
        (select emp_id from hr_employee where id = emp.nf_emp_head) As reporting_head from hr_employee As emp where (select active from resource_resource where id = emp.resource_id) = True and emp.id not in (203,7343,7673,6912,7652) and emp.date_of_join is not null")
         
        temp = cursor.fetchall()
        i = 0
        lst = []
        for val in temp:
            i += 1
            vals = {
                   'work_phone':val[1],
                   'parent_id':self.env['hr.employee'].search([('nf_emp','=',val[3])]) and self.env['hr.employee'].search([('nf_emp','=',val[3])]).id or False,
                   'coach_id':self.env['hr.employee'].search([('nf_emp','=',val[4])]) and self.env['hr.employee'].search([('nf_emp','=',val[4])]).id or False,     
                }
            self.env['hr.employee'].search([('nf_emp','=',val[2])]).write(vals)
        return True
    

        
    
    