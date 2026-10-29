#!/bin/bash
set -eu
src=/srv/opentallas-scratch2/claude/wt/codex-s81-ce12-1029
out=/srv/opentallas-scratch2/claude/codex-s81-ce12-1029
mkdir -p "$out/gen_bound2" "$out/logs_bound2" "$out/rtl_bound2"
cd "$src"
for t in slice_station__t8 slice_station__t23 slice_station__t31 slice_station__t43 slice_station__t44 slice_station__t49 slice_station__t52; do
  if python3 -I tools/die_plan/bind.py kit-rtl physical/die_plan/s81/plan_s13r2.json --asbuilt physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json --out /srv/opentallas-scratch2/claude/die-s81-24-bind/codex_out --type "$t" --kit "$out/rtl_bound2/$t" > "$out/logs_bound2/rtl_$t.log" 2>&1 && python3 -I tools/die_plan/gen.py phys physical/die_plan/s81/plan_s13r2.json --out "$out/gen_bound2/$t" --types "$t" --rtl-root "$src" --kit-rtl "$t=$out/rtl_bound2/$t/kit_rtl.f" --hold-ff-margin 10 --max-wire-um 100 > "$out/logs_bound2/gen_$t.log" 2>&1; then
    printf '%s PASS\n' "$t" >> "$out/gen_bound2_status.txt"
  else
    printf '%s FAIL\n' "$t" >> "$out/gen_bound2_status.txt"
  fi
done
