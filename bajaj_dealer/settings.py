from pathlib import Path
from decouple import config
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='127.0.0.1,192.168.1.37,localhost'
).split(',')
 

# --- APPS ---
INSTALLED_APPS = [
    'jazzmin',                        # ← must be FIRST
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'webpush',  
    'core.apps.CoreConfig',
    'drf_spectacular',
    'cloudinary',
]

WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY":  config('VAPID_PUBLIC_KEY',  default=''),
    "VAPID_PRIVATE_KEY": config('VAPID_PRIVATE_KEY', default=''),
    "VAPID_ADMIN_EMAIL": config('VAPID_ADMIN_EMAIL', default='a4ashwanik4kr@gmail.com'),
}

# --- DRF ---
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --- CLOUDINARY ---
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY':    config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# --- JAZZMIN ---
JAZZMIN_SETTINGS = {
    "site_title":        "Skyline Bajaj",
    "site_header":       "Skyline Bajaj Admin",
    "site_brand":        "Skyline Bajaj",
    "site_logo":         "images/logo.png",
    "login_logo":        "images/logo.png",
    "site_logo_classes": "img-fluid",
    "custom_css":        "css/admin_custom.css",
    "welcome_sign":      "Welcome to Skyline Bajaj Admin",
    "copyright":         "Skyline Bajaj",
    "search_model":      ["core.Enquiry", "core.ServiceBooking"],
    "topmenu_links": [
        {"name": "View Site", "url": "/", "new_window": True},
    ],
    "icons": {
        "auth.User":            "fas fa-users",
        "core.Showroom":        "fas fa-store",
        "core.ServiceStation":  "fas fa-wrench",
        "core.Bike":            "fas fa-motorcycle",
        "core.BikeCategory":    "fas fa-tags",
        "core.Enquiry":         "fas fa-comments",
        "core.ServiceBooking":  "fas fa-calendar-check",
        "core.ExchangeRequest": "fas fa-exchange-alt",
        "core.YouTubeVideo":    "fab fa-youtube",
    },
    "default_icon_parents":  "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "show_ui_builder":       False,
}

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bajaj_dealer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_globals',
            ],
        },
    },
]

WSGI_APPLICATION = 'bajaj_dealer.wsgi.application'

# --- DATABASE ---
_db_name = config('DB_NAME', default='')
if _db_name:
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     _db_name,
            'USER':     config('DB_USER',     default=''),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST':     config('DB_HOST',     default='localhost'),
            'PORT':     config('DB_PORT',     default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }

# --- PASSWORD VALIDATION ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- STATIC & MEDIA ---
STATIC_URL      = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT     = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- LOCALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- EMAIL ---
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('EMAIL_HOST_USER',     default='')
DEALER_MASTER_EMAIL = config('DEALER_MASTER_EMAIL', default='')

# --- TELEGRAM ---
TELEGRAM_BOT_TOKEN       = config('TELEGRAM_BOT_TOKEN',       default='')
TELEGRAM_MASTER_CHAT_ID  = config('TELEGRAM_MASTER_CHAT_ID',  default='')

# --- WHATSAPP ---
WHATSAPP_NUMBER = config('WHATSAPP_NUMBER', default='9470725228')

# --- SECURITY HEADERS (production only) ---
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER      = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    X_FRAME_OPTIONS                = 'DENY'