#!/bin/bash
# setup_variant.sh SRCKIT DSTKIT NX NY   -- copy a kit + its 3_place checkpoint; apply the regional-tap CTS recipe
set -euo pipefail
S=$1; D=$2; NX=$3; NY=$4; P=/srv/opentallas-scratch2/claude/s81-cores-split/probe
mkdir -p $D
rsync -a --exclude run --exclude views --exclude signoff --exclude 'sta_*' --exclude '*.log' --exclude '__pycache__' $S/ $D/
B=$(ls -d $S/run/results/asap7/*/base); N=$(basename $(dirname $B))
mkdir -p $D/run/results/asap7/$N/base $D/run/logs/asap7/$N/base $D/run/reports/asap7/$N/base
cp -p $B/3_place.odb $B/3_place.sdc $D/run/results/asap7/$N/base/
[ -d $S/run/objects ] && rsync -a $S/run/objects $D/run/
cp $P/regional_taps.tcl $P/regional_taps_balance.tcl $D/
cat >> $D/config.mk <<EOM

# S81-CORES/SPLIT 2026-10-25 structured clock (owner 10-23 MSCTS rule, decision 5, COORD F3/F5): regional taps on a
# symmetric buffered H-tree from the clk pin, SRAM clk pin + interface registers on their own skew-group tap, taps balanced
# <= 20 ps; local TritonCTS trees short (diameter 30 um), obstruction-aware (no leaf runs over the SRAM), full macro/register
# latency balance (derate 1.0).  hold_budget.tcl (repair at 100% buffers) dropped: default buffer budget.
export PRE_CTS_TCL = /work/regional_taps.tcl
export POST_CTS_TCL = /work/regional_taps_balance.tcl
export OT_RT_NX = $NX
export OT_RT_NY = $NY
export OT_RT_WIN_PS = 20
export CTS_ARGS = -sink_clustering_enable -obstruction_aware -sink_clustering_size 24 -sink_clustering_max_diameter 30 -delay_buffer_derate 1.0 -repair_clock_nets
EOM
echo "setup $D ($N) NX=$NX NY=$NY"
