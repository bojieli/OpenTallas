#!/bin/bash
# sta.sh NAME SCRIPT [extra args]  PATH-S81-PD9: shared main die_sta_related.py (0f9789993e) on the me1 mesh build,
# table AOCV 0.21 %/mm, signed-mesh MC (mc/me1_{TT,FF}.json), droop per mesh, HB4 per endpoint, 11 real core views (PD6 set)
R=/srv/opentallas-scratch2/claude/path-s81-pd7-1026/pd9; T=/srv/opentallas-scratch2/claude/wt/main-tools-pd9/tools/die_plan
P9=/srv/opentallas-scratch2/claude/wt/path-s81-pd9-1027/tools/die_plan
P=/srv/opentallas-scratch2/claude/path-s81-pd7-1026/d/src/die_plan_pd7_composed.json; V=/srv/opentallas-scratch2/claude/path-s81-pd6-1026/sta/views
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r18-1027/in/pylib:$T; cd $R; mkdir -p sta; N=$1; S=$2; shift 2; ulimit -v 64000000
CV=""; for m in $(ls $V); do CV="$CV --core-view $m=$V/$m"; done
python3 $S me1 --plan $P --out sta/$N --clock-tool $T $CV --clock-ocv table ${MS---mesh-signoff TT=mc/me1_TT.json,FF=mc/me1_FF.json} \
  --hold-buffers HB4 --core-latency-ff 202.5 --droop-region mesh "$@" > sta/$N.log 2>&1
echo "$N rc=$? $(date -Is)" | tee sta/$N.run
