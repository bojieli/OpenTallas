#!/bin/bash
# STEWARD-TOK 10-21: 241-stage release MU calendars with the causal six-position MTP pipeline (overlap424 repair of
# 6f8bbf5c4).  Default --release241 = MTP stage held for the whole step (one job context); G4pos = one job a position
# + greedy phase-grid shift search (sensitivity).  CHECK=1 -> --check.
set -e
M=results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json
O=results/token_pass/calendar_pipeline_s81_1021
mkdir -p $O
sha256sum tools/s81_dv/dv_mu_calendar_phys.py $M > $O/inputs.sha256
for v in G16 G8 G4; do
  python3 tools/s81_dv/dv_mu_calendar_phys.py --map $M --compose romopt --alap --release241 --attn $v --tag rel241_$v --out $O ${CHECK:+--check} > $O/rel241_$v.log
  head -2 $O/rel241_$v.log
done
python3 tools/s81_dv/dv_mu_calendar_phys.py --map $M --compose romopt --alap --release241 --attn G4 --mtp-hold position --mtp-shift-search --tag rel241_G4pos --out $O ${CHECK:+--check} > $O/rel241_G4pos.log
head -2 $O/rel241_G4pos.log
