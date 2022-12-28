from flask import render_template
from app.main import bp


@bp.route("/", methods=["GET"])
def index():
    return render_template('main/index.html', title="Home")

@bp.route("/about", methods=["GET"])
def about():
    return render_template('main/about.html', title="About")