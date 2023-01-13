from flask import request
from wtforms.validators import DataRequired
from wtforms import StringField, SubmitField, SelectField, EmailField, TextAreaField
from flask_wtf import FlaskForm



class BookmarkDocumentForm(FlaskForm):
    submit = SubmitField("Submit")



class SearchForm(FlaskForm):
    q = StringField("Search", validators=[DataRequired()])
    submit = SubmitField("Search")

    
    def __init__(self, *args, **kwargs): 
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args 
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False 
        super(SearchForm, self).__init__(*args, **kwargs)

class FeedbackForm(FlaskForm):
    name = StringField('Name (Optional)', validators=[])
    email = EmailField('Email (If you want response)')
    category = SelectField("Subject", choices=[('general', 'General Feedback'), ('recommendation', 'Recommendation'), ('problem', 'Website Problem'), ('thank_you', "Thank You")])
    text= TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Submit')