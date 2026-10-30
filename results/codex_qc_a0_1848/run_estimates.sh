#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/codex-qc-a0-1848
for tile in nl nk; do
 for leaf in 1 2 4; do
  python3 -I src/gen_a0_tree39.py --kit kit_$tile --census data/$tile.tsv.gz --out plans/${tile}_l${leaf}_t30.json --report plans/${tile}_l${leaf}_t30_rep.json --stages 30 --leg 150 --reg-domains planned --leaf-max $leaf --stage-ff 25.02 --stage-tt 32.10 --stage-src 'DIE-QC39 measured fo2 40-60um' > plans/${tile}_l${leaf}_t30.log 2>&1 || true
 done
done
