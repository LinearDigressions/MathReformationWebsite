from app import db, login
from datetime import datetime
from flask_login import UserMixin
# from flask import redirect, url_for, Response
# from app import admin
# from app import basic_auth
# from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash
 

# MODELS

saved_articles_table = db.Table('saved_articles',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    articles = db.relationship('Article', backref='author', lazy='dynamic')

    saved_articles = db.relationship('Article', secondary = saved_articles_table,
                                 backref=db.backref('articles', lazy=True), lazy=True)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


article_categories_table = db.Table('article_categories',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), index=True, unique=True)
    date_added = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)
    categories = db.relationship('Category', secondary = article_categories_table,
                                 backref=db.backref('articles', lazy=True), lazy=True)
    body = db.Column(db.String(), index=True, unique=True)
    header = db.Column(db.String(), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Article {}>'.format(self.title)

parent_child_table = db.Table('CategoryChild',
    db.Column('ParentChildId', db.Integer, primary_key=True),
    db.Column('ParentId', db.Integer, db.ForeignKey('category.id')),
    db.Column('ChildId', db.Integer, db.ForeignKey('category.id')))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    body = db.Column(db.String(), index=True, unique=True)
    header = db.Column(db.String(), index=True, unique=True)
    category_type = db.Column(db.String(15))

    parents = db.relationship('Category',secondary=parent_child_table,
        primaryjoin=id == parent_child_table.c.ChildId,
        secondaryjoin=id == parent_child_table.c.ParentId,
        backref= db.backref('children'))

    def __repr__(self):
        return '<Category %r>' % self.name

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(32), index=True, unique=False)
    email = db.Column(db.String(50))
    text = db.Column(db.String(2000), index=True, unique=True)
    status = db.Column(db.String(50))

    def __repr__(self):
        return '<Feedback %r>' % self.id


# LOGIN METHODS

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# class AuthException(HTTPException):
#     def __init__(self, message):
#         super().__init__(message, Response(
#             "You could not be authenticated. Please refresh the page.", 401,
#             {'WWW-Authenticate': 'Basic realm="Login Required"'}
#         ))


# class MyModelView(ModelView):
#     def is_accessible(self):
#         if not basic_auth.authenticate():
#             raise AuthException('Not authenticated.')
#         else:
#             return True

#     def inaccessible_callback(self, name, **kwargs):
#         return redirect(basic_auth.challenge())

# class LinkView(MyModelView):
#     column_searchable_list = ['name']
#     column_filters = ['categories']

# class FeedbackView(MyModelView):
#     column_filters=['category']



# admin.add_view(FeedbackView(Feedback, db.session))



# admin.add_view(MyModelView(Category, db.session))
# admin.add_view(LinkView(Link, db.session))