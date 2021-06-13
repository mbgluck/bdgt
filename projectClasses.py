import psycopg2
import psycopg2.extras
import pandas as pd
import os
import glob
import json
from collections import OrderedDict
from ProjectFunctions import read_query, write_query, write_return_query, set_field

# def return_query(query, cursor):
#     cursor.execute(query)
#     return cursor.fetchall()

# def read_query(query, conn, var=()):
#     """ Execute a single read request """
#     cursor = conn.cursor()
#     try:
#         cursor.execute(query,var)
#     except (Exception, psycopg2.DatabaseError) as error:
#         print(f"Error: {error}")
#         cursor.close()
#         raise psycopg2.DatabaseError
    
#     return cursor.fetchall()
#     cursor.close()

# def write_query(query, conn, var=()):
#     """ Execute a single write request """
#     cursor = conn.cursor()
#     try:
#         cursor.execute(query,var)
#         conn.commit()
#     except (Exception, psycopg2.DatabaseError) as error:
#         print("Error: %s" % error)
#         conn.rollback()
#         cursor.close()
#         raise psycopg2.DatabaseError
#     cursor.close()

# def write_return_query(query, conn, var=()):
#     """ Execute a single write request with RETURNING, returns value """
#     cursor = conn.cursor()
#     try:
#         cursor.execute(query, var)
#         r = cursor.fetchone()[0]
#         conn.commit()
#     except (Exception, psycopg2.DatabaseError) as error:
#         print("Error: %s" % error)
#         conn.rollback()
#         cursor.close()
#         raise psycopg2.DatabaseError
#     cursor.close()
#     return r

# def set_field(conn, table, field, new_value, where):
#     """set a field in a table. where clause is a list of 2 tuples (field, value)"""
#     # stg_id = 234 and batch_id = 24
#     # takes the first value in each tuple in pair and joins them with " and "
#     w = ' and '.join(pair[0] + ' = %s' for pair in where)
#     where_clause = 'where ' + w
#     q = f"update {table} set {field} = %s" + where_clause
#     v = ([new_value] + [pair[1] for pair in where])
#     write_query(q, conn, v)
#     msgw = where_clause % tuple(v[1:])
#     print(f"{table} table updated {field} to {new_value} {msgw}")



class BankTemplate(object):
    """Object representing the template used for upload. 
    If an ID is supplied, will call getBankTemplate to get the template from the DB
    if not, will call createDBtemplate"""
    def __init__(self, conn=None, import_template_id=None, **kwargs):
        # id=None, name=None, institution=None, institution_id=None, header_rows=None,
        # self.id =  kwargs['import_template_id']
        # needs to be fed a dictionary of the values below
        # if these values don't exist, they wont be set to anything. may or may not be what I want.
        self.id = None
        if import_template_id: 
            self.id = import_template_id
        elif kwargs.get('id'):
            self.id = kwargs.get('id')
        # else:
        #     raise Exception('Need an ID for the bankTemplate. Make sure to pass in as id or import_template_id')
        self.name = kwargs.get('acct_name')
        self.institution = kwargs.get('institution')
        self.institution_id = kwargs.get('institution_id')
        self.header_rows = kwargs.get('header_rows')

        # build this out:
        self.header_rows = kwargs.get('date_format')

        self.conn = conn
        if self.id:
            self.getBankTemplate()
        else:
            self.createDBtemplate()
        


    def __str__(self):
        return f'template for {self.name} with an ID of {self.id}'

    def createDBtemplate(self):
        # create an entry in finance.import_template, and a line in import_template_map
        if self.name is None or self.institution_id is None or self.header_rows is None:
            raise Exception('Need to have a name, institution ID, and a header row count')
        if self.id is not None:
            raise Exception('How does it already have an ID?')

        q = '''insert into finance.import_template
        (description, acct_institution_id, header_rows)
        values (%s,%s, %s) returning import_template_id'''
        v = (self.name, self.institution_id, self.header_rows)
        newID = write_return_query(q,self.conn,v)

        if self.id is None:
            self.id = newID
        
        q = '''insert into finance.import_template_map
        (import_template_id, import_col_index, stg_field)
        values (%s,0,'unused')'''
        write_query(q, self.conn,(self.id, ))
    
    def setDBtemplate(self):
        # for use if template does not exist, or to update
        # if self.id
        #    
        q = f'''INSERT INTO finance.import_template(description, )
                VALUES ({self.id},{field},{colId})
                ON CONFLICT ON CONSTRAINT import_template_map_pk
                DO UPDATE SET import_template_map = {field}'''
        # add in a try block to return an error if values are missing - check if 
        pass
    

    def getDBcols(self):
        # pull the column lsit and order from the template and add it to the bankTemplate object
        # needs to use the normal cursor, not the dictionary one?
        q = f'select import_col_index, stg_field from finance.import_template_map where import_template_id = {self.id}'
        query = read_query(q, self.conn)
        # make the col map a dictionry of index:columnName
        self.templateCols = dict(query)
    
    def getDBheader(self):
        q = 'select description, acct_institution_id, header_rows, date_format from finance.import_template where import_template_id = %s'
        v = (self.id,)
        query = read_query(q, self.conn, v)
        self.name = query[0][0]
        self.institution_id = query[0][1]
        self.header_rows = query[0][2]
        self.date_format = query[0][3]
        # get the description for the associated institution
        q = f'select description from finance.acct_institution where acct_institution_id = {self.institution_id}'
        query = read_query(q, self.conn)
        self.institution = query[0][0]

    def getBankTemplate(self):
        self.getDBcols()
        self.getDBheader()



    def setDBcols(self):
        # situations - adding a new column. deleting an old mapping
        for colId, field in self.templateCols:
            q = f'''INSERT INTO finance.import_template_map(import_template_id, import_template_map, import_col_index)
                VALUES ({self.id},{field},{colId})
                ON CONFLICT ON CONSTRAINT import_template_map_pk
                DO UPDATE SET import_template_map = {field}'''

            
        # pop a warnng if doubling up on cols?

    def delDBcol(self, col):
        # takes in a column name or index and deletes it from the table
        if isinstance(col,'str'):
            qbuild = 'stg_field'
        elif isinstance(col, 'int'):
            qbuild = 'import_col_index'
        q = f'delete from finance.import_template_map where {qbuild} = {col}'
        write_query(q, self.conn)


    def deleteBankTemplate(self, conn):
        q = f'delete from finance.import_template where import_template_id = {self.id}'
        write_query(q, self.conn)
        q = f'delete from finance.import_template_map where import_template_id = {self.id}'
        write_query(q, self.conn)       

class StagedTransactions():
    """Represents the transactions in the staging table. Carries a bankTemplate object. If no batch_id is supplied, data
    will be cleaned and staged. if batch_id supplied, will get definition from DB.
    """
    def __init__(self, conn=None, batch_id=None, rawData=None, account=None, file_name='None Given', **kwargs):
        # make an instance of stagedTransactions. associate with the template. 
        # steps I want to happen - 
            # pass in the dataframe and the banktemplate (require these 2 inputs on init)
            # attempt to apply the bankTemplate to the dataframe
                # if it breaks, raise a WrongTemplate error
            # load into the stage table. make and associate a batch_id (use a sequence)
            # get rid of duplicates 
                # should delete(or inactivate?) the rows in the staging table, 
                # then reload the dataframe from the staging table
            # reloading the df - pull into df where row is active
                # query to pull in th ecols in the template (not 'unused'), add in the extra columns (charge type, notes, etc.)
        # needed fields to set - conn, raw_data, file_name, associated account
        # needed to get from db - conn, batch
        self.batch_id = batch_id
        self.staged_trans = None
        self.account = account
        self.account_name = None
        self.file_name = file_name
        self.conn = conn
        self.staged_trans = None
        self.ready_to_transfer = False

        # stats
        self.stat_ledger_total = None
        self.stat_staged_total = None
        self.stat_validation_total = None
        self.rows_active = None
        self.rows_inactive = None


        self._bank_template = kwargs.get('bankTemplate')
        self._cleaned = False
        self._raw_data = kwargs.get('raw_data')

        if not conn:
            raise ValueError('A database connection is required to use a StagedTransactions')
        if not self.batch_id:
            if not self._bank_template: 
                raise ValueError('Don''t have a template assigned when trying to create a StagedTransactions from template!')
            if self._raw_data is None:
                raise ValueError('Missing unmapped data when trying to create a StagedTransactions from template!')
            if not self.account:
                raise ValueError('Missing an assigned account when trying to create a StagedTransactions from template!')
            # _stage_raw_data gets run after this, from within _cleanRawData
            self._cleanRawData()
        else:
            # will also call get_stats
            self.get_staged_transactions()



    def _cleanRawData(self):
        """Check the Cleaned flag. If False, clean the rawData"""
        # try to apply the template to the rawData. may want to make this its own thing, not on init?
        # check for headers    
        if not self._cleaned:    
            if self._bank_template.header_rows >  0:
                #  check if the first row still exists, drop if it does
                for i in range(self._bank_template.header_rows):
                    if i in self._raw_data.index:
                        self._raw_data.drop([i], inplace=True)  

            # for the future - do some validations - number of columns matches template, 
            # Map the row headers from the template
            colmap = dict(self._bank_template.templateCols)
            # check if the number of columns are the same. if not, raise an error
            lrc = len(self._raw_data.columns)
            if len(colmap) != lrc:
                raise Exception(f"""The supplied template has a {len(colmap)} columns whereas the uploaded file has {lrc} columns. Please make sure that the correct template was chosen""")
            # rename dataframe cols to integers, 
            self._raw_data.columns = range(lrc)
            # then apply map (in case wrong template applied before)
            self._raw_data.rename(columns=colmap, inplace=True)  

            if 'amount' in self._raw_data.columns: 
                self._raw_data['amount'] = self._raw_data['amount'].str.replace('--', '', regex=False)
                try:
                    self._raw_data['amount'] = pd.to_numeric(self._raw_data['amount'])     
                except ValueError():
                    print("Cannot set the column 'Amount' as numeric, proably the wrong template")
                    raise ValueError()

            if 'description1' in colmap.values() and 'description2' in colmap.values():
                self._raw_data['description'] = self._raw_data[['description1', 'description2']].apply(lambda x: ' - '.join(x.dropna()), axis=1)
            
            self._raw_data['description'] = self._raw_data['description'].str.replace('~+.*', '', regex=True)
            self._raw_data['description'] = self._raw_data['description'].str.replace(r'\s\s+', ' ', regex=True)

            if 'amount_neg' in colmap.values() and 'amount_pos' in colmap.values():
                # amt_cols = self._raw_data[['amount_neg', 'amount_pos']]
                self._raw_data[['amount_neg', 'amount_pos']] = self._raw_data[['amount_neg', 'amount_pos']].replace('[\$,]', '', regex=True).astype(float)
                self._raw_data['amount_neg'] = self._raw_data['amount_neg'].multiply(-1)
                self._raw_data['amount'] = self._raw_data[['amount_neg', 'amount_pos']].sum(axis=1)

            self._raw_data['transaction_date'] = pd.to_datetime(self._raw_data['transaction_date'], format=self._bank_template.date_format)
            if 'post_date' in self._raw_data.columns: 
                self._raw_data['post_date'] = pd.to_datetime(self._raw_data['post_date'], format=self._bank_template.date_format)
            q = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'finance'
                AND table_name   in ('import_transaction_stg')
                AND column_name not in ('stg_id','charge_category_id','account_id','batch_id','charge_type_id','note','charge_tracking_type_id')
                """
            query = read_query(q, self.conn)
            valid_cols = [item for t in query for item in t]

            for n in self._raw_data.columns:
                if n not in valid_cols:
                    # is it right to ignore errors here? it breaks if say, 2 unused cols need to be dropped
                    self._raw_data = self._raw_data.drop(columns=n, axis=1, errors='ignore')
            # fixes: the weird -- thing for amounts in usaa export
            # fix the description in the weird USAA import. add in a column to the mapping table, make this work dynamically:
            # look for a sequence starting with one or more ~s (the plus), followed by any characters. replace with ''
            # fix weird space issue?       
            

            #  set datatypes. Could the column assignments be more dynamic? Storing the type in the table?


            self._cleaned = True
            self._stageRawData()
        else:
            print('Cleaned flag has already been set to True')

    def _stageRawData(self):
        """writes  the rawData to the staging table after it has been cleaned. Activates non-repeat rows"""
        if self._cleaned: 
            if self.batch_id is None:
                # create a batch in the DB
                q = '''insert into finance.import_batch(file_name, import_date, import_template_id, account_id) 
                        values (%s,NOW(),%s, %s) returning batch_id'''
                v = (self.file_name, self._bank_template.id, self.account)
                self.batch_id = write_return_query(q, self.conn, v)
                # stage the data
                account_id = self.account
                import_cols = self._raw_data.columns.tolist()
                dest_cols = ', '.join(import_cols)
                table = 'finance.import_transaction_stg'
                values = '{}'.format(','.join(['%s' for _ in import_cols]))
                insert = f'insert into {table} ({dest_cols}, account_id, batch_id, active) VALUES({values}, {self.account}, {self.batch_id}, {False})'
                # self._raw_data.values is a list of arrays representing each row. so this is building an insert statement for eah row, then running them in batches
                psycopg2.extras.execute_batch(self.conn.cursor(), insert, self._raw_data.values)
                self.conn.commit()

                # activate every row that isnt a duplicate:
                q =  """UPDATE only finance.import_transaction_stg
                        SET    active = true
                        WHERE  ( transaction_date, description, amount ) 
                        IN (SELECT transaction_date, description, amount
                            FROM only finance.import_transaction_stg
                            WHERE  account_id = %s
                            AND batch_id = %s
                            EXCEPT
                            SELECT transaction_date, description, amount
                            FROM finance.transaction_ledger
                            WHERE  account_id = %s)
                        AND batch_id = %s """
                v = (self.account, self.batch_id,self.account, self.batch_id)
                write_query(q, self.conn, v)
                self.get_staged_transactions()
            else:
                raise RuntimeError('Why is this running if a batch ID has already been assigned?')
        else:
            raise RuntimeError('Why is this running if this upload hasn''t been cleaned?')

    def get_stats(self):
        """gets info on the upload. Sets the following properties:
        
        :ledger_total: the sum of amount in the transaction ledger for this account
        :staged_total: the sum of amount in the stage table, for this batch
        :validation total: sum of ledger_total + staged_total
        :active_rows: rows in this batch where active = True
        :inactive_rows: rows in this batch where active = False"""

        q = 'select sum(amount) from finance.transaction_ledger where account_id = %s'
        v  = (self.account,)
        self.stat_ledger_total = read_query(q, self.conn, v)[0][0]
        if self.stat_ledger_total is None:
            self.stat_ledger_total = 0

        q = 'select sum(amount) from only finance.import_transaction_stg where batch_id = %s and active is true'
        v  = (self.batch_id,)
        self.stat_staged_total = read_query(q, self.conn, v)[0][0]
        if self.stat_staged_total is None:
            self.stat_staged_total = 0

        self.stat_validation_total = self.stat_ledger_total + self.stat_staged_total

        q = 'select count(*) from only finance.import_transaction_stg where batch_id = %s and active is %s'
        v = (self.batch_id,True)
        self.rows_active = read_query(q, self.conn, v)[0][0]
        v = (self.batch_id,False)
        self.rows_inactive = read_query(q, self.conn, v)[0][0]
        self.validate()

    def get_staged_transactions(self):
        """this method queries the db and loads the StagedTransactions into the object. Requires a batch_id and a connection"""

        q = """select file_name, account_id from finance.import_batch
            where batch_id = %s"""
        v = (self.batch_id,)
        query = read_query(q,self.conn, v)
        
        if len(query) == 0:
            raise ValueError(f"no import with a batch_id of {self.batch_id} exists")

        self.file_name = query[0][0]
        self.account = query[0][1]

        q = 'select description, currency from finance.account where account_id = %s'
        v = (self.account,)
        acct  = read_query(q, self.conn, v)[0]
        self.account_name = acct[0]
        self.currency = acct[1]

        vc = ['transaction_date','description','amount','charge_type_id','charge_category_id','charge_tracking_type_id','note']
        vcstr = ','.join(vc)
        q = f"select stg_id,{vcstr} from only finance.import_transaction_stg where batch_id = {self.batch_id} and active = true;"
        self.staged_trans = pd.read_sql_query(q, self.conn, index_col='stg_id')
        
        if len(self.staged_trans) == 0:
            msg = 'there are no staged rows to load. Has this template already been submitted?'
            d = {'error': msg}
            self.staged_trans = pd.DataFrame(d, index = [0])
        
        # make sure the dropdown fields are int, not float. Causes problems for dropdowns.
        types = {'charge_type_id':'Int64','charge_category_id':'Int64','charge_tracking_type_id':'Int64'}
        self.staged_trans = self.staged_trans.astype(types, errors='ignore') 

        # sort dataframe by date
        self.staged_trans.sort_values(by='transaction_date', inplace=True, ascending=False) 

        self.get_stats() 
            # raise ValueError('there are no staged rows to load. Has this template already been submitted?') 

        # format some of the DF cols - turning this off, dont think i need it as a date, and its a pain to display:
        # self.staged_trans['transaction_date'] = pd.to_datetime(
        #         self.staged_trans['transaction_date'])
  
        
    
    # is this used anywhere? mark for deletion
    def set_field(self, stg_id, field, new_value):
        """modify df, and set a field in the database from the change in the dataframe"""

        self.staged_trans.at[stg_id,field] = new_value
        print(f"staged_trans dataframe updated {field} to {new_value} where stg_id = {stg_id}")
        q = f"""update only finance.import_transaction_stg set {field} = %s
            where stg_id = %s"""
        v = (new_value, stg_id)
        write_query(q, self.conn, v)
        print(f"import_transaction_stg table updated {field} to {new_value} where stg_id = {stg_id}")

    def validate(self):
        q = """
            SELECT COUNT(*)
            FROM ONLY FINANCE.IMPORT_TRANSACTION_STG
            WHERE BATCH_ID = %s
                AND ACTIVE is TRUE
                AND (CHARGE_CATEGORY_ID IS NULL
                                    OR CHARGE_TRACKING_TYPE_ID IS NULL
                                    OR CHARGE_TYPE_ID IS NULL);
            """
        v = (self.batch_id,)
        unfilled = read_query(q, self.conn, v)[0][0]
        q = """
            SELECT COUNT(*)
            FROM
                (SELECT TRANSACTION_DATE,
                        DESCRIPTION,
                        AMOUNT
                    FROM ONLY FINANCE.IMPORT_TRANSACTION_STG
                    WHERE BATCH_ID = %s
                        AND ACCOUNT_ID = %s
                        AND ACTIVE IS TRUE
                        AND (TRANSACTION_DATE,
                            DESCRIPTION,
                            AMOUNT) in
                            (SELECT TRANSACTION_DATE,
                                    DESCRIPTION,
                                    AMOUNT
                                FROM FINANCE.TRANSACTION_LEDGER
                                WHERE ACCOUNT_ID = %s)) VALIDATION
            """
        v = (self.batch_id, self.account, self.account)
        duplicates = read_query(q, self.conn, v)[0][0]

        if duplicates == 0 and unfilled == 0:
            self.ready_to_transfer = True

        return {'unfilled': unfilled, 'duplicates': duplicates}

    def load_staged(self):
        v = (self.batch_id,)
        q = """
            insert into finance.import_transaction_arc 
            select * from only finance.import_transaction_stg where batch_id = %s;
            """ 
        write_query(q, self.conn, v) #move data to archive table
        q = """
            INSERT INTO FINANCE.TRANSACTION_LEDGER (STG_ID,
                                                    TRANSACTION_DATE,
                                                    POST_DATE,
                                                    DESCRIPTION,
                                                    AMOUNT,
                                                    ACCOUNT_ID,
                                                    BATCH_ID,
                                                    CHARGE_TYPE_ID ,
                                                    CHARGE_CATEGORY_ID,
                                                    CHARGE_TRACKING_TYPE_ID,
                                                    NOTE,
                                                    CURRENCY)
            SELECT STG_ID,
                TRANSACTION_DATE,
                POST_DATE,
                STAGE.DESCRIPTION,
                AMOUNT,
                ACCOUNT_ID,
                BATCH_ID,
                CHARGE_TYPE_ID,
                CHARGE_CATEGORY_ID,
                CHARGE_TRACKING_TYPE_ID,
                NOTE,
                CURRENCY
            FROM
                (SELECT STG.*,CURRENCY
                FROM ONLY FINANCE.IMPORT_TRANSACTION_STG STG
                INNER JOIN FINANCE.ACCOUNT A ON STG.ACCOUNT_ID = A.ACCOUNT_ID
                WHERE STG.ACTIVE IS TRUE
                AND BATCH_ID = %s) STAGE;
            """
        write_query(q, self.conn, v)

        # clear the stg table
        q = """
        delete from only finance.import_transaction_stg 
        where batch_id = %s;
        """ 
        write_query(q, self.conn, v)

class PivotTableJs():
    TEMPLATE = """
    <!DOCTYPE html>
    <html>

    <head>
    	<meta charset="UTF-8">
    	<title>PivotTable.js</title>
    	<!-- external libs from cdnjs -->
    	<link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.11/c3.min.css">
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min.js"></script>
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.11/c3.min.js"></script>
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery/1.11.2/jquery.min.js"></script>
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.11.4/jquery-ui.min.js"></script>
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery-csv/0.71/jquery.csv-0.71.min.js"></script>
    	<link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.19.0/pivot.min.css">
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.19.0/pivot.min.js"></script>
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.19.0/d3_renderers.min.js"></script>
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.19.0/c3_renderers.min.js"></script>
    	<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.19.0/export_renderers.min.js"></script>
    	<style>
    	body {
    		font-family: Verdana;
    	}

    	.node {
    		border: solid 1px white;
    		font: 10px sans-serif;
    		line-height: 12px;
    		overflow: hidden;
    		position: absolute;
    		text-indent: 2px;
    	}

    	.c3-line,
    	.c3-focused {
    		stroke-width: 3px !important;
    	}

    	.c3-bar {
    		stroke: white !important;
    		stroke-width: 1;
    	}

    	.c3 text {
    		font-size: 12px;
    		color: grey;
    	}

    	.tick line {
    		stroke: white;
    	}

    	.c3-axis path {
    		stroke: grey;
    	}

    	.c3-circle {
    		opacity: 1 !important;
    	}

    	.c3-xgrid-focus {
    		visibility: hidden !important;
    	}

    	/* The Modal (background) */
    	.modal {
    		display: none;
    		/* Hidden by default */
    		position: fixed;
    		/* Stay in place */
    		z-index: 1;
    		/* Sit on top */
    		padding-top: 100px;
    		/* Location of the box */
    		left: 0;
    		top: 0;
    		width: 100%%;
    		/* Full width */
    		height: 100%%;
    		/* Full height */
    		overflow: auto;
    		/* Enable scroll if needed */
    		background-color: rgb(0, 0, 0);
    		/* Fallback color */
    		background-color: rgba(0, 0, 0, 0.4);
    		/* Black w/ opacity */
    	}

    	/* The Close Button */
    	.close {
    		color: #aaaaaa;
    		float: right;
    		font-size: 28px;
    		font-weight: bold;
    	}

    	.close:hover,
    	.close:focus {
    		color: #000;
    		text-decoration: none;
    		cursor: pointer;
    	}

    	/* Modal Content */
    	.modal-content {
    		background-color: #fefefe;
    		margin: auto;
    		padding: 20px;
    		border: 1px solid #888;
    		width: 80%%;
    	}
    	</style>
    </head>

    <body>
    	<script type="text/javascript">
    	$(function() {
    		if(window.location != window.parent.location) $("<a>", {
    			target: "_blank",
    			href: ""
    		}).text("[pop out]").prependTo($("body"));
    		$("#output").pivotUI($.csv.toArrays($("#output").text()), $.extend({
    			renderers: $.extend($.pivotUtilities.renderers, $.pivotUtilities.c3_renderers, $.pivotUtilities.d3_renderers, $.pivotUtilities.export_renderers),
    			hiddenAttributes: [""],
    			rendererOptions: {
    				table: {
    					clickCallback: function(e, value, filters, pivotData) {
    						var names = [];
    						var drillcols = %(drillcols)s;
    						/*names.push(drillcols);*/
    						pivotData.forEachMatchingRecord(filters, function(record) {
                                names.push({row_id: record["%(index_name)s"], row_data:[%(drillcolsrecs)s]});
    						});
    						var child = drillback_div.lastElementChild;
    						while(child) {
    							drillback_div.removeChild(child);
    							child = drillback_div.lastElementChild;
    						}

    						function createTable(tableHeader, tableData) {
    							var table = document.createElement('table');
                                var header = table.createTHead();
                                var headerRow = header.insertRow(0);
    							var row = {};
    							var cell = {};
                                tableHeader.forEach(function (rowHeader) {
                                    cell = headerRow.appendChild(document.createElement("th"));
                                    cell.textContent = rowHeader;

                                });
    							tableData.forEach(function(rowData) {
    								row = table.insertRow(-1);
    								rowData["row_data"].forEach(function(cellData) {
    									cell = row.insertCell();
    									cell.textContent = cellData;
    								});
                                    var link_id = rowData["row_id"];
                                    link = document.createElement('a');
                                    link.setAttribute('href',"/transactions/record/"+link_id);
                                    link.setAttribute('target',"_blank");
                                    link.setAttribute('rel',"noopener noreferrer");
                                    linktext = document.createTextNode("Adjust/Modify");
                                    link.appendChild(linktext);
                                    cell = row.insertCell();
                                    cell.appendChild(link);
    							});
    							drillback_div.appendChild(table);
    						}
    						createTable(drillcols, names)
    						modal.style.display = "block";
    					}
    				}
    			}
    		}, %(kwargs)s)).show();
    	});
    	</script>
    	<div id="output" style="display: none;">%(csv)s</div>
    	<div id="myModal" class="modal">
    		<!-- Modal content -->
    		<div class="modal-content">
    			<span class="close">&times;</span>
    			<div id="drillback_div">
    			</div>
    		</div>
    	</div>
    	<script type="text/javascript">
    	// Get the <span> element that closes the modal
    	var span = document.getElementsByClassName("close")[0];
    	var modal = document.getElementById("myModal");
    	var drillback_div = document.getElementById("drillback_div");
    	// When the user clicks on <span> (x), close the modal
    	span.onclick = function() {
    		modal.style.display = "none";
    	}
    	// When the user clicks anywhere outside of the modal, close it
    	window.onclick = function(event) {
    		if(event.target == modal) {
    			modal.style.display = "none";
    		}
    	}
    	</script>
    </body>

    </html>
    """
    
    def __init__(self, df, drillcols=None, **kwargs):
        
        index_name = df.index.name
        if index_name is None:
            df.index.name = 'index'
        if drillcols is None:
            drillcols = [index_name]
        csv = df.to_csv(encoding='utf8')
        def iter(x):
            for field in x:
                yield f'record["{field}"]'

        drillcolsrecs = ','.join(iter(drillcols))
        # # {h} needs to be surrounded in double quotes to be passed into the javascript in Template as a quoted string
        # drillheaders = ''.join(h.ljust(p,' ') for h,p in drillcols)
        # drillheaders = f'"{drillheaders}"'
        
        
        
        if hasattr(csv, 'decode'):
            csv = csv.decode('utf8')
        self.pivot_html = (PivotTableJs.TEMPLATE %
            dict(drillcols=drillcols, drillcolsrecs=drillcolsrecs, index_name=index_name, csv=csv, kwargs=json.dumps(kwargs)))


if __name__ == '__main__':
    t_host = "localhost"  # either "localhost", a domain name, or an IP address.
    t_port = "5432"  # default postgres port
    t_dbname = "max"
    t_user = "python"
    t_pw = "pypassword"
    # connect to the database and make a cursor
    db_conn = psycopg2.connect(host=t_host, port=t_port, dbname=t_dbname,
                            user=t_user, password=t_pw)
    dbDictCursor = db_conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    # dbCursor = db_conn.cursor()
    # q = '''select a.import_template_id, a.description acct_name, a.has_eader, b.description institution  
    # from finance.import_template a inner join finance.acct_institution b on a.acct_institution_id = b.acct_institution_id'''
    # query = return_query(q,dbDictCursor)
    # templateList = []
    # for i in query:
    #     temp = BankTemplate(**i, cursor=dbCursor)
    #     templateList.append(temp)
    # for i in templateList:
    #     i.getDBcols()
    #     for k,v in i.templateCols.items():
    #         print(f'the key is of type {type(k)}')
    #         itype = type(k)
    # q = '''SELECT column_name
    # FROM information_schema.columns
    # WHERE table_schema = 'finance'
    # AND table_name   in ('import_transaction_stg')
    # AND column_name not in ('stg_id','charge_category_id','account_id','batch_id','charge_type_id','note','charge_tracking_type_id')
    # UNION select 'unused';'''
    # query = return_query(q, dbCursor)
    # colList = [item for t in query for item in t]

    # function test

    # sql = "select * from finance.import_transaction_stg;"
    # dat = pd.read_sql_query(sql, db_conn, index_col='stg_id')
    # print(dat.dtypes)
    # print(dat.head())
    # q = 'select * from finance.import_transaction_stg'
    # v = (7,8)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    files = glob.glob(os.path.join(dir_path, 'static', 'csv_uploads',
                                          '*.csv'))
    file_df = pd.read_csv(files[0], header=None)
    template = BankTemplate(conn=db_conn, import_template_id=7)
    # template.getBankTemplate()
    # test2 = stagedTransactions(conn=db_conn, bankTemplate=template, raw_data=file_df, file_name='transactions.csv', account=3)
    # test.cleanRawData()
    test1 = StagedTransactions(batch_id=94, conn=db_conn)
    test1.set_field(704,'charge_category_id',7)
    test1.set_field(704,'note','testing')
    print(test1.staged_trans.sort_values('charge_category_id'))
    # test2.get_staged_transactions()
    # print(test.rawData)
    # test._stageRawData()
    a=1

    uploadedFile

