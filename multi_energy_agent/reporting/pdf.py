from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, PageBreak


def _register_cjk_font() -> str:
    """Register a CJK font that works without bundling TTF files."""
    font_name = "STSong-Light"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    except Exception:
        # If registration fails, fall back to Helvetica (might not render CJK).
        font_name = "Helvetica"
    return font_name


def markdown_to_pdf(markdown_text: str, output_path: str, *, title: Optional[str] = None) -> str:
    """Render (simple) Markdown to a PDF file.

    This renderer is intentionally minimal, but it supports:
    - headings (#/##/###)
    - bullet lists
    - numbered lists
    - blockquotes
    - code blocks

    Args:
        markdown_text: markdown content
        output_path: target pdf path
        title: optional title used as the document metadata

    Returns:
        output_path
    """

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_cjk_font()
    styles = getSampleStyleSheet()

    base = ParagraphStyle(
        "Base",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10.5,
        leading=14,
        spaceAfter=6,
    )
    h1 = ParagraphStyle(
        "H1",
        parent=base,
        fontSize=16,
        leading=20,
        spaceAfter=10,
        spaceBefore=6,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=base,
        fontSize=13.5,
        leading=18,
        spaceAfter=8,
        spaceBefore=10,
    )
    h3 = ParagraphStyle(
        "H3",
        parent=base,
        fontSize=11.5,
        leading=16,
        spaceAfter=6,
        spaceBefore=8,
    )
    quote = ParagraphStyle(
        "Quote",
        parent=base,
        leftIndent=10,
        textColor=colors.HexColor("#333333"),
        italic=True,
    )
    code = ParagraphStyle(
        "Code",
        parent=base,
        fontName=font_name,
        fontSize=9.5,
        leading=12,
    )

    # Escape for ReportLab Paragraph (XML-ish)
    def esc(s: str) -> str:
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return s

    story: List = []
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title or "report",
    )

    lines = (markdown_text or "").splitlines()
    in_code = False
    code_buf: List[str] = []

    for raw in lines:
        line = raw.rstrip("\n")

        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                story.append(Preformatted("\n".join(code_buf), code))
                story.append(Spacer(1, 6))
            continue

        if in_code:
            code_buf.append(line)
            continue

        if not line.strip():
            story.append(Spacer(1, 6))
            continue

        if line.startswith("# "):
            story.append(Paragraph(esc(line[2:].strip()), h1))
            continue
        if line.startswith("## "):
            story.append(Paragraph(esc(line[3:].strip()), h2))
            continue
        if line.startswith("### "):
            story.append(Paragraph(esc(line[4:].strip()), h3))
            continue

        if line.startswith(">"):
            story.append(Paragraph(esc(line.lstrip("> ").strip()), quote))
            continue

        # bullet list
        if re.match(r"^\s*[-*]\s+", line):
            item = re.sub(r"^\s*[-*]\s+", "• ", line)
            story.append(Paragraph(esc(item), base))
            continue

        # numbered list
        if re.match(r"^\s*\d+\.\s+", line):
            story.append(Paragraph(esc(line.strip()), base))
            continue

        # page break marker
        if line.strip() == "---pagebreak---":
            story.append(PageBreak())
            continue

        story.append(Paragraph(esc(line), base))

    doc.build(story)
    return str(out)
