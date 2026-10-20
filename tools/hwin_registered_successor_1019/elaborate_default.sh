#!/usr/bin/env bash
set -euo pipefail
root=${1:?immutable src root}; projection=${2:?existing completed parser projection root}; out=${3:?fresh output}
mkdir "$out" || { echo "REFUSE existing output $out"; exit 73; }
cat > "$out/tb.sv" <<'SV'
module tb;
 reg ck=0,rst_n=0;wire [135:0] a,b;wire [43:0] c,d;wire [1:0] e,f;
 dsdv_mu_hwin_capture_1019 #(.NSLOT(47),.NEV(16),.NEP(4),.NRT(2),.HEAD_STAGE(1),.COMPACT_PTR(1),.CHECK_STAGE(1),.LIVE_COUNT(1),.RAW_SELECT(1),.LOCAL_BOOT(1)) dut_default(.ck(ck),.rst_n(rst_n),.f_ks(53'd0),.f_mc(26'd0),.f_mw(26'd0),.mu_rt(64'd0),.mu_c(a),.mu_rc(c),.t_wf(e));
 dsdv_mu_hwin_capture_1019 #(.NSLOT(47),.NEV(16),.NEP(4),.NRT(2),.HEAD_STAGE(1),.COMPACT_PTR(1),.CHECK_STAGE(1),.LIVE_COUNT(1),.RAW_SELECT(1),.LOCAL_BOOT(1),.EARLY_HEAD_CAPTURE(1)) dut_opt(.ck(ck),.rst_n(rst_n),.f_ks(53'd0),.f_mc(26'd0),.f_mw(26'd0),.mu_rt(64'd0),.mu_c(b),.mu_rc(d),.t_wf(f));
endmodule
SV
files=("$out/tb.sv" "$projection/dsdv_mu_hwin_capture_1019.sv" "$projection/dsdv_mu_hwin_capture_mem_1019.sv" "$projection/dsdv_mu_hwin_capture_early_1019.sv" "$root/tools/hwin_private_package_1019/sim/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v")
sha256sum "${files[@]}" > "$out/sources.sha256"
iverilog -g2012 -s tb -DOT_MEM_NO_INIT -o "$out/tb.vvp" "${files[@]}" > "$out/build.log" 2>&1
sha256sum "$out/tb.vvp" > "$out/vvp.sha256"
echo ELABORATION_ONLY_PASS
