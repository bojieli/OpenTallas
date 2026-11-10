#!/usr/bin/env python3
"""DIE-QC-97 RSTREP-1 LEC yosys script.  argv: MODE(rs|def) [define ...]
rs : gold lec_gold vs gate lec_gate (tops_rs.sv), new RTL both sides; defines go to the gate only.
def: lec_top from the OLD rtl (/rtl_old) vs the NEW rtl (/rtl), default parameters (tops_def.sv).
wl : the same, tops_wl.sv (WLIVE-1 at the pilot ring form)."""
import sys
mode, muts = sys.argv[1], sys.argv[2:]
lib = "ot_dp_clk_landing_ca.sv ot_meso_fifo.sv ot_dp_clk_landing.sv"
def read(top, root, tops, defs):
    d = " ".join(f"-D {m}" for m in defs)
    src = " ".join(f"{root}/{f}" for f in lib.split()) + f" /h/{tops}"
    return [f"read_slang -D SYNTHESIS {d} --top {top} {src}", f"hierarchy -top {top}", "proc", "flatten",
            "memory", "opt_clean -purge", "setattr -unset keep", "setattr -mod -unset keep_hierarchy"]
if mode == "rs":
    L = read("lec_gold", "/rtl", "tops_rs.sv", []) + ["rename lec_gold gold", "design -stash g"]
    L += read("lec_gate", "/rtl", "tops_rs.sv", muts) + ["rename lec_gate gate", "design -copy-from g -as gold gold"]
    adds = "/h/adds_rs.ys"
else:
    tops = "tops_wl.sv" if mode == "wl" else "tops_def.sv"
    L = read("lec_top", "/rtl_old", tops, []) + ["rename lec_top gold", "design -stash g"]
    L += read("lec_top", "/rtl", tops, muts) + ["rename lec_top gate", "design -copy-from g -as gold gold"]
    adds = None
L += ["equiv_make gold gate eq", "hierarchy -top eq", "tee -o /o/equiv_make.txt equiv_status"]
if adds:
    L += ["cd eq", f"tee -o /o/adds.log script {adds}", "cd .."]
L += ["equiv_simple -seq 4", "equiv_induct -seq 4", "tee -o /o/equiv_status.txt equiv_status", "equiv_status -assert"]
print("\n".join(L))
