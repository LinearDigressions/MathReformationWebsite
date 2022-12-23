from flask import render_template
from app.main import bp


@bp.route("/", methods=["GET"])
def home():
    return render_template('home.html', title="Home")

@bp.route("/about", methods=["GET"])
def about():
    return render_template('about.html', title="About")