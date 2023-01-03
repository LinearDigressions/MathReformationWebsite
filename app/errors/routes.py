from flask import render_template 
from MathReformationWebsite import db
from app.errors import bp
from app.roles import admin_permission, author_permission


@bp.context_processor
def add_imports():
    return dict(admin_permission=admin_permission, author_permission=author_permission)

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html', title="Error 404"), 404

@bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html', title="Error 403"), 403

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html', title="Error 500"), 500