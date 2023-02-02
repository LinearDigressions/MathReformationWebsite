from app import create_app, db
from app.models import User, Feedback, Role, Task, Document, Category, Update
from app.roles import admin_permission, author_permission, editor_permission
from flask import g

app=create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db,'User': User,'Feedback':Feedback, 'Role':Role, 'Task':Task, 'Document':Document, 'Category':Category, 'Update':Update}


# Adding permissions so that they are available on every page/template
@app.context_processor
def add_imports():
    return dict(admin_permission=admin_permission, author_permission=author_permission, editor_permission=editor_permission, g=g)
