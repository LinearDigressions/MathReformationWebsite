from app import create_app
from rq import get_current_job 
from app import db
from app.models import Task, User, Document
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


    


def export_document(user_id):

    try:
        user = User.query.get(user_id) 
        _set_task_progress(0)
        data = []
        i=0


        total_documents = Document.query.count()

        for document in Document.query.all():
            if document.parent:
                parent_path = document.parent.path
            else:
                parent_path = None
            
            children = [child.name for child in document.children]
            document_type = document.document_type
            data.append({'name': document.name, 'path': document.path,'body': document.body_main,
                        'header': document.header, 'order': document.order, 'date_added':document.date_added,
                        'last_updated':document.last_updated,'is_visible':document.is_visible
                        'parent_path':parent_path, 'children':children, 'categories': document.categories,
                        'document_type': document_type})
            _set_task_progress(100 * i // total_documents)

       
        send_email('[Math Reformation] Document Archive', 
                    sender=app.config['ADMINS'][0], recipients=[user.email], 
                    text_body=render_template('email/export.txt', user=user, doc_type="Document"), html_body=render_template('email/export.html', user=user, doc_type="Documents"), 
                    attachments=[('documents.json', 'application/json',json.dumps({"Document": data}, indent=4))], 
                    sync=True)
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

    finally:
        _set_task_progress(100)

