"""DataIntakeAgent

Responsibilities (NO heavy math):
- Load / profile CSV(s) (basic statistics, missingness, schema)
- Extract text evidence from PDF(s)
- Parse Excel(s) into table artifacts (especially cashflow / energy-flow if present)
- Initialize and constantly refresh `plan.md`

Inputs (from blackboard state):
- state["scenario"]["scenario_id"] (required)
- state["inputs"]["csv_paths"]   : list[str] (optional)
- state["inputs"]["pdf_paths"]   : list[str] (optional)
- state["inputs"]["excel_paths"] : list[str] (optional)

Outputs:
- envelope stage=intake
- writes outputs/<scenario_id>/plan.md (refresh multiple times)
- writes artifact files under outputs/<scenario_id>/artifacts/
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import AgentRunResult, BaseAgent
from ..llm import StructuredLLMClient
from ..planning import PlanManager
from ..schemas import Assumption, DataGap, Evidence, Stage
from ..tools import default_tool_registry
from ..utils.logging import get_run_context


# ---------- shared plan tasks (full pipeline) ----------
PLAN_TASKS: List[Dict[str, str]] = [
    {"task_id": "T1", "title": "数据清单与来源登记（CSV/PDF/Excel）"},
    {"task_id": "T2", "title": "CSV 基础数据画像：字段、缺失、统计分布、时间粒度"},
    {"task_id": "T3", "title": "PDF 文档解析：抽取关键段落、形成证据条目（可审计）"},
    {"task_id": "T4", "title": "Excel 解析：识别现金流/能流表并结构化输出"},
    {"task_id": "T5", "title": "基于 KG + 基础数据：园区现状“描述”与边界定义"},
    {"task_id": "T6", "title": "DeepResearch：能流分析（来源-转换-去向-损失）"},
    {"task_id": "T7", "title": "DeepResearch：现金流分析（CAPEX/OPEX/补贴/收益）"},
    {"task_id": "T8", "title": "措施机会清单：不做优化，仅筛选+缺口+可解释性"},
    {"task_id": "T9", "title": "生成最终 Markdown 报告（>=1000字）"},
    {"task_id": "T10", "title": "本地保存 report.md，并在 artifacts 中保存中间产物"},
    {"task_id": "T11", "title": "为问答交互准备：生成可检索索引（数据字典/证据索引）"},
]


def _sanitize_id(value: str) -> str:
    value = value.strip() or "default"
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
    return value[:80] or "default"


def _try_import_pandas():
    try:
        import pandas as pd  # type: ignore
        return pd
    except Exception:
        return None


def _try_import_pdf_reader():
    # pypdf is preferred; PyPDF2 is fallback
    try:
        from pypdf import PdfReader  # type: ignore
        return PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
            return PdfReader
        except Exception:
            return None


class DataIntakeAgent(BaseAgent):
    def __init__(self, llm: Optional[StructuredLLMClient] = None, output_root: str = "outputs") -> None:
        super().__init__(stage=Stage.INTAKE, name="data_intake", llm=llm or StructuredLLMClient())
        self.output_root = output_root

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        scenario = state.get("scenario") or {}
        scenario_id = _sanitize_id(str(scenario.get("scenario_id") or "default-scenario"))
        out_dir = Path(state.get("output_dir") or Path(self.output_root) / scenario_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        state["output_dir"] = str(out_dir)

        plan_path = out_dir / "plan.md"
        plan = PlanManager(plan_path)
        plan.init_plan(scenario_id=scenario_id, tasks=PLAN_TASKS)

        inputs = state.get("inputs") or {}
        csv_paths = [str(p) for p in (inputs.get("csv_paths") or [])]
        pdf_paths = [str(p) for p in (inputs.get("pdf_paths") or [])]
        excel_paths = [str(p) for p in (inputs.get("excel_paths") or [])]

        artifacts_dir = out_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        run_ctx = get_run_context(state)
        logger = run_ctx.logger if run_ctx else None

        # tool registry (centralized)
        tools = state.get("tools")
        if tools is None:
            tools = default_tool_registry()
            state["tools"] = tools

        data_gaps: List[DataGap] = []

        # ---- T1: inventory ----
        plan.mark_doing("T1", "扫描输入文件列表并生成 inventory")
        inventory = self._build_inventory(csv_paths, pdf_paths, excel_paths)
        if inventory["missing_files"]:
            data_gaps.append(
                DataGap(
                    missing="missing_files",
                    impact=f"存在 {len(inventory['missing_files'])} 个文件路径不可读；报告将使用占位描述",
                    severity="high",
                )
            )
        plan.mark_done("T1", f"inventory 共 {len(inventory['files'])} 个文件")

        # ---- built-in back-data materialize (FHD + LYX + eco_knowledge_graph) ----
        # These data are shipped in-repo under other_back_data/ and eco_knowledge_graph/.
        selection = state.get("selection") or {}
        meta = selection.get("metadata") or {}
        filters = {
            "province": meta.get("province") or meta.get("province_name") or "",
            "city": meta.get("city") or meta.get("city_name") or "",
            "district": meta.get("district") or meta.get("county") or "",
            "park_name_contains": meta.get("park_name") or meta.get("park") or "",
            "industry_keywords": meta.get("industry_keywords") or meta.get("industry_list") or meta.get("industries") or [],
        }

        plan.append_log("Back-data materialize: fhd / lyx / eco_knowledge_graph")

        fhd_tool = tools.call(
            "load_fhd_back_data",
            {
                "output_dir": str(out_dir),
                "filters": filters,
                "max_matched_rows": 5000,
                "include_aoi_summary": True,
                "aoi_compute_area_km2": False,
            },
        )
        if logger:
            logger.info("tool load_fhd_back_data: ok=%s elapsed_ms=%s", fhd_tool.get("ok"), fhd_tool.get("elapsed_ms"))

        fhd_data = fhd_tool.get("data") or {}
        if not fhd_data.get("ok"):
            data_gaps.append(
                DataGap(
                    missing="fhd_back_data",
                    impact=f"FHD 园区名录/AOI 载入失败：{(fhd_data.get('error') or {}).get('message','unknown')}",
                    severity="medium",
                )
            )

        # Use FHD matched industry distribution as weights for LYX scoring
        industry_weights = {}
        try:
            top_inds = (fhd_data.get("metrics") or {}).get("matched_industry_distribution_top") or []
            for name, cnt in top_inds[:12]:
                if str(name).strip() and float(cnt) > 0:
                    industry_weights[str(name)] = float(cnt)
        except Exception:
            industry_weights = {}

        # If no matched industries, fallback to filter keywords
        if not industry_weights:
            kws = filters.get("industry_keywords") or []
            if isinstance(kws, str):
                kws = [kws]
            for k in kws[:12]:
                if str(k).strip():
                    industry_weights[str(k)] = 1.0

        lyx_tool = tools.call(
            "load_lyx_energy_scores",
            {
                "output_dir": str(out_dir),
                "industry_weights": industry_weights,
                "industry_keywords": list(industry_weights.keys()),
            },
        )
        if logger:
            logger.info("tool load_lyx_energy_scores: ok=%s elapsed_ms=%s", lyx_tool.get("ok"), lyx_tool.get("elapsed_ms"))

        lyx_data = lyx_tool.get("data") or {}
        if not lyx_data.get("ok"):
            data_gaps.append(
                DataGap(
                    missing="lyx_back_data",
                    impact=f"LYX 行业多能倾向推断失败：{(lyx_data.get('error') or {}).get('message','unknown')}",
                    severity="medium",
                )
            )

        eco_tool = tools.call(
            "materialize_eco_knowledge_graph",
            {
                "output_dir": str(out_dir),
                "chunk_size": 600,
                "chunk_overlap": 120,
            },
        )
        if logger:
            logger.info(
                "tool materialize_eco_knowledge_graph: ok=%s elapsed_ms=%s", eco_tool.get("ok"), eco_tool.get("elapsed_ms")
            )

        eco_data = eco_tool.get("data") or {}
        if not eco_data.get("ok"):
            data_gaps.append(
                DataGap(
                    missing="eco_knowledge_graph",
                    impact=f"eco_knowledge_graph 文档索引构建失败：{(eco_data.get('error') or {}).get('message','unknown')}",
                    severity="low",
                )
            )

        # Expand inventory to include these built-in sources for auditability
        try:
            for p in (fhd_data.get("inventory_files") or []):
                inventory["files"].append({"type": "back_data_fhd", "path": p, "size_bytes": os.path.getsize(p) if os.path.exists(p) else None})
            for p in (lyx_data.get("inventory_files") or []):
                inventory["files"].append({"type": "back_data_lyx", "path": p, "size_bytes": os.path.getsize(p) if os.path.exists(p) else None})
            for p in (eco_data.get("inventory_files") or []):
                inventory["files"].append({"type": "eco_knowledge_graph", "path": p, "size_bytes": os.path.getsize(p) if os.path.exists(p) else None})
        except Exception:
            pass

        # Optionally profile the small generated CSV (matched parks)
        try:
            matched_csv = (fhd_data.get("artifacts") or {}).get("matched_parks_csv")
            if matched_csv and os.path.exists(str(matched_csv)):
                csv_paths = csv_paths + [str(matched_csv)]
        except Exception:
            pass

        # Save inventory (after adding built-in sources)
        (artifacts_dir / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

        # ---- T2: CSV profiling ----
        plan.mark_doing("T2", "对 CSV 进行字段/缺失/统计画像（必要时仅抽样）")
        csv_profiles: List[Dict[str, Any]] = []
        csv_descriptions: List[Dict[str, Any]] = []
        if csv_paths:
            for p in csv_paths:
                prof, desc = self._profile_csv(Path(p), artifacts_dir=artifacts_dir)
                if prof:
                    csv_profiles.append(prof)
                if desc:
                    csv_descriptions.append(desc)
        else:
            data_gaps.append(
                DataGap(
                    missing="csv_paths",
                    impact="缺少 CSV 基础数据，无法完成基础数据画像与字段字典",
                    severity="high",
                )
            )
        plan.mark_done("T2", f"完成 {len(csv_profiles)} 份 CSV 画像")

        # ---- T3: PDF extraction ----
        plan.mark_doing("T3", "解析 PDF 文档，抽取关键证据段落")
        pdf_artifacts: List[Dict[str, Any]] = []
        if pdf_paths:
            for p in pdf_paths:
                item = self._extract_pdf(Path(p), artifacts_dir=artifacts_dir)
                if item:
                    pdf_artifacts.append(item)
        else:
            data_gaps.append(
                DataGap(
                    missing="pdf_paths",
                    impact="缺少 PDF 文档来源，政策/调研/设备资料证据链将不足",
                    severity="medium",
                )
            )
        plan.mark_done("T3", f"完成 {len(pdf_artifacts)} 份 PDF 解析")

        # ---- T4: Excel parsing ----
        plan.mark_doing("T4", "解析 Excel，识别现金流与能流表")
        excel_artifacts: List[Dict[str, Any]] = []
        if excel_paths:
            for p in excel_paths:
                item = self._parse_excel(Path(p), artifacts_dir=artifacts_dir)
                if item:
                    excel_artifacts.append(item)
        else:
            data_gaps.append(
                DataGap(
                    missing="excel_paths",
                    impact="缺少 Excel 表格（可能包含现金流/能流），deepresearch 部分将以占位模板输出",
                    severity="medium",
                )
            )
        plan.mark_done("T4", f"完成 {len(excel_artifacts)} 份 Excel 解析")

        # Overall completeness (simple heuristic)
        have_csv = 1 if csv_profiles else 0
        have_pdf = 1 if pdf_artifacts else 0
        have_excel = 1 if excel_artifacts else 0
        completeness = round((have_csv + have_pdf + have_excel) / 3.0, 2)

        metrics = {
            "scenario_id": scenario_id,
            "file_count_csv": len(csv_paths),
            "file_count_pdf": len(pdf_paths),
            "file_count_excel": len(excel_paths),
            "data_completeness_score": completeness,
            "csv_profiled": len(csv_profiles),
            "pdf_parsed": len(pdf_artifacts),
            "excel_parsed": len(excel_artifacts),
            "back_data_fhd_ok": bool(fhd_data.get("ok")) if isinstance(fhd_data, dict) else False,
            "back_data_lyx_ok": bool(lyx_data.get("ok")) if isinstance(lyx_data, dict) else False,
            "back_data_eco_kg_ok": bool(eco_data.get("ok")) if isinstance(eco_data, dict) else False,
            "fhd_matched_parks": (fhd_data.get("metrics") or {}).get("matched_parks") if isinstance(fhd_data, dict) else None,
        }

        artifacts = {
            "output_dir": str(out_dir),
            "plan_path": str(plan_path),
            "inventory": inventory,
            "csv_profiles": csv_profiles,
            "csv_descriptions": csv_descriptions,
            "pdf_artifacts": pdf_artifacts,
            "excel_artifacts": excel_artifacts,
            "back_data": {
                "fhd": fhd_data,
                "lyx": lyx_data,
                "eco_knowledge_graph": eco_data,
                "tool_calls": [
                    {
                        "tool_call_id": fhd_tool.get("tool_call_id"),
                        "name": fhd_tool.get("name"),
                        "ok": fhd_tool.get("ok"),
                        "elapsed_ms": fhd_tool.get("elapsed_ms"),
                    },
                    {
                        "tool_call_id": lyx_tool.get("tool_call_id"),
                        "name": lyx_tool.get("name"),
                        "ok": lyx_tool.get("ok"),
                        "elapsed_ms": lyx_tool.get("elapsed_ms"),
                    },
                    {
                        "tool_call_id": eco_tool.get("tool_call_id"),
                        "name": eco_tool.get("name"),
                        "ok": eco_tool.get("ok"),
                        "elapsed_ms": eco_tool.get("elapsed_ms"),
                    },
                ],
            },
        }

        assumptions = [
            Assumption(
                name="intake_sampling_policy",
                value="If CSV is too large, profiling may use sampling",
                reason="避免将 agent 变成大规模 ETL；只做描述性统计",
                sensitivity="low",
            )
        ]

        evidence: List[Evidence] = [
            self._build_evidence(
                description="Inventory + profiling artifacts saved under output_dir/artifacts",
                source="local_filesystem",
                uri=str(artifacts_dir),
            )
        ]

        confidence = 0.55 + 0.35 * completeness
        envelope = self._create_envelope(
            state=state,
            metrics=metrics,
            artifacts=artifacts,
            assumptions=assumptions,
            evidence=evidence,
            confidence=min(0.9, confidence),
            data_gaps=data_gaps,
            reproducibility_extra={"output_dir": str(out_dir)},
        )

        review_items = []
        if any(g.severity == "high" for g in data_gaps):
            review_items.append(
                self._review_item(
                    checkpoint_id="intake_missing_data",
                    issue="关键数据缺失，后续报告将包含占位与数据缺口说明",
                    editable_fields=["inputs.csv_paths", "inputs.pdf_paths", "inputs.excel_paths"],
                    suggested_action="补充 CSV/PDF/Excel 路径，或将数据导入数据库后再运行。",
                    severity="high",
                )
            )

        return AgentRunResult(envelope=envelope, review_items=review_items)

    # -------------------- helpers --------------------
    def _build_inventory(self, csv_paths: List[str], pdf_paths: List[str], excel_paths: List[str]) -> Dict[str, Any]:
        files: List[Dict[str, Any]] = []
        missing: List[str] = []

        def add(path_str: str, ftype: str) -> None:
            p = Path(path_str)
            if not p.exists():
                missing.append(path_str)
                return
            try:
                stat = p.stat()
                files.append(
                    {
                        "path": str(p),
                        "type": ftype,
                        "size_bytes": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
                )
            except Exception:
                missing.append(path_str)

        for p in csv_paths:
            add(p, "csv")
        for p in pdf_paths:
            add(p, "pdf")
        for p in excel_paths:
            add(p, "excel")

        return {"files": files, "missing_files": missing}

    def _profile_csv(self, path: Path, artifacts_dir: Path) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        pd = _try_import_pandas()
        if pd is None:
            # Minimal fallback: count lines & header with csv module
            try:
                import csv
                with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader, [])
                    row_count = sum(1 for _ in reader)
                prof = {
                    "file": str(path),
                    "rows": row_count,
                    "cols": len(header),
                    "columns": [{"name": c, "dtype": "unknown"} for c in header],
                    "note": "pandas not available; only header+row_count computed",
                }
            except Exception as e:
                return None, None
        else:
            # Read with a reasonable cap to avoid huge memory usage in MVP
            try:
                df = pd.read_csv(path, nrows=200000, low_memory=False)
            except Exception:
                try:
                    df = pd.read_csv(path, nrows=200000, low_memory=False, encoding="gbk")
                except Exception:
                    return None, None

            prof = self._profile_dataframe(df, file=str(path))

        # Persist profile json
        safe_name = _sanitize_id(path.stem)
        prof_path = artifacts_dir / f"csv_profile_{safe_name}.json"
        prof_path.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")

        # Build an LLM-friendly description (optional)
        prompt = self._csv_description_prompt(prof)
        fallback = self._csv_description_fallback(prof)
        desc_md = self.llm.markdown(
            system_prompt="你是多能源园区数据分析专家，专门从事工业园区能源数据的质量评估和业务价值分析。请将数据画像转化为专业、可审计的中文 Markdown 描述，为后续的碳排放分析和减排规划提供数据基础。",
            user_prompt=prompt,
            fallback=fallback,
        )
        desc = {
            "file": str(path),
            "profile_path": str(prof_path),
            "description_markdown": desc_md,
        }
        (artifacts_dir / f"csv_description_{safe_name}.md").write_text(desc_md, encoding="utf-8")

        return prof, desc

    def _profile_dataframe(self, df, file: str) -> Dict[str, Any]:
        # pandas DataFrame profiling (lightweight)
        pd = df.__class__.__module__.split(".")[0]
        # count
        rows = int(df.shape[0])
        cols = int(df.shape[1])

        columns: List[Dict[str, Any]] = []
        for col in df.columns:
            series = df[col]
            dtype = str(series.dtype)
            non_null = int(series.notna().sum())
            missing_pct = float(1.0 - non_null / max(1, rows))
            col_info: Dict[str, Any] = {
                "name": str(col),
                "dtype": dtype,
                "non_null": non_null,
                "missing_pct": round(missing_pct, 4),
            }
            # numeric stats
            try:
                if "int" in dtype or "float" in dtype:
                    col_info.update(
                        {
                            "min": float(series.min()),
                            "max": float(series.max()),
                            "mean": float(series.mean()),
                        }
                    )
            except Exception:
                pass
            # small-cardinality category preview
            try:
                nunique = int(series.nunique(dropna=True))
                col_info["nunique"] = nunique
                if nunique <= 12:
                    samples = [str(x) for x in series.dropna().unique().tolist()[:12]]
                    col_info["unique_samples"] = samples
            except Exception:
                pass
            columns.append(col_info)

        # crude time-grain detection
        time_cols = [c for c in columns if any(k in c["name"].lower() for k in ["time", "date", "ts", "timestamp"])]
        return {
            "file": file,
            "rows": rows,
            "cols": cols,
            "time_like_columns": [c["name"] for c in time_cols],
            "columns": columns,
        }

    def _csv_description_prompt(self, profile: Dict[str, Any]) -> str:
        # Prompt is part of the deliverable: "如何去描述基础数据"
        return (
            "你将获得一份 CSV 数据画像（JSON）。请输出 Markdown 段落，包含：\n"
            "1) 这份数据可能代表什么业务对象/过程（基于字段名推断，允许不确定并标注假设）；\n"
            "2) 时间维度：是否包含时间字段、可能的时间粒度；\n"
            "3) 关键字段：挑选 5-10 个最重要字段，说明含义、类型、缺失率；\n"
            "4) 数据质量：缺失严重字段、异常范围风险；\n"
            "5) 报告可用性：这份数据可支持哪些报告章节（现状/能流/现金流/措施/政策/风险）。\n"
            "要求：语言简洁、可审计；不要发明具体数值；如果无法判断就明确写“无法从字段判断”。\n"
            "\n"
            f"数据画像JSON：\n{json.dumps(profile, ensure_ascii=False)}"
        )

    def _csv_description_fallback(self, profile: Dict[str, Any]) -> str:
        cols = profile.get("columns") or []
        top_cols = cols[:10]
        bullet = "\n".join(
            [f"- {c.get('name')} ({c.get('dtype')}) 缺失率 {c.get('missing_pct')}" for c in top_cols]
        )
        return (
            f"### CSV 基础描述：{profile.get('file')}\n"
            f"- 行数: {profile.get('rows')}，列数: {profile.get('cols')}\n"
            f"- 可能的时间字段: {', '.join(profile.get('time_like_columns') or []) or '未识别'}\n"
            f"- 字段预览（前10列）\n{bullet}\n"
            f"- 说明：此描述为无LLM的占位稿，后续可用LLM生成更自然的文字。\n"
        )

    def _extract_pdf(self, path: Path, artifacts_dir: Path) -> Optional[Dict[str, Any]]:
        PdfReader = _try_import_pdf_reader()
        if PdfReader is None:
            return {
                "file": str(path),
                "error": "PDF reader not available (install pypdf or PyPDF2)",
                "extracted_path": None,
                "evidence_items": [],
            }

        if not path.exists():
            return None

        try:
            reader = PdfReader(str(path))
        except Exception as e:
            return {
                "file": str(path),
                "error": f"failed to open pdf: {e}",
                "extracted_path": None,
                "evidence_items": [],
            }

        pages_text: List[str] = []
        evidence_items: List[Dict[str, Any]] = []
        keywords = ["负荷", "电", "热", "蒸汽", "天然气", "成本", "投资", "补贴", "政策", "排放", "碳", "设备", "能效"]

        for i, page in enumerate(reader.pages):
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            txt = txt.strip()
            pages_text.append(f"## Page {i+1}\n\n{txt}\n")

            # evidence extraction: pick first lines containing keywords
            if txt:
                lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
                hits = []
                for ln in lines:
                    if any(k in ln for k in keywords):
                        hits.append(ln)
                    if len(hits) >= 3:
                        break
                for hidx, h in enumerate(hits, start=1):
                    eid = f"PDF:{path.stem}:P{i+1}:H{hidx}"
                    evidence_items.append(
                        {
                            "evidence_id": eid,
                            "page": i + 1,
                            "excerpt": h[:240],
                            "note": "keyword-hit",
                        }
                    )

        safe_name = _sanitize_id(path.stem)
        extracted_path = artifacts_dir / f"pdf_extract_{safe_name}.md"
        extracted_path.write_text("\n".join(pages_text), encoding="utf-8")

        # Persist evidence json
        (artifacts_dir / f"pdf_evidence_{safe_name}.json").write_text(
            json.dumps(evidence_items, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {
            "file": str(path),
            "extracted_path": str(extracted_path),
            "evidence_items": evidence_items,
        }

    def _parse_excel(self, path: Path, artifacts_dir: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None

        pd = _try_import_pandas()
        sheets: Dict[str, Any] = {}
        sheet_summaries: List[Dict[str, Any]] = []
        detected_cashflow: List[Dict[str, Any]] = []
        detected_energyflow: List[Dict[str, Any]] = []

        if pd is None:
            # Fallback using openpyxl
            try:
                import openpyxl  # type: ignore

                wb = openpyxl.load_workbook(path, data_only=True)
                for sname in wb.sheetnames:
                    ws = wb[sname]
                    rows = list(ws.values)
                    if not rows:
                        continue
                    header = [str(x) for x in (rows[0] or [])]
                    sheet_summaries.append(
                        {
                            "sheet": sname,
                            "rows": len(rows) - 1,
                            "cols": len(header),
                            "header_preview": header[:20],
                            "note": "openpyxl fallback (no pandas)",
                        }
                    )
            except Exception as e:
                return {"file": str(path), "error": f"failed to parse excel: {e}", "sheets": []}
        else:
            try:
                xls = pd.ExcelFile(path)
                for sname in xls.sheet_names:
                    try:
                        df = xls.parse(sname, nrows=200000)
                    except Exception:
                        continue
                    sheet_summaries.append(
                        {
                            "sheet": sname,
                            "rows": int(df.shape[0]),
                            "cols": int(df.shape[1]),
                            "columns": [str(c) for c in df.columns.tolist()[:30]],
                        }
                    )

                    # Save sheet csv for traceability
                    safe_sheet = _sanitize_id(sname)
                    sheet_csv_path = artifacts_dir / f"excel_{_sanitize_id(path.stem)}_{safe_sheet}.csv"
                    try:
                        df.to_csv(sheet_csv_path, index=False)
                    except Exception:
                        pass

                    # Detect cashflow / energyflow tables by heuristics
                    lower_cols = [str(c).lower() for c in df.columns]
                    if any(k in lower_cols for k in ["cashflow", "capex", "opex", "npv", "payback"]) or any(
                        k in sname.lower() for k in ["cash", "finance", "财务", "现金流"]
                    ):
                        detected_cashflow.append(
                            {
                                "sheet": sname,
                                "path_csv": str(sheet_csv_path),
                                "columns": lower_cols,
                                "preview_rows": df.head(5).to_dict(orient="records"),
                            }
                        )
                    if any(k in lower_cols for k in ["from", "to", "carrier", "fuel", "electric", "steam", "heat"]) or any(
                        k in sname.lower() for k in ["energy", "flow", "能流", "能源流"]
                    ):
                        detected_energyflow.append(
                            {
                                "sheet": sname,
                                "path_csv": str(sheet_csv_path),
                                "columns": lower_cols,
                                "preview_rows": df.head(8).to_dict(orient="records"),
                            }
                        )
            except Exception as e:
                return {"file": str(path), "error": f"failed to parse excel with pandas: {e}", "sheets": []}

        safe_name = _sanitize_id(path.stem)
        excel_meta_path = artifacts_dir / f"excel_summary_{safe_name}.json"
        excel_meta_path.write_text(
            json.dumps(
                {
                    "file": str(path),
                    "sheet_summaries": sheet_summaries,
                    "detected_cashflow": detected_cashflow,
                    "detected_energyflow": detected_energyflow,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return {
            "file": str(path),
            "summary_path": str(excel_meta_path),
            "sheet_summaries": sheet_summaries,
            "detected_cashflow": detected_cashflow,
            "detected_energyflow": detected_energyflow,
        }
