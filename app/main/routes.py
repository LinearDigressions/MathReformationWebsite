from flask import render_template, abort
from app.main import bp
from flask_login import login_required
from app.models import Category, Article
from app import db
import markdown

@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():
    main_categories = Category.query.filter_by(parents=None)
    return render_template('main/index.html', title="Home", main_categories=main_categories)

@bp.route("/about", methods=["GET"])
def about():
    return render_template('main/about.html', title="About")


@bp.route("/saved_articles", methods=["GET"])
@login_required
def saved_articles():
    return render_template('main/saved_articles.html', title="Saved Articles")


@bp.route("/article/<path>")
def article_page(path):
    article = db.first_or_404(Article.query.filter_by(path=path))
    return render_template('main/article.html', article=article)


@bp.route("/category/<path>")
def category_page(path):
    category = db.first_or_404(Category.query.filter_by(path=path))
    return render_template('main/category.html', category=category)