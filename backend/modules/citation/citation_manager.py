"""
ResearchAI — Module 11: Citation Management
Generates properly formatted citations in APA, IEEE, MLA, Chicago, and BibTeX.
Never fabricates references — only cites papers with verified metadata.
"""

from __future__ import annotations
from typing import List, Optional
import re

from researchai.backend.core.models import Paper, Citation, CitationCollection
from researchai.backend.core.logger import get_logger
from researchai.backend.core.exceptions import CitationError

logger = get_logger("citation_manager")


class CitationManager:
    """
    Generates citations from Paper metadata.
    Supports APA, IEEE, MLA, Chicago, and BibTeX formats.
    """

    SUPPORTED_FORMATS = ["apa", "ieee", "mla", "chicago", "bibtex"]

    def generate_citation(self, paper: Paper, fmt: str) -> Citation:
        """Generate a single citation for a paper in the specified format."""
        fmt = fmt.lower()
        if fmt not in self.SUPPORTED_FORMATS:
            raise CitationError(f"Unsupported format '{fmt}'. Choose from: {self.SUPPORTED_FORMATS}")

        handler = {
            "apa": self._apa,
            "ieee": self._ieee,
            "mla": self._mla,
            "chicago": self._chicago,
            "bibtex": self._bibtex,
        }[fmt]

        text = handler(paper)
        bibtex_key = self._bibtex_key(paper) if fmt == "bibtex" else None
        return Citation(paper_id=paper.id, format=fmt, citation_text=text, bibtex_key=bibtex_key)

    def generate_collection(
        self, papers: List[Paper], fmt: str
    ) -> CitationCollection:
        """Generate a full reference list for a set of papers."""
        citations = [self.generate_citation(p, fmt) for p in papers]
        if fmt == "bibtex":
            formatted = "\n\n".join(c.citation_text for c in citations)
        else:
            formatted = "\n".join(f"{i+1}. {c.citation_text}" for i, c in enumerate(citations))
        return CitationCollection(format=fmt, citations=citations, formatted_references=formatted)

    # ------------------------------------------------------------------
    # Format Implementations
    # ------------------------------------------------------------------

    def _apa(self, p: Paper) -> str:
        authors = self._authors_apa(p)
        year = f"({p.year})." if p.year else "(n.d.)."
        doi = f" https://doi.org/{p.doi}" if p.doi else (f" {p.url}" if p.url else "")
        venue = f" {p.venue}." if p.venue else ""
        return f"{authors} {year} {p.title}.{venue}{doi}"

    def _ieee(self, p: Paper) -> str:
        authors = self._authors_ieee(p)
        year = f", {p.year}" if p.year else ""
        venue = f", *{p.venue}*" if p.venue else ""
        doi = f", doi: {p.doi}" if p.doi else ""
        return f"{authors}, \"{p.title}\"{venue}{year}{doi}."

    def _mla(self, p: Paper) -> str:
        authors = self._authors_mla(p)
        venue = f" *{p.venue}*," if p.venue else ""
        year = f" {p.year}," if p.year else ""
        doi = f" {p.doi}." if p.doi else (f" {p.url}." if p.url else "")
        return f"{authors} \"{p.title}.\" {venue}{year}{doi}"

    def _chicago(self, p: Paper) -> str:
        authors = self._authors_chicago(p)
        year = f" {p.year}." if p.year else ""
        venue = f" *{p.venue}*." if p.venue else ""
        doi = f" https://doi.org/{p.doi}." if p.doi else ""
        return f"{authors} \"{p.title}.\" {venue}{year}{doi}"

    def _bibtex(self, p: Paper) -> str:
        key = self._bibtex_key(p)
        authors_list = " and ".join(
            a.name if hasattr(a, "name") else a.get("name", "")
            for a in p.authors
        )
        year = str(p.year) if p.year else ""
        venue = p.venue or ""
        doi = p.doi or ""
        url = p.url or ""
        return (
            f"@article{{{key},\n"
            f"  title = {{{p.title}}},\n"
            f"  author = {{{authors_list}}},\n"
            f"  year = {{{year}}},\n"
            f"  journal = {{{venue}}},\n"
            f"  doi = {{{doi}}},\n"
            f"  url = {{{url}}}\n"
            f"}}"
        )

    # ------------------------------------------------------------------
    # Author Formatting Helpers
    # ------------------------------------------------------------------

    def _get_author_names(self, p: Paper) -> List[str]:
        names = []
        for a in p.authors:
            name = a.name if hasattr(a, "name") else a.get("name", "Unknown")
            names.append(name)
        return names or ["Unknown Author"]

    def _authors_apa(self, p: Paper) -> str:
        names = self._get_author_names(p)
        if not names:
            return "Unknown Author"
        formatted = []
        for name in names[:6]:
            parts = name.strip().split()
            if len(parts) > 1:
                last = parts[-1]
                initials = ". ".join(n[0].upper() for n in parts[:-1]) + "."
                formatted.append(f"{last}, {initials}")
            else:
                formatted.append(name)
        if len(names) > 6:
            formatted.append("et al.")
        return ", & ".join(formatted) if len(formatted) > 1 else formatted[0]

    def _authors_ieee(self, p: Paper) -> str:
        names = self._get_author_names(p)
        formatted = []
        for name in names[:3]:
            parts = name.strip().split()
            if len(parts) > 1:
                initials = ". ".join(n[0].upper() for n in parts[:-1]) + "."
                formatted.append(f"{initials} {parts[-1]}")
            else:
                formatted.append(name)
        if len(names) > 3:
            formatted.append("et al.")
        return ", ".join(formatted)

    def _authors_mla(self, p: Paper) -> str:
        names = self._get_author_names(p)
        if not names:
            return "Unknown"
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{names[0]} et al."

    def _authors_chicago(self, p: Paper) -> str:
        return self._authors_apa(p)

    def _bibtex_key(self, p: Paper) -> str:
        names = self._get_author_names(p)
        first_author = names[0].split()[-1].lower() if names else "unknown"
        year = str(p.year or "nd")
        title_word = re.sub(r"[^a-z]", "", (p.title or "").split()[0].lower())
        return f"{first_author}{year}{title_word}"
