from flask import render_template, abort, g, redirect, url_for, request, current_app, flash, session
from flask_login import current_user
from app.main import bp
from flask_login import login_required
from app.models import Category, Article, Feedback, User, Document
from app import db
import markdown
from app.roles import admin_permission, author_permission
from app.main.forms import SearchForm, FeedbackForm, BookmarkArticleForm
import numpy as np
from app.email import send_feedback_email
import datetime
import calendar

# Used for search form
@bp.before_app_request
def before_request():
    g.search_form = SearchForm(meta={'csrf': False})

    if g.search_form.validate():
        print("here")
   
    


@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():

    #exploring_math_children = Document.query.filter_by(name="Exploring Math").first().children
    exploring_math_children = []
    recent_documents = Document.query.order_by(Document.date_added.desc()).filter_by(is_visible=True, ).limit(20)

    return render_template('main/index.html', title="Home", exploring_math_children=exploring_math_children, recent_documents=recent_documents)

@bp.route("/about", methods=["GET"])
def about():
    about_article = Article.query.filter_by(path='about').first()
    return render_template('main/about.html', title="About", about_article=about_article)

@bp.route("/profile", methods=["GET"])
@login_required
def profile():

    user = User.query.get(current_user.get_id())

    return render_template('main/profile.html', title="Profile", user=user)


@bp.route("/exploring_math/<path>", methods=["POST", "GET"])
def document_page(book_path=None, path=None):

    form = BookmarkArticleForm()

    document = db.first_or_404(Document.query.filter_by(path=path))

    if document.parent == None:
        abort(404)

    if document.document_type == "special":
        abort(404)

    if current_user.is_authenticated:

        user = User.query.get(current_user.get_id())
        
        if user.has_bookmarked_document(document):
            form.submit.label.text = "Unbookmark " + document.document_type.capitalize()
        else:
            form.submit.label.text = "Bookmark " + document.document_type.capitalize()
    else:
        user = None

    if form.validate_on_submit():
        if user.has_bookmarked_document(document):
            user.unbookmark_document(document)
        else:
            user.bookmark_document(document)
        db.session.commit()

        return redirect(url_for('main.document_page', path=path))


    breadcrumb_links = []
    doc = document

    while True:
        breadcrumb_links.append({"name":doc.name, "path":doc.path})
        doc = doc.parent

        if doc == None:
            break
        
    content = {}
    content["breadcrumb_links"] = breadcrumb_links
    content["document"] = document
    content["form"] = form
    content["user"] = user

    return render_template('main/document.html', **content, title=document.name)


@bp.route("/article/<path>", methods=["POST", "GET"])
def article_page(path):



    form = BookmarkArticleForm()

    article = db.first_or_404(Article.query.filter_by(path=path))

    if article.categories == []:
        abort(404)

    if article.categories[0].category_type == "special":
        abort(404)

    if current_user.is_authenticated:

        user = User.query.get(current_user.get_id())
        
        if user.has_saved_article(article):
            form.submit.label.text = "Unbookmark Article"
        else:
            form.submit.label.text = "Bookmark Article"
    else:
        user = None

    if form.validate_on_submit():
        if user.has_saved_article(article):
            user.unsave_article(article)
        else:
            user.save_article(article)
        db.session.commit()

        return redirect(url_for('main.article_page', path=path))
        

    content = {}

    content["article"] = article
    content["form"] = form
    content["user"] = user
    content["prev_page_url"] = article.prev_page_url
    content["next_page_url"] = article.next_page_url
    content["prev_page_name"] = article.prev_page_name
    content["next_page_name"] = article.next_page_name



    return render_template('main/article.html', **content, title=article.name)


@bp.route("/category/<path>")
def category_page(path):
    category = db.first_or_404(Category.query.filter_by(path=path))


    if category.parents == [] and category.category_type != "book":
        abort(404)


    content = {}

    content["category"] = category
    content["prev_page_url"] = category.prev_page_url
    content["next_page_url"] = category.next_page_url
    content["prev_page_name"] = category.prev_page_name
    content["next_page_name"] = category.next_page_name


    return render_template('main/category.html', **content, title =category.name)

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

        send_feedback_email(new_feedback)

        flash("Feedback Submitted!")
        return redirect(url_for('main.index'))

    return render_template('main/feedback.html', form=form, title="Feedback")


@bp.route('/search')
def search():
  

    if not g.search_form.validate():
        flash(g.search_form.errors)
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




@bp.route('/citation/<page_type>/<page_name>/<page_url>')
def citation(page_type, page_name, page_url):
    

    page_url = current_app.config["MAIN_URL"] + "/" + page_url.replace("%2F", "/")

    year = datetime.date.today().year
    month = datetime.date.today().month
    month = calendar.month_name[month]
    day = datetime.date.today().month


    if page_type == "Math Reformation":
        page_name = "Math Reformation - " + page_name

    if page_type == "Article":
        art = Article.query.filter_by(name=page_name).first()
        if art != None:
            year = art.date_added.year
            month = calendar.month_name[art.date_added.month]
            day = art.date_added.day

    

    return render_template('main/citation.html', page_type=page_type, page_url=page_url,
                            page_name=page_name, day=day, month=month, year=year, title="Citation")
