from app import db, login, admin
from datetime import datetime
from flask_login import UserMixin
from flask import redirect, url_for, request
from app.roles import admin_permission
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash
from app.search import add_to_index, remove_from_index, query_index


# Search Mixin
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




# MODELS

saved_articles_table = db.Table('saved_articles',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

roles_table = db.Table('roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    articles = db.relationship('Article', backref='author', lazy='dynamic')

    saved_articles = db.relationship('Article', secondary = saved_articles_table,
                                 backref=db.backref('articles', lazy=True), lazy=True)
    
    roles = db.relationship('Role', secondary = roles_table,
                                 backref=db.backref('users', lazy=True), lazy=True)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return '<Role {}>'.format(self.name)


article_categories_table = db.Table('article_categories',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Article(SearchableMixin, db.Model):

    __searchable__ = ["body_main", "name"]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    path = db.Column(db.String(50), unique=True)
    date_added = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)
    categories = db.relationship('Category', secondary = article_categories_table,
                                 backref=db.backref('articles', lazy=True), lazy=True)
    body_main = db.Column(db.String(), index=True)
    body_draft = db.Column(db.String(), index=True)
    is_visible = db.Column(db.Boolean())
    header = db.Column(db.String(), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Article {}>'.format(self.name)

parent_child_table = db.Table('CategoryChild',
    db.Column('ParentChildId', db.Integer, primary_key=True),
    db.Column('ParentId', db.Integer, db.ForeignKey('category.id')),
    db.Column('ChildId', db.Integer, db.ForeignKey('category.id')))

class Category(SearchableMixin, db.Model):

    __searchable__ = ["body_main", "name"]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    path = db.Column(db.String(50), unique=True)
    body_main = db.Column(db.String(), index=True)
    body_draft = db.Column(db.String(), index=True)
    header = db.Column(db.String(), index=True)
    category_type = db.Column(db.String(15))
    is_visible = db.Column(db.Boolean())

    parents = db.relationship('Category',secondary=parent_child_table,
        primaryjoin=id == parent_child_table.c.ChildId,
        secondaryjoin=id == parent_child_table.c.ParentId,
        backref= db.backref('children'))

    def __repr__(self):
        return '<Category %r>' % self.name

    def get_num_children(self):
        return len(list(self.children))

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    category = db.Column(db.String(32), index=True)
    email = db.Column(db.String(50))
    text = db.Column(db.String(2000), index=True)
    is_resolved = db.Column(db.Boolean())

    def __repr__(self):
        return '<Feedback %r>' % self.id


# LOGIN METHODS

@login.user_loader
def load_user(id):
    return User.query.get(int(id))




class AdminModelView(ModelView):

    def is_accessible(self):
        return admin_permission.can()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))


admin.add_view(AdminModelView(Feedback, db.session))
admin.add_view(AdminModelView(Category, db.session))
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Article, db.session))
admin.add_view(AdminModelView(Role, db.session))
