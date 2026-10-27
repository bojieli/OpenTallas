#!/bin/bash
# HBM-CORE-LAT-R3 hcroot: KITDIR (placed, 3_place.odb) -> geo dump -> 12.8c fixed-trunk plan (splits chosen by the plan
# model: min predicted window, then trunk N by |TT-250|+|FF-202.5|) -> render.  Plan model only (UNCHECKED); no CTS.
#   run_plan.sh KITDIR OUTDIR NAME
set -euo pipefail
K=$(cd "$1" && pwd); O=$(mkdir -p "$2" && cd "$2" && pwd); N=$3
H=$(cd "$(dirname "$0")" && pwd); W=$(cd "$H/../.." && pwd); L=${OT_HCR_LIB:-/srv/opentallas-scratch2/claude/hbm-core-lat-r3-hcroot/lib}
ODB=$(ls $K/run/results/asap7/*/base/3_place.odb | head -1)
cp $H/dump_geo.tcl $K/dump_geo_hcr.tcl
docker run --rm --memory=8g --memory-swap=8g -v $K:/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  ODB=${ODB/$K//work} OUT=/work/hcr.geo OT_CLK_PORT=clk openroad -exit /work/dump_geo_hcr.tcl; chown $(id -u):$(id -g) /work/hcr.geo" > $O/$N.geo.log 2>&1
cp $K/hcr.geo $O/$N.geo
best=""; bw=1e9
for s in 2,2,4,4 2,2,4,4,2 2,2,4,4,4; do
  python3 $W/tools/die_plan/core_trunk_plan.py $O/$N.geo $O/$N.s${s//,/} --libtt $L/invbuf_TT.lib --libff $L/invbuf_FF.lib --splits $s > $O/$N.s${s//,/}.log 2>&1 || continue
  w=$(python3 -c "import json;d=json.load(open('$O/$N.s${s//,/}.json'));print(max(d['pred']['TT']['window'],d['pred']['FF']['window']))")
  echo "splits $s window $w"
  if python3 -c "import sys; sys.exit(0 if $w < $bw else 1)"; then bw=$w; best=$s; fi
done
echo "CHOSEN splits $best (min predicted window $bw)"
cp $O/$N.s${best//,/}.json $O/$N.plan.json; cp $O/$N.s${best//,/}.tree_spec.tcl $O/$N.tree_spec.tcl
python3 $H/render_trunk_plan.py $K/placed.csv $K/pins.json $O/$N.plan.json $O/$N.plan.png "$N"
