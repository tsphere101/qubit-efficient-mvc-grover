#!/usr/bin/env python3
"""Generate PROVENANCE.md — master mapping of thesis artifacts to code.

Reads all manifests from experiments/manifests/ and generates
a markdown document mapping every table → manifest, every figure → generator.

Usage:
    python experiments/generate_provenance_map.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = REPO_ROOT / "experiments" / "manifests"
DIAGRAMS_DIR = REPO_ROOT / "diagrams"


def load_manifests() -> list[dict]:
    manifests = []
    for p in sorted(MANIFESTS_DIR.glob("*.json")):
        if p.name == "skipped_graphs.json":
            continue
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict) and "thesis_table" in data:
                manifests.append(data)
        except json.JSONDecodeError:
            print(f"WARNING: could not parse {p}")
    return manifests


def figure_generators() -> list[dict]:
    gens = []
    for p in sorted(DIAGRAMS_DIR.glob("*.py")):
        if p.name in ("__init__.py",):
            continue
        gens.append({
            "script": f"diagrams/{p.name}",
            "name": p.stem,
        })
    return gens


def generate_provenance_md() -> str:
    manifests = load_manifests()
    figures = figure_generators()

    lines = [
        "# Thesis Provenance Map",
        "",
        "Every number, table, figure, and claim in the thesis traces to reproducible code.",
        "",
        "## Tables",
        "",
        "| Table | Manifest | Config | Solver | Method |",
        "|---|---|---|---|---|",
    ]

    for m in manifests:
        table = m.get("thesis_table", "?")
        label = m.get("thesis_label", "")
        solver = m.get("solver", "?")
        method = m.get("input_params", {}).get("method", "?")
        git = m.get("git_commit", "?")[:8]
        lines.append(
            f"| {table} ({label}) | `manifests/table_{table.replace('.', '_')}_manifest.json` | "
            f"`configs/table_{table}*` | {solver} | {method} |"
        )

    lines.extend([
        "",
        "## Figure Generators",
        "",
        "| Generator | Script |",
        "|---|---|",
    ])

    for f in figures:
        lines.append(f"| {f['name']} | `{f['script']}` |")

    lines.extend([
        "",
        "## Environment",
        "",
    ])

    if manifests:
        env = manifests[0].get("environment", {})
        lines.extend([
            "| Package | Version |",
            "|---|---|",
        ])
        for k, v in env.items():
            lines.append(f"| {k} | {v} |")
        lines.append(f"\n**Git commit:** `{manifests[0].get('git_commit', '?')}`")
        lines.append(f"**Branch:** `{manifests[0].get('git_branch', '?')}`")

    lines.append("")
    return "\n".join(lines)


def main():
    md = generate_provenance_md()
    output = REPO_ROOT / "PROVENANCE.md"
    output.write_text(md)
    print(f"Written: {output}")


if __name__ == "__main__":
    main()
