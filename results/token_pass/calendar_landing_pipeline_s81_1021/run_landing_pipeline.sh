#!/bin/bash
set -eu
M=results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json
for n in 0 6 7; do
 O=results/token_pass/calendar_landing_pipeline_s81_1021/land$n
 mkdir -p "$O"
 sha256sum tools/s81_dv/dv_mu_calendar_phys.py "$M" > "$O/inputs.sha256"
 python3 tools/s81_dv/dv_mu_calendar_phys.py --map "$M" --compose romopt --alap --release241 --attn G4 --lane-landing-cycles "$n" --tag rel241_G4 --out "$O" > "$O/recompute.log" 2>&1
 echo "LANDING_CYCLES=$n"; head -2 "$O/recompute.log"
done
