#!/bin/bash
# Approved RING data-five cohort: ordinary shared PRD GRT/MM hold first, real TT/FF gates, then route.
set -euo pipefail
CPUS=$1; shift
M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$CPUS")
"${M[@]}" do-grt "$@" SKIP_INCREMENTAL_REPAIR=1 > /work/run_gated_grt.log 2>&1
O5=$(find /work/run/results/asap7 -name 5_1_grt.odb -print -quit)
test -n "$O5"
for c in TT FF; do
  OT_POSTCTS_GRT=1 OT_CORNER=$c ODB=$O5 openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_$c.log 2>&1
  grep 'OT_POSTCTS_GATE.*PASS' /work/postcts_gate_$c.log
done
python3 - <<'PY'
import json
for corner,key in [('tt','setup_wns_est_ps'),('ff','hold_wns_est_ps')]:
 d=json.load(open('/work/postcts_gate_'+corner+'.json'))
 assert d['verdict']=='PASS' and d['band_verdict']=='PASS', d
 assert d[key]>=0, d
 print('RING_PRE_ROUTE_GATE',corner,key,d[key],'mean',d['pinreg_mean_ps'],'PASS')
PY
"${M[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc "$@" SKIP_INCREMENTAL_REPAIR=1
