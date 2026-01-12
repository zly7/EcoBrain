"""One-command generator for *mock* KG + sources.

Usage:
    python -m multi_enengy_agent.kg.build_mock_kg

What it does:
1) Generate mock source datasets under multi_enengy_agent/data/mock_sources/
2) Build an integrated graph
3) Export an enriched policy KG to multi_enengy_agent/data/mock_policy_kg.json

After running, the existing MVP pipeline will automatically pick up the new file
because PolicyKnowledgeGraphAgent defaults to that path.
"""

from __future__ import annotations

from pathlib import Path

from .mock_sources import write_mock_sources
from .build_kg import write_outputs


def main() -> None:
    base = Path(__file__).resolve().parents[1]  # multi_enengy_agent/
    data_dir = base / "data"
    source_dir = data_dir / "mock_sources"

    write_mock_sources(source_dir)

    outputs = write_outputs(
        source_dir=source_dir,
        out_policy_kg_path=data_dir / "mock_policy_kg.json",
        out_full_graph_path=data_dir / "mock_park_policy_graph.json",
    )

    print("Done. Files:")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
