#!/usr/bin/env python3
"""DIE-HBM-10 hubplace: copy of hbm9/rep/hub_replica_est_q.py (model unchanged) + --placer cons (deterministic constructive
placement: cluster growth from the fixed face windows, best cell per node under the same ^8 net-capacity cost, then greedy
best-move/best-swap passes, no randomness) and --snap (hard cores shifted fully inside their home grid cell, off every cut line,
+halo). --placer sa reproduces hbm9.

DIE-HBM-9 hub ESTIMATE (no build, no adoption; COORD 07:59 DIE-HBM-8 ruling): fan-out core REPLICATION per hub half on
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
A.add_argument("--affine-col", action="store_true", help="bank-affine at COLUMN (quarter) level: a bank->client edge goes to a same-family bank in the client column (k-ordered pick), else half partner")
A.add_argument("--bank-spread", action="store_true", help="move even-k banks (u_{fam}_Q<k>*) one column toward the half edge so every column of a half holds banks")
A.add_argument("--face-align", action="store_true", help="N/S hub-face bus windows moved over the client column (plan face-pin assignment)")
A.add_argument("--cut-clear", action="store_true", help="hard cores straddling a vertical grid cut line shifted off it (+halo) toward their larger side")
A.add_argument("--no-fix-resolve", dest="fix_resolve", action="store_false", help="hbm9 behaviour: resolve station pins on the MOVED rects")
A.add_argument("--pack", action="store_true", help="cons: a core fits a cell only if the cell contents pack legally (legal_pack.pack: MaxRects BL, halo off cut lines, 2 um spacing); final hard rects = packed rects")
A.add_argument("--order", default="conn", choices=("conn", "area", "tot"), help="cons growth order: most bits to placed nodes / largest hard area first / most total bits first")
A.add_argument("--placer", default="sa", choices=("sa", "cons"))
A.add_argument("--snap", action="store_true", help="hard cores that fit a grid cell are shifted fully inside their centre cell (+halo): off v0/v1/v2 and h cuts")
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
    hrect0 = dict(hrect)  # DIE-HBM-10: stations resolve on the PLAN rects (cut-clear/snap moves must not orphan their pins)
    cleared = []
    if a.cut_clear:
        for h, r in list(hrect.items()):
            for k in range(1, nx):
                X = k * cw
                if r[0] - a.halo < X < r[2] + a.halo:
                    dx = (X + a.halo - r[0]) if (r[2] - X) > (X - r[0]) else (X - a.halo - r[2])
                    if 0 <= r[0] + dx and r[2] + dx <= W: hrect[h] = r = (r[0] + dx, r[1], r[2] + dx, r[3]); cleared.append((h, round(dx, 1)))
        print("cut-clear moved", len(cleared), flush=True)
    snapped = []
    if a.snap:
        for h, r in list(hrect.items()):
            w_, h_ = r[2] - r[0], r[3] - r[1]
            cx, cy = min(nx - 1, max(0, int((r[0] + r[2]) / 2 / cw))), min(ny - 1, max(0, int((r[1] + r[3]) / 2 / ch)))
            dx = dy = 0.0
            if w_ + 2 * a.halo <= cw:
                lo, hi = cx * cw + a.halo + (a.halo if cx > 0 else -a.halo), (cx + 1) * cw - a.halo - (a.halo if cx < nx - 1 else -a.halo)
                lo = cx * cw + (a.halo + 1 if cx > 0 else 0); hi = (cx + 1) * cw - (a.halo + 1 if cx < nx - 1 else 0)
                if r[0] < lo: dx = lo - r[0]
                elif r[2] > hi: dx = hi - r[2]
            if h_ + 2 * a.halo <= ch:
                lo = cy * ch + (a.halo + 1 if cy > 0 else 0); hi = (cy + 1) * ch - (a.halo + 1 if cy < ny - 1 else 0)
                if r[1] < lo: dy = lo - r[1]
                elif r[3] > hi: dy = hi - r[3]
            if dx or dy: hrect[h] = (r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy); snapped.append((h, round(dx, 1), round(dy, 1)))
        print("snap moved", len(snapped), "of", len(hrect), "too big for a cell", sum(1 for r in hrect.values() if r[2]-r[0]+2*a.halo > cw or r[3]-r[1]+2*a.halo > ch), flush=True)
    NSF = set()
    def cell(x, y): return (min(nx - 1, max(0, int(x / cw))), min(ny - 1, max(0, int(y / ch))))
    def resolve(name, pt):
        if name.startswith("face bus"):
            n = ("F",) + cell(*pt)
            if pt[1] < 1.0 or pt[1] > H - 1.0: NSF.add(n)
            return n
        for h, r in (hrect0 if a.fix_resolve else hrect).items():
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
    spread = []
    if a.bank_spread:
        for fam in AFF:
            for h in list(hrect):
                m = re.fullmatch(rf"u_{fam}_Q(\d)(.*)", h)
                if m and int(m.group(1)) % 2 == 0:
                    r = hrect[h]; hrect[h] = (r[0] - cw, r[1], r[2] - cw, r[3]); spread.append(h)
        print("bank-spread moved", len(spread), flush=True)
    def partner(n, z, zc=None):
        if n[0] != "H": return n
        for fam in AFF:
            m = re.fullmatch(rf"(u_{fam}_Q)(\d)(.*)", n[1])
            if m:
                k = int(m.group(2))
                if a.affine_col and zc is not None:
                    if init_cell0(n)[0] == zc: return n
                    cand = sorted(h for h in hrect if re.fullmatch(rf"u_{fam}_Q\d{re.escape(m.group(3))}", h) and ccell(hrect[h])[0] == zc)
                    if cand: return ("H", cand[k % len(cand)])
                if zone(init_cell0(n)) == z: return n
                c = ("H", f"{m.group(1)}{k ^ 4}{m.group(3)}")
                return c if c[1] in hrect and zone(init_cell0(c)) == z else n
        return n
    aff_moved = 0
    if AFF:
        raw2 = []
        for (u, v, el, un, b, ends) in raw:
            u2, v2 = partner(u, zone(init_cell0(v)), init_cell0(v)[0]), partner(v, zone(init_cell0(u)), init_cell0(u)[0])
            if (u2, v2) != (u, v): aff_moved += b
            raw2.append((u2, v2, el, un, b, ends))
        raw = raw2
    fa_bits = 0
    if a.face_align:
        raw2 = []
        for (u, v, el, un, b, ends) in raw:
            if u in NSF and v[0] != "F":
                c = init_cell0(v)[0]
                if c != u[1]: u = ("F", c, u[2]); NSF.add(u); fa_bits += b
            elif v in NSF and u[0] != "F":
                c = init_cell0(u)[0]
                if c != v[1]: v = ("F", c, v[2]); NSF.add(v); fa_bits += b
            raw2.append((u, v, el, un, b, ends))
        raw = raw2
        print("face-align moved bits", fa_bits, flush=True)
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
    def cons(mode, net_obj):
        inc = collections.defaultdict(list)
        for e, b in edges.items():
            if e[0] == e[1]: continue
            bb = b / 2 if (mode == "B" and e[2]) else b
            inc[e[0]].append((e, bb)); inc[e[1]].append((e, bb))
        place = {n: base_place[n] for n in nodes if n[0] == "F"}
        L = collections.Counter(); hA = collections.Counter(); Acap = a.hard_util * cw * ch
        per = collections.defaultdict(dict); bl = {f: 0.0 for f in all_faces}
        def capf(f, b_=None): return 6.0 * (max(flen(f) - (bl[f] if b_ is None else b_), 1.0) if net_obj else flen(f))
        def fc(f, l, b_=None): return (l / capf(f, b_)) ** 8
        def delta(n, old, new):
            dL = collections.Counter()
            for e, bb in inc[n]:
                o = e[1] if e[0] == n else e[0]
                if o not in place: continue
                co = place[o]
                if old is not None:
                    for f in (faces(old, co) if e[0] == n else faces(co, old)): dL[f] -= bb
                for f in (faces(new, co) if e[0] == n else faces(co, new)): dL[f] += bb
            newbl = {}
            if n[0] == "H" and net_obj:
                ob = core_block(n[1], old) if old is not None else {}; nb = core_block(n[1], new)
                for f in set(ob) | set(nb):
                    d_ = dict(per[f]); d_.pop(n[1], None)
                    if f in nb: d_[n[1]] = nb[f]
                    newbl[f] = (union_len(d_.values()), d_)
            dc = 0.0
            for f in set(dL) | set(newbl):
                dc += fc(f, L[f] + dL.get(f, 0), newbl[f][0] if f in newbl else None) - fc(f, L[f])
            return dc, dL, newbl
        def commit(n, old, new, dL, newbl):
            for f, d in dL.items(): L[f] += d
            for f, (b_, d_) in newbl.items(): bl[f] = b_; per[f] = d_
            place[n] = new
            if n[0] == "H":
                if old is not None: hA[old] -= harea[n[1]]
                hA[new] += harea[n[1]]
        def area(n): return harea[n[1]] if n[0] == "H" else 0.0
        cells = [(x, y) for x in range(nx) for y in range(ny)]
        def fits(n, c, old=None): return n[0] != "H" or hA[c] + area(n) - (area(n) if c == old else 0) <= Acap + 1e-6
        import os as _os, sys
        sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import legal_pack as _LP
        pcache = {}
        def big(n): r = hrect[n[1]]; return (r[2] - r[0]) + 2 * a.halo > cw or (r[3] - r[1]) + 2 * a.halo > ch
        def inner(c):
            x0 = c[0] * cw + (a.halo + 1 if c[0] > 0 else 0); x1 = (c[0] + 1) * cw - (a.halo + 1 if c[0] < nx - 1 else 0)
            y0 = c[1] * ch + (a.halo + 1 if c[1] > 0 else 0); y1 = (c[1] + 1) * ch - (a.halo + 1 if c[1] < ny - 1 else 0)
            return x0, y0, x1, y1
        def packs(names, c):
            k = (c, tuple(sorted(names)))
            if k not in pcache:
                x0, y0, x1, y1 = inner(c)
                ob = [(r[0] - a.halo - x0, r[1] - a.halo - y0, r[2] + a.halo - x0, r[3] + a.halo - y0) for r in BIGR]
                pcache[k] = _LP.pack(x1 - x0, y1 - y0, [(h, hrect[h][2] - hrect[h][0], hrect[h][3] - hrect[h][1]) for h in names], ob)
            return pcache[k]
        def members(c, excl=None): return [m[1] for m, cc in place.items() if m[0] == "H" and cc == c and m != excl and not big(m)]
        if a.pack:
            _fits_area = fits
            def fits(n, c, old=None, excl=None):
                if n[0] != "H" or big(n): return _fits_area(n, c, old)
                if excl is None and not _fits_area(n, c, old): return False
                return packs([m for m in members(c, excl) if m != n[1]] + [n[1]], c) is not None
        def md(c, d): return abs(c[0] - d[0]) + abs(c[1] - d[1])
        BIGN = [n for n in nodes if n[0] == "H" and big(n)] if a.pack else []
        BIGR = [hrect[n[1]] for n in BIGN]
        for n in BIGN:
            c = ccell(hrect[n[1]]); dc, dL, nb = delta(n, None, c); commit(n, None, c, dL, nb)
        unpl = [n for n in nodes if n[0] != "F" and n not in BIGN]; tie = {n: str(n) for n in unpl}
        conn = collections.Counter()
        for n in unpl:
            for e, bb in inc[n]:
                o = e[1] if e[0] == n else e[0]
                if o in place: conn[n] += bb
        order = []
        while unpl:
            if a.order == "conn": n = max(unpl, key=lambda m: (conn[m], area(m), tie[m]))
            elif a.order == "area": n = max(unpl, key=lambda m: (area(m), conn[m], tie[m]))
            else: n = max(unpl, key=lambda m: (sum(bb for _, bb in inc[m]), area(m), tie[m]))
            cand = [c for c in cells if zone_ok(n, c) and fits(n, c)]
            if not cand: cand = sorted([c for c in cells if zone_ok(n, c)], key=lambda c: hA[c])[:1]
            best = min(cand, key=lambda c: (round(delta(n, None, c)[0], 12), md(c, base_place[n]), c))
            dc, dL, nb = delta(n, None, best); commit(n, None, best, dL, nb); unpl.remove(n); order.append(n)
            for e, bb in inc[n]:
                o = e[1] if e[0] == n else e[0]
                if o not in place: conn[o] += bb
        cost = lambda: sum(fc(f, L[f]) for f in all_faces)
        log = [dict(stage="constructive", worst=round(max(L[f] / capf(f) for f in all_faces), 3))]
        mov = sorted([n for n in nodes if n[0] != "F" and n not in BIGN], key=str)
        for ps in range(40):
            gain = 0.0
            for n in mov:
                old = place[n]
                bc, bd = 0.0, None
                for c in cells:
                    if c == old or not zone_ok(n, c) or not fits(n, c, old): continue
                    d = delta(n, old, c)
                    if d[0] < bc - 1e-12: bc, bd = d[0], (c, d)
                if bd: commit(n, old, bd[0], bd[1][1], bd[1][2]); gain += bc
            # pair swaps of hard cores between cells (area-neutral-ish), first improving swap per core
            Hs = [n for n in mov if n[0] == "H"]
            for i, u in enumerate(Hs):
                for w in Hs[i + 1:]:
                    cu, cw_ = place[u], place[w]
                    if cu == cw_ or not zone_ok(u, cw_) or not zone_ok(w, cu): continue
                    if hA[cw_] - area(w) + area(u) > Acap + 1e-6 or hA[cu] - area(u) + area(w) > Acap + 1e-6: continue
                    if a.pack and not (fits(u, cw_, excl=w) and fits(w, cu, excl=u)): continue
                    c0 = cost(); d1 = delta(u, cu, cw_); commit(u, cu, cw_, *d1[1:]); d2 = delta(w, cw_, cu)
                    if d1[0] + d2[0] < -1e-12 * max(c0, 1e-9):
                        commit(w, cw_, cu, *d2[1:]); gain += d1[0] + d2[0]
                    else:
                        r_ = delta(u, cw_, cu); commit(u, cw_, cu, *r_[1:])
            log.append(dict(stage=f"pass{ps}", gain=gain, worst=round(max(L[f] / capf(f) for f in all_faces), 3)))
            if gain > -1e-12 * max(cost(), 1e-9): break
        print("cons", log[0], log[-1], len(log) - 1, "passes", flush=True)
        out.setdefault("cons_log", {})[tn] = log
        if a.pack:
            lg = 0
            for c in cells:
                ms = members(c); pk = packs(ms, c) if ms else {}
                if pk is None: print("PACK FAIL", c, flush=True); continue
                x0, y0, _, _ = inner(c)
                for h, (px, py) in pk.items():
                    r = hrect[h]; w_, h_ = r[2] - r[0], r[3] - r[1]; hrect[h] = (x0 + px, y0 + py, x0 + px + w_, y0 + py + h_); lg += 1
            print("pack legal rects", lg, flush=True)
        return place
    res = {"added_copies": added, "moved_copies": moved, "added_hard_mm2": round(sum(x["area_mm2"] for x in added), 3),
           "duplicated_shared_bits": dup_bits, "affine_repointed_bits": aff_moved, "repointed_edges": repointed, "station_bits_after": sum(edges.values())}
    p2 = cons("B", True) if a.placer == "cons" else sa("B", True); res["A+B_net"] = summary("B", p2)
    res["snapped"] = snapped; res["hrect"] = {h: [round(v, 1) for v in r] for h, r in hrect.items()}; res["outline_um"] = [W, H]
    out["types"][tn] = res
    print(tn, a.mode, "aff", aff_moved, "added", len(added), res["added_hard_mm2"], "mm2 dup", dup_bits, "worst_net", res["A+B_net"]["worst_ratio_net"],
          "over", res["A+B_net"]["faces_over_net"], "cuts", {k: (v["bits"], v["net_pins"], v["fanout_bits"]) for k, v in res["A+B_net"]["vertical_cuts"].items()},
          "hutil", res["A+B_net"]["max_cell_hard_util"], flush=True)
json.dump(out, open(a.out, "w"), indent=1)
