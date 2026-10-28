#!/bin/bash
cd /srv/opentallas-scratch2/claude/die-hbm-1027/region3
P=r4/hs/plan_hubsplit.json; M=r4/hs/map_hubsplit.json
for V in 209.1 219.2 265.7 278.6 366.4; do
  python3 region3_tok.py tsv ../est/src $P $V fish $M r4/hs/fish_$V.tsv > r4/hs/fish_$V.log 2>&1 &
done
for V in 219.2 278.6 366.4; do python3 spread.py $P $V $M hpmaps/tok_l10_v1_c5.json > r4/hs/spread_$V.log 2>&1 & done
wait
