#!/bin/bash
# DIE-S81-27: compose WS3 variant $1 then G0 and G0C (parallel) on its plan copy; inputs read-only
set -uo pipefail
V=$1; W=/srv/opentallas-scratch2/claude/wt/die-s81-27-ws3; R=/srv/opentallas-scratch2/claude/die-s81-27/ws3/$V
mkdir -p "$R"; cd "$W"
for n in inputs census; do ln -sfn "$W/physical/die_plan/s81/$n" "$R/$n"; done
ln -sfn "$W/physical" "$R/physical"
for n in cells_est.json census_map.json core_conns.json; do cp "$W/physical/die_plan/s81/$n" "$R/$n"; done
echo "start $(date)" > "$R/run.status"
python3 physical/die_plan/s81/compose_ws3_1029.py --variant $V --out "$R" > "$R/compose.log" 2>&1
rc=$?; echo "compose RC $rc $(date)" >> "$R/run.status"; [ $rc -ne 0 ] && exit $rc
P=$(ls "$R"/plan_s13r2_*.json)
python3 tools/die_plan/check.py "$P" --png --out "$R/g0" > "$R/g0.log" 2>&1 &
a=$!
python3 tools/die_plan/check.py "$P" --completeness --png --out "$R/g0c" > "$R/g0c.log" 2>&1 &
b=$!
wait $a; ra=$?; wait $b; rb=$?
echo "G0 RC $ra G0C RC $rb $(date)" >> "$R/run.status"
exit 0
