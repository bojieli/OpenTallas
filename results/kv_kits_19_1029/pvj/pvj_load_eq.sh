#!/bin/bash
# KV-KITS-19 pv_join: old (OLD rev 6a56d58118: js case mux + shared J_OUT load decode) vs new (this branch: KV-KITS-16
# sa/sb one-hot selects + main b83fce6ef OUTPUT_LOAD_LOCAL=1 per-16-bit lookahead load_q), random bench
# tb_pvjoin_portcopy_eq.sv (6000 cycles, mid resets, faults). Negative controls: MUT=1 (join order) and a load
# lookahead mutant (load_q from nage==J_OUT-1). Both must report err>0.
set -e; W=${W:-$(git rev-parse --show-toplevel)}; cd $W; T=$(mktemp -d); F=rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv
H=physical/die_plan/qwen_kvsys/cores/harden/pvpc_1025
git show ${OLD:-6a56d58118}:$F | sed -n "/^module ot_qwen_tp8_pv_join_t #/,/^endmodule/p" | sed "s/module ot_qwen_tp8_pv_join_t/module pvj_old/" > $T/old.sv
sed -n "/^module ot_qwen_tp8_pv_join_t #/,/^endmodule/p" $F > $T/new.sv
grep -q "nage==5.(J_OUT))" $T/new.sv
sed "s/nage==5.(J_OUT))/nage==5'(J_OUT-1))/" $T/new.sv > $T/newm.sv
L="rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv"
sed "s/ot_qwen_tp8_pv_join_t #(.RESET_PIN(1)) b/ot_qwen_tp8_pv_join_t #(.RESET_PIN(1),.OUTPUT_LOAD_LOCAL(1)) b/" $H/tb_pvjoin_portcopy_eq.sv > $T/tb.sv
grep -q "OUTPUT_LOAD_LOCAL(1)) b" $T/tb.sv
iverilog -g2012 -o $T/sim $T/tb.sv $T/old.sv $T/new.sv $L
echo "EQ    $(vvp -n $T/sim | grep DONE)"
sed "s/.OUTPUT_LOAD_LOCAL(1)) b/.OUTPUT_LOAD_LOCAL(1),.MUT(1)) b/" $T/tb.sv > $T/tbm.sv
iverilog -g2012 -o $T/simm $T/tbm.sv $T/old.sv $T/new.sv $L
echo "MUT   $(vvp -n $T/simm | grep DONE) (must be err>0)"
iverilog -g2012 -o $T/siml $T/tb.sv $T/old.sv $T/newm.sv $L
echo "LDMUT $(vvp -n $T/siml | grep DONE) (must be err>0)"
rm -rf $T
