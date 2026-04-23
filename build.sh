#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate




# This creates a superuser automatically if it doesn't exist
# Replace 'admin', 'admin@example.com', and 'yourpassword' with your details
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'spidy2423@gmail.com', 'YourStrongPassword123')
    print("✅ Superuser created successfully!")
else:
    print("✅ Superuser already exists.")
EOF