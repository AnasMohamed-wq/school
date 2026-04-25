import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "false" # لمنع أخطاء التزامن في بعض البيئات
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)



SECRET_KEY = os.getenv('SECRET_KEY')


DEBUG = os.getenv('DEBUG', 'True') == 'True'





INSTALLED_APPS = [
    'daphne', # لتعامل مع بروتوكول ASGI
    'channels',
    'corsheaders',
  
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # تطبيقات المشروع
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',

    
    'attendance',

]



ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,used-alex-techcodesdn-bdb25f1f.koyeb.app').split(',')

CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:8000",   # إضافة نطاق السيرفر نفسه
        "http://127.0.0.1:8000",
        "https://used-alex-techcodesdn-bdb25f1f.koyeb.app",
]

# 3. إعدادات الـ Channels Origins
CHANNELS_CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS # لتوحيد القائمة



if not DEBUG:
    # لا تسمح بالوصول إلا عبر نطاق المدرسة الرسمي

    
    # إعدادات الـ HTTPS
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # إخبار Django أن Nginx هو من يقوم بتشفير الـ SSL
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGIN_URL = 'web_login'
REST_FRAMEWORK = {
    'COERCE_DECIMAL_TO_STRING': True,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication', # للمتصفح فقط
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '5/minute',  # يسمح لغير المسجلين بـ 10 طلبات في الدقيقة
        'user': '1000/day',   # يسمح للمسجلين بـ 1000 طلب في اليوم
        'password_reset_limit': '3/hour', # للمسار الذي خصصناه سابقاً
    }

}





SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5), # مدة صلاحية مفتاح الدخول
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),    # مدة صلاحية مفتاح التجديد
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),  # الكلمة التي توضع قبل التوكن في الـ Header
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',    
    'BLACKLIST_AFTER_ROTATION': True,         
}



MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# مهم جداً مع Koyeb + Cloudflare
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1',
    'http://localhost',
    'http://0.0.0.0',
    'http://178.238.233.218',
]



ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'core.asgi.application'



# في بيئة Docker، سنعتمد على DATABASE_URL إذا وجدت (للسيرفر) 
# أو سنبني الرابط يدوياً للمحلي
if os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'school_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'your_password'),
            'HOST': os.getenv('DB_HOST', 'db'),  # 'db' هو اسم الخدمة في docker-compose
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }


# DATABASES = {
#     'default': dj_database_url.config(
#         # يحاول قراءة DATABASE_URL من البيئة، وإذا لم يجدها يستخدم القيمة الافتراضية
#         default=os.getenv('DATABASE_URL'),
#         conn_max_age=600
#     )
# }

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('DB_NAME'),
#         'USER': os.getenv('DB_USER'),
#         'PASSWORD': os.getenv('DB_PASSWORD'),
#         'HOST': os.getenv('DB_HOST'),
#         'PORT': os.getenv('DB_PORT'),
#     }
# }

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }




AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'attendance.User'





LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Riyadh'

USE_I18N = True

USE_TZ = True






# (7.3) تصحيح منفذ Redis الافتراضي 6379
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.getenv('REDIS_URL', 'redis://redis:6379/0')], 
        },
    },
}




STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django_error.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}