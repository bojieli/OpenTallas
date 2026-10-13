#!/usr/bin/env python3
"""Exact pin plan of the flat HBM B2 IDX wide adapter tile ot_hgi_idx_index_w (ref_tile kit idxw_b2, M5 leaf cap).

Why (el1013-idxw-v3, 2026-10-13): idxw_b2-v2 died in IO placement (PPL-0111).  Under the M5 cap a W/E face has ONE pin
layer (M4): 211.68 um / (2 x 0.048 um) = 2,190 placer slots, and the v2 plan asked W for the whole read group (2,194)
and E for the whole write group (2,258).  The write request bus alone (8 x 280 = 2,240) cannot sit on one M4 face at 2
tracks a pin (215.0 um > 211.68 um), while N / S carry two pin layers (M3 + M5) and S held only the 235 command pins.
Plan by bit count, outline unchanged (211.68 um square), every pin on its layer's track, >= 2 tracks between pins:
  W  M4       read group, lane-coherent: per lane b {wrq[16b +: 16], wrq_cr[b], wrr[257b +: 257]} = 274 pins = 26.3 um
              (8 lanes; rg_req / rg_gnt between lanes 3 and 4): 2,194 pins at exactly 2 tracks (0.096 um)
  S  M3 + M5  write group, lane-coherent: per lane b {wwq[280b +: 280], wwq_cr[b], wwq_done[b]} = 282 pins = 24.9 um
              (wg_req / wg_gnt between lanes 3 and 4): 2,258 pins, layers alternating, x 6 .. 205.68 um
  N  M3 + M5  native selector (fs, kin, qb, qbr, to, toc, co, coc, ev): 2,172 pins, layers alternating, x 6 .. 205.68 um
  E  M4       frame command from the record station + clk / rst_n + done / fault: 235 pins at 11 tracks, y 42 .. 170 um
An M5 pin never sits on a track under the kit's M5 PG stripes (pdn.tcl: pitch 5.4, VSS / VDD pair at core + 0.24 ..
0.552 um); such a pin takes the next free M3 track instead.

  python3 physical/ref_tile_specs/hbm_idx/idxw_b2_pin_plan.py [--check]   -> idxw_b2_pins.tcl + idxw_b2_pins.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = H = 211.68
CORE0 = 2.16
NL = 8
TRK = {"M3": (0.009, 0.036), "M4": (0.012, 0.048), "M5": (0.012, 0.048)}       # asap7 (offset, pitch) across the layer
SIZE = {"M3": "0.018 0.144", "M4": "0.192 0.024", "M5": "0.024 0.192"}
MIN_TRACKS = 2
PG_PITCH, PG_LO, PG_HI, PG_CLEAR = 5.4, 0.24, 0.552, 0.12                        # M5 stripe pair window from the core edge


def bus(name, n, lo=0):
    return [f"{name}[{i}]" for i in range(lo, lo + n)]


def ports():
    w = []
    for b in range(NL):
        if b == NL // 2:
            w += ["rg_req", "rg_gnt"]
        w += bus("wrq", 16, 16 * b) + [f"wrq_cr[{b}]"] + bus("wrr", 257, 257 * b)
    s = []
    for b in range(NL):
        if b == NL // 2:
            s += ["wg_req", "wg_gnt"]
        s += bus("wwq", 280, 280 * b) + [f"wwq_cr[{b}]", f"wwq_done[{b}]"]
    n = bus("fs", 90) + bus("kin", 345) + bus("qb", 1048) + ["qbr"] + bus("to", 612) + ["toc"] + bus("co", 72) + ["coc"] + bus("ev", 2)
    e = (bus("a_base_i", 18) + bus("b_base_i", 18) + bus("c_base_i", 18) + bus("c_stride_i", 18) + bus("c_n_i", 12)
         + bus("k_i", 12) + ["cand_en_i", "keep_en_i", "has_r_i", "go_i", "clk", "rst_n", "done", "fault"]
         + bus("rank_i", 7) + bus("pos_i", 20) + bus("n_i", 32)
         + bus("o_base_i", 18) + bus("r_base_i", 18) + bus("d_base_i", 18) + bus("d_stride_i", 18))
    return {"W": w, "S": s, "N": n, "E": e}


def track(layer, k):
    o, p = TRK[layer]
    return round(o + p * k, 3)


def k_at(layer, x):          # first track index at or after x
    o, p = TRK[layer]
    k = int((x - o) / p)
    while track(layer, k) < x - 1e-9:
        k += 1
    return k


def under_pg(x):
    r = (x - CORE0) % PG_PITCH
    return PG_LO - PG_CLEAR <= r <= PG_HI + PG_CLEAR or r >= PG_PITCH + PG_LO - PG_CLEAR


def plan_h(names, lo, step_tracks):
    """one M4 layer, constant pitch (W / E faces): [(name, 'M4', y)]"""
    k0 = k_at("M4", lo)
    return [(nm, "M4", track("M4", k0 + step_tracks * i)) for i, nm in enumerate(names)]


def plan_v(names, lo, hi):
    """M3 + M5 alternating over [lo, hi] in port order, each layer >= MIN_TRACKS apart, M5 never under a PG stripe"""
    step = (hi - lo) / len(names)
    last = {"M3": None, "M5": None}
    out = []
    for i, nm in enumerate(names):
        x = lo + step * (i + 0.5)
        cands = []
        for layer in (("M5", "M3") if i % 2 else ("M3", "M5")):
            k = k_at(layer, x - TRK[layer][1] / 2)
            if last[layer] is not None:
                k = max(k, last[layer] + MIN_TRACKS)
            if layer == "M5":
                if under_pg(track(layer, k)):
                    continue
            cands.append((layer, k))
        layer, k = min(cands, key=lambda c: abs(track(*c) - x)) if len(cands) > 1 and abs(track(*cands[0]) - x) > 2 * step else cands[0]
        last[layer] = k
        out.append((nm, layer, track(layer, k)))
    return out


def build():
    p = ports()
    w = plan_h(p["W"], (H - (len(p["W"]) - 1) * 0.096) / 2 - 0.024, MIN_TRACKS)
    e = plan_h(p["E"], 42.0, 11)
    s = plan_v(p["S"], 6.0, W - 6.0)
    n = plan_v(p["N"], 6.0, W - 6.0)
    return {"W": w, "E": e, "S": s, "N": n}


def check(pl):
    seen = set()
    rep = {}
    for f, pins in pl.items():
        by = {}
        for nm, layer, c in pins:
            assert nm not in seen, nm
            seen.add(nm)
            o, pt = TRK[layer]
            assert abs(round((c - o) / pt) * pt + o - c) < 1e-6, (nm, layer, c, "off track")
            assert 0.5 < c < W - 0.5, (nm, c)
            assert layer == "M4" if f in "WE" else layer in ("M3", "M5"), (nm, layer)
            assert not (layer == "M5" and under_pg(c)), (nm, c, "under an M5 PG stripe")
            by.setdefault(layer, []).append(c)
        gaps = {}
        for layer, cs in by.items():
            cs = sorted(cs)
            g = min(round((b - a) / TRK[layer][1]) for a, b in zip(cs, cs[1:]))
            assert g >= MIN_TRACKS, (f, layer, g)
            gaps[layer] = dict(pins=len(cs), min_gap_tracks=g, lo=cs[0], hi=cs[-1])
        order = [c for _, _, c in pins]
        assert all(b > a - 0.3 for a, b in zip(order, order[1:])), (f, "port order not monotone along the face")
        rep[f] = dict(pins=len(pins), layers=gaps)
    assert len(seen) == 2194 + 2258 + 2172 + 235, len(seen)
    return rep


def tcl(pl):
    L = ["# generated by physical/ref_tile_specs/hbm_idx/idxw_b2_pin_plan.py -- do not edit; re-run it",
         "# idxw_b2 (ot_hgi_idx_index_w, M5 leaf cap, 211.68 um square): W M4 read group (lane-coherent, 2 tracks a pin),",
         "# S M3+M5 write group (lane-coherent), N M3+M5 native selector, E M4 frame command; M5 pins off the PG stripe tracks."]
    for f, pins in pl.items():
        for nm, layer, c in pins:
            loc = {"W": f"0.0 {c:.3f}", "E": f"{W:.2f} {c:.3f}", "S": f"{c:.3f} 0.0", "N": f"{c:.3f} {H:.2f}"}[f]
            L.append(f"place_pin -pin_name {{{nm}}} -layer {layer} -location {{{loc}}} -pin_size {{{SIZE[layer]}}} -force_to_die_boundary")
    return "\n".join(L) + "\n"


def main():
    pl = build()
    rep = check(pl)
    t = tcl(pl)
    j = json.dumps(dict(schema="opentallas.idxw_b2.pin_plan.v1", die=[0, 0, W, H], min_tracks=MIN_TRACKS, faces=rep,
                        v2_failure=dict(job="idxw_b2-v2-c08e87086", error="PPL-0111", slots_per_m4_face=2190,
                                        W=dict(group="VM wide read", pins=2194), E=dict(group="VM wide write", pins=2258))),
                   indent=1) + "\n"
    if "--check" in sys.argv:
        assert (HERE / "idxw_b2_pins.tcl").read_text() == t and (HERE / "idxw_b2_pins.json").read_text() == j, "stale pin plan"
    else:
        (HERE / "idxw_b2_pins.tcl").write_text(t)
        (HERE / "idxw_b2_pins.json").write_text(j)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
