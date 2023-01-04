import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):

    # General Variables
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    TEMPLATES_AUTO_RELOAD = True

    # Database Variables
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Photo Manager Variables
    UPLOADED_PHOTOS_DEST = os.path.join(basedir, 'app/static/uploads')
    UPLOADS_AUTOSERVE = True


    # Pagination Variable
    POSTS_PER_PAGE = 10

    # Search Variable
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    # Mail Variables
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25) 
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None 
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') 
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # Admins will recieve email notifications on errors and feedback
    ADMINS = ['skylerboyer@gmail.com']

    


    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'