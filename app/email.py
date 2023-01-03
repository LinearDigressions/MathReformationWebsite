from flask_mail import Message 
from app import mail
from flask import render_template, current_app
from threading import Thread

def send_async_email(app, msg): 
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body): 
    msg = Message(subject, sender=sender, recipients=recipients) 
    msg.body = text_body
    msg.html = html_body
    #mail.send(msg)
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_password_reset_email(user):
    token = user.get_reset_password_token() 
    send_email('[Math Reformation] Reset Your Password', sender=current_app.config['MAIL_USERNAME'], 
                recipients=[user.email], 
                text_body=render_template('email/reset_password.txt', user=user, token=token), html_body=render_template('email/reset_password.html',user=user, token=token))


def send_feedback_email(feedback):
    send_email('Feedback (' + feedback.category + ')', 
                sender=current_app.config['MAIL_USERNAME'], 
                recipients=current_app.config['ADMINS'] + [current_app.config['MAIL_USERNAME']],
                text_body = render_template('email/feedback.txt', feedback=feedback),
                html_body = render_template('email/feedback.html', feedback=feedback))