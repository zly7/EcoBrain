"""FDF back-data adapter: eco_knowledge_graph lightweight interface."""

from .interface import materialize, query, EcoKGMaterializeInput, EcoKGQueryInput

__all__ = ["materialize", "query", "EcoKGMaterializeInput", "EcoKGQueryInput"]
