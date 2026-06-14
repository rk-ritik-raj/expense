"""
WSGI config for expenses_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expenses_backend.settings')

application = get_wsgi_application()

from django.core.management import call_command
try:
    print("Running database migrations on WSGI startup...")
    call_command('migrate', interactive=False)
    print("Seeding database on WSGI startup...")
    call_command('seed_data', interactive=False)
except Exception as e:
    print("Error during WSGI startup migrations/seeding:", e)
