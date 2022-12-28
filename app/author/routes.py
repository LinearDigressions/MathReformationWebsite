from flask import render_template
from app.author import bp
from app.models import Article
from flask_login import login_required
from app.roles import admin_permission

@bp.route("/edit_article/<article_id>", methods=["GET"])
@login_required
@admin_permission.require(http_exception=403)
def edit_article(article_id):
    article_query = Article.query.get(article_id)
    if article_query == None:
        print("Hi")
    
    return render_template('author/edit_article.html', title="Edit Article")