"""LEAF4 corridor ledger: per leaf type, FT window clusters vs FULL-LENGTH straight free bands between hard cores
(cores obstruct M1-M7 in the leaf: closed core LEFs OBS M6/M7).  need = bits / D (D = 16 b/um vertical, 11 b/um
horizontal: M3+M5+M7 resp. M2+M4+M6 tracks x 0.5 G2 adjust x 0.5 utilisation)."""
import json, sys
import numpy as np
HALO = 8.64; DV = 16.0; DH = 11.0; J = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
P = json.load(open(sys.argv[1]))
sel = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] != "all" else None
def clusters(iv):
    iv = sorted(iv); out = []
    for a, b, w in iv:
        if out and a <= out[-1][1] + 2: out[-1][1] = max(out[-1][1], b); out[-1][2] += w
        else: out.append([a, b, w])
    return out
rows = {}
for tn, T in P["partition_types"].items():
    if not tn.startswith("ot_s81sl_leaf__t"): continue
    if sel and tn.split("__")[1] not in sel: continue
    W, H = T["outline_um"]
    fx = np.ones(int(W) + 1, bool); fy = np.ones(int(H) + 1, bool)
    for c in T["hard_cores"]:
        x0, y0 = c["origin_um"]; w, h = c["outline_um"]
        fx[max(0, int(x0 - HALO)):int(x0 + w + HALO) + 1] = False
        fy[max(0, int(y0 - HALO)):int(y0 + h + HALO) + 1] = False
    V, Hh = [], []
    for s in T["ft_slots"]:
        for face, win in ((s["in_face"], s["in_window_um"]), (s["out_face"], s["out_window_um"])):
            (V if face in "NS" else Hh).append((win[0], win[1], s["width"] / 2.0))  # each end carries half: in+out
    res = []
    for kind, iv, free, D in (("V", V, fx, DV), ("H", Hh, fy, DH)):
        for a, b, w in clusters(iv):
            lo, hi = max(0, int(a - J)), min(len(free) - 1, int(b + J))
            fw = float(free[lo:hi + 1].sum())
            res.append(dict(k=kind, win=[round(a), round(b)], bits=int(w), need=round(w / D, 1), free=fw,
                            g2cap=int(fw * 2 * D), short=round(max(0, w / D - fw), 1)))
    rows[tn] = dict(tot_short_V=round(sum(r["short"] for r in res if r["k"] == "V"), 1),
                    tot_short_H=round(sum(r["short"] for r in res if r["k"] == "H"), 1),
                    need_V=round(sum(r["need"] for r in res if r["k"] == "V"), 1),
                    need_H=round(sum(r["need"] for r in res if r["k"] == "H"), 1),
                    free_V=float(fx.sum()), free_H=float(fy.sum()), clusters=res)
for tn, r in sorted(rows.items(), key=lambda kv: int(kv[0].split("__t")[1])):
    print(tn.split("__")[1], "needV %.0f freeV(all) %.0f shortV %.0f | needH %.0f freeH(all) %.0f shortH %.0f" % (
        r["need_V"], r["free_V"], r["tot_short_V"], r["need_H"], r["free_H"], r["tot_short_H"]))
if len(sys.argv) > 4: json.dump(rows, open(sys.argv[4], "w"), indent=1)
