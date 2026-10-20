#!/bin/bash
set -eu
L=/srv/opentallas-scratch/claude/l2h-pvmd/census/libs
H=/srv/opentallas-scratch/claude/ref_gate/smh_rp4hs_a_km64-20261019-214641/src/physical/common_flow/ot_keep_regs.tcl
yosys -Q -T -p "read_verilog -sv ot_rp4_g1_capture.sv; hierarchy -check -top ot_rp4_g1_capture; tcl $H; synth -top ot_rp4_g1_capture -flatten; dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; opt_clean -purge; write_verilog -noattr mapped_hook.v; stat" > synth_hook.log 2>&1
python3 textbook_lint.py check --netlist mapped_hook.v --top ot_rp4_g1_capture --out census32_hook.json --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 --waive reset_landing --mode refuse > census32_hook.log 2>&1
cat census32_hook.log
