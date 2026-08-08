#!/usr/bin/env bash
# ============================================================================
# MVC Grover Experiment Suite — Parallel Batch Runner
# ============================================================================
# Runs 27 graphs × 2 solvers (Arithmetic v1.3.0 + Dicke v1.4.0) = 54 jobs.
# Uses 4-way parallelism with progress reporting.
# Auto-copies results to ~/Desktop/all-graph/{arithmetic,dicke}/.
# ============================================================================

set -e

# ---------- Configuration ----------
REPO="${REPO:-/Users/topfee/Desktop/qubit-efficient-mvc-grover}"
ARITH_DIR="$REPO/src/mvc-solver-1.3.0"
DICKE_DIR="$REPO/src/mvc-solver-1.4.0"
VENV="${VENV:-$REPO/.venv/bin/activate}"
DEST="${DEST:-$HOME/Desktop/all-graph}"
JOBS_DIR="/tmp/mvc_jobs"
LOG_DIR="/tmp/mvc_logs"
PARALLEL_JOBS="${PARALLEL_JOBS:-4}"

mkdir -p "$DEST/arithmetic" "$DEST/dicke" "$JOBS_DIR" "$LOG_DIR"

# ---------- Graph definitions: name|edges|pivots ----------
# Each graph: name, edge list (semicolon-separated "u,v" pairs), pivot list
# Pivots run from (n+1) down to mvc (overshoot by 1 is intentional — see docs)
GRAPHS=(
  "P3_path|0,1;1,2|4,3,2,1"
  "C3_triangle|0,1;1,2;2,0|4,3,2"
  "P4_path|0,1;1,2;2,3|5,4,3,2"
  "star_K1_3|0,1;0,2;0,3|5,4,3,2,1"
  "P3_plus_leaf|0,1;1,2;2,0;0,3|5,4,3,2"
  "C4_cycle|0,1;1,2;2,3;3,0|5,4,3,2"
  "diamond_graph|0,1;1,2;2,0;0,3;1,3|5,4,3,2"
  "K4_complete|0,1;0,2;0,3;1,2;1,3;2,3|5,4,3"
  "P5_path|0,1;1,2;2,3;3,4|6,5,4,3,2"
  "K1_4_star|0,1;0,2;0,3;0,4|6,5,4,3,2,1"
  "fork_tree|0,1;0,2;0,3;1,4|6,5,4,3,2"
  "double_fork_tree|0,1;0,2;1,3;1,4|6,5,4,3,2"
  "C5_cycle|0,1;1,2;2,3;3,4;4,0|6,5,4,3"
  "C4_plus_leaf|0,1;1,2;2,3;3,0;0,4|6,5,4,3,2"
  "triangle_path|0,1;1,2;2,0;0,3;3,4|6,5,4,3"
  "triangle_double_leaf|0,1;1,2;2,0;0,3;1,4|6,5,4,3,2"
  "C4_chord_leaf|0,1;1,2;2,3;3,0;0,2;0,4|6,5,4,3,2"
  "theta_graph|0,1;1,2;2,0;0,3;3,4;4,0|6,5,4,3"
  "diamond_tail|0,1;1,2;2,3;3,0;0,2;2,4|6,5,4,3,2"
  "butterfly|0,1;1,2;2,0;1,3;3,4|6,5,4,3"
  "K4_plus_leaf|0,1;0,2;0,3;1,2;1,3;2,3;0,4|6,5,4,3"
  "K5_minus_edge|0,1;0,2;0,3;0,4;1,2;1,3;1,4;2,3;2,4|6,5,4,3"
  "house_graph|0,1;1,2;2,3;3,0;1,3;2,4|6,5,4,3"
  "paw_plus|0,1;1,2;2,0;0,3;1,3;3,4|6,5,4,3"
  "kite_graph|0,1;1,2;2,0;2,3;3,4|6,5,4,3"
  "friendship_fan_5|0,1;0,2;0,3;0,4;1,2|6,5,4,3,2"
  "almost_complete_plus_tail|0,1;0,2;0,3;1,2;1,3;2,4|6,5,4,3"
)

# ---------- Build job list ----------
> "$JOBS_DIR/jobs.txt"
for g in "${GRAPHS[@]}"; do
  IFS='|' read -r name edges pivots <<< "$g"
  echo "arith|${name}|${edges}|${pivots}" >> "$JOBS_DIR/jobs.txt"
  echo "dicke|${name}|${edges}|${pivots}" >> "$JOBS_DIR/jobs.txt"
done

TOTAL=$(wc -l < "$JOBS_DIR/jobs.txt" | tr -d ' ')
COMPLETED_FILE="$JOBS_DIR/completed.txt"
FAILED_FILE="$JOBS_DIR/failed.txt"
> "$COMPLETED_FILE"
> "$FAILED_FILE"

echo "==============================================="
echo " MVC Grover Experiment Suite"
echo "==============================================="
echo " Total jobs:    $TOTAL"
echo " Parallelism:   $PARALLEL_JOBS workers"
echo " Output:        $DEST"
echo "==============================================="
echo ""

# ---------- Worker function (exported for xargs) ----------
run_one_job() {
  local job_file="$1"
  local total="$2"
  IFS='|' read -r solver name edges pivots < "$job_file"

  local workdir target_base
  if [[ "$solver" == "arith" ]]; then
    workdir="$ARITH_DIR"
    target_base="$DEST/arithmetic"
  else
    workdir="$DICKE_DIR"
    target_base="$DEST/dicke"
  fi

  # Per-job isolated output dir — avoids race with concurrent workers
  # writing to a shared outputs/ directory.
  local out_dir="$LOG_DIR/${solver}_${name}_out"
  local log="$LOG_DIR/${solver}_${name}.log"
  local start
  start=$(date +%s)

  # Wipe stale output dir from a previous run for this job
  trash "$out_dir" 2>/dev/null || true

  (
    cd "$workdir"
    source "$VENV"
    python main.py \
      --graph-edges "$edges" \
      --shots 1024 \
      --grover-iteration 1 \
      --pivot "$pivots" \
      --output-dir "$out_dir" \
      > "$log" 2>&1
  )
  local rc=$?
  local end
  end=$(date +%s)
  local dur=$((end - start))

  # Race-free progress index: count lines in append-only log files
  local completed failed idx
  completed=$(wc -l < "$COMPLETED_FILE" 2>/dev/null | tr -d ' ')
  failed=$(wc -l < "$FAILED_FILE" 2>/dev/null | tr -d ' ')
  completed=${completed:-0}
  failed=${failed:-0}
  idx=$((completed + failed + 1))

  if [[ $rc -eq 0 && -d "$out_dir" ]]; then
    echo "[$(date +%H:%M:%S)] ✓ $solver/$name (${dur}s) [$idx/$total]" >&2

    # ---- On-the-fly copy to destination ----
    local target="${target_base}/${name}_$(date +%Y%m%d_%H%M%S)"

    # Trash any existing run for this graph (keep newest only)
    local existing
    existing=$(ls -d "${target_base}/${name}_"*/ 2>/dev/null)
    if [[ -n "$existing" ]]; then
      for old in $existing; do
        trash "$old" 2>/dev/null || true
      done
    fi

    if cp -r "$out_dir" "$target" 2>/dev/null; then
      echo "    -> $(basename "$target")" >&2
    else
      echo "[$(date +%H:%M:%S)] ✗ $solver/$name COPY FAILED (rc=$rc) [$idx/$total]" >&2
      echo "${solver}|${name}|COPY_FAILED" >> "$FAILED_FILE"
      return 0
    fi

    echo "${solver}|${name}|$(basename "$target")" >> "$COMPLETED_FILE"
  else
    echo "[$(date +%H:%M:%S)] ✗ $solver/$name FAILED (rc=$rc) [$idx/$total]" >&2
    echo "${solver}|${name}|FAILED" >> "$FAILED_FILE"
  fi
}

export -f run_one_job
export ARITH_DIR DICKE_DIR VENV JOBS_DIR LOG_DIR DEST COMPLETED_FILE FAILED_FILE

# ---------- Run all jobs in parallel ----------
# Use split files for xargs (one job per file)
split -l 1 -d -a 3 "$JOBS_DIR/jobs.txt" "$JOBS_DIR/job_"

ls "$JOBS_DIR"/job_* | xargs -n 1 -P "$PARALLEL_JOBS" -I {} bash -c '
  run_one_job "$1" "$2"
' _ {} "$TOTAL"

echo ""
echo "==============================================="
echo " All jobs complete."
echo "==============================================="

# ---------- Final summary ----------
echo ""
echo "==============================================="
echo " Summary"
echo "==============================================="
echo " Total jobs:    $TOTAL"
echo " Completed:     $(wc -l < "$COMPLETED_FILE" | tr -d ' ')"
echo " Failed:        $(wc -l < "$FAILED_FILE" | tr -d ' ')"
echo " Arithmetic:    $(ls "$DEST/arithmetic" 2>/dev/null | wc -l | tr -d ' ')"
echo " Dicke:         $(ls "$DEST/dicke" 2>/dev/null | wc -l | tr -d ' ')"
echo "==============================================="

if [[ -s "$FAILED_FILE" ]]; then
  echo ""
  echo "Failed jobs:"
  cat "$FAILED_FILE"
fi
