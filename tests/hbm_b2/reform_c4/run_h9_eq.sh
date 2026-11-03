#!/usr/bin/env bash
# DIE-HBM-61 RE-FORM C4: h9 WP_REG lockstep (new vs origin/main) + killing mutants. Usage: run_h9_eq.sh REPO WORK
set -uo pipefail
R=$(cd "${1:?repo}" && pwd); W=${2:?work}; mkdir -p "$W"; cd "$W"
F=rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv
git -C "$R" show origin/main:$F | sed 's/\bot_hbm_r14_stream_pc_strap_h9\b/ot_hbm_r14_stream_pc_strap_h9_old/' > old.sv
TB=$R/tests/hbm_b2/reform_c4/tb_h9_wpreg_eq.sv
run() { # name file expect P T
  iverilog -g2012 -s tb -Ptb.P=$4 -Ptb.T=$5 -o $1_$4_$5.vvp "$2" old.sv "$TB" > $1_$4_$5.comp.log 2>&1 || { echo "$1 P=$4 T=$5 COMPILE-FAIL"; cat $1_$4_$5.comp.log | head; return; }
  r=$(timeout 1800 vvp -n $1_$4_$5.vvp | grep H9_WPREG_EQ); echo "$1 expect=$3 :: $r"
}
mk() { sed "$2" "$R/$F" > $1.sv; cmp -s $1.sv "$R/$F" && echo "MUTANT $1 did not apply"; }
mk mut_wp  's/if (push_i) wp_oh <= {wp_oh\[WQ-2:0\], wp_oh\[WQ-1\]};/if (push_i \&\& !wq_n[0]) wp_oh <= {wp_oh[WQ-2:0], wp_oh[WQ-1]};/'
mk mut_nf  's/nf_rep <= {WQ{wq_n_nx != (WQW+1)'"'"'(WQ)}};/nf_rep <= {WQ{wq_n != (WQW+1)'"'"'(WQ)}};/'
mk mut_clr 's/else if (pe\[q\]) wq_older\[p\*WQ + q\] <= 1'"'"'b0;/;/'
mk mut_rep 's/({WQ{W \&\& wr_v}} \& nf_rep \& wp_oh)/({WQ{W \&\& wr_v}} \& {nf_rep[WQ-1:1], 1'"'"'b1} \& wp_oh)/'
for pt in "2 0" "2 1" "1 0" "1 1"; do run pos "$R/$F" pass $pt; done
for m in mut_wp mut_nf mut_clr mut_rep; do run $m $m.sv fail 2 1; run $m $m.sv fail 1 0; done
