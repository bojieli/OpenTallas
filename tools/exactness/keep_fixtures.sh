#!/bin/bash
# token-exact 2026-10-09: mark every exactness fixture tree with .keep (honoured by dir48.sh, tools/fleet/sweep.py, deep release)
N="exactness fixture (token-exact 2026-10-09): do not sweep / release; see results/rtl/token_exact_20261009/STATUS.md"
for d in /srv/opentallas-scratch/claude/exactness /srv/opentallas-scratch/claude/exactness/fixtures \
         /srv/opentallas-scratch/claude/token-exact /srv/opentallas-scratch/claude/token-exact/fx /srv/opentallas-scratch/claude/token-exact/gold /srv/opentallas-scratch/claude/token-exact/w12r \
         /srv/opentallas-scratch/claude/realmem-ctx8k /srv/opentallas-scratch/claude/qwen-dspark-system \
         /srv/opentallas-scratch/claude/qwen-dspark-system/img_p1 /srv/opentallas/scratch-overflow/claude/layer-parallel-sim \
         /srv/opentallas/scratch-overflow/claude/layer-parallel-sim/data /srv/opentallas-scratch/claude/hbm-sim \
         /srv/opentallas/scratch-overflow/claude/qwen-dspark-system \
         /home/ubuntu/exactness-fixtures /home/ubuntu/w17work /home/ubuntu/realmem-ctx8k /home/ubuntu/qwen-dspark-oracle-run; do
  [ -d "$d" ] || continue
  echo "$N" > "$d/.keep" && echo "$(hostname) keep $d"
done
