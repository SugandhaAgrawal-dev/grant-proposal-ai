"""apps/documents/serializers.py"""
from rest_framework import serializers
from apps.documents.models import UploadedDocument, ParsedBlock


class ParsedBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ParsedBlock
        fields = ["id", "block_type", "content", "page_number",
                  "block_index", "parsed_data", "word_count", "created_at"]


class UploadedDocumentSerializer(serializers.ModelSerializer):
    blocks      = ParsedBlockSerializer(many=True, read_only=True)
    uploaded_by = serializers.StringRelatedField(read_only=True)
    file_size_kb= serializers.SerializerMethodField()

    class Meta:
        model  = UploadedDocument
        fields = ["id", "name", "document_type", "file", "file_size",
                  "file_size_kb", "status", "error_message", "page_count",
                  "raw_text", "uploaded_by", "blocks", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "error_message", "page_count",
                            "raw_text", "created_at", "updated_at"]

    def get_file_size_kb(self, obj):
        return round(obj.file_size / 1024, 1) if obj.file_size else 0


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Used for upload — only file and name required."""
    class Meta:
        model  = UploadedDocument
        fields = ["name", "file"]

    def validate_file(self, value):
        from django.conf import settings
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB} MB."
            )
        allowed = settings.ALLOWED_UPLOAD_TYPES
        if value.content_type not in allowed:
            raise serializers.ValidationError(
                f"Unsupported file type: {value.content_type}. "
                f"Allowed: PDF, DOCX, Excel, PNG, JPEG, TIFF."
            )
        return value
