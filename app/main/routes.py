from flask import render_template, abort, g, redirect, url_for, request, current_app, flash, session
from flask_login import current_user
from app.main import bp
from flask_login import login_required
from app.models import Feedback, User, Document, Category
from app import db
import markdown
from app.roles import admin_permission, author_permission
from app.main.forms import SearchForm, FeedbackForm, BookmarkDocumentForm
import numpy as np
from app.email import send_feedback_email
import datetime
import calendar
import json


import git
import hmac
import hashlib
from flask_github_signature import verify_signature


# Used for search form
@bp.before_app_request
def before_request():

    if current_app.elasticsearch != None:
        g.search_form = SearchForm(meta={'csrf': False})


@bp.route('/update_server', methods=['POST'])
@verify_signature
def webhook():
    repo = git.Repo('/home/LinearDigressions/MathReformationWebsite')
    origin = repo.remotes.origin
    origin.pull()
    return 'Updated PythonAnywhere successfully', 200

   

@bp.route("/home", methods=["GET"])
@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():

    home_article = Document.query.filter_by(path='home').first()

    recent_documents = Document.query.order_by(Document.date_added.desc()).filter_by(is_visible=True, ).limit(5)

    return render_template('main/index.html', title="Home", home_article=home_article, recent_documents=recent_documents)

@bp.route("/about", methods=["GET"])
def about():
    about_article = Document.query.filter_by(path='about').first()
    return render_template('main/about.html', title="About", about_article=about_article)

@bp.route("/profile", methods=["GET"])
@login_required
def profile():

    user = User.query.get(current_user.get_id())

    return render_template('main/profile.html', title="Profile", user=user)

def generate_table_of_contents(root):
    children = []
    for child in root.ordered_children():
        children.append(generate_table_of_contents(child))
    table_of_contents = {'name':root.name,'path':root.path, 'children':children}
    return table_of_contents



@bp.route("/document/<path>", methods=["GET", "POST"])
def document_page(path):

    form = BookmarkDocumentForm()

    document = db.first_or_404(Document.query.filter_by(path=path))

    if document.document_type == "special":
        abort(404)

    if current_user.is_authenticated:

        user = User.query.get(current_user.get_id())
        is_bookmarked = user.has_bookmarked_document(document)
        
        # if user.has_bookmarked_document(document):
        #     form.submit.label.text = "Unbookmark " + document.document_type.capitalize()
        # else:
        #     form.submit.label.text = "Bookmark " + document.document_type.capitalize()
    else:
        user = None
        is_bookmarked = None

    if form.validate_on_submit():
        if user.has_bookmarked_document(document):
            user.unbookmark_document(document)
        else:
            user.bookmark_document(document)
        db.session.commit()

        return redirect(url_for('main.document_page', path=path))


    breadcrumb_links = []

    if document.document_type != "book":
        doc = document

        while True:
            breadcrumb_links.append({"name":doc.name, "path":doc.path})
            doc = doc.parent

            if doc == None:
                break

        breadcrumb_links = breadcrumb_links[::-1]

    if document.document_type == "book":
        root = document
    else:
        root = Document.query.filter_by(name = breadcrumb_links[0]['name'])[0]
    
    table_of_contents = generate_table_of_contents(root)
    
    if document.last_updated == None:
        document.last_updated = document.date_added
           
    content = {}
    content["root"] = root.name
    content["table_of_contents"] = table_of_contents
    content["breadcrumb_links"] = breadcrumb_links
    content["document"] = document
    content["form"] = form
    content["user"] = user
    content["is_bookmarked"] = is_bookmarked

    return render_template('main/document.html', **content, title=document.name)


@bp.route("/category/<path>", methods=["GET", "POST"])
def category_page(path):
    category = db.first_or_404(Category.query.filter_by(path=path))
    return render_template('main/category.html', category=category, title=category.name)



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
    documents, scores, total = Document.search(g.search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])


    
    if total > page * current_app.config['POSTS_PER_PAGE']:
        next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1)
    else:
        next_url = None 
    
    if page > 1:
        prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) 
    else:
        prev_url = None
    return render_template('main/search.html', title="Search", results=documents,
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

    if page_type == "Document":
        doc = Document.query.filter_by(name=page_name).first()
        if doc != None:
            year = doc.date_added.year
            month = calendar.month_name[doc.date_added.month]
            day = doc.date_added.day

    

    return render_template('main/citation.html', page_type=page_type, page_url=page_url,
                            page_name=page_name, day=day, month=month, year=year, title="Citation")
