#!/bin/bash
set -eu
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for mut in 0 1 2; do
  "$V" --binary -j 2 -Wno-fatal --top-module tb_ot_rp4_g1_capture -GMUT=$mut ot_rp4_g1_capture.sv tb_ot_rp4_g1_capture.sv -Mdir "obj$mut" > "build$mut.log" 2>&1
  set +e
  "obj$mut/Vtb_ot_rp4_g1_capture" > "bench$mut.log" 2>&1
  rc=$?
  set -e
  if [ "$mut" = 0 ]; then test "$rc" = 0; grep -q 'G1_CAPTURE PASS' bench0.log; else test "$rc" != 0; grep -q 'G1_CAPTURE FAIL' "bench$mut.log"; fi
  tail -4 "bench$mut.log"
done
L=/srv/opentallas-scratch/claude/l2h-pvmd/census/libs
yosys -Q -T -p "read_verilog -sv ot_rp4_g1_capture.sv; synth -top ot_rp4_g1_capture -flatten; dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; opt_clean -purge; write_verilog -noattr mapped.v; stat" > synth.log 2>&1
python3 textbook_lint.py check --netlist mapped.v --top ot_rp4_g1_capture --out census32.json --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 --mode refuse > census32.log 2>&1
cat census32.log
