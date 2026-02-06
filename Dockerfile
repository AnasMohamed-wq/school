# استخدام نسخة بايثون مستقرة وخفيفة
FROM python:3.12-slim

# منع بايثون من كتابة ملفات pyc ومنع تأخير الـ output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# تحديد مسار العمل داخل الحاوية
WORKDIR /app

# تثبيت مكتبات النظام اللازمة لـ PostgreSQL و الـ WebSockets
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# تثبيت المكتبات البرمجية
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات المشروع
COPY . .

# إعطاء صلاحية تنفيذ لملف التشغيل (سننشئه لاحقاً)
RUN chmod +x /app/entrypoint.sh

# تشغيل ملف الـ entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]