from flask_mde import MdeField
from flask_wtf import FlaskForm
from wtforms import SubmitField, FileField, StringField, TextAreaField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired



class EditingForm(FlaskForm):


    name = StringField("Name", validators=[DataRequired()])
    path = StringField('URL Path', validators=[DataRequired()])
    body = MdeField('Body')
    header = TextAreaField('Header')
    items = SelectMultipleField('List', choices=[])
    parents = SelectMultipleField('Parents', choices=[])
    children = SelectMultipleField('Children', choices=[])
    is_visible = BooleanField("Is Visible")

    save_draft_to_main = SubmitField("Save to Main")
    save_main_to_draft = SubmitField("Save as Draft")


    load_draft = SubmitField("Load Draft")
    load_main = SubmitField("Load Main")

    save_and_exit = SubmitField("Save and Exit")

    submit_continue_editing = SubmitField("Save and Continue Editing")


class ArticleForm(FlaskForm):
    
    name = StringField('Article Name', validators=[DataRequired()])
    path = StringField('Article URL Path', validators=[DataRequired()])
    header = TextAreaField('Article Header')
    body = MdeField('Article Body', validators=[DataRequired()])
    categories = SelectMultipleField('Article Categories', choices=[])
    
    submit = SubmitField("Save")

class AddPhotoForm(FlaskForm):
    photo = FileField('Photo')
    name = StringField("Name",validators=[DataRequired()])
    submit = SubmitField('Save')

class DeletePhotoForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    submit = SubmitField('Delete Photo')