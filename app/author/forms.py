from flask_mdeditor import  MDEditorField
from flask_wtf import FlaskForm
from wtforms import SubmitField, FileField
from wtforms.validators import DataRequired

class ArticleForm(FlaskForm):
    content = MDEditorField('Body', validators=[DataRequired()])
    submit = SubmitField()

class PhotoForm(FlaskForm):
    photo = FileField('Photo')
    submit = SubmitField('Submit')