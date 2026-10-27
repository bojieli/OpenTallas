#!/bin/bash
# sta.sh NAME [extra args]  PATH-S81-PD13: main die_sta_related.py (471dd392b5) on me1v (PD12 via build), table AOCV 0.21 %/mm,
# signed-mesh MC (PD12 gap-fold mc/me1v_{TT,FF}.json, per-pair U), droop per mesh, HB4 per endpoint, 11 PD6 core views
R=/srv/opentallas-scratch2/claude/path-s81-pd12-1027; T=/srv/opentallas-scratch2/claude/wt/main-tools-pd13/tools/die_plan
P=/srv/opentallas-scratch2/claude/path-s81-pd7-1026/d/src/die_plan_pd7_composed.json; V=/srv/opentallas-scratch2/claude/path-s81-pd6-1026/sta/views
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r18-1027/in/pylib:$T; cd $R; N=$1; shift; ulimit -v 96000000
CV=""; for m in $(ls $V); do CV="$CV --core-view $m=$V/$m"; done
echo "$N start $(date -Is) main $(git -C $T rev-parse --short=10 HEAD)" > pd13/$N.run
python3 $T/die_sta_related.py ${PROOF:-me1v} --plan $P --out pd13/$N --clock-tool $T $CV --clock-ocv table --mesh-signoff ${MSO:-TT=mc/me1v_TT.json,FF=mc/me1v_FF.json} \
  --hold-buffers HB4 --core-latency-ff 202.5 --droop-region mesh "$@" > pd13/$N.log 2>&1
echo "$N rc=$? $(date -Is)" >> pd13/$N.run
