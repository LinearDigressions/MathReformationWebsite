from flask import render_template, request, redirect, url_for, current_app, abort, flash, send_from_directory
from app import photos
from app.author import bp
from app.models import Article
from flask_login import login_required
from app.roles import admin_permission
from app.author.forms import ArticleForm, PhotoForm
import os
from werkzeug.utils import secure_filename


@bp.route("/edit_article/<article_id>", methods=["GET"])
@login_required
@admin_permission.require(http_exception=403)
def edit_article(article_id):
    article_query = Article.query.get(article_id)
    if article_query == None:

        print("Hi")
    form = ArticleForm()
    return render_template('author/edit_article.html', title="Edit Article", form=form)

@bp.route('/upload_photo', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=403)
def upload_photo():
    if request.method == "POST" and "photo" in request.files:
        filename = photos.save(request.files["photo"])
        url =  url_for("_uploads.uploaded_file", setname="photos", filename=filename)
        print("Url: ", url)
        flash("Photo uploaded at: " + url)
        # return redirect(url)

    form = PhotoForm()
    files = os.listdir(current_app.config['UPLOADED_PHOTOS_DEST'])
    return render_template("author/upload_photo.html", form=form,setname=photos.name, files=files)

@bp.route("/show/<setname>/<filename>")
def show(setname, filename):
    config = current_app.upload_set_config.get(setname)  # type: ignore
    if config is None:
        abort(404)
    return send_from_directory(config.destination, filename)
