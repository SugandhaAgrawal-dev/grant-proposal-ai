"""apps/compliance/urls.py"""
from django.urls import path
from apps.compliance import views

urlpatterns = [
    path("<uuid:proposal_id>/check/",  views.run_compliance_check,  name="compliance-check"),
    path("<uuid:proposal_id>/report/", views.get_compliance_report, name="compliance-report"),
]
