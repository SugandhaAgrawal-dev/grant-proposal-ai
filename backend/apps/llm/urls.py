"""apps/llm/urls.py"""
from django.urls import path
from apps.llm import views

urlpatterns = [
    path("health/",    views.health_check,  name="llm-health"),
    path("providers/", views.list_providers, name="llm-providers"),
    path("models/",    views.list_models,    name="llm-models"),
    path("test/",      views.test_generate,  name="llm-test"),
]
