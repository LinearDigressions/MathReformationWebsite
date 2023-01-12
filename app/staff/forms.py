from flask_mde import MdeField
from flask_wtf import FlaskForm
from wtforms import SubmitField, FileField, StringField, TextAreaField, SelectMultipleField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, ValidationError
from app.models import Category, Article, Document



class EditingForm(FlaskForm):
    previous_name = None
    previous_path = None

    name = StringField("Name", validators=[DataRequired()])
    path = StringField('URL Path', validators=[DataRequired()])
    body = MdeField('Body')
    order = IntegerField("Order Number", validators=[DataRequired()])
    header = TextAreaField('Header')
    body = MdeField('Body')
    
    is_visible = BooleanField("Is Visible")

    save_draft_to_main = SubmitField("Save to Main")
    save_main_to_draft = SubmitField("Save as Draft")

    load_draft = SubmitField("Load Draft")
    load_main = SubmitField("Load Main")

    save_and_exit = SubmitField("Save and Exit")
    submit_continue_editing = SubmitField("Save and Continue Editing")

   
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
            raise ValidationError(self.category_type.capitalize() + ' must have a parent.')

    def validate_path(self, path):
        doc = Document.query.filter_by(path=path.data).first() 
        if doc is not None and path.data != self.previous_path:
            raise ValidationError('Please use a different document path.')

    def validate_name(self, name):
        doc = Document.query.filter_by(name=name.data).first() 
        if doc is not None and name.data != self.previous_name:
            raise ValidationError('Please use a different document name.')

   

class EditCategoryForm(EditingForm):
    parents = SelectMultipleField('Parent', choices=[])
    children = SelectMultipleField('Children', choices=[])
    category_type = SelectField('Category Type', choices=[])
    articles = SelectMultipleField('Articles', choices=[])

    def validate_parents(self, parents):
        if self.category_type in ["primary", "secondary"] and len(parents.data) == 0:
            raise ValidationError(self.category_type.capitalize() + ' category must have a parent category.')

    def validate_path(self, path):
        cat = Category.query.filter_by(path=path.data).first() 
        if cat is not None and path.data != self.previous_path:
            raise ValidationError('Please use a different category path.')

    def validate_name(self, name):
        cat = Category.query.filter_by(name=name.data).first() 
        if cat is not None and name.data != self.previous_name:
            raise ValidationError('Please use a different category name.')

class EditArticleForm(EditingForm):
    categories = SelectMultipleField('Categories', choices=[])

    def validate_path(self, path):
        art = Article.query.filter_by(path=path.data).first() 
        if art is not None and path.data != self.previous_path:
            raise ValidationError('Please use a different article path.')

    def validate_name(self, name):
        art = Article.query.filter_by(name=name.data).first() 
        if art is not None and name.data != self.previous_name:
            raise ValidationError('Please use a different article name.')



class AddPhotoForm(FlaskForm):
    photo = FileField('Photo')
    name = StringField("Name",validators=[DataRequired()])
    submit = SubmitField('Save')

class DeletePhotoForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    submit = SubmitField('Delete Photo')