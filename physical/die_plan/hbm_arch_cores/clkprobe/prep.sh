#!/bin/bash
# prep.sh SRC_RUN_DIR DST : copy a CTS-failed core run (kit + run/ through 3_place), drop CTS products, add density taps
set -euo pipefail
S=$1; D=$2; T=$(dirname $(readlink -f $0))
rm -rf "$D"; cp -a "$S" "$D"
rm -f $D/run/results/asap7/*/base/4_* $D/run/logs/asap7/*/base/4_* $D/run/reports/asap7/*/base/4_* $D/FAIL_POSTCTS $D/hold_gate.log $D/placed.csv
cp $T/core_density_taps.tcl $T/core_tap_align.tcl $D/
cat >> $D/config.mk <<'EOC'
# HBM-CLKSTRUCT 2026-10-25: structured in-core clock (port -> balanced trunk -> density taps -> local trees -> tap alignment)
export PRE_CTS_TCL = /work/core_density_taps.tcl
export OT_DTAP_TARGET = 1250
export OT_DTAP_DMAX_UM = 80
export OT_DTAP_OUT = /work/dtap.txt
override export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -sink_clustering_max_diameter 30 -sink_clustering_size 20 -distance_between_buffers 40 -balance_levels
override export POST_CTS_TCL = /work/core_tap_align.tcl
EOC
echo prepared $D
