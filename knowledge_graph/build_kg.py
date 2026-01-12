"""Build an integrated park+policy knowledge graph from sources.

This module:
1) Reads the mock sources (or real sources once replaced)
2) Builds a full KnowledgeGraph (nodes + edges)
3) Exports an *enriched* policy KG JSON compatible with PolicyKnowledgeGraph.load_json()

The resulting JSON keeps backward compatibility with the current policy agent:
- It must contain top-level keys: kg_version, generated_at, docs, clauses
- It MAY contain additional keys like graph, sources, indices, etc.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import resolve_data_dir, resolve_mock_source_dir
from .kg_model import KGRef, KnowledgeGraph, utc_now_iso


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except Exception:
        return None


def build_kg_from_sources(source_dir: Path) -> Tuple[KnowledgeGraph, Dict[str, Any]]:
    """Return (full_graph, policy_extract_payload)."""

    # --- Load sources ---
    survey = _read_json(source_dir / "field_survey.json")
    roof_rows = _read_csv(source_dir / "roof_inventory.csv")
    ent_rows = _read_csv(source_dir / "enterprise_registry.csv")
    ent_energy_rows = _read_csv(source_dir / "enterprise_energy_monthly_2023.csv")
    industry_rows = _read_csv(source_dir / "industry_energy_scale.csv")
    policy_extract = _read_json(source_dir / "policy_report_extract.json")

    kg = KnowledgeGraph(
        kg_version="demo-park-policy-kg-v0.2",
        notes="Mock integrated KG. Replace mock_sources with real survey/crawl/policy extract when available.",
    )

    # --- Provenance refs ---
    ref_survey = KGRef(source="field_survey", uri=str(source_dir / "field_survey.json"))
    ref_roof = KGRef(source="roof_inventory", uri=str(source_dir / "roof_inventory.csv"))
    ref_ent = KGRef(source="enterprise_registry", uri=str(source_dir / "enterprise_registry.csv"))
    ref_ent_energy = KGRef(source="enterprise_energy_monthly_2023", uri=str(source_dir / "enterprise_energy_monthly_2023.csv"))
    ref_industry = KGRef(source="industry_energy_scale", uri=str(source_dir / "industry_energy_scale.csv"))
    ref_policy = KGRef(source="policy_report_extract", uri=str(source_dir / "policy_report_extract.json"))

    # --- Park core node ---
    park_basic = ((survey.get("park") or {}).get("basic") or {})
    region_id = str(park_basic.get("region_id") or "unknown_region")
    park_name = str(park_basic.get("name") or region_id)
    admin_codes = ((park_basic.get("admin") or {}).get("codes") or [])
    location = (park_basic.get("location") or {})
    park_node = kg.upsert_node(
        "Park",
        region_id,
        name=park_name,
        props={
            "region_id": region_id,
            "admin_codes": admin_codes,
            "area_km2": (location.get("area_km2")),
            "center_lat": ((location.get("center") or {}).get("lat")),
            "center_lon": ((location.get("center") or {}).get("lon")),
        },
        refs=[ref_survey],
    )

    # AdminRegion nodes + edges
    for code in admin_codes:
        code_str = str(code)
        region_node = kg.upsert_node(
            "AdminRegion",
            code_str,
            name=code_str,
            props={"admin_code": code_str},
            refs=[ref_survey],
        )
        kg.add_edge(park_node, region_node, "LOCATED_IN", props={"scope": "admin_code"}, refs=[ref_survey])

    # --- Stakeholders needs (Gov + operator) ---
    stakeholders = ((survey.get("park") or {}).get("stakeholders") or {})
    gov = stakeholders.get("government") or {}
    if gov:
        gov_node = kg.upsert_node(
            "Organization",
            "gov_demo",
            name=str(gov.get("org_name") or "政府部门"),
            props={"org_type": "government"},
            refs=[ref_survey],
        )
        kg.add_edge(gov_node, park_node, "GOVERNS", refs=[ref_survey])

        gov_needs = (gov.get("needs") or {})
        req_node = kg.upsert_node(
            "Requirement",
            "gov_kpi_targets",
            name="政府KPI与约束",
            props={"details": gov_needs},
            refs=[ref_survey],
        )
        kg.add_edge(gov_node, req_node, "HAS_REQUIREMENT", refs=[ref_survey])

    operator = stakeholders.get("park_operator") or {}
    if operator:
        op_name = str(operator.get("org_name") or "园区运营方")
        op_node = kg.upsert_node(
            "Organization",
            "park_operator_demo",
            name=op_name,
            props={"org_type": "park_operator", "needs": operator.get("needs") or {}},
            refs=[ref_survey],
        )
        kg.add_edge(op_node, park_node, "OPERATES", refs=[ref_survey])

    # --- Industry reference table (Lin LuoXi) ---
    for row in industry_rows:
        code = str(row.get("industry_code") or "").strip()
        if not code:
            continue
        industry_node = kg.upsert_node(
            "Industry",
            code,
            name=str(row.get("industry_name") or code),
            props={
                "industry_code": code,
                "electricity_mwh_per_billion_output": _float_or_none(row.get("electricity_mwh_per_billion_output")),
                "thermal_mwh_per_billion_output": _float_or_none(row.get("thermal_mwh_per_billion_output")),
                "waste_heat_grade": row.get("waste_heat_grade"),
                "waste_heat_potential_mwh_per_billion_output": _float_or_none(row.get("waste_heat_potential_mwh_per_billion_output")),
                "common_measures": row.get("common_measures"),
                "investment_priority_hint": row.get("investment_priority_hint"),
            },
            refs=[ref_industry],
        )
        kg.add_edge(industry_node, park_node, "IN_PORTFOLIO", props={"meaning": "park_has_industry_reference"}, refs=[ref_industry])

    # --- Enterprises (Zhang survey + Denfin registry) ---
    ent_by_id: Dict[str, str] = {}

    for row in ent_rows:
        ent_id = str(row.get("enterprise_id") or "").strip()
        if not ent_id:
            continue
        ent_node = kg.upsert_node(
            "Enterprise",
            ent_id,
            name=str(row.get("name") or ent_id),
            props={
                "enterprise_id": ent_id,
                "industry_code": row.get("industry_code"),
                "employees": _int_or_none(row.get("employees")),
                "output_value_million_cny": _float_or_none(row.get("output_value_million_cny")),
                "has_boiler": row.get("has_boiler"),
                "has_waste_heat": row.get("has_waste_heat"),
                "has_roof_pv_ready": row.get("has_roof_pv_ready"),
                "notes": row.get("notes"),
            },
            refs=[ref_ent],
        )
        ent_by_id[ent_id] = ent_node
        kg.add_edge(ent_node, park_node, "LOCATED_IN", refs=[ref_ent])

        industry_code = str(row.get("industry_code") or "").strip()
        if industry_code:
            industry_node = kg.upsert_node(
                "Industry",
                industry_code,
                name=industry_code,
                props={"industry_code": industry_code},
                refs=[ref_ent],
            )
            kg.add_edge(ent_node, industry_node, "BELONGS_TO", refs=[ref_ent])

    # survey contains richer enterprise data; merge in
    for ent in stakeholders.get("enterprises") or []:
        profile = ent.get("enterprise_profile") or {}
        ent_id = str(profile.get("enterprise_id") or "").strip()
        if not ent_id:
            continue
        ent_node = kg.upsert_node(
            "Enterprise",
            ent_id,
            name=str(profile.get("name") or ent_id),
            props={
                "enterprise_id": ent_id,
                "industry_code": profile.get("industry_code"),
                "employees": profile.get("employees"),
                "output_value_million_cny": profile.get("output_value_million_cny"),
                "main_products": profile.get("main_products"),
                "land_area_m2": ((profile.get("site") or {}).get("land_area_m2")),
            },
            refs=[ref_survey],
        )
        ent_by_id[ent_id] = ent_node
        kg.add_edge(ent_node, park_node, "LOCATED_IN", refs=[ref_survey])

        # Needs -> Requirement node
        needs = ent.get("needs") or {}
        if needs:
            req_node = kg.upsert_node(
                "Requirement",
                f"{ent_id}_needs",
                name=f"{ent_id} 需求与约束",
                props=needs,
                refs=[ref_survey],
            )
            kg.add_edge(ent_node, req_node, "HAS_REQUIREMENT", refs=[ref_survey])

        # Production -> Process / Equipment / WasteHeatStream nodes
        production = ent.get("production") or {}
        for plant in production.get("plants") or []:
            plant_id = str(plant.get("plant_id") or "")
            plant_node = kg.upsert_node(
                "Plant",
                f"{ent_id}:{plant_id}",
                name=f"{ent_id}:{plant_id}",
                props={"enterprise_id": ent_id, "plant_id": plant_id},
                refs=[ref_survey],
            )
            kg.add_edge(ent_node, plant_node, "HAS_PLANT", refs=[ref_survey])

            for ws in plant.get("workshops") or []:
                ws_id = str(ws.get("workshop_id") or "")
                ws_node = kg.upsert_node(
                    "Workshop",
                    f"{ent_id}:{plant_id}:{ws_id}",
                    name=f"{ent_id}:{ws_id}",
                    props={"workshop_id": ws_id},
                    refs=[ref_survey],
                )
                kg.add_edge(plant_node, ws_node, "HAS_WORKSHOP", refs=[ref_survey])

                for line in ws.get("lines") or []:
                    line_id = str(line.get("line_id") or "")
                    line_node = kg.upsert_node(
                        "ProcessLine",
                        f"{ent_id}:{plant_id}:{ws_id}:{line_id}",
                        name=f"{ent_id}:{line_id}",
                        props={"line_id": line_id},
                        refs=[ref_survey],
                    )
                    kg.add_edge(ws_node, line_node, "HAS_LINE", refs=[ref_survey])

                    # Two possible shapes: process_route (list of units) OR units (list)
                    units = []
                    if line.get("process_route"):
                        units = line.get("process_route") or []
                    elif line.get("units"):
                        units = line.get("units") or []

                    for unit in units:
                        unit_id = str(unit.get("unit_id") or "")
                        unit_name = str(unit.get("unit_name") or unit_id)
                        unit_node = kg.upsert_node(
                            "ProcessUnit",
                            f"{ent_id}:{unit_id}",
                            name=unit_name,
                            props={"unit_id": unit_id, "enterprise_id": ent_id, "line_id": line_id},
                            refs=[ref_survey],
                        )
                        kg.add_edge(line_node, unit_node, "HAS_UNIT", refs=[ref_survey])

                        for eq in unit.get("equipment") or []:
                            eq_id = str(eq.get("equipment_id") or "")
                            eq_type = str(eq.get("type") or "equipment")
                            eq_node = kg.upsert_node(
                                "Equipment",
                                f"{ent_id}:{eq_id}",
                                name=f"{eq_type}:{eq_id}",
                                props={
                                    "equipment_id": eq_id,
                                    "equipment_type": eq_type,
                                    "design": eq.get("design") or {},
                                },
                                refs=[ref_survey],
                            )
                            kg.add_edge(unit_node, eq_node, "HAS_EQUIPMENT", refs=[ref_survey])

                            # Energy use -> EnergyDemand nodes
                            energy_use = eq.get("energy_use") or {}
                            carriers = (energy_use.get("carriers") or {})
                            if carriers:
                                demand_node = kg.upsert_node(
                                    "EnergyDemand",
                                    f"{ent_id}:{eq_id}:energy",
                                    name=f"{ent_id}:{eq_id} energy_demand",
                                    props={"carriers": carriers, "time_series": energy_use.get("time_series") or {}},
                                    refs=[ref_survey],
                                )
                                kg.add_edge(eq_node, demand_node, "CONSUMES", refs=[ref_survey])

                            # Byproducts -> WasteHeatStream nodes (if present)
                            byp = eq.get("byproducts") or {}
                            waste_heat = byp.get("waste_heat") or {}
                            for wh in waste_heat.get("sources") or []:
                                wh_id = str(wh.get("source_id") or "")
                                wh_node = kg.upsert_node(
                                    "WasteHeatStream",
                                    f"{ent_id}:{wh_id}",
                                    name=f"waste_heat:{wh_id}",
                                    props=wh,
                                    refs=[ref_survey],
                                )
                                kg.add_edge(eq_node, wh_node, "EMITS_WASTE_HEAT", refs=[ref_survey])

                                # potential external use -> connect to candidate enterprise if exists
                                potential = (wh.get("potential_uses") or {}).get("external") or []
                                for ext in potential:
                                    cand = str(ext.get("candidate") or "").strip()
                                    if not cand:
                                        continue
                                    if cand == "park_heat_loop":
                                        loop_node = kg.upsert_node(
                                            "EnergyNetwork",
                                            "park_heat_loop",
                                            name="园区余热环网（规划）",
                                            props={"status": "planned"},
                                            refs=[ref_survey],
                                        )
                                        kg.add_edge(wh_node, loop_node, "CAN_SUPPLY", props={"use": ext.get("use"), "temp_c": ext.get("temp_c")}, refs=[ref_survey])
                                    else:
                                        dst_node = ent_by_id.get(cand)
                                        if dst_node:
                                            kg.add_edge(
                                                wh_node,
                                                dst_node,
                                                "CAN_SUPPLY",
                                                props={"use": ext.get("use"), "temp_c": ext.get("temp_c"), "est_mw": ext.get("est_mw")},
                                                refs=[ref_survey],
                                            )

    # --- Roof inventory (Denfin crawl) ---
    for row in roof_rows:
        bldg_id = str(row.get("building_id") or "").strip()
        if not bldg_id:
            continue
        owner = str(row.get("owner_enterprise_id") or "").strip()
        bldg_node = kg.upsert_node(
            "Building",
            bldg_id,
            name=str(row.get("building_name") or bldg_id),
            props={
                "building_id": bldg_id,
                "owner_enterprise_id": owner,
                "function": row.get("function"),
                "roof_area_m2": _float_or_none(row.get("roof_area_m2")),
                "roof_type": row.get("roof_type"),
                "roof_age_year": _int_or_none(row.get("roof_age_year")),
                "structure": {"load_limit_kg_m2": _float_or_none(row.get("structure.load_limit_kg_m2"))},
                "solar": {
                    "shading_factor": _float_or_none(row.get("solar.shading_factor")),
                    "slope_deg": _float_or_none(row.get("solar.slope_deg")),
                    "azimuth_deg": _float_or_none(row.get("solar.azimuth_deg")),
                },
                "grid": {"connection_distance_m": _float_or_none(row.get("grid.connection_distance_m"))},
                "fire_code_ok": str(row.get("fire_code_ok")).lower() in ("true", "1", "yes"),
                "geometry_wkt": row.get("geometry_wkt"),
            },
            refs=[ref_roof],
        )
        kg.add_edge(park_node, bldg_node, "HAS_BUILDING", refs=[ref_roof])
        if owner and owner in ent_by_id:
            kg.add_edge(ent_by_id[owner], bldg_node, "OWNS_BUILDING", refs=[ref_roof])

    # --- Enterprise energy monthly (Denfin crawl) ---
    for row in ent_energy_rows:
        ent_id = str(row.get("enterprise_id") or "").strip()
        if not ent_id or ent_id not in ent_by_id:
            continue
        year = _int_or_none(row.get("year")) or 2023
        month = _int_or_none(row.get("month")) or 1
        key = f"{ent_id}:{year}:{month}"
        record_node = kg.upsert_node(
            "EnergyBillRecord",
            key,
            name=f"{ent_id} energy {year}-{month:02d}",
            props={
                "enterprise_id": ent_id,
                "year": year,
                "month": month,
                "electricity_mwh": _float_or_none(row.get("electricity_mwh")),
                "natural_gas_mwh": _float_or_none(row.get("natural_gas_mwh")),
                "steam_mwh": _float_or_none(row.get("steam_mwh")),
                "peak_demand_kw": _float_or_none(row.get("peak_demand_kw")),
                "power_factor_avg": _float_or_none(row.get("power_factor_avg")),
            },
            refs=[ref_ent_energy],
        )
        kg.add_edge(ent_by_id[ent_id], record_node, "HAS_ENERGY_RECORD", refs=[ref_ent_energy])

    # --- Policy docs & clauses (DeFan policy KG) ---
    for doc in policy_extract.get("docs") or []:
        doc_id = str(doc.get("doc_id") or "").strip()
        if not doc_id:
            continue
        doc_node = kg.upsert_node(
            "PolicyDoc",
            doc_id,
            name=str(doc.get("title") or doc_id),
            props=doc,
            refs=[ref_policy],
        )
        kg.add_edge(doc_node, park_node, "RELEVANT_TO", props={"reason": "policy_scope_may_cover_park"}, refs=[ref_policy])

    # Measures nodes (align with existing measure library ids)
    measure_cache: Dict[str, str] = {}
    for clause in policy_extract.get("clauses") or []:
        clause_id = str(clause.get("clause_id") or "").strip()
        if not clause_id:
            continue
        clause_node = kg.upsert_node(
            "PolicyClause",
            clause_id,
            name=clause_id,
            props=clause,
            refs=[ref_policy],
        )
        doc_id = str(clause.get("doc_id") or "").strip()
        if doc_id:
            doc_node = kg.upsert_node(
                "PolicyDoc",
                doc_id,
                name=doc_id,
                props={},
                refs=[ref_policy],
            )
            kg.add_edge(doc_node, clause_node, "HAS_CLAUSE", refs=[ref_policy])

        # clause scoped to admin regions / industries
        for code in clause.get("admin_codes") or []:
            code_str = str(code)
            region_node = kg.upsert_node(
                "AdminRegion",
                code_str,
                name=code_str,
                props={"admin_code": code_str},
                refs=[ref_policy],
            )
            kg.add_edge(clause_node, region_node, "SCOPED_TO", props={"dimension": "admin_code"}, refs=[ref_policy])

        for code in clause.get("industry_codes") or []:
            code_str = str(code)
            industry_node = kg.upsert_node(
                "Industry",
                code_str,
                name=code_str,
                props={"industry_code": code_str},
                refs=[ref_policy],
            )
            kg.add_edge(clause_node, industry_node, "SCOPED_TO", props={"dimension": "industry_code"}, refs=[ref_policy])

        for mid in clause.get("measure_ids") or []:
            mid_str = str(mid)
            measure_node = measure_cache.get(mid_str)
            if not measure_node:
                measure_node = kg.upsert_node(
                    "Measure",
                    mid_str,
                    name=mid_str,
                    props={"measure_id": mid_str},
                    refs=[ref_policy],
                )
                measure_cache[mid_str] = measure_node
            kg.add_edge(clause_node, measure_node, "SUPPORTS", refs=[ref_policy])

    return kg, policy_extract


def export_enriched_policy_kg(kg: KnowledgeGraph, policy_extract: Dict[str, Any]) -> Dict[str, Any]:
    """Export policy KG JSON compatible with PolicyKnowledgeGraph.load_json(), plus extra graph payload."""
    payload: Dict[str, Any] = {
        "kg_version": kg.kg_version,
        "generated_at": utc_now_iso(),
        "notes": kg.notes,
        "docs": policy_extract.get("docs") or [],
        "clauses": policy_extract.get("clauses") or [],
        "graph": kg.to_graph_dict(),
        "sources": {
            "field_survey": "data/mock_sources/field_survey.json",
            "roof_inventory": "data/mock_sources/roof_inventory.csv",
            "enterprise_registry": "data/mock_sources/enterprise_registry.csv",
            "enterprise_energy_monthly_2023": "data/mock_sources/enterprise_energy_monthly_2023.csv",
            "industry_energy_scale": "data/mock_sources/industry_energy_scale.csv",
            "policy_report_extract": "data/mock_sources/policy_report_extract.json",
        },
        "schema_hints": {
            "policy_agent_compatibility": "PolicyKnowledgeGraph.load_json reads only docs/clauses; extra keys are safe.",
            "graph_model": "See multi_enengy_agent/kg/kg_model.py",
        },
    }
    return payload


def write_outputs(
    *,
    source_dir: Path,
    out_policy_kg_path: Path,
    out_full_graph_path: Optional[Path] = None,
) -> Dict[str, Path]:
    kg, policy_extract = build_kg_from_sources(source_dir)

    enriched_policy = export_enriched_policy_kg(kg, policy_extract)
    out_policy_kg_path.parent.mkdir(parents=True, exist_ok=True)
    out_policy_kg_path.write_text(json.dumps(enriched_policy, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs: Dict[str, Path] = {"policy_kg": out_policy_kg_path}

    if out_full_graph_path:
        out_full_graph_path.parent.mkdir(parents=True, exist_ok=True)
        out_full_graph_path.write_text(json.dumps(kg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["full_graph"] = out_full_graph_path

    return outputs


def main() -> None:
    data_dir = resolve_data_dir()
    source_dir = resolve_mock_source_dir()
    out_policy = data_dir / "mock_policy_kg.json"
    out_full = data_dir / "mock_park_policy_graph.json"

    outputs = write_outputs(source_dir=source_dir, out_policy_kg_path=out_policy, out_full_graph_path=out_full)
    print("KG outputs written:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
