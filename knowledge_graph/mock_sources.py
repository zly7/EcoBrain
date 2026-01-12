"""Generate very detailed *mock* data for early integration.

This file simulates outputs from:
1) 张子辰 / 陈：现场调研（政府/园区/企业需求、工艺、能耗、余热/副产品等）
2) Denfin：数据爬取（屋顶面积/楼栋、企业清单、月度能耗等）
3) 林洛西：指标层数据（产业清单与能耗量级表、典型参数等）

The goal is not realism; it's to create:
- deep nested JSON (>= 6 layers)
- complex CSVs
so downstream KG + agent pipelines can be debugged without real data.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def generate_field_survey_json() -> Dict[str, Any]:
    today = date.today().isoformat()
    return {
        "survey_meta": {
            "survey_id": "SURVEY_2026_01_DEMO",
            "date": today,
            "team": [
                {"name": "张子辰", "role": "现场调研负责人", "org": "咨询团队A"},
                {"name": "陈_重_打_击", "role": "调研协助", "org": "咨询团队A"},
            ],
            "methodology": {
                "instruments": [
                    {"type": "interview", "count": 18, "units": ["government", "park_operator", "enterprise"]},
                    {"type": "site_walkthrough", "count": 6, "units": ["substation", "boiler_house", "cooling_tower"]},
                    {"type": "document_review", "count": 12, "units": ["policies", "EIA", "energy_bills"]},
                ],
                "data_quality": {
                    "completeness": 0.62,
                    "confidence_notes": "部分企业仅提供区间值；蒸汽/余热曲线为典型工况推断。",
                    "known_gaps": [
                        {"missing": "hourly_load_profile", "owner": "park_operator", "severity": "high"},
                        {"missing": "steam_network_map", "owner": "park_operator", "severity": "medium"},
                        {"missing": "roof_structural_load_test", "owner": "3 buildings", "severity": "medium"},
                    ],
                },
            },
        },
        "park": {
            "basic": {
                "region_id": "cn-suzhou-industrial-park",
                "name": "示例产业园（虚拟-苏州）",
                "admin": {"codes": ["320500", "320571"], "province": "江苏省", "city": "苏州市"},
                "location": {"center": {"lat": 31.310, "lon": 120.705}, "area_km2": 15.3},
                "land_use": {
                    "industrial": {"area_km2": 8.1, "dominant": ["C26", "C30", "C34"]},
                    "logistics": {"area_km2": 1.8},
                    "office": {"area_km2": 2.2},
                    "green": {"area_km2": 1.1},
                    "other": {"area_km2": 2.1},
                },
                "operator": {"org_name": "示例园区运营公司（虚拟）", "contact": {"name": "王某", "phone": "13800000000"}},
            },
            "infrastructure": {
                "electricity": {
                    "grid_company": "国网（虚拟）",
                    "substations": [
                        {
                            "substation_id": "SS_110kV_01",
                            "voltage_kv": 110,
                            "transformers": [
                                {"transformer_id": "TR_01", "capacity_mva": 63, "spare_ratio": 0.18},
                                {"transformer_id": "TR_02", "capacity_mva": 63, "spare_ratio": 0.22},
                            ],
                            "reliability": {"saidi_min_per_year": 25, "saifi_times_per_year": 0.6},
                        }
                    ],
                    "tariff": {
                        "tou": {
                            "peak_cny_per_kwh": 1.25,
                            "flat_cny_per_kwh": 0.82,
                            "valley_cny_per_kwh": 0.42,
                            "demand_charge_cny_per_kw_month": 30,
                        }
                    },
                },
                "natural_gas": {
                    "pipeline_pressure_mpa": 0.4,
                    "capacity_nm3_per_h": 18000,
                    "price_cny_per_nm3": 3.2,
                    "backup_fuel": ["diesel"],
                },
                "steam_network": {
                    "status": "partial",
                    "steam_grade": {
                        "medium_pressure": {"pressure_mpa": 1.0, "temp_c": 185},
                        "low_pressure": {"pressure_mpa": 0.4, "temp_c": 151},
                    },
                    "network_map": {"available": False, "reason": "运营方暂未提供CAD管网资料"},
                },
                "hydrogen": {
                    "status": "pilot",
                    "h2_station": {"count": 1, "pressure_mpa": 35, "daily_capacity_kg": 800},
                    "pipeline": {"available": False},
                },
                "waste_heat": {
                    "shared_loop": {"available": False, "note": "目前无统一热网；以企业点对点为主"},
                    "temperature_levels_c": [45, 70, 120, 180],
                },
            },
            "stakeholders": {
                "government": {
                    "org_name": "示例发改委/工信局（虚拟）",
                    "needs": {
                        "kpi_targets": {
                            "carbon": {
                                "target": {
                                    "year": 2030,
                                    "type": "relative_reduction",
                                    "value": 0.35,
                                    "baseline_year": 2023,
                                },
                                "audit_chain": {
                                    "required": True,
                                    "tools": {"MRV": ["计量表计", "第三方核查"], "data_platform": ["园区能管平台"]},
                                },
                            },
                            "energy": {
                                "energy_intensity_reduction": {
                                    "year": 2028,
                                    "value": 0.18,
                                    "unit": "MWh/产值",
                                    "sector_priority": ["C26", "C30"],
                                }
                            },
                            "investment": {
                                "招商引资": {
                                    "target_industries": [
                                        {"industry_code": "C34", "reason": "高端装备+电气化潜力"},
                                        {"industry_code": "C39", "reason": "电子信息产业集群"},
                                    ],
                                    "required_materials": {
                                        "investment_case": {
                                            "include": [
                                                "能源成本对比",
                                                "碳排指标可得性",
                                                "绿电/绿证路径",
                                                "余热/蒸汽供应稳定性",
                                            ],
                                            "format": {"dashboard": True, "report": True, "sankey": True},
                                        }
                                    },
                                }
                            },
                        },
                        "policy_constraints": {
                            "red_lines": {
                                "energy_consumption_cap": {"value": 2.8, "unit": "TWh/year", "type": "hard"},
                                "coal_control": {"new_coal_boiler": "prohibited"},
                            },
                            "approval": {
                                "eia_required": True,
                                "grid_connection_process": {"owner": "grid_company", "typical_days": 45},
                            },
                        },
                    },
                },
                "park_operator": {
                    "org_name": "示例园区运营公司（虚拟）",
                    "needs": {
                        "cost": {
                            "pain_points": [
                                {"item": "尖峰电价", "impact": "用电成本高", "priority": "high"},
                                {"item": "蒸汽价格波动", "impact": "部分企业外购蒸汽不稳定", "priority": "medium"},
                            ],
                            "targets": {
                                "opex_reduction_pct": {"value": 0.08, "year": 2027},
                                "energy_management": {"platform_upgrade": True},
                            },
                        },
                        "carbon": {"wants": ["统一核算口径", "可解释的减排拆解", "对外招商材料"]},
                        "data": {
                            "available": [
                                {"dataset": "企业名录", "format": "csv", "update": "quarterly"},
                                {"dataset": "电力总表", "format": "monthly", "update": "monthly"},
                            ],
                            "restricted": [
                                {"dataset": "企业分表", "reason": "商业敏感", "access": "需签NDA"},
                            ],
                        },
                    },
                },
                "enterprises": [
                    {
                        "enterprise_profile": {
                            "enterprise_id": "ENT_001",
                            "name": "苏澄精细化工（虚拟）",
                            "industry_code": "C26",
                            "employees": 820,
                            "output_value_million_cny": 2200,
                            "main_products": ["溶剂", "树脂", "功能助剂"],
                            "site": {
                                "land_area_m2": 120000,
                                "buildings": [
                                    {"building_id": "B001", "name": "合成车间", "floors": 3},
                                    {"building_id": "B002", "name": "仓储与装卸", "floors": 1},
                                ],
                            },
                        },
                        "production": {
                            "plants": [
                                {
                                    "plant_id": "PLANT_A",
                                    "workshops": [
                                        {
                                            "workshop_id": "WS_A1",
                                            "lines": [
                                                {
                                                    "line_id": "LINE_A1_01",
                                                    "process_route": [
                                                        {
                                                            "unit_id": "UNIT_A1_01_REACT",
                                                            "unit_name": "反应釜组",
                                                            "equipment": [
                                                                {
                                                                    "equipment_id": "EQ_REACTOR_01",
                                                                    "type": "reactor",
                                                                    "design": {
                                                                        "volume_m3": 25,
                                                                        "jacket": {
                                                                            "heat_medium": "steam",
                                                                            "max_temp_c": 200,
                                                                            "heat_transfer_area_m2": 42,
                                                                        },
                                                                    },
                                                                    "energy_use": {
                                                                        "carriers": {
                                                                            "electricity": {
                                                                                "avg_kw": 180,
                                                                                "peak_kw": 260,
                                                                                "meter": {"id": "MTR_E_001", "accuracy": "0.5S"},
                                                                            },
                                                                            "steam": {
                                                                                "avg_tph": 6.5,
                                                                                "pressure_mpa": 1.0,
                                                                                "temperature_c": 185,
                                                                                "meter": {"id": "MTR_S_001", "accuracy": "1.0"},
                                                                            },
                                                                            "natural_gas": {
                                                                                "avg_nm3_h": 0,
                                                                                "note": "主要蒸汽外购/自备锅炉",
                                                                            },
                                                                        },
                                                                        "time_series": {
                                                                            "resolution": "hour",
                                                                            "profiles": {
                                                                                "weekday": {
                                                                                    "hourly_kw": [
                                                                                        160,
                                                                                        150,
                                                                                        145,
                                                                                        142,
                                                                                        140,
                                                                                        150,
                                                                                        175,
                                                                                        200,
                                                                                        220,
                                                                                        240,
                                                                                        250,
                                                                                        255,
                                                                                        260,
                                                                                        255,
                                                                                        250,
                                                                                        245,
                                                                                        240,
                                                                                        235,
                                                                                        230,
                                                                                        220,
                                                                                        210,
                                                                                        195,
                                                                                        180,
                                                                                        170,
                                                                                    ],
                                                                                    "notes": {
                                                                                        "seasonality": {
                                                                                            "winter": {"steam_tph_multiplier": 1.08},
                                                                                            "summer": {"cooling_kw_multiplier": 1.12},
                                                                                        }
                                                                                    },
                                                                                }
                                                                            },
                                                                        },
                                                                    },
                                                                    "byproducts": {
                                                                        "waste_heat": {
                                                                            "sources": [
                                                                                {
                                                                                    "source_id": "WH_A1_01",
                                                                                    "type": "cooling_water",
                                                                                    "temp_in_c": 38,
                                                                                    "temp_out_c": 55,
                                                                                    "flow_m3_h": 620,
                                                                                    "available_mw": 2.6,
                                                                                    "availability": {
                                                                                        "schedule": {"weekday": 0.85, "weekend": 0.6},
                                                                                        "constraints": {"shutdown_days_per_year": 12},
                                                                                    },
                                                                                    "potential_uses": {
                                                                                        "internal": [
                                                                                            {"use": "热泵提温供洗涤", "temp_c": 70, "est_mw": 1.2},
                                                                                            {"use": "工艺预热", "temp_c": 60, "est_mw": 0.6},
                                                                                        ],
                                                                                        "external": [
                                                                                            {"candidate": "ENT_003", "use": "清洗热水", "temp_c": 50, "est_mw": 0.4}
                                                                                        ],
                                                                                    },
                                                                                }
                                                                            ],
                                                                            "measurement": {"method": "spot_measurement+design_doc", "confidence": 0.55},
                                                                        },
                                                                        "offgas": {
                                                                            "streams": [
                                                                                {
                                                                                    "stream_id": "OG_A1_01",
                                                                                    "composition": {"VOC": "low", "CO2_pct": 4.0},
                                                                                    "temp_c": 120,
                                                                                    "flow_nm3_h": 900,
                                                                                    "treatment": {"current": "RTO", "waste_heat_recovery": "none"},
                                                                                }
                                                                            ]
                                                                        },
                                                                    },
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                            "utilities": {
                                "boilers": [
                                    {
                                        "boiler_id": "BLR_01",
                                        "fuel": "natural_gas",
                                        "capacity_tph": 20,
                                        "efficiency": {"design": 0.90, "measured": 0.86},
                                        "flue_gas": {
                                            "temp_c": 165,
                                            "waste_heat_potential_mw": 1.1,
                                            "recovery_options": {"economizer": True, "condensing": "possible"},
                                        },
                                    }
                                ],
                                "cooling_towers": [{"id": "CT_01", "capacity_m3_h": 1800, "pump_kw": 320}],
                            },
                        },
                        "needs": {
                            "capex_budget_million_cny": 25,
                            "preferred_measures": [
                                {"measure_id": "WASTE_HEAT", "reason": "有稳定余热源"},
                                {"measure_id": "EE_MOTOR", "reason": "泵/风机多"},
                            ],
                            "constraints": {
                                "production_continuity": "must_keep",
                                "shutdown_window_days": 7,
                                "safety": {"hot_work": "permit_required"},
                            },
                        },
                    },
                    {
                        "enterprise_profile": {
                            "enterprise_id": "ENT_002",
                            "name": "新材非金属制品（虚拟）",
                            "industry_code": "C30",
                            "employees": 460,
                            "output_value_million_cny": 980,
                            "main_products": ["高性能陶瓷基板", "耐磨衬板"],
                            "site": {"land_area_m2": 86000, "buildings": [{"building_id": "B101", "name": "烧结车间"}]},
                        },
                        "production": {
                            "plants": [
                                {
                                    "plant_id": "PLANT_B",
                                    "workshops": [
                                        {
                                            "workshop_id": "WS_B1",
                                            "lines": [
                                                {
                                                    "line_id": "LINE_B1_01",
                                                    "units": [
                                                        {
                                                            "unit_id": "UNIT_B1_KILN",
                                                            "unit_name": "电窑炉",
                                                            "equipment": [
                                                                {
                                                                    "equipment_id": "EQ_KILN_01",
                                                                    "type": "electric_kiln",
                                                                    "energy_use": {
                                                                        "carriers": {
                                                                            "electricity": {"avg_kw": 820, "peak_kw": 1100},
                                                                        },
                                                                        "time_series": {
                                                                            "resolution": "hour",
                                                                            "profiles": {"weekday": {"hourly_kw": [700] * 24}},
                                                                        },
                                                                    },
                                                                    "byproducts": {
                                                                        "waste_heat": {
                                                                            "sources": [
                                                                                {
                                                                                    "source_id": "WH_B1_01",
                                                                                    "type": "flue_gas",
                                                                                    "temp_c": 260,
                                                                                    "available_mw": 3.4,
                                                                                    "potential_uses": {
                                                                                        "internal": [
                                                                                            {"use": "烘干预热", "temp_c": 120, "est_mw": 1.0}
                                                                                        ],
                                                                                        "external": [
                                                                                            {"candidate": "park_heat_loop", "use": "区域供热", "temp_c": 80, "est_mw": 1.2}
                                                                                        ],
                                                                                    },
                                                                                }
                                                                            ]
                                                                        }
                                                                    },
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ]
                        },
                        "needs": {
                            "capex_budget_million_cny": 18,
                            "preferred_measures": [
                                {"measure_id": "WASTE_HEAT", "reason": "高温烟气余热"},
                                {"measure_id": "BESS_TOU", "reason": "电窑负荷高，削峰潜力"},
                            ],
                            "constraints": {"quality": "strict_temperature_control"},
                        },
                    },
                    {
                        "enterprise_profile": {
                            "enterprise_id": "ENT_003",
                            "name": "高端装备零部件（虚拟）",
                            "industry_code": "C34",
                            "employees": 310,
                            "output_value_million_cny": 760,
                            "main_products": ["精密轴承", "伺服部件"],
                            "site": {"land_area_m2": 54000, "buildings": [{"building_id": "B201", "name": "机加车间"}]},
                        },
                        "production": {
                            "plants": [
                                {
                                    "plant_id": "PLANT_C",
                                    "workshops": [
                                        {
                                            "workshop_id": "WS_C1",
                                            "lines": [
                                                {
                                                    "line_id": "LINE_C1_01",
                                                    "units": [
                                                        {
                                                            "unit_id": "UNIT_C1_CNC",
                                                            "unit_name": "CNC加工单元",
                                                            "equipment": [
                                                                {
                                                                    "equipment_id": "EQ_CNC_01",
                                                                    "type": "cnc_machine",
                                                                    "energy_use": {
                                                                        "carriers": {"electricity": {"avg_kw": 65, "peak_kw": 95}},
                                                                        "time_series": {
                                                                            "resolution": "hour",
                                                                            "profiles": {"weekday": {"hourly_kw": [55, 50, 50] + [60] * 18 + [58, 55, 52]}},
                                                                        },
                                                                    },
                                                                }
                                                            ],
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ]
                        },
                        "needs": {
                            "capex_budget_million_cny": 9,
                            "preferred_measures": [{"measure_id": "EE_MOTOR", "reason": "空压/循环水系统"}],
                            "constraints": {"space": "limited_roof_area"},
                        },
                    },
                ],
            },
        },
    }


def generate_roof_inventory_rows() -> List[Dict[str, Any]]:
    return [
        {
            "building_id": "BLDG_001",
            "building_name": "A区-1号厂房",
            "owner_enterprise_id": "ENT_001",
            "function": "生产",
            "roof_area_m2": 28000,
            "roof_type": "metal",
            "roof_age_year": 6,
            "structure.load_limit_kg_m2": 32,
            "solar.shading_factor": 0.08,
            "solar.slope_deg": 8,
            "solar.azimuth_deg": 190,
            "grid.connection_distance_m": 120,
            "fire_code_ok": True,
            "geometry_wkt": "POLYGON((120.700 31.309,120.701 31.309,120.701 31.310,120.700 31.310,120.700 31.309))",
        },
        {
            "building_id": "BLDG_002",
            "building_name": "A区-2号仓库",
            "owner_enterprise_id": "ENT_001",
            "function": "仓储",
            "roof_area_m2": 16000,
            "roof_type": "concrete",
            "roof_age_year": 12,
            "structure.load_limit_kg_m2": 25,
            "solar.shading_factor": 0.12,
            "solar.slope_deg": 2,
            "solar.azimuth_deg": 175,
            "grid.connection_distance_m": 80,
            "fire_code_ok": True,
            "geometry_wkt": "POLYGON((120.702 31.309,120.703 31.309,120.703 31.310,120.702 31.310,120.702 31.309))",
        },
        {
            "building_id": "BLDG_101",
            "building_name": "B区-烧结车间",
            "owner_enterprise_id": "ENT_002",
            "function": "生产",
            "roof_area_m2": 34000,
            "roof_type": "metal",
            "roof_age_year": 4,
            "structure.load_limit_kg_m2": 30,
            "solar.shading_factor": 0.05,
            "solar.slope_deg": 6,
            "solar.azimuth_deg": 200,
            "grid.connection_distance_m": 160,
            "fire_code_ok": False,
            "fire_issue": "屋顶采光带需整改后方可施工",
            "geometry_wkt": "POLYGON((120.706 31.312,120.707 31.312,120.707 31.313,120.706 31.313,120.706 31.312))",
        },
        {
            "building_id": "BLDG_201",
            "building_name": "C区-机加车间",
            "owner_enterprise_id": "ENT_003",
            "function": "生产",
            "roof_area_m2": 12000,
            "roof_type": "metal",
            "roof_age_year": 9,
            "structure.load_limit_kg_m2": 28,
            "solar.shading_factor": 0.10,
            "solar.slope_deg": 10,
            "solar.azimuth_deg": 185,
            "grid.connection_distance_m": 60,
            "fire_code_ok": True,
            "geometry_wkt": "POLYGON((120.709 31.308,120.710 31.308,120.710 31.309,120.709 31.309,120.709 31.308))",
        },
    ]


def generate_enterprise_registry_rows() -> List[Dict[str, Any]]:
    return [
        {
            "enterprise_id": "ENT_001",
            "name": "苏澄精细化工（虚拟）",
            "industry_code": "C26",
            "employees": 820,
            "output_value_million_cny": 2200,
            "has_boiler": True,
            "has_waste_heat": True,
            "has_roof_pv_ready": True,
            "notes": "余热以冷却水为主；锅炉效率偏低",
        },
        {
            "enterprise_id": "ENT_002",
            "name": "新材非金属制品（虚拟）",
            "industry_code": "C30",
            "employees": 460,
            "output_value_million_cny": 980,
            "has_boiler": False,
            "has_waste_heat": True,
            "has_roof_pv_ready": False,
            "notes": "电窑负荷高，适合储能+余热",
        },
        {
            "enterprise_id": "ENT_003",
            "name": "高端装备零部件（虚拟）",
            "industry_code": "C34",
            "employees": 310,
            "output_value_million_cny": 760,
            "has_boiler": False,
            "has_waste_heat": "low_grade",
            "has_roof_pv_ready": True,
            "notes": "电机系统改造潜力较大",
        },
    ]


def generate_enterprise_energy_monthly_rows() -> List[Dict[str, Any]]:
    # Monthly simplified numbers (MWh); purely mock.
    rows: List[Dict[str, Any]] = []
    for ent_id, base_e, base_g in [("ENT_001", 980, 620), ("ENT_002", 1320, 120), ("ENT_003", 420, 60)]:
        for month in range(1, 13):
            season = 1.15 if month in (7, 8) else 1.0
            electricity = round(base_e * season * (0.92 + month / 200), 2)
            gas = round(base_g * (0.95 + month / 300), 2)
            rows.append(
                {
                    "enterprise_id": ent_id,
                    "year": 2023,
                    "month": month,
                    "electricity_mwh": electricity,
                    "natural_gas_mwh": gas,
                    "steam_mwh": round((gas * 0.65) if ent_id == "ENT_001" else (gas * 0.15), 2),
                    "peak_demand_kw": int(1200 if ent_id == "ENT_002" else 650),
                    "power_factor_avg": 0.92 if ent_id == "ENT_002" else 0.96,
                }
            )
    return rows


def generate_industry_energy_scale_rows() -> List[Dict[str, Any]]:
    return [
        {
            "industry_code": "C26",
            "industry_name": "化学原料和化学制品制造业（示例）",
            "electricity_mwh_per_billion_output": 5200,
            "thermal_mwh_per_billion_output": 6800,
            "waste_heat_grade": "low_to_mid",
            "waste_heat_potential_mwh_per_billion_output": 1100,
            "common_measures": "WASTE_HEAT|EE_MOTOR|PV_ROOF",
            "investment_priority_hint": "副产物/余热耦合空间大，适合构建园区能量梯级利用示范",
        },
        {
            "industry_code": "C30",
            "industry_name": "非金属矿物制品业（示例）",
            "electricity_mwh_per_billion_output": 7600,
            "thermal_mwh_per_billion_output": 2400,
            "waste_heat_grade": "mid_to_high",
            "waste_heat_potential_mwh_per_billion_output": 1900,
            "common_measures": "WASTE_HEAT|BESS_TOU|PV_ROOF",
            "investment_priority_hint": "窑炉负荷+余热，适合热泵/ORC/储能联合",
        },
        {
            "industry_code": "C34",
            "industry_name": "通用设备制造业（示例）",
            "electricity_mwh_per_billion_output": 3200,
            "thermal_mwh_per_billion_output": 800,
            "waste_heat_grade": "low",
            "waste_heat_potential_mwh_per_billion_output": 250,
            "common_measures": "EE_MOTOR|PV_ROOF|BESS_TOU",
            "investment_priority_hint": "电气化程度高，可作为绿电消纳+储能示范",
        },
    ]


def generate_policy_report_extract() -> Dict[str, Any]:
    # Policy docs/clauses are fictional, structured to fit existing policy_kg schema.
    return {
        "docs": [
            {
                "doc_id": "DOC_SUZ_2025_ZCIP_01",
                "title": "苏州市零碳园区试点支持政策（虚拟）",
                "issuer": "苏州市发改委（虚拟）",
                "effective_date": "2025-01-01",
                "uri": "internal://policy/DOC_SUZ_2025_ZCIP_01",
            },
            {
                "doc_id": "DOC_SUZ_2024_EE_02",
                "title": "工业节能与绿色改造奖励办法（虚拟）",
                "issuer": "苏州市工信局（虚拟）",
                "effective_date": "2024-06-01",
                "uri": "internal://policy/DOC_SUZ_2024_EE_02",
            },
            {
                "doc_id": "DOC_JS_2025_POWER_03",
                "title": "江苏省用户侧储能与削峰响应支持细则（虚拟）",
                "issuer": "江苏省能源局（虚拟）",
                "effective_date": "2025-03-01",
                "uri": "internal://policy/DOC_JS_2025_POWER_03",
            },
        ],
        "clauses": [
            {
                "clause_id": "DOC_SUZ_2025_ZCIP_01_C01",
                "doc_id": "DOC_SUZ_2025_ZCIP_01",
                "citation_no": "[ZCIP-1]",
                "effective_date": "2025-01-01",
                "excerpt": "对园区屋顶光伏项目按投资额给予10%一次性补贴，单园区最高不超过200万元。",
                "admin_codes": ["320500"],  # only city-level; should still match district codes via hierarchy
                "industry_codes": [],
                "measure_ids": ["PV_ROOF"],
                "analysis_points": ["PV_SUBSIDY", "GRID_CONNECTION_FAST_TRACK"],
                "incentives": {"capex_subsidy_pct": 0.10, "capex_subsidy_cap_million_cny": 2.0},
                "eligibility": {"min_roof_area_m2": 5000, "requirement": ["并网验收", "消防合规"]},
            },
            {
                "clause_id": "DOC_SUZ_2025_ZCIP_01_C02",
                "doc_id": "DOC_SUZ_2025_ZCIP_01",
                "citation_no": "[ZCIP-2]",
                "effective_date": "2025-01-01",
                "excerpt": "对工业余热回收与热泵耦合改造按投资额给予15%补贴，单项目最高不超过300万元。",
                "admin_codes": ["320500"],
                "industry_codes": ["C26", "C30"],
                "measure_ids": ["WASTE_HEAT"],
                "analysis_points": ["WASTE_HEAT_SUPPORT", "HEAT_PUMP_COUPLING"],
                "incentives": {"capex_subsidy_pct": 0.15, "capex_subsidy_cap_million_cny": 3.0},
                "eligibility": {"min_available_waste_heat_mw": 0.8, "temperature_c_min": 35},
            },
            {
                "clause_id": "DOC_SUZ_2024_EE_02_C01",
                "doc_id": "DOC_SUZ_2024_EE_02",
                "citation_no": "[EE-1]",
                "effective_date": "2024-06-01",
                "excerpt": "对高效电机与变频改造项目按投资额给予8%补贴，单项目最高不超过120万元。",
                "admin_codes": ["320500"],
                "industry_codes": ["C26", "C30", "C34"],
                "measure_ids": ["EE_MOTOR"],
                "analysis_points": ["MOTOR_EFFICIENCY", "VFD_RETROFIT"],
                "incentives": {"capex_subsidy_pct": 0.08, "capex_subsidy_cap_million_cny": 1.2},
                "eligibility": {"min_motor_count": 20, "min_operating_hours_per_year": 3000},
            },
            {
                "clause_id": "DOC_JS_2025_POWER_03_C01",
                "doc_id": "DOC_JS_2025_POWER_03",
                "citation_no": "[BESS-1]",
                "effective_date": "2025-03-01",
                "excerpt": "对用户侧储能项目按投资额给予12%补贴，单项目最高不超过500万元；参与削峰响应可叠加运营补贴。",
                "admin_codes": ["320000"],  # province-level
                "industry_codes": [],
                "measure_ids": ["BESS_TOU"],
                "analysis_points": ["BESS_CAPEX", "DEMAND_RESPONSE"],
                "incentives": {"capex_subsidy_pct": 0.12, "capex_subsidy_cap_million_cny": 5.0},
                "eligibility": {"min_power_mw": 1.0, "min_duration_h": 2, "grid_agreement": "required"},
            },
        ],
    }


def write_mock_sources(out_dir: Path) -> Dict[str, Path]:
    """Write all mock sources under out_dir and return a mapping of dataset names -> paths."""
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, Path] = {}

    field_survey_path = out_dir / "field_survey.json"
    _write_json(field_survey_path, generate_field_survey_json())
    paths["field_survey"] = field_survey_path

    roof_csv_path = out_dir / "roof_inventory.csv"
    _write_csv(roof_csv_path, generate_roof_inventory_rows())
    paths["roof_inventory"] = roof_csv_path

    ent_reg_path = out_dir / "enterprise_registry.csv"
    _write_csv(ent_reg_path, generate_enterprise_registry_rows())
    paths["enterprise_registry"] = ent_reg_path

    ent_energy_path = out_dir / "enterprise_energy_monthly_2023.csv"
    _write_csv(ent_energy_path, generate_enterprise_energy_monthly_rows())
    paths["enterprise_energy_monthly"] = ent_energy_path

    industry_scale_path = out_dir / "industry_energy_scale.csv"
    _write_csv(industry_scale_path, generate_industry_energy_scale_rows())
    paths["industry_energy_scale"] = industry_scale_path

    policy_extract_path = out_dir / "policy_report_extract.json"
    _write_json(policy_extract_path, generate_policy_report_extract())
    paths["policy_report_extract"] = policy_extract_path

    return paths


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    out_dir = base / "data" / "mock_sources"
    mapping = write_mock_sources(out_dir)
    print("Mock sources written:")
    for name, path in mapping.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
