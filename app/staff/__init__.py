from flask import Blueprint

bp = Blueprint('author', __name__)

from app.staff import routes

