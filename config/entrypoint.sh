#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Loading data dump if available..."
if [ -f "data_dump.json" ]; then
    python manage.py loaddata data_dump.json
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
email = '$ADMIN_EMAIL';
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        password='$ADMIN_PASSWORD',
        first_name='Admin',
        last_name='User',
        phone_number='01000000000',
        role='seller'
    );
    print('Superuser created.');
else:
    print('Superuser already exists.');
"

echo "Setting up Celery Beat periodic tasks..."
python manage.py shell -c "
from django_celery_beat.models import PeriodicTask, IntervalSchedule;
schedule, _ = IntervalSchedule.objects.get_or_create(every=2, period='hours');
if not PeriodicTask.objects.filter(name='scrape-all-sources-every-2-hours').exists():
    PeriodicTask.objects.create(
        interval=schedule,
        name='scrape-all-sources-every-2-hours',
        task='scrapers.tasks.scrape_all_sources',
    );
    print('Periodic task created.');
else:
    print('Periodic task already exists.');
"

echo "Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
