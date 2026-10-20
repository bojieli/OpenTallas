#!/usr/bin/env bash
# QW-SLICE7-LEAVES sc2 benches (fleet, Verilator 5.050). Usage: run_sc2.sh OUT
# eq44: sc2 LA4/LM4 vs original qfd_dv_s5_sc (MU_NU 4): OFF0 2 (face regs), merge +1, total DT 5, rsqrt DR 19.
# eq66: DT 15 DR 57; eq76 (station ADD7/MUL6): DT 20, DR 66 = 5*4 + 3 + 4 + 3*(9+4).
# mut44: OT_S5_SC2_MUT (broadcast tap reads VM window 10) must FAIL.
set -euo pipefail
O=$1; mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version | tee "$O/verilator_version.txt" | grep -q 5.050
python3 rtl/test/qwen_dv/s5_scred2/extract_ref.py rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv "$O/ref.sv"
HDC="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv"
RTL="rtl/qwen_dv/qfd_dv_scalar2.sv rtl/qwen_dv/s5/qfd_dv_s5_sc2.sv rtl/qwen_dv/s5/qfd_dv_s5_red2.sv rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv rtl/qwen_dv/qfd_dv_reset_tree.sv"
run() { # name la lm dt dr mut seed
  local n=$1 la=$2 lm=$3 dt=$4 dr=$5 mut=$6 seed=$7 defs=()
  mkdir -p "$O/$n"
  cat > "$O/$n/wrap.sv" <<W
module sc2_w (input wire ck, rst_n, input wire [100:0] sc_cfg, input wire [47:0] dn_i, output wire [47:0] dn_o,
  input wire [47:0] up_i, output wire [47:0] up_o, input wire red_we, input wire [23:0] red_addr, input wire [31:0] red_data,
  input wire [7:0] vm_we, input wire [1:0] vm_win0, input wire [31:0] vm_wdata0, input wire am_v, input wire [23:0] am_idx,
  input wire [31:0] am_val, input wire [1:0] am_u, output wire w1_we, output wire [23:0] w1_addr, output wire [31:0] w1_data,
  output wire tok_v, output wire [23:0] tok_idx, output wire tok_own, output wire [31:0] tok_val, output wire [1:0] tok_user,
  output wire busy, fault);
  qfd_dv_s5_sc2 #(.MU_NU(4), .LA($la), .LM($lm)) u (.*);
endmodule
W
  [[ $mut == 0 ]] || defs+=(+define+OT_S5_SC2_MUT)
  "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign unique --x-initial unique \
    "${defs[@]}" +define+DUTMOD=sc2_w +define+REFMOD=ref_s5_sc +define+OFF0=2 +define+DT=$dt +define+DR=$dr --top-module tb_sc2 \
    "$O/ref.sv" "$O/$n/wrap.sv" $RTL $HDC rtl/test/qwen_dv/s5_scred2/tb_sc2.sv -Mdir "$O/$n/obj" > "$O/$n/build.log" 2>&1
  set +e; "$O/$n/obj/Vtb_sc2" +seed=$seed +rounds=40 +verilator+seed+$seed +verilator+rand+reset+2 > "$O/$n/run.log" 2>&1; local rc=$?; set -e
  tail -4 "$O/$n/run.log"
  if [[ $mut == 0 ]]; then [[ $rc == 0 ]] && grep -q 'SC2_EQ PASS' "$O/$n/run.log"; else [[ $rc != 0 ]] && grep -q 'SC2_EQ FAIL' "$O/$n/run.log"; fi
}
st=0
run eq44 4 4 5 19 0 7 || st=1
run eq44s2 4 4 5 19 0 11 || st=1
run mut44 4 4 5 19 1 7 || st=1
run eq66 6 6 15 57 0 7 || st=1
run eq76 7 6 20 66 0 7 || st=1
run eq76s2 7 6 20 66 0 11 || st=1
run mut76 7 6 20 66 1 7 || st=1
run eq79 7 9 20 96 0 7 || st=1
echo "SC2_BENCH_DONE status=$st"
exit $st
