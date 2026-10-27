"""PATH-S81-PD12 (C) local split-line band what-if: base 4w mesh, straps widened to WIDE only inside a band of half-width
B um around the H-tree L1/L2 split lines (x = root x, y = root y).  MODE cross = only the strap segments that cross a
split line; full = also the parallel straps inside the band.  Model only (main mesh_mc18 + qc_clk_mesh2), UNCHECKED.
Prints the band's added strap capacitance.  usage: whatif2.py REC WIDE B MODE CORNER SAMPLES OUT ROUTED QCDIR MC18 THEV"""
import json, runpy, sys
rec, wide, B, mode, C, ns, out, routed, qc, mc18, thev = sys.argv[1:12]
B = float(B); w = int(wide.rstrip("w"))
sys.path.insert(0, qc)
import qc_clk_mesh2 as Q
R = json.load(open(rec)); rx, ry = R["root_xy"]
b = Q.RC_R6["4w"]; cf = 0.9 + 0.0875 * w
W = {L: (b[L][0] * 4 / w, b[L][1] * cf / 1.3 * 1.13) for L in ("M8", "M9")}
extra = dict(cap_fF=0.0, segs=0)

class Band(dict):
    def __getitem__(self, layer):
        f = sys._getframe(1).f_locals
        ka, kb, L = f["ka"], f["kb"], f["L"]
        if ka[0] == "H":   # M8 row at y = ka[1], x from ka[2] to kb[2]
            fix, lo, hi, line, par = ka[1], ka[2], kb[2], rx, ry
        else:              # M9 column at x = ka[1], y from ka[2] to kb[2]
            fix, lo, hi, line, par = ka[1], ka[2], kb[2], ry, rx
        mid = (lo + hi) / 2
        hit = abs(mid - line) <= B or (mode == "full" and abs(fix - par) <= B)
        if hit:
            if f.get("q", 1) == 1 and f.get("seed_", 0) == 0:
                pass
            return W[layer]
        return b[layer]
Q.RC_R6["band"] = Band(); Q.NDR["band"] = Q.NDR["4w"]
# band capacitance (nominal, once): strap segments between breakpoints are not known here; estimate on the grid
xs, ys = R["xs"], R["ys"]
cap = 0.0
for y in ys:
    for u, v in zip(xs, xs[1:]):
        if abs((u + v) / 2 - rx) <= B or (mode == "full" and abs(y - ry) <= B):
            cap += (W["M8"][1] - b["M8"][1]) * (v - u)
for x in xs:
    for u, v in zip(ys, ys[1:]):
        if abs((u + v) / 2 - ry) <= B or (mode == "full" and abs(x - rx) <= B):
            cap += (W["M9"][1] - b["M9"][1]) * (v - u)
print(json.dumps(dict(band_added_cap_pF=round(cap / 1e3, 1), band_added_power_W_TT=round(cap * 1e-15 * 0.7 ** 2 * 1.2e9, 3),
                      wide=wide, B=B, mode=mode, r_ohm_um=W, base=b)), flush=True)
R["ndr"] = "band"; json.dump(R, open(out + ".rec.json", "w"))
sys.argv = [mc18, out + ".rec.json", "--thev", thev, "--corner", C, "--samples", ns, "--routed", routed, "--out", out, "--qc", qc]
runpy.run_path(mc18, run_name="__main__")
