#!/bin/bash
# QK-SLICE 10-18: re-CTS sweep of the qfd_dv_lane_h gate placement (3_place.odb), ORFS cts + ck_insertion per variant
set -u
R=/srv/opentallas-scratch/claude/ref_gate/qfd_dv_lane_h-20261018-041551
S=/srv/opentallas-scratch/claude/qk-slice/cts_sweep; mkdir -p $S
BASE="-sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.75"
declare -A V
V[v1]="$BASE -sink_clustering_levels 2 -distance_between_buffers 40 -no_obstruction_aware"
V[v2]="$BASE -no_obstruction_aware"
V[v3]="$BASE -sink_clustering_levels 2 -distance_between_buffers 40"
V[v4]="$BASE -sink_clustering_size 20 -sink_clustering_max_diameter 40"
V[v5]="$BASE -sink_clustering_size 30 -sink_clustering_max_diameter 60 -sink_clustering_levels 2 -no_obstruction_aware"
V[v6]="-repair_clock_nets -delay_buffer_derate 0.75"
V[v7]="$BASE -sink_clustering_levels 2 -distance_between_buffers 25 -no_obstruction_aware"
for k in "${!V[@]}"; do (
  C=$S/$k/orfs; rm -rf $S/$k; mkdir -p $S/$k; cp -a $R/routes/gate/work/orfs $C
  B=$(ls -d $C/results/asap7/*/base); rm -f $B/4_* ; rm -f $C/logs/asap7/*/base/4_*
  sed -i "s|/srv/opentallas-scratch/claude/ref_gate/qfd_dv_lane_h-20261018-041551/routes/gate/work/orfs|/work|g" $C/config.mk 2>/dev/null
  docker run --rm --name qkslice_cts_$k -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base CTS_ARGS='${V[$k]}' cts" > $S/$k/cts.log 2>&1; echo "CTS_RC=$?" > $S/$k/rc
  (cd $R/src && python3 tools/closure_loop/ck_insertion.py --base $B --all-clocks --raw-source --output $S/$k/ck.json > $S/$k/ck.log 2>&1); echo "CK_RC=$?" >> $S/$k/rc
  rm -rf $C/objects
) & done; wait
for k in $(echo "${!V[@]}" | tr ' ' '\n' | sort); do python3 - $S/$k "${V[$k]}" <<'PY'
import json,sys
d=sys.argv[1]
try:
  j=json.load(open(d+'/ck.json'))
  def g(c):
    x=j[c] if c in j else j['clocks'][0][c]
    b=x['boundary']; a=x['all']; return f"{c} pin {b['min']}..{b['max']} ({b['max']-b['min']:.1f}) all {a['min']}..{a['max']} ({a['max']-a['min']:.1f})"
  print(d.split('/')[-1], g('tt'), '|', g('ff'), '|', sys.argv[2])
except Exception as e: print(d.split('/')[-1], 'ERR', e, open(d+'/rc').read().split())
PY
done | tee $S/summary.txt
