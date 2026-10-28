#!/usr/bin/env python3
"""DIE-HBM-9 hub ESTIMATE (no build, no adoption; COORD 07:59 DIE-HBM-8 ruling): fan-out core REPLICATION per hub half on
the 4x3 A+B face model of DIE-HBM-8 (hbm8/hub/hub_face_net.py: same edges, B set, hard-core spans subtracted, SA on the net
capacity). Every hub already holds 2 full-outline copies of each fan-out core (PATH-HBM-R9 service quadrants q0/q1).

Replication modes (--mode):
  base   hbm8 model unchanged (reference; reproduces hbm8 numbers for the same seed).
  half   copies per hub half (x-half of the 4x3 grid). Each edge between a fan-out copy and a client is served by the copy in
         the CLIENT's half (copy created there if the group has none); copies are pinned to their half in the SA. Edges between
         two fan-out groups stay inside the half of the first end. Shared sources (face buses whose lane ends outside the SU/SM
         client set: root/io/other hub) feed EVERY copy of the group (duplicated bits, the broadcast input crosses once).
  col    copies per grid column (4 per hub), same rules per column.
  ub     upper bound: fan-out-group edges carry no load at all (what replication can remove at most).
Usage: hub_replica_est.py die_plan.json duty.json out.json --mode half --groups pgp,cxij_q,calendar,sucore,smw,coll_body [--seed 1]"""
import json, math, random, collections, argparse, re
A = argparse.ArgumentParser(); A.add_argument("plan"); A.add_argument("duty"); A.add_argument("out")
A.add_argument("--nx", type=int, default=4); A.add_argument("--ny", type=int, default=3); A.add_argument("--seed", type=int, default=1)
A.add_argument("--iters", type=int, default=400000); A.add_argument("--hard-util", type=float, default=0.80)
A.add_argument("--halo", type=float, default=20.0); A.add_argument("--b-units", default="SU,IDX,HC,FUSED")
A.add_argument("--mode", default="half", choices=("base", "half", "col", "ub"))
A.add_argument("--groups", default="pgp,cxij_q,calendar,sucore,smw,coll_body")
A.add_argument("--affine", default="", help="half mode: bank-affine families (vmb,vmdel): an edge from a bank to a client in the other half goes to the partner bank Q(k^4) in the client half (= half-local data allocation by the static schedule; no new area)")
a = A.parse_args(); P = json.load(open(a.plan)); D = json.load(open(a.duty)); BU = set(a.b_units.split(",")) if a.b_units else set()
GRX = {"pgp": r"u_pgp_Q", "cxij_q": r"u_cxij_Q_q", "calendar": r"u_calendar_Q", "sucore": r"u_sucore_Q", "smw": r"u_smw_Q",
       "coll_body": r"u_hb_coll_Q_body", "coll_reduce": r"u_hb_coll_Q_reduce", "coll_edge": r"u_hb_coll_Q_edge", "coll_vm": r"u_hb_coll_Q_vm",
       "coll_ring": r"u_hb_coll_Q_ring", "cij": r"u_cij_Q", "hcollg": r"u_hcollg[il]_Q"}
GROUPS = [g for g in a.groups.split(",") if g]
UNIT = [("hb_coll", "COLL"), ("hcollg", "COLL"), ("cij", "COLL"), ("cxij", "COLL"), ("cxrc", "SU"), ("sucore", "SU"), ("pgp", "SU"), ("sfu", "SU"),
        ("svg", "SM"), ("smw", "SM"), ("xl_", "SM"), ("xq_", "SM"), ("wbk", "SM"), ("dbk", "DMA"), ("hb_idx", "IDX"), ("mu_", "FUSED"), ("quant", "FUSED"),
        ("hc_", "HC"), ("vmb", "VM"), ("vmks", "VM"), ("vmdel", "VM"), ("vms", "VM"), ("vmfc", "VM"), ("calendar", "VM"), ("ctl_Q", "VM")]
def unit(n):
    for k, u in UNIT:
        if k in n: return u
    return "UNK"
def duty(u): return D["unit_duty_vm_aggregate"] if u == "VM" else D["unit_duty"].get(u, 1.0)
parts = {x["name"]: x for x in P["partitions"]}; ports = {q["id"]: q for q in P["ports"]}
CLIENT = re.compile(r"_(su\d\d|sm\d)$")
out = {"scope": "ESTIMATE only, no build, no adoption; model UNCHECKED", "plan": a.plan, "grid": f"{a.nx}x{a.ny}", "mode": a.mode,
       "groups": GROUPS, "b_units": sorted(BU), "halo_um": a.halo, "seed": a.seed, "types": {}}
for hub, tn in (("NW_hub", "q_hub_nw"), ("NE_hub", "q_hub_ne")):
    t = P["partition_types"][tn]; W, H = t["outline_um"]; nx, ny = a.nx, a.ny; cw, ch = W / nx, H / ny
    bus2end = {}
    for l in P["lanes"]:
        ps = [ports[i] for i in l["ports"]]
        for q in ps:
            if q["src"]["part"] == hub: bus2end[q["src"]["bus"]] = ps[-1]["dst"]["part"]
            if q["dst"]["part"] == hub: bus2end[q["dst"]["bus"]] = ps[0]["src"]["part"]
    hard = t["hard_cores"]
    hrect = {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in hard}
    hmod = {h["inst"]: h["module"] for h in hard}
    def cell(x, y): return (min(nx - 1, max(0, int(x / cw))), min(ny - 1, max(0, int(y / ch))))
    def resolve(name, pt):
        if name.startswith("face bus"): return ("F",) + cell(*pt)
        for h, r in hrect.items():
            if r[0] - 1 <= pt[0] <= r[2] + 1 and r[1] - 1 <= pt[1] <= r[3] + 1: return ("H", h)
        return ("S", name.split(".")[0])
    def grp(n):
        if n[0] not in ("H", "S"): return None
        for g in GROUPS:
            if re.search(GRX[g], n[1]): return g
        return None
    raw = []; pos = collections.defaultdict(list)
    for s in t["internal_stations"]:
        u = resolve(s["launch"], s["from_um"]); v = resolve(s["capture"], s["to_um"])
        pos[u].append(s["from_um"]); pos[v].append(s["to_um"])
        k = s.get("serial_k") or 1
        uu = [unit(x) for x in (s["launch"], s["capture"]) if not x.startswith("face bus")]
        d = max(duty(x) for x in uu) * k; un = max(uu, key=duty)
        ends = [bus2end.get(x.split()[-1], "?") if x.startswith("face bus") else None for x in (s["launch"], s["capture"])]
        raw.append((u, v, d <= 0.5 and un in BU, un, s["bits"], ends))
    harea = {h: (r[2] - r[0]) * (r[3] - r[1]) for h, r in hrect.items()}
    def ccell(r): return cell((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    def init_cell0(n):
        if n[0] == "F": return n[1:]
        if n[0] == "H": return ccell(hrect[n[1]])
        ps = pos[n]; return cell(sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))
    # ---- replication rewrite --------------------------------------------------------------------------------------------
    def zone(c):
        return c[0] // (nx // 2) if a.mode == "half" else c[0]
    nz = 2 if a.mode == "half" else nx
    copies = collections.defaultdict(dict)     # group -> zone -> node
    added = []                                  # (group, zone, node, template, area, module)
    moved = []
    pinned = {}                                 # node -> zone
    if a.mode in ("half", "col"):
        existing = collections.defaultdict(list)
        for n in set(x for e in raw for x in e[:2]) | {("H", h) for h in hrect}:
            g = grp(n)
            if g: existing[g].append(n)
        for g, ns in existing.items():
            hs = sorted([n for n in ns if n[0] == "H"], key=lambda n: hrect[n[1]][0])
            for n in hs:
                z = zone(init_cell0(n)); copies[g].setdefault(z, n)
            tmpl = max(hs, key=lambda n: harea[n[1]]) if hs else None
            spare = [n for n in hs if n not in copies[g].values()]
            for z in range(nz):
                if z in copies[g]: continue
                if spare:  # an existing copy sits in an already-served zone: MOVE it (no added area)
                    n = spare.pop(0); r = hrect[n[1]]; c0 = ccell(r)
                    tc = (z * (nx // 2) + c0[0] % (nx // 2)) if a.mode == "half" else z
                    dx = (tc - c0[0]) * cw; hrect[n[1]] = (r[0] + dx, r[1], r[2] + dx, r[3]); copies[g][z] = n
                    moved.append(dict(group=g, zone=z, inst=n[1], dx_um=round(dx))); continue
                if tmpl is None: copies[g][z] = ("S", f"{g}@z{z}"); continue
                r = hrect[tmpl[1]]; c0 = ccell(r)
                tc = ((z * (nx // 2) if a.mode == "half" else z) + (c0[0] % (nx // 2) if a.mode == "half" else 0), c0[1])
                dx = (tc[0] - c0[0]) * cw; nm = f"{tmpl[1]}__rep_z{z}"
                hrect[nm] = (r[0] + dx, r[1], r[2] + dx, r[3]); harea[nm] = harea[tmpl[1]]; hmod[nm] = hmod[tmpl[1]]
                copies[g][z] = ("H", nm); added.append(dict(group=g, zone=z, inst=nm, template=tmpl[1], module=hmod[tmpl[1]],
                                                          area_mm2=round(harea[nm] / 1e6, 4)))
            for z, n in copies[g].items(): pinned[n] = z
            for n in ns:  # pieces not chosen as a zone's copy stay as extra copies of their own zone
                if n[0] == "H" and n not in pinned: pinned[n] = zone(init_cell0(n))
    AFF = [x for x in a.affine.split(",") if x]
    def partner(n, z):
        if n[0] != "H": return n
        for fam in AFF:
            m = re.fullmatch(rf"(u_{fam}_Q)(\d)(.*)", n[1])
            if m:
                k = int(m.group(2))
                if zone(init_cell0(n)) == z: return n
                c = ("H", f"{m.group(1)}{k ^ 4}{m.group(3)}")
                return c if c[1] in hrect and zone(init_cell0(c)) == z else n
        return n
    aff_moved = 0
    if AFF:
        raw2 = []
        for (u, v, el, un, b, ends) in raw:
            u2, v2 = partner(u, zone(init_cell0(v))), partner(v, zone(init_cell0(u)))
            if (u2, v2) != (u, v): aff_moved += b
            raw2.append((u2, v2, el, un, b, ends))
        raw = raw2
    edges = collections.Counter(); dup_bits = 0; repointed = 0
    for (u, v, el, un, b, ends) in raw:
        gu, gv = grp(u), grp(v)
        if a.mode == "ub" and (gu or gv): continue
        if a.mode in ("half", "col") and (gu or gv):
            if gu and gv:
                z = zone(init_cell0(u)); edges[(copies[gu][z], copies[gv][z], el, un)] += b; repointed += 1; continue
            g, other, oend = (gu, v, ends[1]) if gu else (gv, u, ends[0])
            shared = other[0] == "F" and not (oend and CLIENT.search(oend))
            if shared:
                me = u if gu else v
                if a.mode == "half": zs = [zone(init_cell0(me))]            # each half copy already has its own inputs
                else: h0 = init_cell0(me)[0] // (nx // 2); zs = [h0 * (nx // 2) + i for i in range(nx // 2)]
                for z in zs:
                    key = (copies[g][z], other, el, un) if gu else (other, copies[g][z], el, un); edges[key] += b
                dup_bits += b * (len(zs) - 1); continue
            z = zone(init_cell0(other)); c = copies[g][z]
            edges[(c, other, el, un) if gu else (other, c, el, un)] += b; repointed += 1; continue
        edges[(u, v, el, un)] += b
    nodes = sorted(set(x for e in edges for x in e[:2]), key=str)
    for h in hrect:
        if ("H", h) not in nodes: nodes.append(("H", h))
    def init_cell(n):
        if n[0] == "H": return ccell(hrect[n[1]])
        if n[0] == "S" and n[1].count("@z"): z = int(n[1].split("@z")[1]); return ((z * (nx // 2) if a.mode == "half" else z), 1)
        return init_cell0(n)
    all_faces = [("v", x, y) for x in range(nx - 1) for y in range(ny)] + [("h", x, y) for x in range(nx) for y in range(ny - 1)]
    def flen(f): return ch if f[0] == "v" else cw
    def core_block(h, c):
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
    def ecls(e):
        u, v = e[0], e[1]
        g = grp(u) or grp(v) or (grp(("H", u[1].split("__rep")[0])) if u[0] == "H" and "__rep" in u[1] else None)
        if g: return "fanout:" + g
        us = [unit(n[1]) for n in (u, v) if n[0] != "F"]
        return "face:" + ("/".join(sorted(set(us))) or "-") if (u[0] == "F" or v[0] == "F") else "core:" + "/".join(sorted(set(us)))
    def loads(mode, place, by=None):
        L = collections.Counter()
        for e, b in edges.items():
            u, v, el, un = e
            bb = b / 2 if (mode == "B" and el) else b
            for f in faces(place[u], place[v]):
                L[f] += bb
                if by is not None: by[f][ecls(e)] += bb
        return L
    def blocked(place):
        per = collections.defaultdict(dict)
        for n in nodes:
            if n[0] == "H":
                for f, s in core_block(n[1], place[n]).items(): per[f][n[1]] = s
        return per
    def summary(mode, place):
        by = collections.defaultdict(collections.Counter)
        L = loads(mode, place, by); per = blocked(place); rows = []
        for f in all_faces:
            bl = union_len(per[f].values()) if f in per else 0.0; net = max(flen(f) - bl, 1.0)
            rows.append(dict(face=f"{f[0]}{f[1]}{f[2]}", bits=round(L[f]), len_um=round(flen(f), 1), blocked_um=round(bl, 1),
                             ratio_full=round(L[f] / (6 * flen(f)), 3), ratio_net=round(L[f] / (6 * net), 3),
                             by_class={k: round(v) for k, v in by[f].most_common(6)}))
        rows.sort(key=lambda r: -r["ratio_net"])
        cut = {}
        for x in range(nx - 1):
            cs = collections.Counter()
            for y in range(ny): cs.update(by[("v", x, y)])
            cut[f"v{x}"] = dict(bits=round(sum(cs.values())), net_pins=round(sum(6 * max(flen(("v", x, y)) - (union_len(per[("v", x, y)].values()) if ("v", x, y) in per else 0), 1) for y in range(ny))),
                                fanout_bits=round(sum(v for k, v in cs.items() if k.startswith("fanout"))), top={k: round(v) for k, v in cs.most_common(8)})
        hA = collections.Counter()
        for n in nodes:
            if n[0] == "H": hA[tuple(place[n])] += harea[n[1]]
        return dict(worst_ratio_full=max(r["ratio_full"] for r in rows), worst_ratio_net=rows[0]["ratio_net"],
                    faces_over_net=sum(r["ratio_net"] > 1.0 for r in rows), faces=len(rows), worst_faces=rows[:5], all_faces=rows,
                    vertical_cuts=cut, max_cell_hard_util=round(max(hA.values()) / (cw * ch), 3),
                    place={("/".join(map(str, n))): list(c) for n, c in place.items() if n[0] != "F"})
    base_place = {n: init_cell(n) for n in nodes}
    def zone_ok(n, c): return n not in pinned or zone(c) == pinned[n]
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
            if new == old or not zone_ok(n, new): continue
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
    res = {"added_copies": added, "moved_copies": moved, "added_hard_mm2": round(sum(x["area_mm2"] for x in added), 3),
           "duplicated_shared_bits": dup_bits, "affine_repointed_bits": aff_moved, "repointed_edges": repointed, "station_bits_after": sum(edges.values())}
    p2 = sa("B", True); res["A+B_net"] = summary("B", p2)
    out["types"][tn] = res
    print(tn, a.mode, "aff", aff_moved, "added", len(added), res["added_hard_mm2"], "mm2 dup", dup_bits, "worst_net", res["A+B_net"]["worst_ratio_net"],
          "over", res["A+B_net"]["faces_over_net"], "cuts", {k: (v["bits"], v["net_pins"], v["fanout_bits"]) for k, v in res["A+B_net"]["vertical_cuts"].items()},
          "hutil", res["A+B_net"]["max_cell_hard_util"], flush=True)
json.dump(out, open(a.out, "w"), indent=1)
