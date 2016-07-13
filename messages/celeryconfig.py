CELERY_IMPORTS = ('tasks')
CELERY_IGNORE_RESULT = False
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 5672
BROKER_URL='amqp://'
CELERY_RESULT_BACKEND = "amqp"
CELERY_IMPORTS=("tasks",)

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'every-5-minute': {
        'task': 'tasks.update_streams',
        'schedule': crontab(minute='*/5')
    },
}
