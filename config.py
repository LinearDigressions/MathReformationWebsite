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
