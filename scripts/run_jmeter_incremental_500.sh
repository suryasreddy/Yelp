#!/usr/bin/env bash
# One JMeter run: ramp up to 500 concurrent threads (incremental load in a single process).
# Uses one RESTAURANT_ID and jmeter/data/jmeter_users.csv — need ≥500 distinct rows (Lab 1: one review per user per restaurant).
#
# Prereq: python3 scripts/jmeter_prepare_load_users.py --base-url http://localhost:8000 --count 500
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

JMETER_BIN="${JMETER_BIN:-jmeter}"
PLAN="${PLAN:-jmeter/lab2_backend.jmx}"
OUT_DIR="${OUT_DIR:-jmeter/results}"
HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
# Seconds to go from 0 → 500 active threads (spread starts incrementally).
RAMP="${RAMP:-600}"
CSV_PATH="${CSV_PATH:-jmeter/data/jmeter_users.csv}"
RESTAURANT_ID="${RESTAURANT_ID:-2}"
THREADS="${THREADS:-500}"

mkdir -p "$OUT_DIR"

if ! command -v "$JMETER_BIN" >/dev/null 2>&1; then
  echo "JMeter not found. Set JMETER_BIN to your jmeter executable." >&2
  exit 1
fi

JTL="${JTL:-$OUT_DIR/lab2_incremental_${THREADS}users.jtl}"
HTML="${HTML:-$OUT_DIR/html_incremental_${THREADS}users}"
rm -rf "$HTML"

echo "Single run: threads=$THREADS ramp=${RAMP}s restaurant_id=$RESTAURANT_ID CSV=$CSV_PATH"
echo ">>> JMeter prints 'summary' lines every ~30s — normal."

"$JMETER_BIN" -n \
  -t "$PLAN" \
  -l "$JTL" \
  -e -o "$HTML" \
  -JHOST="$HOST" \
  -JPORT="$PORT" \
  -Jthreads="$THREADS" \
  -Jramp="$RAMP" \
  -JCSV_PATH="$CSV_PATH" \
  -JRESTAURANT_ID="$RESTAURANT_ID"

echo "Wrote $JTL and $HTML/index.html"
