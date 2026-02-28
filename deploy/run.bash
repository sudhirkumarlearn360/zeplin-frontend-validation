#!/bin/bash
echo "Starting Zeplin Validator Django Application..."

# Make sure migrations are run on container start
python manage.py migrate

# Collect static files (optional but good practice for prod/docker)
python manage.py collectstatic --noinput

# Run the Django server. Note: Gunicorn is recommended for production.
# For local container testing as 127.0.0.1:8080 as requested in Dockerfile EXPOSE
exec python manage.py runserver 0.0.0.0:8080
