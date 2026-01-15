"""Policy Knowledge Graph (KG) utilities.

This module is used by InsightSynthesisAgent (NOT a standalone agent) to:
- Load a policy KG (JSON)
- Deterministically match clauses to a region/industry/measures
- Produce auditable incentive mapping for report

IMPORTANT:
- Deterministic matching is intentional for MVP (auditable, testable).
- Replace this module with a real KG service when available.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class PolicyKnowledgeGraph:
    kg_version: str
    clauses: List[Dict[str, Any]]

    @classmethod
    def load_json(cls, path: Path) -> "PolicyKnowledgeGraph":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            kg_version=str(data.get("kg_version") or data.get("version") or "unknown"),
            clauses=list(data.get("clauses") or data.get("nodes") or []),
        )

    def match(
        self,
        admin_codes: Sequence[str],
        industry_codes: Sequence[str],
        measure_ids: Sequence[str],
        top_k: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return matched clauses sorted by deterministic overlap score."""

        admin_set = set([str(x) for x in admin_codes if x])
        ind_set = set([str(x) for x in industry_codes if x])
        measure_set = set([str(x) for x in measure_ids if x])

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for clause in self.clauses:
            c_admin = set([str(x) for x in (clause.get("admin_codes") or []) if x])
            c_ind = set([str(x) for x in (clause.get("industry_codes") or []) if x])
            c_mea = set([str(x) for x in (clause.get("measure_ids") or []) if x])

            score = 0.0
            if admin_set and c_admin:
                score += 1.5 * len(admin_set & c_admin)
            elif not c_admin:
                score += 0.2  # clause without region tag

            if ind_set and c_ind:
                score += 1.0 * len(ind_set & c_ind)
            elif not c_ind:
                score += 0.1

            if measure_set and c_mea:
                score += 2.0 * len(measure_set & c_mea)

            # If clause has no measure tag, it's less actionable for incentive mapping.
            if not c_mea:
                score -= 0.3

            if score <= 0:
                continue

            # Attach score for traceability
            enriched = dict(clause)
            enriched["_score"] = round(score, 4)
            scored.append((score, enriched))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]


def compute_incentives_by_measure(
    measures: List[Dict[str, Any]],
    matched_clauses: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Compute a simple incentive map per measure.

    Output example:
    {
      "PV_ROOF": {
         "capex_subsidy_million_cny": 1.2,
         "matched_clause_ids": [...],
         "citations": [...]
      }
    }
    """

    # Index clauses by measure id
    clauses_by_measure: Dict[str, List[Dict[str, Any]]] = {}
    for clause in matched_clauses:
        for mid in (clause.get("measure_ids") or []):
            mid = str(mid)
            clauses_by_measure.setdefault(mid, []).append(clause)

    incentives: Dict[str, Dict[str, Any]] = {}
    for m in measures:
        mid = str(m.get("id") or "")
        if not mid:
            continue
        capex = float(m.get("capex_million_cny") or 0.0)
        candidates = clauses_by_measure.get(mid, [])
        if not candidates or capex <= 0:
            incentives[mid] = {
                "capex_subsidy_million_cny": 0.0,
                "matched_clause_ids": [],
                "citations": [],
            }
            continue

        # pick the best clause by _score
        best = sorted(candidates, key=lambda x: float(x.get("_score") or 0.0), reverse=True)[0]
        fixed = best.get("capex_subsidy_million_cny")
        ratio = best.get("capex_subsidy_ratio")
        subsidy = 0.0
        if fixed is not None:
            try:
                subsidy = float(fixed)
            except Exception:
                subsidy = 0.0
        elif ratio is not None:
            try:
                subsidy = capex * float(ratio)
            except Exception:
                subsidy = 0.0
        subsidy = max(0.0, min(subsidy, capex))

        clause_id = str(best.get("clause_id") or best.get("citation_no") or best.get("doc_id") or "unknown")
        citation = str(best.get("citation_no") or best.get("doc_title") or clause_id)

        incentives[mid] = {
            "capex_subsidy_million_cny": round(subsidy, 4),
            "matched_clause_ids": [clause_id],
            "citations": [citation],
            "best_clause_score": float(best.get("_score") or 0.0),
        }

    return incentives
