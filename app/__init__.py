from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Initializing Extension Objects
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()

def create_app(config_class=Config):

    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    login.login_view = 'auth.login'
    
    return app


from app import models