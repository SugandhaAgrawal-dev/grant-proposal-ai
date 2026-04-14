"""
apps/proposals/models.py

Models:
  OrganizationProfile — health system profile used across proposals
  GrantProposal       — a full proposal draft linked to an RFP document
  ProposalSection     — an individual generated section of the proposal
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.documents.models import UploadedDocument


class OrganizationProfile(models.Model):
    """Health system profile reused across all proposals."""

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner                 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="org_profiles")
    name                  = models.CharField(max_length=300)
    short_name            = models.CharField(max_length=50, blank=True)
    service_area          = models.CharField(max_length=500, blank=True)
    patient_population    = models.TextField(blank=True)
    annual_patient_volume = models.PositiveIntegerField(null=True, blank=True)
    specialties           = models.JSONField(default=list, blank=True)
    certifications        = models.JSONField(default=list, blank=True)
    mission_statement     = models.TextField(blank=True)
    capability_statement  = models.TextField(blank=True)
    primary_contact_name  = models.CharField(max_length=200, blank=True)
    primary_contact_email = models.EmailField(blank=True)
    uei_number            = models.CharField(max_length=50, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def to_dict(self) -> dict:
        return {
            "id":                    str(self.id),
            "name":                  self.name,
            "service_area":          self.service_area,
            "patient_population":    self.patient_population,
            "annual_patient_volume": self.annual_patient_volume,
            "specialties":           self.specialties,
            "certifications":        self.certifications,
            "mission_statement":     self.mission_statement,
            "capability_statement":  self.capability_statement,
            "primary_contact_name":  self.primary_contact_name,
            "primary_contact_email": self.primary_contact_email,
        }


class GrantProposal(models.Model):

    class Status(models.TextChoices):
        DRAFT             = "draft",             "Draft"
        GENERATING        = "generating",        "Generating"
        COMPLIANCE_REVIEW = "compliance_review",  "Compliance Review"
        HUMAN_REVIEW      = "human_review",       "Human Review"
        APPROVED          = "approved",           "Approved"
        SUBMITTED         = "submitted",          "Submitted"
        ERROR             = "error",              "Error"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="proposals")
    rfp_document  = models.ForeignKey(UploadedDocument, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name="proposals")
    org_profile   = models.ForeignKey(OrganizationProfile, on_delete=models.SET_NULL,
                                       null=True, blank=True)
    title         = models.CharField(max_length=500)
    status        = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    llm_provider  = models.CharField(max_length=20, default="ollama")
    rfp_metadata  = models.JSONField(default=dict, blank=True)    # extracted from RFP doc
    reviewer_notes= models.TextField(blank=True)
    docx_file     = models.FileField(upload_to="proposals/exports/", null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def total_words(self) -> int:
        return sum(s.word_count for s in self.sections.all())


class ProposalSection(models.Model):

    class SectionStatus(models.TextChoices):
        PENDING     = "pending",     "Pending"
        GENERATING  = "generating",  "Generating"
        DONE        = "done",        "Done"
        FAILED      = "failed",      "Failed"

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal       = models.ForeignKey(GrantProposal, on_delete=models.CASCADE, related_name="sections")
    name           = models.CharField(max_length=200)
    requirements   = models.TextField(blank=True)
    page_limit     = models.PositiveIntegerField(null=True, blank=True)
    order          = models.PositiveIntegerField(default=0)
    content        = models.TextField(blank=True)                  # generated text
    status         = models.CharField(max_length=20, choices=SectionStatus.choices,
                                       default=SectionStatus.PENDING)
    llm_provider   = models.CharField(max_length=20, blank=True)
    generation_time= models.FloatField(null=True, blank=True)     # seconds
    word_count     = models.PositiveIntegerField(default=0)
    quality_score  = models.FloatField(null=True, blank=True)     # 0–10
    reviewer_notes = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.proposal.title} — {self.name}"

    def save(self, *args, **kwargs):
        self.word_count = len(self.content.split()) if self.content else 0
        super().save(*args, **kwargs)
