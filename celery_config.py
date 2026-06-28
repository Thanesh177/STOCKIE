from celery import Celery

# Initialize Celery
celery = Celery('tasks', broker='redis://localhost:6379/0')

# Optional: Configure task result backend
celery.conf.update(
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)
