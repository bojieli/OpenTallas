# OT_EDGES v1 arr (FLOW-ONEMODEL-2 readout) -> the DIE-QC-11 duty_eval input form: T rows as is, F rows as
# 'F port fall_late rise_late fall_slew' (the old patch_combo_inv form duty_eval reads)
import sys
T = {}; F = []
for l in open(sys.argv[1]):
    x = l.split()
    if x and x[0] == "T": T[x[1]] = x
    elif x and x[0] == "F": F.append(x)
with open(sys.argv[2], "w") as o:
    for x in T.values(): o.write(" ".join(x) + "\n")
    for x in F: o.write(f"F {x[1]} {x[2]} {T[x[1]][2]} {x[4]}\n")
