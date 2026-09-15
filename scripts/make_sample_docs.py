"""Render the demo handbooks in sample_docs/ as paginated PDFs.

Run once after cloning:

    python scripts/make_sample_docs.py

The PDFs are committed to the repo as well, so this script is only needed when
the content in scripts/sample_content.py changes. Each top-level numbered
section starts on a fresh page, which spreads citations across pages the way a
real handbook does and makes page-level citation visibly correct in the demo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    PageTemplate,
    Paragraph,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sample_content import DOCUMENTS  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "sample_docs"

TOP_LEVEL_RE = re.compile(r"^(\d+)\s")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "HandbookTitle", parent=base["Title"], fontSize=22, leading=27, spaceAfter=10
        ),
        "subtitle": ParagraphStyle(
            "HandbookSubtitle",
            parent=base["Normal"],
            fontSize=11.5,
            leading=16,
            textColor="#555555",
            alignment=1,
            spaceAfter=26,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontSize=15, leading=19, spaceBefore=4, spaceAfter=10
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontSize=12, leading=16, spaceBefore=14, spaceAfter=7
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=16.5,
            alignment=TA_JUSTIFY,
            spaceAfter=9,
        ),
    }


def _footer_factory(footer_text: str):
    def draw(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColorCMYK(0, 0, 0, 0.55)
        canvas.drawString(2.2 * cm, 1.35 * cm, footer_text)
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.35 * cm, f"Page {doc.page}")
        canvas.setStrokeColorCMYK(0, 0, 0, 0.25)
        canvas.line(2.2 * cm, 1.75 * cm, A4[0] - 2.2 * cm, 1.75 * cm)
        canvas.restoreState()

    return draw


def build(document: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / document["filename"]
    styles = _styles()

    doc = BaseDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.4 * cm,
        title=document["title"],
        author="Northwind Freight Group",
        subject=document["subtitle"],
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body", showBoundary=0
    )
    doc.addPageTemplates(
        [PageTemplate(id="main", frames=[frame], onPage=_footer_factory(document["footer"]))]
    )

    story: list = [
        Paragraph(document["title"], styles["title"]),
        Paragraph(document["subtitle"], styles["subtitle"]),
    ]

    # CondPageBreak rather than PageBreak: it breaks only when the page has
    # already been written to, so a section that happens to end exactly at the
    # page boundary does not leave a blank page behind.
    # The tolerance absorbs trailing paragraph spacing that can spill a few
    # points onto the next page and otherwise strand a near-empty one.
    section_break = CondPageBreak(doc.height - 30)

    first_section = True
    for heading, paragraphs in document["blocks"]:
        is_top_level = bool(TOP_LEVEL_RE.match(heading)) or heading.startswith("Appendix")
        if is_top_level and not first_section:
            story.append(section_break)
        if is_top_level:
            first_section = False
        story.append(Paragraph(heading, styles["h1" if is_top_level else "h2"]))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["body"]))

    doc.build(story)
    return out_path


def main() -> None:
    for document in DOCUMENTS:
        path = build(document)
        print(f"wrote {path.relative_to(path.parent.parent)} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
