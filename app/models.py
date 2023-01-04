from app import db, login, admin
from datetime import datetime
from flask_login import UserMixin
from flask import redirect, url_for, request, current_app
from app.roles import admin_permission
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash
from app.search import add_to_index, remove_from_index, query_index
import numpy as np
from time import time
import jwt
from sqlalchemy.orm import backref


# SEARCH MIXIN
class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, scores, total = query_index(cls.__tablename__, expression, page, per_page) 
        if total == 0:
            return cls.query.filter_by(id=0), [], 0 
        when = []
        for i in range(len(ids)): 
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by( db.case(when, value=cls.id)), scores, total

    @classmethod
    def before_commit(cls, session): 
        session._changes = {'add': list(session.new), 
                            'update': list(session.dirty), 
                            'delete': list(session.deleted)}

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin): 
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']: 
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj) 
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin): 
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(obj.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit) 
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)




# RELATION TABLES

# User saves articles
saved_articles_table = db.Table('saved_articles',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# User has role(s)
roles_table = db.Table('roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

# Article belongs to category (categories)
article_categories_table = db.Table('article_categories',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

# Parent Category has Children Categories
parent_child_table = db.Table('CategoryChild',
    db.Column('ParentChildId', db.Integer, primary_key=True),
    db.Column('ParentId', db.Integer, db.ForeignKey('category.id')),
    db.Column('ChildId', db.Integer, db.ForeignKey('category.id')))


class User(UserMixin, db.Model):
    # Attributes
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    # Relations
    articles = db.relationship('Article', backref='author', lazy='dynamic')

    saved_articles = db.relationship('Article', secondary = saved_articles_table,
                                 backref=db.backref('saved_articles', lazy=True), lazy=True)
    
    roles = db.relationship('Role', secondary = roles_table,
                                 backref=db.backref('users', lazy=True), lazy=True)

    # Save Article Methods
    def save_article(self, article):
        if not self.has_saved_article(article):
            self.saved_articles.append(article)
    
    def unsave_article(self, article):
        if self.has_saved_article(article):
            self.saved_articles.remove(article)
    
    def has_saved_article(self, article): 
        return article in self.saved_articles


    # Login Methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600): 
        return jwt.encode({'reset_password': self.id, 'exp': time() + expires_in}, 
                            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token): 
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return '<Role {}>'.format(self.name)


class Article(SearchableMixin, db.Model):

    # Attributes that are indexed by search engine
    __searchable__ = ["body_main", "name"]


    # Attributes
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    path = db.Column(db.String(50), unique=True, nullable=False)
    date_added = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)
    body_main = db.Column(db.String(), index=True)
    body_draft = db.Column(db.String(), index=True)
    is_visible = db.Column(db.Boolean())
    header = db.Column(db.String(), index=True)
    order = db.Column(db.Integer())


    # Foreign key for user writing articles
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


    # Relations
    categories = db.relationship('Category', secondary = article_categories_table,
                                 backref=db.backref('articles', lazy=True), lazy=True)


    # For generating next/prev links on article pages
    def next_sibling(self):
        if not self.categories:
            return None
        secondary_category = self.categories[0]
        siblings = secondary_category.ordered_articles()
        if len(siblings) == 0:
            return None
        num_siblings = len(siblings)
        idx = np.where(siblings == self)[0][0]
        if idx + 2 > num_siblings:
            return None
        else:
            return siblings[idx + 1]

    def prev_sibling(self):
        if not self.categories:
            return None
        secondary_category = self.categories[0]
        siblings = secondary_category.ordered_articles()
        if len(siblings) == 0:
            return None
        idx = np.where(siblings == self)[0][0]
        if idx == 0:
            return None
        else:
            return siblings[idx - 1]


    def __repr__(self):
        return '<Article {}>'.format(self.name)


class Category(SearchableMixin, db.Model):

    # Attributes that are indexed by search engine
    __searchable__ = ["body_main", "name"]


    # Attributes
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    path = db.Column(db.String(50), unique=True, nullable=False)
    body_main = db.Column(db.String(), index=True)
    body_draft = db.Column(db.String(), index=True)
    header = db.Column(db.String(), index=True)
    order = db.Column(db.Integer())
    is_visible = db.Column(db.Boolean())
    

    # Foreign Key for CategoryType relation
    categorytype_id = db.Column(db.Integer, db.ForeignKey('categorytype.id'))


    # Relations
    parents = db.relationship('Category',secondary=parent_child_table,
        primaryjoin=id == parent_child_table.c.ChildId,
        secondaryjoin=id == parent_child_table.c.ParentId,
        backref= db.backref('children'))


    # For displaying articles/categories in specific order
    def ordered_children(self):
        if not self.children:
            return []
        children = np.array(self.children)
        children_idx = np.array([child.order if child.order else 1 for child in children])
        sorted_children_idx = np.argsort(children_idx)
        return children[sorted_children_idx]

    def ordered_articles(self):
        if not self.articles:
            return []
        articles = np.array(self.articles)
        articles_idx = np.array([article.order if article.order else 1 for article in articles])
        sorted_articles_idx = np.argsort(articles_idx)
        return articles[sorted_articles_idx]


    # For getting next/prev category for articles at the beginning or end of a category
    def next_sibling(self):
        if self.category_type.name == "root":
            return None

        if not self.parents:
            return None
        parent = self.parents[0]
        siblings = parent.ordered_children()
        if len(siblings) == 0:
            return None
        num_siblings = len(siblings)
        idx = np.where(siblings == self)[0][0]
        if idx + 2 > num_siblings:
            return None
        else:
            return siblings[idx + 1]

    def prev_sibling(self):
        if self.category_type.name == "root":
            return None

        if not self.parents:
            return None
            
        parent = self.parents[0]
        siblings = parent.ordered_children()
        if len(siblings) == 0:
            return None
        idx = np.where(siblings == self)[0][0]
        if idx == 0:
            return None
        else:
            return siblings[idx - 1]

    # To check if category has children (SHOULD CHANGE?)
    def get_num_children(self):
        return len(list(self.children))

    def __repr__(self):
        return '<Category ' + self.name +'>'

class CategoryType(db.Model):
    # Added to resolve errors
    __tablename__ = "categorytype"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    # Foreign key for parent/child relation
    parent_id = db.Column(db.Integer, db.ForeignKey('categorytype.id'))

    # Relations
    categories = db.relationship('Category', backref='category_type', lazy='dynamic')
    parent = db.relationship('CategoryType', remote_side=[id], backref='child')

    def __repr__(self):
        return '<Category Type %r>' % self.name


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    category = db.Column(db.String(32), index=True)
    email = db.Column(db.String(50))
    text = db.Column(db.String(2000), index=True)
    is_resolved = db.Column(db.Boolean())

    def __repr__(self):
        return '<Feedback %r>' % self.id

# View that only permits admins to see content
class AdminModelView(ModelView):

    def is_accessible(self):
        return admin_permission.can()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

# Adding admin views for all objects
admin.add_view(AdminModelView(Feedback, db.session))
admin.add_view(AdminModelView(Category, db.session))
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Article, db.session))
admin.add_view(AdminModelView(Role, db.session))
admin.add_view(AdminModelView(CategoryType, db.session))
