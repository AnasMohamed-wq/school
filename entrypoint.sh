#!/bin/sh

# تنفيذ الميجريشن
python manage.py migrate --noinput

# تجميع الملفات الثابتة
python manage.py collectstatic --noinput

# تشغيل الأمر الممرر (الذي سيكون daphne)
exec "$@"
