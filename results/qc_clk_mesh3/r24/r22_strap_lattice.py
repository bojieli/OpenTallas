"""R22: publish the d43 die fine-mesh strap lattice (die coordinates) exactly as the solver builds it (rec xs/ys after
M3.build with the R17-R22 d43 arguments): M9 vertical straps at xs (span ys[0]..ys[-1]), M8 horizontal straps at ys
(span xs[0]..xs[-1]), width = --fine-w.  Usage: python3 r22_strap_lattice.py OUT.json <solver common args>"""
import argparse, json, sys
from collections import Counter
import qc_clk_mesh3 as M3
out = sys.argv[1]
ap = argparse.ArgumentParser(); M3.add_common(ap)
a = ap.parse_args(sys.argv[2:])
a.no_spine, a.top_w, a.top_m, a.top_reach = True, "16w", 2, 450.0
a.islands, a.feed, a.lanes = "type", "periodic", "vss"
B = M3.build(a, M3.Stage(a.stage))
rec = B["rec"]
xs, ys = [M3.r3(x) for x in rec["xs"]], [M3.r3(y) for y in rec["ys"]]
r2 = json.load(open(a.r2))
def pitches(v):
    return sorted(Counter(M3.r3(b - a_) for a_, b in zip(v, v[1:])).items(), key=lambda t: -t[1])
d = dict(schema="ot_qc_strap_lattice/1", plan=rec.get("plan"), plan_sha256=rec.get("plan_sha256"), r2=a.r2,
         die_W_um=rec.get("W"), die_H_um=rec.get("H"), fine_w=a.fine_w, width_um=M3.WIDTH_UM[a.fine_w],
         M9_vertical=dict(n=len(xs), x_um=xs, y_span_um=[ys[0], ys[-1]], pitch_hist_um=pitches(xs)),
         M8_horizontal=dict(n=len(ys), y_um=ys, x_span_um=[xs[0], xs[-1]], pitch_hist_um=pitches(ys)),
         crossings=len(xs) * len(ys),
         same_as_r2_file=dict(xs=xs == [M3.r3(x) for x in r2["xs"]], ys=ys == [M3.r3(y) for y in r2["ys"]]),
         note="irregular pitch: x follows the nk partition-channel lattice (207.36 / 198.72 / 216), y the gap-row "
              "lattice incl. the R17 43.2-um centre clock channel (no strap inside it); crossings = every (x, y) pair. "
              "UNCHECKED")
json.dump(d, open(out, "w"), indent=1)
print("xs", len(xs), xs[0], xs[-1], pitches(xs)); print("ys", len(ys), ys[0], ys[-1], pitches(ys)); print(d["same_as_r2_file"])
