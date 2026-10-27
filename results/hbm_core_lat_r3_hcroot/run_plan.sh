#!/bin/bash
# HBM-CORE-LAT-R3 hcroot: KITDIR (placed, 3_place.odb) -> geo dump -> structured tree + 12.8c fixed-trunk plan -> render.
# Candidates (plan geometry only): splits {2,2,4,4 | 2,2,4,4,2 | 2,2,4,4,4} x repeater pitch smax {35, 50, 70} um
# (smax sets the repeater waypoints that make every edge of a level exactly T_l long = equal structure).  Choice rule,
# fixed before any build: predicted TT/FF window <= 20 first, then min |TT-250|+|FF-202.5| (trunk N inside each
# candidate by the same cost), ties -> fewer cells.  Plan model only (UNCHECKED); no CTS.
#   run_plan.sh KITDIR OUTDIR NAME
set -euo pipefail
K=$(cd "$1" && pwd); O=$(mkdir -p "$2" && cd "$2" && pwd); N=$3
H=$(cd "$(dirname "$0")" && pwd); W=$(cd "$H/../.." && pwd); L=${OT_HCR_LIB:-/srv/opentallas-scratch2/claude/hbm-core-lat-r3-hcroot/lib}
ODB=$(ls $K/run/results/asap7/*/base/3_place.odb | head -1)
if [ ! -s $O/$N.geo ]; then
  cp $H/dump_geo.tcl $K/dump_geo_hcr.tcl
  docker run --rm --memory=8g --memory-swap=8g -v $K:/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
    ODB=${ODB/$K//work} OUT=/work/hcr.geo OT_CLK_PORT=clk openroad -exit /work/dump_geo_hcr.tcl; chown $(id -u):$(id -g) /work/hcr.geo" > $O/$N.geo.log 2>&1
  cp $K/hcr.geo $O/$N.geo
fi
mkdir -p $O/cand_$N
for sm in 35 50 70; do for s in 2,2,4,4 2,2,4,4,2 2,2,4,4,4; do
  t=$O/cand_$N/s${s//,/}_m$sm
  ( python3 $W/tools/die_plan/core_trunk_plan.py $O/$N.geo $t --libtt $L/invbuf_TT.lib --libff $L/invbuf_FF.lib --splits $s --smax $sm > $t.log 2>&1 || true ) &
done; done; wait
python3 - "$O/cand_$N" "$O/$N" <<'PY'
import glob, json, shutil, sys
rows = []
for f in sorted(glob.glob(sys.argv[1] + '/*.json')):
    d = json.load(open(f)); p = d['pred']; w = max(p['TT']['window'], p['FF']['window'])
    cost = abs(p['TT']['mean'] - 250) + abs(p['FF']['mean'] - 202.5)
    ncell = len(d['nodes']) + d['trunk']['n']
    rows.append((w > 20, round(cost, 2), ncell, f, w, p['TT']['mean'], p['FF']['mean'], d['trunk']['n']))
rows.sort()
for r in rows: print('cand %s win %.2f TT %.2f FF %.2f trunkN %d cells %d cost %.2f%s' % (r[3].split('/')[-1], r[4], r[5], r[6], r[7], r[2], r[1], '' if not r[0] else ' (window>20)'))
best = rows[0][3]; print('CHOSEN', best.split('/')[-1])
shutil.copyfile(best, sys.argv[2] + '.plan.json'); shutil.copyfile(best[:-5] + '.tree_spec.tcl', sys.argv[2] + '.tree_spec.tcl')
d = json.load(open(sys.argv[2] + '.plan.json')); d['choice'] = dict(rule='window<=20 first, then min |TT-250|+|FF-202.5|, then fewer cells', candidates=[dict(cand=r[3].split('/')[-1], window=r[4], TT=r[5], FF=r[6], trunk_n=r[7], cells=r[2]) for r in rows])
json.dump(d, open(sys.argv[2] + '.plan.json', 'w'), indent=1)
PY
python3 $H/render_trunk_plan.py $K/placed.csv $K/pins.json $O/$N.plan.json $O/$N.plan.png "$N"
