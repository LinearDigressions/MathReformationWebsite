from flask import render_template, abort, g, redirect, url_for, request, current_app, flash
from flask_login import current_user
from app.main import bp
from flask_login import login_required
from app.models import Category, Article, Feedback
from app import db
import markdown
from app.roles import admin_permission
from app.main.forms import SearchForm, FeedbackForm
import numpy as np




@bp.before_app_request
def before_request():
    g.search_form = SearchForm(meta={'csrf': False})

@bp.context_processor
def add_imports():
    return dict(admin_permission=admin_permission)

@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():
    math_category = Category.query.filter_by(name="math")[0]
    main_categories = math_category.children
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

@bp.route("/feedback", methods=["GET","POST"])
def feedback():
    form = FeedbackForm()

    if form.validate_on_submit():

        new_feedback = Feedback(
            name=form.name.data,
            email=form.email.data,
            text=form.text.data,
            category=form.category.data,
            is_resolved=False
        )

        db.session.add(new_feedback)
        db.session.commit()

        flash("Feedback Submitted!")
        return redirect(url_for('main.index'))

    return render_template('main/feedback.html', form=form)


@bp.route('/search')
def search():
  

    if not g.search_form.validate():
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    cat, cat_scores, cat_total = Category.search(g.search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])

    art, art_scores, art_total = Article.search(g.search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])

    cat = [("category", item) for item in cat]
    art = [("article", item) for item in art]

    scores = cat_scores + art_scores

    sorted_scores_idx = np.argsort(scores)

    total = cat_total + art_total

    results = np.array(cat + art)[sorted_scores_idx]

    
    if total > page * current_app.config['POSTS_PER_PAGE']:
        next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1)
    else:
        next_url = None 
    
    if page > 1:
        prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) 
    else:
        prev_url = None
    return render_template('main/search.html', title="Search", results=results,
    next_url=next_url, prev_url=prev_url)