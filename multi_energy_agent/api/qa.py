"""Interactive Q&A service for generated reports."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportQAService:
    """Provides Q&A capabilities over generated reports."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._qa_index_cache: Dict[str, Dict[str, Any]] = {}

    def load_qa_index(self, scenario_id: str, output_root: str = "outputs") -> Optional[Dict[str, Any]]:
        """Load QA index for a scenario."""
        cache_key = f"{scenario_id}:{output_root}"
        if cache_key in self._qa_index_cache:
            return self._qa_index_cache[cache_key]

        qa_index_path = Path(output_root) / scenario_id / "artifacts" / "qa_index.json"
        if not qa_index_path.exists():
            logger.warning(f"QA index not found: {qa_index_path}")
            return None

        try:
            with open(qa_index_path, "r", encoding="utf-8") as f:
                qa_index = json.load(f)
            self._qa_index_cache[cache_key] = qa_index
            return qa_index
        except Exception as exc:
            logger.error(f"Failed to load QA index: {exc}")
            return None

    def load_report(self, scenario_id: str, output_root: str = "outputs") -> Optional[str]:
        """Load report markdown content."""
        report_path = Path(output_root) / scenario_id / "report.md"
        if not report_path.exists():
            logger.warning(f"Report not found: {report_path}")
            return None

        try:
            return report_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error(f"Failed to load report: {exc}")
            return None

    def search_relevant_sections(
        self, 
        question: str, 
        qa_index: Dict[str, Any], 
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Search for relevant sections based on question keywords."""
        question_lower = question.lower()
        keywords = set(question_lower.split())
        
        sections = []
        
        # Search in data gaps
        for gap in qa_index.get("data_gaps", []):
            gap_text = f"{gap.get('missing', '')} {gap.get('impact', '')}".lower()
            score = sum(1 for kw in keywords if kw in gap_text)
            if score > 0:
                sections.append({
                    "type": "data_gap",
                    "content": gap,
                    "score": score
                })
        
        # Search in measures
        for measure in qa_index.get("measures", []):
            measure_text = f"{measure.get('name', '')} {measure.get('id', '')}".lower()
            score = sum(1 for kw in keywords if kw in measure_text)
            if score > 0:
                sections.append({
                    "type": "measure",
                    "content": measure,
                    "score": score
                })
        
        # Search in policies
        for policy in qa_index.get("policies", []):
            policy_text = f"{policy.get('citation_no', '')} {policy.get('excerpt', '')}".lower()
            score = sum(1 for kw in keywords if kw in policy_text)
            if score > 0:
                sections.append({
                    "type": "policy",
                    "content": policy,
                    "score": score
                })
        
        # Sort by score and return top_k
        sections.sort(key=lambda x: x["score"], reverse=True)
        return sections[:top_k]

    def answer_question(
        self,
        question: str,
        scenario_id: str,
        output_root: str = "outputs"
    ) -> Dict[str, Any]:
        """Answer a question about the report."""
        # Load QA index and report
        qa_index = self.load_qa_index(scenario_id, output_root)
        if not qa_index:
            return {
                "answer": "无法加载报告索引，请确保场景已完成执行。",
                "sources": [],
                "confidence": 0.0
            }

        report_content = self.load_report(scenario_id, output_root)
        
        # Search relevant sections
        relevant_sections = self.search_relevant_sections(question, qa_index)
        
        # Build context from relevant sections
        context_parts = []
        sources = []
        
        for section in relevant_sections:
            section_type = section["type"]
            content = section["content"]
            
            if section_type == "measure":
                context_parts.append(
                    f"措施：{content.get('name')} (ID: {content.get('id')})\n"
                    f"评分：{content.get('applicability_score')}\n"
                    f"减排：{content.get('expected_reduction_tco2')} tCO2\n"
                    f"投资：{content.get('capex_million_cny')} 百万元"
                )
                sources.append({
                    "type": "measure",
                    "id": content.get("id"),
                    "name": content.get("name")
                })
            
            elif section_type == "policy":
                context_parts.append(
                    f"政策条款：{content.get('citation_no')}\n"
                    f"内容：{content.get('excerpt')}"
                )
                sources.append({
                    "type": "policy",
                    "citation": content.get("citation_no"),
                    "excerpt": content.get("excerpt", "")[:100]
                })
            
            elif section_type == "data_gap":
                context_parts.append(
                    f"数据缺口：{content.get('missing')}\n"
                    f"影响：{content.get('impact')}\n"
                    f"严重程度：{content.get('severity')}"
                )
                sources.append({
                    "type": "data_gap",
                    "missing": content.get("missing"),
                    "severity": content.get("severity")
                })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer
        if self.llm_client:
            try:
                answer = self._generate_llm_answer(question, context, qa_index)
                confidence = 0.8
            except Exception as exc:
                logger.warning(f"LLM generation failed: {exc}, using fallback")
                answer = self._generate_fallback_answer(question, context, qa_index)
                confidence = 0.5
        else:
            answer = self._generate_fallback_answer(question, context, qa_index)
            confidence = 0.5
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "relevant_sections": len(relevant_sections)
        }

    def _generate_llm_answer(
        self, 
        question: str, 
        context: str, 
        qa_index: Dict[str, Any]
    ) -> str:
        """Generate answer using LLM."""
        system_prompt = """你是一位资深的多能源园区低碳规划专家，专门从事工业园区碳中和路径设计和技术经济分析。你具备能源工程、环境科学、经济学和政策分析的跨学科专业知识。

基于提供的报告内容，请进行专业的技术经济分析并回答用户问题。

分析要求：
1. **多维度深度分析**：从技术可行性、经济合理性、环境效益、政策支持四个维度综合评估
2. **数据驱动决策**：引用具体的排放数据、投资额度、减排潜力、政策条款等支持分析
3. **专业见解提供**：基于能源工程和碳管理最佳实践，提供可操作的专业建议
4. **风险识别评估**：识别技术风险、经济风险、政策风险，并提出应对措施
5. **数据缺口管理**：明确指出关键数据缺失对分析结果的影响，建议补充方案
6. **客观专业表达**：保持技术中立，基于事实和标准方法进行分析，避免过度乐观或悲观

请确保所有数值都有明确来源，关键假设条件透明标注，在不确定情况下采用保守估算。"""

        user_prompt = f"""问题：{question}

相关内容：
{context}

报告摘要：
- 基线排放：{qa_index.get('baseline', {}).get('total_emissions_tco2', 'N/A')} tCO2
- 措施数量：{len(qa_index.get('measures', []))}
- 政策条款：{len(qa_index.get('policies', []))}

请基于以上信息回答问题。"""

        fallback = self._generate_fallback_answer(question, context, qa_index)
        response = self.llm_client.markdown(system_prompt, user_prompt, fallback=fallback)
        return response.strip()

    def _generate_fallback_answer(
        self, 
        question: str, 
        context: str, 
        qa_index: Dict[str, Any]
    ) -> str:
        """Generate fallback answer without LLM."""
        question_lower = question.lower()
        
        # Pattern matching for common questions
        if any(kw in question_lower for kw in ["措施", "建议", "方案"]):
            measures = qa_index.get("measures", [])
            if measures:
                top_measures = measures[:3]
                answer = "根据报告分析，推荐以下措施：\n\n"
                for i, m in enumerate(top_measures, 1):
                    answer += f"{i}. {m.get('name')} (评分: {m.get('applicability_score')})\n"
                    answer += f"   - 预期减排：{m.get('expected_reduction_tco2')} tCO2\n"
                    answer += f"   - 投资额：{m.get('capex_million_cny')} 百万元\n\n"
                return answer
        
        elif any(kw in question_lower for kw in ["政策", "补贴", "支持"]):
            policies = qa_index.get("policies", [])
            if policies:
                answer = "相关政策支持：\n\n"
                for i, p in enumerate(policies[:3], 1):
                    answer += f"{i}. {p.get('citation_no')}\n"
                    answer += f"   {p.get('excerpt', '')[:100]}...\n\n"
                return answer
        
        elif any(kw in question_lower for kw in ["排放", "碳", "基线"]):
            baseline = qa_index.get("baseline", {})
            answer = f"园区基线排放情况：\n\n"
            answer += f"- 总排放：{baseline.get('total_emissions_tco2', 'N/A')} tCO2\n"
            answer += f"- Scope1：{baseline.get('scope1_tco2', 'N/A')} tCO2\n"
            answer += f"- Scope2：{baseline.get('scope2_tco2', 'N/A')} tCO2\n"
            return answer
        
        elif any(kw in question_lower for kw in ["数据", "缺口", "完善"]):
            gaps = qa_index.get("data_gaps", [])
            if gaps:
                high_gaps = [g for g in gaps if g.get("severity") == "high"]
                answer = f"当前存在 {len(gaps)} 个数据缺口"
                if high_gaps:
                    answer += f"，其中 {len(high_gaps)} 个高优先级：\n\n"
                    for g in high_gaps[:3]:
                        answer += f"- {g.get('missing')}\n"
                        answer += f"  影响：{g.get('impact')}\n\n"
                else:
                    answer += "，均为中低优先级。\n"
                return answer
        
        # Generic answer with context
        if context:
            return f"根据报告内容，找到以下相关信息：\n\n{context}\n\n如需更详细的分析，请查看完整报告。"
        else:
            return "抱歉，未能在报告中找到直接相关的信息。请尝试更具体的问题，或查看完整报告。"

    def get_suggested_questions(self, scenario_id: str, output_root: str = "outputs") -> List[str]:
        """Get suggested questions based on report content."""
        qa_index = self.load_qa_index(scenario_id, output_root)
        if not qa_index:
            return []
        
        suggestions = [
            "有哪些推荐的减排措施？",
            "园区的基线排放是多少？",
            "有哪些政策支持和补贴？",
        ]
        
        # Add measure-specific questions
        measures = qa_index.get("measures", [])
        if measures:
            top_measure = measures[0]
            suggestions.append(f"{top_measure.get('name')}的具体情况如何？")
        
        # Add data gap questions if any
        gaps = qa_index.get("data_gaps", [])
        if gaps:
            suggestions.append("还需要补充哪些数据？")
        
        return suggestions


__all__ = ["ReportQAService"]
