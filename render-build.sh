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
