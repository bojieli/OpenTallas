#!/usr/bin/env python3
"""DIE-HBM-24/L7: hub S-face fix on VL3d (die-local plan delta; no shared tool changed).

Root cause (CHECKED, hubface.py on VL3d): L6 and L7 are both NW_hub->NW_b100 2484 b (one 4968-b as-built pair).
At 6 pins/um x 2 layers each needs a 414.1-um window; the hub|b100 shared edge is 734.4 um and already holds L6 (414.1)
+ 5 small lanes (L70/L91/L100/L123/L137), leaving one 225.3-um gap.  Both 2484-b lanes direct need 828 um > 734 edge,
so 'L7 before L6' (option a) only swaps which lane detours (same 3 G0 errors).  Option (b): L7 is split over parallel
windows into NW_b100: piece 0 direct hub|b100 (largest that fits the 225-um gap), the rest hub|spu1 -> spu1 E face
-> b100 (spu1 is the W neighbour of b100 under the hub; its hub-face gaps nearest b100 are 166.2 / 99.9 um).
The pieces form ONE latency group L7_word (Plan.lane_pads equalises cycles), like L12/L12s (C20f precedent).
NE mirror: L7m the same on NE_hub/NE_spu1/NE_b100 (pieces L7m, L7ms1, ...).

Also fixes the L203/L203m boundary-slot hop (527 um in NW_su31 / NE_su31): the event re-created the su31 slot with
even stations from its face point, ignoring the upstream b101 station 233 um before the face.  Generic: any slot of a
listed lane whose first/last station leaves an inter-partition hop > LIMIT (0.9 x reach, G0C reach rule) gets its
stations re-placed on its own route (same zroute), first station within LIMIT of the previous register, last within
LIMIT of the next one, evenly between, snapped to the 4.32 lattice, macro-free (Builder.macro_hits); count raised
only if needed.

usage: l7fix.py TOOLS IN_PLAN_DIR OUT_DIR [--lanes L7,L7m] [--hopfix L203,L203m]"""
import sys, json, os, copy, math, argparse, hashlib
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("tools"); ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--hopfix", default="L203,L203m")
ap.add_argument("--limit", type=float, default=None, help="hop limit um (default 0.9 x Builder.reach)")
a = ap.parse_args()
sys.path.insert(0, a.tools)
import schema as S
import lane_add as LA
import check as C

plan_dir, out = Path(a.plan), Path(a.out)
raw = json.loads((plan_dir / "die_plan.json").read_text())
base_sha = hashlib.sha256((plan_dir / "die_plan.json").read_bytes()).hexdigest()[:12]
T = raw["partition_types"]
pt = {p["name"]: p["type"] for p in raw["partitions"]}
rep = dict(schema="die_hbm_24.l7fix.v1", base=str(plan_dir), base_sha=base_sha, removed={}, pieces={}, hopfix=[])
OPP = LA.OPP


def drop_lane(lid):
    P = S.Plan(raw)
    ln = P.lanes[lid]
    old = dict(cycles=raw["latency"]["lanes"].get(lid, {}).get("cycles"), ports=list(ln["ports"]))
    for q in ln["ports"]:
        pr = P.ports[q]
        for side in ("src", "dst"):
            part, bus = pr[side]["part"], pr[side]["bus"]
            if part not in pt:
                continue
            tn = pt[part]
            nb = len(T[tn].get("buses", []))
            T[tn]["buses"] = [b for b in T[tn].get("buses", []) if b["name"] != bus]
            stem = bus[:-2]
            ns = len(T[tn].get("ft_slots", []))
            T[tn]["ft_slots"] = [s for s in T[tn].get("ft_slots", []) if s["name"] != stem]
            old.setdefault("decl", []).append([tn, bus, nb - len(T[tn].get("buses", [])), ns - len(T[tn].get("ft_slots", []))])
    ids = set(ln["ports"])
    raw["ports"] = [p for p in raw["ports"] if p["id"] not in ids]
    raw["lanes"] = [l for l in raw["lanes"] if l["id"] != lid]
    raw["latency"]["lanes"].pop(lid, None)
    rep["removed"][lid] = old


def cap(B, u, v, prefer=None, hi=2484):
    """largest width alloc(u, v) can place now (dry run)."""
    lo, best = 1, 0
    while lo <= hi:
        m = (lo + hi) // 2
        got = B.alloc(u, v, m, prefer=prefer)
        if got:
            df, win, _ = got
            B.taken[(u, df)].remove(tuple(win)); B.taken[(v, OPP[df])].remove(tuple(win))
            best, lo = m, m + 1
        else:
            hi = m - 1
    return best


def build_split(B, side, bits, base_id):
    hub, b100, spu1 = f"{side}_hub", f"{side}_b100", f"{side}_spu1"
    pieces, left = [], bits
    e_sb = LA.shared_edge(B.P, spu1, b100)          # vertical edge spu1|b100 (E face of spu1)
    top_pref = e_sb[2] - 60.0                        # spu1|b100 window near the hub (top), short L in spu1
    # hub|spu1 prefer the end next to b100
    e_hs = LA.shared_edge(B.P, hub, spu1)
    near_b100 = e_hs[2] if B.P.rect(b100)[0] >= B.P.rect(spu1)[2] - 1 else e_hs[1]
    k = 0
    while left > 0:
        if k == 0:
            chain, w = [hub, b100], min(left, cap(B, hub, b100))
        else:
            w = min(left, cap(B, hub, spu1, prefer=near_b100), cap(B, spu1, b100, prefer=top_pref))
            chain = [hub, spu1, b100]
        if w <= 0:
            raise SystemExit(f"{side}: no window left for {left} b of {base_id} after {k} pieces")
        lid = base_id if k == 0 else f"{base_id}s{k}"
        B.new_id = (lambda lid_: (lambda a_, b_, part=0: lid_))(lid)
        orig_alloc = B.alloc
        if k > 0:
            def alloc2(u, v, width, prefer=None, _o=orig_alloc):
                if (u, v) == (hub, spu1):
                    prefer = near_b100
                elif (u, v) == (spu1, b100):
                    prefer = top_pref
                return _o(u, v, width, prefer=prefer)
            B.alloc = alloc2
        r = B.build_one(hub, b100, w, chain, "adj" if k == 0 else "path", None, record=False)
        B.alloc = orig_alloc
        if r is None:
            raise SystemExit(f"{side} piece {k} ({w} b, chain {chain}) failed: {B._why}")
        pieces.append(dict(lane=lid, bits=w, chain=chain, cycles=r["cycles"], stations=r["stations"],
                           windows=r["windows"], crossings=r["crossings"]))
        left -= w; k += 1
    return pieces


# ---- 1. L7 / L7m split
for side, lid in (("NW", "L7"), ("NE", "L7m")):
    drop_lane(lid)
B = LA.Builder(raw, near_um=1e9, max_hops=4, require_cycle_match=False)
B.shared = set()
for side, lid in (("NW", "L7"), ("NE", "L7m")):
    pcs = build_split(B, side, 2484, lid)
    rep["pieces"][lid] = pcs
    raw = B.raw
    gname = "L7_word" if side == "NW" else "L7m_word"
    raw.setdefault("latency_groups", []).append(dict(
        name=gname, kind="bus", lanes=[p["lane"] for p in pcs], source=f"{side}_hub.{lid}_o",
        note=f"DIE-HBM-24 L7 hub-S-face fix: one as-built {side}_hub->{side}_b100 bus (2484 b) over {len(pcs)} lanes "
             f"(direct hub|b100 + hub|spu1->b100), same cycle"))
    for p in pcs:
        for l in raw["lanes"]:
            if l["id"] == p["lane"]:
                l["note"] = (f"{side}_hub->{side}_b100 data | DIE-HBM-24 L7 split piece {p['bits']} b of {lid} "
                             f"({'direct' if len(p['chain']) == 2 else 'via ' + side + '_spu1'}); group {gname}")
T = raw["partition_types"]

# ---- 2. boundary-slot hop fix
P = S.Plan(raw)
LIM = a.limit or 0.9 * B.reach
import station_resite as SR
G = SR.G


def lane_regs(P, lid):
    """[(part or None, slotname or None, [die regs])] in order, with the bus face points at the ends."""
    ln = P.lanes[lid]
    hops = [P.ports[q] for q in ln["ports"]]
    out = []
    g0 = P.port_geom_from(hops[0], "src")
    out.append((None, None, [LA.Builder.face_pt(P, hops[0]["src"]["part"], g0[0], g0[1])]))
    for part, sl, _, _ in P.lane_crossings(lid):
        if sl:
            d = P.slot(part, sl)
            out.append((part, sl, [P.to_die(part, tuple(r)) for r in d.get("regs_um", [])]))
    gl = P.port_geom_from(hops[-1], "src")
    out.append((None, None, [LA.Builder.face_pt(P, hops[-1]["dst"]["part"], OPP[gl[0]], gl[1])]))
    return out


def md(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


for lid in [x for x in a.hopfix.split(",") if x]:
    P = S.Plan(raw)
    B.P = P
    seq = lane_regs(P, lid)
    # downstream-first: a boundary hop is fixed in the slot the event re-created (later in the chain), so a kept
    # upstream slot is only touched if the downstream one cannot absorb the hop
    for i in sorted(range(1, len(seq) - 1), key=lambda j: -j):
        P = S.Plan(raw); B.P = P
        seq = lane_regs(P, lid)
        part, sl, regs = seq[i]
        prev_r = seq[i - 1][2][-1]
        next_r = seq[i + 1][2][0]
        if not regs:
            continue
        pts = [prev_r] + regs + [next_r]
        worst = max(md(p, q) for p, q in zip(pts, pts[1:]))
        if worst <= LIM + 1e-6:
            continue
        d = T[pt[part]]["ft_slots"]
        decl = [x for x in d if x["name"] == sl][0]
        # slot route (die frame) between its own face windows
        # derive die faces/points from the neighbouring ports of this lane
        ln = P.lanes[lid]
        hops = [P.ports[q] for q in ln["ports"]]
        hin = [h for h in hops if h["dst"]["part"] == part][0]
        hout = [h for h in hops if h["src"]["part"] == part][0]
        gi, go = P.port_geom_from(hin, "src"), P.port_geom_from(hout, "src")
        fin, fout = OPP[gi[0]], go[0]
        pa = LA.Builder.face_pt(P, part, fin, gi[1]); pb = LA.Builder.face_pt(P, part, fout, go[1])
        seg = C.zroute(pa, pb, fin, fout)
        L = C.plen(seg)
        dA, dB = md(prev_r, pa), md(pb, next_r)
        s_first, s_last = max(0.0, LIM - dA) * 0.97, L - max(0.0, LIM - dB) * 0.97
        solved = None
        for n in range(max(1, len(regs)), len(regs) + 6):
            if n == 1:
                cand = [0.5 * (s_first + s_last)] if s_last <= s_first + 1e-6 else None
                if cand is None:
                    continue
            else:
                s1 = min(s_first, L); sn = max(s_last, 0.0)
                if sn < s1:
                    sn = s1
                cand = [s1 + (sn - s1) * j / (n - 1) for j in range(n)]
            rr = []
            for s in cand:
                x, y = C.point_at(seg, s)
                # snap to lattice in TYPE frame, try small offsets off macros
                best = None
                for dx in (0, G, -G, 2 * G, -2 * G, 3 * G, -3 * G):
                    for dy in (0, G, -G, 2 * G, -2 * G):
                        tx, ty = P.to_type(part, (x, y))
                        tx = round(round(tx / G) * G + dx, 4); ty = round(round(ty / G) * G + dy, 4)
                        dp = P.to_die(part, (tx, ty))
                        if B.macro_hits(part, [dp]) == 0:
                            best = dp; break
                    if best:
                        break
                rr.append(best)
            if any(r is None for r in rr):
                continue
            pts2 = [prev_r] + rr + [next_r]
            w2 = max(md(p, q) for p, q in zip(pts2, pts2[1:]))
            if w2 <= LIM + 1e-6 and L / n <= B.smax + 1e-6:
                solved = (n, rr, w2)
                break
        if solved is None:
            rep["hopfix"].append(dict(lane=lid, part=part, slot=sl, worst=round(worst, 1), fixed=False))
            continue
        n, rr, w2 = solved
        decl["stations"] = n
        decl["regs_um"] = [[round(v, 4) for v in P.to_type(part, r)] for r in rr]
        rep["hopfix"].append(dict(lane=lid, part=part, slot=sl, type=pt[part], worst_old=round(worst, 1),
                                  worst_new=round(w2, 1), stations_old=len(regs), stations_new=n))
    P = S.Plan(raw)
    nat = P.lane_natural(lid)
    raw["latency"]["lanes"][lid] = dict(nat, natural=nat["cycles"], pad=0, param="LAT_" + lid.upper())

# ---- write
out.mkdir(parents=True, exist_ok=True)
for f in plan_dir.iterdir():
    dst = out / f.name
    if f.name in ("die_plan.json", "replan_report.json") or dst.exists():
        continue
    try:
        os.link(f, dst) if f.is_file() else os.symlink(f.resolve(), dst)
    except OSError:
        pass
raw["note"] = raw.get("note", "") + " | DIE-HBM-24 l7fix: L7/L7m split hub|b100 + hub|spu1->b100 (group L7_word), L203 boundary hop re-site"
txt = json.dumps(raw, indent=1)
(out / "die_plan.json").write_text(txt)
rep["out_sha"] = hashlib.sha256(txt.encode()).hexdigest()[:12]
rep["limit_um"] = round(LIM, 2)
(out / "l7fix_report.json").write_text(json.dumps(rep, indent=1, default=str))
print(json.dumps(dict(out_sha=rep["out_sha"], pieces={k: [(p["lane"], p["bits"], p["cycles"]) for p in v] for k, v in rep["pieces"].items()},
                      hopfix=rep["hopfix"]), default=str))
