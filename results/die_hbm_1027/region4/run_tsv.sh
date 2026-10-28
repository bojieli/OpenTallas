#!/bin/bash
# DIE-HBM-4: best map tok_l10_v1_c5 fish on C20f plan, nominal vs x1.0485 (12.15b) wire speeds
cd /srv/opentallas-scratch2/claude/die-hbm-1027/region3
P=/srv/opentallas-scratch2/claude/die-hbm-1027/c20f/die_plan.json
for V in 209.1 219.2 265.7 278.6 366.4; do
  python3 region3_tok.py tsv ../est/src $P $V fish hpmaps/tok_l10_v1_c5.json r4/v1c5_fish_$V.tsv > r4/v1c5_fish_$V.log 2>&1 &
done
wait
