from flask_mde import MdeField
from flask_wtf import FlaskForm
from wtforms import SubmitField, FileField, StringField, TextAreaField, SelectMultipleField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, ValidationError
from app.models import Document


class EditCategoryForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    path = StringField("Path",validators=[DataRequired()])
    documents = SelectMultipleField('Documents', choices=[])
    submit = SubmitField('Save')

class EditUpdateForm(FlaskForm):
    body = TextAreaField("Update",validators=[DataRequired()])
    submit = SubmitField('Save')
   
class EditDocumentForm(FlaskForm):
    previous_name = None
    previous_path = None

    name = StringField("Name", validators=[DataRequired()])
    path = StringField('URL Path', validators=[DataRequired()])
    body = MdeField('Body')
    order = IntegerField("Order Number", validators=[DataRequired()])
    header = TextAreaField('Header')
    body = MdeField('Body')

    parent = SelectField('Parent', choices=[])
    children = SelectMultipleField('Children', choices=[])
    categories = SelectMultipleField('Categories', choices=[])
    document_type = SelectField('Document Type', choices=[])
    
    is_visible = BooleanField("Is Visible")

    save_draft_to_main = SubmitField("Save to Main")
    save_main_to_draft = SubmitField("Save as Draft")

    load_draft = SubmitField("Load Draft")
    load_main = SubmitField("Load Main")

    save_and_exit = SubmitField("Save and Exit")
    submit_continue_editing = SubmitField("Save and Continue Editing")

    def validate_parent(self, parent):
        if self.document_type in ["chapter", "section", "article"] and len(parent.data) == 0:
            print("here")
            raise ValidationError(self.category_type.capitalize() + ' must have a parent.')

    def validate_path(self, path):
        doc = Document.query.filter_by(path=path.data).first() 
        if doc is not None and path.data != self.previous_path:
            raise ValidationError('Please use a different document path.')

    # Not enforcing uniqueness of names
    # def validate_name(self, name):
    #     doc = Document.query.filter_by(name=name.data).first() 
    #     if doc is not None and name.data.lower() != self.previous_name.lower():
    #         raise ValidationError('Please use a different document name.')

   
class AddPhotoForm(FlaskForm):
    photo = FileField('Photo')
    name = StringField("Name",validators=[DataRequired()])
    submit = SubmitField('Save')

class DeletePhotoForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    submit = SubmitField('Delete Photo')