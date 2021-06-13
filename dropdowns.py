from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField

class bankTemplateColNames(FlaskForm):
    colNames = SelectField('Column Name', choices=[(0,0)])

if __name__ == '__main__':
    pass

    

