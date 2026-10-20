#!/bin/bash
cd "$(dirname "$0")"
LIBS=""; for l in libs/asap7*.lib libs/asap7*.lib.gz; do LIBS="$LIBS --liberty $l"; done
top=$(grep '^export DESIGN_NAME' in/bc4/config.mk | awk '{print $4}')
python3 tools/ref_tile/native_census.py --netlist in/bc4/1_2_yosys.v --top $top $LIBS --out out_bc4.json > out_bc4.log 2>&1; echo "bc4 rc=$?" >> census.rc
