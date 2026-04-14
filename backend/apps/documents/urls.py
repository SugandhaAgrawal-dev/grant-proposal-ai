"""apps/documents/urls.py"""
from django.urls import path
from apps.documents import views

urlpatterns = [
    path("",                views.DocumentListCreateView.as_view(), name="document-list"),
    path("<uuid:pk>/",      views.DocumentDetailView.as_view(),     name="document-detail"),
    path("<uuid:pk>/blocks/",    views.DocumentBlocksView.as_view(),     name="document-blocks"),
    path("<uuid:pk>/reprocess/", views.reprocess_document,              name="document-reprocess"),
]
