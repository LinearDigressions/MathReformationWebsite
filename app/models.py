from app import db, login, admin
from datetime import datetime
from flask_login import UserMixin
from flask import redirect, url_for, request, current_app
from app.roles import admin_permission
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
import os.path as op

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


# User has role(s)
roles_table = db.Table('roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

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
    documents = db.relationship('Document', backref='author', lazy='dynamic')

    bookmarked_documents = db.relationship('Document', secondary = bookmarked_documents_table,
                                 backref=db.backref('bookmarked_users', lazy=True), lazy=True)


    roles = db.relationship('Role', secondary = roles_table,
                            backref=db.backref('users', lazy=True), lazy=True)

    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    # Save Article Methods

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


class Document(SearchableMixin, db.Model):

    __tablename__ = "document"

    # Attributes that are indexed by search engine
    __searchable__ = ["body_main", "name"]

    # Attributes
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=False, index=True)
    path = db.Column(db.String(250), unique=True, nullable=False, index=True)
    body_main = db.Column(db.Text())
    body_draft = db.Column(db.String(50000))
    date_added = db.Column(db.DateTime, nullable=False,
        default=datetime.utcnow)
    header = db.Column(db.String(50000))
    order = db.Column(db.Integer())
    is_visible = db.Column(db.Boolean())
    document_type = db.Column(db.String(10), index=True)


    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))



    prev_page_id = db.Column(db.Integer(), db.ForeignKey("document.id"))
    next_page = db.relationship("Document", backref=backref("prev_page", remote_side=[id]), uselist=False, foreign_keys=[prev_page_id])

    parent_id = db.Column(db.Integer(), db.ForeignKey("document.id"))
    children = db.relationship("Document", backref=backref("parent", remote_side=[id]), foreign_keys=[parent_id])

    def make_visible_on_index(self):
        add_to_index(self.__tablename__, self)

    def make_invisible_on_index(self):
        remove_from_index(self.__tablename__, self)

    # For displaying articles/categories in specific order
    def ordered_children(self):
        print(self.children)

        children = [child for child in self.children if child.is_visible]

        if self.children == []:
            return []

        children_idx = np.array([child.order if child.order != None else 0 for child in children])
        print(children_idx)
        sorted_children_idx = np.argsort(children_idx)
        print(sorted_children_idx)

        return np.array(self.children)[sorted_children_idx]


    # For getting next/prev category for articles at the beginning or end of a category

    def find_next_sibling(self):

        if self.parent == None:
            return None

        else:
            siblings = self.parent.ordered_children()

            if self == siblings[-1]:
                return None

            else:
                idx = np.where(siblings==self)[0][0]
                return siblings[idx + 1]

    def find_prev_sibling(self):

        if self.parent == None:
            return None

        else:
            siblings = self.parent.ordered_children()

            if self == siblings[0]:
                return self.parent.find_prev_sibling()

            else:

                idx = np.where(siblings==self)[0][0]
                return siblings[idx - 1]

    def find_next_page(self):

        if self.children != []:
            return self.children[0]

        next_sibling = self.find_next_sibling()

        if next_sibling == None and self.parent != None:
            return self.parent.find_next_sibling()
        else:
            return next_sibling
        # if self.children != []:
        #     return self.ordered_children[0]

        # else:

        #     doc = self

        #     while True:
        #         next_sibling = doc.find_next_sibling()

        #         if next_sibling == None:
        #             doc = doc.parent
        #             if doc==None:
        #                 return None
        #         else:
        #             return next_sibling

        #         if doc.document_type == "book":
        #             return None

    def find_prev_page(self):

        prev_sibling = self.find_prev_sibling()

        if prev_sibling == None and self.parent != None:
            return self.parent
        else:
            return prev_sibling

        # doc = self

        # while True:
        #     prev_sibling = doc.find_prev_sibling()

        #     if prev_sibling == None:
        #         doc = doc.parent

        #         if doc == None:
        #             return None
        #     else:
        #         break

        #     if doc.document_type == "book":
        #         return None

        # while True:

        #     if doc.children == []:
        #         return doc
        #     else:
        #         doc = doc.children[-1]

    def set_links(self):
        self.prev_page = self.find_prev_page()
        self.next_page = self.find_next_page()

    def remove_links(self):
        if self.prev_page == None and self.next_page == None:
            return
        elif self.prev_page == None:
            self.next_page.prev_page = None
        elif self.next_page == None:
            self.prev_page.next_page = None
        else:
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

class AdminFileView(FileAdmin):

    def is_accessible(self):
        return admin_permission.can()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

# Adding admin views for all objects
admin.add_view(AdminModelView(Feedback, db.session))
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Role, db.session))
admin.add_view(AdminModelView(Task, db.session))
admin.add_view(AdminModelView(Document, db.session))
path = op.join(op.dirname(__file__), 'static')
admin.add_view(AdminFileView(path, '/static/', name='Static Files'))