#!/bin/sh

# تنفيذ الميجريشن
python manage.py migrate

# تجميع الملفات الثابتة
python manage.py collectstatic --no-input

# تشغيل السيرفر
exec "$@"
