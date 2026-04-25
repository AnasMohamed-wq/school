#!/bin/sh

# الانتظار حتى تعمل قاعدة البيانات
echo "Waiting for postgres..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"
# تنفيذ الميجريشن
python manage.py migrate

# تجميع الملفات الثابتة
python manage.py collectstatic --no-input

# تشغيل السيرفر
exec "$@"
