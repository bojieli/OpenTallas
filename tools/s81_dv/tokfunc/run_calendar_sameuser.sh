#!/bin/bash
# Fleet model-only recomputation. A failed calendar returns 2; preserve outputs.
set -u
ROOT=$(realpath "$1"); OUT=$(realpath -m "$2")
mkdir -p "$OUT"
cd "$ROOT" || exit 1
sha256sum tools/s81_dv/dv_mu_calendar_phys.py tools/s81_dv/tokfunc/mu_hop_plan.py \
  results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json > "$OUT/inputs.sha256"
python3 tools/s81_dv/dv_mu_calendar_phys.py --release241 --attn G4 --compose romopt --alap \
  --map results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json \
  --tag rel241_G4 --out "$OUT" > "$OUT/recompute.log" 2>&1
rc=$?
echo "$rc" > "$OUT/exit_status"
exit "$rc"
