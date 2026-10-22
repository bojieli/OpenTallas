#!/bin/bash
# S81-CAL241: regenerate the 241-stage release MU calendars (G16 / G8 / G4 attention) from the committed inputs
set -e
M=results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json
O=results/token_pass/mucal241_s81_1021
mkdir -p $O
for v in G16 G8 G4; do
  python3 tools/s81_dv/dv_mu_calendar_phys.py --map $M --compose romopt --alap --release241 --attn $v --tag rel241_$v --out $O ${CHECK:+--check} > $O/rel241_$v.log
  head -2 $O/rel241_$v.log
done
