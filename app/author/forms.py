from flask_mde import MdeField
from flask_wtf import FlaskForm
from wtforms import SubmitField, FileField, StringField, TextAreaField, SelectMultipleField, SelectField
from wtforms.validators import DataRequired









class ArticleForm(FlaskForm):
    
    name = StringField('Article Name', validators=[DataRequired()])
    path = StringField('Article URL Path', validators=[DataRequired()])
    header = TextAreaField('Article Header')
    body = MdeField('Body', validators=[DataRequired()])
    #categories = SelectMultipleField(choices=[("1", 'Option 1'), ("2", "Option 2"), ("3", "Option 3")])
    categories = SelectMultipleField('Categories', choices=[])
    submit = SubmitField("Save")

class PhotoForm(FlaskForm):
    photo = FileField('Photo')
    submit = SubmitField('Save')