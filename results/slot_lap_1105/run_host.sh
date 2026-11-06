#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
R=/srv/opentallas-scratch2/claude/codex-kv-ring;O=$R/results/slot_lap_1105
cd $O
grep -q 'SUCCESS' comb.log
verilator --binary --timing -Wno-fatal -j 8 --top-module tb +define+OT_MESO_CA_SLOT_LAP $O/gold.sv $R/rtl/common/ot_meso_fifo.sv $R/rtl/common/ot_dp_clk_landing.sv $R/rtl/common/ot_dp_clk_landing_ca.sv $O/tb.sv >build.log 2>&1
./obj_dir/Vtb >bench.log 2>&1
verilator --binary --timing -Wno-fatal -j 8 --Mdir obj_mut --top-module tb +define+OT_MESO_CA_SLOT_LAP+OT_MESO_CA_MUTANT_SLOT_LAP $O/gold.sv $R/rtl/common/ot_meso_fifo.sv $R/rtl/common/ot_dp_clk_landing.sv $R/rtl/common/ot_dp_clk_landing_ca.sv $O/tb.sv >build_mut.log 2>&1
set +e
./obj_mut/Vtb >mutant.log 2>&1
rc=$?
set -e
[ "$rc" != 0 ];grep -q MISMATCH mutant.log
echo PASS_MUTANT_CAUGHT rc=$rc
