"""PATH-S81-PD13 gate prediction for a what-if mesh MC (model only, UNCHECKED).
The shared STA (main die_sta_related --mesh-signoff) charges U(a,b) on every 'm' pair; tap re-reference, AOCV below the
mesh and register arcs do not change with the tree above the mesh.  So per pair: S' = S + U_TT_old - U_TT_new,
H' = H + U_FF_old - U_FF_new; the routed-vs-sim RC gap is kept per load (gap = routed - OLD sim nominal, folded per
sample exactly as die_sta_related.mesh_signoff).  HB4 plan model: k = ceil(-H'/44.6), setup after = S' - 83.0 k.
usage: predict.py STA_JSON MESH_JSON ROUTED_TT ROUTED_FF OLD_TT OLD_FF NEW_TT NEW_FF REC [--pairs-only]"""
import json, math, sys
sta, meshj, rTT, rFF, oTT, oFF, nTT, nFF, recp = sys.argv[1:10]
M = json.load(open(meshj)); load = {t["port"]: t["stub"] for t in M["taps"] if not t.get("mesh_in")}
rec = json.load(open(recp)); rx, ry = rec["root_xy"]
def mk(oldp, newp, routedp):
    O = json.load(open(oldp)); N = json.load(open(newp)); rt = json.load(open(routedp))["stubs"]
    io = {k: i for i, k in enumerate(O["loads"])}; inn = {k: i for i, k in enumerate(N["loads"])}
    gap = {k: rt[k]["late"] - O["arr"][0][i] for k, i in io.items() if k in rt}
    def U(S, idx, x, y):
        i, j = idx[x], idx[y]; g = gap.get(x, 0.0) - gap.get(y, 0.0)
        ds = [S["arr"][s][i] - S["arr"][s][j] + g for s in range(len(S["arr"]))]; mc = ds[1:] or ds
        mu = sum(mc) / len(mc); sd = (sum((v - mu) ** 2 for v in mc) / max(1, len(mc) - 1)) ** .5
        gv = S["grad_vec_ps"]; gd = math.hypot(gv[i][0] - gv[j][0], gv[i][1] - gv[j][1])
        return max(max(abs(v) for v in ds), abs(mu) + 3 * sd) + gd
    return lambda x, y: (U(O, io, x, y), U(N, inn, x, y)), O, N
UT, OT, NT = mk(oTT, nTT, rTT); UF, _, _ = mk(oFF, nFF, rFF)
D = json.load(open(sta)); out = {}
for cl in ("intra", "seam", "seam_nearest_INFO"):
    L = D["hb4"][cl]["all"]["setup_neg_after"]; res = dict(fail_now=len(L), band=0, mesh=0, mesh_pass_pred=0, worst_after_pred=None, worst=None)
    for p in L:
        a, b = p["launch"], p["capture"]
        if a not in load or b not in load: res["band"] += 1; continue
        res["mesh"] += 1
        uo, un = UT(load[a], load[b]); fo, fn = UF(load[a], load[b])
        S = p["tt_setup_before"] + uo - un; H = p["ff_hold_before"] + fo - fn
        k = max(0, math.ceil(-H / 44.6 - 1e-9)); after = S - 83.0 * k
        if after >= 0: res["mesh_pass_pred"] += 1
        if res["worst_after_pred"] is None or after < res["worst_after_pred"]:
            res["worst_after_pred"] = round(after, 1); res["worst"] = dict(p, U_TT=[round(uo, 1), round(un, 1)], U_FF=[round(fo, 1), round(fn, 1)], k=k)
    out[cl] = res
# neighbour-pair U stats (<= 1 mm, PD12 pairs.py set) old vs new, TT, with the gap folded
P = json.load(open(sys.argv[2].replace("mesh.json", "place.json")))
xy = {k: (P[k]["x"], P[k]["y"]) for k in OT["loads"] if k in P and not k.startswith("ckm_br_")}
cell = {}
for k, (x, y) in xy.items(): cell.setdefault((int(x // 1000), int(y // 1000)), []).append(k)
Uo, Un, X, Y, neg = [], [], [], [], 0
for k, (x, y) in xy.items():
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in cell.get((int(x // 1000) + dx, int(y // 1000) + dy), []):
                if j <= k: continue
                xj, yj = xy[j]
                if abs(x - xj) + abs(y - yj) > 1000: continue
                uo, un = UT(k, j); Uo.append(uo); Un.append(un); neg += un > uo + 0.5
                if (x - rx) * (xj - rx) < 0: X.append(un)
                if (y - ry) * (yj - ry) < 0: Y.append(un)
q = lambda v, p: round(sorted(v)[min(len(v) - 1, int(p * len(v)))], 1)
out["U_TT_neighbour"] = dict(pairs=len(Un), old=dict(p50=q(Uo, .5), p99=q(Uo, .99), max=q(Uo, 1), over80=sum(u > 80 for u in Uo)),
                             new=dict(p50=q(Un, .5), p99=q(Un, .99), max=q(Un, 1), over80=sum(u > 80 for u in Un)),
                             new_xline=dict(n=len(X), p50=q(X, .5), max=q(X, 1)), new_yline=dict(n=len(Y), p50=q(Y, .5), max=q(Y, 1)),
                             pairs_U_worse=neg)
out["sim"] = dict(old=OT["summary"], new=NT["summary"])
print(json.dumps(out, indent=1))
