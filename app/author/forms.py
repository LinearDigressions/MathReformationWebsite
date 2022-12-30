from flask_mde import MdeField
from flask_wtf import FlaskForm
from wtforms import SubmitField, FileField, StringField, TextAreaField, SelectMultipleField, SelectField
from wtforms.validators import DataRequired



class CategoryForm(FlaskForm):

    def __init__(self, doc_type):
        self.doc_type = "10"

    def test(self):
        print(self.doc_type)



    #name = StringField(self.doc_type + 'Name', validators=[DataRequired()])
    path = StringField('Category URL Path', validators=[DataRequired()])
    body = MdeField('Article Body', validators=[DataRequired()])
    header = TextAreaField('Article Header')
    articles = SelectMultipleField('Category Articles', choices=[])
    submit = SubmitField("Save")


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