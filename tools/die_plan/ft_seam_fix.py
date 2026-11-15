#!/usr/bin/env python3
"""S81-LEAF-PLAN 11-14 (COORD, DIE-S81-92 B6c4 seam hops 454-540 um): seam-side companion of ft_reach_fix.

ft_reach_fix re-sites the S1 bit sites of a normal FT slot that sit too far from their input-face S0.  This tool takes
the other end: a lane hop (check.py check_hops / lane_pin_hops, through the mandatory slot pins) that starts at the
LAST station of a crossed slot and runs over the out pin and the partition seam to the next register (the next
partition's first station, or the lane's destination flop) and is longer than the reach.

For every such (type, slot) it first re-sites the last station toward the slot's out face: the station centre
(regs_um[k-1]) and its bit-site group (bit_sites_um[k-2]) move together by one offset along the line to the out window
point, at the smallest step that puts every hop of every lane crossing that type's slot (all partitions, all orients)
at <= LIMIT, keeps S0->S1 for k == 2, and lands every bit on a free legal row site (RowAllocator, the obstacles of
ft_nudge / ft_reach_fix).  When no step works and --add is given, it appends a station between the last one and the out
face instead (stations +1, regs_um / bit_sites_um +1 row, and stations / cycles / natural +1 on the latency row of every
lane that crosses the slot: COORD +1 ft register pre-approved).  Windows, pins, outlines and cores never change.

    ft_seam_fix.py PLAN OUT LEDGER [--add] [--limit UM] [--lane REGEX] [--dry]
Exit 0 when every seam hop it found is fixed; 1 otherwise (the ledger names the rest and why).
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import check as C  # noqa: E402

LIMIT = 400.0                       # 5 um under the 405 rule (cell centre vs pin model), as ft_reach_fix
MAX_ADD = 3
STEPS = tuple(round(0.05 * i, 2) for i in range(1, 20))     # fraction of the way to the out window point


def lane_labels(P, lid):
    """registers of lane_geometry order: ('src',), (part, slot, j), ('dst',)."""
    out = [("src",)]
    for part, slot, _, _ in P.lane_crossings(lid):
        k = int((P.slot(part, slot) or {}).get("stations", 1))
        out += [(part, slot, j) for j in range(k)]
    return out + [("dst",)]


def lane_hops(P, lid):
    pts, regs, xs = C.lane_geometry(P, lid)
    return C.lane_pin_hops(P, lid, regs)


def seam_hops(P, lim, lane_rx=None):
    """[(lane, hop_um, type, slot, part, kind)] for every hop > lim that leaves the last station of a crossed slot."""
    found = []
    for lid in P.lanes:
        if lane_rx and not re.search(lane_rx, lid):
            continue
        try:
            hops = lane_hops(P, lid)
        except Exception:        # lanes without crossings / geometry are not this tool's
            continue
        lab = lane_labels(P, lid)
        if len(hops) != len(lab) - 1:
            continue
        for i, h in enumerate(hops):
            if h <= lim + 1e-6:
                continue
            a, b = lab[i], lab[i + 1]
            if len(a) == 3:
                k = int(P.slot(a[0], a[1]).get("stations", 1))
                if a[2] == k - 1 and (len(b) == 1 or b[2] == 0):
                    found.append((lid, round(h, 1), P.parts[a[0]]["type"], a[1], a[0], "last->seam"))
    return found


def slot_lanes(P, tn, sn):
    """every lane crossing slot sn of a partition of type tn."""
    out = []
    for lid in P.lanes:
        for part, slot, _, _ in P.lane_crossings(lid):
            if slot == sn and P.parts[part]["type"] == tn:
                out.append(lid)
                break
    return out


def max_slot_hop(P, lids, tn, sn):
    """worst hop touching a station of (tn, sn) over lids, and worst hop overall (to check nothing else grows)."""
    worst_touch, worst_all = 0.0, 0.0
    for lid in lids:
        hops = lane_hops(P, lid); lab = lane_labels(P, lid)
        for i, h in enumerate(hops):
            worst_all = max(worst_all, h)
            for x in (lab[i], lab[i + 1]):
                if len(x) == 3 and x[1] == sn and P.parts[x[0]]["type"] == tn:
                    worst_touch = max(worst_touch, h)
    return worst_touch, worst_all


def out_point(P, tn, s):
    import route_supply as RS
    W, H = P.types[tn]["outline_um"]
    return np.array(RS.face_point(W, H, s.get("out_face", "E"), s.get("out_window_um")), dtype=float)


def allocator(t, skip_slot=None, skip_stage=None):
    from placement_obstacles import placement_boxes
    from tools.die_trial.legal_sites import RowAllocator
    from ft_nudge import KEEPOFF, CELL_DEFAULT, clock_points
    w, h = t["outline_um"]
    macro = list(placement_boxes(t).values())
    boxes = [(a - KEEPOFF, b - KEEPOFF, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in macro]
    hh = C.CLOCK_BUF_HALO_UM + 0.01
    boxes += [(q[0] - hh - CELL_DEFAULT[0], q[1] - hh - CELL_DEFAULT[1], q[0] + hh, q[1] + hh) for q in clock_points(t)]
    al = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL_DEFAULT,
                      column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
    for x in t["ft_slots"]:
        cw, ch = x.get("bit_site_cell_um", CELL_DEFAULT)
        for j, st in enumerate(x.get("bit_sites_um") or []):
            if x["name"] == skip_slot and j == skip_stage:
                continue
            for bx, by in st:
                al.reserve_rectangle((bx, by, bx + cw, by + ch))
    return al


def group_at(t, s, stage, delta, base=None):
    """bit sites of bit-site row `stage` moved by delta onto free legal sites (None if any bit has none within 20 um)."""
    from ft_nudge import CELL_DEFAULT
    cw, ch = s.get("bit_site_cell_um", CELL_DEFAULT)
    al = allocator(t, s["name"], stage if base is None else None)
    rows = s["bit_sites_um"][stage] if base is None else base
    new = []
    for bx, by in rows:
        c = np.array([bx + cw / 2, by + ch / 2]) + delta
        try:
            q = al.allocate(c, 1, max_radius_um=20.0)[0][0]
        except ValueError:
            return None
        new.append([round(float(q[0] - cw / 2), 6), round(float(q[1] - ch / 2), 6)])
    return new


def first_hop_ok(P, tn, s):
    from die_hop_scan import first_internal_hops
    return max((d for _, d in first_internal_hops(P, tn, s)), default=0.0) <= C.SIGNAL_REACH_UM if hasattr(C, "SIGNAL_REACH_UM") \
        else max((d for _, d in first_internal_hops(P, tn, s)), default=0.0) <= 405.0


def fix_slot(P, raw, tn, sn, lim, add, rec):
    t = raw["partition_types"][tn]
    s = next(x for x in t["ft_slots"] if x["name"] == sn)
    k = int(s.get("stations", 1)); lids = slot_lanes(P, tn, sn)
    before_touch, before_all = max_slot_hop(P, lids, tn, sn)
    rec.update(stations=k, lanes=len(lids), worst_before=round(before_touch, 1))
    tgt = out_point(P, tn, s)
    regs = s.get("regs_um")
    has_sites = bool(s.get("bit_sites_um")) and len(s["bit_sites_um"]) == k - 1
    if k >= 2 and regs and len(regs) == k:
        # slots without bit sites (centre-only stations): the station centre moves alone
        r0 = np.array(regs[-1], dtype=float); keep_r = list(regs[-1])
        keep_g = s["bit_sites_um"][-1] if has_sites else None
        for f in STEPS:
            q = r0 + (tgt - r0) * f
            regs[-1] = [round(float(q[0]), 4), round(float(q[1]), 4)]
            touch, allw = max_slot_hop(P, lids, tn, sn)
            if touch > lim + 1e-6 or (k == 2 and not first_hop_ok(P, tn, s)):
                continue
            if has_sites:
                g = group_at(t, s, k - 2, q - r0)
                if g is None:
                    rec.setdefault("no_sites_at", []).append(f)
                    continue
                s["bit_sites_um"][-1] = g
            if k == 2 and not first_hop_ok(P, tn, s):
                s["bit_sites_um"][-1] = keep_g
                continue
            rec.update(action="resite", step=f, moved_um=round(float(abs(q - r0).sum()), 1), worst_after=round(touch, 1))
            s["note"] = (s.get("note", "") + " | ft_seam_fix 11-14: last station re-sited %.1f um toward the out face"
                         % rec["moved_um"]).strip(" |")
            return True
        regs[-1] = keep_r
        if has_sites:
            s["bit_sites_um"][-1] = keep_g
    if not add:
        rec["why"] = "no re-site step clears the seam hop" if k >= 2 else "single-station slot (S0 only): needs --add"
        return False
    if not regs:
        # analytic slot (no regs_um: check.lane_geometry spaces the k stations evenly on the slot route): +n stations
        for n in range(1, MAX_ADD + 1):
            s["stations"] = k + n
            touch, _ = max_slot_hop(P, lids, tn, sn)
            if touch <= lim + 1e-6:
                for lid in lids:
                    r = raw["latency"]["lanes"][lid]
                    for fld in ("stations", "cycles", "natural"):
                        r[fld] = int(r[fld]) + n
                rec.update(action="add", stations=[k, k + n], worst_after=round(touch, 1), lane_rows=lids, analytic=True)
                s["note"] = (s.get("note", "") + " | ft_seam_fix 11-14: +%d evenly spaced station(s) (COORD +1 ft "
                             "register pre-approved)" % n).strip(" |")
                return True
        s["stations"] = k
        rec["why"] = "analytic slot: +%d stations do not clear the seam hop (the seam gap itself is long)" % MAX_ADD
        return False
    if len(regs) != k:
        rec["why"] = "regs_um rows != stations"
        return False
    # --add: new last station(s) between the old last one and the out face (up to MAX_ADD, +1 cycle each)
    keep = json.dumps(s, sort_keys=True); added = 0
    while added < MAX_ADD:
        kk = int(s["stations"]); r0 = np.array(regs[-1], dtype=float); placed = False
        for f in (0.5, 0.6, 0.4, 0.7, 0.3, 0.8):
            q = r0 + (tgt - r0) * f
            regs.append([round(float(q[0]), 4), round(float(q[1]), 4)])
            s["stations"] = kk + 1
            touch, _ = max_slot_hop(P, lids, tn, sn)
            if has_sites:
                g = group_at(t, s, None, q - r0, base=s["bit_sites_um"][-1])
                if g is None:
                    regs.pop(); s["stations"] = kk
                    continue
                s["bit_sites_um"].append(g)
            placed = True
            break
        if not placed:
            break
        added += 1
        if touch <= lim + 1e-6:
            for lid in lids:
                r = raw["latency"]["lanes"][lid]
                for fld in ("stations", "cycles", "natural"):
                    r[fld] = int(r[fld]) + added
            rec.update(action="add", stations=[k, k + added], worst_after=round(touch, 1), lane_rows=lids)
            s["note"] = (s.get("note", "") + " | ft_seam_fix 11-14: +%d station(s) at the out end (COORD +1 ft "
                         "register pre-approved)" % added).strip(" |")
            return True
    s.clear(); s.update(json.loads(keep))
    if not has_sites and k >= 2:
        # centre-only slot: re-space S1..S(k-1+n) evenly from S0 to the out face point (S0 stays), n = 0..MAX_ADD
        regs = s["regs_um"]; r0 = np.array(regs[0], dtype=float)
        d = tgt - r0; L1 = float(abs(d).sum())
        end = tgt - d * (4.32 / L1) if L1 > 4.32 else tgt          # last station one cell pitch inside the out face
        for n in range(0, MAX_ADD + 1):
            m = k + n
            s["regs_um"] = [list(regs[0])] + [[round(float(v), 4) for v in r0 + (end - r0) * (j / (m - 1))]
                                              for j in range(1, m)]
            s["stations"] = m
            touch, _ = max_slot_hop(P, lids, tn, sn)
            if touch <= lim + 1e-6:
                if n:
                    for lid in lids:
                        r = raw["latency"]["lanes"][lid]
                        for fld in ("stations", "cycles", "natural"):
                            r[fld] = int(r[fld]) + n
                rec.update(action="respace", stations=[k, m], worst_after=round(touch, 1), lane_rows=lids if n else [])
                s["note"] = (s.get("note", "") + " | ft_seam_fix 11-14: stations re-spaced S0 -> out face, +%d" % n
                             ).strip(" |")
                return True
        s.clear(); s.update(json.loads(keep))
    rec["why"] = "neither a re-site nor an added station clears the seam hop"
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("ledger")
    ap.add_argument("--add", action="store_true"); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=float, default=LIMIT); ap.add_argument("--lane")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text()); P = S.Plan(raw)
    found = seam_hops(P, a.limit, a.lane)
    by = defaultdict(list)
    for x in found:
        by[(x[2], x[3])].append(x)
    ledger = dict(found=[list(x) for x in found], slots=[])
    ok = True
    for (tn, sn), xs in sorted(by.items()):
        rec = dict(type=tn, slot=sn, lanes_over=[x[0] for x in xs], worst_hop=max(x[1] for x in xs))
        if not a.dry:
            ok &= fix_slot(P, raw, tn, sn, a.limit, a.add, rec)
        ledger["slots"].append(rec)
    if not a.dry:
        rest = seam_hops(P, a.limit, a.lane)
        ledger["after"] = [list(x) for x in rest]
        ok = ok and not rest
        raw["note"] = "S81-LEAF-PLAN ft_seam_fix <- " + raw.get("note", "")[:200]
        Path(a.out).write_text(json.dumps(raw) + "\n")
    Path(a.ledger).write_text(json.dumps(ledger, indent=1) + "\n")
    print("seam hops %d on %d slots; %s" % (len(found), len(by), "dry" if a.dry else
          "fixed %d, left %d" % (sum(1 for r in ledger["slots"] if r.get("action")), len(ledger.get("after", [])))))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
