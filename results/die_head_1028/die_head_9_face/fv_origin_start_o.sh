#!/bin/bash
# DIE-HEAD-9 FACE: start_o == start (ot_dp_landing_origin_s) by SAT temporal induction, PADW 1..4, every strap_pad,
# both strap_efall; mutant OT_ORIGIN_MUTANT_LATE must FAIL.  Usage: fv_origin_start_o.sh <repo> <outdir>
set -u
R=$1; O=$2; mkdir -p $O
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
rc_all=0
for mut in "" "-DOT_ORIGIN_MUTANT_LATE"; do
 for W in 1 2 3 4; do
  for P in $(seq 0 $(( (1<<W) - 1 ))); do
   for E in 0 1; do
    cat > $O/m_${W}_${P}_${E}.sv <<V
module fvtop(input wire clk, input wire rst_raw_n, input wire p_start, output wire ok);
  wire start, start_o;
  ot_dp_landing_origin_s #(.PADW($W)) u (.clk(clk), .rst_raw_n(rst_raw_n), .p_start(p_start), .strap_efall(1'b$E),
      .strap_pad($W'd$P), .start(start), .start_o(start_o));
  assign ok = (start == start_o);
endmodule
V
    tag="W${W}_P${P}_E${E}${mut:+_MUT}"
    docker run --rm -m 4g -v $R:$R:ro -v $O:$O openroad/orfs:asap7lock $Y -q -p "read_verilog -sv -DSYNTHESIS $mut $R/rtl/common/ot_dp_clk_landing_ca.sv $O/m_${W}_${P}_${E}.sv; hierarchy -top fvtop; proc; setattr -mod -unset keep_hierarchy *; flatten; hierarchy -top fvtop; opt_clean; async2sync; dffunmap; sat -tempinduct -prove ok 1 -set-at 1 rst_raw_n 0 -seq 1 -maxsteps 24 -verify -show-ports fvtop" > $O/$tag.log 2>&1
    rc=$?
    if [ -z "$mut" ]; then [ $rc -eq 0 ] && echo "PASS $tag" || { echo "FAIL $tag"; rc_all=1; }
    else [ $rc -ne 0 ] && echo "MUTANT_CAUGHT $tag" || { echo "MUTANT_MISSED $tag"; rc_all=1; }; fi
   done
  done
 done
done
exit $rc_all
