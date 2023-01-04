from app import create_app
from rq import get_current_job 
from app import db
from app.models import Task, Article, User
import sys
from flask import render_template
from app.email import send_email
import json

app = create_app() 
app.app_context().push()


def _set_task_progress(progress): 
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id()) 
        #task.user.add_notification('task_progress', {'task_id': job.get_id(),'progress':progress})

        if progress >= 100: 
            task.complete = True
        db.session.commit()

def export_articles(user_id):
    try:
        user = User.query.get(user_id) 
        _set_task_progress(0)
        data = []
        i=0
        total_articles = Article.query.count()
        for article in Article.query.all():
            catagories = [cat.name for cat in article.categories]
            data.append({'name': article.name, 'path': article.path,'body': article.body_main,
                        'header': article.header, 'order': article.order,
                        'categories': catagories})
            _set_task_progress(100 * i // total_articles)
        print(app.config['ADMINS'][0])
        send_email('[Math Reformation] Articles', sender=app.config['ADMINS'][0], recipients=[user.email], text_body=render_template('email/export_articles.txt', user=user), html_body=render_template('email/export_articles.html', user=user), attachments=[('articles.json', 'application/json',json.dumps({'articles': data}, indent=4))], sync=True)
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        _set_task_progress(100)