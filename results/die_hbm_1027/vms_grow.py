#!/usr/bin/env python3
"""DIE-HBM-3 C20f (COORD 22:18 ruling (c)): vms_glue height growth only (REPACK grow-alt dh), pins in centre form (0.096 inset).
Derived from DIE-HBM/REPACK repack.py: C17g outline-growth re-pack as a machine-applicable delta on a plan dir (C19), for the C20 event.
usage: repack.py PLANDIR OUTDIR
Reads PLANDIR/die_plan.json + cores/ (never writes there). Writes OUTDIR/c20_repack_delta.json, OUTDIR/cores/*.json,
OUTDIR/repack_report.json.
Method
 1. pin6 face capacity per pins table (5.5 pins/um over L - 2*8.64; face = nearest edge). Over faces -> grow the side
    that carries the face: N/S over -> width, E/W over -> height, by ceil((n/5.5 + 17.28 - L)/0.864)*0.864 (C17 respread.py
    (ii) rule on the 0.864 size grid the plan's core outlines use; C17 used 4.32). vms_glue (E 5.88 on C19) is computed the same way but reported separately (C20 already spills E->W).
 2. New pins table: every face re-spread evenly over the new face span (pitch 0.048, ends 8.64, inset 0.019), pins
    sorted along the face, same as apply_c19.py does for vms_glue. Face membership unchanged.
 3. Re-pack per partition type (type frame; every instance of a shared type follows): the grown rect is tried at origins
    on the 4.32 grid within +-MAXC um of its current origin; conflicts are pushed away (neighbour shifts on the 4.32 grid,
    cascading). Constraints: inside the type outline; no new overlap with type clock keepouts or with currently core-free
    die_ft_bands; core pair separation (Chebyshev gap = max(gx, gy); pairs overlapping today ignored): pairs < 34.56 apart
    keep >= min(current, hmin) where hmin = the smallest positive core gap in that type today (the halo in use); pairs
    >= 34.56 apart keep >= 34.56, and with STREETS=strict (default) FACING pairs (a street between them) keep their
    current width. A pins table is applied only if every instance of it (all types) re-packs; else it is unresolved and
    its cores keep their C19 outline (iterated to a fixed point). Cost = sum of moves + 30 um per moved neighbour. Moved cores carry their clock taps
    (taps named <inst> or <inst>.<pin>); grown cores' taps keep their offset to the core centre.
"""
import json, sys, math, collections, itertools, hashlib, os
from pathlib import Path
pd, od = Path(sys.argv[1]), Path(sys.argv[2])
assert od.resolve() != pd.resolve()
(od / "cores").mkdir(parents=True, exist_ok=True)
raw = json.load(open(pd / "die_plan.json")); T = raw["partition_types"]
GS = 0.864   # core sizes in the plan are multiples of 0.864 (= 18 pin pitches); origins move on the 4.32 grid
CAP, END, G, PITCH, OFF, INS, STREET = 5.5, 8.64, 4.32, 0.048, 0.024, 0.096, 34.56
MAXC, MAXMOVE, EPS = float(os.environ.get("MAXC", 129.6)), float(os.environ.get("MAXMOVE", 216.0)), 1e-6
def r4(v): return round(v, 4)
def lface(x, y, w, h): return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]
def load(f):
    ps = json.load(open(pd / f)); return ps.get("pins", ps) if isinstance(ps, dict) else ps
# ---------- 1. capacity + growth ----------
users = collections.defaultdict(list)
for tn, t in T.items():
    for c in t.get("hard_cores") or []:
        if c.get("pins_file"): users[c["pins_file"]].append((tn, c))
def dens(ps, w, h):
    cnt = collections.Counter(lface(p["x"], p["y"], w, h) for p in ps)
    return {F: round(cnt[F] / ((w if F in "NS" else h) - 2 * END), 3) for F in "NSEW"}, cnt
grow = {}
for f, us in sorted(users.items()):
    w, h = us[0][1]["outline_um"]; ps = load(f); d, cnt = dens(ps, w, h)
    over = [F for F in "NSEW" if d[F] > CAP + 1e-9]
    if not over: continue
    need_w = max([cnt[F] / CAP + 2 * END for F in "NS" if F in over] or [w])
    need_h = max([cnt[F] / CAP + 2 * END for F in "EW" if F in over] or [h])
    dw = max(0.0, math.ceil((need_w - w) / GS - 1e-9) * GS); dh = max(0.0, math.ceil((need_h - h) / GS - 1e-9) * GS)
    nw, nh = r4(w + dw), r4(h + dh)
    # re-spread
    by = {F: [] for F in "NSEW"}
    for p in ps: by[lface(p["x"], p["y"], w, h)].append(p)
    def spread(lst, key, L, fix):
        out, used, n = [], set(), len(lst)
        for i, p in enumerate(sorted(lst, key=key)):
            v = END + (L - 2 * END) * (i + 0.5) / n; k = round((v - OFF) / PITCH)
            while k in used: k += 1
            used.add(k); q = dict(p); q[fix[0]] = r4(OFF + k * PITCH); q[fix[1]] = fix[2]; out.append(q)
        return out
    newp = spread(by["S"], lambda p: p["x"], nw, ("x", "y", INS)) + spread(by["N"], lambda p: p["x"], nw, ("x", "y", r4(nh - INS))) \
        + spread(by["E"], lambda p: p["y"], nh, ("y", "x", r4(nw - INS))) + spread(by["W"], lambda p: p["y"], nh, ("y", "x", INS))
    assert len(newp) == len(ps)
    d2, _ = dens(newp, nw, nh)
    mod = us[0][1]["module"]
    nf = f"cores/{Path(f).stem}__c20f_{nw:g}x{nh:g}.json"   # unique per old table (one module can have several tables)
    grow[f] = dict(module=mod, old_outline=[w, h], new_outline=[nw, nh], dw=r4(dw), dh=r4(dh), over=over, dens_before=d,
                   dens_after=d2, new_pins_file=nf, insts=[f"{tn}/{c['inst']}" for tn, c in us], pins=newp,
                   area_growth=round(nw * nh / (w * h) - 1, 3))
# ---------- 3. re-pack ----------
def rect(c, o=None, s=None):
    x, y = o or c["origin_um"]; w, h = s or c["outline_um"]; return (x, y, x + w, y + h)
def sep(a, b): return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])
def facing(a, b): return (a[1] < b[3] - EPS and b[1] < a[3] - EPS) or (a[0] < b[2] - EPS and b[0] < a[2] - EPS)
PEN = 30.0
MODE = os.environ.get("STREETS", "strict")   # strict: facing gaps >= 34.56 keep their width; req: keep >= 34.56
def ovl(a, b): return a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS
VMS = "hfd_hgi_vms_glue_nw_t"
def keepouts(t):
    ks = [tuple(k) for k in (t.get("clock") or {}).get("keepouts_um") or []]
    W, H = t["outline_um"]; cores = [rect(c) for c in t.get("hard_cores") or []]
    for b in t.get("die_ft_bands") or []:
        a0, a1 = b["span_um"]; k = (0, a0, W, a1) if b["dir"] == "EW" else (a0, 0, a1, H)
        if not any(ovl(k, r) for r in cores): ks.append(k)
    return ks
def repack_type(tn, growths):
    """growths: inst -> (new w, new h). returns (ok, moves{inst: (old_origin,new_origin,old_size,new_size)}, msg)"""
    t = T[tn]; W, H = t["outline_um"]; K = keepouts(t)
    cores = {c["inst"]: c for c in t.get("hard_cores") or []}
    R0 = {i: rect(c) for i, c in cores.items()}
    req = {}; pos = [sep(R0[a], R0[b]) for a, b in itertools.combinations(R0, 2)]
    hmin = min([s for s in pos if s > EPS] or [G])     # smallest halo used in this type today
    for a, b in itertools.combinations(R0, 2):
        s = sep(R0[a], R0[b])
        if s < -EPS: continue
        if s >= STREET - EPS:
            req[frozenset((a, b))] = s if (MODE == "strict" and facing(R0[a], R0[b])) else STREET
        else: req[frozenset((a, b))] = min(max(s, 0.0), hmin)
    old_k = {i: [k for k in K if ovl(R0[i], k)] for i in R0}
    state = dict(R0)
    size = {i: (R0[i][2] - R0[i][0], R0[i][3] - R0[i][1]) for i in R0}
    for i, (nw, nh) in growths.items(): size[i] = (nw, nh)
    def legal_alone(i, r):
        if r[0] < -EPS or r[1] < -EPS or r[2] > W + EPS or r[3] > H + EPS: return False
        return not any(ovl(r, k) for k in K if k not in old_k[i])
    def conflicts(i, r, st):
        out = []
        for j, rj in st.items():
            if j == i: continue
            q = req.get(frozenset((i, j)))
            if q is None: continue
            if sep(r, rj) < q - EPS: out.append(j)
        return out
    def push(i, r, st, fixed, depth=0):
        """place i at r, push conflicting cores; returns new state or None"""
        st = dict(st); st[i] = r; queue = [i]; moved = set(fixed) | {i}; n = 0
        while queue:
            n += 1
            if n > 400: return None
            a = queue.pop(0); ra = st[a]
            for j in conflicts(a, ra, st):
                if j in fixed or (j in moved and j != a and j in growths and j not in queue and False): pass
                if j in fixed: return None
                q = req[frozenset((a, j))]; rj = st[j]
                opts = []
                for ax, sg in (("x", 1), ("x", -1), ("y", 1), ("y", -1)):
                    if ax == "x": d = (ra[2] + q - rj[0]) if sg > 0 else (ra[0] - q - rj[2])
                    else: d = (ra[3] + q - rj[1]) if sg > 0 else (ra[1] - q - rj[3])
                    d = math.ceil(abs(d) / G - 1e-9) * G * sg
                    nr = (rj[0] + d, rj[1], rj[2] + d, rj[3]) if ax == "x" else (rj[0], rj[1] + d, rj[2], rj[3] + d)
                    tot = abs(nr[0] - R0[j][0]) + abs(nr[1] - R0[j][1])
                    if tot > MAXMOVE or not legal_alone(j, nr): continue
                    opts.append((tot, len(conflicts(j, nr, st)), nr))
                if not opts: return None
                opts.sort(key=lambda o: o[0] + PEN * o[1]); st[j] = opts[0][2]; moved.add(j); queue.append(j)
        return st
    done = set(); failed = []
    for i in sorted(growths, key=lambda i: -(size[i][0] * size[i][1])):
        x0, y0 = R0[i][0], R0[i][1]; w, h = size[i]; best = None
        steps = int(MAXC / G)
        cands = sorted(((dx * G, dy * G) for dx in range(-steps, steps + 1) for dy in range(-steps, steps + 1)),
                       key=lambda d: abs(d[0]) + abs(d[1]))
        for dx, dy in cands:
            if best and abs(dx) + abs(dy) >= best[0][0]: break
            r = (r4(x0 + dx), r4(y0 + dy), r4(x0 + dx + w), r4(y0 + dy + h))
            if not legal_alone(i, r): continue
            st = push(i, r, state, done)
            if st is None: continue
            mv = [abs(st[j][0] - R0[j][0]) + abs(st[j][1] - R0[j][1]) for j in st if j != i and st[j] != R0[j]]
            cost = (sum(mv) + abs(dx) + abs(dy) + PEN * len(mv), max(mv + [abs(dx) + abs(dy)]))
            if best is None or cost < best[0]: best = (cost, st)
        if best is None:
            failed.append(i); size[i] = (R0[i][2] - R0[i][0], R0[i][3] - R0[i][1]); continue
        state = best[1]; done.add(i)
    moves = {}
    for i in state:
        if state[i] != R0[i] or (i in growths and i not in failed):
            moves[i] = dict(old_origin=[R0[i][0], R0[i][1]], new_origin=[r4(state[i][0]), r4(state[i][1])],
                            old_outline=[r4(R0[i][2] - R0[i][0]), r4(R0[i][3] - R0[i][1])],
                            new_outline=list(size[i]))
    shrunk = []
    for pr, q in req.items():
        a, b = tuple(pr); s0, s1 = sep(R0[a], R0[b]), sep(state[a], state[b])
        if s1 < s0 - EPS and s1 < 200 and facing(state[a], state[b]):
            shrunk.append(dict(pair=[a, b], before=round(s0, 2), after=round(s1, 2), street=s0 >= STREET - EPS))
    return failed, moves, dict(hmin=round(hmin, 3), shrunk=shrunk)
live = {f for f, g in grow.items() if g["module"] == VMS}   # C20f: vms_glue only (the 21 other tables stay REPACK-owned)
for it in range(10):
    by_type = collections.defaultdict(dict)
    for f in live:
        for tn, c in users[f]: by_type[tn][c["inst"]] = tuple(grow[f]["new_outline"])
    reports, failed_inst = {}, set()
    for tn, gs in sorted(by_type.items()):
        failed, moves, info = repack_type(tn, gs)
        failed_inst |= {(tn, i) for i in failed}
        reports[tn] = dict(grown=sorted(set(gs) - set(failed)), failed=failed, moved=sorted(set(moves) - set(gs)), moves=moves, **info)
    bad = {f for f in live if any((tn, c["inst"]) in failed_inst for tn, c in users[f])}
    print("iter", it, "live tables", len(live), "failed tables", len(bad), flush=True)
    if not bad: break
    live -= bad
tables_ok = {f: f in live for f, g in grow.items() if g["module"] == VMS}
unresolved = []
for f, ok in tables_ok.items():
    if not ok: unresolved.append(dict(table=f, module=grow[f]["module"], types=sorted({tn for tn, c in users[f]}), dens=grow[f]["dens_before"], grow=[grow[f]["dw"], grow[f]["dh"]]))
for tn, rp in sorted(reports.items()):
    mv = [m for i, m in rp["moves"].items() if i not in rp["grown"]]
    print(tn, "grown", len(rp["grown"]), "moved", len(mv), "max move", max([abs(m["new_origin"][0]-m["old_origin"][0])+abs(m["new_origin"][1]-m["old_origin"][1]) for m in rp["moves"].values()] or [0]), "hmin", rp["hmin"], "facing gaps shrunk", len(rp["shrunk"]), "streets shrunk", sum(1 for x in rp["shrunk"] if x["street"]))
delta = []
mod_of = {}
for tn in T:
    for c in T[tn].get("hard_cores") or []: mod_of[(tn, c["inst"])] = c
def taps_for(tn, inst): return [tp for tp in (T[tn].get("clock") or {}).get("taps") or [] if str(tp.get("name", "")).split(".")[0] == inst and tp.get("xy")]
for tn, rp in reports.items():
    for inst, m in rp["moves"].items():
        c = mod_of[(tn, inst)]; g = grow.get(c["pins_file"]) if inst in rp["grown"] else None
        ow, oh = m["old_outline"]; nw, nh = m["new_outline"]
        dcx = (m["new_origin"][0] + nw / 2) - (m["old_origin"][0] + ow / 2); dcy = (m["new_origin"][1] + nh / 2) - (m["old_origin"][1] + oh / 2)
        tm = [dict(name=tp["name"], old_xy=tp["xy"], new_xy=[r4(tp["xy"][0] + dcx), r4(tp["xy"][1] + dcy)]) for tp in taps_for(tn, inst)]
        e = dict(type=tn, inst=inst, module=c["module"], orient=c.get("orient", "R0"), old_origin=m["old_origin"], new_origin=m["new_origin"],
                 old_outline=m["old_outline"], new_outline=m["new_outline"], old_pins_file=c["pins_file"],
                 new_pins_file=(g["new_pins_file"] if g else c["pins_file"]), grown=bool(g), taps_moved=tm,
                 move_um=r4(abs(m["new_origin"][0] - m["old_origin"][0]) + abs(m["new_origin"][1] - m["old_origin"][1])))
        if g: e["clock_entry_local_shift_um"] = [r4(g["dw"] / 2), r4(g["dh"] / 2)]
        delta.append(e)
written = set()
for e in delta:
    if e["grown"] and e["new_pins_file"] not in written:
        g = next(v for v in grow.values() if v["new_pins_file"] == e["new_pins_file"])
        (od / g["new_pins_file"]).write_text(json.dumps(g["pins"])); written.add(e["new_pins_file"])
vms = {f: {k: v for k, v in g.items() if k != "pins"} for f, g in grow.items() if g["module"] == VMS}
src_sha = hashlib.sha256((pd / "die_plan.json").read_bytes()).hexdigest()[:12]
json.dump(dict(basis=str(pd / "die_plan.json"), basis_sha=src_sha, method=__doc__, entries=delta,
               unresolved_tables=unresolved, vms_glue_alt=vms), open(od / "c20_repack_delta.json", "w"), indent=1)
json.dump(dict(basis_sha=src_sha, growth={f: {k: v for k, v in g.items() if k != "pins"} for f, g in grow.items()},
               types=reports, tables_ok=tables_ok), open(od / "repack_report.json", "w"), indent=1)
print("tables grown", len(grow), "applicable", sum(tables_ok.values()), "unresolved", len(unresolved), "entries", len(delta))
