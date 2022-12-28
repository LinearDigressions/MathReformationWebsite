from flask import render_template
from app.author import bp
from flask_login import login_required
from app.auth.roles import admin_permission

@bp.route("/edit_article", methods=["GET"])
@login_required
@admin_permission.require(http_exception=403)
def edit_article():
    return render_template('author/edit_article.html', title="Edit Article")