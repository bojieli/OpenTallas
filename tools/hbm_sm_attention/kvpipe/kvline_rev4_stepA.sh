#!/bin/bash
# DIE-HBM-97 KVPIPE rev4 equivalence STEP A (yosys k-induction, no bounded simulation), -DOT_KVLINE_EQ_COPIES:
# from reset, in every reachable state of rev4
#   (1) the NC = 16 group copies g_col[g].{h128_r, wf4_r, in_v_r, fill_r} are equal, and
#   (2) each copy's pre-decoded registers equal the decode of its own fill / format:
#       ge_r == (fill_r >= rqw(h128_r, wf4_r)),  win_r[m] == (fill_r == 6g - 16 + m), m = 0 .. 21.
# With (1) + (2) every group may read copy CC's fill / format and decode them combinationally (-DOT_KVLINE_EQ_TIED),
# which is the form STEP B (repo LEC tools/die_plan/lec.py, golden = rev3s = rev3 + the same two bank-edge stages)
# compares.  The 8 SRAM macros are cut: rd_out is a free input, their inputs are outputs (not constrained).
# usage: kvline_rev4_stepA.sh REV4.sv WORKDIR    (YOSYS=... binary, yosys >= 0.40)
set -euo pipefail
T=$1; W=$2; Y=${YOSYS:-yosys}
mkdir -p "$W"
cat > "$W/sram_bb.v" <<'EOV'
(* blackbox *)
module ot_sram_1r1w_64x512_m1_r2c2 (input clk, input r_ce_in, input [5:0] r_addr_in, output [511:0] rd_out,
    input w_ce_in, input [5:0] w_addr_in, input [511:0] wd_in, input [511:0] w_mask_in,
    input [1:0] rr_en, input [11:0] rr_addr, input [1:0] cr_en, input [17:0] cr_sel);
endmodule
EOV
cat > "$W/stepA.ys" <<EOY
read_verilog -sv $W/sram_bb.v
read_verilog -sv -formal -DOT_KVLINE_EQ_COPIES $T
hierarchy -check -top ot_hbm_sm_kv_line
proc
memory -nomap
memory_map
delete t:ot_sram_1r1w_64x512_m1_r2c2
delete -port o:*
opt_clean
opt -fast
async2sync
stat
sat -tempinduct -prove-asserts -set-at 1 rst_n 0 -maxsteps 6 -verify -show-ports
EOY
"$Y" -q -l "$W/stepA.log" -s "$W/stepA.ys" && echo "KVLINE_REV4_EQ STEP_A PASS (copies equal, pre-decodes equal their decode, every reachable state)" \
  || { echo "KVLINE_REV4_EQ STEP_A FAIL (see $W/stepA.log)"; exit 1; }
grep -E "Induction step proven|SUCCESS|PASSED" "$W/stepA.log" | tail -3 || true
