from flask import render_template, request, redirect, url_for, current_app, abort, flash, send_from_directory, json
from datetime import datetime
from flask_login import current_user
from app import photos, db
from app.staff import bp
from app.models import Document
from flask_login import login_required
from app.roles import admin_permission, EditArticlePermission, author_permission, editor_permission
from app.staff.forms import AddPhotoForm, DeletePhotoForm, EditDocumentForm
import os
from werkzeug.utils import secure_filename
from markdown import markdown
import random
from flask_principal import identity_changed, Identity


# Old Structure
child2parent = {"book":None, "chapter":"book", "section":"chapter","article":"section", "special":None}
parent2child = {"book":"chapter","chapter":"section","section":"article","article":None, "special":None}

# Removing Section
# child2parent = {"book":None, "chapter":"book", "article":"chapter", "special":None}
# parent2child = {"book":"chapter","chapter":"article", "article":None, "special":None}

# I modified the flask_mde in two ways.
# I commented out the sanitizeTag function in Markdown.Sanitizer.js to allow for all html rendering
# I added MathJax.typeset();  to the end of makePreviewHtml function in Markdown.Editor.js to allow for real time latex rendering


# @bp.context_processor
# def add_imports():
#     return dict(admin_permission=admin_permission, author_permission=author_permission)

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


    authored_articles = Document.query.filter_by(author=current_user, document_type="article")

    return render_template('staff/author_home.html', authored_articles=authored_articles, add_photo_form=add_photo_form, setname=photos.name, files=files, title="Author Home")


@bp.route("/editor_home", methods=["GET", "POST"])
@login_required
@editor_permission.require(http_exception=403)
def editor_home():


    add_photo_form = AddPhotoForm()

    if add_photo_form.validate_on_submit():
        filename = photos.save(request.files["photo"], name=add_photo_form.name.data)
        url =  url_for("_uploads.uploaded_file", setname="photos", filename=filename)
        print("Url: ", url)
        flash("Photo uploaded at: " + url)

    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])


    books = Document.query.filter_by(document_type="book")
    special_documents = Document.query.filter_by(document_type="special")

    invisible_documents = Document.query.filter_by(is_visible=False)


    lost_documents = [doc for doc in Document.query.filter_by(parent=None) if doc.document_type not in ["book", "special"]]


    return render_template('staff/editor_home.html', 
                            books=books,
                            special_documents=special_documents,
                            invisible_documents=invisible_documents,
                            lost_documents=lost_documents,
                            add_photo_form=add_photo_form, 
                            setname=photos.name, 
                            files=files, 
                            title="Editor Home")

@bp.route("/create/<document_type>/<parent_path>", methods=["GET", "POST"])
@bp.route("/create/<document_type>", methods=["GET", "POST"])
@bp.route("/create/", methods=["GET", "POST"])
@login_required
@author_permission.require(http_exception=403)
def new_document(document_type=None, parent_path=None):


    document_number = str(random.randint(0, 10000000000000000000000))

    while Document.query.filter_by(name=document_number).first() != None:
        document_number = str(random.randint(0, 10000000000000000000000))
    

    document = Document(name=document_number, path=document_number)
    parent = Document.query.filter_by(path=parent_path).first()

    document.order = 1
    document.author = current_user
    document.parent = parent

    if document_type != None:
        document.document_type = document_type
    elif document.parent != None:
        document.document_type = parent2child[document.parent.document_type]
    else:
        document.document_type = "article"
    
    db.session.add(document)
    db.session.commit()

    return redirect(url_for('staff.edit_document', document_type=document.document_type, path=document.path, version='main'))

@bp.route("/edit/<document_type>/<path>/<version>", methods=["GET", "POST"])
@login_required
def edit_document(document_type, path, version):


    # Checking version and doc_type
    if version not in ["main", "draft"] or document_type not in ["book","chapter","section", "article", "special"]:
        abort(404)
        
    # Initializing Multiple Select attributes
    selected_children = []
    selected_parent = []
    selected_document_type = []


    # INITIALIZING FORMS
    form = EditDocumentForm()
    document = db.first_or_404(Document.query.filter_by(path=path))
   
    form.previous_name = document.name
    form.previous_path = document.path


    # CHECKING PERMISSIONS
    if document_type in ["book", "section", "chapter", "special"] and not editor_permission.can():
            abort(403)
    elif document_type == "article" and not (EditArticlePermission(document.id).can() or editor_permission.can() or admin_permission.can()):
            abort(403)


    # GETTING OPTIONS

    if not editor_permission.can():
        form.document_type.choices = [("article", "Article")]
    else:
        form.document_type.choices = [(doc_type, doc_type.capitalize()) for doc_type in ["special", "book","chapter","section","article"]]

    # Selecting only the allowable parents/children/articles for each category type

    form.parent.choices = [(str(doc.id), doc.name) for doc in Document.query.filter_by(document_type=child2parent[document_type])]
    form.children.choices = [(str(doc.id), doc.name) for doc in Document.query.filter_by(document_type=parent2child[document_type])]

    form.parent.choices.append(("none", "None"))
    form.children.choices.append(("none", "None"))


    if form.validate_on_submit():
        document.last_updated = datetime.utcnow()

        # Switches versions (Does not save current changes so there is a JS alert)
        if form.load_draft.data:
            return redirect(url_for('staff.edit_document', path=document.path, document_type=document_type, version="draft"))
        elif form.load_main.data:
            return redirect(url_for('staff.edit_document', path=document.path, document_type=document_type, version="main"))

        # Saves draft as main or saves main as draft 
        if form.save_draft_to_main.data:
            document.body_main = markdown(form.body.data)
            document.body_draft = markdown(form.body.data)
            flash("Draft Saved to Main")
        elif form.save_main_to_draft.data:
            document.body_draft = markdown(form.body.data)
            flash("Saved as Draft")

        # Saves current work
        if form.save_and_exit.data or form.submit_continue_editing.data:
            if version == "main":
                document.body_main = markdown(form.body.data)
            elif version == "draft":
                document.body_draft = markdown(form.body.data)


        # Gets data from form 
        document.children = [Document.query.get(document_id) for document_id in form.children.data if document_id != "none"]
        if form.parent.data != "none":
            document.parent = Document.query.get(form.parent.data)
        
        document.document_type = form.document_type.data
    
        document.header = form.header.data
        document.name = form.name.data
        document.path = form.path.data
        document.order = form.order.data
        document.is_visible = form.is_visible.data

        if document.is_visible:
            document.set_links()
            document.make_visible_on_index()
        else:
            document.remove_links()
            document.make_invisible_on_index()



        db.session.commit()
        flash("Changes Saved")

        # Switches view if needed
        if form.save_draft_to_main.data:
            flash("Switching to Main View")
            return redirect(url_for('staff.edit_document', path=document.path, document_type=document.document_type, version="main"))
        elif form.save_main_to_draft.data:
            flash("Switching to Draft View")
            return redirect(url_for('staff.edit_document', path=document.path, document_type=document.document_type, version="draft"))
        elif form.save_and_exit.data:
            if editor_permission.can():
                return redirect(url_for('staff.editor_home'))
            else:
                return redirect(url_for('staff.author_home'))

        elif form.submit_continue_editing.data:
            return redirect(url_for('staff.edit_document', path=document.path, document_type=document.document_type, version=version))




    

    # Prepares form
    if document.parent != None:
        selected_parent = json.dumps([str(document.parent.id)])
    else:
        selected_parent = json.dumps(["none"])

    if document.children != None:
        selected_children = json.dumps([str(child.id) for child in document.children])
    else:
        selected_parent = json.dumps(["none"])

    selected_document_type = json.dumps([document.document_type])

    # Saves form fields if form fails to prevent changes from being lost
    if form.errors == {}:

        # Prepares form.body data
        if version == "main":
            form.body.data = document.body_main
        elif version == "draft":
            form.body.data = document.body_draft

        form.header.data = document.header
        form.is_visible.data = document.is_visible
        form.name.data = document.name
        form.path.data = document.path
        form.order.data = document.order
  


    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])


    # Lots of parameters so dictionary!
    content = {}


    content["document_type"] = document_type
    content["form"] = form
    content["document"] = document
    content["version"] = version

    content["selected_parent"] = selected_parent
    content["selected_children"] = selected_children
    content["selected_document_type"] = selected_document_type
    
    content["setname"] = photos.name
    content["files"] = files

    content["title"] = "Document Editor"

    #flash(form.errors)
    return render_template('staff/edit_document.html', **content)



@bp.route('/manage_photos', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=403)
def manage_photos():
    add_photo_form = AddPhotoForm()

    # if request.method == "POST" and "photo" in request.files:
    if add_photo_form.validate_on_submit():
        filename = photos.save(request.files["photo"], name=add_photo_form.name.data)
        url =  url_for("_uploads.uplo`aded_file", setname="photos", filename=filename)
        print("Url: ", url)
        flash("Photo uploaded at: " + url)

    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])
    return render_template("staff/manage_photos.html", add_photo_form=add_photo_form, setname=photos.name, files=files)

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
        return redirect(url_for('staff.author_home'))

    elif item_type in ["chapter", "section", "article", "book"]:
        document = db.first_or_404(Document.query.filter_by(path=item_name))

        document.remove_links()

        
        db.session.delete(document)

        db.session.commit()
        flash(item_name + " document deleted.")
        if editor_permission.can():
            return redirect(url_for('staff.editor_home'))    
        else:
            return redirect(url_for('staff.author_home'))

    else:
        abort(404)



@bp.route('/export/')
@login_required
@editor_permission.require(http_exception=403)
def export():
    if current_user.get_task_in_progress('export'):
        flash('An export task is currently in progress')
    else:
        current_user.launch_task('export_document','Exporting Documents...')
        db.session.commit()
    return redirect(url_for('staff.editor_home'))