from flask import render_template
from app.main import bp
from flask_login import login_required


@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():
    return render_template('main/index.html', title="Home")

@bp.route("/about", methods=["GET"])
def about():
    return render_template('main/about.html', title="About")


@bp.route("/saved_articles", methods=["GET"])
@login_required
def saved_articles():
    return render_template('main/saved_articles.html', title="Saved Articles")