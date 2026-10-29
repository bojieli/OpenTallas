#!/bin/bash
set -eu
src=/srv/opentallas-scratch2/claude/wt/codex-s81-ce12-1029
out=/srv/opentallas-scratch2/claude/codex-s81-ce12-1029
mkdir -p "$out/core_kits" "$out/core_logs"
cd "$src"
for m in dsfd_su_t_rxsf ot_s81sl_vs ot_s81sl_ve_m ot_s81sl_ve_s ot_s81sl_vn_a ot_s81sl_vn_b ot_s81sl_vsw; do
  if python3 -I physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py --module "$m" --out "$out/core_kits" --plan physical/die_plan/s81/plan_s13r2.json --suffix ce12 > "$out/core_logs/gen_$m.log" 2>&1; then
    printf '%s PASS\n' "$m" >> "$out/core_status.txt"
  else
    printf '%s FAIL\n' "$m" >> "$out/core_status.txt"
  fi
done
