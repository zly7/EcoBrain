"""Policy knowledge graph utilities used by the policy agent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class PolicyDoc:
    doc_id: str
    title: str
    issuer: str = ""
    effective_date: str = ""
    uri: Optional[str] = None


@dataclass
class PolicyClause:
    clause_id: str
    doc_id: str
    citation_no: str
    excerpt: str
    effective_date: str = ""
    admin_codes: List[str] = field(default_factory=list)
    industry_codes: List[str] = field(default_factory=list)
    measure_ids: List[str] = field(default_factory=list)
    incentives: Dict[str, Any] = field(default_factory=dict)
    analysis_points: List[str] = field(default_factory=list)


@dataclass
class PolicyKnowledgeGraph:
    kg_version: str
    generated_at: str = ""
    docs: Dict[str, PolicyDoc] = field(default_factory=dict)
    clauses: List[PolicyClause] = field(default_factory=list)

    @classmethod
    def load_json(cls, path: Path) -> "PolicyKnowledgeGraph":
        """Load a JSON knowledge graph from disk."""

        raw = json.loads(path.read_text(encoding="utf-8-sig"))

        docs: Dict[str, PolicyDoc] = {}
        for doc_entry in raw.get("docs", []):
            doc = PolicyDoc(
                doc_id=str(doc_entry.get("doc_id")),
                title=str(doc_entry.get("title", "")),
                issuer=str(doc_entry.get("issuer", "")),
                effective_date=str(doc_entry.get("effective_date", "")),
                uri=doc_entry.get("uri"),
            )
            if doc.doc_id:
                docs[doc.doc_id] = doc

        clauses: List[PolicyClause] = []
        for clause_entry in raw.get("clauses", []):
            clause = PolicyClause(
                clause_id=str(clause_entry.get("clause_id")),
                doc_id=str(clause_entry.get("doc_id")),
                citation_no=str(clause_entry.get("citation_no", "")),
                excerpt=str(clause_entry.get("excerpt", "")),
                effective_date=str(clause_entry.get("effective_date", "")),
                admin_codes=[str(code) for code in (clause_entry.get("admin_codes") or [])],
                industry_codes=[str(code) for code in (clause_entry.get("industry_codes") or [])],
                measure_ids=[str(mid) for mid in (clause_entry.get("measure_ids") or [])],
                incentives=dict(clause_entry.get("incentives") or {}),
                analysis_points=[str(item) for item in (clause_entry.get("analysis_points") or [])],
            )
            if clause.clause_id and clause.doc_id:
                clauses.append(clause)

        return cls(
            kg_version=str(raw.get("kg_version", "unknown")),
            generated_at=str(raw.get("generated_at", "")),
            docs=docs,
            clauses=clauses,
        )

    def match(
        self,
        admin_codes: Sequence[str],
        industry_codes: Sequence[str] | None,
        measure_ids: Sequence[str],
        *,
        top_k: int = 30,
    ) -> List[Dict[str, Any]]:
        """Match clauses deterministically by overlapping tags."""

        admin_set = {str(code) for code in (admin_codes or []) if code}
        industry_set = {str(code) for code in (industry_codes or []) if code}
        measure_set = {str(mid) for mid in (measure_ids or []) if mid}

        hits: List[Dict[str, Any]] = []
        for clause in self.clauses:
            clause_measure_set = set(clause.measure_ids)
            clause_admin_set = set(clause.admin_codes)
            clause_industry_set = set(clause.industry_codes)

            measure_hit = bool(clause_measure_set & measure_set) if clause_measure_set else True
            admin_hit = bool(clause_admin_set & admin_set) if clause_admin_set else True

            industry_hit = True
            if industry_set and clause_industry_set:
                industry_hit = bool(clause_industry_set & industry_set)

            if not (measure_hit and admin_hit and industry_hit):
                continue

            score = 0.40
            score += 0.25 if clause_admin_set else 0.05
            score += 0.25 if clause_measure_set else 0.05
            if industry_set:
                score += 0.10 if clause_industry_set else 0.00
            score = min(0.95, score)

            doc_title = self.docs.get(clause.doc_id).title if clause.doc_id in self.docs else ""
            hits.append(
                {
                    "clause_id": clause.clause_id,
                    "doc_id": clause.doc_id,
                    "doc_title": doc_title,
                    "citation_no": clause.citation_no,
                    "effective_date": clause.effective_date,
                    "excerpt": clause.excerpt,
                    "admin_codes": clause.admin_codes,
                    "industry_codes": clause.industry_codes,
                    "measure_ids": clause.measure_ids,
                    "analysis_points": clause.analysis_points,
                    "incentives": clause.incentives,
                    "relevance_score": round(score, 3),
                }
            )

        hits.sort(key=lambda item: item["relevance_score"], reverse=True)
        return hits[: max(0, int(top_k))]


def compute_incentives_by_measure(
    measures: Sequence[Dict[str, Any]],
    matched_clauses: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate deterministic capex subsidy per measure for finance."""

    by_measure: Dict[str, Any] = {}
    for measure in measures:
        measure_id = str(measure.get("id") or "")
        if not measure_id:
            continue

        capex = float(measure.get("capex_million_cny") or 0.0)

        best_match = None
        for clause in matched_clauses:
            if measure_id not in (clause.get("measure_ids") or []):
                continue
            incentives = clause.get("incentives") or {}
            pct = float(incentives.get("capex_subsidy_pct") or 0.0)
            cap = incentives.get("capex_subsidy_cap_million_cny")
            cap_value = float(cap) if cap is not None else float("inf")

            if best_match is None or pct > best_match[0] or (pct == best_match[0] and cap_value > best_match[1]):
                best_match = (pct, cap_value, clause)

        if best_match:
            pct, cap_value, clause = best_match
            subsidy = capex * pct
            if cap_value != float("inf"):
                subsidy = min(subsidy, cap_value)

            by_measure[measure_id] = {
                "capex_subsidy_pct": pct,
                "capex_subsidy_cap_million_cny": None if cap_value == float("inf") else cap_value,
                "capex_subsidy_million_cny": round(subsidy, 4),
                "matched_clause_id": clause.get("clause_id"),
                "citation_no": clause.get("citation_no"),
                "doc_id": clause.get("doc_id"),
            }
        else:
            by_measure[measure_id] = {
                "capex_subsidy_pct": 0.0,
                "capex_subsidy_cap_million_cny": None,
                "capex_subsidy_million_cny": 0.0,
                "matched_clause_id": None,
                "citation_no": None,
                "doc_id": None,
            }

    return by_measure
