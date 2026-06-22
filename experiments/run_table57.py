#!/usr/bin/env python3
"""Run weighted MVC experiments with 5-min hard timeout per graph."""
import json, subprocess, sys, time, os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENV = REPO / ".venv" / "bin" / "python"
SOLVER = REPO / "src" / "mvc-solver-1.5.0"
TIMEOUT = 300  # 5 minutes

GRAPHS = [
    {"name": "K_{2,2}", "n": 4, "edges": [[0,2],[0,3],[1,2],[1,3]], "weights": [1,2,3,4]},
    {"name": "K_{2,3}", "n": 5, "edges": [[0,2],[0,3],[0,4],[1,2],[1,3],[1,4]], "weights": [2,3,1,4,5]},
    {"name": "K_{3,3}", "n": 6, "edges": [[0,3],[0,4],[0,5],[1,3],[1,4],[1,5],[2,3],[2,4],[2,5]], "weights": [5,2,3,1,4,6]},
    {"name": "K_{3,4}", "n": 7, "edges": [[0,3],[0,4],[0,5],[0,6],[1,3],[1,4],[1,5],[1,6],[2,3],[2,4],[2,5],[2,6]], "weights": [3,7,2,5,1,4,6]},
    {"name": "K_{3,5}", "n": 8, "edges": [[0,3],[0,4],[0,5],[0,6],[0,7],[1,3],[1,4],[1,5],[1,6],[1,7],[2,3],[2,4],[2,5],[2,6],[2,7]], "weights": [2,4,6,8,1,3,5,7]},
]

results = []
for g in GRAPHS:
    name = g["name"]
    edges_str = ";".join(f"{u},{v}" for u,v in g["edges"])
    weights_str = ",".join(str(w) for w in g["weights"])
    cmd = [str(VENV), "main.py",
           "--graph-edges", edges_str,
           "--vertex-weights", weights_str,
           "--shots", "1024",
           "--no-barrier", "--skip-k"]
    print(f"\n{'='*60}")
    print(f"Running {name} (n={g['n']}, edges={len(g['edges'])}) timeout={TIMEOUT}s")
    print(f"{'='*60}", flush=True)
    start = time.time()
    try:
        r = subprocess.run(cmd, cwd=str(SOLVER), capture_output=True, text=True, timeout=TIMEOUT)
        elapsed = time.time() - start
        if r.returncode == 0:
            print(f"  OK ({elapsed:.1f}s)")
            # Parse run_summary.json
            summaries = sorted((SOLVER / "outputs").glob("run_*/run_summary.json"))
            if summaries:
                summary = json.loads(summaries[-1].read_text())
                print(f"  Summary: {json.dumps(summary, indent=2)[:500]}")
                results.append({"name": name, "n": g["n"], "edges": len(g["edges"]),
                                "weights": g["weights"], "elapsed": round(elapsed,1),
                                "status": "ok", "summary": summary})
            else:
                # Parse from stdout
                results.append({"name": name, "n": g["n"], "edges": len(g["edges"]),
                                "weights": g["weights"], "elapsed": round(elapsed,1),
                                "status": "ok", "stdout": r.stdout[-2000:]})
        else:
            print(f"  FAIL ({elapsed:.1f}s)")
            print(f"  stderr: {r.stderr[:500]}")
            results.append({"name": name, "n": g["n"], "edges": len(g["edges"]),
                            "weights": g["weights"], "elapsed": round(elapsed,1),
                            "status": "fail", "stderr": r.stderr[:500]})
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"  TIMEOUT ({elapsed:.1f}s) — SKIPPED")
        results.append({"name": name, "n": g["n"], "edges": len(g["edges"]),
                        "weights": g["weights"], "elapsed": round(elapsed,1),
                        "status": "timeout"})

# Write results
out = REPO / "experiments" / "manifests" / "table_5.7_rerun.json"
out.write_text(json.dumps(results, indent=2))
print(f"\n{'='*60}")
print(f"Results written to {out}")
print(f"{'='*60}")
for r in results:
    print(f"  {r['name']}: {r['status']} ({r['elapsed']}s)")
