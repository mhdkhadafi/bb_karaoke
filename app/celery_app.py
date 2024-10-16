from celery import Celery
from app import create_app

flask_app = create_app()

celery_app = Celery(flask_app.import_name, broker=flask_app.config['CELERY_BROKER_URL'], include=['app.tasks'])
celery_app.conf.update(flask_app.config)

class ContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery_app.Task = ContextTask