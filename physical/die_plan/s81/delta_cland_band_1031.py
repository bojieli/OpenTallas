#!/usr/bin/env python3
"""DIE-S81-40/BAND 10-31: one-block plan fix (METHODOLOGY 12.20) -- clock-landing ring bands over their own pins.

Root cause (CHECKED on plan_h2_2249.json sha256 84fc22ab807d): on a few slice_station types the landed N-face
slots carried in_window_um == out_window_um in plan_s13r2 (straight-through pins), and the H2 event moved their
in (landing) windows along the N face without recomposing the clock-landing ring bands.  Each band rect still spans
the slot's OUT window x-range (exact equality), so it sits beside its fclk_in / data pins, not over them
(t38 ft5_i band x 1020.3..1128.5 vs pins 1299.7..1422.6).  The kit must place the ring inside the plan band, so
pin_reg_p90 stays ~179-202 um (AUTOBUILD-PIPE-2 02:10 FINDING, GEOM-85 22:48/00:57/01:20).

Fix (per type, bands only): every ring band of the detected class is moved along its face so that it sits over its
own pin window.  The face-side band edge stays where it was (inset unchanged); area is preserved:
  variant A  centre the band on the pin span; band width = min(old width, span), depth = old area / width (rounded
             up to the 2.16-um row pair), i.e. a narrower span gets a deeper band centred on the pins;
  variant B  clamp the band to the pin span (band along-face extent = pin span exactly, kept >= 17.28 um inside the
             outline), depth = max(old depth, old area / span), so the band covers every pin.
Nothing else changes: outlines, pins, windows, slots, taps, clock entries, collector graph, sinks and every other
type are asserted JSON-equal.  The duplicate band copy under landing_contract.collector_local_sources[*].band and
max_pin_to_band_hop_um are updated with the rect.  Obstacles (hard cores/keepouts, die clock islands, reserved die
clock-tree sites, ft bit sites, the type's other bands) are checked on the new rect; any hit fails closed.

Class detection (default, all types): a ring band whose along-face extent equals the OTHER side window of its slot to
0.01 um and does not cover its own window.  On 84fc22ab807d: slice_station__t28, __t38, __t30__cl6a190133.

The bind's clock landing table (h2_2249/landed_sidecar_h2.json, collector.types[tn].bands and .local_sources[*].band)
carries the same band copies; --sidecar IN OUT rewrites exactly those (compact separators, byte-identical otherwise).

usage (repo root): delta_cland_band_1031.py PLAN_IN PLAN_OUT REPORT.json --variant A|B [--types t1,t2]
                   [--sidecar SIDECAR_IN SIDECAR_OUT]"""
import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compact_plan as CP  # noqa: E402
import reset_tree as RT  # noqa: E402

MARGIN = 17.28
ROW = 2.16
REACH = 405 - 2.16


def _ov(a, o):
    return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6


def slot_side(t, bus):
    if "_" not in bus:
        return None
    name, suf = bus.rsplit("_", 1)
    if suf not in ("i", "o"):
        return None
    s = next((x for x in t.get("ft_slots", []) if x["name"] == name), None)
    if s is None:
        return None
    me, other = ("in", "out") if suf == "i" else ("out", "in")
    face, win, owin = s.get(me + "_face"), s.get(me + "_window_um"), s.get(other + "_window_um")
    if face is None or win is None:
        return None
    return dict(slot=s, face=face, win=win, owin=owin)


def along(face, r):
    return (r[0], r[2]) if face in "NS" else (r[1], r[3])


def detect(raw):
    out = {}
    for tn, t in raw["partition_types"].items():
        bands = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
        for bus, b in bands.items():
            g = slot_side(t, bus)
            if g is None or not b.get("rect_um") or g["owin"] is None:
                continue
            lo, hi = along(g["face"], b["rect_um"])
            cover = lo <= g["win"][0] + 1e-3 and hi >= g["win"][1] - 1e-3
            eq_other = abs(lo - g["owin"][0]) < .01 and abs(hi - g["owin"][1]) < .01
            if eq_other and not cover:
                out.setdefault(tn, []).append(bus)
    return out


def obstacles(t, skip_bus=None):
    obs = [list(o) for o in RT.blockages(t)]
    ck = t.get("clock") or {}
    obs += [list(r) for r in ck.get("die_islands_um", [])]
    obs += [list(r["rect_um"]) for r in ck.get("reserved_sites_um", []) if r.get("kind") == "die_clock_tree"]
    for slot in t.get("ft_slots", []):
        cell = slot.get("bit_site_cell_um", [1.404, .27])
        for stage in slot.get("bit_sites_um", []) or []:
            if stage:
                obs.append([min(p[0] for p in stage) - cell[0] / 2, min(p[1] for p in stage) - cell[1] / 2,
                            max(p[0] for p in stage) + cell[0] / 2, max(p[1] for p in stage) + cell[1] / 2])
        if not slot.get("bit_sites_um"):
            obs += [[x - 2.16, y - 2.16, x + 2.16, y + 2.16] for x, y in slot.get("regs_um", [])]
    return obs


def new_rect(t, face, win, r, variant):
    w, h = t["outline_um"]
    ext = w if face in "NS" else h
    lo, hi = along(face, r)
    width = hi - lo
    depth = (r[3] - r[1]) if face in "NS" else (r[2] - r[0])
    area = width * depth
    span_lo, span_hi = max(MARGIN, win[0]), min(ext - MARGIN, win[1])
    span = span_hi - span_lo
    c = (win[0] + win[1]) / 2
    if variant == "A":
        nw = min(width, span)
        nlo = min(max(MARGIN, c - nw / 2), ext - MARGIN - nw)
        nhi = nlo + nw
        nd = depth if nw >= width - 1e-9 else math.ceil(area / nw / ROW - 1e-9) * ROW
    else:
        nlo, nhi = span_lo, span_hi
        nw = nhi - nlo
        nd = max(depth, math.ceil(area / nw / ROW - 1e-9) * ROW)
    nlo, nhi, nd = round(nlo, 6), round(nhi, 6), round(nd, 6)
    if face == "N":
        out = [nlo, round(r[3] - nd, 6), nhi, r[3]]
    elif face == "S":
        out = [nlo, r[1], nhi, round(r[1] + nd, 6)]
    elif face == "W":
        out = [r[0], nlo, round(r[0] + nd, 6), nhi]
    else:
        out = [round(r[2] - nd, 6), nlo, r[2], nhi]
    return out, area


def hop(t, face, win, r):
    w, h = t["outline_um"]
    at = (win[0] + win[1]) / 2
    px, py = ([0 if face == "W" else w, at] if face in "EW" else [at, 0 if face == "S" else h])
    return round(max(abs(x - px) + abs(y - py) for x in (r[0], r[2]) for y in (r[1], r[3])), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("report")
    ap.add_argument("--variant", choices=("A", "B"), required=True)
    ap.add_argument("--types", default="")
    ap.add_argument("--sidecar", nargs=2)
    a = ap.parse_args()
    text = open(a.plan_in).read()
    raw = json.loads(text); orig = copy.deepcopy(raw)
    found = detect(raw)
    types = [x for x in a.types.split(",") if x] or sorted(found)
    rep = dict(lane="DIE-S81-40/BAND", variant=a.variant, plan_in=a.plan_in, detected=found, types={})
    for tn in types:
        t = raw["partition_types"][tn]
        lc = t["clock"]["landing_contract"]
        bands = lc["bands"]
        rows = []
        for bus in found.get(tn, []):
            g = slot_side(t, bus); b = bands[bus]; old = list(b["rect_um"])
            nr, area = new_rect(t, g["face"], g["win"], old, a.variant)
            hits = [o for o in obstacles(t, bus) if _ov(nr, o)]
            assert not hits, (tn, bus, nr, hits[:4])
            assert nr[0] >= MARGIN - 1e-6 and nr[1] >= MARGIN - 1e-6, (tn, bus, nr)
            assert nr[2] <= t["outline_um"][0] - MARGIN + 1e-6 and nr[3] <= t["outline_um"][1] - MARGIN + 1e-6, (tn, bus, nr)
            nh = hop(t, g["face"], g["win"], nr)
            assert nh <= REACH, (tn, bus, nh)
            narea = (nr[2] - nr[0]) * (nr[3] - nr[1])
            assert narea + 1e-6 >= area and narea + 1e-6 >= b.get("area_reserve_um2", 0), (tn, bus, narea, area)
            b["rect_um"] = nr; b["max_pin_to_band_hop_um"] = nh
            n_copy = 0
            for s in lc.get("collector_local_sources", []):
                if s.get("name") == bus and s.get("band", {}).get("rect_um") == old:
                    s["band"]["rect_um"] = nr; s["band"]["max_pin_to_band_hop_um"] = nh; n_copy += 1
            lo, hi = along(g["face"], nr)
            rows.append(dict(bus=bus, face=g["face"], pins=g["win"], band_old=old, band_new=nr,
                             old_along=list(along(g["face"], old)), new_along=[lo, hi],
                             covers_pins=bool(lo <= g["win"][0] + 1e-3 and hi >= g["win"][1] - 1e-3),
                             uncovered_um=round(max(0, lo - g["win"][0]) + max(0, g["win"][1] - hi), 3),
                             area_old=round(area, 3), area_new=round(narea, 3),
                             depth_old=round((old[3] - old[1]) if g["face"] in "NS" else (old[2] - old[0]), 3),
                             depth_new=round((nr[3] - nr[1]) if g["face"] in "NS" else (nr[2] - nr[0]), 3),
                             hop_um=nh, copies_updated=n_copy))
        # the type's bands after the move (moved and unmoved) must stay pairwise disjoint
        fin = [(o, bands[o]["rect_um"]) for o in bands if bands[o].get("rect_um")]
        for i, (n1, r1) in enumerate(fin):
            for n2, r2 in fin[i + 1:]:
                assert not _ov(r1, r2), (tn, n1, r1, n2, r2)
        rep["types"][tn] = rows
    # nothing else moved
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn, t in raw["partition_types"].items():
        if tn not in types:
            assert t == orig["partition_types"][tn], tn
            continue
        o = orig["partition_types"][tn]
        for k in t:
            if k != "clock":
                assert t[k] == o[k], (tn, k)
        for k in t["clock"]:
            if k != "landing_contract":
                assert t["clock"][k] == o["clock"][k], (tn, "clock", k)
        lc, olc = t["clock"]["landing_contract"], o["clock"]["landing_contract"]
        for k in lc:
            if k not in ("bands", "collector_local_sources"):
                assert lc[k] == olc[k], (tn, k)
        for s, os_ in zip(lc["collector_local_sources"], olc["collector_local_sources"]):
            assert {k: v for k, v in s.items() if k != "band"} == {k: v for k, v in os_.items() if k != "band"}, tn
    for tn in types:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        assert m, tn
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    open(a.plan_out, "w").write(text)
    if a.sidecar:
        stext = open(a.sidecar[0]).read(); side = json.loads(stext); sorig = copy.deepcopy(side)
        assert json.dumps(side, separators=(",", ":")) + "\n" == stext, "sidecar format"
        n = 0
        for tn, rows in rep["types"].items():
            st = side["collector"]["types"][tn]
            for r in rows:
                b = st["bands"][r["bus"]]
                assert b["rect_um"] == r["band_old"], (tn, r["bus"])
                b["rect_um"] = r["band_new"]; b["max_pin_to_band_hop_um"] = r["hop_um"]; n += 1
                for src in st.get("local_sources", []):
                    if src.get("name") == r["bus"] and src.get("band", {}).get("rect_um") == r["band_old"]:
                        src["band"]["rect_um"] = r["band_new"]; src["band"]["max_pin_to_band_hop_um"] = r["hop_um"]; n += 1
            # the sidecar band copy must now equal the plan's
            assert st["bands"] == {k: v for k, v in raw["partition_types"][tn]["clock"]["landing_contract"]["bands"].items()
                                   if k in st["bands"]} or all(st["bands"][r["bus"]]["rect_um"] == r["band_new"] for r in rows), tn
        for k in side:
            if k != "collector":
                assert side[k] == sorig[k], k
        for k in side["collector"]:
            if k != "types":
                assert side["collector"][k] == sorig["collector"][k], k
        for tn in side["collector"]["types"]:
            if tn not in rep["types"]:
                assert side["collector"]["types"][tn] == sorig["collector"]["types"][tn], tn
        open(a.sidecar[1], "w").write(json.dumps(side, separators=(",", ":")) + "\n")
        rep["sidecar_band_copies_updated"] = n
    json.dump(rep, open(a.report, "w"), indent=1)
    for tn, rows in rep["types"].items():
        for r in rows:
            print(tn, r["bus"], r["face"], "pins", r["pins"], "old", [round(v, 1) for v in r["old_along"]],
                  "new", [round(v, 1) for v in r["new_along"]], "depth", r["depth_old"], "->", r["depth_new"],
                  "cover" if r["covers_pins"] else f"uncov {r['uncovered_um']}", "hop", r["hop_um"])


if __name__ == "__main__":
    main()
