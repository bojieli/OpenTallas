#!/bin/bash
set -eu
cd /work/am_map_fa
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 prepare.py
for top in old_am new_am; do
 yosys -s "$top.ys" > "$top.map.log" 2>&1
done
