"""
apps/documents/models.py

Models:
  UploadedDocument  — a raw uploaded file (PDF, DOCX, Excel, image)
  ParsedBlock       — an individual content block extracted from the document
                      (text paragraph, table, OCR'd image, chart, metadata)
"""
import uuid
from django.db import models
from django.contrib.auth.models import User


class UploadedDocument(models.Model):

    class DocumentType(models.TextChoices):
        PDF    = "pdf",   "PDF"
        DOCX   = "docx",  "DOCX"
        EXCEL  = "excel", "Excel"
        IMAGE  = "image", "Scanned Image"

    class Status(models.TextChoices):
        UPLOADED  = "uploaded",  "Uploaded"
        PARSING   = "parsing",   "Parsing"
        PARSED    = "parsed",    "Parsed"
        FAILED    = "failed",    "Failed"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by   = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    name          = models.CharField(max_length=500)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file          = models.FileField(upload_to="documents/%Y/%m/")
    file_size     = models.PositiveIntegerField(default=0)         # bytes
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    error_message = models.TextField(blank=True)
    page_count    = models.PositiveIntegerField(default=0)
    raw_text      = models.TextField(blank=True)                   # full extracted text
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.document_type})"


class ParsedBlock(models.Model):

    class BlockType(models.TextChoices):
        TEXT     = "text",     "Text"
        TABLE    = "table",    "Table"
        IMAGE    = "image",    "Image/OCR"
        CHART    = "chart",    "Chart"
        METADATA = "metadata", "Metadata"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document     = models.ForeignKey(UploadedDocument, on_delete=models.CASCADE, related_name="blocks")
    block_type   = models.CharField(max_length=20, choices=BlockType.choices)
    content      = models.TextField()                              # extracted text / markdown table
    page_number  = models.PositiveIntegerField(default=0)
    block_index  = models.PositiveIntegerField(default=0)          # order within page
    parsed_data  = models.JSONField(null=True, blank=True)         # structured output from LLM
    word_count   = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["page_number", "block_index"]

    def __str__(self):
        return f"{self.block_type} block (page {self.page_number}) — {self.document.name}"
