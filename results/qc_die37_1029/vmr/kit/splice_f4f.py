"""DIE-QC-37: splice the F4F common entry trunk (codex/qc-f4f-2000@55f5cab504, mscts_spec_f4f.tcl of vmr_f4k_final) into a
F4D-recipe spec: the 4 ot_h_fixed TR*_nd lines + the 4 TR tree lines verbatim, every 'root'-parented tree node re-parented to TR3.
usage: splice_f4f.py F4F_SPEC NEW_S56_SPEC OUT"""
import re, sys
f4f, new, out = sys.argv[1:4]
F = open(f4f).read().splitlines()
fixed_tr = [l for l in F if re.match(r"\s*\{ot_ms_TR\d_nd ", l)]
tree_tr = [l for l in F if re.match(r"\s*\{TR\d (root|TR\d) ", l)]
assert len(fixed_tr) == 4 and len(tree_tr) == 4, (fixed_tr, tree_tr)
o, sec, n_rep = [], None, 0
for l in open(new).read().splitlines():
    m = re.match(r"set (\w+) \{", l)
    if m: sec = m.group(1)
    if sec == "ot_ms_tree" and re.match(r"\s*\{\S+ root ", l):
        l = re.sub(r"^(\s*\{\S+) root ", r"\1 TR3 ", l); n_rep += 1
    o.append(l)
    if m and sec == "ot_h_fixed": pass
    if sec == "ot_h_fixed" and re.match(r"\s*\{ot_ms_root ", l): o += fixed_tr
    if m and sec == "ot_ms_tree": o += tree_tr
hdr = ["# DIE-QC-37 VMR MIF1: F4D recipe plan on the MIF1 3_place (plan_mif1/vmr_k8_s56.tcl) + F4F entry trunk spliced verbatim"
       f" from {f4f} ({n_rep} root children -> TR3)"]
open(out, "w").write("\n".join(hdr + o) + "\n")
print("SPLICE", n_rep, "re-parented; TR fixed", len(fixed_tr), "TR tree", len(tree_tr))
