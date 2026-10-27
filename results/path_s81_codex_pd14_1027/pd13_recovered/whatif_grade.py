"""PATH-S81-PD13 (3) GRADED split-line band what-if (model only, UNCHECKED).  Base 4w continuous mesh; every strap
segment whose midpoint lies within B um of an H-tree L1/L2 split line (x = root x for M8 rows crossing it, and for M9
columns running parallel inside the band; same for y) gets width w(d) = 4 + (WMAX - 4) * (1 - d/B) (linear taper, d =
distance of the segment midpoint / column from the line), quantised to 4w steps.  KMODE prop = plan-computed band driver
sizing (12.8 d1): each mesh driver gets k = round(cf(w_local)/cf(4w)) parallel BUFx24 (R_th/k), w_local = the widest
strap at its site; KMODE none = k 1.  Strap R/C = PD12 RC_R6 width extrapolation (r x 4/w, cf 0.9 + 0.0875 w).
Prints band strap cap, power, max driver k, worst per-site edge estimate; then runs main mesh_mc18.
usage: whatif_grade.py REC WMAX B KMODE CORNER SAMPLES OUT ROUTED QCDIR MC18 THEV"""
import inspect, json, math, runpy, sys
rec, wmax, B, kmode, C, ns, out, routed, qc, mc18, thev = sys.argv[1:12]
wmax, B = int(wmax), float(B)
sys.path.insert(0, qc)
import qc_clk_mesh2 as Q
R = json.load(open(rec)); rx, ry = R["root_xy"]
b = Q.RC_R6["4w"]
def wq(d):
    if d >= B: return 4
    return max(4, int(round((4 + (wmax - 4) * (1 - d / B)) / 4)) * 4)
def rcw(layer, w):
    cf = 0.9 + 0.0875 * w
    return (b[layer][0] * 4 / w, b[layer][1] * cf / 1.3 * 1.13) if w > 4 else b[layer]
def seg_w(kind, fix, lo, hi):
    # kind H = M8 row at y=fix spanning x lo..hi ; V = M9 column at x=fix spanning y lo..hi
    mid = (lo + hi) / 2
    if kind == "H": d = min(abs(mid - rx), abs(fix - ry))
    else:           d = min(abs(mid - ry), abs(fix - rx))
    return wq(d)
class Band(dict):
    def __getitem__(self, layer):
        f = sys._getframe(1).f_locals
        ka, kb = f["ka"], f["kb"]
        return rcw(layer, seg_w(ka[0], ka[1], ka[2], kb[2]))
Q.RC_R6["grade"] = Band(); Q.NDR["grade"] = Q.NDR["4w"]
# band cap (nominal, on the strap grid) and driver k
xs, ys = R["xs"], R["ys"]; cap = 0.0
for y in ys:
    for u, v in zip(xs, xs[1:]): cap += (rcw("M8", seg_w("H", y, u, v))[1] - b["M8"][1]) * (v - u)
for x in xs:
    for u, v in zip(ys, ys[1:]): cap += (rcw("M9", seg_w("V", x, u, v))[1] - b["M9"][1]) * (v - u)
cf = lambda w: 0.9 + 0.0875 * w
K = {}
for n in R["nodes"]:
    if not n["driver"]: continue
    x, y = n["site"]; w = max(wq(abs(x - rx)), wq(abs(y - ry)))
    K[n["tag"]] = max(1, round(cf(w) / cf(4))) if kmode == "prop" else 1
print(json.dumps(dict(wmax=wmax, B=B, kmode=kmode, band_added_cap_pF=round(cap / 1e3, 1),
                      band_added_power_W_TT=round(cap * 1e-15 * 0.7 ** 2 * 1.2e9, 3), drivers_k_gt1=sum(k > 1 for k in K.values()),
                      k_max=max(K.values()), added_bufx24=sum(k - 1 for k in K.values()))), flush=True)
# per-driver strength: patch netlist (tag -> k) and solve_netlist (per-driver R_th / k)
_net = Q.netlist
def netlist(*a, **kw):
    N = _net(*a, **kw)
    for d in N["drv"]: d["k"] = K.get(d["tag"], 1)
    return N
Q.netlist = netlist
src = inspect.getsource(Q.solve_netlist)
src = src.replace('rth = th["R_ohm"] / max(1, th.get("mult", 1)) + 51.2',
                  'rth = np.array([th["R_ohm"] / max(1, th.get("mult", 1)) / d.get("k", 1) + 51.2 for d in N["drv"]])')
assert "d.get(\"k\", 1)" in src
ns_ = {}; exec(compile(src, "solve_patched", "exec"), Q.__dict__, ns_); Q.solve_netlist = ns_["solve_netlist"]
R["ndr"] = "grade"; json.dump(R, open(out + ".rec.json", "w"))
sys.argv = [mc18, out + ".rec.json", "--thev", thev, "--corner", C, "--samples", ns, "--routed", routed, "--out", out, "--qc", qc]
runpy.run_path(mc18, run_name="__main__")
