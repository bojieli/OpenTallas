#!/bin/bash
# pv_join one-hot select equivalence: old (OLD rev, renamed pvj_old) vs new, random bench (tb_pvjoin_portcopy_eq.sv) + MUT=1 mutant
set -e; W=${W:-$(git rev-parse --show-toplevel)}; cd $W; T=$(mktemp -d); F=rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv
H=physical/die_plan/qwen_kvsys/cores/harden/pvpc_1025
git show ${OLD:-6a56d58118}:$F | sed -n "/^module ot_qwen_tp8_pv_join_t #/,/^endmodule/p" | sed "s/module ot_qwen_tp8_pv_join_t/module pvj_old/" > $T/old.sv
sed -n "/^module ot_qwen_tp8_pv_join_t #/,/^endmodule/p" $F > $T/new.sv
L="rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv"
iverilog -g2012 -o $T/sim $H/tb_pvjoin_portcopy_eq.sv $T/old.sv $T/new.sv $L
echo "EQ   $(vvp -n $T/sim | grep DONE)"
sed "s/ot_qwen_tp8_pv_join_t #(.RESET_PIN(1)) b/ot_qwen_tp8_pv_join_t #(.RESET_PIN(1),.MUT(1)) b/" $H/tb_pvjoin_portcopy_eq.sv > $T/tbm.sv
iverilog -g2012 -o $T/simm $T/tbm.sv $T/old.sv $T/new.sv $L
echo "MUT  $(vvp -n $T/simm | grep DONE) (must be err>0)"
rm -rf $T
