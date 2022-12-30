from flask import render_template, request, redirect, url_for, current_app, abort, flash, send_from_directory, json
from app import photos, db
from app.author import bp
from app.models import Article, Category
from flask_login import login_required
from app.roles import admin_permission
from app.author.forms import ArticleForm, PhotoForm
import os
from werkzeug.utils import secure_filename
from markdown import markdown



# I modified the flask_mde in two ways.
# I commented out the sanitizeTag function in Markdown.Sanitizer.js to allow for all html rendering
# I added MathJax.typeset();  to the end of makePreviewHtml function in Markdown.Editor.js to allow for real time latex rendering


@bp.route("/edit_article/<path>", methods=["GET", "POST"])
@login_required
@admin_permission.require(http_exception=403)
def edit_article(path):

    path_changed = False

    #form = ArticleForm()
    form = ArticleForm()
    article = db.first_or_404(Article.query.filter_by(path=path))


    form.categories.choices = [(str(cat.id), cat.name) for cat in Category.query.all()]

    if form.validate_on_submit():

        if article.path != form.path.data:
            path_changed = True
        print(article.categories)
        print(form.categories.data)
        print(article.categories)

        
        article.categories = [Category.query.get(category_id) for category_id in form.categories.data]
        article.body = markdown(form.body.data)
        article.header = form.header.data
        article.name = form.name.data
        article.path = form.path.data
        db.session.commit()
        flash("Changes Saved")

        if path_changed == True:
            return redirect(url_for('author.edit_article', path=article.path))


    categories_data = json.dumps([str(cat.id) for cat in article.categories])
    form.body.data = article.body
    form.header.data = article.header
    form.name.data = article.name
    form.path.data = article.path

    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])


    return render_template('author/edit_article.html', title="Edit Article", form=form, article=article, categories_data=categories_data, setname=photos.name, files=files)

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
