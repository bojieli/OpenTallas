"""CPL-HBM-B1 hcol S2 re-layout inside the DIE-LAYOUT-HBM ladder outlines (t19 6391dea6), 2026-11-11.
Positions only: every idx stack (h0 ra + h0 rb + h1) is placed as one frame so the bound h0->h1 (and ra->rb) 33-bit
direct pairs are centre <= 405 um; banks keep their ladder sites unless the spec moves them (then the internal-station
from/to pins translate with the core).  Plan-station and ft-slot register COUNTS are never changed (EQ by construction):
only register sites that the new core boxes cover are re-sited on free sites, hops <= 405 um (360 next to a face reg).
usage: lad.py PLAN.json TYPE SPEC.json OUT_TYPE.json [TRACE.json]"""
import json, sys, re, math, collections
import numpy as np

RA = (106.272, 290.304); H1 = (218.592, 187.488); RBDX = 112.32; GAP = 4.32; G = 0.864
BANK = (250.56, 267.84); HALO_BANK = 8.64; R = 405.0
snap = lambda v: round(round(v / G) * G, 3)


def frame(form, x, y):
    """unit footprint -> {part: (x, y)} ; parts ra rb h1"""
    if form == "V1L":      # h1 low, ra/rb above
        return {"h1": (x, y), "ra": (x, y + H1[1] + GAP), "rb": (x + RBDX, y + H1[1] + GAP)}
    if form == "V1H":      # ra/rb low, h1 above
        return {"ra": (x, y), "rb": (x + RBDX, y), "h1": (x, y + RA[1] + GAP)}
    if form == "H":        # ra rb h1 in one row (h1 bottom-aligned)
        return {"ra": (x, y), "rb": (x + RBDX, y), "h1": (x + RBDX + RA[0] + GAP, y)}
    if form == "HR":       # h1 ra rb in one row
        return {"h1": (x, y), "ra": (x + H1[0] + GAP, y), "rb": (x + H1[0] + GAP + RBDX, y)}
    if form == "RAB":
        return {"ra": (x, y), "rb": (x + RBDX, y)}
    if form == "RABV":
        return {"ra": (x, y), "rb": (x, y + RA[1] + GAP)}
    if form == "H1":
        return {"h1": (x, y)}
    raise SystemExit(form)


def fsize(form):
    return {"V1L": (H1[0], H1[1] + GAP + RA[1]), "V1H": (H1[0], H1[1] + GAP + RA[1]), "H": (RBDX + RA[0] + GAP + H1[0], RA[1]),
            "HR": (RBDX + RA[0] + GAP + H1[0], RA[1]), "RAB": (H1[0], RA[1]), "RABV": (RA[0], 2 * RA[1] + GAP), "H1": H1}[form]


def main():
    plan, tn, specf, outf = sys.argv[1:5]
    trf = sys.argv[5] if len(sys.argv) > 5 else None
    P = json.load(open(plan)); T = P["partition_types"][tn]; S = json.load(open(specf)).get(tn, {})
    W, H = T["outline_um"]; tap = T["clock"]["tap_um"]
    hc = {h["inst"]: h for h in T["hard_cores"]}
    old = {i: list(h["origin_um"]) for i, h in hc.items()}
    def find(stack, part):
        if part in ("ra", "rb"):
            k = [i for i in hc if re.search(stack + r"h0__" + part + "$", i)]
        else:
            k = [i for i in hc if re.search(stack + r"h1$", i)]
        if len(k) != 1: raise SystemExit(f"{tn}: {stack} {part} -> {k}")
        return k[0]
    pos = {}
    # rows: {y, x0, x1, units:[[name, form]], align}
    for row in S.get("rows", []):
        us = row["units"]; ws = [fsize(f)[0] for _, f in us]
        slack = row["x1"] - row["x0"] - sum(ws)
        if slack < -1e-6: raise SystemExit(f"row y{row['y']} overfull by {-slack:.2f}")
        mode = row.get("gaps", "inner")
        n = len(us)
        if mode == "inner": g = slack / (n - 1) if n > 1 else 0; x = row["x0"]
        else: g = slack / (n + 1); x = row["x0"] + g
        for (nm, f), w in zip(us, ws):
            yy = row["y"] + row.get("dy", {}).get(nm, 0.0)
            for part, (px, py) in frame(f, x, yy).items():
                pos[find(nm.replace("h1", "").replace("h0", ""), part)] = (px, py)
            x += w + g
    for nm, (f, x, y) in S.get("units", {}).items():
        for part, (px, py) in frame(f, x, y).items():
            pos[find(nm.replace("h1", "").replace("h0", ""), part)] = (px, py)
    for nm, xy in S.get("banks", {}).items():
        k = [i for i in hc if i.endswith("bank128_" + nm)]
        pos[k[0]] = tuple(xy)
    moved = {}
    for i, (x, y) in pos.items():
        n = [snap(x), snap(y)]
        if n != hc[i]["origin_um"]:
            moved[i] = (n[0] - hc[i]["origin_um"][0], n[1] - hc[i]["origin_um"][1])
        hc[i]["origin_um"] = n
    boxes = {i: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for i, h in hc.items()}
    halo = {i: (h.get("halo_um") or 0.0) for i, h in hc.items()}
    bad = []
    for i, b in boxes.items():
        m = halo[i]
        if b[0] - m < -1e-6 or b[1] - m < -1e-6 or b[2] + m > W + 1e-6 or b[3] + m > H + 1e-6 or b[0] < 4.32 - 1e-6 or b[1] < 4.32 - 1e-6 or b[2] > W - 4.32 + 1e-6 or b[3] > H - 4.32 + 1e-6:
            bad.append(f"outline {i[-28:]} {b}")
        if b[0] - 4.32 < tap[0] < b[2] + 4.32 and b[1] - 4.32 < tap[1] < b[3] + 4.32: bad.append(f"tap {i[-28:]}")
    ks = sorted(boxes)
    for a in range(len(ks)):
        for c in range(a + 1, len(ks)):
            A, B = boxes[ks[a]], boxes[ks[c]]; m = max(halo[ks[a]], halo[ks[c]]) + (4.32 if max(halo[ks[a]], halo[ks[c]]) else 4.32 - 1e-3)
            if halo[ks[a]] == 0 and halo[ks[c]] == 0: m = 4.32 - 0.01
            if not (A[2] + m <= B[0] + 1e-6 or B[2] + m <= A[0] + 1e-6 or A[3] + m <= B[1] + 1e-6 or B[3] + m <= A[1] + 1e-6):
                bad.append(f"spacing {ks[a][-26:]} / {ks[c][-26:]}")
    unplaced = [i for i in hc if i not in pos and "bank" not in i]
    # h0/h1 centre distances
    ctr = lambda i: ((boxes[i][0] + boxes[i][2]) / 2, (boxes[i][1] + boxes[i][3]) / 2)
    d01 = {}
    for i in hc:
        m = re.search(r"(r\dc\d_k\d)h1$", i)
        if m:
            for p in ("ra", "rb"):
                j = [k for k in hc if k.endswith(m.group(1) + "h0__" + p)]
                if j: d01[m.group(1) + "." + p] = round(abs(ctr(i)[0] - ctr(j[0])[0]) + abs(ctr(i)[1] - ctr(j[0])[1]), 1)
    # ---------------- free-site field
    g = 4.32; nx, ny = int(W // g), int(H // g); xs = (np.arange(nx) + 0.5) * g; ys = (np.arange(ny) + 0.5) * g
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    blk = np.zeros_like(X, bool)
    for i, b in boxes.items():
        blk |= (X > b[0]) & (X < b[2]) & (Y > b[1]) & (Y < b[3])
    def dt1(a, ax):
        a = np.moveaxis(a.copy(), ax, 0)
        for k in range(1, a.shape[0]): a[k] = np.minimum(a[k], a[k - 1] + g)
        for k in range(a.shape[0] - 2, -1, -1): a[k] = np.minimum(a[k], a[k + 1] + g)
        return np.moveaxis(a, 0, ax)
    clr = dt1(dt1(np.where(blk, 0.0, 1e9), 0), 1)          # L1 clearance to the nearest core cell
    edge = np.minimum.reduce([X, W - X, Y, H - Y])
    def inside(p, eps=0.5):
        return any(b[0] + eps < p[0] < b[2] - eps and b[1] + eps < p[1] < b[3] - eps for b in boxes.values())
    def ok_pt(p):
        return not inside(p, -1.0)       # keep >= 1 um outside every core box
    L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    def cand(c_min):
        m = (clr >= c_min) & (edge > 2.0)
        return np.stack([X[m], Y[m]], 1)
    CAND = {c: cand(c) for c in (17.28, 8.64, 4.32)}
    FREE = (clr >= 8.64) & (edge > 2.0)
    def ldist(m):
        return dt1(dt1(np.where(m, 0.0, 1e9), 0), 1)
    def adist(anc, px, py):
        """max L1 from (px, py) to every anchor point (a window = its two end points)"""
        return np.maximum.reduce([np.abs(px - a[0]) + np.abs(py - a[1]) for a in anc]) if len(anc) > 1 else np.abs(px - anc[0][0]) + np.abs(py - anc[0][1])
    HOP = R - 1.0
    def chain_ok(ancA, regs, ancB, limA, limB):
        if not regs: return False
        if any(not ok_pt(p) for p in regs): return False
        if adist(ancA, regs[0][0], regs[0][1]) > limA + 1e-6 or adist(ancB, regs[-1][0], regs[-1][1]) > limB + 1e-6: return False
        return all(L1(p, q) <= R + 1e-6 for p, q in zip(regs, regs[1:]))
    def resite1(ancA, regs, ancB, limA, limB):
        pts = [list(p) for p in regs]; N = len(pts)
        badi = [k for k in range(N) if not ok_pt(pts[k])]
        for k in badi:
            j = k + 1
            while j < N and j in badi: j += 1
            for c in (17.28, 8.64, 4.32):
                q = CAND[c]; px, py = q[:, 0], q[:, 1]
                m = (adist(ancA, px, py) <= limA) if k == 0 else (np.abs(px - pts[k - 1][0]) + np.abs(py - pts[k - 1][1]) <= HOP)
                if j < N: m &= np.abs(px - pts[j][0]) + np.abs(py - pts[j][1]) <= (j - k) * HOP
                else: m &= adist(ancB, px, py) <= (j - k - 1) * HOP + limB
                if m.any():
                    qq = q[m]; do = np.abs(qq[:, 0] - pts[k][0]) + np.abs(qq[:, 1] - pts[k][1])
                    jj = int(np.argmin(do)); pts[k] = [round(float(qq[jj][0]), 3), round(float(qq[jj][1]), 3)]; break
            else:
                return None
        return pts if chain_ok(ancA, pts, ancB, limA, limB) else None
    def glob(ancA, N, ancB, limA, limB):
        dA = adist(ancA, X, Y); dB = adist(ancB, X, Y)
        layers = [FREE & (dA <= limA)]
        while not (layers[-1] & (dB <= limB)).any():
            if len(layers) >= N: return None
            nxt = FREE & (ldist(layers[-1]) <= HOP)
            if (nxt & ~np.logical_or.reduce(layers)).sum() == 0: return None
            layers.append(nxt)
        m = layers[-1] & (dB <= limB); c = np.argwhere(m); j = c[np.argmin(dB[m])]; sq = [[float(xs[j[0]]), float(ys[j[1]])]]
        for k in range(len(layers) - 2, -1, -1):
            p = sq[-1]; m = layers[k] & ((np.abs(X - p[0]) + np.abs(Y - p[1])) <= HOP); c = np.argwhere(m); j = c[np.argmin(dA[m])]
            sq.append([float(xs[j[0]]), float(ys[j[1]])])
        sq = sq[::-1]
        while len(sq) < N:      # pad: a free site within one hop of both ends of the longest inner hop (or next to an end reg)
            hops = [L1(sq[k], sq[k + 1]) for k in range(len(sq) - 1)]
            if hops:
                k = int(np.argmax(hops)); a2, b2 = sq[k], sq[k + 1]
                m = FREE & ((np.abs(X - a2[0]) + np.abs(Y - a2[1])) <= HOP) & ((np.abs(X - b2[0]) + np.abs(Y - b2[1])) <= HOP)
                mid = ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)
            else:
                k = 0; a2 = sq[0]; m = FREE & ((np.abs(X - a2[0]) + np.abs(Y - a2[1])) <= HOP) & (dB <= limB); mid = a2
            if not m.any(): return None
            c = np.argwhere(m); j = c[np.argmin((np.abs(X - mid[0]) + np.abs(Y - mid[1]))[m])]
            sq.insert(k + 1, [float(xs[j[0]]), float(ys[j[1]])])
        sq = [[round(a2, 3), round(b2, 3)] for a2, b2 in sq]
        return sq if chain_ok(ancA, sq, ancB, limA, limB) else None
    def resite(ancA, regs, ancB, limA, limB):
        if chain_ok(ancA, regs, ancB, limA, limB): return regs, 0
        r1 = resite1(ancA, regs, ancB, limA, limB)
        if r1 is not None: return r1, sum(1 for a2, b2 in zip(regs, r1) if list(a2) != list(b2))
        g2 = glob(ancA, len(regs), ancB, limA, limB)
        return (g2, len(regs)) if g2 is not None else (None, -1)
    rep = dict(ft=[], st=[])
    # ft slots: reg[0] and reg[-1] are face regs (kept)
    def face_pt(face, win, near):
        lo, hi = win
        if face in ("E", "W"): return [W if face == "E" else 0.0, min(max(near[1], lo), hi)]
        return [min(max(near[0], lo), hi), H if face == "N" else 0.0]
    def wends(face, win):
        lo, hi = win
        return [[W if face == "E" else 0.0, lo], [W if face == "E" else 0.0, hi]] if face in ("E", "W") else [[lo, H if face == "N" else 0.0], [hi, H if face == "N" else 0.0]]
    for f in T.get("ft_slots") or []:
        r = f["regs_um"]
        if not r: continue
        if not ok_pt(r[0]): rep["ft"].append(dict(slot=f["name"], issue="reg0 inside core")); continue
        if len(r) == 1: continue
        ancA = wends(f["in_face"], f["in_window_um"]) + [r[0]]; ancB = wends(f["out_face"], f["out_window_um"])
        inner = [list(p) for p in r[1:]]
        limA = max(HOP, float(adist(ancA, inner[0][0], inner[0][1]))); limB = max(HOP, float(adist(ancB, inner[-1][0], inner[-1][1])))
        if all(ok_pt(p) for p in inner): continue
        new, n = resite(ancA, inner, ancB, limA, limB)
        if new is None: rep["ft"].append(dict(slot=f["name"], issue="RESITE_FAIL")); continue
        f["regs_um"] = [r[0]] + new
        rep["ft"].append(dict(slot=f["name"], moved=n, max_hop=round(max([L1(a2, b2) for a2, b2 in zip(new, new[1:])] + [0]), 1),
                              first=round(float(adist(ancA, new[0][0], new[0][1])), 1), last=round(float(adist(ancB, new[-1][0], new[-1][1])), 1)))
    # internal stations: from/to pins translate with a moved core
    def core_of(s):
        return s.split(".")[0] if s and not s.startswith("face") else None
    full = {h["inst"]: h["inst"] for h in T["hard_cores"]}
    def match(name):
        c = [i for i in hc if name == i or name.startswith(i + ".")]
        return max(c, key=len) if c else None
    for s in T.get("internal_stations") or []:
        for key, end in (("from_um", s.get("launch")), ("to_um", s.get("capture"))):
            if end and not str(end).startswith("face"):
                i = match(str(end))
                if i in moved:
                    dx, dy = moved[i]; b0 = boxes[i]; p = s[key]
                    ob = (b0[0] - dx - 10, b0[1] - dy - 10, b0[2] - dx + 10, b0[3] - dy + 10)   # the core's OLD box (+10 um)
                    if ob[0] <= p[0] <= ob[2] and ob[1] <= p[1] <= ob[3]:
                        s[key] = [round(p[0] + dx, 3), round(p[1] + dy, 3)]
        if not s["regs_um"]:
            if L1(s["from_um"], s["to_um"]) > R: rep["st"].append(dict(conn=s["conn"], issue="0 regs over reach"))
            continue
        ancA, ancB = [s["from_um"]], [s["to_um"]]; inner = [list(p) for p in s["regs_um"]]
        new, n = resite(ancA, inner, ancB, HOP, HOP)
        if new is None:
            rep["st"].append(dict(conn=s["conn"], cap=s.get("capture"), issue="RESITE_FAIL", L=round(L1(s["from_um"], s["to_um"])), regs=len(inner))); continue
        if n:
            s["regs_um"] = new
            rep["st"].append(dict(conn=s["conn"], cap=s.get("capture"), moved=n))
    # soft-relay reach (trace): window <-> core with r registers: L1 <= (r+1)*R
    reach = []
    if trf:
        tr = json.load(open(trf)); bus = {b["name"]: b for b in T["buses"]}
        def bname(n):
            if n in bus: return n
            n2 = n.replace("m_", "_")
            return n2 if n2 in bus else None
        def wpt(b, c):
            lo, hi = bus[b]["window_um"]; f = bus[b]["face"]
            if f in ("E", "W"): return (W if f == "E" else 0.0, min(max(c[1], lo), hi))
            return (min(max(c[0], lo), hi), H if f == "N" else 0.0)
        def tcore(s):
            m = re.search(r"r(\d)c(\d)_k(\d)h(\d)(?:.*u_(r[ab]))?", s)
            if m:
                st = f"r{m.group(1)}c{m.group(2)}_k{m.group(3)}"
                if m.group(4) == "1": k = [i for i in hc if i.endswith(st + "h1")]
                else: k = [i for i in hc if i.endswith(st + "h0__" + (m.group(5) or "ra"))]
                return k[0] if k else None
            m = re.search(r"bank128_pair(\d)", s)
            if m: return next(i for i in hc if i.endswith("pair" + m.group(1)))
            return None
        for l in tr["links"]:
            a, b = l["src"], l["dst"]
            if a.startswith("bus:") == b.startswith("bus:"): continue
            bb, cc = (a, b) if a.startswith("bus:") else (b, a)
            bn = bname(bb[4:]); ci = tcore(cc)
            if not bn or not ci: continue
            d = L1(wpt(bn, ctr(ci)), ctr(ci)); lim = (l["regs_min"] + 1) * R
            reach.append(dict(bus=bn, core=ci, regs=l["regs_min"], bits=l.get("bits"), L1=round(d), lim=lim, ok=d <= lim))
    out = dict(type=tn, illegal=bad, unplaced=unplaced, h0h1_max=max(d01.values()) if d01 else None,
               h0h1_over405=sorted(k for k, v in d01.items() if v > R), reach_viol=[r for r in reach if not r["ok"]],
               ft_changes=rep["ft"], st_changes=rep["st"], moved=len(moved))
    json.dump(T, open(outf, "w"))
    print(json.dumps(dict(type=tn, illegal=bad[:12], n_illegal=len(bad), unplaced=unplaced, h0h1_max=out["h0h1_max"], h0h1_over405=out["h0h1_over405"],
                          reach_viol=[(r["bus"], r["core"][-22:], r["regs"], r["L1"]) for r in out["reach_viol"]],
                          ft_fail=[r for r in rep["ft"] if "issue" in r], st_fail=[r for r in rep["st"] if "issue" in r],
                          ft_moved=sum(r.get("moved", 0) for r in rep["ft"]), st_moved=sum(r.get("moved", 0) for r in rep["st"]),
                          ft_slots_touched=len([r for r in rep["ft"] if "moved" in r]), st_touched=len([r for r in rep["st"] if "moved" in r]), moved=len(moved))))
    json.dump(out, open(outf.replace(".json", ".rep.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
