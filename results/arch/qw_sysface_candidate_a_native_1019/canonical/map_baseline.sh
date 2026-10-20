#!/bin/bash
set -euo pipefail
mkdir -p baseline_map
P=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 tools/hbm_int8_safe_source/merge_libs.py baseline_map/comb.lib "$P"/asap7sc7p5t_AO_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_INVBUF_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_OA_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_SIMPLE_RVT_TT_*.lib.gz
cp "$P/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" baseline_map/seq.lib
python3 tools/hbm_int8_safe_source/merge_libs.py baseline_map/all.lib baseline_map/comb.lib baseline_map/seq.lib
export OT_KEEP_PIN_REGS=1 DESIGN_NAME=ot_smh_int8_tile_safe
yosys -Q -T -p 'read_liberty -lib baseline_map/all.lib; read_verilog -sv -DSYNTHESIS rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv tools/hbm_int8_safe_source/baseline_wrapper.sv; hierarchy -check -top ot_smh_int8_tile_safe; flatten; tcl tools/hbm_int8_safe_source/ot_keep_regs.tcl; synth -top ot_smh_int8_tile_safe -flatten -noabc; dfflibmap -liberty baseline_map/seq.lib; abc -liberty baseline_map/comb.lib; clean; stat -liberty baseline_map/all.lib; write_verilog -noattr baseline_map/netlist.v; write_json baseline_map/netlist.json' > baseline_map/yosys.log 2>&1
