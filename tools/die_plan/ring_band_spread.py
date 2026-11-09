#!/usr/bin/env python3
"""ring_band_spread.py (KV-TYPES-4 11-08): LANDING-RING-DENSITY class fix as one plan event for a whole die.

Every wide landing ring (ring_width >= --min-ring, default 192 bits) gets its storage band re-sized by the existing
clock_landing_plan band sizer at BAND_RESERVE ring_ff, spread --spread (default 7, the DIE-HEAD-84 l48vd value and the
KV-TYPES-3 kv3_hroot value).  The sizer steps the spread down in 0.05 steps until a legal band fits (macro-, station-,
reset-, island- and other-band-free, every corner within 405 um of its pin), so a crowded face keeps a smaller band
rather than failing.  Bands are taken widest ring first; each new band becomes an obstacle for the next.
Plan data only: no RTL, pin, ring width, cycle or outline change.  Every other key of the plan stays byte-equal
(asserted); types outside --types are untouched (asserted).

Evidence for the class: kv3_hroot c4bf6600c551 GRT-0116 (1581/1609 overflow regions in the 28.6-um kvpc band
column); after that one band was spread, the remaining overflow sits on the next two wide bands (o_hroot_Q 1152,
ft2_i 320).  HEAD hd_ctl_n vC3 GRT-0183 (l48vd).  504 bands with ring_width >= 192 in the KV plan are all at the
default spread (~100 % reserve fill).

usage (repo root): ring_band_spread.py PLAN_IN SIDECAR PLAN_OUT REPORT.json [--types a,b|all] [--min-ring 192]
                   [--spread 7] [--die-tag TAG] [--bisect]
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as C  # noqa: E402
import schema as S  # noqa: E402


def wide_bands(t, min_ring):
    b = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
    return sorted([k for k, v in b.items() if v.get("rect_um") and int(v.get("ring_width", 0)) >= min_ring],
                  key=lambda k: (-int(b[k]["ring_width"]), k))


def _band_bisect(tt, bus, width, used, phy, resets, spread):
    """--bisect (KV-TYPES-5 11-08, opt-in): same 0.05 spread grid as the sizer's linear step-down (spread, spread-0.05,
    ... 1.0), but the first legal step is found by bisection (~8 sizer calls instead of up to 121).  Exact when legality
    is monotone in the spread (a smaller band fits wherever a larger one does, the usual case); otherwise it may return
    a smaller legal step than the linear scan.  Every returned band is a normal sizer result (same legality rules)."""
    steps = [round(spread - 0.05 * k, 4) for k in range(int(round((spread - 1) / 0.05)) + 1)]
    def at(k):
        try:
            return C._storage_band(tt, bus, width, used, phy=phy, resets=resets, _scale=steps[k])
        except ValueError:
            return None
    b = at(0)
    if b is not None:
        return b
    last = at(len(steps) - 1)
    if last is None:
        return C._storage_band(tt, bus, width, used, phy=phy, resets=resets, _scale=steps[-1])  # raises the sizer error
    lo, hi, best = 0, len(steps) - 1, last  # steps[lo] illegal, steps[hi] legal
    while hi - lo > 1:
        mid = (lo + hi) // 2
        r = at(mid)
        if r is None:
            lo = mid
        else:
            hi, best = mid, r
    return best


def resize_type(plan, side, tn, min_ring, spread, tag, P=None, bisect=False):
    t = plan["partition_types"][tn]
    lc = t["clock"]["landing_contract"]
    bands = lc["bands"]
    geoms = side["collector"]["types"]
    if tn not in geoms:
        return [dict(type=tn, skipped="no sidecar bus geometry")]
    phy = C.phy_supply_rects(P, tn) if P is not None else []
    resets = C._reset_sites_for_type(plan, tn, geoms[tn].get("tree"), lc.get("base_type"))
    tt = copy.deepcopy(t)
    tt["_cland_geom"] = copy.deepcopy(geoms[tn]["bus_geometry"])
    rows = []
    saved = (C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING)
    try:
        for bus in wide_bands(t, min_ring):
            old = bands[bus]
            C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING = "ring_ff", float(spread), old.get("ring_place", "ff") or "ff"
            used = [list(o["rect_um"]) for k, o in bands.items() if k != bus and o.get("rect_um")]
            try:
                if bisect:
                    nb = _band_bisect(tt, bus, int(old["width"]), used, phy, resets, float(spread))
                else:
                    nb = C._storage_band(tt, bus, int(old["width"]), used, phy=phy, resets=resets)
            except ValueError as e:
                rows.append(dict(type=tn, bus=bus, ring=int(old["ring_width"]), kept=list(old["rect_um"]), error=str(e)[:200]))
                continue
            for k, v in old.items():
                if k not in nb and k not in ("spread", "band_spread_target", "max_pin_to_band_hop_um", "area_reserve_um2",
                                             "resized_from_um", "resize"):
                    nb[k] = v
            nb["resized_from_um"] = list(old["rect_um"])
            nb["resize"] = f"{tag} LANDING-RING-DENSITY: ring_ff spread {spread:g} (class, ring_width >= {min_ring})"
            ox0, oy0, ox1, oy1 = old["rect_um"]
            x0, y0, x1, y1 = nb["rect_um"]
            rows.append(dict(type=tn, bus=bus, ring=int(old["ring_width"]), old_um=list(old["rect_um"]), new_um=nb["rect_um"],
                             old_area=round((ox1 - ox0) * (oy1 - oy0)), new_area=round((x1 - x0) * (y1 - y0)),
                             spread=nb.get("spread"), hop_um=nb.get("max_pin_to_band_hop_um")))
            bands[bus] = nb
    finally:
        C.BAND_RESERVE, C.BAND_SPREAD, C.BAND_RING = saved
    # no two bands overlap after the event
    rr = [(k, v["rect_um"]) for k, v in bands.items() if v.get("rect_um")]
    for i, (a, ra) in enumerate(rr):
        for b, rb in rr[i + 1:]:
            if C._rect_overlap(ra, rb):
                raise ValueError(f"{tn}: bands {a} and {b} overlap after the event")
    return rows


def splice(text, plan, changed):
    out = text
    for tn in changed:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', out, re.M)
        _, j = json.JSONDecoder().raw_decode(out, m.end())
        out = out[:m.end()] + json.dumps(plan["partition_types"][tn], indent=1).replace("\n", "\n  ") + out[j:]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in")
    ap.add_argument("sidecar")
    ap.add_argument("plan_out")
    ap.add_argument("report")
    ap.add_argument("--types", default="all")
    ap.add_argument("--min-ring", type=int, default=192)
    ap.add_argument("--spread", type=float, default=7.0)
    ap.add_argument("--tag", default="KV-TYPES-4 11-08")
    ap.add_argument("--bisect", action="store_true", help="find the sizer spread step by bisection (opt-in, faster)")
    a = ap.parse_args(argv)
    text = open(a.plan_in).read()
    plan = json.loads(text)
    orig = copy.deepcopy(plan)
    side = json.load(open(a.sidecar))
    P = S.Plan(copy.deepcopy(plan)) if (plan.get("die") or {}).get("pg", {}).get("domains") and plan.get("partitions") else None
    names = sorted(plan["partition_types"]) if a.types == "all" else a.types.split(",")
    rows, changed = [], []
    for tn in names:
        if not wide_bands(plan["partition_types"][tn], a.min_ring):
            continue
        r = resize_type(plan, side, tn, a.min_ring, a.spread, a.tag, P, bisect=a.bisect)
        rows += r
        if any("new_um" in x for x in r):
            changed.append(tn)
    for k in plan:
        if k != "partition_types":
            assert plan[k] == orig[k], k
    for tn in plan["partition_types"]:
        if tn not in changed:
            assert plan["partition_types"][tn] == orig["partition_types"][tn], tn
    out = splice(text, plan, changed)
    assert json.loads(out) == plan
    S.Plan(json.loads(out), Path(a.plan_in).resolve())
    open(a.plan_out, "w").write(out)
    over = [x for x in rows if (x.get("hop_um") or 0) > 405]
    rep = dict(min_ring=a.min_ring, spread=a.spread, types_changed=changed, bands_resized=sum("new_um" in x for x in rows),
               bands_kept=[x for x in rows if "error" in x or "skipped" in x], hop_over_405=over, rows=rows)
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: (v if k != "rows" else len(v)) for k, v in rep.items()}, indent=1)[:4000])
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
