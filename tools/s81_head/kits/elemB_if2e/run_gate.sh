#!/bin/bash
# PATH-S81/ELEMB: GRT-mode post-CTS gate (main postcts_gate.tcl, OT_POSTCTS_GRT=1, setRC_rcx) + per-sink clock dump
K=$(cd "$1" && pwd); IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
R=$K/run/results/asap7/hd_elemB_rb/base
[ -f $R/5_1_grt.odb ] || { echo "GATE: no 5_1_grt.odb"; exit 2; }
mkdir -p $K/gate
docker run --rm --name egate-$(basename $K)-$$ --memory=40g -v $K:/work -w /work $IMAGE bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  for C in TT FF; do OT_CORNER=\$C OT_POSTCTS_GRT=1 ODB=/work/run/results/asap7/hd_elemB_rb/base/5_1_grt.odb openroad -exit /work/postcts_gate.tcl > /work/gate/postcts_gate_\$C.log 2>&1 & \
  C=\$C MODE=grt OUT=/work/gate ODB=/work/run/results/asap7/hd_elemB_rb/base/5_1_grt.odb openroad -exit /work/ckdump2.tcl > /work/gate/ckdump_\$C.log 2>&1 & done; wait; \
  cp /work/postcts_gate_*.json /work/gate/ 2>/dev/null; chown -R \$(stat -c %u:%g /work) /work/gate /work/postcts_gate_*.json"
grep -h "STA_\|verdict\|POSTCTS" $K/gate/*.log | head; cat $K/gate/postcts_gate_*.json 2>/dev/null
