#!/bin/bash
set -u
cd "$(dirname "$0")"
export CCACHE_DISABLE=1
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --assert -Wno-fatal --top-module head_guard_tb --output-groups 4 -j 2 -CFLAGS '-O1 -fno-var-tracking' -Mdir obj tb.sv controls.sv start_stages.sv ot_dp_cells.sv ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv ot_meso_fifo.sv > build.log 2>&1
rc=$?; echo "$rc" > build.rc
[ "$rc" -eq 0 ] || exit "$rc"
obj/Vhead_guard_tb > TT.log 2>&1
rc=$?; echo "$rc" > TT.rc
[ "$rc" -eq 0 ] || exit "$rc"
obj/Vhead_guard_tb +FF > FF.log 2>&1
rc=$?; echo "$rc" > FF.rc
[ "$rc" -eq 0 ] || exit "$rc"
# These are diagnostic observations. Local count faults are results to diagnose,
# and upstream propagated faults are deliberately absent from this finite cut.
echo 'GUARD_DIAGNOSTIC_COMPLETE: read individual TT/FF statuses'
