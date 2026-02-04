from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict


ENERGY_DIM_COLS = [
    "高品位热能",
    "中品位热能",
    "低品位热能",
    "高品位冷能",
    "中品位冷能",
    "低品位冷能",
    "电能",
    "天然气",
]

MATCH_COLS_DEFAULT = [
    "细分类（中文）",
    "小类（中文）",
    "中类（中文）",
    "大类（中文）",
]


def _normalize_keyword(k: str) -> str:
    k = (k or "").strip()
    if not k:
        return ""
    # common suffix cleanup
    k = re.sub(r"(产业园|园区|园|工业园|工业园区)$", "", k)
    k = re.sub(r"(工业|产业|制造业|行业|产业链)$", "", k)
    return k.strip() or (k or "").strip()


class LYXMaterializeInput(BaseModel):
    """Stable input schema for the LYX back-data adapter."""

    model_config = ConfigDict(extra="allow")

    output_dir: str = Field(..., description="Scenario output directory (e.g. outputs/<scenario_id>)")

    # Two ways to pass industries
    industry_keywords: List[str] = Field(default_factory=list, description="Industry keywords (Chinese)")
    industry_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional weights per keyword (e.g. from fhd industry distribution).",
    )

    match_columns: List[str] = Field(default_factory=lambda: list(MATCH_COLS_DEFAULT))
    top_k_matches_per_keyword: int = Field(default=50, ge=1, le=500)


class LYXMaterializeResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    ok: bool
    source_id: str = "lyx"
    version: str = "0.1.0"

    metrics: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    inventory_files: List[str] = Field(default_factory=list)
    recommended_inputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None


@lru_cache(maxsize=2)
def _load_score_table(csv_path: str):
    import pandas as pd  # type: ignore

    df = pd.read_csv(csv_path)
    # ensure numeric
    for c in ENERGY_DIM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _discover_score_file(data_dir: Path) -> Optional[Path]:
    # file name might be encoded in zip; just pick the first CSV
    return next(iter(sorted(data_dir.glob("*.csv"))), None)


def _match_rows(df, keyword: str, match_cols: List[str], top_k: int):
    kw = _normalize_keyword(keyword)
    if not kw:
        return df.iloc[0:0]

    mask = None
    for col in match_cols:
        if col not in df.columns:
            continue
        m = df[col].astype(str).str.contains(kw, na=False)
        mask = m if mask is None else (mask | m)

    if mask is None:
        return df.iloc[0:0]

    matched = df[mask]
    if len(matched) > top_k:
        matched = matched.iloc[:top_k]
    return matched


def _aggregate_scores(df_rows) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    if df_rows is None or len(df_rows) == 0:
        return {c: float("nan") for c in ENERGY_DIM_COLS}

    for c in ENERGY_DIM_COLS:
        try:
            v = float(df_rows[c].mean())
        except Exception:
            v = float("nan")
        scores[c] = round(v, 3) if v == v else float("nan")
    return scores


def _scores_to_mix(scores: Dict[str, float]) -> Dict[str, float]:
    # turn 1-5 scores into weights
    weights = {}
    total = 0.0
    for k, v in scores.items():
        if v != v:  # nan
            w = 0.0
        else:
            w = max(0.0, float(v))
        weights[k] = w
        total += w
    if total <= 0:
        return {k: 0.0 for k in scores.keys()}
    return {k: round(v / total, 4) for k, v in weights.items()}


def _priority_rules(scores: Dict[str, float]) -> Dict[str, Any]:
    # rule-based, deterministic
    def s(k: str) -> float:
        v = scores.get(k)
        return float(v) if v == v else 0.0

    heat = max(s("高品位热能"), s("中品位热能"), s("低品位热能"))
    cold = max(s("高品位冷能"), s("中品位冷能"), s("低品位冷能"))
    elec = s("电能")
    gas = s("天然气")

    suggestions: List[str] = []
    priorities: List[Dict[str, Any]] = []

    # Electricity-driven
    if elec >= 3.5:
        priorities.append({"theme": "电力侧", "why": "电能需求评分较高", "measures": ["屋顶光伏/分布式新能源", "储能削峰填谷", "高效电机/变频改造", "能管平台EMS"]})
        suggestions.append("电力侧负荷较高，优先考虑‘源-网-荷-储’协同：分布式光伏 + 储能 + 负荷侧能效。")

    # Heat
    if heat >= 3.5:
        priorities.append({"theme": "热力侧", "why": "热能需求评分较高", "measures": ["余热回收与梯级利用", "热泵（中低温）", "高温工艺优化/燃烧改造", "蒸汽管网保温与凝结水回收"]})
        suggestions.append("热需求显著：建议做余热盘点与梯级利用，能用热泵的尽量电气化替代，减少燃气/燃煤边际排放。")

    # Cold
    if cold >= 3.5:
        priorities.append({"theme": "冷量侧", "why": "冷能需求评分较高", "measures": ["集中冷站优化", "冷却塔与冷冻水系统优化", "蓄冷（与TOU联动）", "工艺冷却余冷回收"]})
        suggestions.append("冷需求较高：集中冷站/冷却水系统的COP提升与分时策略往往是低成本高收益选项。")

    # Gas
    if gas >= 3.5:
        priorities.append({"theme": "燃气侧", "why": "天然气需求评分较高", "measures": ["燃气锅炉/窑炉能效提升", "燃气-蒸汽系统优化", "CHP/三联供可行性评估（需边界条件）"]})
        suggestions.append("天然气需求较高：可优先评估燃气端能效提升与系统改造，必要时再评估CHP/三联供（需负荷与价格边界）。")

    if not priorities:
        priorities.append({"theme": "通用能效", "why": "未识别显著高分项", "measures": ["分项计量与能管平台", "设备能效普查", "用能结构与负荷曲线补数"]})
        suggestions.append("当前行业画像无法识别显著偏好，建议先补充分项计量与负荷曲线，再做针对性措施筛选。")

    return {
        "priorities": priorities,
        "suggestions": suggestions,
    }


def materialize(payload: LYXMaterializeInput) -> Dict[str, Any]:
    """Entry point used by multi_energy_agent.

    MUST NOT raise.
    """
    print("[LYX] Starting materialize...")

    out_dir = Path(payload.output_dir)
    artifacts_dir = out_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    data_dir = Path(__file__).resolve().parent
    csv_path = _discover_score_file(data_dir)
    if not csv_path:
        print("[LYX] Error: score csv not found")
        return LYXMaterializeResult(
            ok=False,
            inventory_files=[],
            error={"type": "missing_file", "message": "LYX score csv not found under other_back_data/lyx"},
        ).model_dump()

    inv = [str(csv_path)]

    try:
        print(f"[LYX] Loading score table: {csv_path}")
        df = _load_score_table(str(csv_path))
        print(f"[LYX] Score table loaded, {len(df)} rows")

        # Build keyword list (prefer weighted keys)
        keywords = list(payload.industry_weights.keys()) if payload.industry_weights else list(payload.industry_keywords)
        keywords = [k for k in keywords if str(k).strip()]

        per_kw: List[Dict[str, Any]] = []
        weighted_scores_sum = {c: 0.0 for c in ENERGY_DIM_COLS}
        weight_total = 0.0

        for kw in keywords:
            rows = _match_rows(df, kw, payload.match_columns, payload.top_k_matches_per_keyword)
            scores = _aggregate_scores(rows)
            weight = float(payload.industry_weights.get(kw, 1.0)) if payload.industry_weights else 1.0
            if weight < 0:
                weight = 0.0
            if rows is not None and len(rows) > 0:
                weight_total += weight
                for c in ENERGY_DIM_COLS:
                    v = scores.get(c)
                    if v == v:  # not nan
                        weighted_scores_sum[c] += float(v) * weight

            per_kw.append(
                {
                    "keyword": kw,
                    "normalized_keyword": _normalize_keyword(kw),
                    "matched_rows": int(len(rows)) if rows is not None else 0,
                    "scores_mean": scores,
                    "weight": weight,
                    "matched_examples": (
                        rows[["大类（中文）", "中类（中文）", "小类（中文）", "细分类（中文）"]].head(3).to_dict("records")
                        if rows is not None and len(rows) > 0
                        else []
                    ),
                }
            )

        if weight_total <= 0:
            # fallback: global average
            global_scores = _aggregate_scores(df)
            final_scores = global_scores
            used = "global_average"
        else:
            final_scores = {c: round(weighted_scores_sum[c] / weight_total, 3) for c in ENERGY_DIM_COLS}
            used = "weighted_keyword_average"

        mix = _scores_to_mix(final_scores)
        top_dims = sorted(final_scores.items(), key=lambda kv: (-(kv[1] if kv[1] == kv[1] else -1)))[:5]
        rule_out = _priority_rules(final_scores)

        result_payload = {
            "method": used,
            "final_scores_mean": final_scores,
            "energy_mix": mix,
            "top_dimensions": top_dims,
            "per_keyword": per_kw,
            **rule_out,
        }

        out_json = artifacts_dir / "lyx_energy_tendency.json"
        out_json.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[LYX] Completed: {len(keywords)} keywords processed")

        return LYXMaterializeResult(
            ok=True,
            metrics={
                "keywords": keywords,
                "method": used,
                "weight_total": round(weight_total, 4),
                "top_dimensions": top_dims,
            },
            artifacts={
                "score_csv_path": str(csv_path),
                "tendency_json": str(out_json),
                "tendency": result_payload,
            },
            inventory_files=inv,
            recommended_inputs={"json_paths": [str(out_json)]},
        ).model_dump()

    except Exception as e:
        print(f"[LYX] Error: {e}")
        return LYXMaterializeResult(
            ok=False,
            inventory_files=inv,
            error={"type": "exception", "message": str(e)},
        ).model_dump()
