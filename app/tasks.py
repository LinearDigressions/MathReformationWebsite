from app import create_app
from rq import get_current_job 
from app import db
from app.models import Task, Article, User, Category
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

def export_category(user_id):
    return export(user_id, 'category')


def export_article(user_id):
    return export(user_id, 'article')

def export(user_id, doc_type):

    try:
        user = User.query.get(user_id) 
        _set_task_progress(0)
        data = []
        i=0

        if doc_type == 'category':

            total_categories = Category.query.count()

            for category in Category.query.all():
                articles = [cat.name for cat in category.articles]
                parents = [parent.name for parent in category.parents]
                children = [child.name for child in category.children]
                category_type = category.category_type.name
                data.append({'name': category.name, 'path': category.path,'body': category.body_main,
                            'header': category.header, 'order': category.order,
                            'articles': articles, 'parents':parents, 'children':children,
                            'category_type': category_type})
                _set_task_progress(100 * i // total_categories)

        elif doc_type == 'article':

            total_articles = Article.query.count()
            
            for article in Article.query.all():
                catagories = [cat.name for cat in article.categories]
                data.append({'name': article.name, 'path': article.path,'body': article.body_main,
                            'header': article.header, 'order': article.order,
                            'categories': catagories, 'author': article.author.username})
                _set_task_progress(100 * i // total_articles)
                
        send_email('[Math Reformation] ' + doc_type.capitalize() +' Archive', 
                    sender=app.config['ADMINS'][0], recipients=[user.email], 
                    text_body=render_template('email/export.txt', user=user, doc_type=doc_type), html_body=render_template('email/export.html', user=user, doc_type=doc_type), 
                    attachments=[(doc_type + '.json', 'application/json',json.dumps({doc_type: data}, indent=4))], 
                    sync=True)
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

    finally:
        _set_task_progress(100)

