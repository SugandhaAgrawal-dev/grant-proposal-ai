"""apps/proposals/serializers.py"""
from rest_framework import serializers
from apps.proposals.models import OrganizationProfile, GrantProposal, ProposalSection


class OrganizationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrganizationProfile
        fields = "__all__"
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class ProposalSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProposalSection
        fields = ["id", "name", "requirements", "page_limit", "order",
                  "content", "status", "llm_provider", "generation_time",
                  "word_count", "quality_score", "reviewer_notes",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "status", "llm_provider", "generation_time",
                            "word_count", "created_at", "updated_at"]


class GrantProposalSerializer(serializers.ModelSerializer):
    sections    = ProposalSectionSerializer(many=True, read_only=True)
    total_words = serializers.IntegerField(read_only=True)
    created_by  = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = GrantProposal
        fields = ["id", "title", "status", "llm_provider", "rfp_metadata",
                  "reviewer_notes", "docx_file", "error_message", "total_words",
                  "created_by", "rfp_document", "org_profile", "sections",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "status", "error_message", "docx_file",
                            "created_at", "updated_at"]


class GenerateProposalSerializer(serializers.Serializer):
    """Request body for kicking off proposal generation."""
    rfp_document_id  = serializers.UUIDField(required=False, allow_null=True)
    org_profile_id   = serializers.UUIDField()
    title            = serializers.CharField(max_length=500)
    llm_provider     = serializers.ChoiceField(
        choices=["ollama", "openai", "claude"], default="ollama"
    )
    sections         = serializers.ListField(
        child=serializers.DictField(),
        help_text='[{"name":"Technical Approach","requirements":"...","page_limit":10,"order":1}]'
    )


class RegenerateSectionSerializer(serializers.Serializer):
    reviewer_feedback = serializers.CharField(min_length=5)
    llm_provider      = serializers.ChoiceField(
        choices=["ollama", "openai", "claude"], default="ollama"
    )
