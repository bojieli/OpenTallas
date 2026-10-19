#!/bin/bash
set -euo pipefail
mkdir -p out
T=tools/hbm_hidx_coupon1
P=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 "$T/merge_libs.py" out/comb.lib "$P"/asap7sc7p5t_AO_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_INVBUF_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_OA_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_SIMPLE_RVT_TT_*.lib.gz
cp "$P/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" out/seq.lib
python3 "$T/merge_libs.py" out/all.lib out/comb.lib out/seq.lib
export OT_KEEP_PIN_REGS=1 DESIGN_NAME=hidx_coupon1
# Existing canonical hook and keep_hierarchy, with normal synth -flatten.
# Final explicit flatten is representation-only AFTER native mapping; no opt.
yosys -Q -T -p 'read_liberty -lib out/all.lib; read_verilog -sv tools/hbm_hidx_coupon1/coupon.sv; chparam -set ENABLE 1 hidx_coupon1; hierarchy -check -top hidx_coupon1; tcl tools/hbm_hidx_coupon1/ot_keep_regs.tcl; synth -top hidx_coupon1 -flatten -noabc; dfflibmap -liberty out/seq.lib; abc -liberty out/comb.lib; clean; stat -liberty out/all.lib; write_json out/hierarchical.json; setattr -mod -unset keep_hierarchy; flatten; write_verilog -noattr out/netlist.v; write_json out/netlist.json' >out/yosys.log 2>&1

python3 tools/hbm_hidx_coupon1/native.py
bash tools/hbm_hidx_coupon1/formal.sh
