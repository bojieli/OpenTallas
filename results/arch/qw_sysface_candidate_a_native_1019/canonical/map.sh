#!/bin/bash
set -euo pipefail
mkdir -p mapped2
P=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 tools/hbm_int8_safe_source/merge_libs.py mapped2/comb.lib "$P"/asap7sc7p5t_AO_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_INVBUF_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_OA_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_SIMPLE_RVT_TT_*.lib.gz
cp "$P/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" mapped2/seq.lib
python3 tools/hbm_int8_safe_source/merge_libs.py mapped2/all.lib mapped2/comb.lib mapped2/seq.lib
export OT_KEEP_PIN_REGS=1 DESIGN_NAME=ot_smh_int8_tile_safe
yosys -Q -T -p 'read_liberty -lib mapped2/all.lib; read_verilog -sv -DSYNTHESIS rtl/hbm_accel/sm/static/ot_smh_int8_tile_safe.sv; hierarchy -check -top ot_smh_int8_tile_safe; tcl tools/hbm_int8_safe_source/ot_keep_regs.tcl; synth -top ot_smh_int8_tile_safe -flatten -noabc; dfflibmap -liberty mapped2/seq.lib; abc -liberty mapped2/comb.lib; clean; stat -liberty mapped2/all.lib; write_verilog -noattr mapped2/netlist.v; write_json mapped2/netlist.json' > mapped2/yosys.log 2>&1
