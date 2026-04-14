"""apps/proposals/urls.py"""
from django.urls import path
from apps.proposals import views

urlpatterns = [
    # Organisation profiles
    path("organisations/",          views.OrgProfileListCreate.as_view(), name="org-list"),
    path("organisations/<uuid:pk>/", views.OrgProfileDetail.as_view(),    name="org-detail"),

    # Proposals
    path("",                          views.ProposalListView.as_view(),  name="proposal-list"),
    path("generate/",                 views.generate_proposal,           name="proposal-generate"),
    path("<uuid:pk>/",                views.ProposalDetailView.as_view(),name="proposal-detail"),
    path("<uuid:pk>/status/",         views.proposal_status,             name="proposal-status"),
    path("<uuid:pk>/export/",         views.export_to_docx,              name="proposal-export"),
    path("<uuid:pk>/download/",       views.download_docx,               name="proposal-download"),
    path("<uuid:pk>/review/",         views.update_proposal_review,      name="proposal-review"),

    # Sections
    path("sections/<uuid:pk>/",           views.update_section,       name="section-update"),
    path("sections/<uuid:pk>/regenerate/", views.regenerate_section,  name="section-regenerate"),
]
