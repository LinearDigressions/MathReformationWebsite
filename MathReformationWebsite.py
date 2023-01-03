from app import create_app, db
from app.models import Article, User, Category, Feedback, Role, CategoryType
from app.roles import admin_permission

app=create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Article': Article, 'User': User, 'Category':Category, 'Feedback':Feedback, 'Role':Role, 'CategoryType': CategoryType}

@app.context_processor
def add_imports():
    return dict(admin_permission=admin_permission)
