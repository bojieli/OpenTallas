#!/bin/bash
# S81-DIE10 10-20 PARALLEL FALLBACK: export the n32s CTRL view from the daemon's READY route (route 04:55 rc0) before
# the daemon's CLOSED record exists (owner: parallel fallback routes; closure first).  Read-only on the daemon run.
# Sequence = the route's own corner_sta Tcl (no routed_ioref verdict yet) -> recorded UNCHECKED; the CLOSED record
# (waiter) supersedes it.
R=${R:-/srv/opentallas-scratch/claude/closure-loop/s81ctrl_rg2_n32s-n32s-f1f7c42d9}
W=$R/routes/s81ctrl_rg2_n32s_n32s_f1f7c42d9/work/orfs
L=$(cd $(dirname $0) && pwd); rm -rf $L/views $L/tmp; mkdir -p $L/views $L/tmp
python3 $L/view_export.py --orfs-dir $W --name dsfd_ctrl_rg2 --out $L/views --corners ss,ff,tt --forwarded-clock clk:ck_o \
  --macro-view $R/src/physical/asap7_memory_macros/ot_sram_1r1w2c_16x340_p192 --image openroad/orfs:asap7lock --tmp-dir $L/tmp > $L/export.log 2>&1
rc=$?; rm -rf $L/tmp; echo "CTRLPRE_EXPORT rc=$rc"; tail -n 2 $L/export.log; exit $rc
