#!/bin/bash
# prep_f4.sh SRC_DTAP_RUN DST : re-run CTS of a density-tap run with the current hook versions (F4 same-tap zero-logic pairs)
set -euo pipefail
S=$1; D=$2; T=$(dirname $(readlink -f $0))
rm -rf "$D"; cp -a "$S" "$D"
rm -f $D/run/results/asap7/*/base/4_* $D/run/logs/asap7/*/base/4_* $D/run/reports/asap7/*/base/4_* $D/FAIL_POSTCTS $D/hold_gate.log $D/placed.csv $D/dtap.txt $D/run_cts.log
cp $T/core_density_taps.tcl $T/core_tap_align.tcl $D/
echo prepared $D
