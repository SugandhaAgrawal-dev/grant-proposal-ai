"""
apps/documents/parser.py

Synthetic Parsing Pipeline
==========================
Routes each content block to the right extractor based on content type:

  PDF text   → PyMuPDF direct extraction
  PDF tables → pdfplumber table parser → markdown
  PDF images → pytesseract OCR
  DOCX       → python-docx paragraph + table extraction
  Excel      → openpyxl sheet → markdown tables
  Images     → pytesseract OCR

Each block is then optionally summarised by the LLM for structured output.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from apps.documents.models import UploadedDocument, ParsedBlock


@dataclass
class ContentBlock:
    """Raw extracted content block before DB persistence."""
    block_type:  str               # text | table | image | chart | metadata
    content:     str               # extracted text or markdown table
    page_number: int = 0
    block_index: int = 0
    parsed_data: Optional[dict] = None
    word_count:  int = 0

    def __post_init__(self):
        self.word_count = len(self.content.split())


class SyntheticParser:
    """
    Detects and routes each content block to the right parser.

    Usage:
        parser = SyntheticParser()
        blocks = parser.parse(file_path, document_type)
        # returns list[ContentBlock]
    """

    def parse(self, file_path: str, document_type: str) -> list[ContentBlock]:
        path = Path(file_path)
        dt   = document_type.lower()

        if dt == "pdf":
            return self._parse_pdf(path)
        elif dt == "docx":
            return self._parse_docx(path)
        elif dt == "excel":
            return self._parse_excel(path)
        elif dt == "image":
            return self._parse_image(path)
        else:
            raise ValueError(f"Unsupported document type: {dt}")

    # ── PDF ───────────────────────────────────────────────────────────────────

    def _parse_pdf(self, path: Path) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        block_idx = 0

        # Text + image blocks via PyMuPDF
        try:
            import fitz
            doc = fitz.open(str(path))
            for page_num, page in enumerate(doc):
                # Text blocks
                for raw in page.get_text("blocks"):
                    text = raw[4].strip()
                    if not text or len(text) < 10:
                        continue
                    blocks.append(ContentBlock(
                        block_type  = "text",
                        content     = text,
                        page_number = page_num + 1,
                        block_index = block_idx,
                    ))
                    block_idx += 1

                # Image blocks → OCR
                for img_info in page.get_images(full=True):
                    xref    = img_info[0]
                    base_img= doc.extract_image(xref)
                    img_bytes = base_img["image"]
                    ocr_text  = self._ocr_image_bytes(img_bytes)
                    if ocr_text and len(ocr_text.strip()) > 20:
                        blocks.append(ContentBlock(
                            block_type  = "image",
                            content     = ocr_text,
                            page_number = page_num + 1,
                            block_index = block_idx,
                        ))
                        block_idx += 1
            doc.close()
        except Exception as exc:
            blocks.append(ContentBlock(
                block_type="metadata",
                content=f"PyMuPDF extraction failed: {exc}",
            ))

        # Table blocks via pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    for table in page.extract_tables():
                        md = self._table_to_markdown(table)
                        if md:
                            blocks.append(ContentBlock(
                                block_type  = "table",
                                content     = md,
                                page_number = page_num + 1,
                                block_index = block_idx,
                            ))
                            block_idx += 1
        except Exception:
            pass

        return blocks

    # ── DOCX ──────────────────────────────────────────────────────────────────

    def _parse_docx(self, path: Path) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        block_idx = 0

        try:
            from docx import Document
            doc = Document(str(path))

            # Paragraphs
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text or len(text) < 5:
                    continue
                blocks.append(ContentBlock(
                    block_type  = "text",
                    content     = text,
                    page_number = 1,
                    block_index = block_idx,
                ))
                block_idx += 1

            # Tables
            for table in doc.tables:
                rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
                md   = self._table_to_markdown(rows)
                if md:
                    blocks.append(ContentBlock(
                        block_type  = "table",
                        content     = md,
                        page_number = 1,
                        block_index = block_idx,
                    ))
                    block_idx += 1

        except Exception as exc:
            blocks.append(ContentBlock(
                block_type="metadata",
                content=f"DOCX extraction failed: {exc}",
            ))

        return blocks

    # ── Excel ─────────────────────────────────────────────────────────────────

    def _parse_excel(self, path: Path) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        block_idx = 0

        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), data_only=True)

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = []
                for row in ws.iter_rows(values_only=True):
                    rows.append([str(c) if c is not None else "" for c in row])

                if rows:
                    md = self._table_to_markdown(rows)
                    blocks.append(ContentBlock(
                        block_type  = "table",
                        content     = f"## Sheet: {sheet_name}\n\n{md}",
                        page_number = 1,
                        block_index = block_idx,
                    ))
                    block_idx += 1

        except Exception as exc:
            blocks.append(ContentBlock(
                block_type="metadata",
                content=f"Excel extraction failed: {exc}",
            ))

        return blocks

    # ── Image (OCR) ───────────────────────────────────────────────────────────

    def _parse_image(self, path: Path) -> list[ContentBlock]:
        try:
            from PIL import Image
            import pytesseract
            img  = Image.open(str(path))
            text = pytesseract.image_to_string(img)
            if text.strip():
                return [ContentBlock(block_type="image", content=text.strip())]
        except Exception as exc:
            return [ContentBlock(
                block_type="metadata",
                content=f"OCR failed: {exc}",
            )]
        return []

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _ocr_image_bytes(self, img_bytes: bytes) -> str:
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(io.BytesIO(img_bytes))
            return pytesseract.image_to_string(img)
        except Exception:
            return ""

    def _table_to_markdown(self, table: list[list]) -> str:
        if not table or not table[0]:
            return ""
        header    = "| " + " | ".join(str(c or "") for c in table[0]) + " |"
        separator = "| " + " | ".join(["---"] * len(table[0])) + " |"
        rows = [
            "| " + " | ".join(str(c or "") for c in row) + " |"
            for row in table[1:]
            if any(c for c in row)
        ]
        return "\n".join([header, separator] + rows)


class DocumentProcessor:
    """
    Orchestrates parsing + LLM metadata extraction + DB persistence.

    Usage:
        processor = DocumentProcessor()
        await processor.process(document)   # updates document.status in DB
    """

    def __init__(self):
        self.parser = SyntheticParser()

    async def process(self, document: UploadedDocument) -> None:
        """Full pipeline: parse → extract metadata → save blocks to DB."""
        from apps.llm.router import LLMRouter
        import asyncio

        document.status = UploadedDocument.Status.PARSING
        document.save(update_fields=["status"])

        try:
            # 1. Parse into blocks
            blocks = self.parser.parse(
                file_path     = document.file.path,
                document_type = document.document_type,
            )

            # 2. Assemble raw text
            raw_text = "\n\n".join(b.content for b in blocks if b.block_type == "text")
            document.raw_text  = raw_text[:100_000]   # cap at 100k chars
            document.page_count= max((b.page_number for b in blocks), default=0)

            # 3. Save blocks to DB
            ParsedBlock.objects.filter(document=document).delete()
            db_blocks = [
                ParsedBlock(
                    document    = document,
                    block_type  = b.block_type,
                    content     = b.content,
                    page_number = b.page_number,
                    block_index = b.block_index,
                    word_count  = b.word_count,
                )
                for b in blocks
            ]
            ParsedBlock.objects.bulk_create(db_blocks)

            # 4. Extract structured metadata via LLM
            if raw_text:
                metadata = await self._extract_metadata(raw_text[:4000])
                # Save metadata as a special block
                import json
                ParsedBlock.objects.create(
                    document    = document,
                    block_type  = "metadata",
                    content     = json.dumps(metadata),
                    parsed_data = metadata,
                    page_number = 0,
                    block_index = 9999,
                )

            document.status = UploadedDocument.Status.PARSED
            document.save(update_fields=["status", "raw_text", "page_count"])

        except Exception as exc:
            document.status        = UploadedDocument.Status.FAILED
            document.error_message = str(exc)
            document.save(update_fields=["status", "error_message"])
            raise

    async def _extract_metadata(self, text: str) -> dict:
        """Use LLM to extract structured RFP/grant metadata from raw text."""
        import json, re
        from apps.llm.router import LLMRouter

        prompt = f"""Extract structured information from this healthcare grant/RFP document.
Return ONLY a JSON object with these fields:
{{
  "title":                    "document title or RFP name",
  "agency":                   "issuing agency or funder",
  "deadline":                 "submission deadline if found",
  "budget_limit":             "maximum budget if stated",
  "page_limit":               null,
  "certifications_required":  [],
  "grant_type":               "RFP | grant | solicitation | other",
  "naics_codes":              [],
  "key_sections":             []
}}

Document text:
{text}

JSON:"""

        try:
            router   = LLMRouter()
            raw      = await router.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )
            clean    = re.sub(r"```(?:json)?|```", "", raw).strip()
            return json.loads(clean)
        except Exception:
            return {}
