#!/usr/bin/env python3
"""DIE-HBM-8 hub ESTIMATE (no build): A+B face ratios on the 4x3 regional grid with HARD-CORE SPANS SUBTRACTED from the
face length (COORD 07:29 condition 2). Same edge model as hbm7/hub/hub_replace_est.py (station bits, B = 2:1 on eligible
links, SA re-placement of hub contents by connectivity, same outline and cores).
Face capacity = 6 pins/um x (face length - union of hard-core spans on the face). A hard core blocks a face where its
rectangle (plus a halo, default 20 um) touches the face line; the blocked span is its projection on the face.
Hard-core position rule: an unmoved core keeps its planned rectangle; a core the SA moves to another cell keeps its offset
inside the cell (shifted by whole cells), so a core that straddles a grid line in the plan still straddles it after a move.
Two scorings: (rescore) SA on full length as in hbm7, then scored net of spans; (net) SA objective on the net capacity.
Usage: hub_face_net.py die_plan.json duty.json out.json [--b-units SU,SM,IDX,HC,FUSED] [--seed 1]"""
import json, math, random, collections, argparse
A = argparse.ArgumentParser(); A.add_argument("plan"); A.add_argument("duty"); A.add_argument("out")
A.add_argument("--nx", type=int, default=4); A.add_argument("--ny", type=int, default=3); A.add_argument("--seed", type=int, default=1)
A.add_argument("--iters", type=int, default=400000); A.add_argument("--hard-util", type=float, default=0.80)
A.add_argument("--halo", type=float, default=20.0); A.add_argument("--b-units", default="SU,SM,IDX,HC,FUSED")
a = A.parse_args(); P = json.load(open(a.plan)); D = json.load(open(a.duty)); BU = set(a.b_units.split(",")) if a.b_units else set()
UNIT = [("hb_coll", "COLL"), ("hcollg", "COLL"), ("cij", "COLL"), ("cxij", "COLL"), ("cxrc", "SU"), ("sucore", "SU"), ("pgp", "SU"), ("sfu", "SU"),
        ("svg", "SM"), ("smw", "SM"), ("xl_", "SM"), ("xq_", "SM"), ("wbk", "SM"), ("dbk", "DMA"), ("hb_idx", "IDX"), ("mu_", "FUSED"), ("quant", "FUSED"),
        ("hc_", "HC"), ("vmb", "VM"), ("vmks", "VM"), ("vmdel", "VM"), ("vms", "VM"), ("vmfc", "VM"), ("calendar", "VM"), ("ctl_Q", "VM")]
def unit(n):
    for k, u in UNIT:
        if k in n: return u
    return "UNK"
def duty(u): return D["unit_duty_vm_aggregate"] if u == "VM" else D["unit_duty"].get(u, 1.0)
out = {"scope": "ESTIMATE only, no build, no adoption", "plan": a.plan, "grid": f"{a.nx}x{a.ny}", "b_units": sorted(BU), "halo_um": a.halo, "seed": a.seed, "types": {}}
for tn in ("q_hub_nw", "q_hub_ne"):
    t = P["partition_types"][tn]; W, H = t["outline_um"]; nx, ny = a.nx, a.ny; cw, ch = W / nx, H / ny
    hard = t["hard_cores"]
    hrect = {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in hard}
    def cell(x, y): return (min(nx - 1, max(0, int(x / cw))), min(ny - 1, max(0, int(y / ch))))
    def resolve(name, pt):
        if name.startswith("face bus"): return ("F",) + cell(*pt)
        for h, r in hrect.items():
            if r[0] - 1 <= pt[0] <= r[2] + 1 and r[1] - 1 <= pt[1] <= r[3] + 1: return ("H", h)
        return ("S", name.split(".")[0])
    edges = collections.Counter(); pos = collections.defaultdict(list)
    for s in t["internal_stations"]:
        u = resolve(s["launch"], s["from_um"]); v = resolve(s["capture"], s["to_um"])
        pos[u].append(s["from_um"]); pos[v].append(s["to_um"])
        k = s.get("serial_k") or 1
        uu = [unit(x) for x in (s["launch"], s["capture"]) if not x.startswith("face bus")]
        d = max(duty(x) for x in uu) * k; un = max(uu, key=duty)
        edges[(u, v, d <= 0.5 and un in BU, un)] += s["bits"]
    nodes = sorted(set(x for e in edges for x in e[:2]), key=str)
    for h in hrect:
        if ("H", h) not in nodes: nodes.append(("H", h))
    harea = {h: (r[2] - r[0]) * (r[3] - r[1]) for h, r in hrect.items()}
    def ccell(r): return cell((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    def init_cell(n):
        if n[0] == "F": return n[1:]
        if n[0] == "H": return ccell(hrect[n[1]])
        ps = pos[n]; return cell(sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))
    all_faces = [("v", x, y) for x in range(nx - 1) for y in range(ny)] + [("h", x, y) for x in range(nx) for y in range(ny - 1)]
    def flen(f): return ch if f[0] == "v" else cw
    def core_block(h, c):
        """{face: (lo, hi)} spans blocked by core h placed in cell c (offset rule)."""
        r = hrect[h]; c0 = ccell(r); dx, dy = (c[0] - c0[0]) * cw, (c[1] - c0[1]) * ch
        x0, y0, x1, y1 = r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy; res = {}
        for f in all_faces:
            if f[0] == "v":
                X = (f[1] + 1) * cw; lo, hi = max(y0, f[2] * ch), min(y1, (f[2] + 1) * ch)
                if x0 - a.halo <= X <= x1 + a.halo and hi > lo: res[f] = (lo, hi)
            else:
                Y = (f[2] + 1) * ch; lo, hi = max(x0, f[1] * cw), min(x1, (f[1] + 1) * cw)
                if y0 - a.halo <= Y <= y1 + a.halo and hi > lo: res[f] = (lo, hi)
        return res
    def union_len(iv):
        tot = 0.0; cur = None
        for lo, hi in sorted(iv):
            if cur is None or lo > cur[1]:
                if cur: tot += cur[1] - cur[0]
                cur = [lo, hi]
            else: cur[1] = max(cur[1], hi)
        if cur: tot += cur[1] - cur[0]
        return tot
    def faces(ca, cb):
        (ax, ay), (bx, by) = ca, cb; f = []
        for x in range(min(ax, bx), max(ax, bx)): f.append(("v", x, ay))
        for y in range(min(ay, by), max(ay, by)): f.append(("h", bx, y))
        return f
    def loads(mode, place):
        L = collections.Counter()
        for (u, v, el, un), b in edges.items():
            bb = b / 2 if (mode == "B" and el) else b
            for f in faces(place[u], place[v]): L[f] += bb
        return L
    def blocked(place):
        per = collections.defaultdict(dict)
        for n in nodes:
            if n[0] == "H":
                for f, s in core_block(n[1], place[n]).items(): per[f][n[1]] = s
        return per
    def summary(mode, place):
        L = loads(mode, place); per = blocked(place); rows = []
        for f in all_faces:
            bl = union_len(per[f].values()) if f in per else 0.0; net = max(flen(f) - bl, 1.0)
            rows.append(dict(face=f"{f[0]}{f[1]}{f[2]}", bits=round(L[f]), len_um=round(flen(f), 1), blocked_um=round(bl, 1),
                             ratio_full=round(L[f] / (6 * flen(f)), 3), ratio_net=round(L[f] / (6 * net), 3)))
        rows.sort(key=lambda r: -r["ratio_net"])
        return dict(worst_ratio_full=max(r["ratio_full"] for r in rows), worst_ratio_net=rows[0]["ratio_net"],
                    faces_over_net=sum(r["ratio_net"] > 1.0 for r in rows), faces=len(rows), worst_faces=rows[:5], all_faces=rows,
                    place={("/".join(map(str, n))): list(c) for n, c in place.items() if n[0] != "F"})
    base_place = {n: init_cell(n) for n in nodes}
    res = {"base": summary("base", base_place), "B": summary("B", base_place)}
    def sa(mode, net_obj):
        rnd = random.Random(a.seed); place = dict(base_place); inc = collections.defaultdict(list)
        for e, b in edges.items():
            bb = b / 2 if (mode == "B" and e[2]) else b
            inc[e[0]].append((e, bb)); inc[e[1]].append((e, bb))
        L = loads(mode, place); hA = collections.Counter()
        for n in nodes:
            if n[0] == "H": hA[place[n]] += harea[n[1]]
        Acap = max(a.hard_util * cw * ch, max(hA.values()))
        per = blocked(place)
        bl = {f: (union_len(per[f].values()) if f in per else 0.0) for f in all_faces}
        def capf(f): return 6.0 * (max(flen(f) - bl[f], 1.0) if net_obj else flen(f))
        def fc(f, l, c=None): return (l / (c if c is not None else capf(f))) ** 8
        cost = sum(fc(f, L[f]) for f in all_faces); mov = [n for n in nodes if n[0] != "F" and n in inc]
        for it in range(a.iters):
            n = rnd.choice(mov); old = place[n]
            new = (min(nx - 1, max(0, old[0] + rnd.choice((-1, 0, 1)))), min(ny - 1, max(0, old[1] + rnd.choice((-1, 0, 1)))))
            if new == old: continue
            if n[0] == "H" and hA[new] + harea[n[1]] > Acap: continue
            dL = collections.Counter()
            for e, bb in inc[n]:
                u, v = e[0], e[1]
                if u == v: continue
                cu, cv = place[u], place[v]
                for f in faces(cu, cv): dL[f] -= bb
                cu2 = new if u == n else cu; cv2 = new if v == n else cv
                for f in faces(cu2, cv2): dL[f] += bb
            newbl = {}
            if n[0] == "H" and net_obj:
                ob = core_block(n[1], old); nb = core_block(n[1], new)
                for f in set(ob) | set(nb):
                    d_ = dict(per[f]); d_.pop(n[1], None)
                    if f in nb: d_[n[1]] = nb[f]
                    newbl[f] = (union_len(d_.values()), d_)
            touched = set(dL) | set(newbl)
            dc = 0.0
            for f in touched:
                c_new = 6.0 * max(flen(f) - newbl[f][0], 1.0) if f in newbl else None
                dc += fc(f, L[f] + dL.get(f, 0), c_new) - fc(f, L[f])
            Tk = 0.5 * (1 - it / a.iters) + 1e-6
            if dc < 0 or rnd.random() < math.exp(-dc / (Tk * max(cost, 1e-9))):
                for f, d in dL.items(): L[f] += d
                for f, (b_, d_) in newbl.items(): bl[f] = b_; per[f] = d_
                cost += dc; place[n] = new
                if n[0] == "H": hA[old] -= harea[n[1]]; hA[new] += harea[n[1]]
        return place
    for mode, nm in (("base", "A"), ("B", "A+B")):
        p1 = sa(mode, False); res[nm + "_rescore"] = summary(mode, p1)
        p2 = sa(mode, True); res[nm + "_net"] = summary(mode, p2)
        res[nm + "_net_moved_nodes"] = sum(p2[n] != base_place[n] for n in nodes)
    out["types"][tn] = res
    print(tn, json.dumps({k: (v["worst_ratio_full"], v["worst_ratio_net"], v["faces_over_net"]) for k, v in res.items() if isinstance(v, dict)}), flush=True)
json.dump(out, open(a.out, "w"), indent=1)
