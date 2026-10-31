#!/usr/bin/env python3
"""DIE-S81-42/BANDROW 10-31: one-block plan fix (METHODOLOGY 12.20) -- corner-clamped ring band pushes its neighbour
into a second band row.

Root cause (GEOM-89 06:51, COORD spot-check 07:20, CHECKED on plan_h2_2249.json): a slot whose pin window starts
inside the 17.28-um outline margin (window 6.144..117.084) got a ring band of the window's width clamped to the
margin (17.28..128.22), i.e. shifted ~11 um past its own pins and over the next slot's window (119.04..).  The
composer then placed the next slot's band in a SECOND row (one band depth further from the face), so the kit's
ring flops sit 43-52 um under their pins: pin_reg_p90 31.16 / 31.13 (max 57.4) on slice_station__t42__cl4bd1432c
and __t40__cl1ea9de02.

Fix (bands only, per type): the clamped band A is clamped to its own pin span inside the margin and deepened to
keep its area (delta_cland_band_1031.new_rect variant B); every band B on the same face whose along-face range
overlapped A's old range and sat behind A (further from the face) is moved up to A's row (face-side edge = A's
face-side edge, same along range and depth); a band is never moved further from its face.  Obstacles (hard cores/keepouts, die clock islands, reserved die clock sites, ft bit sites)
are checked on every new rect, the type's bands must stay pairwise disjoint, reach <= 402.84, area >= reserve.
Outlines, pins, windows, slots, taps, clock entries, collector graph and every other type are asserted unchanged;
the band copies in landing_contract.collector_local_sources and in the bind sidecar are rewritten with the rect.

usage (repo root): delta_bandrow_1031.py PLAN_IN PLAN_OUT REPORT.json --types t1,t2 [--sidecar IN OUT]"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import delta_cland_band_1031 as D  # noqa: E402

CP = D.CP


def face_edge(face, r):
    return {"N": r[3], "S": r[1], "W": r[0], "E": r[2]}[face]


def face_dist(face, edge, W, H):
    """distance of a band's face-side edge from its face; a neighbour only ever moves closer to its pins"""
    return {"N": H - edge, "S": edge, "W": edge, "E": W - edge}[face]


def to_face_row(face, r, edge):
    if face == "N":
        d = r[3] - r[1]; return [r[0], round(edge - d, 6), r[2], edge]
    if face == "S":
        d = r[3] - r[1]; return [r[0], edge, r[2], round(edge + d, 6)]
    if face == "W":
        d = r[2] - r[0]; return [edge, r[1], round(edge + d, 6), r[3]]
    d = r[2] - r[0]; return [round(edge - d, 6), r[1], edge, r[3]]


def plan_type(t):
    """[(bus, old, new, face, win, role)] for one type."""
    bands = t["clock"]["landing_contract"]["bands"]
    W, H = t["outline_um"]
    out = []
    for bus, b in bands.items():
        g = D.slot_side(t, bus)
        if not g or not b.get("rect_um"):
            continue
        lo, hi = D.along(g["face"], b["rect_um"])
        ext = W if g["face"] in "NS" else H
        wl, wh = g["win"]
        clamp = ((wl < D.MARGIN - 1e-3 and abs(lo - D.MARGIN) < 1e-3 and hi > wh + 1e-3) or
                 (wh > ext - D.MARGIN + 1e-3 and abs(hi - (ext - D.MARGIN)) < 1e-3 and lo < wl - 1e-3))
        if not clamp:
            continue
        old = list(b["rect_um"])
        nr, _ = D.new_rect(t, g["face"], g["win"], old, "B")
        edge = face_edge(g["face"], old)
        pushed = []
        for b2, r2 in bands.items():
            g2 = D.slot_side(t, b2)
            if b2 == bus or not g2 or g2["face"] != g["face"] or not r2.get("rect_um"):
                continue
            l2, h2 = D.along(g["face"], r2["rect_um"])
            if (min(hi, h2) > max(lo, l2) + 1e-6 and abs(face_edge(g["face"], r2["rect_um"]) - edge) > 1e-6 and
                    face_dist(g["face"], edge, W, H) < face_dist(g["face"], face_edge(g["face"], r2["rect_um"]), W, H) - 1e-6):
                o2 = list(r2["rect_um"])
                pushed.append((b2, o2, to_face_row(g["face"], o2, edge), g2["face"], g2["win"], "pushed"))
        # only a clamped band that displaced a neighbour moves, and never to a longer pin hop
        if pushed and D.hop(t, g["face"], g["win"], nr) <= D.hop(t, g["face"], g["win"], old) + 1e-6:
            out.append((bus, old, nr, g["face"], g["win"], "clamped"))
            out.extend(pushed)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("report")
    ap.add_argument("--types", required=True)
    ap.add_argument("--sidecar", nargs=2)
    a = ap.parse_args()
    text = open(a.plan_in).read()
    raw = json.loads(text); orig = copy.deepcopy(raw)
    types = [x for x in a.types.split(",") if x]
    rep = dict(lane="DIE-S81-42/BANDROW", plan_in=a.plan_in, types={})
    for tn in types:
        t = raw["partition_types"][tn]
        lc = t["clock"]["landing_contract"]; bands = lc["bands"]
        moves = plan_type(t)
        assert moves, (tn, "no clamped band")
        rows = []
        obs = D.obstacles(t)
        for bus, old, nr, face, win, role in moves:
            b = bands[bus]
            hits = [o for o in obs if D._ov(nr, o)]
            assert not hits, (tn, bus, nr, hits[:4])
            W, H = t["outline_um"]
            assert nr[0] >= D.MARGIN - 1e-6 and nr[1] >= D.MARGIN - 1e-6, (tn, bus, nr)
            assert nr[2] <= W - D.MARGIN + 1e-6 and nr[3] <= H - D.MARGIN + 1e-6, (tn, bus, nr)
            nh = D.hop(t, face, win, nr)
            assert nh <= D.REACH, (tn, bus, nh)
            narea = (nr[2] - nr[0]) * (nr[3] - nr[1])
            assert narea + 1e-6 >= b.get("area_reserve_um2", 0), (tn, bus, narea)
            oh = b.get("max_pin_to_band_hop_um")
            b["rect_um"] = nr; b["max_pin_to_band_hop_um"] = nh
            n_copy = 0
            for s in lc.get("collector_local_sources", []):
                if s.get("name") == bus and s.get("band", {}).get("rect_um") == old:
                    s["band"]["rect_um"] = nr; s["band"]["max_pin_to_band_hop_um"] = nh; n_copy += 1
            lo, hi = D.along(face, nr)
            rows.append(dict(bus=bus, role=role, face=face, pins=win, band_old=old, band_new=nr,
                             covers_pins=bool(lo <= max(win[0], D.MARGIN) + 1e-3 and hi >= win[1] - 1e-3),
                             area_new=round(narea, 3), hop_old=oh, hop_um=nh, copies_updated=n_copy))
        fin = [(o, bands[o]["rect_um"]) for o in bands if bands[o].get("rect_um")]
        for i, (n1, r1) in enumerate(fin):
            for n2, r2 in fin[i + 1:]:
                assert not D._ov(r1, r2), (tn, n1, r1, n2, r2)
        rep["types"][tn] = rows
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn, t in raw["partition_types"].items():
        o = orig["partition_types"][tn]
        if tn not in types:
            assert t == o, tn
            continue
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
        for s, os_ in zip(lc.get("collector_local_sources", []), olc.get("collector_local_sources", [])):
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
            st = side["collector"]["types"].get(tn)
            if st is None:
                continue
            for r in rows:
                b = st.get("bands", {}).get(r["bus"])
                if b is not None:
                    assert b["rect_um"] == r["band_old"], (tn, r["bus"])
                    b["rect_um"] = r["band_new"]; b["max_pin_to_band_hop_um"] = r["hop_um"]; n += 1
                for src in st.get("local_sources", []):
                    if src.get("name") == r["bus"] and src.get("band", {}).get("rect_um") == r["band_old"]:
                        src["band"]["rect_um"] = r["band_new"]; src["band"]["max_pin_to_band_hop_um"] = r["hop_um"]; n += 1
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
            print(tn, r["bus"], r["role"], r["face"], "pins", r["pins"], r["band_old"], "->", r["band_new"],
                  "cover" if r["covers_pins"] else "UNCOVERED", "hop", r["hop_old"], "->", r["hop_um"])
    if a.sidecar:
        print("sidecar copies", rep["sidecar_band_copies_updated"])


if __name__ == "__main__":
    main()
