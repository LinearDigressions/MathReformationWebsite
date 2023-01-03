import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    TEMPLATES_AUTO_RELOAD = True

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MDEDITOR_FILE_UPLOADER = os.path.join(basedir, 'app/static/uploads')
    MDEDITOR_LANGUAGE = "en"

    UPLOADED_PHOTOS_DEST = os.path.join(basedir, 'app/static/uploads')
    UPLOADS_AUTOSERVE = True

    POSTS_PER_PAGE = 10
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')


    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25) 
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None 
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') 
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['skylerboyer@gmail.com']


