#!/bin/bash
# usage: chain_gated.sh <dir> <tile_um> <grt_threads> <grt_mem_gb> <drt_threads> <drt_mem_gb> [drt_iters]
# GRT, then DRT ONLY when the final GRT congestion report says total overflow == 0 (owner rule: never detail-route a
# congested global route). The gate verdict is written to <dir>/gate.txt either way.
set -u -o pipefail
cd /srv/opentallas-scratch/claude/qwen-die-r20/dietop_r21
D=$1; TILE=$2; GT=$3; GM=$4; DT=$5; DM=$6; IT=${7:-64}
./dietop_run.sh $D grt.tcl $GT $GM OT_ITERS=30 OT_TILE_UM=$TILE
mkdir -p $D/grt_stage; mv $D/rss.tsv $D/run.start $D/run.end $D/run.exit $D/grt_stage/ 2>/dev/null
if ! grep -q OT_GRT_DONE $D/grt.log; then echo "GATE FAIL: no OT_GRT_DONE" > $D/gate.txt; exit 1; fi
OV=$(awk '/Final congestion report/{f=1} f && /^Total/{print $NF; exit}' $D/grt.log)
if [ "$OV" != "0" ]; then echo "GATE FAIL: GRT total overflow=$OV (DRT not launched)" > $D/gate.txt; exit 2; fi
echo "GATE PASS: GRT total overflow=0 -> DRT" > $D/gate.txt
./dietop_run.sh $D drt.tcl $DT $DM OT_DRT_ITERS=$IT
