#!/bin/bash
# DIE-HEAD-10 FSTART out: the forwarded start face flop equals the region start every cycle (0 added cycles).
#  A: strap child origin as clock_landings emits it: ot_dp_landing_origin_s start_d -> ot_dp_landing_relay face flop
#     u_cland_fstart_<b> on the same raw reset: q == start, PADW 1..4 x every strap_pad x strap_efall 0/1.
#  B: the root+child strap wrapper exactly as clock_landings emits it (u_cland_root + origin_s + face flop
#     ot_dp_landing_relay u_cland_fstart_<b> on cland_raw_sel, d = selected start_d): q == cland_start for
#     strap_ca_root 0/1 (static), SETTLE 1/3/6, PADW 1/2 x every pad x efall, independent free raw resets.
#  C: root-only strap-mode wrapper (ot_dp_landing_root start_d + face flop): equal for SETTLE 1/3/6/64.
#  Mutants (must FAIL): OT_ORIGIN_MUTANT_LATE (start_d one tap late) on A and B(root=0); OT_ROOT_MUTANT_EARLY on B(root=1), C.
# Usage: fv_start_o.sh <repo> <outdir>
set -u
R=$1; O=$2; mkdir -p $O
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
pass=0; fail=0; caught=0; missed=0
run() {  # tag file mutdef expect(pass|fail)
  local tag=$1 f=$2 mut=$3 exp=$4
  docker run --rm -m 4g -v $R:$R:ro -v $O:$O openroad/orfs:asap7lock $Y -q -p "read_verilog -sv -DSYNTHESIS $mut $R/rtl/common/ot_dp_clk_landing_ca.sv $f; hierarchy -top fvtop; proc; setattr -mod -unset keep_hierarchy *; flatten; hierarchy -top fvtop; opt_clean; async2sync; dffunmap; sat -tempinduct -prove ok 1 -set-at 1 rraw 0 -set-at 1 raw 0 -seq 1 -maxsteps 80 -verify -show-ports fvtop" > $O/$tag.log 2>&1
  local rc=$?
  if [ $exp = pass ]; then if [ $rc -eq 0 ]; then echo "PASS $tag"; pass=$((pass+1)); else echo "FAIL $tag"; fail=$((fail+1)); fi
  else if [ $rc -ne 0 ]; then echo "MUTANT_CAUGHT $tag"; caught=$((caught+1)); else echo "MUTANT_MISSED $tag"; missed=$((missed+1)); fi; fi
}
for W in 1 2 3 4; do for P in $(seq 0 $(( (1<<W) - 1 ))); do for E in 0 1; do
  f=$O/a_${W}_${P}_${E}.sv
  cat > $f <<V
module fvtop(input wire clk, input wire raw, input wire rraw, input wire p_start, output wire ok);
  wire start, start_o, start_d;
  ot_dp_landing_origin_s #(.PADW($W)) u (.clk(clk), .rst_raw_n(raw), .p_start(p_start), .strap_efall(1'b$E),
      .strap_pad($W'd$P), .start(start), .start_d(start_d));
  ot_dp_landing_relay u_cland_fstart_o (.clk(clk), .rst_raw_n(raw), .d(start_d), .q(start_o));
  assign ok = (start == start_o);
endmodule
V
  run A_W${W}_P${P}_E${E} $f "" pass
  run A_W${W}_P${P}_E${E}_MUT $f "-DOT_ORIGIN_MUTANT_LATE" fail
done; done; done
for S in 1 3 6; do for W in 1 2; do for P in $(seq 0 $(( (1<<W) - 1 ))); do for E in 0 1; do for RT in 0 1; do
  f=$O/b_${S}_${W}_${P}_${E}_${RT}.sv
  cat > $f <<V
module fvtop(input wire clk, input wire raw, input wire rraw, input wire p_start, output wire ok);
  wire strap_ca_root = 1'b$RT;
  wire cland_start, cland_start_o;
  wire cland_start_child, cland_start_root, cland_start_child_d, cland_start_root_d;
  wire cland_raw_sel = strap_ca_root ? rraw : raw;
  ot_dp_landing_root #(.SETTLE($S)) u_cland_root (.clk(clk), .rst_raw_n(rraw), .start(cland_start_root), .start_d(cland_start_root_d));
  assign cland_start = strap_ca_root ? cland_start_root : cland_start_child;
  wire cland_start_d = strap_ca_root ? cland_start_root_d : cland_start_child_d;
  wire cland_start_raw = cland_raw_sel;
  ot_dp_landing_relay u_cland_fstart_x (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(cland_start_o));
  ot_dp_landing_origin_s #(.PADW($W)) u_cland_origin (.clk(clk), .rst_raw_n(raw), .p_start(p_start), .strap_efall(1'b$E),
      .strap_pad($W'd$P), .start(cland_start_child), .start_d(cland_start_child_d));
  assign ok = (cland_start == cland_start_o);
endmodule
V
  run B_S${S}_W${W}_P${P}_E${E}_R${RT} $f "" pass
  if [ $RT = 1 ]; then run B_S${S}_W${W}_P${P}_E${E}_R1_MUT $f "-DOT_ROOT_MUTANT_EARLY" fail
  else run B_S${S}_W${W}_P${P}_E${E}_R0_MUT $f "-DOT_ORIGIN_MUTANT_LATE" fail; fi
done; done; done; done; done
for S in 1 3 6 64; do
  f=$O/c_${S}.sv
  cat > $f <<V
module fvtop(input wire clk, input wire raw, input wire rraw, input wire p_start, output wire ok);
  wire cland_start, cland_start_o, cland_start_root_d;
  ot_dp_landing_root #(.SETTLE($S)) u_cland_origin (.clk(clk), .rst_raw_n(raw), .start(cland_start), .start_d(cland_start_root_d));
  ot_dp_landing_relay u_cland_fstart_x (.clk(clk), .rst_raw_n(raw), .d(cland_start_root_d), .q(cland_start_o));
  assign ok = (cland_start == cland_start_o);
endmodule
V
  run C_S${S} $f "" pass
  run C_S${S}_MUT $f "-DOT_ROOT_MUTANT_EARLY" fail
done
echo "SUMMARY pass=$pass fail=$fail mutants_caught=$caught mutants_missed=$missed"
[ $fail -eq 0 ] && [ $missed -eq 0 ]
