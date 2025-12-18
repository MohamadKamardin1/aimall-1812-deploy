#!/usr/bin/env bash
set -o errexit


/opt/render/project/src/.venv/bin/python -m pip install --upgrade pip
# Upgrade pip and setuptools first
pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt

# If Pillow still fails, install it separately with specific flags
pip install pillow --no-cache-dir

# Static files and migrations
python manage.py collectstatic --no-input
python manage.py migrate


python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
phone = "+255778769590"
password = "1234"
if not User.objects.filter(phone_number=phone, user_type="admin").exists():
    User.objects.create_superuser(
        phone_number=phone,
        password=password,
        user_type="admin",
        is_staff=True,
        is_superuser=True,
        is_active=True
    )
EOF