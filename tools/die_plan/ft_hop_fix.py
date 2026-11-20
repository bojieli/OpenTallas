#!/usr/bin/env python3
"""S81-LEAF-PLAN 11-15 (COORD / FABLE-CLOSURE-STRATEGY 05:1x item 1): every lane hop over the reach, in-slot or over a
seam, closed by ft stations (plan delta, latency priced).

check.lane_geometry carries registers only at the ft stations of the partitions a lane crosses, so a long hop is
either (a) between two stations of one slot (in-slot), (b) from a slot's last station over the out pin and seam to
the next partition's first station / the lane end (seam, ft_seam_fix's case), or (c) from the lane start / the in pin
to S1.  For each (type, slot) that owns such a hop:
  - regs_um slots: a station is inserted in the middle of the longest hop that touches the slot (centre off any macro;
    bit-site group = the neighbouring stage's group moved there onto free legal sites), repeated until every hop that
    touches the slot is <= LIMIT; a last->seam hop first tries ft_seam_fix.fix_slot (re-site, then append);
  - analytic slots (no regs_um, stations spaced on the slot route): stations + n;
  - every station added is +1 on stations / cycles / natural of every lane crossing that slot (all partitions).
Windows, pins, outlines and cores never change.  Exit 0 when no hop over LIMIT is left on the lanes it touched.

    ft_hop_fix.py PLAN OUT LEDGER [--limit 400] [--report 405] [--lane REGEX] [--max-add 8] [--dry]
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import check as C  # noqa: E402
import ft_seam_fix as SF  # noqa: E402

import os as _os_cbc, sys as _sys_cbc
_sys_cbc.path.insert(0, _os_cbc.path.dirname(_os_cbc.path.abspath(__file__)))
import cbc_rules as _CBC  # noqa: E402  OWNER 11-20 #6: generator hop default (300 um), one knob for every die
LIMIT = _CBC.REACH_UM_PER_HOP - _CBC.SITE_MARGIN_UM
REPORT = 405.0
MAX_ADD = 8
FRACTIONS = (.5, .4, .6, .3, .7, .2, .8)


def long_hops(P, lim, lane_rx=None, lids=None):
    """[(lane, hop_um, (part, slot) owning it, kind, i)] for hops > lim; the owner is the slot whose station starts the
    hop (in-slot / seam), or the slot whose station ends it when it starts at the lane source."""
    out = []
    for lid in (lids if lids is not None else P.lanes):
        if lane_rx and not re.search(lane_rx, lid):
            continue
        try:
            hops = SF.lane_hops(P, lid)
        except Exception:
            continue
        lab = SF.lane_labels(P, lid)
        if len(hops) != len(lab) - 1:
            continue
        for i, h in enumerate(hops):
            if h <= lim + 1e-6:
                continue
            a, b = lab[i], lab[i + 1]
            if len(a) == 3 and len(b) == 3 and a[:2] == b[:2]:
                out.append((lid, h, (a[0], a[1]), "in", a[2]))
            elif len(a) == 3:
                out.append((lid, h, (a[0], a[1]), "seam", a[2]))
            elif len(b) == 3:
                out.append((lid, h, (b[0], b[1]), "start", -1))
            else:
                out.append((lid, h, None, "direct", i))
    return out


def bump_latency(raw, lids, n):
    for lid in lids:
        r = raw["latency"]["lanes"].get(lid)
        if r is None:
            continue
        for f in ("stations", "cycles", "natural"):
            if f in r:
                r[f] = int(r[f]) + n


def touching_hops(P, lids, tn, sn):
    """[(hop_um, lane, i, j_from, j_to)] of every hop with an end on a station of (tn, sn); j = station index or None."""
    out = []
    for lid in lids:
        hops = SF.lane_hops(P, lid); lab = SF.lane_labels(P, lid)
        for i, h in enumerate(hops):
            a, b = lab[i], lab[i + 1]
            ja = a[2] if len(a) == 3 and a[1] == sn and P.parts[a[0]]["type"] == tn else None
            jb = b[2] if len(b) == 3 and b[1] == sn and P.parts[b[0]]["type"] == tn else None
            if ja is not None or jb is not None:
                out.append((h, lid, i, ja, jb))
    return out


def insert_station(t, s, j):
    """insert a station between regs[j] and regs[j+1] (centre off macros, bit sites moved from the neighbour)."""
    regs = s["regs_um"]
    a, b = np.array(regs[j], float), np.array(regs[j + 1], float)
    has_sites = bool(s.get("bit_sites_um")) and len(s["bit_sites_um"]) == int(s["stations"]) - 1
    for f in FRACTIONS:
        mid = SF.off_macro(SF.macro_boxes(t), a + (b - a) * f)
        if mid is None:
            continue
        if has_sites:
            ref = s["bit_sites_um"][j] if j < len(s["bit_sites_um"]) else s["bit_sites_um"][-1]   # stage j+1's group
            refc = np.array(regs[j + 1], float)
            g = SF.group_at(t, s, None, np.array(mid) - refc, base=ref)
            if g is None:
                continue
            s["bit_sites_um"].insert(j, g)
        break
    else:
        return False
    regs.insert(j + 1, [float(mid[0]), float(mid[1])])
    s["stations"] = int(s["stations"]) + 1
    return True


def append_station(t, s, out_pt):
    """append a station halfway between the last station and the out point (bit sites moved from the last group)."""
    regs = s["regs_um"]
    last = np.array(regs[-1], float); op = np.array(out_pt, float)
    has_sites = bool(s.get("bit_sites_um")) and len(s["bit_sites_um"]) == int(s["stations"]) - 1
    for f in FRACTIONS:
        mid = SF.off_macro(SF.macro_boxes(t), last + (op - last) * f)
        if mid is None:
            continue
        if has_sites:
            g = SF.group_at(t, s, None, np.array(mid) - last, base=s["bit_sites_um"][-1])
            if g is None:
                continue
            s["bit_sites_um"].append(g)
        break
    else:
        return False
    regs.append([float(mid[0]), float(mid[1])])
    s["stations"] = int(s["stations"]) + 1
    return True


def fix_slot(P, raw, tn, sn, lim, max_add, rec):
    t = raw["partition_types"][tn]
    s = next(x for x in t["ft_slots"] if x["name"] == sn)
    lids = SF.slot_lanes(P, tn, sn)
    k0 = int(s.get("stations", 1)); keep = json.dumps(s)
    lat_keep = {l: json.dumps(raw["latency"]["lanes"][l]) for l in lids if l in raw["latency"]["lanes"]}

    def restore():
        s.clear(); s.update(json.loads(keep))
        for l, v in lat_keep.items():
            raw["latency"]["lanes"][l] = json.loads(v)
    th = touching_hops(P, lids, tn, sn)
    rec.update(stations_before=k0, lanes=len(lids), worst_before=round(max(h for h, *_ in th), 1) if th else 0.0)
    added = 0
    if not s.get("regs_um"):
        # analytic slot: stations spaced evenly on the slot route
        for n in range(1, max_add + 1):
            s["stations"] = k0 + n
            th = touching_hops(P, lids, tn, sn)
            if max(h for h, *_ in th) <= lim + 1e-6:
                added = n
                break
        else:
            restore()
            rec["why"] = f"analytic slot: +{max_add} stations do not bring the touching hops under {lim}"
            return False
    else:
        while True:
            th = touching_hops(P, lids, tn, sn)
            bad = [x for x in th if x[0] > lim + 1e-6 and not (x[3] is None and x[4] == 0)]
            if not bad:
                break
            if added >= max_add:
                restore()
                rec["why"] = f"+{max_add} stations leave hops {sorted(round(x[0], 1) for x in bad)[-3:]} um"
                return False
            h, lid, i, ja, jb = max(bad)
            k = int(s["stations"])
            if ja is not None and jb is not None:                 # in-slot hop ja -> jb
                j = min(ja, jb)
            elif ja is not None:                                  # last -> seam / lane end: re-site or append
                r2 = {}
                if SF.fix_slot(P, raw, tn, sn, lim, True, r2) and r2.get("action"):
                    n = int(s["stations"]) - k
                    if n:                                         # SF.fix_slot already priced its own adds
                        added += n
                        rec.setdefault("seam_adds", 0); rec["seam_adds"] += n
                    rec.setdefault("seam", []).append(r2.get("action"))
                    continue
                if not append_station(t, s, SF.out_point(P, tn, s)):
                    restore(); rec["why"] = "no legal site for an appended station"
                    return False
                added += 1; bump_latency(raw, lids, 1)
                continue
            else:                                                 # source / in pin -> station jb
                j = None
                if jb == 0:
                    rec["why"] = "hop ends at S0 (the in pin): the far side owns it"
                    restore(); return False
                j = jb - 1
            if not insert_station(t, s, j):
                restore(); rec["why"] = f"no legal site between stations {j} and {j + 1}"
                return False
            added += 1; bump_latency(raw, lids, 1)
    if not s.get("regs_um") and added:
        bump_latency(raw, lids, added)
    th = touching_hops(P, lids, tn, sn)
    rec.update(stations_after=int(s["stations"]), added=int(s["stations"]) - k0,
               worst_after=round(max(h for h, *_ in th), 1) if th else 0.0, lane_rows=lids if s["stations"] != k0 else [])
    if s["stations"] != k0:
        s["note"] = (s.get("note", "") + " | ft_hop_fix 11-15: +%d station(s), every touching hop <= %g um (COORD "
                     "+1 ft register pre-approved)" % (int(s["stations"]) - k0, lim)).strip(" |")
    return True


def part_box(P, p):
    pr = P.parts[p]; w, h = P.types[pr["type"]]["outline_um"]; x, y = pr["origin_um"]
    if pr.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    return (float(x), float(y), float(x) + w, float(y) + h)


GROW_KEEPS = {"N": ("R0", "MY"), "E": ("R0", "MX")}      # die-face growth that keeps the type-frame origin side


def grow_gaps(P, raw, found, min_gap=1.0):
    """--grow-gaps: a seam hop between partitions A -> B whose faces look at each other across EMPTY die area (no
    partition in the gap) is closed by growing the partition whose facing side is its die N / E face (type origin and
    the other faces' windows stay) by exactly the gap, so the two faces abut.  Single-instance, non-hard types only.
    Returns [(type, side, gap_um, grown part, abutted part)]."""
    inst = defaultdict(int)
    for pr in P.parts.values():
        inst[pr["type"]] += 1
    boxes = {p: part_box(P, p) for p in P.parts}
    done, out = set(), []
    for lid, h, own, kind, j in found:
        if kind != "seam":
            continue
        lab = SF.lane_labels(P, lid)
        i = next((n for n, x in enumerate(lab) if len(x) == 3 and (x[0], x[1]) == own and x[2] == j), None)
        if i is None or i + 1 >= len(lab) or len(lab[i + 1]) != 3:
            continue
        pa, pb = own[0], lab[i + 1][0]
        for lo, hi, side in ((pa, pb, "N"), (pb, pa, "N"), (pa, pb, "E"), (pb, pa, "E")):
            Lb, Ub = boxes[lo], boxes[hi]
            if side == "N":
                gap = Ub[1] - Lb[3]; ov = min(Lb[2], Ub[2]) - max(Lb[0], Ub[0])
            else:
                gap = Ub[0] - Lb[2]; ov = min(Lb[3], Ub[3]) - max(Lb[1], Ub[1])
            if gap < min_gap or ov <= 0:
                continue
            tn = P.parts[lo]["type"]
            if (tn, side) in done or inst[tn] != 1 or P.types[tn].get("hard") or \
                    P.parts[lo].get("orient", "R0") not in GROW_KEEPS[side]:
                continue
            full = (Lb[0], Lb[1], Lb[2] + (gap if side == "E" else 0), Lb[3] + (gap if side == "N" else 0))
            if any(q != lo and min(full[2], b[2]) - max(full[0], b[0]) > 1e-6 and
                   min(full[3], b[3]) - max(full[1], b[1]) > 1e-6 for q, b in boxes.items()):
                continue                                          # the gap is not empty over the grown face
            t = raw["partition_types"][tn]
            ax = 1 if side == "N" else 0
            old = float(t["outline_um"][ax])
            t["outline_um"][ax] = round(old + gap, 4)
            for fs in t.get("ft_slots", []):                      # face-site registers follow the moved face
                for r in fs.get("regs_um") or []:
                    if r[ax] >= old - 1.0:
                        r[ax] = round(r[ax] + gap, 4)
            t["note"] = (t.get("note", "") + " | ft_hop_fix 11-15 --grow-gaps: +%.2f um on the die %s side to abut "
                         "%s across an empty gap (seam hop %.1f um)" % (gap, side, hi, h)).strip(" |")
            boxes[lo] = full
            chans = raw.get("die", {}).get("channels", [])
            keep = [c for c in chans if set(c.get("between", [])) != {lo, hi}]
            if len(keep) != len(chans):                           # the gap is gone: its declared die channel too
                raw["die"]["channels"] = keep
            done.add((tn, side)); out.append((tn, side, round(gap, 2), lo, hi))
            break
    return out


def run_pass(P, raw, found, a, led, npass):
    owners = defaultdict(list)
    for x in found:
        if x[2] is not None:
            owners[(P.parts[x[2][0]]["type"], x[2][1])].append(x)
    n = 0
    for (tn, sn), xs in sorted(owners.items()):
        rec = dict(type=tn, slot=sn, lanes_over=sorted({x[0] for x in xs}), worst=round(max(x[1] for x in xs), 1))
        rec["pass"] = npass
        rec["ok"] = fix_slot(P, raw, tn, sn, a.limit, a.max_add, rec)
        n += bool(rec["ok"] and rec.get("added", 0) or rec.get("seam"))
        led["slots"].append(rec)
        print(npass, tn, sn, rec.get("worst"), "->", rec.get("worst_after"), "+%s" % rec.get("added"), rec.get("why", ""),
              flush=True)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("ledger")
    ap.add_argument("--limit", type=float, default=LIMIT); ap.add_argument("--report", type=float, default=REPORT)
    ap.add_argument("--lane"); ap.add_argument("--max-add", type=int, default=MAX_ADD); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--grow-gaps", action="store_true", help="grow N/E partition faces into empty seam gaps first")
    ap.add_argument("--passes", type=int, default=3)
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text()); P = S.Plan(raw)
    found0 = long_hops(P, a.report, a.lane)
    lids = sorted({x[0] for x in found0})
    lat0 = json.loads(json.dumps(raw["latency"]["lanes"]))
    led = dict(found=[[x[0], round(x[1], 1), list(x[2] or []), x[3], x[4]] for x in found0], grown=[], slots=[])
    if a.dry:
        Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
        print("hops > %g: %d on %d lanes (dry)" % (a.report, len(found0), len(lids)))
        return 0
    if a.grow_gaps:
        led["grown"] = grow_gaps(P, raw, found0)
        P = S.Plan(raw)
        for g in led["grown"]:
            print("GROW", *g, flush=True)
    for npass in range(a.passes):
        found = long_hops(P, a.report, None, lids)
        if not found or not run_pass(P, raw, found, a, led, npass):
            break
    rest = long_hops(P, a.report, None, lids)
    led["after"] = [[x[0], round(x[1], 1), list(x[2] or []), x[3], x[4]] for x in rest]
    led["latency_delta"] = {l: [lat0[l].get("cycles"), raw["latency"]["lanes"][l].get("cycles")]
                            for l in raw["latency"]["lanes"] if lat0.get(l) != raw["latency"]["lanes"][l]}
    raw["note"] = "S81-LEAF-PLAN ft_hop_fix <- " + raw.get("note", "")[:200]
    Path(a.out).write_text(json.dumps(raw) + "\n")
    Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    print("hops > %g: %d on %d lanes; grown %d types; after: %d hops on %d lanes; lanes re-priced %d" % (
        a.report, len(found0), len(lids), len(led["grown"]), len(rest), len({x[0] for x in rest}), len(led["latency_delta"])))
    return 0 if not rest else 1


if __name__ == "__main__":
    sys.exit(main())
