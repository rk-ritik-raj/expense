"""
ASGI config for expenses_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expenses_backend.settings')

application = get_asgi_application()

from django.core.management import call_command
try:
    print("Running database migrations on ASGI startup...")
    call_command('migrate', interactive=False)
    print("Seeding database on ASGI startup...")
    call_command('seed_data', interactive=False)
except Exception as e:
    print("Error during ASGI startup migrations/seeding:", e)
