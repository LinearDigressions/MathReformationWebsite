from flask import render_template, flash, redirect, url_for, request, current_app, session
from app import db, login
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user, logout_user, login_manager, login_required
from app.models import User
from werkzeug.urls import url_parse
from flask_principal import Principal, Identity, AnonymousIdentity, identity_changed, identity_loaded, UserNeed, RoleNeed 
from app.roles import admin_permission, author_permission


@bp.context_processor
def add_imports():
    return dict(admin_permission=admin_permission)

@login.user_loader
def load_user(userid):
    # Return an instance of the User model
    return User.query.filter_by(id=userid).first()


@bp.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if form.validate_on_submit():

        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data) 

        identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

        next_page = request.args.get('next')

        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')

        return redirect(next_page)
        
    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/logout')
@login_required
def logout():

    logout_user()

    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST']) 
def register():
    if current_user.is_authenticated: 
        return redirect(url_for('index'))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data) 
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Register', form=form)


