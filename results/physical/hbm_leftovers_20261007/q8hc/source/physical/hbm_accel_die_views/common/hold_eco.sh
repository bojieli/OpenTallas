#!/bin/bash
# hold_eco.sh <src snapshot> <route dir> <post-sdc (src-relative)> <interface sdc (src-relative)> <view name>
#   post-detailed-route FF hold ECO (common/post_route_hold_eco.tcl) of a finished route_lane.sh / route_view.sh route
#   (<route dir>/work/orfs); writes <route dir>/eco as a self-contained route dir (work/orfs results, exit,
#   corner_sta.json at the route SDC, corner_sta_833.json at the sign-off post-SDC, outcheck, view/, physical.json with
#   the ECO's own detailed-route DRC count) so su/collect.py collects it like any other route.
#   env: KEEPCLK (1: clock nets keep their wires), HM (hold margin ps, 22), SM (setup margin ps, 45), THREADS (8), MAXL (M5), BUF (max buffer %, 10)
set -o pipefail
S=$1; W=$2; PS=$3; IF=$4; NAME=$5
O=$W/work/orfs; B=$(ls -d $O/results/asap7/*/base); rel=${B#$O/}
E=$W/${ECODIR:-eco}; EO=$E/work/orfs; EB=$EO/$rel
rm -rf $E; mkdir -p $EB $EO/logs
cp $B/6_final.sdc $EB/; cp $W/args $W/SOURCE_COMMIT $E/ 2>/dev/null
cat $S/SOURCE_COMMIT > $E/ECO_SOURCE_COMMIT
docker run --rm -v $B:/in:ro -v $EB:/out -v $S:/src:ro \
  -e OT_IN=/in -e OT_OUT=/out -e OT_POST_SDC="/src/$PS" -e OT_HOLD_MARGIN=${HM:-22} -e OT_SETUP_MARGIN=${SM:-45} \
  -e OT_KEEP_CLOCK=${KEEPCLK:-0} -e OT_THREADS=${THREADS:-8} -e OT_MAXL=${MAXL:-M5} -e OT_MAX_BUF_PCT=${BUF:-10} openroad/orfs:latest bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/physical/hbm_accel_die_views/common/post_route_hold_eco.tcl" \
  > $E/eco.log 2>&1
rc=$?; grep -q "OT_ECO done" $E/eco.log || rc=9
echo "rc=$rc" > $E/exit
cd $S
python3 tools/w18/corner_sta.py --orfs-dir $EO --output $E/corner_sta.json > $E/corner.log 2>&1; echo "corner_rc=$?" >> $E/exit
python3 tools/w18/corner_sta.py --orfs-dir $EO --post-sdc $PS --output $E/corner_sta_833.json > $E/corner833.log 2>&1
python3 physical/hbm_accel_die_views/su/outcheck.py $EO > $E/outcheck.txt 2>&1; echo "post_rc=$?" >> $E/exit
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $EO --name $NAME --out $E/view --tmp-dir $E/abs_tmp --interface-sdc $IF \
  > $E/export.log 2>&1; echo "export_rc=$?" >> $E/exit
python3 - $W $E <<'PY'
import json, re, sys
w, e = sys.argv[1:]
log = open(f'{e}/eco.log').read()
nv = re.findall(r'Number of violations = (\d+)', log)
drc = int(nv[-1]) if nv else None
p = json.load(open(f'{w}/physical.json'))
for c in (p.get('acceptance') or {}).get('checks') or []:
    if c.get('stage') == 'place_and_route':
        c['drc_errors_pre_eco'] = c.get('drc_errors'); c['drc_errors'] = drc
add = re.findall(r'OT_ECO cells_added (-?\d+)', log)
p['post_route_hold_eco'] = dict(script='physical/hbm_accel_die_views/common/post_route_hold_eco.tcl', drc_violations=drc,
                                cells_added=int(add[0]) if add else None,
                                slack_lines=[l for l in log.splitlines() if l.startswith(('OT_ECO', 'worst slack'))][:16])
json.dump(p, open(f'{e}/physical.json', 'w'), indent=1)
PY
echo "eco_done" >> $E/exit
