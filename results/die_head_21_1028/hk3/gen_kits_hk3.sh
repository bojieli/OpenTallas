#!/bin/bash
# DIE-HEAD-21 HK3: plan_hk3 = plan_hk2 + landing bands re-composed at ring_ff x spread 2.0, ring_place ff (main
# clock_landing_plan._storage_band) on the 15 non-tile types, hd_lep0N lep_pair cores moved so every band sits in front
# of its own window (README (b)), SRAM re-placed around the new bands (HK2 placer). Then G0C, trial kits, kit_preflight.
#   gen_kits_hk3.sh OUT [--plan-only]
set -euo pipefail
W=$(git rev-parse --show-toplevel); R=$W/results/die_head_21_1028; O=${1:?out dir}; P=u_core.u.g_pp
mkdir -p "$O"; gunzip -c "$R/hk2/plan_hk2.json.gz" > "$O/plan_hk2.json"; gunzip -c "$W/results/head_kits_1_1028/landed_sidecar.json.gz" > "$O/landed_sidecar.json"
mkdir -p "$O/core_pins"; cp "$R"/hk2/core_pins/*.json "$O/core_pins/"     # LEP-C0 SRAM pins_file (hk2 form, same relative path)
python3 "$W/tools/s81_head/head_band_ringff_delta.py" "$O/plan_hk2.json" --census "$R/hk2/sram_census.json" --spread 2.0 --ring ff \
  --sram-shift hd_lep0N:440:25.92 \
  --core-move "hd_lep0N:$P[3].u_pair=950.4,639.36" --core-move "hd_lep0N:$P[0].u_pair=544.32,786.24" \
  --core-move "hd_lep0N:$P[1].u_pair=69.12,639.36" --core-move "hd_lep0N:$P[2].u_pair=69.12,120.96" \
  --out "$O/plan_hk3.json" --report "$O/report.json" --png-dir "$O/png"
python3 "$W/tools/die_plan/check.py" "$O/plan_hk3.json" --completeness --core-conns "$W/physical/die_plan/s81_head/core_conns.json" \
  --out "$O/g0c" --quiet | tail -1 || true   # G0C: only the 16 one-entry insertion_target ERRORs of plan_hk1/hk2 allowed
[ "${2:-}" = --plan-only ] && exit 0
T=$(python3 -c "import json;print(','.join(json.load(open('$O/report.json'))['types']))")
python3 "$W/tools/die_plan/gen.py" phys "$O/plan_hk3.json" --out "$O/kits" --rtl-root "$W" --types $T \
  --clock-landing "$O/landed_sidecar.json" --trial
for k in "$O"/kits/hd_*; do echo "$(basename $k): $(python3 "$W/tools/die_plan/kit_preflight.py" "$k" | tail -2 | tr "\n" " ")"; done
# land_slots.json: the one written by gen phys (Landings.land_slots, land_slots/2 incl. the cland_fstart_in_* ring_start
# entries). DIE-HEAD-21 lepwe (COORD HEAD-KITS-3 23:13): head_land_slots.py is NOT run any more - it rewrote the
# file and dropped the start-port entries.
