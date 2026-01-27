"""InsightSynthesisAgent

This stage turns *ingested artifacts* into **descriptive, auditable insights**
(no heavy optimization / no black-box math).

Key integrations (project requirement):
- fhd：园区名录 + 空间 AOI -> 园区画像底座
- lyx：行业多能需求倾向 -> 多能侧推断（冷热电气比例、措施优先级）
- eco_knowledge_graph -> 证据链/合规引用（条文片段插入报告）

Outputs:
- envelope stage=insight
- updates plan.md (T5-T8)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import AgentRunResult, BaseAgent
from ..llm import StructuredLLMClient
from ..planning import PlanManager
from ..schemas import Assumption, DataGap, Evidence, Stage
from ..utils.logging import get_run_context


def _sanitize_id(value: str) -> str:
    value = (value or "").strip() or "default"
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
    return value[:80] or "default"


# A minimal measure library. (No optimization; just screening + explanation)
MEASURE_LIBRARY: List[Dict[str, Any]] = [
    {
        "id": "PV_ROOF",
        "name": "屋顶光伏/分布式新能源",
        "themes": ["电力侧"],
        "required_inputs": ["roof_area_m2", "solar_profile", "grid_connection_limit"],
    },
    {
        "id": "BESS_TOU",
        "name": "储能削峰填谷（TOU联动）",
        "themes": ["电力侧"],
        "required_inputs": ["tou_tariff", "load_profile", "battery_capex"],
    },
    {
        "id": "EE_EMS",
        "name": "分项计量 + 能源管理系统（EMS）",
        "themes": ["通用能效", "电力侧", "热力侧", "冷量侧"],
        "required_inputs": ["metering_points", "submeter_data"],
    },
    {
        "id": "WASTE_HEAT_HP",
        "name": "余热回收 + 热泵（梯级利用）",
        "themes": ["热力侧"],
        "required_inputs": ["waste_heat_profile", "steam_grade", "heat_sink_temperature"],
    },
    {
        "id": "STEAM_RECYCLE",
        "name": "蒸汽系统与凝结水回收（保温/疏水/回收）",
        "themes": ["热力侧"],
        "required_inputs": ["steam_network_map", "condensate_ratio", "boiler_efficiency"],
    },
    {
        "id": "COOLING_OPT",
        "name": "集中冷站/冷却水系统优化（COP提升）",
        "themes": ["冷量侧"],
        "required_inputs": ["chiller_cop", "cooling_load_profile", "water_system_diagram"],
    },
    {
        "id": "GAS_EFF",
        "name": "燃气锅炉/窑炉能效提升（燃烧/余热/控制）",
        "themes": ["燃气侧", "热力侧"],
        "required_inputs": ["gas_consumption", "boiler_inventory", "flue_gas_temp"],
    },
]


class InsightSynthesisAgent(BaseAgent):
    def __init__(self, llm: Optional[StructuredLLMClient] = None) -> None:
        super().__init__(stage=Stage.INSIGHT, name="insight_synthesis", llm=llm or StructuredLLMClient())

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        scenario = state.get("scenario") or {}
        selection = state.get("selection") or {}
        metadata = selection.get("metadata") or {}

        scenario_id = _sanitize_id(str(scenario.get("scenario_id") or "default-scenario"))
        out_dir = Path(state.get("output_dir") or Path("outputs") / scenario_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        plan = PlanManager(out_dir / "plan.md")

        run_ctx = get_run_context(state)
        logger = run_ctx.logger if run_ctx else None

        # intake artifacts
        intake_artifacts = self._get_envelope_artifacts(state, Stage.INTAKE, default={})
        back_data = (intake_artifacts.get("back_data") or {})
        fhd = back_data.get("fhd") or {}
        lyx = back_data.get("lyx") or {}
        eco = back_data.get("eco_knowledge_graph") or {}

        data_gaps: List[DataGap] = []

        # ---------------- T5: park profile ----------------
        plan.mark_doing("T5", "生成园区画像底座（fhd：名录+AOI）")
        park_profile, park_gaps = self._build_park_profile(fhd=fhd, metadata=metadata)
        data_gaps.extend(park_gaps)
        plan.mark_done(
            "T5",
            f"matched_parks={park_profile.get('matched_parks','?')} top_industries={len(park_profile.get('top_industries') or [])}",
        )

        # DeepResearch tasks are out of scope for this lightweight offline version.
        plan.mark_done("T6", "占位：未提供能流/转换/去向数据，跳过 deepresearch 能流分析")
        plan.mark_done("T7", "占位：未提供现金流表格，跳过 deepresearch 现金流分析")

        # ---------------- LYX energy tendency ----------------
        plan.mark_doing("T8", "行业多能需求倾向推断（lyx：冷热电气比例->措施优先级）")
        energy_tendency, tendency_gaps = self._build_energy_tendency(lyx=lyx)
        data_gaps.extend(tendency_gaps)
        plan.mark_done("T8", f"energy_mix_keys={len((energy_tendency.get('energy_mix') or {}).keys())}")

        # ---------------- Measure screening (rule-based) ----------------
        plan.append_log("Screen measures based on energy_tendency priorities")
        measures = self._screen_measures(energy_tendency=energy_tendency, metadata=metadata)

        # ---------------- eco_knowledge_graph evidence ----------------
        plan.append_log("Query eco_knowledge_graph for compliance/evidence snippets")
        evidence_blocks, evidence_items, eco_gaps = self._build_eco_evidence(
            state=state,
            metadata=metadata,
            measures=measures,
            eco_materialize_result=eco,
        )
        data_gaps.extend(eco_gaps)

        # ---------- metrics / artifacts ----------
        metrics = {
            "park_profile": park_profile,
            "energy_tendency": {
                "top_dimensions": energy_tendency.get("top_dimensions"),
                "method": energy_tendency.get("method"),
            },
            "top_measures": measures,
            "eco_kg": {
                "query_count": len(evidence_blocks),
                "hit_count": sum(len(b.get("snippets") or []) for b in evidence_blocks),
            },
        }

        artifacts = {
            "park_profile": park_profile,
            "energy_tendency": energy_tendency,
            "measures": measures,
            "eco_kg_evidence": evidence_blocks,
        }

        assumptions = [
            Assumption(
                name="insight_boundary",
                value="No optimization; deterministic screening + evidence retrieval",
                reason="导师要求：agent 不承担复杂数学求解；输出必须可审计",
                sensitivity="low",
            )
        ]

        evidence: List[Evidence] = []
        evidence.extend(evidence_items)

        confidence = 0.55
        if park_profile.get("matched_parks"):
            confidence += 0.10
        if (energy_tendency.get("energy_mix") or {}).get("电能") is not None:
            confidence += 0.10
        if metrics["eco_kg"]["hit_count"] > 0:
            confidence += 0.10
        confidence -= 0.05 * len([g for g in data_gaps if g.severity == "high"])
        confidence = max(0.15, min(0.90, confidence))

        if logger:
            logger.info("Insight: confidence=%.2f gaps=%s", confidence, len(data_gaps))

        envelope = self._create_envelope(
            state=state,
            metrics=metrics,
            artifacts=artifacts,
            assumptions=assumptions,
            evidence=evidence,
            confidence=confidence,
            data_gaps=data_gaps,
            reproducibility_extra={
                "fhd_ok": bool(fhd.get("ok")),
                "lyx_ok": bool(lyx.get("ok")),
                "eco_kg_ok": bool(eco.get("ok")),
            },
        )

        review_items = []
        if any(g.severity == "high" for g in data_gaps):
            review_items.append(
                self._review_item(
                    checkpoint_id="insight_high_gaps",
                    issue="Insight 阶段存在关键缺口，建议补充园区地区/产业/负荷信息以提升可用性。",
                    editable_fields=["selection.metadata.city", "selection.metadata.province", "selection.metadata.industry_keywords"],
                    suggested_action="至少提供 city/province/industry_keywords 中的一项，以便匹配园区名录与行业画像。",
                    severity="high",
                )
            )

        return AgentRunResult(envelope=envelope, review_items=review_items)

    # ---------------- internals ----------------
    def _build_park_profile(self, *, fhd: Dict[str, Any], metadata: Dict[str, Any]) -> tuple[Dict[str, Any], List[DataGap]]:
        gaps: List[DataGap] = []
        if not fhd or not fhd.get("ok"):
            gaps.append(
                DataGap(
                    missing="fhd",
                    impact="园区名录/AOI 未载入，无法形成园区画像底座（园区数量/产业结构/空间覆盖）",
                    severity="high",
                )
            )
            return {"ok": False}, gaps

        m = fhd.get("metrics") or {}
        aoi = ((fhd.get("artifacts") or {}).get("aoi_summary") or {})

        # produce concise, frontend-friendly profile
        profile = {
            "ok": True,
            "filters": fhd.get("artifacts", {}).get("filters") if isinstance(fhd.get("artifacts"), dict) else None,
            "total_parks": m.get("total_parks"),
            "matched_parks": m.get("matched_parks"),
            "top_industries": m.get("matched_industry_distribution_top") or m.get("industry_distribution_top") or [],
            "top_levels": m.get("matched_level_distribution_top") or m.get("level_distribution_top") or [],
            "top_cities": m.get("matched_city_distribution_top") or m.get("city_distribution_top") or [],
            "aoi": {
                "total_features": aoi.get("total_features") if isinstance(aoi, dict) else None,
                "bounds": aoi.get("bounds") if isinstance(aoi, dict) else None,
                "matched_features": (aoi.get("matched") or {}).get("matched_features") if isinstance(aoi, dict) else None,
                "matched_bounds": (aoi.get("matched") or {}).get("bounds") if isinstance(aoi, dict) else None,
                "matched_area_km2": (aoi.get("matched") or {}).get("area_km2") if isinstance(aoi, dict) else None,
            },
        }

        # if user didn't provide city/province filters, remind
        if not (metadata.get("city") or metadata.get("province") or metadata.get("park_name")):
            gaps.append(
                DataGap(
                    missing="selection.metadata.city/province/park_name",
                    impact="未提供地区/园区筛选条件，园区画像可能为全国汇总而非目标园区",
                    severity="medium",
                )
            )

        return profile, gaps

    def _build_energy_tendency(self, *, lyx: Dict[str, Any]) -> tuple[Dict[str, Any], List[DataGap]]:
        gaps: List[DataGap] = []
        if not lyx or not lyx.get("ok"):
            gaps.append(
                DataGap(
                    missing="lyx",
                    impact="行业多能倾向未生成，无法推断冷热电气比例与措施优先级",
                    severity="high",
                )
            )
            return {"ok": False}, gaps

        tendency = (lyx.get("artifacts") or {}).get("tendency") or {}
        if not tendency:
            gaps.append(
                DataGap(
                    missing="lyx.artifacts.tendency",
                    impact="LYX 结果缺少 tendency 字段，无法用于后续筛选",
                    severity="medium",
                )
            )

        # ensure minimal keys
        out = {
            "ok": True,
            "method": tendency.get("method"),
            "final_scores_mean": tendency.get("final_scores_mean"),
            "energy_mix": tendency.get("energy_mix"),
            "top_dimensions": tendency.get("top_dimensions"),
            "priorities": tendency.get("priorities"),
            "suggestions": tendency.get("suggestions"),
        }
        return out, gaps

    def _screen_measures(self, *, energy_tendency: Dict[str, Any], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        priorities = energy_tendency.get("priorities") or []
        priority_themes = [p.get("theme") for p in priorities if p.get("theme")]

        area_km2 = metadata.get("area_km2") or metadata.get("area")
        try:
            area_km2 = float(area_km2) if area_km2 is not None else None
        except Exception:
            area_km2 = None

        entity_count = metadata.get("entity_count") or metadata.get("enterprise_count")
        try:
            entity_count = int(entity_count) if entity_count is not None else None
        except Exception:
            entity_count = None

        measures: List[Dict[str, Any]] = []

        for m in MEASURE_LIBRARY:
            score = 0.5
            # theme match bonus
            if any(t in (m.get("themes") or []) for t in priority_themes):
                score += 0.25
            # scale hints
            if area_km2 is not None and area_km2 >= 5 and "屋顶光伏" in m.get("name", ""):
                score += 0.10
            if entity_count is not None and entity_count >= 50 and "能源管理系统" in m.get("name", ""):
                score += 0.10

            score = max(0.0, min(1.0, round(score, 3)))

            measures.append(
                {
                    "id": m["id"],
                    "name": m["name"],
                    "applicability_score": score,
                    "themes": m.get("themes") or [],
                    "missing_inputs": m.get("required_inputs") or [],
                    "explain": "基于行业多能倾向（lyx）与园区规模信息的规则筛选，未做优化求解。",
                }
            )

        # sort by score desc
        measures.sort(key=lambda x: x.get("applicability_score", 0), reverse=True)
        return measures[:8]

    def _build_eco_evidence(
        self,
        *,
        state: Dict[str, Any],
        metadata: Dict[str, Any],
        measures: List[Dict[str, Any]],
        eco_materialize_result: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], List[Evidence], List[DataGap]]:
        gaps: List[DataGap] = []

        tools = state.get("tools")
        if tools is None:
            gaps.append(
                DataGap(
                    missing="tools",
                    impact="工具注册表缺失，无法查询 eco_knowledge_graph 证据",
                    severity="medium",
                )
            )
            return [], [], gaps

        out_dir = Path(state.get("output_dir") or "outputs")
        evidence_blocks: List[Dict[str, Any]] = []
        evidence_items: List[Evidence] = []

        # If eco materialize failed, we can not query.
        if not eco_materialize_result or not eco_materialize_result.get("ok"):
            gaps.append(
                DataGap(
                    missing="eco_knowledge_graph",
                    impact="eco_knowledge_graph 索引不可用，报告将缺少可引用的政策/指南证据链",
                    severity="medium",
                )
            )
            return [], [], gaps

        # Queries: accounting boundary + local management (if city hints)
        city = str(metadata.get("city") or metadata.get("city_name") or "").strip()
        queries: List[str] = [
            "Scope 1 Scope 2 Scope 3",
            "组织边界 运营控制 财务控制",
            "排放因子 活动数据 数据质量",
        ]
        if "柳" in city or "柳州" in city:
            queries.append("入园 管理 办法 节能 环保 能耗")
        else:
            queries.append("入园 管理 办法 产业园")

        # Also add 1-2 measure-themed queries (won't always hit, but harmless)
        top_measures = measures[:2]
        for m in top_measures:
            name = m.get("name") or ""
            if "光伏" in name:
                queries.append("分布式 光伏 工业园区")
            if "储能" in name:
                queries.append("储能 削峰填谷 电价")
            if "余热" in name or "热泵" in name:
                queries.append("余热 回收 热泵 工业")

        # de-dup
        seen = set()
        uniq_queries = []
        for q in queries:
            q = q.strip()
            if not q or q in seen:
                continue
            seen.add(q)
            uniq_queries.append(q)

        for q in uniq_queries:
            resp = tools.call(
                "query_eco_knowledge_graph",
                {
                    "output_dir": str(out_dir),
                    "query": q,
                    "top_k": 5,
                },
            )
            data = resp.get("data") or {}
            snippets = (data.get("artifacts") or {}).get("snippets") or []

            evidence_blocks.append({"query": q, "snippets": snippets, "tool_call_id": resp.get("tool_call_id")})

            for idx, sn in enumerate(snippets, start=1):
                evidence_items.append(
                    Evidence(
                        evidence_id=f"eco_kg_{len(evidence_items)+1}",
                        description=f"eco_knowledge_graph snippet for query='{q}'",
                        source=str(sn.get("source") or "eco_knowledge_graph"),
                        uri=str((data.get("artifacts") or {}).get("corpus_path") or ""),
                        page=sn.get("page"),
                        excerpt=sn.get("text"),
                    )
                )

        if not any((b.get("snippets") or []) for b in evidence_blocks):
            gaps.append(
                DataGap(
                    missing="eco_knowledge_graph_hits",
                    impact="未检索到可用条文片段，报告中的政策引用将偏弱（可尝试更贴近文档的关键词）。",
                    severity="low",
                )
            )

        return evidence_blocks, evidence_items, gaps
