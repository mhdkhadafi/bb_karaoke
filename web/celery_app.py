from celery import Celery

# Define the Celery app, using Redis as the broker
app = Celery('bb_karaoke', broker='redis://redis:6379/0')

# Optional configuration
app.conf.update(
    result_backend='redis://redis:6379/0',
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
app.autodiscover_tasks(['track_downloader', 'karaoke_video_maker', 'app'])
