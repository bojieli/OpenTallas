#!/bin/bash
# DIE-HBM-4: all HBM region-map candidates with the MESO-RECONCILE-2 planner, spice x1.0485 TT / x1.0552 FF
cd /srv/opentallas-scratch2/claude/die-hbm-1027/region3
PF=/srv/opentallas-scratch2/claude/die-hbm-1027/c20f/die_plan.json; PH=r4/hs/plan_hubsplit.json
for V in 219.2 278.6; do for F in fish spt; do
  python3 r4/r4_tok.py ../est/src $PF $V $F hpmaps/tok_l10_v1_c5.json r4/mr/v1c5_${F}_$V.tsv > r4/mr/v1c5_${F}_$V.log 2>&1 &
  python3 r4/r4_tok.py ../est/src $PH $V $F r4/hs/map_hubsplit.json r4/mr/hs_${F}_$V.tsv > r4/mr/hs_${F}_$V.log 2>&1 &
  python3 r4/r4_tok.py ../est/src $PF $V $F ../est/one_t63/hbm_t63c20_regions.json r4/mr/t63_${F}_$V.tsv > r4/mr/t63_${F}_$V.log 2>&1 &
done; done
wait
