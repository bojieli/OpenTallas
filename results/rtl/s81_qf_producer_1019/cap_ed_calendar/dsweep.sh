#!/bin/bash
# min E-column static delay D: six frames, E kinds shifted +D, gap-0 12-pair pool
for D in $(seq 1 40); do
  timeout 600 python3 -I root_pack.py gap0_complete_generated_pool.json.gz packD_$D.json "[[0,0],[1,0],[1,7],[0,$D],[1,$D],[1,$((7+D))]]" | sed "s/^/D=$D /" | grep ROOT_PACK
done
