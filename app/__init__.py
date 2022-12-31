from flask import Flask

from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_principal import Principal
from flask_admin import Admin
from flask_mde import Mde
from flask_uploads import IMAGES, UploadSet, configure_uploads
from flaskext.markdown import Markdown



# Flask Principal signal stuff
from flask_login import current_user
from flask_principal import UserNeed, RoleNeed, identity_loaded

# Initializing Extension Objects
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
principals = Principal()
admin = Admin()
mde = Mde()



photos = UploadSet("photos", IMAGES)


def create_app(config_class=Config):

    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.author import bp as author_bp
    app.register_blueprint(author_bp)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    login.login_view = 'auth.login'
    principals.init_app(app)
    admin.init_app(app)
    mde.init_app(app)
    Markdown(app)

    configure_uploads(app, photos)

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
        
    return app


from app import models

