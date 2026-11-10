#!/bin/bash
# DIE-HBM-97 KVPIPE rev3: SEQUENTIAL equivalence rev2 (gold, GOLD_SHA) == rev3 (gate, this tree) of ot_hbm_sm_kv_line,
# yosys equiv_make / equiv_struct / equiv_induct (one inductive proof over the whole state: every $equiv is assumed
# at step 1 and proven at step 2, so the result holds for every reachable state; no bounded run).
#  - the 8 SRAM macros are cut: their outputs (rdat) become a shared free input, their inputs (rce, raddr, per-bank
#    we / wa / wd / wm) become compared outputs, so the proof covers every value the banks can return;
#  - sc / sc1 / fn / rf memories are mapped to registers (memory -nomap; memory_map) and matched by name;
#  - the rev3 copies g_col[c].{h128_r, wf4_r, fill_r, in_v_r} are matched to the rev2 registers h128 / wf4 / fill / in_v
#    with equiv_add (the induction then proves every copy equals the rev2 register in every reachable state).
# usage: kvline_rev3_eq.sh GOLD.sv GATE.sv WORKDIR   (run with yosys >= 0.40 on PATH or YOSYS=...)
set -euo pipefail
G=$1; T=$2; W=$3; Y=${YOSYS:-yosys}
mkdir -p "$W"
sed 's/^module ot_hbm_sm_kv_line #(/module kvl_gold #(/' "$G" > "$W/gold.sv"
sed 's/^module ot_hbm_sm_kv_line #(/module kvl_gate #(/' "$T" > "$W/gate.sv"
grep -q '^module kvl_gold' "$W/gold.sv" && grep -q '^module kvl_gate' "$W/gate.sv"
cat > "$W/sram_bb.v" <<'EOF'
(* blackbox *)
module ot_sram_1r1w_64x512_m1_r2c2 (input clk, input r_ce_in, input [5:0] r_addr_in, output [511:0] rd_out,
    input w_ce_in, input [5:0] w_addr_in, input [511:0] wd_in, input [511:0] w_mask_in,
    input [1:0] rr_en, input [11:0] rr_addr, input [1:0] cr_en, input [17:0] cr_sel);
endmodule
EOF
cat > "$W/eq.ys" <<EOF
read_verilog -sv $W/sram_bb.v
read_verilog -sv $W/gold.sv
read_verilog -sv $W/gate.sv
hierarchy -check
proc
memory -nomap
memory_map
opt_clean
# cut the macros: rdat = free shared input, bank inputs = compared outputs
expose -cut w:rdat
expose w:rce w:raddr w:g_bank[*].we w:g_bank[*].wa w:g_bank[*].wd w:g_bank[*].wm
delete t:ot_sram_1r1w_64x512_m1_r2c2
opt -fast
async2sync
equiv_make kvl_gold kvl_gate eq
hierarchy -top eq
cd eq
EOF
for c in 0 1 2 3; do
  for p in "h128 g_col[$c].h128_r" "wf4 g_col[$c].wf4_r" "fill g_col[$c].fill_r" "in_v g_col[$c].in_v_r"; do
    set -- $p
    echo "equiv_add -try \\${1}_gold \\${2}_gate" >> "$W/eq.ys"
  done
done
cat >> "$W/eq.ys" <<'EOF'
cd ..
equiv_struct
equiv_induct -seq 1
equiv_status
equiv_status -assert
EOF
"$Y" -q -l "$W/eq.log" -s "$W/eq.ys" && echo "KVLINE_REV3_EQ PASS" || { echo "KVLINE_REV3_EQ FAIL (see $W/eq.log)"; grep -E "Found|unproven|Unproven|ERROR" "$W/eq.log" | tail -20; exit 1; }
grep -E "Found [0-9]+ \\\$equiv cells|proven|unproven" "$W/eq.log" | tail -5
