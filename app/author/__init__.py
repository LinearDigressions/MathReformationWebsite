from flask import Blueprint

bp = Blueprint('author', __name__)

from app.author import routes

