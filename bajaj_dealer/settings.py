from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,192.168.1.37,localhost,809b-103-46-201-88.ngrok-free.app').split(',')


# --- APPS ---
INSTALLED_APPS = [
    'jazzmin',                        # ← must be FIRST
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
]
JAZZMIN_SETTINGS = {
    "site_title":        "Skyline Bajaj",
    "site_header":       "Skyline Bajaj Admin",
    "site_brand":        "Skyline Bajaj",
    "welcome_sign":      "Welcome to Skyline Bajaj Admin",
    "copyright":         "Skyline Bajaj",
    "search_model":      ["core.Enquiry", "core.ServiceBooking"],
    "topmenu_links": [
        {"name": "View Site", "url": "/", "new_window": True},
    ],
    "icons": {
        "auth.User":              "fas fa-users",
        "core.Showroom":          "fas fa-store",
        "core.ServiceStation":    "fas fa-wrench",
        "core.Bike":              "fas fa-motorcycle",
        "core.BikeCategory":      "fas fa-tags",
        "core.Enquiry":           "fas fa-comments",
        "core.ServiceBooking":    "fas fa-calendar-check",
        "core.ExchangeRequest":   "fas fa-exchange-alt",
        "core.YouTubeVideo":      "fab fa-youtube",
    },
    "default_icon_parents":  "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "show_ui_builder":       False,
}

JAZZMIN_UI_TWEAKS = {
    "theme":                    "flatly",
    "dark_mode_theme":          None,
    "navbar_small_text":        False,
    "brand_colour":             "navbar-primary",
    "accent":                   "accent-primary",
    "navbar":                   "navbar-white navbar-light",
    "no_navbar_border":         False,
    "sidebar":                  "sidebar-light-primary",
    "sidebar_nav_compact_style": True,
    "sidebar_disable_expand":   False,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serve static files efficiently
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',    # CSRF protection on all forms
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
                # 'core.context_processors.site_settings',  # global context
                'core.context_processors.site_globals'
            ],
        },
    },
]

WSGI_APPLICATION = 'bajaj_dealer.wsgi.application'

# --- DATABASE ---
# Uses SQLite by default. Set env vars to switch to PostgreSQL.
_db_name = config('DB_NAME', default='')
if _db_name:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _db_name,
            'USER': config('DB_USER', default=''),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- LOCALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── EMAIL ──────────────────────────────────────────────────────────────────────
EMAIL_BACKEND    = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST       = 'smtp.gmail.com'
EMAIL_PORT       = 587
EMAIL_USE_TLS    = True
EMAIL_HOST_USER  = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('EMAIL_HOST_USER', default='')
DEALER_MASTER_EMAIL = config('DEALER_MASTER_EMAIL', default='')

# --- SECURITY HEADERS (enable in production) ---
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'

# --- CUSTOM SITE SETTINGS ---
WHATSAPP_NUMBER = config('WHATSAPP_NUMBER', default='8360156287')
