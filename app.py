from flask import Flask, render_template, url_for, request, jsonify, redirect
from flask_wtf import FlaskForm
import os
import glob
import pandas as pd
import pandas.io.sql as sqlio
import psycopg2
import psycopg2.extras
import numpy as np
from decimal import Decimal
from projectClasses import BankTemplate, StagedTransactions, PivotTableJs
from ProjectFunctions import read_query, write_query, write_return_query, set_field
from FormClasses import CT_Test, csv_info, newBankTemplate, chargeTypeForm, chargeCategoryForm, trackingTypeForm, ModifyRecord
from datetime import date, datetime
import dropdowns
import dbconnection
# from pivottablejs import pivot_ui

# import psycopg2.extras

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ahdflajshgdfjashd'

app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# connect to the database and make a cursor
db_conn = psycopg2.connect(host=dbconnection.t_host, port=dbconnection.t_port, dbname=dbconnection.t_dbname,
                           user=dbconnection.t_user, password=dbconnection.t_pw)
db_cursor = db_conn.cursor()


dir_path = os.path.dirname(os.path.realpath(__file__))
# should dfdic be a session variable?
dfdic = {}

def return_query(query, cursor):
    cursor.execute(query)
    return cursor.fetchall()

def modify_query(conn, query):
    """ Execute a single INSERT request """
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1
    cursor.close()






@app.route('/form_test')
def form_test():
    # testing space to try out an example of having the full form built out using wtforms
    cols = ['transaction_date','description','amount','currency','charge_type_id','charge_category_id','charge_tracking_type_id','note']
    colstr = ', '.join(cols)
    q = f'select {colstr} from finance.test_trans'
    rec = pd.read_sql_query(q, db_conn)   
    ct = CT_Test(conn=db_conn)
    return render_template('form_test.html', rec=rec, cols=cols, ct=ct)
    
@app.route('/', methods=['POST', 'GET'])
def index():
    query = '''select b.description, max(transaction_date), sum(amount)
                from finance.transaction_ledger a
                inner join finance.account b
                    on a.account_id = b.account_id
                group by b.description
                order by max(transaction_date) desc, abs(sum(amount)) desc'''
    latest_values = return_query(query, db_cursor)
    return render_template('index.html', latest_values=latest_values)

@app.route('/transactions/view', methods=['GET'])
def transactions_view_home():
    cy = date.today().year
    return redirect(url_for('transactions_view',minyear=str(cy-1), maxyear=str(cy)))

@app.route('/transactions/view/<minyear>-<maxyear>', methods=['GET'])
def transactions_view(minyear, maxyear):
    q = 'select count(usd_amount) from finance.vw_transaction_records_usd;'
    q = 'select count(*) from finance.transaction_ledger;'
    vr = read_query(q, db_conn)[0][0]
    tr = read_query(q, db_conn)[0][0]
    if vr != tr:
        return f'Something is wrong with the view. There are {vr} records in the view, and {tr} in the transaction_ledger'

    q = "select * from finance.vw_transaction_records_usd where transaction_year >= %s and transaction_year <= %s order by transaction_date desc;"
    df = pd.read_sql_query(q, db_conn, params=(minyear, maxyear), index_col='transaction_id')
    
    colmapper = lambda x:x.replace('_',' ').title().replace('Usd','USD') 
    df.rename(mapper=colmapper, axis=1, inplace=True)      
    dc = ['Transaction Date','Description','USD Amount','Charge Type','Note','Currency','Amount']
    pt = PivotTableJs(df, drillcols=dc,
        rows=['Tracking Type','Charge Category'],
        cols=['Transaction Year','Transaction Month'], 
        vals=['USD Amount'],
        aggregatorName='Sum',
        exclusions={'Tracking Type':['Income','Non-Spending']},
        unusedAttrsVertical=False)

    return render_template('transactions_pivot_table.html', pt=pt)


@app.route('/transactions/record/<transaction_id>')
def transaction_record(transaction_id):
    cols = ['transaction_date','description','amount','currency','charge_type_id','charge_category_id','charge_tracking_type_id','note']
    colstr = ', '.join(cols)
    q = f'select {colstr} from finance.transaction_ledger where transaction_id = %s'
    v = (transaction_id,)
    rec = pd.read_sql_query(q, db_conn, params=v)

    q = f'select {colstr} from finance.transaction_ledger where adjustment_source_id = %s'
    adj = rec = pd.read_sql_query(q, db_conn, params=v)

    ct_form = chargeTypeForm()
    ct_form.get_charge_type(db_conn)
    cc_form = chargeCategoryForm()
    cc_form.get_charge_category(db_conn)
    tt_form = trackingTypeForm()
    tt_form.get_tracking_type(db_conn)    

    return render_template('transactions_record.html', record=rec, transaction_id = transaction_id,
        adj=adj, ct_form=ct_form, cc_form=cc_form, tt_form=tt_form)


@app.route('/net_worth/input', methods=['POST', 'GET'])
def nw_input():
    if request.method == 'GET':
        q = '''
            SELECT account_id, description, currency
            FROM FINANCE.ACCOUNT
            WHERE ACTIVE = TRUE
            order by acct_institution_id;
            '''
        accts = read_query(q, db_conn)
        today = date.today().strftime('%Y-%m-%d')
        return render_template('nw_input.html', accts=accts, today=today)
    elif request.method == 'POST':
        d = request.form['record_date'] #date as str YYYY-MM-DD
        fd = datetime.strptime(d, '%Y-%m-%d')
        changes = 0
        for i in request.form.items():
            if i[0] != 'record_date' and i[0][:4] != 'note': #i[0] is the account id, i[1] is the amount. Skip the record_date and note fields
                if i[1]:
                    note = request.form['note'+i[0]]
                    q = """
                        INSERT INTO FINANCE.NET_WORTH_RECORDS (ACCOUNT_ID, date, AMOUNT, NOTE)
                        VALUES (%s, %s, %s, %s) 
                        ON CONFLICT ON CONSTRAINT PK_NET_WORTH_RECORDS 
                        DO UPDATE
                        SET AMOUNT = %s,
                            NOTE = %s;
                        """
                    v = (i[0], fd, i[1], note, i[1], note)
                    write_query(q, db_conn, v)
                    changes += 1
        return(f'modified {changes} entries')

@app.route('/net_worth/view', methods=['POST', 'GET'])
def nw_view():
    q = "select * from finance.VW_NET_WORTH_RECORDS order by date desc;"
    df = pd.read_sql_query(q, db_conn)
    colmapper = lambda x:x.replace('_',' ').title().replace('Usd','USD') 
    df.rename(mapper=colmapper, axis=1, inplace=True) 
    pt = PivotTableJs(df,
        rows=['Holding Type'],
        cols=['Date'], 
        vals=['USD Amount'],
        rendererName='Area Chart',
        aggregatorName='Sum',
        unusedAttrsVertical=False)

    return render_template('net_worth_pivot_table.html', pt=pt)



@app.route('/import_transactions')
def stage_import_home():
    q = """
        WITH ROWCOUNTS AS
            (SELECT BATCH_ID,
                    SUM(ACTIVE) AS ACTIVE,
                    SUM(INACTIVE) AS INACTIVE,
                    SUM(NULLED) AS NULLED,
                    sum(REMAINING) as REMAINING
                FROM
                    (SELECT BATCH_ID,
                            COUNT(*) AS ACTIVE,
                            0 AS INACTIVE,
                            0 AS NULLED,
                            0 as REMAINING
                        FROM ONLY FINANCE.IMPORT_TRANSACTION_STG
                        WHERE ACTIVE IS TRUE
                        GROUP BY BATCH_ID
                        UNION SELECT BATCH_ID,
                            0,
                            COUNT(*),
                            0,
                            0
                        FROM ONLY FINANCE.IMPORT_TRANSACTION_STG
                        WHERE ACTIVE IS FALSE
                        GROUP BY BATCH_ID
                        UNION SELECT BATCH_ID,
                            0,
                            0,
                            COUNT(*),
                            0
                        FROM ONLY FINANCE.IMPORT_TRANSACTION_STG
                        WHERE ACTIVE IS NULL
                        GROUP BY BATCH_ID
                        UNION SELECT BATCH_ID,
                            0,
                            0,
                            0,
                            count(*)
                        FROM ONLY FINANCE.IMPORT_TRANSACTION_STG
                        WHERE (Charge_category_id IS NULL or charge_tracking_type_id is null or charge_type_id is null)
                        and active is True
                        GROUP BY BATCH_ID) A
                GROUP BY BATCH_ID)
        SELECT B.BATCH_ID,
            IMPORT_DATE,
            ACCT.DESCRIPTION "Account",
            TE.DESCRIPTION "Template",
            ROWCOUNTS.ACTIVE,
            rowcounts.remaining,														
            INACTIVE,
            NULLED,
            FILE_NAME
        FROM FINANCE.IMPORT_BATCH B
        INNER JOIN FINANCE.IMPORT_TEMPLATE TE ON B.IMPORT_TEMPLATE_ID = TE.IMPORT_TEMPLATE_ID
        INNER JOIN FINANCE.ACCOUNT ACCT ON ACCT.ACCOUNT_ID = B.ACCOUNT_ID
        INNER JOIN ROWCOUNTS ON B.BATCH_ID = ROWCOUNTS.BATCH_ID
        order by rowcounts.active desc;
    """
    table = read_query(q, db_conn)
    header = ['Batch','Import Date','Account', 'Template', 'Active Rows','Remaining','Inactive Rows',  'Nulled Rows','File Name']
    return render_template('stage_transactions_home.html', table=table, header=header)

@app.route('/import_transactions/upload')
def uploadTransactionsFile():
    # this function should clear out the upload folder, prompt the user for a file, then copy that file to the upload folder.
    # if successful, should display the file and ask which bankTemplate to use, and which account it is.
    # if submission on this page should redirect to the stagedtransactions page

    # skipping the upload a file part for now - will assume a file is in there
    # Load the file into a dataframe
    dir_path = os.path.dirname(os.path.realpath(__file__))
    files = glob.glob(os.path.join(dir_path, 'static', 'csv_uploads',
                                          '*.[cC][sS][vV]')) #upper or lowercase extension
    # if nothing in the string, ask for upload:
    msg=''
    if len(files) == 0:
        return('you need to upload a file')
        # need to build out upload logic here - No, do it on dedicated page
    file_name = os.path.basename(files[0])    
    if len(files) != 1:
        msg = f'{len(files)} files have been uploaded. Will be starting with "{file_name}" first.' 

    try:
        file_df = pd.read_csv(files[0], header=None)
    except pd.errors.ParserError:   # the schwab template has a first row that has a different number of cols
        file_df = pd.read_csv(files[0], header=None, skiprows=1)
    # initialize the info form and load in the options
    file_info = csv_info()
    file_info.get_accounts(db_cursor)
    file_info.get_bankTemplate(db_cursor)
    return render_template('importTransactionsUpload.html', file_df=file_df, file_info=file_info, file_name=file_name, msg=msg)

@app.route('/import_transactions/stage', methods = ['POST'])
def stage_import():
    # receives the file name, bankTemplate ID, and the proper account_id 
    if request.method == 'POST':
        form_type = request.form['formType']
        if form_type == 'file_info':
            # load the StagedTransactions object from scratch
            file_name = request.form['fileName']
            file_account = request.form['account']
            file_bt = request.form['bankTemplate']            
            dir_path = os.path.dirname(os.path.realpath(__file__))
            f = os.path.join(dir_path, 'static', 'csv_uploads', file_name)
            nf = os.path.join(dir_path, 'static', 'csv_uploads', file_name)
            # rename file
            if '_uploaded_' not in file_name:
                now = datetime.now()
                lfile = file_name.lower()
                name = lfile[:lfile.index(".csv")]
                file_name = name + f'_uploaded_{now}.csv'
                nf = os.path.join(dir_path, 'static', 'csv_uploads', file_name)
                os.rename(f, nf)

            # this should be a function if it gets any more complicated, as it happens twice
            try:
                df = pd.read_csv(nf, header=None)
            except pd.errors.ParserError:
                df = pd.read_csv(nf, header=None, skiprows=1)
   
            template = BankTemplate(conn=db_conn, import_template_id=file_bt)
            # try:
            staged = StagedTransactions(conn=db_conn, file_name=file_name, raw_data=df, bankTemplate=template, account=file_account)
            # except Exception as error:
            #     return(error)
            src = os.path.join(dir_path, 'static', 'csv_uploads', file_name)
            dst = os.path.join(dir_path, 'static', 'csv_uploads', 'uploaded_csvs', file_name)
            os.rename(src, dst)
        else:
            raise Exception('something went wrong, no/incorrect form_type. how did you get here?')
        
    return redirect(url_for('staged_transactions', batch_id=staged.batch_id))

@app.route('/import_transactions/stage/<batch_id>')
def staged_transactions(batch_id):

    try:
        int(batch_id)
    except ValueError:
        return f"batch_id must be a number"

    try:
        staged = StagedTransactions(conn=db_conn, batch_id=batch_id)
    except ValueError as error:
        return f"Error getting staged transactions from DB: {error}"

    ct_form = chargeTypeForm()
    ct_form.get_charge_type(db_conn)
    cc_form = chargeCategoryForm()
    cc_form.get_charge_category(db_conn)
    tt_form = trackingTypeForm()
    tt_form.get_tracking_type(db_conn)

    col_names = {
        'transaction_date': 'Transaction Date',
        'description':'Description',
        'amount':'Amount',
        'charge_type_id':'Charge Type',
        'charge_category_id':'Category',
        'charge_tracking_type_id':'Tracking Type',
        'note':'Note',
        'error':'Error message!'
        }
    
    return render_template('staged_transactions.html',staged=staged, ct_form=ct_form, cc_form=cc_form, tt_form=tt_form, col_names=col_names)

@app.route('/import_transactions/stage/<batch_id>/submit', methods=['POST'])
def staged_transactions_submit(batch_id):
    # validate that everything is filed in
    staged = StagedTransactions(conn=db_conn, batch_id=batch_id)
    if staged.ready_to_transfer:
        staged.load_staged() # copy stg to arc, load in to transaction_records
        return redirect(url_for('stage_import_home'))       
    else:
        # send back to batch home with a message (?)
        return url_for('staged_transaction', batch_id=batch_id)

@app.route('/import_transactions/stage/field_change', methods = ['POST'])
def staged_field_change():
    try: 
        form_type = request.form['form_type']
        batch_id = request.form['batch_id']
        stg_id = int(request.form['row_index'])
    except KeyError:
        raise KeyError("there was no form_type on the submitted request")
    where = [('batch_id', batch_id),('stg_id',stg_id)]    
    
    if form_type == 'charge_type':
        ct = request.form['chargeType']
        q =  'select default_charge_category_id, default_charge_tracking_type_id from finance.charge_type where charge_type_id = %s'
        v = (ct,)
        cc, tt = read_query(q, db_conn, v)[0]
        ccformid = 'charge_category' + str(stg_id)
        ttformid = 'tracking_type' + str(stg_id)
        # set charge_type_id, charge_category_id, charge_tracking_type_id
        set_field(db_conn, 'only finance.import_transaction_stg','charge_type_id', ct, where)
        set_field(db_conn, 'only finance.import_transaction_stg','charge_category_id', cc, where)
        set_field(db_conn, 'only finance.import_transaction_stg','charge_tracking_type_id', tt, where)
        return {'ccformid': ccformid, 'ccdef': cc, 'ttformid': ttformid, 'ttdef': tt}
    elif form_type == 'note':
        set_field(db_conn, 'only finance.import_transaction_stg','note', request.form['note'], where)
        return ('', 204)
    elif form_type == 'charge_category':
        set_field(db_conn, 'only finance.import_transaction_stg','charge_category_id', request.form['chargeCategory'], where)
        return ('', 204)
    elif form_type == 'tracking_type':
        set_field(db_conn, 'only finance.import_transaction_stg','charge_tracking_type_id', request.form['trackingType'], where)
        return ('', 204)
    else:
        print("wrong form type submitted")
        return ('', 400)



@app.route('/bankTemplates', methods=['POST','GET'])
def templateMaint():
    # to do - add in the header flag. Make the field updateable. make institution updatable. Ajax call, or promise, to make template fields updatable.
    
    # Display the existing templates and allow to change their values
    # query list of templates
    with db_conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor) as dbDictCursor:
        q = '''select a.import_template_id, a.description acct_name, a.header_rows, b.description institution, 
        b.acct_institution_id institution_id from finance.import_template a inner join 
        finance.acct_institution b on a.acct_institution_id = b.acct_institution_id'''
        query = return_query(q,dbDictCursor)
    templateList = []
    for i in query:
        # create BankTemplate objects and get their definitions from the DB
        t = BankTemplate(**i, conn=db_conn)
        t.getDBcols()
        templateList.append(t)
    q = '''SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'finance'
        AND table_name   in ('import_transaction_stg')
        AND column_name not in ('stg_id','charge_category_id','account_id','batch_id','charge_type_id','note','charge_tracking_type_id')
        UNION select 'unused'
        UNION select 'description1'
        UNION select 'description2'
        UNION select 'amount_neg'
        UNION select 'amount_pos'
        ;'''
    query = return_query(q, db_cursor)
    # learn more about list comprehensions
    colList = [item for t in query for item in t]
    colList.sort()
    q='select acct_institution_id, description from finance.acct_institution'
    institutions = return_query(q, db_cursor)
    return render_template('bankTemplateHome.html', bankTemplates=templateList, colList=colList, institutions=institutions)

@app.route('/bankTemplates/addDelCol', methods=['POST'])
def templateAddDelCol():
    template_id = request.form['bankTemplateId']
    # check if adding or deleting a col
    # only proceed if it's the right kind of form?
    # if request.form[]
    if request.form['AddOrDel'] == 'add':
        # when the addcol button is pressed, add a column to the template
        q = '''insert into finance.import_template_map(import_template_id, import_col_index, stg_field) 
        select %s, max(import_col_index)+1, 'unused'
        from finance.import_template_map
        where import_template_id = %s;'''
        v = (template_id,template_id)
        write_query(q, db_conn, v)
    elif request.form['AddOrDel'] == 'del':
        q = ''' delete from finance.import_template_map
        where (import_template_id, import_col_index) in (
            select import_template_id, max(import_col_index) 
            from finance.import_template_map 
            where import_template_id = %s
            group by import_template_id)
        and import_col_index <> 0'''
        v = (template_id,)
        write_query(q, db_conn, v)
    return redirect(url_for('templateMaint'))

@app.route('/bankTemplates/modCol', methods=['POST'])
def templateModCol():
    # templateId - corresponds to the ID of the bank template
    # templateCol - corresponds to the column index being passed back
    # formType - should be bankCol
    # bankCol - the template column that this indexed column (templateCol) references
    if request.form['formType'] == 'bankCol':
        template_id = request.form['templateId']
        template_col = request.form['templateCol']
        stg_field = request.form['bankCol']
        q = '''update finance.import_template_map 
        set stg_field = %s where import_template_id = %s 
        and import_col_index =  %s'''
        v = (stg_field, template_id, template_col)
        write_query(q, db_conn, v)
        return ('', 204)
    return('',500)

@app.route('/bankTemplates/newtemp', methods=['POST','GET'])
def templateNewTemp():
    # page should be a form that asks for the template details then writes a template header ans one blank row into the tables
    # needs a template name, institution dropdown, header flag, institution
    if request.method == 'GET':
        form = newBankTemplate()
        form.getInstitutions(db_cursor)
        return render_template('bankTemplateNew.html', form=form)
    if request.method == 'POST':
        # get the request and make a new banktemplate
        tname = request.form['name']
        tinstitution = request.form['institution_id']
        theader_rows = request.form['header_rows']

        # mark for deletion:
        # if 'has_header' in request.form:
        #     thas_header = True
        # else:
        #     thas_header = False
        
        new = BankTemplate(acct_name=tname, institution_id=tinstitution, conn=db_conn, header_rows=theader_rows)
        return redirect(url_for('templateMaint'))

