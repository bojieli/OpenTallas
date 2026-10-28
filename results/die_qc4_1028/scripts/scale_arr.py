"""DIE-QC-3: METHODOLOGY 12.15b spice-calibrated clock arrivals for die STA: scale every clock-network arrival (tap ports T,
tree cells N; late and early) of a combo arr_<C>.txt by data/asap7_bufx24_spice_cal.json (x1.0485 TT / x1.0552 FF);
slews unchanged.  usage: scale_arr.py IN OUT CORNER"""
import sys
F = {"TT": 1.0485, "FF": 1.0552}
i, o, c = sys.argv[1:4]
k = F[c]
with open(o, "w") as w:
    for ln in open(i):
        f = ln.split()
        if f and f[0] in ("T", "N"):
            f[2], f[3] = "%.4f" % (float(f[2]) * k), "%.4f" % (float(f[3]) * k)
            ln = " ".join(f) + "\n"
        w.write(ln)
