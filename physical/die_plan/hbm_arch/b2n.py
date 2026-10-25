#!/usr/bin/env python3
"""B2n = B2m + OWNER DECISION 12 (2026-10-24 21:31): partition feedthroughs on <= M7 with registered stations every
<= 405 um; M8/M9 reserved for the die clock spine, die reset and PG.  Derived deterministically from B2m (B2m stays):

    python3 physical/die_plan/hbm_arch/b2n.py [--src B2m] [--out B2n]

  1. layers   every type face drops its M8/M9 third pin layer (face_layers -> E/W [M6, M4], N/S [M7, M5]); every port
              drops M8/M9; die layer_budget.die_use loses ft_reserved (M8/M9 = clock spine / reset / PG only).
  2. windows  ports re-windowed for 2 pin layers: each port's window grows to width / PIN_DENS um (<= the 6 pins/um
              face budget with PG-band slack), then every face line is re-packed in one pass (isotonic least-squares
              shift, order kept, die-IO ports fixed, each port inside both abutting faces).  Mirror pairs stay mirror
              images (the packing is mirror-equivariant), so one pin table per type still holds.
  3. reach    die reach_um and budgets.ft_station_max_um = 405 (owner reach405; repeaters inside a hop as before).
  4. stations every ft slot's stations are re-derived on its route (type frame) with hops <= HOP, sited off the hard
              cores (cores_b2.RelayRouter / free_point: macro-free relay channels); internal_stations[] (R3-INTERNAL)
              re-derived the same way, plus new entries for every core link now over the 405-um limit.
  5. latency  plan latency table recomputed from the new stations (schema.Plan.lane_latency).
Reset stays as in B2m until lane RESET lands the neighbour-wavefront mode (decision 13); the clock H-tree (M8/M9) is
re-derived on the moved partition rects (b2m.clock: same symmetric binary H-tree on M8/M9).
"""
import argparse
import json
import math
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
from cores_b2 import RelayRouter, free_point  # noqa: E402

SIDECARS = ["census_map.json", "core_conns.json", "cores_b2.json", "hbm_rows.json", "cores", "inputs"]
DIE_ONLY = {"M8", "M9"}
REACH = 405.0
HOP = 360.0          # station spacing target (check: lane hop <= 0.9 x reach 405 = 364.5)
PIN_DENS = 5.6       # pins / um per port window on 2 layers (budget 6 / um, PG-band and rounding slack)
GAP = 0.48           # um between packed windows
SNAP = 0.008         # window ends on a 0.008-um grid (divides the 8.64 lattice: mirror images stay exact)
MIN_WIN = 8.64       # smallest window: one partition PG period on every pin layer (a 1-2 bit port needs a free track)
# 2-layer faces that cannot carry their abutting traffic: (grown type, shrunk neighbour type, um moved, reason).  The
# grown type gains the strip on its type-frame W face, so all its contents / taps / cores keep their DIE positions.
BOUNDARY_MOVES = [("q_su10", "q_spu0", 216.0,
                   "hub<->su10 N face carries 2998+1719+1615+514+514+268 b = 1363 um at 5.6 pins/um on M7/M5 vs "
                   "1166 um of hub overlap; spu0 (soft, no cores) gives 216 um (its hub face needs 1087 of 2290 um)"),
                  ("q_su30", "q_spu1", 216.0, "hub<->su30 S face: same traffic as su10 (mirror in y); spu1 soft")]


def snap(v):
    return round(round(v / SNAP) * SNAP, 4)


def move_boundaries(plan, log):
    parts = plan["partitions"]
    T = plan["partition_types"]
    for grow, shrink, d, why in BOUNDARY_MOVES:
        tg, ts = T[grow], T[shrink]
        assert not ts.get("hard_cores"), f"{shrink} has hard cores: shrinking it needs a re-place"
        tg["outline_um"][0] = round(tg["outline_um"][0] + d, 4)
        ts["outline_um"][0] = round(ts["outline_um"][0] - d, 4)

        def sh(xy):
            xy[0] = round(xy[0] + d, 4)
        for hc in tg.get("hard_cores", []):
            sh(hc["origin_um"])
        for c in tg.get("contents", []):
            if "origin_um" in c:
                sh(c["origin_um"])
        for k in ("clock", "reset"):
            if "tap_um" in tg.get(k, {}):
                sh(tg[k]["tap_um"])
        for tp in tg.get("clock", {}).get("taps", []):
            if "xy" in tp:
                sh(tp["xy"])
        for e in tg.get("internal_stations", []):
            sh(e["from_um"]); sh(e["to_um"])
            for r in e["regs_um"]:
                sh(r)
        for sl in tg.get("ft_slots", []):
            for r in sl.get("regs_um", []):
                sh(r)
            sl.pop("bit_sites_um", None)
        for k in ("clock", "reset"):
            if "tap_um" in ts.get(k, {}):
                ts[k]["tap_um"][0] = round(min(ts[k]["tap_um"][0], ts["outline_um"][0] / 2), 4)
        for p in parts:
            if p["type"] == grow and p.get("orient", "R0") in ("R0", "MX"):
                p["origin_um"][0] = round(p["origin_um"][0] - d, 4)
            if p["type"] == shrink and p.get("orient", "R0") in ("MY", "R180"):
                p["origin_um"][0] = round(p["origin_um"][0] + d, 4)
        log.append(f"boundary {grow} +{d:g} / {shrink} -{d:g} um ({why})")


def drop_die_layers(plan, log):
    n = 0
    for t in plan["partition_types"].values():
        for f, ls in list(t.get("face_layers", {}).items()):
            t["face_layers"][f] = [x for x in ls if x not in DIE_ONLY]
    for p in plan["ports"]:
        if any(x in DIE_ONLY for x in p.get("layers", [])):
            p["layers"] = [x for x in p["layers"] if x not in DIE_ONLY]
            n += 1
    lb = plan["die"]["layer_budget"]
    lb["die_use"] = [u for u in lb.get("die_use", []) if u != "ft_reserved"] + ["reset"]
    plan["die"]["reach_um"] = REACH
    plan["budgets"]["ft_station_max_um"] = REACH
    log.append(f"decision 12: {n} ports drop M8/M9 (2 pin layers), reach / ft_station_max 405")


def _pava(items):
    """items: [(desired_start, length, lo, hi)] in order; lo/hi bound the START.  Least-squares shift keeping order and
    GAP between windows; returns starts.  Pool-adjacent-violators over blocks, each block clipped to its bounds."""
    blocks = []      # [sum_desired_offsetted, n, members, lo, hi, offsets]
    for i, (d, L, lo, hi) in enumerate(items):
        blocks.append(dict(m=[i], off=[0.0], s=d, n=1, lo=lo, hi=hi, len=L))
        while True:
            b = blocks[-1]
            pos = min(max(b["s"] / b["n"], b["lo"]), b["hi"])
            b["pos"] = pos
            if len(blocks) < 2:
                break
            a = blocks[-2]
            if a["pos"] + a["len"] + GAP <= pos + 1e-9:
                break
            # merge b into a: b's members sit after a's
            sh = a["len"] + GAP
            a["m"] += b["m"]
            a["off"] += [o + sh for o in b["off"]]
            a["s"] += b["s"] - sh * b["n"]
            a["n"] += b["n"]
            a["lo"] = max(a["lo"], b["lo"] - sh)
            a["hi"] = min(a["hi"], b["hi"] - sh)
            a["len"] += GAP + b["len"]
            blocks.pop()
            a["pos"] = min(max(a["s"] / a["n"], a["lo"]), a["hi"])
            blocks[-1] = a
    out = [None] * len(items)
    bad = []
    for b in blocks:
        if b["lo"] > b["hi"] + 1e-6:
            bad.append(b["m"])
        for i, o in zip(b["m"], b["off"]):
            out[i] = b["pos"] + o
    return out, bad


def rewindow(plan, log, fixed_ids=frozenset()):
    P = S.Plan(plan)
    ports = {p["id"]: p for p in plan["ports"]}
    groups = defaultdict(list)
    for pid, p in ports.items():
        part = P.face_part(pid)
        line, a, b = CK.face_line(P.rect(part), p["face"])
        fixed = S.DIE_PART in (p["src"]["part"], p["dst"]["part"]) or pid in fixed_ids
        if not fixed:
            _, a2, b2 = CK.face_line(P.rect(p["dst"]["part"]), S.OPP[p["face"]])
            a, b = max(a, a2), min(b, b2)
        axis = "H" if p["face"] in "NS" else "V"
        groups[(axis, round(line, 3))].append((pid, a, b, fixed))
    grown = moved = 0
    worst = []
    for key, mem in groups.items():
        rows = []
        for pid, a, b, fixed in mem:
            lo, hi = sorted(ports[pid]["window_um"])
            need = max(S.port_pins_count(ports[pid]) / PIN_DENS + 0.5, MIN_WIN)
            L = (hi - lo) if fixed else max(hi - lo, need)
            c = 0.5 * (lo + hi)
            d = c - L / 2
            if fixed:
                blo = bhi = lo
            else:
                blo, bhi = a + 0.5, b - 0.5 - L
            rows.append((c, pid, d, L, blo, bhi, lo, hi))
        rows.sort()
        starts, bad = _pava([(d, L, blo, bhi) for _, _, d, L, blo, bhi, _, _ in rows])
        for idx in bad:
            worst.append([rows[i][1] for i in idx][:4])
        for (c, pid, d, L, blo, bhi, lo, hi), s0 in zip(rows, starts):
            nw = [snap(s0), snap(s0 + L)] if not fixed else [lo, hi]
            if abs(nw[0] - lo) > 1e-4 or abs(nw[1] - hi) > 1e-4:
                moved += 1
                grown += (L > hi - lo + 1e-6)
                ports[pid]["window_um"] = nw
    log.append(f"re-windowed {moved} ports ({grown} grown to <= {PIN_DENS:g} pins/um on 2 layers); "
               f"{len(worst)} infeasible face groups")
    return worst


def enforce_mirror(plan, log):
    """replicated types (2 instances): the second instance's ports take the first instance's windows through the type
    frame, so both carry ONE pin table (check: 'a replicated type must have identical pins')."""
    P = S.Plan(plan)
    ports = {p["id"]: p for p in plan["ports"]}
    end = {}
    for pid, p in ports.items():
        for sd in ("src", "dst"):
            end[(p[sd]["part"], p[sd]["bus"], sd)] = pid
    insts = defaultdict(list)
    for n, p in P.parts.items():
        insts[p["type"]].append(n)
    touched, n = set(), 0
    pairs = []
    for tn, ps in insts.items():
        if len(ps) != 2:
            continue
        A, B = sorted(ps, key=lambda q: (P.orient(q) != "R0", P.parts[q]["origin_um"][0]))
        for (part, bus, sd), pid in list(end.items()):
            if part != A:
                continue
            qid = end.get((B, bus, sd))
            if not qid:
                continue
            p, q = ports[pid], ports[qid]
            if p["face"] in "NS":
                pts = [(c, 0.0) for c in p["window_um"]]
                nw = sorted(P.to_die(B, P.to_type(A, xy))[0] for xy in pts)
            else:
                pts = [(0.0, c) for c in p["window_um"]]
                nw = sorted(P.to_die(B, P.to_type(A, xy))[1] for xy in pts)
            nw = [snap(v) for v in nw]
            if nw != sorted(q["window_um"]):
                q["window_um"] = nw
                n += 1
            touched |= {pid, qid}
            pairs.append((A, B, pid, qid))
    log.append(f"mirror: {n} second-instance port windows set from the first instance (type frame)")
    return touched, pairs


def _tab(P, part, pid):
    ax = 0 if P.ports[pid]["face"] in "NS" else 1
    out = []
    for bit, ln, c in P.port_pins(pid):
        xy = (c, 0.0) if ax == 0 else (0.0, c)
        out.append((bit, ln, round(P.to_type(part, xy)[ax], 4)))
    return sorted(out)


def fix_mirror_pins(plan, pairs, log):
    """the nearest-track pick is mirror-equivariant only for an odd usable-track count when the pin count is odd
    (schema.spread): nudge the first instance's window end by 0.008-um steps (mirrored on the second) until both
    instances get one pin table."""
    ports = {p["id"]: p for p in plan["ports"]}
    fixed = bad = 0
    for A, B, pid, qid in pairs:
        P = S.Plan(plan)
        if _tab(P, A, pid) == _tab(P, B, qid):
            continue
        p, q = ports[pid], ports[qid]
        lo0, hi0 = sorted(p["window_um"])
        ok = False
        for k in list(range(1, 40)) + list(range(-1, -40, -1)):
            p["window_um"] = [lo0, snap(hi0 + k * SNAP)]
            ax = 0 if p["face"] in "NS" else 1
            pts = [((c, 0.0) if ax == 0 else (0.0, c)) for c in p["window_um"]]
            q["window_um"] = sorted(snap(P.to_die(B, P.to_type(A, xy))[ax]) for xy in pts)
            P = S.Plan(plan)
            try:
                if _tab(P, A, pid) == _tab(P, B, qid):
                    ok = True
                    break
            except ValueError:
                continue
        if ok:
            fixed += 1
        else:
            bad += 1
            p["window_um"] = [lo0, hi0]
    log.append(f"mirror pin tables: {fixed} port pairs nudged to one table, {bad} unresolved")


def _type_routes(P):
    """{(type, slot): type-frame route polyline} from the first lane crossing of each slot."""
    out = {}
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            if not slot:
                continue
            key = (P.parts[part]["type"], slot)
            if key in out:
                continue
            s = P.slot(part, slot) or {}
            seg = CK.zroute(P.port_point(a), P.port_point(b), P.die_face(part, s.get("in_face", "W")),
                            P.die_face(part, s.get("out_face", "E")))
            out[key] = [P.to_type(part, q) for q in seg]
    return out


def _boxes(t):
    bx = []
    for hc in t.get("hard_cores", []):
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        bx.append((hc["origin_um"][0] + dx, hc["origin_um"][1] + dy, hc["outline_um"][0], hc["outline_um"][1]))
    return bx


def _chain(router, free, a, b):
    """stations from a (incl. a near-face site) to b with every hop <= HOP; off the cores."""
    first = free(a)
    regs = [first] + router(first, b)
    return regs


def restation(plan, log):
    P = S.Plan(plan)
    routes = _type_routes(P)
    tot0 = tot1 = 0
    ist0 = ist1 = added = 0
    fails = []
    for tn, t in plan["partition_types"].items():
        w, h = t["outline_um"]
        boxes = _boxes(t)
        router = RelayRouter(boxes, w, h, HOP)
        router_reach = RelayRouter(boxes, w, h, REACH - 1.0)
        free = (lambda p, boxes=boxes, w=w, h=h: free_point(p, boxes, w, h))
        for sl in t.get("ft_slots", []):
            seg = routes.get((tn, sl["name"]))
            if not seg:
                continue
            tot0 += int(sl.get("stations", 1))
            try:
                regs = _chain(router, free, seg[0], seg[-1])
            except ValueError as e:
                fails.append(f"{tn}.{sl['name']}: {e}")
                continue
            # spacing rule (check R3): route length / stations <= 405
            L = CK.plen(seg)
            while L / len(regs) > REACH:
                regs.append(regs[-1])
            sl["stations"] = len(regs)
            sl["regs_um"] = [[round(v, 3) for v in p] for p in regs]
            sl.pop("bit_sites_um", None)
            tot1 += len(regs)
        ist = t.get("internal_stations", [])
        for e in ist:
            ist0 += len(e["regs_um"])
            if CK._hops_ok(e["from_um"], e["regs_um"], e["to_um"], REACH):
                ist1 += len(e["regs_um"])
                continue
            a_, b_ = tuple(e["from_um"]), tuple(e["to_um"])
            land = free(b_)            # the station next to the capture pin, off the core (keeps the pin face)
            regs = None
            for r_ in (router, router_reach):
                try:
                    regs = r_(a_, land)
                    break
                except ValueError as ex:
                    err = ex
            if regs is None:
                fails.append(f"{tn} internal {e.get('conn')}: {err}")
                continue
            if not regs or abs(regs[-1][0] - land[0]) + abs(regs[-1][1] - land[1]) > 1.0:
                regs = list(regs) + [land]
            if not CK._hops_ok(a_, regs, b_, REACH):
                fails.append(f"{tn} internal {e.get('conn')}: hop > {REACH:g} um after re-stationing")
            e["regs_um"] = [[round(v, 3) for v in p] for p in regs]
            e["note"] = (e.get("note", "").split(" | B2n")[0] + f" | B2n decision 12: {len(regs)} station(s), "
                         f"hops <= {REACH:g} um")
            ist1 += len(regs)
    # new internal links now over 405 um (were <= 750/900): same enumeration as check_completeness
    P = S.Plan(plan)
    for tn, t in plan["partition_types"].items():
        if t.get("hard"):
            continue
        w, h = t["outline_um"]
        boxes = _boxes(t)
        bxs = {}
        for hc in t.get("hard_cores", []):
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
            bxs[hc["inst"]] = (x0, y0, x0 + hc["outline_um"][0], y0 + hc["outline_um"][1])
        for c in t.get("contents", []):
            if c["inst"] not in bxs and "origin_um" in c and "outline_um" in c:
                x0, y0 = c["origin_um"]
                bxs[c["inst"]] = (x0, y0, x0 + c["outline_um"][0], y0 + c["outline_um"][1])
        if not bxs:
            continue
        router = RelayRouter(boxes, w, h, HOP)
        free = (lambda p, boxes=boxes, w=w, h=h: free_point(p, boxes, w, h))
        ist = t.setdefault("internal_stations", [])
        conns = {e.get("conn") for e in ist if e.get("conn")}

        def covered(key, a, b_box):
            if key in conns:
                return True
            return any(abs(e["from_um"][0] - a[0]) + abs(e["from_um"][1] - a[1]) <= 50.0
                       and CK._box_dist(e["to_um"], b_box) <= 50.0 for e in ist)

        def near(a, box):
            return (min(max(a[0], box[0]), box[2]), min(max(a[1], box[1]), box[3]))

        bt = None
        for b in t.get("buses", []):
            lf = b.get("leaf") or ""
            li = lf.split(".")[0]
            cand = [ci for ci in bxs if ci == li or ci.startswith(li + "_")] if li else []
            if not cand:
                continue
            if bt is None:
                bt = CK._bus_targets(P, tn)
            if b["name"] not in bt:
                continue
            a = bt[b["name"]][1]
            ci = min(cand, key=lambda c_: CK._box_dist(a, bxs[c_]))
            d = CK._box_dist(a, bxs[ci])
            if d > REACH and not covered(f"bus:{b['name']}", a, bxs[cand[0]]) and not covered(lf, a, bxs[cand[0]]):
                tgt = near(a, bxs[ci])
                try:
                    regs = router(a, tgt) or [free(a)]
                except ValueError as ex:
                    fails.append(f"{tn} bus {b['name']}: {ex}")
                    continue
                if not CK._hops_ok(a, regs, tgt, REACH):
                    regs = regs + [free(tgt)]
                ist.append(dict(conn=f"bus:{b['name']}", from_um=[round(a[0], 3), round(a[1], 3)],
                                to_um=[round(tgt[0], 3), round(tgt[1], 3)],
                                regs_um=[[round(v, 3) for v in p] for p in regs], bits=int(b.get("width", 1)),
                                launch=f"face bus {b['name']}", capture=lf,
                                note=f"B2n decision 12: face window -> {lf} {d:.0f} um, {len(regs)} station(s), "
                                     f"hops <= {REACH:g} um"))
                conns.add(f"bus:{b['name']}")
                added += 1
        nets = defaultdict(set)
        for c in t.get("contents", []):
            for lp, v in c.get("bind", {}).items():
                if v.startswith("net:"):
                    nets[v[4:]].add(c["inst"])
        for nm, insts in nets.items():
            ins = sorted(i for i in insts if i in bxs)
            for i, x in enumerate(ins):
                for y in ins[i + 1:]:
                    bx, by = bxs[x], bxs[y]
                    d = max(bx[0] - by[2], by[0] - bx[2], 0) + max(bx[1] - by[3], by[1] - bx[3], 0)
                    if d <= REACH or f"{x}|{y}" in conns or f"{y}|{x}" in conns:
                        continue
                    cy = ((by[0] + by[2]) / 2, (by[1] + by[3]) / 2)
                    a = near(cy, bx)
                    tgt = near(a, by)
                    try:
                        regs = router(a, tgt) or [free(a)]
                    except ValueError as ex:
                        fails.append(f"{tn} net {nm} {x}|{y}: {ex}")
                        continue
                    if not CK._hops_ok(a, regs, tgt, REACH):
                        regs = regs + [free(tgt)]
                    ist.append(dict(conn=f"{x}|{y}", from_um=[round(a[0], 3), round(a[1], 3)],
                                    to_um=[round(tgt[0], 3), round(tgt[1], 3)],
                                    regs_um=[[round(v, 3) for v in p] for p in regs], bits=1, launch=x, capture=y,
                                    note=f"B2n decision 12: net {nm} {d:.0f} um core link, {len(regs)} station(s), "
                                         f"hops <= {REACH:g} um"))
                    conns.add(f"{x}|{y}")
                    added += 1
        if not ist:
            t.pop("internal_stations", None)
    log.append(f"ft slot stations {tot0} -> {tot1}; internal stations {ist0} -> {ist1} (+{added} new links over "
               f"{REACH:g} um); {len(fails)} unroutable")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(HERE / "B2m"))
    ap.add_argument("--out", default=str(HERE / "B2n"))
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in SIDECARS:
        s, d = src / f, out / f
        if s.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d)
        elif s.exists():
            shutil.copy2(s, d)
    plan = json.loads((src / "die_plan.json").read_text())
    log = []
    plan["die"]["name"] = "hbm_arch_B2n"
    plan["die"]["label"] = plan["die"]["label"].replace("B2m = ", "B2n = B2m + decision 12 (ft <= M7, 405-um "
                                                        "stations); B2m = ")
    drop_die_layers(plan, log)
    move_boundaries(plan, log)
    rewindow(plan, log)
    touched, pairs = enforce_mirror(plan, log)
    worst = rewindow(plan, log, fixed_ids=touched)
    fix_mirror_pins(plan, pairs, log)
    fails = restation(plan, log)
    import b2m as B2M   # noqa: E402  (H-tree + tap assignment re-derived: su10/su30 / spu0/spu1 rects moved)
    B2M.clock(plan, out, log)
    P = S.Plan(plan)
    plan["latency"]["lanes"] = {lid: P.lane_latency(lid) for lid in P.lanes}
    c0 = json.loads((src / "die_plan.json").read_text())["latency"]["lanes"]
    dc = {lid: plan["latency"]["lanes"][lid]["cycles"] - c0[lid]["cycles"] for lid in c0 if lid in plan["latency"]["lanes"]}
    up = [v for v in dc.values() if v > 0]
    log.append(f"latency: {len(up)}/{len(dc)} lanes +cycles (max +{max(up) if up else 0}, sum +{sum(up)})")
    plan["note"] = plan.get("note", "") + " | B2n derived by physical/die_plan/hbm_arch/b2n.py: " + "; ".join(log)
    (out / "die_plan.json").write_text(json.dumps(plan, indent=0) + "\n")
    (out / "die_io.json").write_text((src / "die_io.json").read_text())
    (out / "b2n_report.json").write_text(json.dumps(dict(log=log, infeasible_faces=worst, unroutable=fails,
                                                         lane_cycle_delta={k: v for k, v in dc.items() if v}),
                                                    indent=1) + "\n")
    print("\n".join(log))
    for x in (worst[:5] + fails[:10]):
        print("  !", x)


if __name__ == "__main__":
    main()
