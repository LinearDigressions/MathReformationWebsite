from flask import render_template, request, redirect, url_for, current_app, abort, flash, send_from_directory, json
from app import photos, db
from app.author import bp
from app.models import Article, Category
from flask_login import login_required
from app.roles import admin_permission
from app.author.forms import ArticleForm, PhotoForm, EditingForm
import os
from werkzeug.utils import secure_filename
from markdown import markdown
import random


# I modified the flask_mde in two ways.
# I commented out the sanitizeTag function in Markdown.Sanitizer.js to allow for all html rendering
# I added MathJax.typeset();  to the end of makePreviewHtml function in Markdown.Editor.js to allow for real time latex rendering

@bp.route("/author_home")
@login_required
@admin_permission.require(http_exception=403)
def author_home():

    return render_template('author/author_home.html')

@bp.route("/create/<doc_type>/", methods=["GET", "POST"])
@login_required
@admin_permission.require(http_exception=403)
def new_document(doc_type):

    new_doc_num = str(random.randint(0, 10000000000000000000000))

    if doc_type == "category":
        while Category.query.filter_by(name=new_doc_num).first() != None:
            new_doc_num = str(random.randint(0, 10000000000000000000000))
        
        new_doc = Category(name=new_doc_num, path=new_doc_num)

    elif doc_type == "article":
        while Article.query.filter_by(name=new_doc_num).first() != None:
            new_doc_num = str(random.randint(0, 10000000000000000000000))
        
        new_doc = Article(name=new_doc_num, path=new_doc_num)


    db.session.add(new_doc)
    db.session.commit()

    return redirect(url_for('author.edit_document', doc_type=doc_type, path=new_doc_num))

@bp.route("/edit/<doc_type>/<path>", methods=["GET", "POST"])
@login_required
@admin_permission.require(http_exception=403)
def edit_document(doc_type, path):
    
    selected_children = []
    selected_parents = []
    path_changed = False

    form = EditingForm()

    if doc_type == "category":
        doc = db.first_or_404(Category.query.filter_by(path=path))
        form.items.choices = [(str(art.id), art.name) for art in Article.query.all()]
        form.parents.choices = [(str(cat.id), cat.name) for cat in Category.query.all()]
        form.children.choices = [(str(cat.id), cat.name) for cat in Category.query.all()]
        opposite_type = "article"

    elif doc_type == "article":
        doc = db.first_or_404(Article.query.filter_by(path=path))
        form.items.choices = [(str(cat.id), cat.name) for cat in Category.query.all()]
        opposite_type = "category"
    else:
        abort(500)

    if form.validate_on_submit():

        if doc.path != form.path.data:
            path_changed = True

        if doc_type == "category":
            doc.articles = [Article.query.get(article_id) for article_id in form.items.data]
            doc.parents = [Category.query.get(category_id) for category_id in form.parents.data]
            doc.children = [Category.query.get(category_id) for category_id in form.children.data]
        elif doc_type == "article":
            doc.categories = [Category.query.get(category_id) for category_id in form.items.data]
        else:
            abort(500)


        doc.body = markdown(form.body.data)
        doc.header = form.header.data
        doc.name = form.name.data
        doc.path = form.path.data
        db.session.commit()
        flash("Changes Saved")

        if form.submit.data:
            return redirect(url_for('author.author_home'))

        if path_changed == True:
            return redirect(url_for('author.edit_document', path=doc.path, doc_type=doc_type))


    if doc_type == "category":
        selected_items = json.dumps([str(art.id) for art in doc.articles])
        selected_parents = json.dumps([str(cat.id) for cat in doc.parents])
        selected_children = json.dumps([str(cat.id) for cat in doc.children])
    elif doc_type == "article":
        selected_items = json.dumps([str(cat.id) for cat in doc.categories])
    else:
        abort(500)

    form.body.data = doc.body
    form.header.data = doc.header
    form.name.data = doc.name
    form.path.data = doc.path
    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])

    content = {}

    content["title"] = "Edit " + doc_type.capitalize()
    content["doc_type"] = doc_type
    content["opposite_type"] = opposite_type
    content["form"] = form
    content["doc"] = doc
    content["selected_items"] = selected_items
    print(selected_items)
    content["selected_parents"] = selected_parents
    content["selected_children"] = selected_children
    content["setname"] = photos.name
    content["files"] = files

    return render_template('author/edit_document.html', **content)



@bp.route('/manage_photos', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=403)
def upload_photo():
    if request.method == "POST" and "photo" in request.files:
        filename = photos.save(request.files["photo"])
        url =  url_for("_uploads.uploaded_file", setname="photos", filename=filename)
        print("Url: ", url)
        flash("Photo uploaded at: " + url)

    form = PhotoForm()
    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])
    return render_template("author/upload_photo.html", form=form,setname=photos.name, files=files)

@bp.route("/show/<setname>/<filename>")
def show(setname, filename):
    config = current_app.upload_set_config.get(setname)  # type: ignore
    if config is None:
        abort(404)
    return send_from_directory(config.destination, filename)
