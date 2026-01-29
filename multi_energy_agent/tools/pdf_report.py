from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict

from .base import BaseTool


class RenderPDFReportInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    markdown_path: str = Field(..., description="Path to report.md")
    pdf_path: str = Field(..., description="Target path for report.pdf")
    title: Optional[str] = Field(default=None, description="Optional PDF title")


class RenderPDFReportTool(BaseTool):
    name = "render_pdf_report"
    description = "Render a markdown report to a PDF file saved locally."
    InputModel = RenderPDFReportInput
    timeout_s = 60.0

    def _run(self, payload: RenderPDFReportInput) -> Dict[str, Any]:
        from pathlib import Path

        md_path = Path(payload.markdown_path)
        if not md_path.exists():
            return {
                "ok": False,
                "error": {"type": "missing_file", "message": f"markdown_path not found: {md_path}"},
            }

        md_text = md_path.read_text(encoding="utf-8", errors="ignore")
        
        # Try WeasyPrint first, fall back to ReportLab
        try:
            from ..reporting.pdf_weasyprint import markdown_to_pdf_weasyprint
            pdf_path = markdown_to_pdf_weasyprint(md_text, payload.pdf_path, title=payload.title)
            pdf_engine = "weasyprint"
        except ImportError:
            from ..reporting.pdf import markdown_to_pdf
            pdf_path = markdown_to_pdf(md_text, payload.pdf_path, title=payload.title)
            pdf_engine = "reportlab"
        
        return {
            "ok": True,
            "pdf_path": pdf_path,
            "markdown_path": str(md_path),
            "pdf_engine": pdf_engine,
        }
