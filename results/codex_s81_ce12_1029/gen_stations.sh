#!/bin/bash
set -eu
src=/srv/opentallas-scratch2/claude/wt/codex-s81-ce12-1029
out=/srv/opentallas-scratch2/claude/codex-s81-ce12-1029
mkdir -p "$out/gen" "$out/logs"
cd "$src"
for t in slice_station__t8 slice_station__t23 slice_station__t31 slice_station__t43 slice_station__t44 slice_station__t49 slice_station__t52; do
  if python3 -I tools/die_plan/gen.py phys physical/die_plan/s81/plan_s13r2.json --out "$out/gen/$t" --types "$t" --rtl-root "$src" --clock-landing physical/die_plan/s81/s13/landed_sidecar_s13.json --hold-ff-margin 10 --max-wire-um 100 > "$out/logs/gen_$t.log" 2>&1; then
    printf '%s PASS\n' "$t" >> "$out/gen_status.txt"
  else
    printf '%s FAIL\n' "$t" >> "$out/gen_status.txt"
  fi
done
