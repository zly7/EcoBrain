"""Report orchestrator agent."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .base import AgentRunResult, BaseAgent
from ..llm import StructuredLLMClient
from ..schemas import Assumption, DataGap, Stage


class ReportOrchestratorAgent(BaseAgent):
    def __init__(self, llm: StructuredLLMClient | None = None) -> None:
        super().__init__(stage=Stage.REPORT, name="report_orchestrator", llm=llm or StructuredLLMClient())

    def run(self, state) -> AgentRunResult:  # type: ignore[override]
        scenario = state.get("scenario") or {}
        geo = self._get_envelope_metrics(state, Stage.GEO)
        baseline = self._get_envelope_metrics(state, Stage.BASELINE)
        measures = self._get_envelope_metrics(state, Stage.MEASURES)
        finance = self._get_envelope_metrics(state, Stage.FINANCE)

        summary_context = self._build_summary_context(geo, baseline, measures, finance)
        system_prompt = (
            "你是工业园区低碳路线图助手。输出简洁的 markdown 段落，包含现状、机会、风险。"
        )
        fallback_summary = self._fallback_summary(summary_context)
        summary_markdown = self.llm.markdown(
            system_prompt=system_prompt,
            user_prompt=summary_context,
            fallback=fallback_summary,
        )

        report_markdown = self._build_report(
            scenario=scenario,
            geo=geo,
            baseline=baseline,
            measures=measures,
            finance=finance,
            summary=summary_markdown,
        )

        appendix = [{"parameter": key, "value": value} for key, value in scenario.items()]
        aggregated_gaps = list(self._collect_data_gaps(state))

        metrics = {
            "summary_section": summary_markdown,
            "outstanding_gaps": [gap.__dict__ for gap in aggregated_gaps],
        }

        assumptions = [
            Assumption(
                name="report_template",
                value="mvp_v0.1",
                reason="Matches 指引.md requirements for ResultEnvelope/report stage",
            )
        ]
        evidence = [
            self._build_evidence(
                description="Report composes previous envelopes to guarantee auditable traceability",
                source="envelope_chain",
            )
        ]

        confidence = 0.6 if aggregated_gaps else 0.8
        envelope = self._create_envelope(
            state=state,
            metrics=metrics,
            artifacts={"report_markdown": report_markdown, "appendix_params_table": appendix},
            assumptions=assumptions,
            evidence=evidence,
            confidence=confidence,
            data_gaps=aggregated_gaps,
        )

        review_items = []
        if aggregated_gaps:
            review_items.append(
                self._review_item(
                    checkpoint_id="report_outstanding_gaps",
                    issue="Report contains unresolved data gaps. Annotate mitigations before delivery.",
                    editable_fields=["report_markdown", "appendix_params_table"],
                    suggested_action="Document mitigation for each data gap in the summary section.",
                    severity="medium",
                )
            )
        return AgentRunResult(envelope=envelope, review_items=review_items)

    def _collect_data_gaps(self, state) -> Iterable[DataGap]:
        envelopes = state.get("envelopes") or {}
        for envelope in envelopes.values():
            for gap in envelope.get("data_gaps") or []:
                yield DataGap(
                    missing=gap.get("missing", ""),
                    impact=gap.get("impact", ""),
                    severity=gap.get("severity", "medium"),
                )

    def _build_summary_context(
        self, geo: Dict[str, Any], baseline: Dict[str, Any], measures: Dict[str, Any], finance: Dict[str, Any]
    ) -> str:
        measures_brief = ", ".join(
            f"{item['name']} ({item['applicability_score']})" for item in measures.get("top_measures", [])
        )
        context = (
            f"园区面积{geo.get('area_km2', 'N/A')} km2，估算企业 {geo.get('entity_count_est','N/A')} 家。"
            f" 基线排放 {baseline.get('total_emissions_tco2','N/A')} tCO2。"
            f" 推荐措施：{measures_brief or '暂无' }。"
            f" 投资 {finance.get('portfolio_capex_million_cny','-')} 百万，NPV "
            f"{finance.get('portfolio_npv_million_cny','-')} 百万。"
            " 输出一段 3 句话的总结。"
        )
        return context

    def _fallback_summary(self, context: str) -> str:
        return f"## 摘要\n{context}\n- 按照代理链路生成的结果，优先推进数据完整度较高的措施。\n"

    def _build_report(
        self,
        scenario: Dict[str, Any],
        geo: Dict[str, Any],
        baseline: Dict[str, Any],
        measures: Dict[str, Any],
        finance: Dict[str, Any],
        summary: str,
    ) -> str:
        lines: List[str] = [
            f"# 场景 {scenario.get('scenario_id','default')} 低碳路线图",
            summary.strip(),
            "## 1. 选区与数据完备度",
            f"- 面积：{geo.get('area_km2','?')} km^2",
            f"- 行政区划：{', '.join(geo.get('admin_codes', [])) or '未提供'}",
            f"- 企业数估计：{geo.get('entity_count_est','?')}",
            f"- 数据完整度：{geo.get('data_completeness_score','?')}",
            "## 2. 基线排放",
            f"- Scope1：{baseline.get('scope1_emissions_tco2','?')} tCO2",
            f"- Scope2：{baseline.get('scope2_emissions_tco2','?')} tCO2",
            f"- 能源强度：{baseline.get('energy_intensity_mwh_per_entity','?')} MWh/企业",
            "## 3. 筛选措施",
        ]
        for idx, item in enumerate(measures.get("top_measures", []), start=1):
            lines.append(
                f"{idx}. {item['name']} (评分 {item['applicability_score']}) "
                f"- 减排 {item['expected_reduction_tco2']} tCO2"
                f", 投资 {item['capex_million_cny']} 百万"
            )
        if not measures.get("top_measures"):
            lines.append("- 暂无推荐，需要补充数据。")

        lines.extend(
            [
                "## 4. 经济性",
                f"- 总投资：{finance.get('portfolio_capex_million_cny','?')} 百万 CNY",
                f"- 年净收益：{finance.get('portfolio_annual_net_million_cny','?')} 百万 CNY",
                f"- NPV：{finance.get('portfolio_npv_million_cny','?')} 百万 CNY",
                f"- 投资回收期：{finance.get('portfolio_payback_years','?')} 年",
                "## 5. 风险与下一步",
                "- 针对数据缺口建立人工校验点，确保证据链完整。",
                "- 结合政策条款匹配工具补充政策激励引用。",
            ]
        )
        return "\n".join(lines)
