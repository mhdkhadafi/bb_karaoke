from celery import Celery

# Define the Celery app, using Redis as the broker
app = Celery('bb_karaoke', broker='redis://localhost:6379/0')

# Optional configuration
app.conf.update(
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)