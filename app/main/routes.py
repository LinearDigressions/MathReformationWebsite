from flask import render_template
from app.main import bp


@bp.route("/", methods=["GET"])
def home():
    return render_template('home.html', title="Home")

