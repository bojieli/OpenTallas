#!/usr/bin/env python3
import sys
K=sys.argv[1]
src="/rtl/ot_dp_clk_landing_ca.sv /rtl/ot_meso_fifo.sv /rtl/ot_dp_clk_landing.sv /h/tops.sv"
def read(top):
    return [f"read_slang -D SYNTHESIS --top {top} {src}", f"hierarchy -top {top}", "proc", "flatten", "memory",
            "opt_dff", "opt_clean -purge", "setattr -unset keep", "setattr -mod -unset keep_hierarchy"]
L=read(f"lec_gold_k{K}")+[f"rename lec_gold_k{K} gold","design -stash g"]
L+=read(f"lec_gate_k{K}")+[f"rename lec_gate_k{K} gate","design -copy-from g -as gold gold"]
L+=["equiv_make gold gate eq","hierarchy -top eq","tee -o /o/equiv_make_k%s.txt equiv_status"%K,
    "equiv_simple -seq 4","equiv_induct -seq 4","tee -o /o/equiv_status_k%s.txt equiv_status"%K,"equiv_status -assert"]
print("\n".join(L))
