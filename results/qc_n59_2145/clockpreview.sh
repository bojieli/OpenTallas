#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for i in 0 1 2 3; do
 OT_DTSH_LEAF_FANOUT=4 OT_DTSH_RMAX_UM=180 python3 shallow_clock.py root$i.tsv --closed-loop --out root${i}_leaf4_r180.json --image root${i}_leaf4_r180.png
 done
