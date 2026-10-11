#!/bin/bash
# st_yosys.sh <src> <master> <out.json> [yosys define, e.g. MUT_SEATP]: bit-level flattened netlist of one VM8 half for
# subtile.py (SRAM / ot_fwd_clk_inv kept as cells).  YOSYS=<binary> (default: the ORFS image yosys when run inside it).
S=$1; M=$2; O=$3; DEF=${4:+-D$4}; Y=${YOSYS:-yosys}; V=$S/physical/hbm_accel_die_views
cat > $O.ys <<EOT
read_verilog -sv -lib $S/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v
read_verilog -sv $DEF $V/common/ot_hfd_oreg1.sv $V/vm/vcut8/ot_hfd_oreg_fc.sv $S/rtl/common/ot_fwd_link_stage.sv $V/vm/tiles/ot_hfd_vm_slice.sv $V/vm/tiles/ot_hfd_vm_root_x.sv $V/vm/vcut8/$M.sv
hierarchy -top $M
setattr -mod -set keep_hierarchy 1 ot_fwd_clk_inv
proc; flatten; opt_clean; opt_expr; memory -nomap; memory_map; opt_expr; opt_clean
techmap; opt_expr; opt_clean -purge   # no opt_merge: every RTL flop stays (the flat flow keeps the oreg chains with SYNTH_KEEP_MODULES)
stat
write_json $O
EOT
$Y -q -l $O.log $O.ys > /dev/null 2>&1; echo rc=$?; grep -A40 "Number of cells" $O.log | grep -E "cells|\\\$_|ot_" | head -30
