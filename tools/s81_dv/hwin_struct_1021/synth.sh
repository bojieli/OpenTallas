#!/usr/bin/env bash
# Technology-independent sizing only; no physical/area/clock qualification.
set -euo pipefail
O=${1:?outdir}; mkdir -p "$O"
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
R=rtl/dsrom_sys/s81_dv/unit
D=tools/hwin_private_package_1019
if [ ! -d "$D" ]; then
  mkdir -p "$O/deps"
  git archive e20095385d2024cabe267f4227e1fb17c24dac90 tools/hwin_private_package_1019 | tar -x -C "$O/deps"
  D=$O/deps/tools/hwin_private_package_1019
fi
M=$D/sim/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v
for v in 0 1; do
cat > "$O/top$v.sv" <<EOF
module ot_cost_top(input ck,rst_n,input [52:0] f_ks,input [25:0] f_mc,f_mw,input [63:0] mu_rt,output [135:0] mu_c,output [43:0] mu_rc,output [1:0] t_wf);
dsdv_mu_hwin_capture_1019 #(.NSLOT(47),.NEV(16),.NEP(4),.NRT(2),.HEAD_STAGE(1),.COMPACT_PTR(1),.CHECK_STAGE(1),.LIVE_COUNT(1),.RAW_SELECT(1),.LOCAL_BOOT(1),.EARLY_HEAD_CAPTURE(1),.CFG_RELAY(1),.DUE_COPIES(2),.SAFE_NATIVE(1),.LOCAL_RECORD($v)) u (.*);
endmodule
EOF
cat > "$O/v$v.ys" <<EOF
read_verilog -lib $M
read_verilog -sv -DSYNTHESIS $R/dsdv_mu_hwin_capture_mem_1019.sv $R/dsdv_mu_hwin_capture_early_1019.sv $R/dsdv_mu_hwin_capture_1019.sv
read_verilog -sv $O/top$v.sv
hierarchy -top ot_cost_top
synth -top ot_cost_top -noabc
tee -o $O/v$v.json stat -json
write_json $O/v$v.net.json
EOF
"$Y" -Q -T -s "$O/v$v.ys" > "$O/v$v.log" 2>&1
done
