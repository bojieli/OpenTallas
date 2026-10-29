#!/bin/bash
# HEAD-KITS-1: regenerate the 15 non-tile HEAD kits from this commit (main tools + plan_hk1 + Codex landed sidecar).
# plan_hk1 = DIE-HEAD-9 one-entry plan_one_entry_450.json (sha 23b20750) + for every non-tile type
#   clock.landing_export_form=fwd_buffer, clock.tap_passthrough=true (COORD 21:05 ruling, DIE-HEAD-19 ASK 1)
#   + hd_host sources minus rtl/lib/ot_reset_sync.sv (gen_phys always adds it; listed twice -> duplicate module).
set -euo pipefail
W=$(git rev-parse --show-toplevel); R=$W/results/head_kits_1_1028; O=${1:?out dir}
mkdir -p "$O"; gunzip -c "$R/plan_hk1.json.gz" > "$O/plan_hk1.json"; gunzip -c "$R/landed_sidecar.json.gz" > "$O/landed_sidecar.json"
T=hd_turn_a,hd_turn_b,hd_spn,hd_spn_end,hd_serdes,hd_st_turn,hd_st_str,hd_st_n3,hd_st_n4,hd_st_m,hd_st_k5,hd_mesh,hd_lep0N,hd_ctl,hd_host
python3 "$W/tools/die_plan/gen.py" phys "$O/plan_hk1.json" --out "$O/kits" --rtl-root "$W" --types $T \
  --clock-landing "$O/landed_sidecar.json" --trial
for k in "$O"/kits/hd_*; do python3 "$W/tools/die_plan/kit_preflight.py" "$k" | tail -1 || true; done
# declared landing-ring buses for face_guard (D = forwarded_write_flops / ring_width, hold_mux slots)
python3 "$W/tools/s81_head/head_land_slots.py" "$O"/kits/hd_*
