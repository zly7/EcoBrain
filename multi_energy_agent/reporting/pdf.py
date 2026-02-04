from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Callable

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    PageBreak, Table, TableStyle, HRFlowable
)


# 品牌色彩定义
BRAND_COLORS = {
    "primary": colors.HexColor("#667eea"),      # 主色调 - 紫蓝色
    "secondary": colors.HexColor("#764ba2"),    # 次要色 - 深紫色
    "accent": colors.HexColor("#10b981"),       # 强调色 - 绿色
    "dark": colors.HexColor("#1f2937"),         # 深色文字
    "gray": colors.HexColor("#6b7280"),         # 灰色文字
    "light_gray": colors.HexColor("#f3f4f6"),   # 浅灰背景
    "white": colors.white,
}


def _register_cjk_font() -> str:
    """Register a CJK font that works without bundling TTF files."""
    font_name = "STSong-Light"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    except Exception:
        # If registration fails, fall back to Helvetica (might not render CJK).
        font_name = "Helvetica"
    return font_name


def _create_styles(font_name: str) -> dict:
    """Create styled paragraph styles with brand colors."""
    styles = getSampleStyleSheet()

    custom_styles = {
        "base": ParagraphStyle(
            "Base",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10.5,
            leading=16,
            spaceAfter=8,
            textColor=BRAND_COLORS["dark"],
        ),
        "title": ParagraphStyle(
            "Title",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=24,
            leading=32,
            spaceAfter=20,
            spaceBefore=10,
            textColor=BRAND_COLORS["primary"],
            alignment=1,  # Center
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=18,
            leading=24,
            spaceAfter=12,
            spaceBefore=20,
            textColor=BRAND_COLORS["primary"],
            borderPadding=(0, 0, 4, 0),
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=14,
            leading=20,
            spaceAfter=10,
            spaceBefore=16,
            textColor=BRAND_COLORS["secondary"],
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=12,
            leading=18,
            spaceAfter=8,
            spaceBefore=12,
            textColor=BRAND_COLORS["dark"],
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            leftIndent=15,
            rightIndent=15,
            spaceAfter=8,
            textColor=BRAND_COLORS["gray"],
            backColor=BRAND_COLORS["light_gray"],
            borderPadding=8,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=12,
            textColor=BRAND_COLORS["dark"],
            backColor=BRAND_COLORS["light_gray"],
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10.5,
            leading=16,
            spaceAfter=4,
            leftIndent=20,
            bulletIndent=10,
            textColor=BRAND_COLORS["dark"],
        ),
        "summary": ParagraphStyle(
            "Summary",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=18,
            spaceAfter=10,
            textColor=BRAND_COLORS["dark"],
            backColor=colors.HexColor("#f0f9ff"),
            borderPadding=12,
        ),
    }

    return custom_styles


def _header_footer(canvas, doc, title: str = "绿色园区低碳发展规划报告"):
    """Add header and footer to each page."""
    canvas.saveState()

    # Header
    canvas.setFillColor(BRAND_COLORS["primary"])
    canvas.rect(0, A4[1] - 15*mm, A4[0], 15*mm, fill=1, stroke=0)

    canvas.setFillColor(BRAND_COLORS["white"])
    canvas.setFont("STSong-Light", 10)
    try:
        canvas.drawString(18*mm, A4[1] - 10*mm, title)
    except Exception:
        canvas.drawString(18*mm, A4[1] - 10*mm, "Green Park Report")

    # Footer
    canvas.setFillColor(BRAND_COLORS["gray"])
    canvas.setFont("STSong-Light", 9)
    page_num = doc.page
    try:
        footer_text = f"第 {page_num} 页 | EcoBrain 多能源园区低碳规划系统"
    except Exception:
        footer_text = f"Page {page_num}"
    canvas.drawCentredString(A4[0]/2, 10*mm, footer_text)

    # Footer line
    canvas.setStrokeColor(BRAND_COLORS["light_gray"])
    canvas.setLineWidth(0.5)
    canvas.line(18*mm, 15*mm, A4[0] - 18*mm, 15*mm)

    canvas.restoreState()


def _escape_text(s: str) -> str:
    """Escape for ReportLab Paragraph (XML-ish) and handle special chars."""
    # First escape XML special chars
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Replace problematic special symbols with safe alternatives
    replacements = {
        "°": "度",
        "²": "2",
        "³": "3",
        "±": "+/-",
        "×": "x",
        "÷": "/",
        "≈": "约",
        "≤": "<=",
        "≥": ">=",
        "≠": "!=",
        "→": "->",
        "←": "<-",
        "↑": "^",
        "↓": "v",
        "•": "·",
        "…": "...",
        "—": "-",
        "–": "-",
        "'": "'",
        "'": "'",
        """: '"',
        """: '"',
    }

    for old, new in replacements.items():
        s = s.replace(old, new)

    return s


def _format_markdown_inline(text: str) -> str:
    """转换 Markdown 行内格式（粗体、斜体）为 ReportLab XML 标签。

    注意：必须先调用 _escape_text 转义文本，再调用此函数。
    """
    # Bold text handling
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

    # Italic text handling
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)

    return text


def _add_colored_bullet(text: str, color: colors.Color = BRAND_COLORS["accent"]) -> str:
    """Add a colored bullet point to text."""
    return f'<font color="{color.hexval()}">●</font> {text}'


def markdown_to_pdf(markdown_text: str, output_path: str, *, title: Optional[str] = None) -> str:
    """Render (simple) Markdown to a professional PDF file with brand colors.

    This renderer supports:
    - headings (#/##/###)
    - bullet lists
    - numbered lists
    - blockquotes
    - code blocks
    - horizontal rules
    - colored styling

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
    styles = _create_styles(font_name)

    story: List = []

    # Title page
    doc_title = title or "绿色园区低碳发展规划报告"
    story.append(Spacer(1, 60))
    story.append(Paragraph(_escape_text(doc_title), styles["title"]))
    story.append(Spacer(1, 20))

    # Decorative line
    story.append(HRFlowable(
        width="60%",
        thickness=2,
        color=BRAND_COLORS["primary"],
        spaceBefore=10,
        spaceAfter=30,
        hAlign='CENTER'
    ))

    # Subtitle
    story.append(Paragraph(
        _escape_text("EcoBrain 多能源园区低碳规划系统"),
        ParagraphStyle(
            "Subtitle",
            parent=styles["base"],
            fontSize=12,
            textColor=BRAND_COLORS["gray"],
            alignment=1,
        )
    ))
    story.append(PageBreak())

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title=doc_title,
    )

    lines = (markdown_text or "").splitlines()
    in_code = False
    code_buf: List[str] = []
    chapter_count = 0

    for raw in lines:
        line = raw.rstrip("\n")

        # Code block handling
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                # Add code block with background
                code_text = "\n".join(code_buf)
                story.append(Preformatted(code_text, styles["code"]))
                story.append(Spacer(1, 8))
            continue

        if in_code:
            code_buf.append(line)
            continue

        # Empty line
        if not line.strip():
            story.append(Spacer(1, 6))
            continue

        # Horizontal rule
        if line.strip() in ["---", "***", "___"]:
            story.append(HRFlowable(
                width="100%",
                thickness=1,
                color=BRAND_COLORS["light_gray"],
                spaceBefore=10,
                spaceAfter=10,
            ))
            continue

        # H1 - Chapter heading with colored background
        if line.startswith("# "):
            chapter_count += 1
            heading_text = _format_markdown_inline(_escape_text(line[2:].strip()))

            # Add chapter separator
            if chapter_count > 1:
                story.append(Spacer(1, 20))

            # Create a table for colored heading background
            heading_table = Table(
                [[Paragraph(heading_text, styles["h1"])]],
                colWidths=[doc.width],
            )
            heading_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, -1), 3, BRAND_COLORS["primary"]),
            ]))
            story.append(heading_table)
            story.append(Spacer(1, 10))
            continue

        # H2
        if line.startswith("## "):
            story.append(Spacer(1, 8))
            h2_text = _format_markdown_inline(_escape_text(line[3:].strip()))
            story.append(Paragraph(h2_text, styles["h2"]))
            # Add subtle underline
            story.append(HRFlowable(
                width="30%",
                thickness=1,
                color=BRAND_COLORS["secondary"],
                spaceBefore=2,
                spaceAfter=8,
                hAlign='LEFT'
            ))
            continue

        # H3
        if line.startswith("### "):
            h3_text = _format_markdown_inline(_escape_text(line[4:].strip()))
            story.append(Paragraph(h3_text, styles["h3"]))
            continue

        # Blockquote
        if line.startswith(">"):
            quote_text = _format_markdown_inline(_escape_text(line.lstrip("> ").strip()))
            story.append(Paragraph(quote_text, styles["quote"]))
            continue

        # Bullet list with colored bullets
        if re.match(r"^\s*[-*]\s+", line):
            item_text = re.sub(r"^\s*[-*]\s+", "", line)
            # 先转义文本，再处理格式，最后添加 colored bullet
            escaped_item = _format_markdown_inline(_escape_text(item_text))
            colored_item = _add_colored_bullet(escaped_item)
            story.append(Paragraph(colored_item, styles["bullet"]))
            continue

        # Numbered list
        if re.match(r"^\s*\d+\.\s+", line):
            numbered_text = _format_markdown_inline(_escape_text(line.strip()))
            story.append(Paragraph(numbered_text, styles["base"]))
            continue

        # Page break marker
        if line.strip() == "---pagebreak---":
            story.append(PageBreak())
            continue

        # 普通文本：先转义，再处理 Markdown 格式
        text = _format_markdown_inline(_escape_text(line))
        story.append(Paragraph(text, styles["base"]))

    # Build with header/footer
    def add_page_elements(canvas, doc):
        _header_footer(canvas, doc, doc_title)

    doc.build(story, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
    return str(out)
