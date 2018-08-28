from odoo import models, fields, api, _
from openerp.osv import osv
from datetime import datetime
import time
from odoo.exceptions import UserError, ValidationError
from openerp import SUPERUSER_ID

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib2 import Request, urlopen
import json,urllib,urllib2
from dateutil.relativedelta import relativedelta
import requests
from pprint import pprint
from lxml import etree

FOS_Desig = ('Associate - FOS','Consultant - FOS','Principal Consultant - FOS','Senior Consultant - FOS','Associate Product Specialist','Principal Product Specialist','Product Specialist','Senior Product Specialist','Associate - Customer First','Consultant - Customer First','Principal Consultant - Customer First','Senior Consultant - Customer First','Associate - Verticals','Consultant - Verticals','Principal Consultant - Verticals','Senior Consultant - Verticals')

Tele_Desig = ('Associate - Tele Sales','Consultant - Tele Sales','Principal Consultant - Tele Sales','Senior Consultant - Tele Sales')

BM_Desig = ('Branch Manager','Regional Manager','Store Manager','Cluster Manager','Sales Manager','Team Lead - FOS')

class nf_open_url(osv.TransientModel):
    _name = "nf.open.url"
    _description = "NF Open URL"

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self.env.context
        uid = self.env.uid
        cr = self.env.cr
        if context is None:context = {}
        res = super(nf_open_url, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if view_type == 'form':
            str_sql = "SELECT emp.intrnal_desig FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.user_id = {}".format(uid)
            cr.execute(str_sql)
            emp_desig = cr.fetchone()
            if emp_desig:
                emp_desig = emp_desig[0]
                if emp_desig in FOS_Desig:
                    res['arch'] = """<form string="Open URL" create="false" edit="false">
                                       <iframe src="https://dub01.online.tableau.com/t/nowfloats/views/FOSIndividual/Overview?paramuserid="""+str(uid)+"""&amp;:embed=y&amp;:showShareOptions=true&amp;:display_count=no&amp;:showVizHome=no&amp;:toolbar=no" width="1250" height="1000"/>
                                     </form>"""
                elif emp_desig in Tele_Desig:
                    res['arch'] = """<form string="Open URL" create="false" edit="false">
                                       <iframe src="https://dub01.online.tableau.com/t/nowfloats/views/TeleIndividual/Overview?paramuserid="""+str(uid)+"""&amp;:embed=y&amp;:showShareOptions=true&amp;:display_count=no&amp;:showVizHome=no&amp;:toolbar=no" width="1250" height="1000"/>
                                     </form>"""
                else:
                    res['arch'] = """<form string="Open URL" create="false" edit="false">
                                        <iframe src="https://sites.google.com/a/nowfloats.com/nfmis/fos/fosbranch" width="1250" height="1000"/>
                                     </form>"""

        return res

class nf_attendence_url(osv.TransientModel):
    _name = "nf.attendence.url"
    _description = "NF Attendence"

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self.env.context
        uid = self.env.uid
        cr = self.env.cr
        if context is None:context = {}
        res = super(nf_attendence_url, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,submenu=False)
        if view_type == 'form':
            str_sql = "SELECT job.name FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id LEFT JOIN hr_job job ON emp.job_id = job.id " \
                      "WHERE res.user_id = {}".format(uid)
            cr.execute(str_sql)
            emp_desig = cr.fetchone()
            if emp_desig:
                emp_desig = emp_desig[0]
                if emp_desig in FOS_Desig:
                    res['arch'] = """<form string="Open URL" create="false" edit="false">
                                       <iframe src="https://dub01.online.tableau.com/t/nowfloats/views/FOSIndiAttendance/Overview?paramuserid="""+str(uid)+"""&amp;:embed=y&amp;:showShareOptions=true&amp;:display_count=no&amp;:showVizHome=no&amp;:toolbar=no" width="1250" height="1000"/>
                                     </form>"""

                elif emp_desig in Tele_Desig:
                    res['arch'] = """<form string="Open URL" create="false" edit="false">
                                       <iframe src="https://dub01.online.tableau.com/t/nowfloats/views/TeleIndiAttendance/Overview?paramuserid="""+str(uid)+"""&amp;:embed=y&amp;:showShareOptions=true&amp;:display_count=no&amp;:showVizHome=no&amp;:toolbar=no" width="1250" height="1000"/>
                                     </form>"""

                elif emp_desig in BM_Desig:
                    res['arch'] = """<form string="Open URL" version="7.0" create="false" edit="false">
                                       <iframe src="https://dub01.online.tableau.com/t/nowfloats/views/BMIndiAttendance/Overview?paramuserid="""+str(uid)+"""&amp;:embed=y&amp;:showShareOptions=true&amp;:display_count=no&amp;:showVizHome=no&amp;:toolbar=no" width="1250" height="1000"/>
                                     </form>"""

                else:
                    res['arch'] = """<form string="Open URL" create="false" edit="false">
                                        <iframe src="https://nowfloatsmis.com" width="1250" height="1000"/>
                                     </form>"""

        return res



