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



# I modified the flask_mde in two ways.
# I commented out the sanitizeTag function in Markdown.Sanitizer.js to allow for all html rendering
# I added MathJax.typeset();  to the end of makePreviewHtml function in Markdown.Editor.js to allow for real time latex rendering



@bp.route("/edit/<doc_type>/<path>", methods=["GET", "POST"])
@login_required
@admin_permission.require(http_exception=403)
def edit_document(doc_type, path):
    print(doc_type)
    path_changed = False

    form = EditingForm()

    if doc_type == "category":
        doc = db.first_or_404(Category.query.filter_by(path=path))
        form.select_multiple.choices = [(str(art.id), art.name) for art in Article.query.all()]
        opposite_type = "article"

    elif doc_type == "article":
        doc = db.first_or_404(Article.query.filter_by(path=path))
        form.select_multiple.choices = [(str(cat.id), cat.name) for cat in Category.query.all()]
        opposite_type = "category"
    else:
        abort(500)

    if form.validate_on_submit():

        if doc.path != form.path.data:
            path_changed = True

        if doc_type == "category":
            doc.articles = [Article.query.get(article_id) for article_id in form.select_multiple.data]
        elif doc_type == "article":
            doc.categories = [Category.query.get(category_id) for category_id in form.select_multiple.data]
        else:
            abort(500)


        doc.body = markdown(form.body.data)
        doc.header = form.header.data
        doc.name = form.name.data
        doc.path = form.path.data
        db.session.commit()
        flash("Changes Saved")

        if path_changed == True:
            return redirect(url_for('author.edit_article', path=doc.path))


    if doc_type == "category":
        selected_items = json.dumps([str(art.id) for art in doc.articles])
    elif doc_type == "article":
        selected_items = json.dumps([str(cat.id) for cat in doc.categories])
    else:
        abort(500)

    form.body.data = doc.body
    form.header.data = doc.header
    form.name.data = doc.name
    form.path.data = doc.path
    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])

    return render_template('author/edit_document.html', title="Edit " + doc_type.capitalize(), opposite_type=opposite_type, form=form, doc=doc, selected_items=selected_items, setname=photos.name, files=files)



@bp.route('/upload_photo', methods=['GET', 'POST'])
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
