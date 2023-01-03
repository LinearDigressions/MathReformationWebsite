from flask import render_template, request, redirect, url_for, current_app, abort, flash, send_from_directory, json
from flask_login import current_user
from app import photos, db
from app.author import bp
from app.models import Article, CategoryType, Category
from flask_login import login_required
from app.roles import admin_permission, EditArticlePermission, author_permission
from app.author.forms import AddPhotoForm, EditingForm, DeletePhotoForm
import os
from werkzeug.utils import secure_filename
from markdown import markdown
import random
from flask_principal import identity_changed, Identity


# I modified the flask_mde in two ways.
# I commented out the sanitizeTag function in Markdown.Sanitizer.js to allow for all html rendering
# I added MathJax.typeset();  to the end of makePreviewHtml function in Markdown.Editor.js to allow for real time latex rendering


@bp.context_processor
def add_imports():
    return dict(admin_permission=admin_permission, author_permission=author_permission)

@bp.route("/author_home", methods=["GET", "POST"])
@login_required
@author_permission.require(http_exception=403)
def author_home():


    add_photo_form = AddPhotoForm()

    if add_photo_form.validate_on_submit():
        filename = photos.save(request.files["photo"], name=add_photo_form.name.data)
        url =  url_for("_uploads.uploaded_file", setname="photos", filename=filename)
        print("Url: ", url)
        flash("Photo uploaded at: " + url)

    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])

    if admin_permission.can():

        root_categories = CategoryType.query.filter_by(name="root").first().categories


        return render_template('author/admin_home.html', root_categories=root_categories, add_photo_form=add_photo_form, setname=photos.name, files=files, title="Author Home")

    else:

        authored_articles = Article.query.filter_by(author=current_user)

        return render_template('author/author_home.html', authored_articles= authored_articles, add_photo_form=add_photo_form, setname=photos.name, files=files, title="Author Home")


@bp.route("/create/<doc_type>/", methods=["GET", "POST"])
@login_required
@author_permission.require(http_exception=403)
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

        if new_doc.author == None:
            new_doc.author = current_user
            

    db.session.add(new_doc)
    db.session.commit()

    return redirect(url_for('author.edit_document', doc_type=doc_type, path=new_doc_num, version='main'))

@bp.route("/edit/<doc_type>/<path>/<version>", methods=["GET", "POST"])
@login_required
def edit_document(doc_type, path, version):


    if version not in ["main", "draft"]:
        abort(404)

    if doc_type not in ["category", "article"]:
        abort(404)

    
    # Setting variables to preload multiple selection fields 
    selected_items=[]
    selected_children = []
    selected_parents = []
    selected_category_type = []

   

    # Checks to see if path changed (To redirect to appropriate edit page later on)
    path_changed = False

    form = EditingForm()

     # To avoid errors for article (NEED TO FIX)
    if doc_type == "article":
        form.category_type.data="secondary"



    # Gets available category and article choices for form)
    if doc_type == "category":
            # Only admins can create categories
        if not admin_permission.can():
            abort(403)

        


        doc = db.first_or_404(Category.query.filter_by(path=path))

        # To avoid errors
        if doc.category_type == None:
            doc.category_type = CategoryType.query.filter_by(name="secondary").first()


        form.items.choices = [(str(art.id), art.name) for art in Article.query.all()]

        form.category_type.choices = [(str(cat_type.id), cat_type.name) for cat_type in CategoryType.query.all()]

        # Selecting only the allowable parents/children for each category type
        if doc.category_type.name == "root":
            form.parents.choices = []
            form.children.choices = [(str(cat.id), cat.name) for cat in CategoryType.query.filter_by(name="primary").first().categories]
        elif doc.category_type.name == "primary":
            form.parents.choices = [(str(cat.id), cat.name) for cat in CategoryType.query.filter_by(name="root").first().categories]
            form.children.choices = [(str(cat.id), cat.name) for cat in CategoryType.query.filter_by(name="secondary").first().categories]
        else:
            form.parents.choices = [(str(cat.id), cat.name) for cat in CategoryType.query.filter_by(name="primary").first().categories]
            form.children.choices = []
        
        opposite_type = "article"
        form.items.label="Articles"

    if doc_type == "article":
        doc = db.first_or_404(Article.query.filter_by(path=path))
        form.items.choices = [(str(cat.id), cat.name) for cat in CategoryType.query.filter_by(name="secondary").first().categories]

        opposite_type = "category"
        form.items.label="Categories"

        # Only admins or specific authors can edit
        if not (EditArticlePermission(doc.id).can() or admin_permission.can()):
                abort(403)

    if form.validate_on_submit():


        # Switches versions (Does not save current changes so there is a JS alert)
        if form.load_draft.data:
            return redirect(url_for('author.edit_document', path=doc.path, doc_type=doc_type, version="draft"))

        if form.load_main.data:
            return redirect(url_for('author.edit_document', path=doc.path, doc_type=doc_type, version="main"))

        # Checks if path is changed (Redirects if path is changed later on)
        if doc.path != form.path.data:
            path_changed = True

        # Gets selection from multiple select fields
        if doc_type == "category":
            doc.articles = [Article.query.get(article_id) for article_id in form.items.data]
            doc.parents = [Category.query.get(category_id) for category_id in form.parents.data]
            doc.children = [Category.query.get(category_id) for category_id in form.children.data]
            doc.category_type = CategoryType.query.get(form.category_type.data)
        elif doc_type == "article":
            doc.categories = [Category.query.get(category_id) for category_id in form.items.data]
        else:
            abort(500)

        # Saves the field to both main and draft
        if form.save_draft_to_main.data:
            doc.body_main = markdown(form.body.data)
            doc.body_draft = markdown(form.body.data)
            flash("Draft Saved to Main")

        # Saves the field as draft
        if form.save_main_to_draft.data:
            doc.body_draft = markdown(form.body.data)
            flash("Draft Saved to Main")

        # Saves current work
        if form.save_and_exit.data or form.submit_continue_editing.data:
            if version == "main":
                doc.body_main = markdown(form.body.data)

            if version == "draft":
                doc.body_draft = markdown(form.body.data)

        doc.header = form.header.data
        doc.name = form.name.data
        doc.path = form.path.data
        doc.order = form.order.data
        doc.is_visible = form.is_visible.data
        db.session.commit()
        flash("Changes Saved")

        
        # Switches view if needed
        if form.save_draft_to_main.data:
            flash("Switching to Main View")
            return redirect(url_for('author.edit_document', path=doc.path, doc_type=doc_type, version="main"))

        if form.save_main_to_draft.data:
            flash("Switching to Draft View")
            return redirect(url_for('author.edit_document', path=doc.path, doc_type=doc_type, version="draft"))


        if form.save_and_exit.data:
            return redirect(url_for('author.author_home'))


        if path_changed == True:
            return redirect(url_for('author.edit_document', path=doc.path, doc_type=doc_type, version=version))


    # Prepares preselected multiple select field data
    if doc_type == "category":
        selected_items = json.dumps([str(art.id) for art in doc.articles])
        selected_parents = json.dumps([str(cat.id) for cat in doc.parents])
        selected_children = json.dumps([str(cat.id) for cat in doc.children])
        selected_category_type = json.dumps([doc.category_type.id])
    elif doc_type == "article":
        selected_items = json.dumps([str(cat.id) for cat in doc.categories])
        print(selected_items)
    else:
        abort(500)

    # Prepares form.body data
    if version == "main":
        form.body.data = doc.body_main

    if version == "draft":
        form.body.data = doc.body_draft

    # # Prepares remaining fields of form
    form.header.data = doc.header
    form.is_visible.data = doc.is_visible
    form.name.data = doc.name
    form.path.data = doc.path
    if doc.order:
        form.order.data = doc.order
    else:
        form.order.data = 1
    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])


    # Lots of parameters so dictionary!
    content = {}

    if doc_type == "category":
        content["category_type"] = doc.category_type.name
    else:
        content["category_type"] = None


    content["title"] = "Edit " + doc_type.capitalize()
    content["doc_type"] = doc_type
    content["opposite_type"] = opposite_type
    content["form"] = form
    content["doc"] = doc

    content["selected_items"] = selected_items
    content["selected_parents"] = selected_parents
    content["selected_children"] = selected_children
    content["selected_category_type"] = selected_category_type
    
    content["setname"] = photos.name
    content["files"] = files
    content["version"] = version
    content["title"] = "Edit Document"

    #flash(form.errors)
    return render_template('author/edit_document.html', **content)



@bp.route('/manage_photos', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=403)
def manage_photos():
    add_photo_form = AddPhotoForm()

    # if request.method == "POST" and "photo" in request.files:
    if add_photo_form.validate_on_submit():
        filename = photos.save(request.files["photo"], name=add_photo_form.name.data)
        url =  url_for("_uploads.uploaded_file", setname="photos", filename=filename)
        print("Url: ", url)
        flash("Photo uploaded at: " + url)

    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])
    return render_template("author/manage_photos.html", add_photo_form=add_photo_form, setname=photos.name, files=files)

@bp.route("/show/<setname>/<filename>")
def show(setname, filename):
    config = current_app.upload_set_config.get(setname)  # type: ignore
    if config is None:
        abort(404)
    return send_from_directory(config.destination, filename)


@bp.route("/delete/<item_type>/<item_name>", methods=["GET"])
@login_required
@author_permission.require(http_exception=403)
def delete_file(item_type, item_name):

    # Only admins can delete photos and categories
    if not admin_permission.can() and item_type != "article":
        abort(403)

    if item_type == "photos":
        path = photos.path(item_name)
        os.remove(path)
        flash(item_name + " file deleted.")
        return redirect(url_for('author.author_home'))

    elif item_type == "category":
        cat = db.first_or_404(Category.query.filter_by(path=item_name))
        db.session.delete(cat)
        db.session.commit()
        flash(item_name + " category deleted.")
        return redirect(url_for('author.author_home'))
    elif item_type == "article":
        
        art = db.first_or_404(Article.query.filter_by(path=item_name))

        if not (EditArticlePermission(art.id).can() or admin_permission.can()):
            abort(403)

        db.session.delete(art)
        db.session.commit()
        flash(item_name + " article deleted.")
        return redirect(url_for('author.author_home'))
    else:
        print('here')
        abort(404)
