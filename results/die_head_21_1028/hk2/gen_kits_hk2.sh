#!/bin/bash
# DIE-HEAD-21 HK2: plan_hk2 = plan_hk1 (HEAD-KITS-1) + SRAM macros (hard_cores, S81 form) on hd_serdes/mesh/ctl/host
# + LEP-C0 hd_lep0N (lep_pair hard cores + 45 parent SRAM), then trial kits + kit_preflight for the 5 changed types.
set -euo pipefail
W=$(git rev-parse --show-toplevel); K=$W/results/head_kits_1_1028; R=$W/results/die_head_21_1028/hk2; O=${1:?out dir}
mkdir -p "$O"; gunzip -c "$K/plan_hk1.json.gz" > "$O/plan_hk1.json"; gunzip -c "$K/landed_sidecar.json.gz" > "$O/landed_sidecar.json"
python3 "$W/tools/s81_head/head_kit_macros_delta.py" "$O/plan_hk1.json" "$R/sram_census.json" --out "$O/plan_hk2.json" \
  --report "$O/report.json" --png-dir "$O/png"
python3 "$W/tools/die_plan/check.py" "$O/plan_hk2.json" --completeness --core-conns "$W/physical/die_plan/s81_head/core_conns.json" \
  --out "$O/g0c" --quiet | tail -1 || true   # G0C: 16 pre-existing one-entry insertion_target ERRORs (plan_hk1 too)
T=hd_serdes,hd_mesh,hd_lep0N,hd_ctl,hd_host
python3 "$W/tools/die_plan/gen.py" phys "$O/plan_hk2.json" --out "$O/kits" --rtl-root "$W" --types $T \
  --clock-landing "$O/landed_sidecar.json" --trial
for k in "$O"/kits/hd_*; do echo "$(basename $k): $(python3 "$W/tools/die_plan/kit_preflight.py" "$k" | tail -2 | tr "\n" " ")"; done
