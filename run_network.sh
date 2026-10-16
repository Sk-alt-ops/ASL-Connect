#!/bin/bash
echo "Starting server on 0.0.0.0:8000 — accessible from other devices on the same network"
echo "Find your local IP with: ifconfig | grep inet"
echo ""
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
