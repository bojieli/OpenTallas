#!/usr/bin/env python3
"""DIE-S81-47 11-01 (COORD 15:5x class fix, GEOM-105 t41 attempt 4 FAIL: GRT overflow 4750, col_v 1.071 at the NW
corner (90,1207), where the north landing bank runs into the west ft column): slice_station north/south landing banks
start >= 150 um from a feedthrough-column edge.

Census (every slice_station type, every N/S-face input landing band = the N/S bank): the side (W/E-face) ft column
footprint of a slot = its face window strip plus, for a side INPUT slot, its own landing band rect(s).  gap = L-inf
gap between a bank band and a footprint.  Class = a bank band with gap < 150 um to a side ft LANDING column (an input
slot with its own band: two landing banks meet at one corner, the t41 mechanism).  Bank bands within 150 um of an
OUT-ONLY side ft row (no side landing band) are listed, not changed: that form is measured GRT 0 at the current geometry
on slice_station__t31 / __t44 / __t6__cl0755c26e (12.28b: measured route decides, no stricter reading).

Fix (band geometry only, per class band): the same rect (same width x height or rotated, so the same area / ring
capacity) moves to the legal position outside every side ft footprint grown by 150 um, with the same legality as the
band search (17.28-um outline margin; no overlap with blockages, other bands, FT bit sites / regs, collector / reset /
reader / writer / status sites, group rects, die islands, die clock-tree sites; every corner within 405-2.16 = 402.84 um
of the bus pin).  Choice: least detour of the bus path in-pin -> band centre -> out-pin (Manhattan; a N->S slot keeps
its band in its own column), then least pin hop, then nearest the old rect.  ring_place / width / reserve / instance /
clock and reset taps are unchanged; the band copies in collector_local_sources and in the landed sidecar follow.
Nothing else changes (asserted); landing_place.tcl() succeeds for every changed type.
usage (repo root): delta_stnbank_1101.py PLAN_IN PLAN_OUT SIDECAR_IN SIDECAR_OUT REPORT.json"""
import copy
import itertools
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402
import landing_place as LP  # noqa: E402
import compact_plan as CP  # noqa: E402
import clock_landing_plan as C  # noqa: E402

GAP, REACH, MARGIN, G = 150.0, 405 - 2.16, 17.28, 0.54
MEASURED_CLEAN_OUT_ONLY = {   # 3_place AUTO-GEOM GRT (50-it deck) on the current band geometry, intel1 kit-wave/s81
    "slice_station__t31": "e8cbe5f6c70 GRT 0 (GEOM-105 10:25 PASS-COND)",
    "slice_station__t44": "95b1992a3d0 attempt_2 GRT 0, col_v 0.464",
    "slice_station__t6__cl0755c26e": "f1a8dcffa6e attempt_5 GRT 0, col_v 0.618"}


def rects(b):
    return [list(r) for r in (b.get("rects_um") or [b["rect_um"]])]


def gap(a, b):
    return max(0.0, a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3])


def geom(t, side_t):
    tt = copy.deepcopy(t)
    tt["_cland_geom"] = copy.deepcopy(side_t.get("bus_geometry") or {})
    return tt


def face_of(tt, bus):
    try:
        return C._bus_geom(tt, bus)["face"]
    except ValueError:
        return None


def footprints(t, tt):
    """side ft column footprints: (slot, face, kind, rects); kind 'landing' = side input slot with its own band."""
    w, h = t["outline_um"]
    bands = t["clock"]["landing_contract"]["bands"]
    out = []
    for s in t.get("ft_slots", []):
        for sfx, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
            f = s.get(fk)
            if f not in ("W", "E") or wk not in s:
                continue
            a, b = s[wk]
            x = 0.0 if f == "W" else w
            rs = [[x, a, x, b]]
            band = bands.get(s["name"] + sfx) if sfx == "_i" else None
            if band and band.get("rect_um"):
                rs += rects(band)
            out.append((s["name"] + sfx, f, "landing" if len(rs) > 1 else "out_only", rs))
    return out


def census(raw, side):
    rows = []
    for tn in sorted(k for k in raw["partition_types"] if k.startswith("slice_station")):
        t = raw["partition_types"][tn]
        tt = geom(t, side["collector"]["types"].get(tn, {}))
        fps = footprints(t, tt)
        for bus, b in sorted(t["clock"]["landing_contract"]["bands"].items()):
            f = face_of(tt, bus)
            if f not in ("N", "S") or not b.get("rect_um"):
                continue
            best = {}
            for name, sf, kind, rs in fps:
                g = min(gap(r, q) for r in rects(b) for q in rs)
                if kind not in best or g < best[kind][0]:
                    best[kind] = (round(g, 3), name, sf)
            rows.append(dict(type=tn, bus=bus, face=f, rect_um=b["rect_um"],
                             start_from_W_um=round(min(r[0] for r in rects(b)), 3),
                             end_from_E_um=round(t["outline_um"][0] - max(r[2] for r in rects(b)), 3),
                             landing_col=best.get("landing"), out_only_col=best.get("out_only"),
                             hop_um=b.get("max_pin_to_band_hop_um")))
    return rows


def obstacles(t, tt, side_t, moving):
    lc = t["clock"]["landing_contract"]
    used = [r for k, o in lc["bands"].items() if k not in moving and o.get("rect_um") for r in rects(o)]
    resets = C.reset_site_rects(lc.get("collector_tree")) + C.reset_site_rects(side_t.get("tree"))
    resets += [list(r) for _p, r, _g in LP._reader_start_groups(t) + LP._writer_start_groups(t) +
               LP._status_reset_groups(t)]
    resets += [list(r) for r in lc.get("group_rects_um", {}).values()]
    ck = t.get("clock") or {}
    obs = C._band_obstacles(tt, used, resets=resets)
    obs += [list(r) for r in ck.get("die_islands_um", [])]
    obs += [list(r["rect_um"]) for r in ck.get("reserved_sites_um", []) if r.get("kind") == "die_clock_tree"]
    return obs


def place(t, tt, bus, old, obs, keep):
    """same-shape legal rect outside keep, least (detour, hop, shift)."""
    w, h = t["outline_um"]
    px, py = C._bus_xy(tt, bus)
    try:
        ox, oy = C._bus_xy(tt, bus[:-2] + "_o") if bus.endswith("_i") else (None, None)
    except ValueError:
        ox, oy = None, None
    bw0, bh0 = old[2] - old[0], old[3] - old[1]
    nx, ny = int(w / G) + 1, int(h / G) + 1
    occ = np.zeros((nx, ny), np.int32)
    for o in list(obs) + list(keep):
        i0, i1 = max(0, int(math.floor(o[0] / G))), min(nx, int(math.ceil(o[2] / G)))
        j0, j1 = max(0, int(math.floor(o[1] / G))), min(ny, int(math.ceil(o[3] / G)))
        if i1 > i0 and j1 > j0:
            occ[i0:i1, j0:j1] = 1
    Sm = np.zeros((nx + 1, ny + 1), np.int64)
    Sm[1:, 1:] = occ.cumsum(0).cumsum(1)
    best = None
    for bw, bh in {(bw0, bh0), (bh0, bw0)}:
        cw, chh = int(math.ceil(bw / G - 1e-9)) + 1, int(math.ceil(bh / G - 1e-9)) + 1
        if cw > nx or chh > ny:
            continue
        blk = Sm[cw:, chh:] - Sm[:-cw, chh:] - Sm[cw:, :-chh] + Sm[:-cw, :-chh]
        ii, jj = np.nonzero(blk == 0)
        x0, y0 = ii * G, jj * G
        x1, y1 = x0 + bw, y0 + bh
        ok = (x0 >= MARGIN - 1e-6) & (y0 >= MARGIN - 1e-6) & (x1 <= w - MARGIN + 1e-6) & (y1 <= h - MARGIN + 1e-6)
        hop = np.maximum(np.abs(x0 - px), np.abs(x1 - px)) + np.maximum(np.abs(y0 - py), np.abs(y1 - py))
        ok &= hop <= REACH + 1e-6
        if not ok.any():
            continue
        x0, y0, x1, y1, hop = x0[ok], y0[ok], x1[ok], y1[ok], hop[ok]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if ox is None:
            det = np.zeros_like(cx)
        else:
            det = (np.abs(cx - px) + np.abs(cy - py) + np.abs(cx - ox) + np.abs(cy - oy)) - (abs(ox - px) + abs(oy - py))
        shift = np.abs(x0 - old[0]) + np.abs(y0 - old[1])
        key = np.lexsort((shift, np.round(hop, 3), np.round(det, 0)))
        k = key[0]
        cand = (round(float(det[k]), 0), round(float(hop[k]), 3), float(shift[k]))
        box = [round(float(x0[k]), 6), round(float(y0[k]), 6), round(float(x1[k]), 6), round(float(y1[k]), 6)]
        if best is None or cand < best[0]:
            best = (cand, box)
    if best is None:
        raise ValueError(f"{bus}: no legal same-shape rect outside the ft keep-out within reach")
    box = best[1]
    assert not any(C._rect_overlap(box, o) for o in list(obs) + list(keep)), box
    assert C._hop(box, px, py) <= REACH + 1e-6
    return box, dict(detour_um=best[0][0], hop_um=round(C._hop(box, px, py), 3), pin_xy_um=[px, py],
                     out_xy_um=None if ox is None else [ox, oy])


def capacity(b, fill=0.90, w=1.08, h=0.27, sw=0.054):
    """first-fit ring-flop estimate (as delta_bands_1101.py): UNCHECKED estimate, mapped placement decides."""
    rs = rects(b)
    area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs)
    flops = 5 * (b["width"] + 1) + 160
    need = flops * math.ceil(w / 0.4 / sw - 1e-9) * sw * h
    sp = max(1.0, fill * area / need)
    rw = math.ceil(w / 0.4 * sp / sw - 1e-9) * sw
    cap = sum(int((r[3] - r[1]) / h + 1e-9) * (int((r[2] - r[0] - w) / rw + 1e-9) + 1)
              for r in rs if r[2] - r[0] >= w)
    return dict(flops_est=flops, capacity_flops=cap, ratio=round(cap / flops, 3))


def main():
    src, dst, sside, dside, rp = sys.argv[1:6]
    text = Path(src).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    stext = Path(sside).read_text()
    side = json.loads(stext)
    assert json.dumps(side, separators=(",", ":")) + "\n" == stext     # sidecar round-trips byte-identical
    sorig = copy.deepcopy(side)
    before = census(raw, side)
    cls = [r for r in before if r["landing_col"] and r["landing_col"][0] < GAP]
    watch = [r for r in before if not (r["landing_col"] and r["landing_col"][0] < GAP)
             and r["out_only_col"] and r["out_only_col"][0] < GAP]
    types = sorted({r["type"] for r in cls})
    moved, exceptions = [], []
    for tn in types:
        t = raw["partition_types"][tn]
        st = side["collector"]["types"][tn]
        tt = geom(t, st)
        lc = t["clock"]["landing_contract"]
        buses = sorted(r["bus"] for r in cls if r["type"] == tn)
        keep = [[max(0.0, q[0] - GAP), max(0.0, q[1] - GAP), min(t["outline_um"][0], q[2] + GAP),
                 min(t["outline_um"][1], q[3] + GAP)] for _n, _f, _k, rs in footprints(t, tt) for q in rs]
        done = None
        for order in itertools.permutations(buses):
            obs = obstacles(t, tt, st, set(buses))
            got = {}
            try:
                for bus in order:
                    box, info = place(t, tt, bus, lc["bands"][bus]["rect_um"], obs, keep)
                    got[bus] = (box, info)
                    obs = obs + [box]
            except ValueError as e:
                err = str(e)
                continue
            done = got
            break
        if done is None:
            exceptions.append(dict(type=tn, buses=buses, reason=err))
            continue
        for bus in buses:
            b = lc["bands"][bus]
            assert "rects_um" not in b, (tn, bus)
            box, info = done[bus]
            old = dict(rect_um=b["rect_um"], hop_um=b["max_pin_to_band_hop_um"])
            b["rect_um"] = box
            b["max_pin_to_band_hop_um"] = info["hop_um"]
            for src_ in lc.get("collector_local_sources", []):
                if src_["name"] == bus:
                    src_["band"] = copy.deepcopy(b)
            assert st["bands"][bus]["rect_um"] == old["rect_um"]
            st["bands"][bus] = copy.deepcopy(b)
            for src_ in st.get("local_sources", []):
                if src_["name"] == bus and "band" in src_:
                    src_["band"] = copy.deepcopy(b)
            moved.append(dict(type=tn, bus=bus, old_rect_um=old["rect_um"], new_rect_um=box,
                              old_hop_um=old["hop_um"], new_hop_um=info["hop_um"], detour_um=info["detour_um"],
                              pin_xy_um=info["pin_xy_um"], out_xy_um=info["out_xy_um"],
                              area_um2=round((box[2] - box[0]) * (box[3] - box[1]), 3),
                              reserve_um2=b["area_reserve_um2"], **capacity(b)))
    after = census(raw, side)
    # only the moved bands (and their copies) change
    mv = {(m["type"], m["bus"]) for m in moved}
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        a, b = copy.deepcopy(raw["partition_types"][tn]), copy.deepcopy(orig["partition_types"][tn])
        for obj in (a, b):
            lc = (obj.get("clock") or {}).get("landing_contract") or {}
            for bus in [x for (y, x) in mv if y == tn]:
                for kk in ("rect_um", "max_pin_to_band_hop_um"):
                    lc["bands"][bus].pop(kk)
                for src_ in lc.get("collector_local_sources", []):
                    if src_["name"] == bus:
                        for kk in ("rect_um", "max_pin_to_band_hop_um"):
                            src_["band"].pop(kk)
        assert a == b, tn
    for k in side:
        if k != "collector":
            assert side[k] == sorig[k], k
    for k in side["collector"]:
        if k != "types":
            assert side["collector"][k] == sorig["collector"][k], k
    for tn in side["collector"]["types"]:
        if tn not in {m["type"] for m in moved}:
            assert side["collector"]["types"][tn] == sorig["collector"]["types"][tn], tn
    # every moved band: legal, outside every side ft footprint +150, hop <= 402.84, same area
    for r in after:
        if (r["type"], r["bus"]) in mv:
            assert r["landing_col"] is None or r["landing_col"][0] >= GAP - 1e-6, r
            assert r["out_only_col"] is None or r["out_only_col"][0] >= GAP - 1e-6, r
    for m in moved:
        o, n = m["old_rect_um"], m["new_rect_um"]
        assert abs((o[2] - o[0]) * (o[3] - o[1]) - (n[2] - n[0]) * (n[3] - n[1])) < 1e-3, m
        assert m["new_hop_um"] <= REACH + 1e-6, m
    P = S.Plan(raw)
    for tn in {m["type"] for m in moved}:
        LP.tcl(P, tn)                                   # raises on an absent / invalid band
    for tn in sorted({m["type"] for m in moved}):
        mm = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, mm.end())
        text = text[:mm.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    Path(dst).write_text(text)
    Path(dside).write_text(json.dumps(side, separators=(",", ":")) + "\n")

    def hops(rows, tn):
        return max([x["hop_um"] for x in rows if x["type"] == tn] or [0])

    rep = dict(rule="COORD 11-01 15:5x: slice_station N/S landing bank >= 150 um from a feedthrough-column edge "
                    "(class = bank band within 150 um of a side ft LANDING column); same-shape band move, hop <= 402.84",
               gap_um=GAP, reach_um=round(REACH, 3), changed_types=sorted({m["type"] for m in moved}), moved=moved,
               exceptions=exceptions,
               max_hop_um={tn: dict(before=hops(before, tn), after=hops(after, tn),
                                    all_bands_before=max(b["max_pin_to_band_hop_um"] for b in
                                                         orig["partition_types"][tn]["clock"]["landing_contract"]["bands"].values()),
                                    all_bands_after=max(b["max_pin_to_band_hop_um"] for b in
                                                        raw["partition_types"][tn]["clock"]["landing_contract"]["bands"].values()))
                           for tn in sorted({m["type"] for m in moved})},
               out_only_unchanged=[dict(r, measured=MEASURED_CLEAN_OUT_ONLY.get(r["type"], "unmeasured (same out-only form)"))
                                   for r in watch],
               census_before=before, census_after=[r for r in after if (r["type"], r["bus"]) in mv])
    Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    for m in moved:
        print(m["type"], m["bus"], m["old_rect_um"], "->", m["new_rect_um"], "hop", m["old_hop_um"], "->",
              m["new_hop_um"], "detour", m["detour_um"], "cap", m["capacity_flops"], m["flops_est"])
    print("exceptions", exceptions)
    print("out-only <150 unchanged", [(r["type"], r["bus"], r["out_only_col"]) for r in watch])


if __name__ == "__main__":
    main()
