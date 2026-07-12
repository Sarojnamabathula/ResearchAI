"""
ResearchAI — Module 3: PDF Acquisition and Processing
Downloads PDFs, extracts structured text, splits into semantic chunks,
and prepares documents for embedding and retrieval.
"""

from __future__ import annotations
import re
import uuid
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import httpx

from researchai.backend.core.models import ExtractedPaper, PaperChunk
from researchai.backend.core.exceptions import PDFProcessingError
from researchai.backend.core.logger import get_logger
from researchai.config import settings

logger = get_logger("pdf_processor")

# Section heading heuristics
SECTION_PATTERNS = re.compile(
    r"^(?:\d+\.?\s+)?(abstract|introduction|background|related work|"
    r"methodology|methods|approach|experiments?|results?|evaluation|"
    r"discussion|conclusion|future work|references?|acknowledgements?)",
    re.IGNORECASE | re.MULTILINE,
)


class PDFProcessor:
    """
    Downloads a PDF from a URL, extracts structured text using PyMuPDF
    (fitz), splits the text into overlapping semantic chunks, and stores
    the result as an ExtractedPaper.
    """

    def __init__(self) -> None:
        self.papers_dir = settings.PAPERS_DIR

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download(self, pdf_url: str, paper_id: str) -> Path:
        """Download a PDF and return the local path."""
        safe_id = re.sub(r"[^\w\-]", "_", paper_id)
        dest = self.papers_dir / f"{safe_id}.pdf"
        if dest.exists():
            logger.info("PDF already cached: %s", dest)
            return dest

        logger.info("Downloading PDF: %s", pdf_url)
        try:
            with httpx.Client(
                timeout=settings.REQUEST_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "ResearchAI/1.0 (research assistant)"},
            ) as client:
                resp = client.get(pdf_url)
                resp.raise_for_status()
                size_mb = len(resp.content) / (1024 * 1024)
                if size_mb > settings.MAX_PDF_SIZE_MB:
                    raise PDFProcessingError(
                        f"PDF too large: {size_mb:.1f} MB > {settings.MAX_PDF_SIZE_MB} MB"
                    )
                dest.write_bytes(resp.content)
        except httpx.HTTPError as exc:
            raise PDFProcessingError(f"PDF download failed: {exc}") from exc

        logger.info("PDF saved: %s (%.1f MB)", dest, size_mb)
        return dest

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------

    def extract(self, pdf_path: Path, paper_id: str) -> ExtractedPaper:
        """Extract structured content from a local PDF file."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise PDFProcessingError(
                "PyMuPDF (fitz) is not installed. Run: pip install pymupdf"
            )

        logger.info("Extracting PDF: %s", pdf_path)
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            raise PDFProcessingError(f"Cannot open PDF: {exc}") from exc

        pages_text: List[str] = []
        figure_captions: List[str] = []
        table_captions: List[str] = []

        for page in doc:
            text = page.get_text("text")
            pages_text.append(text)
            # Detect figure/table captions
            for line in text.splitlines():
                stripped = line.strip()
                if re.match(r"^(figure|fig\.?)\s+\d+", stripped, re.IGNORECASE):
                    figure_captions.append(stripped)
                elif re.match(r"^table\s+\d+", stripped, re.IGNORECASE):
                    table_captions.append(stripped)

        full_text = "\n".join(pages_text)
        full_text = self._clean_text(full_text)

        sections = self._split_sections(full_text)
        abstract = sections.get("abstract") or self._extract_abstract(full_text)
        title = self._extract_title(pages_text[0] if pages_text else "")
        references = self._extract_references(sections.get("references", ""))

        chunks = self._chunk_text(full_text, paper_id)

        logger.info(
            "Extracted %d pages, %d sections, %d chunks from %s",
            len(doc), len(sections), len(chunks), paper_id,
        )

        return ExtractedPaper(
            paper_id=paper_id,
            title=title,
            abstract=abstract,
            sections=sections,
            references=references,
            figure_captions=figure_captions[:20],
            table_captions=table_captions[:20],
            full_text=full_text,
            total_pages=len(doc),
            chunks=chunks,
        )

    # ------------------------------------------------------------------
    # Process (download + extract)
    # ------------------------------------------------------------------

    def process(self, pdf_url: str, paper_id: str) -> ExtractedPaper:
        """End-to-end: download a PDF and return extracted content."""
        local_path = self.download(pdf_url, paper_id)
        extracted = self.extract(local_path, paper_id)
        extracted.paper_id = paper_id
        return extracted

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        # Remove excessive whitespace and ligature artefacts
        text = re.sub(r"\f", "\n", text)          # form feeds
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove lone page numbers
        text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
        return text.strip()

    def _split_sections(self, text: str) -> Dict[str, str]:
        """Split text into named sections using heading heuristics."""
        sections: Dict[str, str] = {}
        matches = list(SECTION_PATTERNS.finditer(text))
        for i, match in enumerate(matches):
            heading = match.group(0).strip().lower()
            heading = re.sub(r"^\d+\.?\s*", "", heading)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if content:
                sections[heading] = content
        return sections

    def _extract_abstract(self, text: str) -> Optional[str]:
        m = re.search(
            r"abstract[:\s]+([\s\S]{100,1500}?)(?=\n\n|\nintroduction|\n1\.)",
            text, re.IGNORECASE
        )
        return m.group(1).strip() if m else None

    def _extract_title(self, first_page: str) -> Optional[str]:
        lines = [l.strip() for l in first_page.splitlines() if l.strip()]
        # Title is usually the first non-trivially-short line
        for line in lines[:10]:
            if 10 < len(line) < 200:
                return line
        return None

    def _extract_references(self, ref_section: str) -> List[str]:
        if not ref_section:
            return []
        refs = re.split(r"\n(?=\[\d+\]|\d+\.\s)", ref_section)
        return [r.strip() for r in refs if len(r.strip()) > 20][:100]

    def _chunk_text(self, text: str, paper_id: str) -> List[PaperChunk]:
        """Split text into overlapping chunks of ~CHUNK_SIZE tokens."""
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        words = text.split()
        chunks: List[PaperChunk] = []
        i = 0
        idx = 0
        while i < len(words):
            chunk_words = words[i: i + chunk_size]
            chunk_text = " ".join(chunk_words)
            if len(chunk_text) >= 50:
                chunks.append(PaperChunk(
                    paper_id=paper_id,
                    chunk_index=idx,
                    text=chunk_text,
                ))
                idx += 1
            i += chunk_size - overlap
        return chunks
