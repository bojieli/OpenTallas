#!/usr/bin/env python3
"""KITS-SPARE-2 batched S81 plan delta (COORD rulings 2026-10-25 10:23 items 2, 4, 5).

(2) Large hard cores publish their core clock latency (owner MSCTS "core latency", core_clock_contract): the parent
    type gets an EARLY core tap (clock.core_taps 'early', schema.core_taps) for the core, so the spine delivers the
    core's clock (insertion_ps - common latency) early and the core's flops see the common latency.  No split.
      bk_sel__t2  u_bk_sel.u_sel.u_c  dsdv_bksel_c   BUDGET TT 430 (KITS-SPARE rt42s CTS 401/426/446)
      gunit__t1   u_gunit.u_l5        dsdv_gunit_l5  BUDGET TT 520 (KITS-SPARE/L5 rtA 496/518/576, rtB 505/524/583)
    These are budgets (placement-RC CTS, not SIGNED); the core's SIGNED TT pin-register mean replaces them
    (early_core_taps.add_from_means) before the parent signs off.
(4) ot_s81sl_xrt3 outline 570.24x395.28 (5.8% fill, GEOM-REVIEW-3 06:20 FAIL-F5+outline) -> 207.36x164.16 (~38% of the
    measured 13,083 um2 placed cell area).  Pin-limited core (9122 pins): N/S keep M3+M5, E/W go 2-layer M4+M6;
    every face keeps its pins and group order, re-spread uniformly, alternate layers, snapped to the plan tracks.
    Placed in the parent slot centred in x, its S (R0) face edge on the cap/xfin top line (MX parent).
(5) slice_station t23/t46: clock taps follow the station band -- tap_mode 'density' (taps at the sink sites: ft
    station banks + face pin registers, none empty, no grid), and the ft banks get fixed Manhattan knee sites
    (tools/die_plan/ft_knee_sites.py, merged a9417c88c2) so every bank is a compact row and a tap sits on it.
    t46: 0 added cycles.  t23: 0 added cycles (arclength station targets, ft_knee_sites).
Idempotent.  usage: delta_kitsspare2_1025.py LEDGER.json"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(W / "tools/die_plan"))
import compact_plan  # noqa: E402

PLAN = HERE / "die_plan.json"

CORE_LAT = {
    ("bk_sel__t2", "u_bk_sel.u_sel.u_c", "dsdv_bksel_c"): (430.0, "BUDGET KITS-SPARE rt42s CTS TT 401/426/446 "
                                                           "(placement RC; FF ~350); SIGNED TT pin-reg mean replaces it"),
    ("gunit__t1", "u_gunit.u_l5", "dsdv_gunit_l5"): (520.0, "BUDGET KITS-SPARE/L5 rtA 496/518/576 rtB 505/524/583 "
                                                     "(placement RC; FF ~430); SIGNED TT pin-reg mean replaces it"),
}
XRT3 = "ot_s81sl_xrt3"
XRT3_OLD = [570.24, 395.28]
XRT3_NEW = [207.36, 164.16]
# t23: coll-lanes option A is on HOLD (PATH-S81 10:42: the C hop is a bind-map artifact, lanes stay) -> t23 is
# re-planned here; ft_knee_sites arclength candidates keep all 4 slots at their old depth (0 added cycles).
STATION_TYPES = ("slice_station__t23", "slice_station__t46")
TRACK = {"M3": (0.009, 0.036), "M4": (0.024, 0.048), "M5": (0.024, 0.048), "M6": (0.032, 0.064)}
FACE_LAYERS = {"N": ("M3", "M5"), "S": ("M3", "M5"), "E": ("M4", "M6"), "W": ("M4", "M6")}
MARGIN = 6.48


def core_taps(raw, rep):
    import schema as S
    for (tn, inst, mod), (ps, why) in CORE_LAT.items():
        t = raw["partition_types"][tn]
        c = next(h for h in t["hard_cores"] if h["inst"] == inst)
        assert c["module"] == mod, (tn, inst, c["module"])
        pins = json.loads((HERE / c["pins_file"]).read_text())["pins"] if c.get("pins_file") else c.get("pins", [])
        ck = [p for p in pins if re.fullmatch(r"(clk|ck)(\[0\])?", p["name"])]
        assert len(ck) == 1, (mod, ck)
        px, py = ck[0]["x"], ck[0]["y"]
        w, h = c["outline_um"]
        o = c.get("orient", "R0")
        if o in ("MY", "R180"):
            px = w - px
        if o in ("MX", "R180"):
            py = h - py
        x0, y0 = c["origin_um"]
        dx, dy = c.get("track_offset_um", [0.0, 0.0])
        clock = t.setdefault("clock", {})
        if any(tp.get("name") == inst and tp.get("insertion_ps") == ps for tp in clock.get("taps", [])):
            continue                                      # already applied (idempotent re-run)
        others = [tp for tp in clock.get("taps", []) if tp.get("name") != inst]
        xy = S.tap_clear(t, x0 + dx + px, y0 + dy + py, [tp["xy"] for tp in others], clear=4.32)
        tap = dict(name=inst, kind="core", xy=[round(xy[0], 4), round(xy[1], 4)], insertion_ps=ps,
                   insertion_tol_ps=40.0, budget_owner="KITS-SPARE-2 plan delta 1025 (core-clock-contract BUDGET)",
                   note=f"COORD 10:23 ruling 2: published core latency, parent tap advanced; {why}")
        clock["core_taps"] = "early"
        clock["taps"] = others + [tap]
        rep.setdefault("core_taps", []).append(dict(type=tn, inst=inst, module=mod, clk_pin=ck[0]["name"],
                                                    tap_xy=tap["xy"], insertion_ps=ps,
                                                    early_ps=ps - float(raw["clock"]["insertion_ps"])))


def _face(p, w, h):
    d = {"S": p["y"], "N": h - p["y"], "W": p["x"], "E": w - p["x"]}
    return min(d, key=d.get)


def _snap(v, layer, lo, hi, used, frame):
    off, pitch = TRACK[layer]
    off = frame(layer, off, pitch)
    k = round((v - off) / pitch)
    for dk in sorted(range(-40, 41), key=lambda d: (abs(d), d)):
        q = round(off + (k + dk) * pitch, 4)
        if lo <= q <= hi and (layer, q) not in used:
            used.add((layer, q))
            return q
    raise ValueError(f"no free {layer} track near {v}")


def xrt3_pins(path, old, new, place):
    d = json.loads(path.read_text())
    ps = d["pins"]
    ow, oh = old
    nw, nh = new
    faces = {}
    for p in ps:
        faces.setdefault(_face(p, ow, oh), []).append(p)
    rep = {}
    for f, fp in faces.items():
        along = "x" if f in "NS" else "y"
        L = nw if f in "NS" else nh
        fp.sort(key=lambda p: (p[along], p["name"]))
        n = len(fp)
        lo, hi = MARGIN, L - MARGIN
        step = (hi - lo) / max(1, n - 1)
        used = set()
        lays = FACE_LAYERS[f]
        (ox, oy), (dx, dy), orient = place
        # core-frame track offset so the pin sits on the plan track in the PARENT TYPE frame (origin + track_offset,
        # MX flips y: type y = oy + dy + nh - y)
        if along == "x":
            fr = lambda l_, o, pt: (o - ox - dx) % pt
        elif orient == "MX":
            fr = lambda l_, o, pt: (oy + dy + nh - o) % pt
        else:
            fr = lambda l_, o, pt: (o - oy - dy) % pt
        for i, p in enumerate(fp):
            lay = lays[i % 2] if p["name"] not in ("clk", "rst_n") else lays[0]
            p["layer"] = lay
            p[along] = _snap(lo + i * step, lay, lo, hi, used, fr)
            inset = 0.019 if lay == "M3" else 0.042          # the table's own per-layer pin-centre inset
            perp = "y" if f in "NS" else "x"
            p[perp] = round({"S": inset, "W": inset, "N": nh - inset, "E": nw - inset}[f], 3)
        per = {l_: sum(1 for p in fp if p["layer"] == l_) for l_ in lays}
        rep[f] = dict(pins=n, face_um=L, per_layer=per, pins_per_um_per_layer=round(max(per.values()) / (hi - lo), 2))
    d["source"] = (d.get("source", "") + "; KITS-SPARE-2 10-25: outline 570.24x395.28 -> "
                   f"{nw}x{nh} (COORD ruling 4), faces re-spread in order, 2 layers per face").lstrip("; ")
    import hashlib
    d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
    path.write_text(json.dumps(d, indent=0) + "\n")
    return rep


def xrt3(raw, rep):
    hits = [(tn, c) for tn, t in raw["partition_types"].items() for c in t.get("hard_cores", []) if c.get("module") == XRT3]
    assert hits, "no xrt3"
    out = []
    for tn, c in hits:
        if c["outline_um"] == XRT3_NEW:
            c["obs_max"] = "M6"
            out.append(dict(type=tn, inst=c["inst"], origin=c["origin_um"], already=True))
            continue
        assert c["outline_um"] == XRT3_OLD, c["outline_um"]
        x0, y0 = c["origin_um"]
        ow, oh = XRT3_OLD
        nw, nh = XRT3_NEW
        nx = x0 + round((ow - nw) / 2 / 8.64) * 8.64
        t = raw["partition_types"][tn]
        tops = [h["origin_um"][1] + h["outline_um"][1] for h in t["hard_cores"] if h["inst"] != c["inst"]
                and h["origin_um"][1] + h["outline_um"][1] <= y0 + oh + 1e-6 and h["origin_um"][1] + h["outline_um"][1] > y0]
        if c.get("orient") == "MX":      # R0 S face = parent top edge: keep it on the neighbours' top line
            top = max(tops) if tops else y0 + oh
            ny = top - nh
        else:                            # R0 S face = parent bottom edge: keep it
            ny = y0
        c["origin_um"] = [round(nx, 4), round(ny, 4)]
        c["outline_um"] = list(XRT3_NEW)
        c["obs_max"] = "M6"          # E/W 2-layer faces (M4+M6 pin grant): the core obstructs M1..M6
        out.append(dict(type=tn, inst=c["inst"], old_origin=[x0, y0], origin=c["origin_um"], orient=c.get("orient")))
    pf = HERE / hits[0][1]["pins_file"]
    d = json.loads(pf.read_text())
    if max(p["x"] for p in d["pins"]) > XRT3_NEW[0] + 1:
        c0 = hits[0][1]
        assert all(c["origin_um"] == c0["origin_um"] and c.get("orient") == c0.get("orient") for _, c in hits)
        rep["xrt3_pins"] = xrt3_pins(pf, XRT3_OLD, XRT3_NEW, (c0["origin_um"], c0.get("track_offset_um", [0, 0]),
                                                           c0.get("orient", "R0")))
    rep["xrt3"] = out
    rep["xrt3_fill"] = round(13083.0 / (XRT3_NEW[0] * XRT3_NEW[1]), 4)


def stations(raw, rep):
    import ft_knee_sites as K
    todo = [tn for tn in STATION_TYPES if not all("bit_sites_um" in s for s in raw["partition_types"][tn]["ft_slots"])]
    if todo:
        rep["knee"] = K.place(raw, todo)
        assert all(r["added_cycles"] == 0 for r in rep["knee"]), [(r["type"], r["slot"], r["added_cycles"]) for r in rep["knee"]]
    for tn in STATION_TYPES:
        ck = raw["partition_types"][tn].setdefault("clock", {})
        ck["tap_mode"] = "density"
        # one tap per station bank (515 sinks) / pin-register strip: target below one bank so two banks never share
        ck["tap_target_sinks"] = 600
        ck["tap_max_sinks"] = 1500
        ck["tap_radius_um"] = 150.0
    rep["station_clock"] = {tn: raw["partition_types"][tn]["clock"] for tn in STATION_TYPES}


def main():
    raw = json.loads(PLAN.read_text())
    rep = {}
    core_taps(raw, rep)
    xrt3(raw, rep)
    stations(raw, rep)
    PLAN.write_text(compact_plan.dumps(raw))
    Path(sys.argv[1]).write_text(json.dumps(rep, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("knee", "station_clock")}, default=str)[:3000])


if __name__ == "__main__":
    main()
