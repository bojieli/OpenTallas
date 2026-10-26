#!/usr/bin/env python3
"""G0C-FIX (PATH-HBM, 2026-10-26): structural G0C fixes on the D-HBM-B1 native plan (b1n2 -> b1n3; b1n4 = argv[5] q_b100 column override + path_hbm_perbit_nudge.py).

 (b) hard-core lattice: q_b100 idx cores and hub subtree32 origins snapped to the 8.64-um lattice (smallest move, no
     overlap/halo clash); every type-frame coordinate tied to the moved core pins (core clock taps, internal-station
     from/to) moves with it; stations re-routed only when a hop breaks.
 (c) reach: q_spu1 L117x3/L138x3/L139x1 get explicit regs_um on the slot route, station 0 set D0 um inside the
     entry so all 6 downstream hops <= 0.9 x 405 (same station count, 0 cycles); q_su21 L136x1 station 3 slid along
     its route so hops 3/4 balance.
 (a) core faces, orient part: per failing core, greedy orient (R0/MX/MY/R180, box unchanged) accepted only when the
     type's core_faces error ports fall and the core's own do not rise; pins mirror in the box, so taps and station
     endpoints mirror with them; stations re-routed (RelayRouter, macro-free) with the station count kept (padded at
     the capture landing when the new route is shorter) -- cycle deltas recorded.
"""
import json, sys, copy, math, shutil
from pathlib import Path
WT, SRC, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, WT + "/tools/die_plan"); sys.path.insert(0, WT + "/physical/die_plan/hbm_arch")
import check as C, schema as S
from cores_b2 import RelayRouter, free_point
G = 8.64; LIM = 364.0; D0 = 10.0
# optional argv[5]: per-type lattice x targets "type=old:new,old:new;type2=..." (b1n4: q_b100 columns 17.28/267.84/509.76: the
# W strip keeps 2 FF columns (L70x1) and the col0|col1 channel 6 (L5x2 stages 1-2); the nearest snap 17.28/259.2/501.12 left
# that channel 2 columns (b1n2 had 3) and broke the per-bit census; no lattice choice keeps all four b1n2 strips)
XOVR = {}
for item in (sys.argv[5].split(";") if len(sys.argv) > 5 and sys.argv[5] else []):
    tn_, m_ = item.split("=")
    XOVR[tn_] = {round(float(o), 3): float(n) for o, n in (q.split(":") for q in m_.split(","))}
raw = json.loads((SRC / "die_plan.json").read_text())
T = raw["partition_types"]
log = dict(lattice=[], reach=[], orient=[], stations=[], cycle_delta={}, fails=[])

def boxes(t):
    return [(h["origin_um"][0] + h.get("track_offset_um", [0, 0])[0], h["origin_um"][1] + h.get("track_offset_um", [0, 0])[1],
             *h["outline_um"]) for h in t["hard_cores"]]

def ovl(a, b, m):
    return a[0] < b[0] + b[2] + m - 1e-6 and b[0] < a[0] + a[2] + m - 1e-6 and a[1] < b[1] + b[3] + m - 1e-6 and b[1] < a[1] + a[3] + m - 1e-6

def touched(t, ci):
    """(entry, end) pairs of internal stations whose endpoint is a pin of core ci."""
    for e in t.get("internal_stations", []):
        if str(e.get("launch", "")).startswith(ci + "."): yield e, "from_um"
        cap = str(e.get("capture", ""))
        if cap.startswith(ci + "."): yield e, "to_um"     # a core-level capture lands on the box edge: kept

def restation(t, e, why):
    w, h = t["outline_um"]; bx = boxes(t)
    if C._hops_ok(e["from_um"], e["regs_um"], e["to_um"], LIM): return
    n0 = len(e["regs_um"])
    fr = lambda p: free_point(p, bx, w, h)
    a, b = tuple(e["from_um"]), tuple(e["to_um"])
    land = fr(b)
    # first: the same station count evenly on the L route from -> to, each pulled to the nearest macro-free point
    seg = [a, (b[0], a[1]), b]; Lr = C.plen(seg)
    if n0:
        cand = [fr(C.point_at(seg, Lr * j / (n0 + 1))) for j in range(1, n0 + 1)]
        if C._hops_ok(a, cand, b, LIM):
            e["regs_um"] = [[round(v, 3) for v in p] for p in cand]
            e["note"] = e.get("note", "") + f" | G0C-FIX {why}: {n0} station(s) re-sited on the new route"
            log["stations"].append(dict(conn=e.get("conn"), why=why, before=n0, after=n0)); return
    try:
        regs = RelayRouter(bx, w, h, 360.0)(a, land)
    except ValueError as ex:
        log["fails"].append(f"{why} {e.get('conn')}: {ex}"); return
    if not regs or abs(regs[-1][0] - land[0]) + abs(regs[-1][1] - land[1]) > 1.0: regs = list(regs) + [land]
    while len(regs) < n0: regs.append(regs[-1])          # keep the scheduled latency (padding at the capture landing)
    if not C._hops_ok(a, regs, b, LIM): log["fails"].append(f"{why} {e.get('conn')}: hop > {LIM} after re-station")
    e["regs_um"] = [[round(v, 3) for v in p] for p in regs]
    e["note"] = e.get("note", "") + f" | G0C-FIX {why}: re-stationed {n0}->{len(regs)}"
    log["stations"].append(dict(conn=e.get("conn"), why=why, before=n0, after=len(regs)))
    if len(regs) != n0: log["cycle_delta"][e.get("conn")] = len(regs) - n0

def move_core(tn, ci, fn, why):
    """apply fn(x, y)->(x, y) to every tap / station endpoint tied to core ci's pins."""
    t = T[tn]
    for tp in t.get("clock", {}).get("taps", []):
        if tp["name"].split(".")[0] == ci or tp["name"].startswith(ci + "."):
            if tp.get("kind") == "core": tp["xy"] = [round(v, 4) for v in fn(*tp["xy"])]
    ents = list(touched(t, ci))
    for e, k in ents: e[k] = [round(v, 4) for v in fn(*e[k])]
    for e in {id(e): e for e, _ in ents}.values(): restation(t, e, why)

# ---------------- (b) lattice snap
for tn, t in T.items():
    for hc in t.get("hard_cores", []):
        ox, oy = hc["origin_um"]
        if abs(ox / G - round(ox / G)) < 1e-6 and abs(oy / G - round(oy / G)) < 1e-6: continue
        others = [b for h2, b in zip(t["hard_cores"], boxes(t)) if h2 is not hc]
        cw, ch = hc["outline_um"]; W, H = t["outline_um"]; halo = max(hc.get("halo_um", 0) or 0, G)
        cands = sorted({(math.floor(ox / G + 1e-9) * G, math.floor(oy / G + 1e-9) * G), (math.ceil(ox / G - 1e-9) * G, math.floor(oy / G + 1e-9) * G),
                        (math.floor(ox / G + 1e-9) * G, math.ceil(oy / G - 1e-9) * G), (math.ceil(ox / G - 1e-9) * G, math.ceil(oy / G - 1e-9) * G)},
                       key=lambda q: abs(q[0] - ox) + abs(q[1] - oy))
        if tn in XOVR:
            nx_ = XOVR[tn][round(ox, 3)]
            if abs(nx_ / G - round(nx_ / G)) > 1e-6: raise SystemExit(f"x override {tn} {nx_} off the {G}-um lattice")
            cands = sorted({(nx_, q[1]) for q in cands}, key=lambda q: abs(q[1] - oy))
        ok = None
        for nx, ny in cands:
            b = (nx, ny, cw, ch)
            if nx < 0 or ny < 0 or nx + cw > W or ny + ch > H: continue
            if any(ovl(b, o, halo) for o in others): continue
            ok = (round(nx, 4), round(ny, 4)); break
        if ok is None: log["fails"].append(f"lattice {tn} {hc['inst']}: no legal lattice origin"); continue
        dx, dy = ok[0] - ox, ok[1] - oy
        hc["origin_um"] = list(ok)
        hc["note"] = hc.get("note", "") + f" | G0C-FIX lattice snap [{ox:g},{oy:g}] -> [{ok[0]:g},{ok[1]:g}]"
        log["lattice"].append(dict(type=tn, core=hc["inst"], before=[ox, oy], after=list(ok)))
        x0, y0 = ox, oy
        def fn(x, y, dx=dx, dy=dy, x0=x0, y0=y0, cw=cw, ch=ch):
            if x0 - 1.0 <= x <= x0 + cw + 1.0 and y0 - 1.0 <= y <= y0 + ch + 1.0: return x + dx, y + dy
            return x, y
        move_core(tn, hc["inst"], fn, "lattice")

# ---------------- (c) reach
P = S.Plan(raw, SRC / "die_plan.json")
def slot_route(part, sname):
    for lid in P.lanes:
        for pt, sl, a, b in P.lane_crossings(lid):
            if pt == part and sl == sname:
                s = P.slot(pt, sl)
                seg = C.zroute(P.port_point(a), P.port_point(b), P.die_face(pt, s.get("in_face", "W")), P.die_face(pt, s.get("out_face", "E")))
                return [P.to_type(pt, q) for q in seg]
for sname in ("L117x3", "L138x3", "L139x1"):
    t = T["q_spu1"]; s = [x for x in t["ft_slots"] if x["name"] == sname][0]
    seg = slot_route("NW_spu1", sname); L = C.plen(seg); k = int(s["stations"])
    step = (L - D0) / k
    regs = [C.point_at(seg, D0 + j * step) for j in range(k)]
    bx = S.placed_macro_boxes(t)
    inside = [r for r in regs if any(x0 < r[0] < x1 and y0 < r[1] < y1 for x0, y0, x1, y1 in bx.values())]
    if inside: log["fails"].append(f"reach q_spu1.{sname}: station on a hard core {inside}")
    s["regs_um"] = [[round(v, 3) for v in r] for r in regs]
    s["note"] = (s.get("note", "") + f" | G0C-FIX reach: explicit regs on the slot route, station 0 {D0:g} um inside the entry, "
                 f"{k} hops of {step:.1f} um (<= 0.9x405); stations unchanged").lstrip(" |")
    log["reach"].append(dict(type="q_spu1", slot=sname, route_um=round(L, 1), step_um=round(step, 2), stations=k))
s = [x for x in T["q_su21"]["ft_slots"] if x["name"] == "L136x1"][0]
r3 = s["regs_um"][3]; r3n = [round(r3[0] + 3.5, 3), r3[1]]
s["regs_um"][3] = r3n
s["note"] = (s.get("note", "") + f" | G0C-FIX reach: station 3 slid {r3} -> {r3n} along the route (hops 3/4 balanced <= 364)").lstrip(" |")
log["reach"].append(dict(type="q_su21", slot="L136x1", moved=[r3, r3n]))

# ---------------- (a) orient
FX = lambda o: o in ("MY", "R180"); FY = lambda o: o in ("MX", "R180")
P = S.Plan(raw, SRC / "die_plan.json"); types_all = P.types
def errs(tn):
    P.types = {tn: types_all[tn]}; R = C.Report(True)
    C.check_core_faces(P, R, str(SRC), max_msgs=10**6); P.types = types_all
    d = {}
    for i in R.items:
        if i["check"] == "core_faces" and i["level"] == "ERROR":
            m = i["msg"]; d.setdefault(m.split(" core ")[1].split(" port ")[0], []).append(m.split(" port ")[1].split(":")[0])
    return d
for tn in sys.argv[4].split(","):
    t = T[tn]; rejected = set()
    for _ in range(8):
        base = errs(tn)
        for hc in t["hard_cores"]:
            if hc["inst"] not in base or hc["inst"] in rejected: continue
            o0 = hc.get("orient", "R0"); tot0 = sum(map(len, base.values())); own0 = len(base[hc["inst"]])
            best = None
            for o in ("R0", "MX", "MY", "R180"):
                if o == o0: continue
                hc["orient"] = o; b = errs(tn); tot = sum(map(len, b.values())); own = len(b.get(hc["inst"], []))
                if tot < tot0 and own <= own0 and (best is None or tot < best[1]): best = (o, tot, own)
            hc["orient"] = o0
            if not best: continue
            snap = copy.deepcopy(t); nlog = (len(log["stations"]), dict(log["cycle_delta"]), len(log["fails"]))
            o1 = best[0]; fx, fy = FX(o0) != FX(o1), FY(o0) != FY(o1)
            (x0, y0), (cw, ch) = hc["origin_um"], hc["outline_um"]
            hc["orient"] = o1
            hc["note"] = hc.get("note", "") + f" | G0C-FIX orient {o0} -> {o1}: core_faces error ports {own0} -> {best[2]} (type {tot0} -> {best[1]})"
            log["orient"].append(dict(type=tn, core=hc["inst"], before=o0, after=o1, own=[own0, best[2]], type_err=[tot0, best[1]]))
            def fn(x, y, fx=fx, fy=fy, x0=x0, y0=y0, cw=cw, ch=ch):
                if x0 - 1.0 <= x <= x0 + cw + 1.0 and y0 - 1.0 <= y <= y0 + ch + 1.0:
                    return (2 * x0 + cw - x if fx else x), (2 * y0 + ch - y if fy else y)
                return x, y
            move_core(tn, hc["inst"], fn, "orient")
            if log["cycle_delta"] != nlog[1] or len(log["fails"]) != nlog[2]:
                # an orient that needs extra stations (latency) or has no corridor is not taken: re-pin item instead
                added = {k: v for k, v in log["cycle_delta"].items() if nlog[1].get(k) != v}
                t.clear(); t.update(snap)
                del log["stations"][nlog[0]:]; log["cycle_delta"] = nlog[1]; del log["fails"][nlog[2]:]
                rec = log["orient"].pop(); rec["rejected"] = f"{len(added)} internal links would gain stations"
                log.setdefault("orient_rejected", []).append(rec); rejected.add(rec["core"])
                break
            base = errs(tn)
    log.setdefault("remaining", {})[tn] = errs(tn)

shutil.copytree(SRC, OUT)
(OUT / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
(OUT / "g0c_fix_report.json").write_text(json.dumps(log, indent=1) + "\n")
print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in log.items() if k != "remaining"}, indent=0)[:3000])
print("remaining", json.dumps({k: sum(map(len, v.values())) for k, v in log["remaining"].items()}))
