# General Imports
from flask import Flask
from config import Config

# Flask Extensions
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_principal import Principal
from flask_admin import Admin
from flask_admin.contrib import rediscli
from flask_admin.contrib.fileadmin import FileAdmin
import os.path as op

from flask_mde import Mde
from flask_uploads import IMAGES, UploadSet, configure_uploads
from flaskext.markdown import Markdown
from elasticsearch import Elasticsearch
from flask_mail import Mail
from flask_compress import Compress
from flask_assets import Environment, Bundle



# For background tasks
from redis import Redis
import rq

# Logging Imports
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os

# Flask Principal Imports
from flask_login import current_user
from flask_principal import UserNeed, RoleNeed, identity_loaded
from app.roles import EditArticleNeed

# Initializing Extension Objects
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
principals = Principal()
admin = Admin(url="/admin_home")
mde = Mde()
mail = Mail()
compress = Compress()
assets = Environment()

# Creating Photo Manager
photos = UploadSet("photos", IMAGES)


def create_app(config_class=Config):

    # Creating App
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Registering Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.staff import bp as author_bp
    app.register_blueprint(author_bp)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp, url_prefix='/error')


    # Registering Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    login.login_view = 'auth.login'
    principals.init_app(app)
    admin.init_app(app)
    mde.init_app(app)
    Markdown(app)
    mail.init_app(app)
    compress.init_app(app)
    assets.init_app(app)


    # Registering Photo Manager
    configure_uploads(app, photos)


    # Registering Elastic Search If Available
    if app.config['ELASTICSEARCH_URL']:
        app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']])
        
    else:
        app.elasticsearch = None


    # Background tasks
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('mathreformation-tasks', connection=app.redis)
    path = op.join(op.dirname(__file__), 'static')
    admin.add_view(FileAdmin(path, '/static/', name='Static Files'))
    

    # Setting Up Admin Views
    admin.add_view(rediscli.RedisCli(app.redis))

    # Setting up Logger
    if not app.debug:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']) 
            secure = None
            if app.config['MAIL_USE_TLS']: 
                secure = ()
    
            mail_handler = SMTPHandler(mailhost=(app.config['MAIL_SERVER'], 
                app.config['MAIL_PORT']), fromaddr='no-reply@' + app.config['MAIL_SERVER'], 
                toaddrs=app.config['ADMINS'], subject='Math Reformation Failure', credentials=auth, 
                secure=secure) 

            mail_handler.setLevel(logging.ERROR) 
            app.logger.addHandler(mail_handler)

    # Storing and Initalizing Log System
    if not os.path.exists('logs'): 
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/mathreformation.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO) 
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO) 
    app.logger.info('Mathreformation startup')


    # Loads User Permissions and Needs
    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        # Set the identity user object
        identity.user = current_user
        # Add the UserNeed to the identity
        if hasattr(current_user, 'id'):
            identity.provides.add(UserNeed(current_user.id))

        # Assuming the User model has a list of roles, update the
        # identity with the roles that the user provides
        if hasattr(current_user, 'roles'):
            for role in current_user.roles:
                identity.provides.add(RoleNeed(role.name))

        # Adds need for every article where the user is the author
        if hasattr(current_user, 'articles'):
            for article in current_user.articles:
                identity.provides.add(EditArticleNeed(article.id))
        
    return app

from app import models

