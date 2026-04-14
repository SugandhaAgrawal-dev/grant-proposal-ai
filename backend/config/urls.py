"""config/urls.py — Root URL configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/",          admin.site.urls),
    # Auth
    path("api/auth/token/",         TokenObtainPairView.as_view(),  name="token_obtain"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(),     name="token_refresh"),
    # Apps
    path("api/documents/",  include("apps.documents.urls")),
    path("api/proposals/",  include("apps.proposals.urls")),
    path("api/compliance/", include("apps.compliance.urls")),
    path("api/llm/",        include("apps.llm.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
