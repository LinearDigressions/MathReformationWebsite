from flask_mde import MdeField
from flask_wtf import FlaskForm
from wtforms import SubmitField, FileField, StringField, TextAreaField, SelectMultipleField, SelectField
from wtforms.validators import DataRequired



class EditingForm(FlaskForm):


    name = StringField("Name", validators=[DataRequired()])
    path = StringField('URL Path', validators=[DataRequired()])
    body = MdeField('Body')
    header = TextAreaField('Header')
    items = SelectMultipleField('List', choices=[])
    parents = SelectMultipleField('Parents', choices=[])
    children = SelectMultipleField('Children', choices=[])
    submit = SubmitField("Save")
    submit_continue_editing = SubmitField("Save and Continue Editing")


class ArticleForm(FlaskForm):
    
    name = StringField('Article Name', validators=[DataRequired()])
    path = StringField('Article URL Path', validators=[DataRequired()])
    header = TextAreaField('Article Header')
    body = MdeField('Article Body', validators=[DataRequired()])
    categories = SelectMultipleField('Article Categories', choices=[])
    submit = SubmitField("Save")

class PhotoForm(FlaskForm):
    photo = FileField('Photo')
    submit = SubmitField('Save')