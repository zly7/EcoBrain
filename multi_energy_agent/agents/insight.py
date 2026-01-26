"""InsightSynthesisAgent

Responsibilities:
- Based on KG + intake artifacts, generate *descriptive* insights:
  - Park baseline description (no heavy optimization)
  - Measures opportunity list (screening + data gaps)
  - Policy KG matching (deterministic)
  - Finance roll-up (prefer reading Excel/precomputed results; fallback to simple roll-up)
  - DeepResearch narratives: energy-flow & cash-flow interpretation

Inputs:
- intake envelope artifacts from Stage.INTAKE
- selection metadata (admin_codes / industry_codes / area_km2 / entity_count, etc.)
- scenario params (prices, factors, discount rate, etc.)

Output:
- envelope stage=insight
- updates plan.md (T5-T8)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import AgentRunResult, BaseAgent
from ..llm import StructuredLLMClient
from ..planning import PlanManager
from ..policy_kg import PolicyKnowledgeGraph, compute_incentives_by_measure
from ..schemas import Assumption, DataGap, Evidence, Stage


MEASURE_LIBRARY = [
    {
        "id": "PV_ROOF",
        "name": "屋顶光伏",
        "target_scope": "scope2",
        "base_score": 0.72,
        "reduction_ratio": 0.18,
        "required_inputs": ["roof_area_m2", "solar_profile"],
    },
    {
        "id": "WASTE_HEAT",
        "name": "余热回收+热泵",
        "target_scope": "scope1",
        "base_score": 0.65,
        "reduction_ratio": 0.12,
        "required_inputs": ["waste_heat_profile", "steam_grade"],
    },
    {
        "id": "BESS_TOU",
        "name": "储能削峰填谷",
        "target_scope": "scope2",
        "base_score": 0.58,
        "reduction_ratio": 0.07,
        "required_inputs": ["tou_tariff", "load_profile"],
    },
    {
        "id": "EE_MOTOR",
        "name": "高效电机与变频改造",
        "target_scope": "scope2",
        "base_score": 0.61,
        "reduction_ratio": 0.09,
        "required_inputs": ["motor_inventory", "operating_hours"],
    },
]


def _sanitize_id(value: str) -> str:
    value = value.strip() or "default"
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value)
    return value[:80] or "default"


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
        plan_path = out_dir / "plan.md"
        plan = PlanManager(plan_path)

        intake_metrics = self._get_envelope_metrics(state, Stage.INTAKE)
        intake_artifacts = self._get_envelope_artifacts(state, Stage.INTAKE, default={})

        data_gaps: List[DataGap] = []

        # -------- T5: baseline descriptive (KG-ready) --------
        plan.mark_doing("T5", "生成园区现状画像（描述性，不做优化求解）")
        baseline_metrics, baseline_assumptions, baseline_gaps = self._estimate_baseline(
            selection_metadata=metadata,
            scenario=scenario,
            intake_artifacts=intake_artifacts,
        )
        data_gaps.extend(baseline_gaps)
        plan.mark_done("T5", f"基线总排放(估算) {baseline_metrics.get('total_emissions_tco2','?')} tCO2")

        # -------- T8: measure screening --------
        plan.mark_doing("T8", "筛选措施机会清单，并标注缺失输入")
        measures, measures_gaps = self._screen_measures(
            baseline_metrics=baseline_metrics,
            selection_metadata=metadata,
            scenario=scenario,
        )
        data_gaps.extend(measures_gaps)
        plan.mark_done("T8", f"Top 措施数量 {len(measures)}")

        # -------- Policy KG matching (part of T5/T8 narrative) --------
        admin_codes = metadata.get("admin_codes") or []
        if isinstance(admin_codes, str):
            admin_codes = [admin_codes]
        if not admin_codes and metadata.get("admin_code"):
            admin_codes = [metadata.get("admin_code")]

        industry_codes = (
            metadata.get("industry_codes")
            or metadata.get("industry_list")
            or metadata.get("industries")
            or []
        )
        if isinstance(industry_codes, str):
            industry_codes = [industry_codes]

        if not admin_codes:
            data_gaps.append(
                DataGap(
                    missing="admin_codes",
                    impact="政策匹配可能不准确（缺少地区标识）；建议补充行政区划代码。",
                    severity="high",
                )
            )
        if not industry_codes:
            data_gaps.append(
                DataGap(
                    missing="industry_codes",
                    impact="行业特定政策条款无法过滤，匹配结果可能过宽。",
                    severity="medium",
                )
            )

        plan.append_log("Policy KG matching start")
        policy_metrics, policy_artifacts, policy_evidence, policy_gaps = self._match_policy_kg(
            scenario=scenario,
            admin_codes=admin_codes,
            industry_codes=industry_codes,
            measures=measures,
        )
        data_gaps.extend(policy_gaps)
        plan.append_log("Policy KG matching done")

        # -------- T6: energy flow deepresearch --------
        plan.mark_doing("T6", "解释能流：来源-转换-去向-损失（若缺表则写缺口）")
        energy_flow_summary, energy_flow_gaps = self._energy_flow_deepresearch(intake_artifacts=intake_artifacts)
        data_gaps.extend(energy_flow_gaps)
        plan.mark_done("T6", "能流章节完成（解释性输出）")

        # -------- T7: cash flow deepresearch --------
        plan.mark_doing("T7", "解释现金流：CAPEX/OPEX/补贴/收益（优先读Excel）")
        cash_flow_summary, cash_flow_table, cash_flow_gaps = self._cash_flow_deepresearch(
            intake_artifacts=intake_artifacts
        )
        data_gaps.extend(cash_flow_gaps)
        plan.mark_done("T7", "现金流章节完成（解释性输出）")

        # -------- Finance roll-up (fallback if no cashflow table) --------
        finance_metrics, finance_artifacts, finance_gaps = self._finance_rollup(
            scenario=scenario,
            measures=measures,
            incentives_by_measure=policy_artifacts.get("incentives_by_measure") or {},
            cash_flow_table=cash_flow_table,
        )
        data_gaps.extend(finance_gaps)

        # Evidence: propagate pdf evidence ids for report citations
        pdf_evidence = self._collect_pdf_evidence(intake_artifacts=intake_artifacts)
        evidence: List[Evidence] = list(policy_evidence)
        if pdf_evidence:
            evidence.append(
                self._build_evidence(
                    description=f"PDF evidence items prepared: {len(pdf_evidence)}",
                    source="intake.pdf_evidence",
                    uri=str(out_dir / "artifacts"),
                )
            )

        metrics = {
            "baseline": baseline_metrics,
            "top_measures": measures,
            "policy": policy_metrics,
            "finance": finance_metrics,
            "deepresearch_energy_flow": energy_flow_summary,
            "deepresearch_cash_flow": cash_flow_summary,
        }
        artifacts = {
            "baseline": baseline_metrics,
            "baseline_assumptions": [a.as_dict() for a in baseline_assumptions],
            "measures": measures,
            "policy_artifacts": policy_artifacts,
            "finance_artifacts": finance_artifacts,
            "pdf_evidence_items": pdf_evidence,
            "cashflow_table": cash_flow_table,
            "energy_flow_summary": energy_flow_summary,
        }

        confidence = 0.55
        if measures:
            confidence += 0.10
        if policy_metrics.get("matched_clause_count", 0) > 0:
            confidence += 0.10
        if intake_metrics.get("data_completeness_score", 0) >= 0.66:
            confidence += 0.10
        confidence -= 0.05 * len([g for g in data_gaps if g.severity == "high"])
        confidence = max(0.15, min(0.90, confidence))

        assumptions = baseline_assumptions + [
            Assumption(
                name="insight_boundary",
                value="No optimization; interpret existing data/KG and precomputed tables only",
                reason="导师要求：agent 不承担复杂数学求解",
                sensitivity="low",
            )
        ]

        envelope = self._create_envelope(
            state=state,
            metrics=metrics,
            artifacts=artifacts,
            assumptions=assumptions,
            evidence=evidence,
            confidence=confidence,
            data_gaps=data_gaps,
            reproducibility_extra={"policy_kg_used": bool(policy_metrics.get("kg_path"))},
        )

        review_items = []
        if confidence < 0.6 or any(g.severity == "high" for g in data_gaps):
            review_items.append(
                self._review_item(
                    checkpoint_id="insight_review",
                    issue="Insight 阶段存在关键缺口或置信度较低，需要人工确认。",
                    editable_fields=[
                        "selection.metadata.admin_codes",
                        "selection.metadata.industry_codes",
                        "inputs.csv_paths",
                        "inputs.excel_paths",
                        "scenario",
                    ],
                    suggested_action="补充 admin_codes/industry_codes 与能流/现金流表，或提供外部优化结果文件。",
                    severity="high" if any(g.severity == "high" for g in data_gaps) else "medium",
                )
            )

        return AgentRunResult(envelope=envelope, review_items=review_items)

    # -------------------- baseline --------------------
    def _estimate_baseline(
        self,
        selection_metadata: Dict[str, Any],
        scenario: Dict[str, Any],
        intake_artifacts: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Assumption], List[DataGap]]:
        data_gaps: List[DataGap] = []
        area = float(selection_metadata.get("area_km2") or 10.0)
        entity_count = int(selection_metadata.get("entity_count") or selection_metadata.get("entity_count_est") or 12)

        # If CSV provided a better hint (optional)
        # For MVP, keep deterministic.
        electricity_mwh = round(entity_count * 4.8 + area * 1.2, 2)
        thermal_mwh = round(entity_count * 3.1, 2)

        grid_ef = float(scenario.get("grid_emission_factor_tco2_per_mwh") or 0.58)
        s1_factor = float(scenario.get("thermal_scope1_factor_tco2_per_mwh") or 0.21)

        s1_emissions = round(thermal_mwh * s1_factor, 2)
        s2_emissions = round(electricity_mwh * grid_ef, 2)
        total = round(s1_emissions + s2_emissions, 2)

        # data gaps (descriptive)
        completeness = (intake_artifacts.get("inventory") or {}).get("files")
        if not completeness:
            data_gaps.append(
                DataGap(
                    missing="metering_or_inventory_files",
                    impact="缺少可追溯的能耗计量或文件清单，基线仅能使用代理估算。",
                    severity="high",
                )
            )

        assumptions = [
            Assumption(
                name="baseline_electricity_proxy",
                value="entity_count * 4.8 + area_km2 * 1.2",
                unit="MWh",
                reason="MVP 代理估算，等真实计量数据接入后替换。",
                sensitivity="high",
            ),
            Assumption(
                name="baseline_thermal_proxy",
                value="entity_count * 3.1",
                unit="MWh",
                reason="MVP 代理估算，等锅炉/蒸汽/天然气计量接入后替换。",
                sensitivity="high",
            ),
            Assumption(
                name="grid_emission_factor",
                value=grid_ef,
                unit="tCO2/MWh",
                reason="来自 scenario 或默认排放因子库（需后续校验地区口径）。",
                sensitivity="high",
            ),
            Assumption(
                name="thermal_scope1_factor",
                value=s1_factor,
                unit="tCO2/MWh",
                reason="平均化排放因子（示例）；后续应替换为燃料类型与效率相关因子。",
                sensitivity="medium",
            ),
        ]

        metrics = {
            "baseline_year": scenario.get("baseline_year", 2023),
            "area_km2": round(area, 3),
            "entity_count_est": entity_count,
            "electricity_mwh": electricity_mwh,
            "thermal_mwh": thermal_mwh,
            "scope1_emissions_tco2": s1_emissions,
            "scope2_emissions_tco2": s2_emissions,
            "total_emissions_tco2": total,
            "boundary_note": "Scope1=燃料热用能(代理)；Scope2=外购电(代理)",
        }
        return metrics, assumptions, data_gaps

    # -------------------- measures --------------------
    def _screen_measures(
        self,
        baseline_metrics: Dict[str, Any],
        selection_metadata: Dict[str, Any],
        scenario: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[DataGap]]:
        total_emissions = float(baseline_metrics.get("total_emissions_tco2") or 1000.0)
        electricity_price = float(scenario.get("electricity_price") or 0.72)
        carbon_price = float(scenario.get("carbon_price") or 45.0)

        available_fields = set(selection_metadata.keys()) | set(scenario.keys())

        measures_payload: List[Dict[str, Any]] = []
        gaps: List[DataGap] = []

        for measure in MEASURE_LIBRARY:
            missing_inputs = sorted(set(measure["required_inputs"]) - available_fields)
            missing_penalty = 0.1 * len(missing_inputs)
            score = max(0.35, measure["base_score"] - missing_penalty)
            if measure["target_scope"] == "scope2" and electricity_price > 0.7:
                score += 0.05
            if measure["target_scope"] == "scope1" and carbon_price > 60:
                score += 0.03
            score = min(0.95, score)

            reduction = round(total_emissions * float(measure["reduction_ratio"]), 2)
            capex_million = round(reduction * 0.015, 2)
            annual_savings = round(reduction * (electricity_price * 0.1 + carbon_price * 0.02), 2)

            measures_payload.append(
                {
                    "id": measure["id"],
                    "name": measure["name"],
                    "target_scope": measure["target_scope"],
                    "applicability_score": round(score, 2),
                    "expected_reduction_tco2": reduction,
                    "capex_million_cny": capex_million,
                    "annual_net_savings_million_cny": annual_savings,
                    "missing_inputs": missing_inputs,
                }
            )

            if missing_inputs:
                gaps.append(
                    DataGap(
                        missing=f"{measure['id']}:{','.join(missing_inputs)}",
                        impact=f"无法完成 {measure['name']} 的工程选型/定容，需补充输入字段",
                        severity="medium" if len(missing_inputs) < 2 else "high",
                    )
                )

        measures_payload.sort(key=lambda x: x["applicability_score"], reverse=True)
        return measures_payload[:6], gaps

    # -------------------- policy KG --------------------
    def _match_policy_kg(
        self,
        scenario: Dict[str, Any],
        admin_codes: List[str],
        industry_codes: List[str],
        measures: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[Evidence], List[DataGap]]:
        data_gaps: List[DataGap] = []
        evidence: List[Evidence] = []

        kg_path_str = (
            scenario.get("policy_kg_path")
            or os.getenv("POLICY_KG_PATH")
            or str(Path(__file__).resolve().parents[1] / "data" / "mock_policy_kg.json")
        )
        kg_path = Path(str(kg_path_str))
        measure_ids = [str(m.get("id")) for m in measures if m.get("id")]

        if not measure_ids:
            data_gaps.append(
                DataGap(
                    missing="measure_ids",
                    impact="没有可匹配的措施ID，政策匹配与补贴估算无法进行。",
                    severity="high",
                )
            )

        matched: List[Dict[str, Any]] = []
        incentives_by_measure: Dict[str, Any] = {}
        kg_version = "unknown"
        confidence = 0.35

        try:
            kg = PolicyKnowledgeGraph.load_json(kg_path)
            kg_version = kg.kg_version

            matched = kg.match(
                admin_codes=admin_codes,
                industry_codes=industry_codes,
                measure_ids=measure_ids,
                top_k=30,
            )
            incentives_by_measure = compute_incentives_by_measure(measures, matched)

            matched_docs = {clause.get("doc_id") for clause in matched if clause.get("doc_id")}
            matched_by_measure: Dict[str, int] = {}
            for clause in matched:
                for mid in clause.get("measure_ids") or []:
                    mid = str(mid)
                    matched_by_measure[mid] = matched_by_measure.get(mid, 0) + 1

            total_subsidy = round(
                sum(float(item.get("capex_subsidy_million_cny") or 0.0) for item in incentives_by_measure.values()),
                4,
            )

            metrics: Dict[str, Any] = {
                "kg_version": kg_version,
                "kg_path": str(kg_path),
                "matched_clause_count": len(matched),
                "matched_doc_count": len(matched_docs),
                "matched_by_measure": matched_by_measure,
                "policy_capex_subsidy_total_million_cny": total_subsidy,
            }
            artifacts = {
                "kg_path": str(kg_path),
                "matched_clauses": matched,
                "incentives_by_measure": incentives_by_measure,
            }
            evidence.append(
                Evidence(
                    evidence_id="EVID-POLICY-KG",
                    description=f"Policy KG loaded (kg_version={kg_version})",
                    source="policy_kg_file",
                    uri=str(kg_path),
                )
            )

            confidence = 0.55
            if matched:
                confidence += 0.20
            if admin_codes:
                confidence += 0.10
            if industry_codes:
                confidence += 0.05
            confidence -= 0.05 * len([gap for gap in data_gaps if gap.severity == "high"])
            confidence = max(0.15, min(0.90, confidence))

            metrics["policy_confidence"] = round(confidence, 3)
            return metrics, artifacts, evidence, data_gaps
        except FileNotFoundError:
            data_gaps.append(
                DataGap(
                    missing="policy_kg_file",
                    impact="政策KG文件缺失，无法进行政策匹配与补贴估算。",
                    severity="high",
                )
            )
            metrics = {
                "kg_version": kg_version,
                "kg_path": str(kg_path),
                "matched_clause_count": 0,
                "matched_doc_count": 0,
                "matched_by_measure": {},
                "policy_capex_subsidy_total_million_cny": 0.0,
                "policy_confidence": 0.15,
            }
            artifacts = {"kg_path": str(kg_path), "matched_clauses": [], "incentives_by_measure": {}}
            return metrics, artifacts, evidence, data_gaps
        except Exception as e:
            data_gaps.append(
                DataGap(
                    missing="policy_kg_parse_error",
                    impact=f"政策KG解析失败：{e}",
                    severity="high",
                )
            )
            metrics = {
                "kg_version": kg_version,
                "kg_path": str(kg_path),
                "matched_clause_count": 0,
                "matched_doc_count": 0,
                "matched_by_measure": {},
                "policy_capex_subsidy_total_million_cny": 0.0,
                "policy_confidence": 0.15,
            }
            artifacts = {"kg_path": str(kg_path), "matched_clauses": [], "incentives_by_measure": {}}
            return metrics, artifacts, evidence, data_gaps

    # -------------------- energy flow deepresearch --------------------
    def _energy_flow_deepresearch(self, intake_artifacts: Dict[str, Any]) -> Tuple[str, List[DataGap]]:
        gaps: List[DataGap] = []
        excel_items = intake_artifacts.get("excel_artifacts") or []
        detected = []
        for item in excel_items:
            detected.extend(item.get("detected_energyflow") or [])

        if not detected:
            gaps.append(
                DataGap(
                    missing="energy_flow_table",
                    impact="未检测到能流表（Excel sheet），能流分析将以方法论+数据缺口形式输出。",
                    severity="medium",
                )
            )
            summary = (
                "### 能流分析（DeepResearch，占位模板）\n"
                "- 当前未提供结构化能流表（来源-转换-去向）。\n"
                "- 建议补充：一次能源输入（电/气/煤/蒸汽/热）、转换设备效率、终端负荷曲线、损失项。\n"
                "- 影响：无法定量识别高损失环节与梯级利用机会；本报告仅给出逻辑框架与待办数据项。\n"
            )
            return summary, gaps

        # Use first detected table preview for narrative
        first = detected[0]
        preview = first.get("preview_rows") or []
        prompt = (
            "你是工业园区能流分析助手。\n"
            "请基于能流表的预览行，输出一段中文 Markdown 的“能流解释”章节：\n"
            "1) 描述主要能源载体（电/热/蒸汽/燃气等）从哪里来、经过哪些转换、到哪里去；\n"
            "2) 指出可能的损失或效率风险（如果表中有相关字段就引用，否则用'可能'并标注缺口）；\n"
            "3) 输出 3-5 个建议的补充数据字段。\n"
            "要求：不做复杂计算，不编造不存在的数值；若字段不足，明确说明。\n"
            f"能流表预览（JSON）：{preview}"
        )
        fallback = (
            "### 能流分析（DeepResearch）\n"
            f"- 检测到能流表：sheet={first.get('sheet')}\n"
            "- 由于字段口径不确定，本节先给出解释框架与数据缺口。\n"
            "- 建议在能流表中包含：from/to/carrier/value/unit/efficiency/loss 等字段。\n"
        )
        summary = self.llm.markdown(
            system_prompt="你是资深的工业园区能流分析专家，专门从事多能源系统的技术经济分析。请输出专业的 Markdown 分析报告。",
            user_prompt=prompt,
            fallback=fallback,
        )
        return summary, gaps

    # -------------------- cash flow deepresearch --------------------
    def _cash_flow_deepresearch(
        self, intake_artifacts: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]], List[DataGap]]:
        gaps: List[DataGap] = []
        excel_items = intake_artifacts.get("excel_artifacts") or []
        detected = []
        for item in excel_items:
            detected.extend(item.get("detected_cashflow") or [])

        if not detected:
            gaps.append(
                DataGap(
                    missing="cashflow_table",
                    impact="未检测到现金流表（Excel sheet），现金流分析将以方法论+占位模板输出。",
                    severity="medium",
                )
            )
            summary = (
                "### 现金流分析（DeepResearch，占位模板）\n"
                "- 当前未提供现金流表（CAPEX/OPEX/年度收益/折现/补贴等）。\n"
                "- 建议补充：CAPEX构成、运维成本、节能收益、电价/碳价假设、补贴条款与兑现条件。\n"
                "- 影响：无法形成可审计的回收期/NPV 结论；本报告仅给出解释框架与数据缺口。\n"
            )
            return summary, [], gaps

        first = detected[0]
        preview = first.get("preview_rows") or []
        prompt = (
            "你是工业园区经济性分析助手。\n"
            "请基于现金流表预览，输出一段中文 Markdown 的“现金流解释”章节：\n"
            "1) 说明现金流表的时间维度（年/季度/月份）、关键科目（CAPEX/OPEX/收益/补贴）；\n"
            "2) 识别最敏感的参数（电价/负荷/补贴兑现/折现率等）；\n"
            "3) 输出风险点与需要补充的数据。\n"
            "要求：不做复杂金融建模，不编造数值。\n"
            f"现金流表预览（JSON）：{preview}"
        )
        fallback = (
            "### 现金流分析（DeepResearch）\n"
            f"- 检测到现金流表：sheet={first.get('sheet')}\n"
            "- 当前仅有预览，建议补充完整年度现金流与关键假设（折现率、寿命期、税费等）。\n"
        )
        summary = self.llm.markdown(
            system_prompt="你是资深的工业园区经济性分析专家，专门从事多能源项目的财务评估和投资分析。请输出专业的 Markdown 分析报告。",
            user_prompt=prompt,
            fallback=fallback,
        )

        # For artifacts: use the preview as lightweight cashflow_table
        table = preview if isinstance(preview, list) else []
        return summary, table, gaps

    # -------------------- finance rollup (fallback) --------------------
    def _finance_rollup(
        self,
        scenario: Dict[str, Any],
        measures: List[Dict[str, Any]],
        incentives_by_measure: Dict[str, Any],
        cash_flow_table: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[DataGap]]:
        gaps: List[DataGap] = []

        # If a cashflow table exists, trust it (agent should not override heavy modeling).
        if cash_flow_table:
            metrics = {
                "finance_source": "excel_cashflow_table_preview",
                "note": "已提供现金流表预览，建议在生产环境读取完整表进行解释与审计。",
            }
            artifacts = {"cashflow_table": cash_flow_table}
            return metrics, artifacts, gaps

        # Otherwise: simple portfolio roll-up similar to MVP
        discount_rate = float(scenario.get("discount_rate") or 0.08)
        lifetime_years = int(scenario.get("finance_horizon_years") or 10)

        gross_capex = 0.0
        total_incentive = 0.0
        total_capex = 0.0
        total_annual_net = 0.0
        for m in measures:
            capex = float(m.get("capex_million_cny") or 0.0)
            gross_capex += capex
            mid = str(m.get("id") or "")
            incentive = float((incentives_by_measure.get(mid) or {}).get("capex_subsidy_million_cny") or 0.0)
            incentive = max(0.0, min(incentive, capex))
            total_incentive += incentive
            total_capex += capex - incentive
            total_annual_net += float(m.get("annual_net_savings_million_cny") or 0.0)

        cashflows: List[Dict[str, float]] = []
        for year in range(1, lifetime_years + 1):
            discounted = total_annual_net / pow(1 + discount_rate, year)
            cashflows.append({"year": year, "discounted_net_million_cny": round(discounted, 4)})

        npv = round(sum(flow["discounted_net_million_cny"] for flow in cashflows) - total_capex, 2)
        payback = round(total_capex / total_annual_net, 2) if total_annual_net else None

        if not measures:
            gaps.append(
                DataGap(
                    missing="measures",
                    impact="缺少措施清单，无法进行组合经济性估算。",
                    severity="high",
                )
            )
        if total_annual_net <= 0:
            gaps.append(
                DataGap(
                    missing="annual_net_savings",
                    impact="年净收益不足或为0，无法计算NPV/回收期。",
                    severity="high",
                )
            )

        metrics = {
            "finance_source": "fallback_rollup",
            "portfolio_capex_million_cny": round(total_capex, 2),
            "portfolio_capex_gross_million_cny": round(gross_capex, 2),
            "policy_incentive_million_cny": round(total_incentive, 2),
            "portfolio_annual_net_million_cny": round(total_annual_net, 2),
            "portfolio_npv_million_cny": npv,
            "portfolio_payback_years": payback,
            "discount_rate": discount_rate,
            "finance_horizon_years": lifetime_years,
        }
        artifacts = {"cashflow_table": cashflows}
        return metrics, artifacts, gaps

    # -------------------- pdf evidence collector --------------------
    def _collect_pdf_evidence(self, intake_artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        pdf_items = intake_artifacts.get("pdf_artifacts") or []
        evidence_items: List[Dict[str, Any]] = []
        for item in pdf_items:
            evidence_items.extend(item.get("evidence_items") or [])
        return evidence_items
