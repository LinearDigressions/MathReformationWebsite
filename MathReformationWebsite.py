from app import create_app, db
from app.models import Article, User, Category, Feedback, Role, Task
from app.roles import admin_permission, author_permission
from flask import g

app=create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Article': Article, 'User': User, 
            'Category':Category, 'Feedback':Feedback, 'Role':Role, 'Task':Task}


# Adding permissions so that they are available on every page
@app.context_processor
def add_imports():
    return dict(admin_permission=admin_permission, author_permission=author_permission, g=g)
