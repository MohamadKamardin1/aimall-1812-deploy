#!/usr/bin/env bash
# Exit on error
set -o errexit

# Upgrade pip
pip install --upgrade pip

# Install requirements (without Pillow)
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
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