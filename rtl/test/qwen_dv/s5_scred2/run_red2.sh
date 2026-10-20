#!/usr/bin/env bash
# QW-SLICE7-LEAVES red2 benches (fleet, Verilator 5.050). Usage: run_red2.sh OUT [DUT_SV...]
# eq44: red2 LA4/LM4 vs original qfd_dv_s5_red, OFF 14 (2 face + 1 + 11); eq45: LA4/LM5 OFF 15;
# eq66: LA6/LM6 OFF 38; eq76: LA7/LM6 (station ADD7/MUL6) OFF 49 (2 + 3 + 44); mut76 must FAIL.
# mut44: red2 LA4/LM4 with OT_S5_RED2_MUT (SUM taken as MAX) must FAIL.
set -euo pipefail
O=$1; mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version | tee "$O/verilator_version.txt" | grep -q 5.050
python3 rtl/test/qwen_dv/s5_scred2/extract_ref.py rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv "$O/ref.sv"
HDC="rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv"
RTL="rtl/qwen_dv/s5/qfd_dv_s5_red2.sv rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv rtl/qwen_dv/qfd_dv_reset_tree.sv"
run() { # name la lm off mut
  local n=$1 la=$2 lm=$3 off=$4 mut=$5 defs=()
  mkdir -p "$O/$n"
  cat > "$O/$n/wrap.sv" <<W
module red2_w (input wire ck, rst_n, input wire [7:0] l_ov, input wire [255:0] l_out, input wire [1:0] l_red0,
  input wire l_redsq0, l_last0, input wire [23:0] l_raddr0, output wire red_we, output wire [23:0] red_addr,
  output wire [31:0] red_data, output wire rd_v, busy, fault);
  qfd_dv_s5_red2 #(.LA($la), .LM($lm)) u (.*);
endmodule
W
  [[ $mut == 0 ]] || defs+=(+define+OT_S5_RED2_MUT)
  "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign unique --x-initial unique \
    "${defs[@]}" +define+DUTMOD=red2_w +define+REFMOD=ref_s5_red +define+OFF=$off +define+RDOFF=2 --top-module tb_red2 \
    "$O/ref.sv" "$O/$n/wrap.sv" $RTL $HDC rtl/test/qwen_dv/s5_scred2/tb_red2.sv -Mdir "$O/$n/obj" > "$O/$n/build.log" 2>&1
  set +e; "$O/$n/obj/Vtb_red2" +seed=7 +segs=3000 +verilator+seed+7 +verilator+rand+reset+2 > "$O/$n/run.log" 2>&1; local rc=$?; set -e
  tail -3 "$O/$n/run.log"
  if [[ $mut == 0 ]]; then [[ $rc == 0 ]] && grep -q 'RED2_EQ PASS' "$O/$n/run.log"; else [[ $rc != 0 ]] && grep -q 'RED2_EQ FAIL' "$O/$n/run.log"; fi
}
st=0
run eq44 4 4 14 0 || st=1
run eq45 4 5 15 0 || st=1
run eq66 6 6 38 0 || st=1
run eq76 7 6 49 0 || st=1
run mut76 7 6 49 1 || st=1
run eq79 7 9 52 0 || st=1
run mut44 4 4 14 1 || st=1
echo "RED2_BENCH_DONE status=$st"
exit $st
