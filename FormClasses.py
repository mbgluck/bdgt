from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField, IntegerField, validators
from wtforms.fields.simple import HiddenField
from ProjectFunctions import read_query, write_query, write_return_query, set_field, return_query, modify_query

class csv_info(FlaskForm):
    has_headers = BooleanField(label='Headers?')
    account = SelectField('Account', [])
    bankTemplate = SelectField('Template', [])
    submit = SubmitField('Set File Info')

    def get_accounts(self, cursor):
        q = 'select account_id, description from finance.account where close_date is null and acct_institution_id is not null;'
        self.account.choices = return_query(q, cursor)

    def get_bankTemplate(self, cursor):
        q = 'select import_template_id, description from finance.import_template;'
        self.bankTemplate.choices = return_query(q, cursor)

class newBankTemplate(FlaskForm):
    # has_header = BooleanField(label='Headers?')
    header_rows = IntegerField('Template Name', [validators.Length(min=1, max=25)])
    name = StringField('Template Name', [validators.Length(min=1, max=25)])
    institution_id = SelectField('Institution', choices=[])
    submit = SubmitField('Create Template')
    # dropdowns for the form.
    def getInstitutions(self, cursor):
        q = 'select acct_institution_id, description from finance.acct_institution'
        query = return_query(q,cursor)
        self.institution_id.choices.extend(query)

class ModifyRecord(FlaskForm):
    pass

class CT_Test(FlaskForm):
    ct_test = SelectField('Charge Type', choices=[(0, '')]) # make sure to add validators
    cc_test = SelectField('Charge Category', choices=[(0, '')])
    tt_test = SelectField('Tracking Type', choices=[(0, '')])
    row_index = HiddenField('row_index')
    def __init__(self, *args, **kwargs):
        super(CT_Test, self).__init__(*args, **kwargs)
        conn = kwargs.get('conn')

        q = 'select charge_type_id, description from finance.charge_type order by description'
        query = read_query(q,conn)
        self.ct_test.choices.extend(query)
        q = 'select charge_category_id, description from finance.charge_category order by description'
        query = read_query(q,conn)
        self.cc_test.choices.extend(query)
        q = 'select charge_tracking_type_id, description from finance.charge_tracking_type order by description'
        query = read_query(q,conn)
        self.tt_test.choices.extend(query)

class chargeTypeForm(FlaskForm):
    chargeType = SelectField('Charge Type', choices=[(0, '')])
    def get_charge_type(self, conn):
        q = 'select charge_type_id, description from finance.charge_type order by description'
        query = read_query(q,conn)
        self.chargeType.choices.extend(query)

class chargeCategoryForm(FlaskForm):
    chargeCategory = SelectField('Charge Category', choices=[(0, '')])
    def get_charge_category(self, conn):
        q = 'select charge_category_id, description from finance.charge_category order by description'
        query = read_query(q,conn)
        self.chargeCategory.choices.extend(query)

class trackingTypeForm(FlaskForm):
    trackingType = SelectField('Tracking Type', choices=[(0, '')])
    def get_tracking_type(self, conn):
        q = 'select charge_tracking_type_id, description from finance.charge_tracking_type order by description'
        query = read_query(q,conn)
        self.trackingType.choices.extend(query)

