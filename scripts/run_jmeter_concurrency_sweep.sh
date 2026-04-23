#!/usr/bin/env bash
# Run Lab 2 JMeter plan at 100, 200, 300, 400, 500 threads. Writes .jtl per level and HTML dashboards.
# Prereqs: JMeter on PATH as `jmeter`, backend up, `python scripts/jmeter_prepare_load_users.py` already run with matching --count.
#
# Each tier uses a different RESTAURANT_ID (2..6 by default) so the same CSV users do not hit
# "already reviewed" on every sequential run (one review per user per restaurant).
#
# Repeating "summary + / summary =" lines during one tier are JMeter's normal 30s progress — not a hang.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

JMETER_BIN="${JMETER_BIN:-jmeter}"
PLAN="${PLAN:-jmeter/lab2_backend.jmx}"
OUT_DIR="${OUT_DIR:-jmeter/results}"
HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
RAMP="${RAMP:-120}"
CSV_PATH="${CSV_PATH:-jmeter/data/jmeter_users.csv}"
# First tier uses this restaurant id; each next tier uses +1 (override entire sequence with RESTAURANT_ID if you only run one tier).
RESTAURANT_BASE="${RESTAURANT_BASE:-2}"

mkdir -p "$OUT_DIR"

if ! command -v "$JMETER_BIN" >/dev/null 2>&1; then
  echo "JMeter not found. Set JMETER_BIN to your jmeter executable, e.g.:" >&2
  echo "  export JMETER_BIN=\"\$HOME/apache-jmeter-5.6.3/bin/jmeter\"" >&2
  exit 1
fi

tier=0
for threads in 100 200 300 400 500; do
  rid=$((RESTAURANT_BASE + tier))
  echo ""
  echo "========== tier $((tier + 1))/5: threads=$threads  restaurant_id=$rid  (separate run, ~2+ min) =========="
  echo ">>> JMeter will print 'summary' lines every ~30s during this run — that is normal progress."
  JTL="$OUT_DIR/lab2_${threads}users.jtl"
  HTML="$OUT_DIR/html_${threads}users"
  rm -rf "$HTML"
  "$JMETER_BIN" -n \
    -t "$PLAN" \
    -l "$JTL" \
    -e -o "$HTML" \
    -JHOST="$HOST" \
    -JPORT="$PORT" \
    -Jthreads="$threads" \
    -Jramp="$RAMP" \
    -JCSV_PATH="$CSV_PATH" \
    -JRESTAURANT_ID="$rid"
  echo "Wrote $JTL and $HTML"
  tier=$((tier + 1))
done

echo ""
echo "Done. Open each html_*/index.html for response-time graphs. Aggregate latency vs threads in your report."
