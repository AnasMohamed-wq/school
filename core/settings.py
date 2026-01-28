import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv


os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true" # لمنع أخطاء التزامن في بعض البيئات
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent



SECRET_KEY = os.getenv('SECRET_KEY')


DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = ['*']


INSTALLED_APPS = [
    'daphne', # لتعامل مع بروتوكول ASGI
    'channels',
  
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

CHANNELS_CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

REST_FRAMEWORK = {
    'COERCE_DECIMAL_TO_STRING': True,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}




SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60), # مدة صلاحية مفتاح الدخول
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),    # مدة صلاحية مفتاح التجديد
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),  # الكلمة التي توضع قبل التوكن في الـ Header
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',    
    'BLACKLIST_AFTER_ROTATION': True,         
}



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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




DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}




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
            "hosts": [('127.0.0.1', 6379)], 
        },
    },
}


STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # المجلد الذي ستجمع فيه الملفات
