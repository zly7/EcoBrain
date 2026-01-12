"""A tiny, dependency-free knowledge graph model.

Why this exists:
- DeFan needs to fuse survey/crawled/indicator/policy data into one KG.
- XieLinGuo's agent currently consumes a simplified "policy KG" JSON (docs+clauses).
- We keep compatibility by exporting docs+clauses while also persisting full nodes/edges.

Design principles:
- Deterministic IDs via (node_type, external_key) upsert index.
- Provenance-first: every node/edge can carry refs (where did it come from?).
- JSON-first: the whole graph can be persisted as JSON without external DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    safe = "".join(ch for ch in prefix.upper() if ch.isalnum())
    return f"{safe}_{uuid4().hex[:10]}"


@dataclass
class KGRef:
    """Lightweight provenance reference."""
    source: str
    uri: Optional[str] = None
    retrieved_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KGNode:
    id: str
    type: str
    name: str
    props: Dict[str, Any] = field(default_factory=dict)
    refs: List[KGRef] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "props": self.props,
            "refs": [ref.to_dict() for ref in self.refs],
        }


@dataclass
class KGEdge:
    id: str
    source: str
    target: str
    type: str
    props: Dict[str, Any] = field(default_factory=dict)
    refs: List[KGRef] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "props": self.props,
            "refs": [ref.to_dict() for ref in self.refs],
        }


@dataclass
class KnowledgeGraph:
    """In-memory knowledge graph with deterministic upsert capability."""

    kg_version: str
    generated_at: str = field(default_factory=utc_now_iso)
    notes: str = ""
    nodes: Dict[str, KGNode] = field(default_factory=dict)
    edges: List[KGEdge] = field(default_factory=list)

    # Internal indices (not serialized)
    _upsert_index: Dict[Tuple[str, str], str] = field(default_factory=dict, repr=False)

    def upsert_node(
        self,
        node_type: str,
        external_key: str,
        *,
        name: str,
        props: Optional[Dict[str, Any]] = None,
        refs: Optional[Iterable[KGRef]] = None,
    ) -> str:
        """Create or update a node by (type, external_key).

        external_key should be stable across datasets (e.g., enterprise_id, admin_code, doc_id).
        """
        key = (str(node_type), str(external_key))
        if key in self._upsert_index:
            node_id = self._upsert_index[key]
            node = self.nodes[node_id]
            if name and (not node.name or node.name == node.id):
                node.name = name
            if props:
                node.props.update(props)
            if refs:
                node.refs.extend(list(refs))
            return node_id

        node_id = _new_id(node_type)
        node = KGNode(
            id=node_id,
            type=str(node_type),
            name=name,
            props=dict(props or {}),
            refs=list(refs or []),
        )
        self.nodes[node_id] = node
        self._upsert_index[key] = node_id
        return node_id

    def add_edge(
        self,
        source: str,
        target: str,
        rel_type: str,
        *,
        props: Optional[Dict[str, Any]] = None,
        refs: Optional[Iterable[KGRef]] = None,
    ) -> str:
        edge_id = _new_id(rel_type)
        self.edges.append(
            KGEdge(
                id=edge_id,
                source=source,
                target=target,
                type=str(rel_type),
                props=dict(props or {}),
                refs=list(refs or []),
            )
        )
        return edge_id

    def to_graph_dict(self) -> Dict[str, Any]:
        """Serialize only the graph (nodes+edges)."""
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize header + graph."""
        return {
            "kg_version": self.kg_version,
            "generated_at": self.generated_at,
            "notes": self.notes,
            "graph": self.to_graph_dict(),
        }
