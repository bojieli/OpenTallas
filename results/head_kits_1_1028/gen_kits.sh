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
# HEAD-KITS-3: land_slots.json (land_slots/2: ring buses hold_mux + cland_fstart_in ring_start) is written by gen phys
# --clock-landing (DIE-HEAD-21 landslots 528a7d3edb + ringstart 52a35ca59d); head_land_slots.py would overwrite it
# without the ring_start entries, so it is no longer run here.
