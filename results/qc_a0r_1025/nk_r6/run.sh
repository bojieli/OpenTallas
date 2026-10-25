#!/bin/bash
# PATH-QC-NK2 2026-10-25 R6 (qfd_tile_nk_a0cv10): R5 (v9) + LSL fp1 x8 and rb0 ROM-leaf pair on core-only taps at their clock pins,
# 3 re-pitch flop taps (ck_t50..52), RTL ports ck_t42..52 (no loads).  src = R5 src snapshot + claude/path-qc-nk2-1025 changes,
# kit generated before launch.  synth -> place -> CTS (SKIP_CTS_REPAIR_TIMING=1, as the autopilot adapter) -> FF hold gate on the
# v10 signoff.sdc.  Stops before route (GEOM REQ [PATH-QC-NK-R6]).
B=/srv/opentallas-scratch2/claude/path-qc-nk2/r6
cd "$B/src"
echo "start $(date -Is)" > "$B/place.log"
export OT_ORFS_CORNER_OVERRIDE=TC
HM=0.003 OT_MM_FF_SDC=physical/ref_tile/qfd_tile_nk_a0cv10/signoff.sdc SRC="$B/src" OT_PIN_GROUP_MAX=32 NC=16 \
  bash tools/ref_tile/ref_route.sh physical/ref_tile/qfd_tile_nk_a0cv10/kit.env r6 "$B/run" place >> "$B/place.log" 2>&1 || { echo place rc $?; exit 2; }
# CTS + FF gate: cts.sh (the inline docker tail here was lost to a quoting error on 10:15; place ran, CTS relaunched 10:53)
bash $B/cts.sh
