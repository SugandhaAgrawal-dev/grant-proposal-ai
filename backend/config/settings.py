"""
config/settings.py
Django settings for Healthcare Grant Proposal Generator.
"""
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
# Reading env file but not failing if it doesn't exist (production)
if Path(BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-change-in-production")
DEBUG       = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    # Local apps
    "apps.documents",
    "apps.proposals",
    "apps.compliance",
    "apps.llm",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Serve static files
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

# Only enable AutoLogin in Debug mode for convenience
if DEBUG:
    MIDDLEWARE.append("config.middleware.AutoLoginMiddleware")

MIDDLEWARE += [
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://postgres:password@localhost:5432/grant_proposal_db",
    )
}

# ── Password Validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True

# ── Static & Media ────────────────────────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Cloud deployment static file serving
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL   = "/media/"
MEDIA_ROOT  = BASE_DIR / env("MEDIA_ROOT", default="media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000"],
)
CORS_ALLOW_CREDENTIALS = True

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL        = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND    = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"

# ── LLM Configuration ─────────────────────────────────────────────────────────
LLM_CONFIG = {
    "default_provider": env("DEFAULT_LLM_PROVIDER", default="ollama"),
    "ollama": {
        "base_url":   env("OLLAMA_BASE_URL",   default="http://localhost:11434"),
        "llm_model":  env("OLLAMA_LLM_MODEL",  default="llama3.1:8b"),
        "embed_model":env("OLLAMA_EMBED_MODEL", default="nomic-embed-text"),
        "timeout":    env.int("OLLAMA_TIMEOUT", default=120),
    },
    "openai": {
        "api_key": env("OPENAI_API_KEY", default=""),
        "model":   env("OPENAI_MODEL",   default="gpt-4o"),
    },
    "claude": {
        "api_key": env("ANTHROPIC_API_KEY", default=""),
        "model":   env("ANTHROPIC_MODEL",   default="claude-opus-4-5"),
    },
    "vertex": {
        "project":     env("GOOGLE_CLOUD_PROJECT",  default=""),
        "location":    env("GOOGLE_CLOUD_LOCATION", default="us-central1"),
        "llm_model":   env("VERTEX_LLM_MODEL",      default="gemini-1.5-pro-002"),
        "embed_model": env("VERTEX_EMBED_MODEL",     default="text-embedding-004"),
    },
}

# ── File Upload ───────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB   = env.int("MAX_UPLOAD_SIZE_MB", default=50)
ALLOWED_UPLOAD_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "image/tiff",
]
