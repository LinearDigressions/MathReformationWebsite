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
from sqlalchemy.orm import backref, Mapper
import redis
import rq


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

bookmarked_documents_table = db.Table('bookmarked_documents',
    db.Column('document_id', db.Integer, db.ForeignKey('document.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    # Attributes
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    # Relations
    articles = db.relationship('Article', backref='author', lazy='dynamic')
    documents = db.relationship('Document', backref='author', lazy='dynamic')

    saved_articles = db.relationship('Article', secondary = saved_articles_table,
                                 backref=db.backref('saved_articles', lazy=True), lazy=True)
    
    bookmarked_documents = db.relationship('Document', secondary = bookmarked_documents_table,
                                 backref=db.backref('bookmarked_users', lazy=True), lazy=True)
    

    roles = db.relationship('Role', secondary = roles_table,
                            backref=db.backref('users', lazy=True), lazy=True)

    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    # Save Article Methods
    def save_article(self, article):
        if not self.has_saved_article(article):
            self.saved_articles.append(article)
    
    def unsave_article(self, article):
        if self.has_saved_article(article):
            self.saved_articles.remove(article)
    
    def has_saved_article(self, article): 
        return article in self.saved_articles

    def bookmark_document(self, document):
        if not self.has_bookmarked_document(document):
            self.bookmarked_documents.append(document)
    
    def unbookmark_document(self, document):
        if self.has_bookmarked_document(document):
            self.bookmarked_documents.remove(document)
    
    def has_bookmarked_document(self, document): 
        return document in self.bookmarked_documents


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



    def launch_task(self, name, description, *args, **kwargs):
        
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self) 
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self, complete=False).first()

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
    next_page_url = db.Column(db.String(64))
    prev_page_url = db.Column(db.String(50))
    next_page_name = db.Column(db.String(50))
    prev_page_name = db.Column(db.String(50))
    prev_page_type = db.Column(db.String(10))
    next_page_type = db.Column(db.String(10))


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
            sibling = siblings[idx + 1]
            if sibling.is_visible:
                return sibling
            else:
                return sibling.next_sibling()

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
            sibling = siblings[idx - 1]
            if sibling.is_visible:
                return sibling
            else:
                return sibling.prev_sibling()

    def update_prev_page_info(self):
        article_prev_sibling = self.prev_sibling()
        # If prev article in same category exists, then return that article

        if article_prev_sibling:
            self.prev_page_url = url_for('main.article_page', path=article_prev_sibling.path)
            self.prev_page_name = article_prev_sibling.name
            self.prev_page_type = "article"
        else:
            
            # If no next article, return the next secondary category.
            category_prev_sibling = self.categories[0].prev_sibling()

            if category_prev_sibling:

                prev_sibling_articles = category_prev_sibling.articles

                if prev_sibling_articles != []:
                    self.prev_page_url = url_for('main.article_page', path=prev_sibling_articles[-1].path)    
                    self.prev_page_name = prev_sibling_articles[-1].name
                    self.prev_page_type = "article"
                else:
                    self.prev_page_url = url_for('main.article_page', path=category_prev_sibling.path)    
                    self.prev_page_name = category_prev_sibling.name
                    self.prev_page_type = "article"
            else:

                self.prev_page_url = url_for('main.category_page', path=self.categories[0].path)    
                self.prev_page_name = self.categories[0].name
                self.prev_page_type = "category"


    def update_next_page_info(self):
        article_next_sibling = self.next_sibling()

        # If next article in same category exists, then return that article
        if article_next_sibling:
            self.next_page_url = url_for('main.article_page', path=article_next_sibling.path)
            self.next_page_name = article_next_sibling.name
            self.next_page_type = "article"
        else:
            # If no next article, return the next secondary category.
            category_next_sibling = self.categories[0].next_sibling()

            if category_next_sibling:
                self.next_page_url = url_for('main.category_page', path=category_next_sibling.path)    
                self.next_page_name = category_next_sibling.name
                self.next_page_type = "category"
            else:
                self.next_page_url = None
                self.next_page_name = None
                self.next_page_type = None

    def update_self_page_info(self):
        if self.categories[0].category_type == "special":
            return
        self.update_prev_page_info()
        self.update_next_page_info()

    def update_neighbors_page_info(self):
        if self.categories[0].category_type == "special":
            return
        if self.next_page_name != None and self.is_visible:
            if self.next_page_type == "article":
                Article.query.filter_by(name=self.next_page_name).first().update_prev_page_info()
            elif self.next_page_type == "category":
                Category.query.filter_by(name=self.next_page_name).first().update_prev_page_info()

        if self.prev_page_name != None and self.is_visible:
            if self.prev_page_type == "article":
                Article.query.filter_by(name=self.prev_page_name).first().update_next_page_info()
            elif self.prev_page_type == "category":
                Category.query.filter_by(name=self.prev_page_name).first().update_next_page_info()
                


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
    category_type = db.Column(db.String(10), index=True)
    next_page_url = db.Column(db.String(50))
    prev_page_url = db.Column(db.String(50))
    prev_page_type = db.Column(db.String(10))
    next_page_type = db.Column(db.String(10))
    next_page_name = db.Column(db.String(50))
    prev_page_name = db.Column(db.String(50))
    


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
        if self.category_type == "root":
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
            sibling = siblings[idx + 1]
            if sibling.is_visible:
                return sibling
            else:
                return sibling.next_sibling()

    def prev_sibling(self):
        if self.category_type == "root":
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
            sibling = siblings[idx - 1]
            if sibling.is_visible:
                return sibling
            else:
                return sibling.next_sibling()


    # To check if category has children (SHOULD CHANGE?)
    def get_num_children(self):
        return len(list(self.children))


    def update_next_page_info(self):
        if self.category_type == "special":
            self.next_page_url = None
            self.next_page_name = None
            self.next_page_type = None
        if self.category_type in ["root", "primary"]:
            category_children = self.ordered_children()

            # If category has sub categories, make the next page to the first sub categories
            if category_children.any():

                self.next_page_url = url_for('main.category_page', path=category_children[0].path)
                self.next_page_name = category_children[0].name
                self.next_page_type = 'category'

            # If no sub categories, then look for sibling category
            else:
                category_next_sibling = self.next_sibling()

                if category_next_sibling and self.category_type != "root":
                    next_page_url = url_for('main.category_page', path=category_next_sibling.path)
                    next_page_name = category_next_sibling[0].name
                    self.next_page_type = 'category'
                else:
                    self.next_page_name = None
                    self.next_page_url = None
                    self.next_page_type = None


        
        # If the category can have articles, look for first available article
        else:
            category_ordered_articles = self.articles
            if category_ordered_articles != []:
                self.next_page_url = url_for('main.article_page', path=category_ordered_articles[0].path)
                self.next_page_name = category_ordered_articles[0].name
                self.next_page_type = 'article'

            # If category has no articles, then choose sibling
            else: 
                category_next_sibling = self.next_sibling()

                if category_next_sibling:
                    self.next_page_url = url_for('main.category_page', path=category_next_sibling.path)
                    self.next_page_name = category_next_sibling[0].name
                    self.next_page_type = 'category'
                else:
                    self.next_page_name = None
                    self.next_page_url = None
                    self.next_page_type = None



    def update_prev_page_info(self):
        if self.category_type == "special":
            self.prev_page_name = None
            self.prev_page_url = None
            self.prev_page_type = None

        # Root category can't have previous page
        if self.category_type == "root":
            self.prev_page_url = None
            self.prev_page_name = None
            self.prev_page_type = None
        else:
            category_prev_sibling = self.prev_sibling()

            if category_prev_sibling:

                prev_sibling_articles = category_prev_sibling.ordered_articles()

                if prev_sibling_articles != []:
                    self.prev_page_url = url_for('main.article_page', path=prev_sibling_articles[-1].path)
                    self.prev_page_name = prev_sibling_articles[-1].name
                    self.prev_page_type = "article"
                else:
                    self.prev_page_url = url_for('main.category_page', path=category_prev_sibling.path)
                    self.prev_page_name = category_prev_sibling.name
                    self.prev_page_type = "category"
            else:
                self.prev_page_url = url_for('main.category_page', path=self.parents[0].path)
                self.prev_page_name = self.parents[0].name
                self.prev_page_type = "category"

    def update_self_page_info(self):
        if self.category_type == "special":
            return
        self.update_prev_page_info()
        self.update_next_page_info()

    def update_neighbors_page_info(self):
        if self.category_type == "special":
            return
        if self.next_page_name != None and self.is_visible:
            if self.next_page_type == "article":
                Article.query.filter_by(name=self.next_page_name).first().update_prev_page_info()
            elif self.next_page_type == "category":
                Category.query.filter_by(name=self.next_page_name).first().update_prev_page_info()

        if self.prev_page_name != None and self.is_visible:
            if self.prev_page_type == "article":
                Article.query.filter_by(name=self.prev_page_name).first().update_next_page_info()
            elif self.prev_page_type == "category":
                Category.query.filter_by(name=self.prev_page_name).first().update_next_page_info()
                

    def __repr__(self):
        return '<Category ' + self.name +'>'


class Document(SearchableMixin, db.Model):

    __tablename__ = "document"

    # Attributes that are indexed by search engine
    __searchable__ = ["body_main", "name"]

    # Attributes
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=False)
    path = db.Column(db.String(250), unique=True, nullable=False)
    body_main = db.Column(db.String(), index=True)
    body_draft = db.Column(db.String(), index=True)
    date_added = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)
    header = db.Column(db.String(), index=True)
    order = db.Column(db.Integer())
    is_visible = db.Column(db.Boolean())
    document_type = db.Column(db.String(10), index=True)


    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    

    prev_page_id = db.Column(db.Integer(), db.ForeignKey("document.id"))
    next_page = db.relationship("Document", backref=backref("prev_page", remote_side=[id]), uselist=False, foreign_keys=[prev_page_id])

    parent_id = db.Column(db.Integer(), db.ForeignKey("document.id"))
    children = db.relationship("Document", backref=backref("parent", remote_side=[id]), foreign_keys=[parent_id])


    # For displaying articles/categories in specific order
    def ordered_children(self):

        if self.children == []:
            return []

        children_idx = np.array([child.order if child.order else 1 for child in self.children])
        sorted_children_idx = np.argsort(children_idx)
        return self.children[sorted_children_idx]


    # For getting next/prev category for articles at the beginning or end of a category

    def find_next_sibling(self):

        if self.parent == None:
            return None

        else:
            siblings = self.parent.ordered_children()

            if self == siblings[-1]:
                return None

            else:
                idx = siblings.index(self)
                return siblings[idx + 1]

    def find_prev_sibling(self):

        if self.parent == None:
            return None
            
        else:
            siblings = self.parent.ordered_children()

            if self == siblings[0]:
                return self.parent.find_prev_sibling()

            else:

                idx = siblings.index(self)
                return siblings[idx - 1]

    def find_next_page(self):

        if self.children != []:
            return self.ordered_children[0]

        else:

            doc = self

            while True:
                next_sibling = doc.find_next_sibling()

                if next_sibling == None:
                    doc = doc.parent
                else:
                    return next_sibling

                if doc.document_type == "book":
                    return None
    
    def find_prev_page(self):

        doc = self

        while True:
            prev_sibling = doc.find_prev_sibling()

            if prev_sibling == None:
                doc = doc.parent 
            else:
                break

            if doc.document_type == "book":
                return None

        while True:

            if doc.children == []:
                return doc
            else:
                doc = doc.children[-1]
  
    def set_links(self):
        self.prev_page = self.find_prev_page()
        self.next_page = self.find_next_page()

    def remove_links(self):
        if self.prev_page == None and self.next_page == None:
            return

        self.prev_page.next_page = self.next_page.prev_page
        self.prev_page = None
        self.next_page = None

    def update_path(self):
        self.path = ""

        doc = self

        while True:

            self.path = "/" + doc.name.lower().replace(" ", "_") + self.path

            if doc.document_type == "book":
                break
            else:
                doc = doc.parent


    def __repr__(self):
        return '<Document ' + self.name + '>'



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


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) 
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self): 
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis) 
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None 
        return rq_job

    def get_progress(self):
        job = self.get_rq_job() 
        return job.meta.get('progress', 0) if job is not None else 100


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
admin.add_view(AdminModelView(Task, db.session))
admin.add_view(AdminModelView(Document, db.session))
