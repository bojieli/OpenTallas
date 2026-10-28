# replace the combo.tcl arr readout block (from 'set ot_odd' to the first 'close $fh' after it) by the shared
# FLOW-ONEMODEL-2 'die_trial.py readout' block (T/F per tap, N/M per clock cell)
import sys
p, r = sys.argv[1], sys.argv[2]
L = open(p).read().split("\n"); R = open(r).read().rstrip("\n").split("\n")
i = next(k for k, l in enumerate(L) if l.startswith("set ot_odd "))
j = next(k for k in range(i, len(L)) if L[k].strip() == "close $fh")
assert all(x.startswith(("set ot_odd", "set fh", "foreach", "puts")) for x in L[i:j]), "unexpected block"
L[i:j + 1] = R
open(p, "w").write("\n".join(L)); print("spliced", p, j - i + 1, "->", len(R))
