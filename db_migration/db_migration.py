from odoo import api, models, fields, _, SUPERUSER_ID
from dateutil.relativedelta import relativedelta
import datetime
import psycopg2
import json

class ouc_db_migration(models.Model):
    _name = "ouc.dbmigration"
    
    db_host = fields.Char("DB Host")
    db_port = fields.Char("DB Port")
    db_name = fields.Char("DB Name")
    db_user = fields.Char("DB User")
    db_passwd = fields.Char("Password")
    job_name = fields.Char("Job Name")
    job_description = fields.Char("Description")
    
    log_field = fields.Text("LOGS", default=" ")
    
    _rec_name = 'job_name'
    
    table_ids = fields.One2many('ouc.table_update', 'db_id', string='Table Operation')
    
    def execute_job(self):
        print "Connecting......"
        
        dbname = self.db_name
        user = self.db_user
        password = self.db_passwd
        host = self.db_host
        port = self.db_port
        
        print "Hello"
        
        conn = ''
        
        try:
            conn = psycopg2.connect(database=dbname, user=user, password=password, host=host, port=port)
            print "Established"
            
        except:
            print "I am unable to connect to the database."
        
        cur = conn.cursor()
        
        if not self.log_field:
            self.log_field = "-----------------------------"
        
        for table_op in self.table_ids:
            clause = table_op.query
            if table_op.operation == 'query':
                self.log_field = "[INFO-LOCAL] Executing query: %s \n%s" % (clause,self.log_field)
                self.env.cr.execute(clause)
                continue
            
            source_table = table_op.source_table
            destination_table = table_op.table_name
            all_columns = self.convert_to_dictionary(table_op.column_mapping)
            
            if table_op.operation == 'sync':
                self.sync_data(cur, source_table, destination_table, all_columns, clause)
                continue
            
            self.migrate_data(cur, source_table, destination_table, all_columns, clause)
        
        cur.close()
        del cur
        conn.close()  
    
    def sync_data(self, cur, source_table, destination_table, all_columns, clause):
        columns = ",".join(all_columns["old_columns"])
        print columns
        query = 'SELECT id,%s from %s %s' % (str(columns),source_table, clause)
        print query
        try:
            print "[INFO-REMOTE] Executing query:", query
            cur.execute(query)
            self.log_field = "[INFO-REMOTE] Fetched all records from table %s \n%s" % (source_table,self.log_field)
        except:
            print "[ERROR-REMOTE] : Select is not working properly with query", query

        new_columns = ",".join(all_columns["new_columns"])
        print new_columns
        rows = cur.fetchall()
        num_rows = 0
        for row in rows:
            row_as_list = [self.format_string(i) if isinstance(i, basestring) else i for i in row]
            row = tuple(row_as_list)
            row_id = row[0]
            data_list = row_as_list[1:]
            update_data = self.map_list_to_string(all_columns["new_columns"],data_list)
            num_rows = num_rows + 1
            query = "UPDATE {} set {} where id={}".format(destination_table, update_data, row_id)
            query = query.replace("None", "NULL")
            self.env.cr.execute(query)
            print "%s of %s rows updated" % (num_rows,len(rows))
            
        self.log_field = "[INFO-LOCAL] Updated [%s] records in table %s \n%s" % (len(rows), destination_table,self.log_field)
        
    def map_list_to_string(self, new_columns,data_list):
        query_str = ""
        for ind in range(0,len(new_columns)):
            data = data_list[ind]
            if data is None:
                query_str = "%s %s = %s," % (query_str,new_columns[ind],str(data_list[ind]))
            else:
                query_str = "%s %s = '%s'," % (query_str,new_columns[ind],str(data_list[ind]))
            
        
        if len(query_str)>0:
            query_str = query_str[:-1]
        return query_str

    def migrate_data(self, cur, source_table, destination_table, all_columns, clause):
        columns = ",".join(all_columns["old_columns"])
        print columns
        query = 'SELECT %s from %s %s' % (str(columns),source_table, clause)
        try:
            print "[INFO-REMOTE] Executing Query:", query
            cur.execute(query)
        except:
            print "\n\n\n\n"
            print "[ERROR-REMOTE] Select is not working properly with query:", query
            print "\n\n\n\n"
                         
        new_columns = ",".join(all_columns["new_columns"])
        print new_columns
        new_query = "INSERT INTO %s (%s) values" % (destination_table,str(new_columns))
        num_rows = 0                
        try:
            rows = cur.fetchall()
            totl = len(rows)
            for row in rows:
                row_as_list = [self.format_string(i) if isinstance(i, basestring) else i for i in row]
                row = tuple(row_as_list)
                new_query = "%s %s," % (new_query,row)
                new_query = new_query.replace("None", "NULL")
                num_rows = num_rows + 1
                print "# %s out of %s" % (num_rows,totl)
        except:
            print "There is some problem in iterating row"
        print "Total %s records fetched" % num_rows
        new_query= new_query[:-1]
        new_query = new_query.replace('"','\'')
        new_query = new_query.replace('_db_migration_quotes_','"')
        print "[INFO-REMOTE] Inserting records in table %s \n%s" % (destination_table,self.log_field)
        print "\n\n\n\n"
        self.env.cr.execute(new_query)
        print "\n\n\n\n"
        self.log_field = "[INFO-REMOTE] Inserted [%s] records in table %s \n%s" % (num_rows, source_table,self.log_field)

        
    def format_string(self, str):
        str = str.encode('UTF-8')
        str = str.replace("'","''")
        str = str.replace('"','_db_migration_quotes_')
        return str
             
    def convert_to_dictionary(self, data):
        new_columns = []
        old_columns = []
        data_lines = data.splitlines()
        
        for data_line in data_lines:
            each_col = data_line.split("=")
            print each_col
            data_line = str(data_line)
            first_part = data_line[0:data_line.find('=')]
            second_part = data_line[data_line.find('=') + 1:]
            new_columns.append(first_part)
            old_columns.append(second_part)
        
        columns = {
                'new_columns': new_columns,
                'old_columns': old_columns
            }
        
        return columns
        
class ouc_table_update(models.Model):
    _name = "ouc.table_update"
    
    db_id = fields.Many2one('ouc.dbmigration', string = 'DB')
    table_name = fields.Char("Local Table")
    source_table = fields.Char("Remote Table")
    query = fields.Char("Query")
    operation = fields.Selection([('query','Query'), ('migrate','Migrate'), ('sync','Synchronize')], string='Operation')
    column_mapping = fields.Text("Column Mapping (New=Old)")