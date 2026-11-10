#!/bin/bash
# DIE-HBM-97 KVPIPE rev3: SEQUENTIAL equivalence of ot_hbm_sm_kv_line rev2 (GOLD) and rev3 (GATE), in two inductive steps
# (yosys; no bounded simulation):
#  STEP A  (rev3 alone, -DOT_KVLINE_EQ_COPIES): `sat -tempinduct -prove-asserts` from reset: the 4 per-column copies
#          g_col[c].{h128_r, wf4_r, in_v_r, fill_r} are equal in every reachable state (k-induction).
#  STEP B  (rev2 vs the TIED form of rev3, -DOT_KVLINE_EQ_TIED = every column reads copy 3): equiv_make (registers
#          matched by name; rev2 h128 / wf4 / fill / in_v = copy 3) + equiv_struct + equiv_simple -seq 1 +
#          equiv_induct -seq 1; equiv_status -assert.
#  A + B => rev3 == rev2: in every reachable state of rev3 the copies are equal (A), so reading copy c or copy 3 gives the
#  same value and rev3 steps exactly as its tied form, which equals rev2 (B).
#  The 8 SRAM macros are cut in both steps: rd_out (rdat) is a free input (shared by gold and gate in B), their inputs
#  (rce, raddr, per-bank we / wa / wd / wm) are compared outputs; memories sc / sc1 / fn / rf are mapped to registers.
# usage: kvline_rev3_eq.sh GOLD.sv GATE.sv WORKDIR   (YOSYS=... for the binary; needs `sat` / `equiv_*`, yosys >= 0.40)
set -euo pipefail
G=$1; T=$2; W=$3; Y=${YOSYS:-yosys}
mkdir -p "$W"
cat > "$W/sram_bb.v" <<'EOF'
(* blackbox *)
module ot_sram_1r1w_64x512_m1_r2c2 (input clk, input r_ce_in, input [5:0] r_addr_in, output [511:0] rd_out,
    input w_ce_in, input [5:0] w_addr_in, input [511:0] wd_in, input [511:0] w_mask_in,
    input [1:0] rr_en, input [11:0] rr_addr, input [1:0] cr_en, input [17:0] cr_sel);
endmodule
EOF
CUT='expose -cut w:rdat
expose w:rce w:raddr w:g_bank[*].we w:g_bank[*].wa w:g_bank[*].wd w:g_bank[*].wm
delete t:ot_sram_1r1w_64x512_m1_r2c2'
# ---------------- STEP A ----------------
cat > "$W/stepA.ys" <<EOF
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
EOF
"$Y" -q -l "$W/stepA.log" -s "$W/stepA.ys" && echo "KVLINE_REV3_EQ STEP_A PASS (copies equal in every reachable state)" \
  || { echo "KVLINE_REV3_EQ STEP_A FAIL (see $W/stepA.log)"; exit 1; }
grep -E "Induction step proven|induction|SUCCESS|PASSED" "$W/stepA.log" | tail -3 || true
# ---------------- STEP B ----------------
sed 's/^module ot_hbm_sm_kv_line #(/module kvl_gold #(/' "$G" > "$W/gold.sv"
sed 's/^module ot_hbm_sm_kv_line #(/module kvl_tied #(/' "$T" > "$W/tied.sv"
grep -q '^module kvl_gold' "$W/gold.sv" && grep -q '^module kvl_tied' "$W/tied.sv"
cat > "$W/stepB.ys" <<EOF
read_verilog -sv $W/sram_bb.v
read_verilog -sv $W/gold.sv
read_verilog -sv -DOT_KVLINE_EQ_TIED $W/tied.sv
hierarchy -check
proc
memory -nomap
memory_map
opt_clean
$CUT
opt -fast
async2sync
equiv_make kvl_gold kvl_tied eq
hierarchy -top eq
equiv_struct
equiv_simple -seq 1
equiv_induct -seq 1
equiv_status
equiv_status -assert
EOF
"$Y" -q -l "$W/stepB.log" -s "$W/stepB.ys" && echo "KVLINE_REV3_EQ STEP_B PASS (tied rev3 == rev2)" \
  || { echo "KVLINE_REV3_EQ STEP_B FAIL (see $W/stepB.log)"; grep -E "Found [0-9]+ .*equiv|Unproven|unproven" "$W/stepB.log" | tail -20; exit 1; }
grep -E "Found [0-9]+ \\\$equiv cells|proven" "$W/stepB.log" | tail -3
echo "KVLINE_REV3_EQ PASS (A + B: rev3 == rev2 sequentially)"
