#!/bin/bash
echo "Starting Zeplin Validator Django Application via Gunicorn..."

# Make sure migrations are run on container start
python manage.py migrate

# Collect static files (optional but good practice for prod/docker)
python manage.py collectstatic --noinput

# Run the Django server using Gunicorn behind Nginx
# Binding to 0.0.0.0:8080 as expected by the Docker EXPOSE instruction.
exec gunicorn design_validator.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
