"""apps/documents/tasks.py — Background document processing tasks."""
import asyncio
from celery import shared_task
from apps.documents.models import UploadedDocument
from apps.documents.parser import DocumentProcessor


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id: str):
    """
    Background task: parse a document and extract all content blocks.
    Triggered automatically on upload.
    """
    try:
        document  = UploadedDocument.objects.get(id=document_id)
        processor = DocumentProcessor()
        asyncio.run(processor.process(document))
        return {"status": "success", "document_id": document_id}
    except UploadedDocument.DoesNotExist:
        return {"status": "error", "message": f"Document {document_id} not found"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
