"""WeasyPrint-based PDF generator with Strict Formal/Official Document Styling.

This generator follows strict Chinese formal document standards (Gongwen/Academic):
- Fonts: Cross-platform compatible (Windows/macOS/Linux)
- Margins: Standard official document margins
- Numbering: Chinese ideographic numbering for headers (一、 (一) 1. (1))
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import datetime

def markdown_to_pdf_weasyprint(markdown_text: str, output_path: str, *, title: Optional[str] = None) -> str:
    """Render Markdown to PDF using WeasyPrint with Strict Formal Styling.
    
    Args:
        markdown_text: markdown content
        output_path: target pdf path
        title: optional title used as the document metadata and header
        
    Returns:
        output_path
        
    Raises:
        ImportError: if weasyprint or markdown is not installed
    """
    try:
        import markdown as md
        from weasyprint import HTML, CSS
    except ImportError as e:
        raise ImportError(
            "WeasyPrint PDF generator requires: pip install weasyprint markdown\n"
            "System dependencies may also be needed. See module docstring."
        ) from e
    
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    doc_title = title or "正式报告"

    # Convert Markdown to HTML
    html_body = md.markdown(
        markdown_text,
        extensions=[
            'tables',           # Support tables
            'fenced_code',      # Support ```code blocks```
            'nl2br',            # Convert newlines to <br>
            'sane_lists',       # Better list handling
            'toc',              # Table of contents support
            'attr_list'         # Support for custom attributes
        ]
    )
    
    # Wrap in full HTML document
    html_doc = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>{doc_title}</title>
    </head>
    <body>
        <main>
            {html_body}
        </main>
    </body>
    </html>
    """
    
    # CSS styling - Strict Formal Standard (公文/正式论文规范)
    # 跨平台字体兼容：Windows (SimSun/SimHei), macOS (Songti/Heiti), Linux (Noto CJK)
    css = CSS(string=f"""
        /* ============================================================
           1. 页面设置 (Page Setup)
           ============================================================ */
        @page {{
            size: A4;
            /* 上3.7cm, 右2.6cm, 下3.5cm, 左2.8cm */
            margin: 3.7cm 2.6cm 3.5cm 2.8cm;
            
            /* 页眉：五号 (10.5pt)，居中 */
            @top-center {{
                content: "{doc_title}";
                font-size: 10.5pt;
                border-bottom: 1px solid #000;
                width: 100%;
                text-align: center;
                padding-bottom: 5px;
            }}
            
            /* 页脚：阿拉伯数字页码，五号，居中 */
            @bottom-center {{
                content: counter(page);
                font-size: 10.5pt;
            }}
        }}

        /* ============================================================
           2. 全局排版与字体 (Global Layout & Fonts)
           ============================================================ */
        /* 正文：宋体系列，跨平台回退 
           - Windows: SimSun
           - macOS: Songti SC, STSong
           - Linux: Noto Serif CJK SC, Source Han Serif SC
        */
        body {{
            font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif CJK SC', 'Noto Serif CJK', 'Source Han Serif SC', 'WenQuanYi Micro Hei', serif;
            font-size: 12pt;  /* 小四号 */
            line-height: 1.5; /* 1.5倍行距 */
            color: #000000;   /* 纯黑 */
            text-align: justify; /* 两端对齐 */
            text-justify: inter-ideograph;
            margin: 0;
            counter-reset: h1counter h2counter h3counter h4counter;
        }}
        
        /* 段落首行缩进2字符 */
        p {{
            text-indent: 2em;
            margin-top: 0;
            margin-bottom: 10pt; /* 段后间距 */
        }}

        /* ============================================================
           3. 标题层级与编号 (Headings)
           ============================================================ */
        /* 标题通用样式：黑体系列，跨平台回退 
           - Windows: SimHei
           - macOS: Heiti SC, STHeiti
           - Linux: Noto Sans CJK SC, Source Han Sans SC
        */
        h1, h2, h3, h4 {{
            font-family: 'SimHei', 'Heiti SC', 'STHeiti', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans SC', 'WenQuanYi Zen Hei', sans-serif;
            font-weight: bold;
            color: #000;
            text-align: left; /* 顶格书写 */
            margin-top: 1em;
            margin-bottom: 0.8em;
            page-break-after: avoid;
            page-break-inside: avoid;
        }}

        /* 一级标题：三号黑体 (16pt)，格式"一、" */
        h1 {{
            font-size: 16pt;
            counter-increment: h1counter;
            counter-reset: h2counter;
        }}
        h1::before {{
            content: counter(h1counter, cjk-ideographic) "、";
        }}

        /* 二级标题：小三号黑体 (15pt)，格式"（一）" */
        h2 {{
            font-size: 15pt;
            counter-increment: h2counter;
            counter-reset: h3counter;
        }}
        h2::before {{
            content: "（" counter(h2counter, cjk-ideographic) "）";
        }}

        /* 三级标题：四号黑体 (14pt)，格式"1." */
        h3 {{
            font-size: 14pt;
            counter-increment: h3counter;
            counter-reset: h4counter;
        }}
        h3::before {{
            content: counter(h3counter) ". ";
        }}

        /* 四级标题：小四号加粗 (12pt)，格式"（1）" */
        h4 {{
            font-size: 12pt;
            counter-increment: h4counter;
        }}
        h4::before {{
            content: "（" counter(h4counter) "）";
        }}

        /* ============================================================
           4. 表格样式 (Tables)
           ============================================================ */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1em auto;
            font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif CJK SC', 'Noto Serif CJK', 'Source Han Serif SC', 'WenQuanYi Micro Hei', serif;
            font-size: 10.5pt; /* 五号 */
            page-break-inside: avoid;
        }}
        
        /* 简单实线边框 (公文常用) */
        th, td {{
            border: 1px solid #000;
            padding: 5px 8px;
            text-align: center; /* 表格内容通常居中 */
        }}
        
        /* 表头加粗 */
        th {{
            font-weight: bold;
            background-color: transparent; /* 不使用背景色 */
        }}

        /* ============================================================
           5. 图片与说明 (Figures & Captions)
           ============================================================ */
        img {{
            display: block;
            max-width: 80%; /* 图片不宜过大 */
            height: auto;
            margin: 10px auto;
            page-break-inside: avoid;
        }}

        /* 图注表注样式 */
        em, .caption {{
            display: block;
            text-align: center;
            font-size: 10.5pt; /* 五号 */
            font-style: normal; /* 取消斜体 */
            margin-top: 5px;
            margin-bottom: 1em;
        }}

        /* ============================================================
           6. 其他元素 (Misc)
           ============================================================ */
        
        /* 链接 */
        a {{
            color: #000;
            text-decoration: none;
        }}
        
        /* 列表 */
        ul, ol {{
            margin-left: 2em;
            padding-left: 0;
            line-height: 1.5;
        }}

        /* 代码块 */
        pre {{
            font-family: 'Courier New', 'Monaco', 'Consolas', monospace;
            font-size: 10.5pt;
            border: 1px solid #000;
            padding: 10px;
            margin: 10px 0;
            white-space: pre-wrap;
            text-indent: 0; /* 代码块内部不缩进 */
        }}
    """)
    
    # Generate PDF
    HTML(string=html_doc).write_pdf(str(out), stylesheets=[css])
    
    return str(out)


def markdown_to_pdf_auto(markdown_text: str, output_path: str, *, title: Optional[str] = None) -> str:
    """Try WeasyPrint first, fall back to ReportLab if not available."""
    try:
        return markdown_to_pdf_weasyprint(markdown_text, output_path, title=title)
    except ImportError:
        from .pdf import markdown_to_pdf
        return markdown_to_pdf(markdown_text, output_path, title=title)
