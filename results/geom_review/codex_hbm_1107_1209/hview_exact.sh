#!/bin/bash
# Read-only review: choose exactly requested stage; record path before rendering.
set -euo pipefail
K=$(realpath "$1");ST=$2;O=$3;T=$(cd "$(dirname "$0")" && pwd)
B=$(find "$K/run/results/asap7" -mindepth 2 -maxdepth 2 -type d -name base -print -quit)
case "$ST" in place) F="$B/3_place.odb";;grt) F="$B/5_1_grt.odb";;route) F="$B/6_final.odb";;*)echo "unknown stage $ST" >&2;exit 2;;esac
test -f "$F" || { echo "MISSING EXACT STAGE $F" >&2;exit 2; }
mkdir -p "$O";touch "$O/.keep";printf '%s\n' "$F" > "$O/requested_stage_odb.txt"
DIE=$(awk '/^export DIE_AREA/{print $6, $7}' "$K/config.mk")
docker run --rm --memory=4g --memory-swap=4g --cpus=2 -v "$K":/work:ro -v "$O":/out -v "$F":/odb/in.odb:ro -e ODB=/odb/in.odb -e OUT=/out/all.csv openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/dump_placed.py > /out/dump.log 2>&1'
python3 -I - "$O" <<'PY'
import csv,sys
from pathlib import Path
p=Path(sys.argv[1]);r=csv.DictReader((p/'all.csv').open())
with (p/'logic.csv').open('w')as f:
 w=csv.DictWriter(f,fieldnames=r.fieldnames);w.writeheader()
 for x in r:
  if not x['master'].startswith(('FILLER','DECAP','TAPCELL')):w.writerow(x)
PY
if python3 -I -c 'import matplotlib' >/dev/null 2>&1; then
  python3 -I "$T/vk_render.py" "$O/logic.csv" "$O/$ST.png" --die $DIE --title "$ST EXACT $(basename "$F") logic-only; source path in requested_stage_odb.txt" > "$O/metrics.txt"
else
  echo "CAPTURE COMPLETE; RENDER NOT RUN: isolated python lacks matplotlib. Render logic.csv with isolated plot environment; requested_stage_odb.txt records exact source." >&2
fi
