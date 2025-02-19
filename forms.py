from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField, SelectField, IntegerField, SubmitField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange



class CustomerForm(FlaskForm):
    given_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    surname = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    streetaddress = StringField('Street Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    zipcode = StringField('Zip Code', validators=[DataRequired()])
    country = StringField('Country', validators=[DataRequired()])
    country_code = StringField('Country Code', validators=[DataRequired()])
    birthday = DateField('Birthday', format='%Y-%m-%d', validators=[DataRequired()])
    national_id = StringField('National ID', validators=[DataRequired(), Length(min=5, max=20)])
    telephone_country_code = StringField('Telephone Country Code', validators=[DataRequired()])
    telephone = StringField('Telephone Number', validators=[DataRequired()])
    email_address = StringField('Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Save Customer')

class AccountForm(FlaskForm):
    account_type = SelectField(
        'Kontotyp',
        choices=[('savings', 'Sparkonto'), ('checking', 'Cheching'),('personal','Personal')],
        validators=[DataRequired()]
    )
 
    initial_balance = DecimalField(
        'Initial saldo',
        validators=[DataRequired(), NumberRange(min=0)],
        places=2
    )
    submit = SubmitField('Skapa Konto')