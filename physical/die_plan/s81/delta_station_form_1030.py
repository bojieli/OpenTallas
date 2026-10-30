#!/usr/bin/env python3
"""DIE-S81-36/STFORM 10-30: S81 post-freeze class fix "station form" (COORD RULING 2026-10-30 12:25), applied per
slice_station TYPE.  Outlines, pins, windows, buses, partitions and every non-station type are unchanged (exact JSON
equality asserted).

(a) 5-point form for every UNLANDED ft slot (no fclk_in_<slot>_i landing ring).  Before, stage 0 registered the in
    face and stages j = 1..k-1 sat at L*j/k, so the out pins were one spacing (300-390 um) past the last register
    (AUTO-GEOM R2 pin_reg_p90 310-378 um vs 30).  Now stations k -> k+1: the old stages keep their places (explicit
    bit sites where the slot had them, else check.py's own per-bit route points L_b*j/k) and the new last stage k is
    an out-face register per bit, sited next to its out pin.  This adds +1 crossing cycle on the slot's lanes
    (accepted under METHODOLOGY 12.15c; TOK-12 prices it).  Hops stay <= L/k.  Every stage of a changed slot gets
    per-bit sites (RowAllocator 1.404 x 0.27 on the 2.16 x 0.27 lattice, as ft_sites_unblock.py), and regs_um = the
    in-window face centre + the per-stage site centroids, so the tap planner (taps.planned_sinks) sees the real form.
    Landed slots (ring + k stations ending at the out face) are already 5-point and stay unchanged.
(b) Clock taps follow the ft columns: every station type takes clock.tap_mode "density" (taps from the planned
    face / ft-stage sinks, <= 600 per tap target, 1500 cap, radius 150 um, the t23/t46 settings) with
    clock.control_sinks (reset in/out pin registers) and clock.sink_sites_um = the landing-contract control pins
    (cland_* ready/fault registers), whose registers the t23/t46 sited canary left 641-1043 um from any tap.
    Forwarded out clocks (landing_contract fclk_out_*) re-pick their source tap = the nearest new tap (the
    clock_landing_plan._finish rule).
usage (repo root): delta_station_form_1030.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT))
import check as C  # noqa: E402
import schema as S  # noqa: E402
from gen_phys import type_pins, clock_pins  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compact_plan as CP  # noqa: E402

CELL = (1.404, 0.27)
PREFIX = "slice_station"
CLOCK = dict(tap_mode="density", tap_target_sinks=600, tap_max_sinks=1500, tap_radius_um=150.0)
SMAX = 405.0
FACE_INSET = 2.0


CHUNK = 16   # consecutive bits sited together (one bulk RowAllocator call per chunk): pins / parallel routes of one
             # chunk span a few um, so each bit stays within a few um of its own target


def alloc_bits(al, targets, radius):
    """lower-left sites for per-bit targets [(x, y)], in bit order: chunks of CHUNK consecutive bits are allocated in
    bulk around the chunk centroid and matched to their targets along the chunk's spread axis."""
    out = []
    for c0 in range(0, len(targets), CHUNK):
        tg = np.array(targets[c0:c0 + CHUNK], dtype=float)
        q, _ = al.allocate(tg.mean(axis=0), len(tg), max_radius_um=radius)
        ax = 0 if np.ptp(tg[:, 0]) >= np.ptp(tg[:, 1]) else 1
        oq = np.lexsort((q[:, 1 - ax], q[:, ax]))
        ot = np.lexsort((tg[:, 1 - ax], tg[:, ax]))
        got = [None] * len(tg)
        for a, b in zip(ot, oq):
            got[a] = [round(float(q[b][0] - CELL[0] / 2), 6), round(float(q[b][1] - CELL[1] / 2), 6)]
        out += got
    return out


def landed(t, s):
    ck = t.get("clock", {})
    ports = {e["port"] for e in ck.get("edge_clocks", [])}
    ports |= {p["name"] for p in ck.get("landing_contract", {}).get("pins", []) if p.get("dir") == "in"}
    return f"fclk_in_{s['name']}_i" in ports


def inset(p):
    x, y, face = p
    return {"E": (x - 1, y), "W": (x + 1, y), "N": (x, y - 1), "S": (x, y + 1)}[face]


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def win_centre(t, s, key, face):
    w, h = t["outline_um"]
    a = sum(s[key]) / 2
    return [0.0 if face == "W" else w, round(a, 6)] if face in "EW" else [round(a, 6), 0.0 if face == "S" else h]


def face_point(x, y, w, h):
    face = min(((x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")))[1]
    return {"W": (FACE_INSET, y), "E": (w - FACE_INSET, y), "S": (x, FACE_INSET), "N": (x, h - FACE_INSET)}[face]


def fix_type(P, raw, tn, rep):
    t = raw["partition_types"][tn]
    W, H = t["outline_um"]
    pins = {}
    for bus, bit, _l, x, y, face in type_pins(P, tn):
        pins.setdefault(bus, {})[bit] = (x, y, face)
    gate = list(S.placed_macro_boxes(t, halo=0.0).values())
    grow = [(x0 - 4.32, y0 - 4.32, x1 + 4.32, y1 + 4.32) for x0, y0, x1, y1 in gate]
    al = RowAllocator((4.32, 4.32, W - 4.32, H - 4.32), blocked=grow, cell_size=CELL, column_pitch=2.16,
                      row_pitch=.27, origin=(4.32, 4.32))
    for s in t["ft_slots"]:
        for st in s.get("bit_sites_um") or []:
            for x, y in st:
                al.reserve_rectangle((x, y, x + CELL[0], y + CELL[1]))
    todo = [s for s in t["ft_slots"] if not landed(t, s)]
    # out-face registers first (each bit next to its own pin), then the interior stages of slots without sites
    plan = {}
    for s in sorted(todo, key=lambda s: (-s["width"], s["name"])):
        name, k = s["name"], int(s.get("stations", 1))
        pi, po = pins[name + "_i"], pins[name + "_o"]
        bits = sorted(set(pi) | set(po))
        if len(bits) != s["width"] + 1:
            raise SystemExit(f"{tn}/{name}: {len(bits)} pin bits != width+1 {s['width'] + 1}")
        geo = {}
        for b in bits:
            A, B = pi.get(b) or po[b], po.get(b) or pi[b]
            ia, ib = inset(A), inset(B)
            r = C.zroute(ia, ib, A[2], B[2])
            geo[b] = (ia, ib, r, C.plen(r))
        last = alloc_bits(al, [geo[b][1] for b in bits], 40.)
        plan[name] = (s, k, bits, geo, last)
    for name, (s, k, bits, geo, last) in sorted(plan.items(), key=lambda kv: (-kv[1][0]["width"], kv[0])):
        if s.get("bit_sites_um"):
            inner = [list(map(list, st)) for st in s["bit_sites_um"]]
        else:
            regs = s.get("regs_um") or []
            inner = []
            for j in range(1, k):
                tg = [tuple(regs[j]) if len(regs) >= k else C.point_at(geo[b][2], geo[b][3] * j / k) for b in bits]
                inner.append(alloc_bits(al, tg, 60.))
        sites = inner + [last]
        worst, preg = 0.0, []
        for i, b in enumerate(bits):
            ia, ib = geo[b][0], geo[b][1]
            ch = [ia] + [(st[i][0] + CELL[0] / 2, st[i][1] + CELL[1] / 2) for st in sites]
            worst = max(worst, max(man(u, v) for u, v in zip(ch, ch[1:])))
            preg.append(man(ch[-1], ib))
        if worst > SMAX:
            raise SystemExit(f"{tn}/{name}: hop {worst:.1f} > {SMAX}")
        regs = [win_centre(t, s, "in_window_um", s["in_face"])]
        for st in sites:
            a = np.array(st) + np.array(CELL) / 2
            regs.append([round(float(v), 4) for v in a.mean(axis=0)])
        old = dict(stations_before=k, sited=bool(s.get("bit_sites_um")), regs=bool(s.get("regs_um")))
        s["stations"] = k + 1
        s["regs_um"] = regs
        s["bit_site_cell_um"] = list(CELL)
        s["bit_sites_um"] = sites
        rep["slots"].append(dict(type=tn, slot=name, width=s["width"], stations_after=k + 1, **old,
                                 max_hop_um=round(worst, 1), out_pin_reg_p90=round(float(np.quantile(preg, .9)), 2),
                                 out_pin_reg_max=round(max(preg), 2)))
    ck = t["clock"]
    ck.update(CLOCK)
    lc = ck.get("landing_contract", {}).get("pins", [])
    ss = [[round(v, 4) for v in face_point(p["xy_um"][0], p["xy_um"][1], W, H)] + [1]
          for p in lc if p.get("kind") != "clock"]
    if ss:
        ck["sink_sites_um"] = ss
    else:
        ck.pop("sink_sites_um", None)
    rep["_arst"][tn] = (raw.get("reset", {}).get("in_sites") or {}).get(tn)


_P2 = None


def _type_density(tn):
    import taps as TP
    return [tuple(r[:3]) for r in TP.density_taps(_P2, tn, control=False)]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    raw = json.load(open(src))
    orig = copy.deepcopy(raw)
    P = S.Plan(raw)
    rep = dict(slots=[], types={}, _arst={})
    types = sorted(tn for tn in raw["partition_types"] if tn.startswith(PREFIX))
    if os.environ.get("STFORM_ONLY"):          # debug / estimate subset (the plan of record uses every station type)
        types = [tn for tn in types if tn in os.environ["STFORM_ONLY"].split(",")]
    for tn in types:
        fix_type(P, raw, tn, rep)
        print("sited", tn, flush=True)
    # (b) taps.  Density taps over the planned sinks are computed ONCE here (minutes per type: one forked worker
    # per type, control pins as plain sink rows: the reset IN site reset.in_sites[type] + the landing control pins)
    # and then FROZEN as an explicit tap table (clock.tap_mode "explicit" + control_sinks: taps.explicit_tap_sites /
    # explicit_taps -- the documented way to materialise a density table, so the die reset solve and every kit read
    # fixed endpoints instead of re-running the density solver for 46 types).  Any actual control-pin sink (reset
    # out pins solved on the frozen taps) beyond tap_radius_um gets one light tap at the pin (legalised), iterated.
    global _P2
    for tn in types:
        if rep["_arst"].get(tn):
            ck = raw["partition_types"][tn]["clock"]
            ck.setdefault("sink_sites_um", []).append([float(v) for v in rep["_arst"][tn]] + [1])
    _P2 = S.Plan(raw)
    import multiprocessing as mp
    with mp.get_context("fork").Pool(min(len(types), int(os.environ.get("STFORM_JOBS", "48")))) as pool:
        got = dict(zip(types, pool.map(_type_density, types)))
    for tn in types:
        ck = raw["partition_types"][tn]["clock"]
        if rep["_arst"].get(tn):
            ck["sink_sites_um"].pop()
            if not ck["sink_sites_um"]:
                ck.pop("sink_sites_um")
        ck["tap_mode"] = "explicit"
        ck["control_sinks"] = True
        order = sorted(got[tn], key=lambda r: 0 if r[0] == "clk" else int(r[0][5:]))
        assert [r[0] for r in order] == ["clk"] + [f"clk_t{i}" for i in range(1, len(order))], order
        ck["taps"] = [dict(name=n, xy=[round(x, 4), round(y, 4)]) for n, x, y in order]
    import taps as TP
    for it in range(4):
        P3 = S.Plan(raw)
        added = 0
        for tn in types:
            ck = raw["partition_types"][tn]["clock"]
            txy = [tuple(p["xy"]) for p in ck["taps"]]
            far = [(x, y) for x, y, w in TP.sink_sites(P3, tn)
                   if w > 0 and min(abs(x - a) + abs(y - b) for a, b in txy) > CLOCK["tap_radius_um"]]
            for x, y in far:
                if min(abs(x - a) + abs(y - b) for a, b in txy) <= CLOCK["tap_radius_um"]:
                    continue
                w, h = raw["partition_types"][tn]["outline_um"]
                q = S.tap_clear(raw["partition_types"][tn], min(max(x, TP.TAP_MARGIN_UM), w - TP.TAP_MARGIN_UM),
                                min(max(y, TP.TAP_MARGIN_UM), h - TP.TAP_MARGIN_UM), txy, strict=True)
                q = (round(q[0], 4), round(q[1], 4))
                ck["taps"].append(dict(name=f"clk_t{len(ck['taps'])}", xy=list(q)))
                txy.append(q)
                added += 1
                rep["types"].setdefault(tn, {}).setdefault("light_taps", []).append(dict(sink=[x, y], tap=list(q)))
        print("control-tap pass", it, "added", added, flush=True)
        if not added:
            break
    else:
        raise SystemExit("control taps did not converge")
    P3 = S.Plan(raw)
    for tn in types:
        t = raw["partition_types"][tn]
        fin = TP.explicit_taps(P3, tn)       # full budget: every data + control sink, load <= cap, radius <= 150
        roots = clock_pins(P3, tn)
        moved = []
        for p in t["clock"].get("landing_contract", {}).get("pins", []):
            if p.get("kind") == "clock" and p.get("dir") == "out" and "source_clock_port" in p:
                tap = min(roots, key=lambda r: abs(r[1] - p["xy_um"][0]) + abs(r[2] - p["xy_um"][1]))[0]
                if tap != p["source_clock_port"]:
                    moved.append(f"{p['name']}:{p['source_clock_port']}->{tap}")
                p["source_clock_port"] = tap
        r = rep["types"].setdefault(tn, {})
        r.update(taps=len(fin), tap_load_max=max(q[3] for q in fin), tap_radius_max=max(q[4] for q in fin),
                 source_retap=moved)
        print("taps", tn, r["taps"], r["tap_load_max"], r["tap_radius_max"], flush=True)
    rep.pop("_arst")
    for tn in raw["partition_types"]:
        if tn not in types:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    # lane latency table (+1 cycle per crossed unlanded slot, priced for TOK-12): gen.latency_table, as prepare_h2_2249
    import gen
    newP = S.Plan(raw)
    raw["latency"]["lanes"] = gen.latency_table(newP)
    rep["latency"] = [dict(lane=lid, old=orig["latency"]["lanes"][lid]["cycles"], new=v["cycles"],
                           added_cycles=v["cycles"] - orig["latency"]["lanes"][lid]["cycles"])
                      for lid, v in raw["latency"]["lanes"].items()
                      if v["cycles"] != orig["latency"]["lanes"].get(lid, {}).get("cycles")]
    assert set(raw["latency"]["lanes"]) == set(orig["latency"]["lanes"])
    for x in rep["latency"]:          # every other changed field of a repriced lane, for the record
        a, b = orig["latency"]["lanes"][x["lane"]], raw["latency"]["lanes"][x["lane"]]
        x["fields"] = {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}
    for lid, v in raw["latency"]["lanes"].items():
        if v["cycles"] == orig["latency"]["lanes"][lid]["cycles"]:
            assert v == orig["latency"]["lanes"][lid], lid
    for k in raw:
        if k not in ("partition_types", "latency"):
            assert raw[k] == orig[k], k
    assert set(raw["latency"]) == set(orig["latency"])
    for tn in types:
        a, b = raw["partition_types"][tn], orig["partition_types"][tn]
        assert a["outline_um"] == b["outline_um"] and a.get("buses") == b.get("buses"), tn
        for x, y in zip(a["ft_slots"], b["ft_slots"]):
            for key in ("name", "in_face", "out_face", "width", "in_window_um", "out_window_um", "order", "layers"):
                assert x.get(key) == y.get(key), (tn, x["name"], key)
    # splice only the station type blocks into the original text (rest of the file byte-identical)
    text = open(src).read()
    for tn in types:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        assert m, tn
        _, j = json.JSONDecoder().raw_decode(text, m.end())
        text = text[:m.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    m = re.search(r'^ "latency": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    text = text[:m.end()] + CP._d(raw["latency"], 1) + text[j:]
    assert json.loads(text) == raw
    open(dst, "w").write(text)
    rep["summary"] = dict(types=len(types), slots_changed=len(rep["slots"]),
                          added_stage_bits=sum(s["width"] + 1 for s in rep["slots"]),
                          max_hop_um=max(s["max_hop_um"] for s in rep["slots"]),
                          worst_out_pin_reg_p90=max(s["out_pin_reg_p90"] for s in rep["slots"]),
                          worst_out_pin_reg_max=max(s["out_pin_reg_max"] for s in rep["slots"]))
    rep["summary"].update(lanes_repriced=len(rep["latency"]),
                          added_cycles_max=max((x["added_cycles"] for x in rep["latency"]), default=0))
    print(json.dumps(rep["summary"]))
    if len(sys.argv) > 3:
        json.dump(rep, open(sys.argv[3], "w"), indent=1)


if __name__ == "__main__":
    main()
