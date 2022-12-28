from app import create_app, db
from app.models import Article, User, Category, Feedback, Role


app=create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Article': Article, 'User': User, 'Category':Category, 'Feedback':Feedback, 'Role':Role}