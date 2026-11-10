#!/usr/bin/env python3
"""Emit the DIE-QC-97 ring LEC yosys script.  argv: [mutant define ...] [--discover]"""
import sys
args = sys.argv[1:]
disc = "--discover" in args
muts = [a for a in args if a != "--discover"]
src = "/rtl/ot_dp_clk_landing_ca.sv /rtl/ot_meso_fifo.sv /rtl/ot_dp_clk_landing.sv /h/tops.sv"
def read(top, defs):
    d = " ".join(f"-D {m}" for m in defs)
    return [f"read_slang -D SYNTHESIS {d} --top {top} {src}", f"hierarchy -top {top}", "proc", "flatten",
            "memory", "opt_clean -purge", "setattr -unset keep", "setattr -mod -unset keep_hierarchy"]
L = read("lec_gold", []) + ["rename lec_gold gold", "design -stash g"]
L += read("lec_gate", muts) + ["rename lec_gate gate", "design -copy-from g -as gold gold"]
if disc:
    L += ["equiv_make gold gate eq", "select -list eq/w:*u_dsel.di* eq/w:*sr*u_sel.di* eq/w:*ch[1].u_wen.q* eq/w:*ch[2].u_wen.q* %u",
          "tee -o /o/equiv_make.txt equiv_status"]
else:
    L += ["equiv_make gold gate eq", "hierarchy -top eq", "tee -o /o/equiv_make.txt equiv_status",
          "cd eq", "tee -o /o/adds.log script /h/adds.ys", "cd ..", "tee -o /o/equiv_added.txt equiv_status", "equiv_simple -seq 4", "equiv_induct -seq 4", "tee -o /o/equiv_status.txt equiv_status",
          "equiv_status -assert"]
print("\n".join(L))
