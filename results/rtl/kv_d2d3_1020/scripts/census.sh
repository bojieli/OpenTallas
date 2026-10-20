#!/bin/bash
cd "$(dirname "$0")"
LIBS=""; for l in libs/*.lib libs/*.lib.gz; do LIBS="$LIBS --liberty $l"; done
for k in r7w ovl; do
  top=$(grep '^export DESIGN_NAME' in/$k/config.mk | awk '{print $4}')
  python3 tools/ref_tile/native_census.py --netlist in/$k/1_2_yosys.v --top $top $LIBS --out out_$k.json > out_$k.log 2>&1; echo "$k rc=$?" >> census.rc
done
