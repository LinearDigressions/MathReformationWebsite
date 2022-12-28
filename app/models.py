from app import db
from datetime import datetime
# from flask import redirect, url_for, Response
# from app import admin
# from app import basic_auth
# from werkzeug.exceptions import HTTPException
 

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    articles = db.relationship('Article', backref='author', lazy='dynamic')
    def __repr__(self):
        return '<User {}>'.format(self.username)


article_categories = db.Table('article_categories',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), index=True, unique=True)
    date_added = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)
    categories = db.relationship('Category', secondary = article_categories,
                                 backref=db.backref('articles', lazy=True), lazy=True)
    body = db.Column(db.String(), index=True, unique=True)
    header = db.Column(db.String(), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Article {}>'.format(self.title)

parent_child = db.Table('CategoryChild',
    db.Column('ParentChildId', db.Integer, primary_key=True),
    db.Column('ParentId', db.Integer, db.ForeignKey('category.id')),
    db.Column('ChildId', db.Integer, db.ForeignKey('category.id')))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    body = db.Column(db.String(), index=True, unique=True)
    header = db.Column(db.String(), index=True, unique=True)
    category_type = db.Column(db.String(15))

    parents = db.relationship('Category',secondary=parent_child,
        primaryjoin=id == parent_child.c.ChildId,
        secondaryjoin=id == parent_child.c.ParentId,
        backref= db.backref('children'))

    def __repr__(self):
        return '<Category %r>' % self.name



class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(32), index=True, unique=False)
    text = db.Column(db.String(2048), index=True, unique=True)
    status = db.Column(db.String(500))

    def __repr__(self):
        return '<Recommmendation %r>' % self.id



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