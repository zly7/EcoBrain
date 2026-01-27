from __future__ import annotations

from typing import Any, Dict

from .base import BaseTool

from other_back_data.fhd.interface import FHDMaterializeInput, materialize as fhd_materialize
from other_back_data.lyx.interface import LYXMaterializeInput, materialize as lyx_materialize
from other_back_data.fdf.interface import EcoKGMaterializeInput, EcoKGQueryInput, materialize as eco_materialize, query as eco_query


class LoadFHDBackDataTool(BaseTool):
    name = "load_fhd_back_data"
    description = "Load and profile FHD park directory + AOI into small artifacts for multi_energy_agent."
    InputModel = FHDMaterializeInput
    timeout_s = 120.0

    def _run(self, payload: FHDMaterializeInput) -> Dict[str, Any]:
        return fhd_materialize(payload)


class LoadLYXEnergyScoresTool(BaseTool):
    name = "load_lyx_energy_scores"
    description = "Infer multi-energy demand tendency from LYX industry scoring table."
    InputModel = LYXMaterializeInput
    timeout_s = 60.0

    def _run(self, payload: LYXMaterializeInput) -> Dict[str, Any]:
        return lyx_materialize(payload)


class MaterializeEcoKGTool(BaseTool):
    name = "materialize_eco_knowledge_graph"
    description = "Build a lightweight corpus cache from eco_knowledge_graph/data for retrieval."
    InputModel = EcoKGMaterializeInput
    timeout_s = 120.0

    def _run(self, payload: EcoKGMaterializeInput) -> Dict[str, Any]:
        return eco_materialize(payload)


class QueryEcoKGTool(BaseTool):
    name = "query_eco_knowledge_graph"
    description = "Query the lightweight eco_knowledge_graph corpus cache and return top snippets."
    InputModel = EcoKGQueryInput
    timeout_s = 30.0

    def _run(self, payload: EcoKGQueryInput) -> Dict[str, Any]:
        return eco_query(payload)
