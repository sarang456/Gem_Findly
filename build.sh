#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate




# python manage.py shell <<EOF
# from django.contrib.auth import get_user_model
# User = get_user_model()
# # We check for the email since that is your unique field
# if not User.objects.filter(email='geminai@gmail.com').exists():
#     User.objects.create_superuser(
#         email='geminai@gmail.com', 
#         password='Google@123'
#     )
#     print("✅ Superuser created successfully!")
# else:
#     print("✅ Superuser already exists.")
# EOF