#!/usr/bin/env python3
"""DIE-LAYOUT-HBM 11-11 (DIE-HBM-100 RE-FORM NW_io / NE_io, two strikes): cut each io type to logic + macro height and
move its long face-station chain into a new relay-column partition in the freed strip (die stays fully tiled).

Positions + partition split only; 0 cycles per lane: every station keeps its DIE position, the stations that fall above
the cut move from the io type's internal_stations row into the relay type's ft slot (count kept), so the lane's
ft-slot stations rise by k and its fixed_cycles fall by k (latency table cycles unchanged).
  NW_io  648 x 4320 -> 648 x H_NW; NW_iorly 648 x (4320 - H_NW) at (0, y0 + H_NW): slots L8007x0 (S->N, 641 b),
         L8008x8 (N->S, 632 b); NW_io's N-face L8007_o window moves to the station column x (it now faces NW_iorly),
         NW_iorly keeps the su01-facing windows (su01 untouched).
  NE_io  648 x 4320 -> 648 x H_NE; NE_iorly 648 x (4320 - H_NE): slot L8006x0 (S->W, 13 b); NE_io's L8006_o moves from
         the W face to the N face at the station column x; NE_iorly's W window = the old die position (NE_b013 untouched).
usage: io_reform.py PLAN_IN PLAN_OUT [H_NW H_NE]"""
import copy
import json
import sys

H_NW, H_NE = 1814.4, 1425.6
EXTRA_L8008 = 1
TAG = "DIE-LAYOUT-HBM IO-REFORM 11-11"
LAYERS_NS, LAYERS_EW = ["M7", "M5"], ["M6", "M4"]
WIN_W = 110.0        # um of face per 632/641-b bus on 2 layers: <= 6 pins/um (faces budget) on the faces this form owns
INSET = 4.0          # normal FT S0 = the input face (die_hop_scan.input_site); su01 uses 4 um


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def along(path, n_hops):
    """the n_hops - 1 interior points that cut the polyline into n_hops equal hops (+ the hop length)"""
    L = sum(dist(a, b) for a, b in zip(path, path[1:]))
    out = []
    for j in range(1, n_hops):
        s = L * j / n_hops
        for a, b in zip(path, path[1:]):
            d = dist(a, b)
            if s <= d + 1e-9:
                f = s / d if d else 0.0
                out.append([round(a[0] + f * (b[0] - a[0]), 3), round(a[1] + f * (b[1] - a[1]), 3)])
                break
            s -= d
    return out, L / n_hops


def relay_type(name, w, h, slots, note):
    return {"module": f"hbm_arch_{name}", "outline_um": [w, h], "hard": False,
            "face_layers": {"E": LAYERS_EW, "W": LAYERS_EW, "N": LAYERS_NS, "S": LAYERS_NS},
            "buses": [], "clock": {"tap_um": [round(w / 2, 2), round(h / 2, 2)], "layer": "M9", "insertion_ps": 250,
                                   "taps": []},
            "reset": {"tap_um": [round(w / 2, 2), round(h / 2, 2)], "sync_stages": 2},
            "contents": [{"inst": "u_ft", "module": f"hbm_arch_ft_{name}", "status": "new", "cells": 0,
                          "note": "transit only: ft stations + pin registers"}],
            "cells": 1000, "ft_slots": slots, "note": note}


def main(argv):
    P = json.load(open(argv[0]))
    hn, he = (float(argv[2]), float(argv[3])) if len(argv) > 3 else (H_NW, H_NE)
    T = P["partition_types"]
    parts = {p["name"]: p for p in P["partitions"]}
    ports = {p["id"]: p for p in P["ports"]}
    lanes = {l["id"]: l for l in P["lanes"]}
    rep = {}

    def split_row(tn, bus, H):
        t = T[tn]
        rows = [r for r in t["internal_stations"] if r["conn"] == f"bus:{bus}"]
        assert len(rows) == 1, (tn, bus, len(rows))
        r = rows[0]
        lo = [p for p in r["regs_um"] if p[1] < H - 20]
        hi = [p for p in r["regs_um"] if p[1] > H + 20]
        assert len(lo) + len(hi) == len(r["regs_um"]), f"{tn} {bus}: a station within 20 um of the cut {H}"
        return r, lo, hi

    out_types, new_parts = {}, []
    # ---------------- NW
    W0, H0 = T["NW_io"]["outline_um"]
    hr = round(H0 - hn, 3)
    r7, lo7, hi7 = split_row("NW_io", "L8007_o", hn)
    r8, lo8, hi8 = split_row("NW_io", "L8008_i", hn)
    assert not lo7 and not lo8, "NW: stations below the cut are not handled by this form"
    b7 = next(b for b in T["NW_io"]["buses"] if b["name"] == "L8007_o")
    b8 = next(b for b in T["NW_io"]["buses"] if b["name"] == "L8008_i")
    x7 = hi7[0][0]                                     # station column of L8007 (557.184)
    win7 = [round(x7 - WIN_W / 2, 4), round(x7 + WIN_W / 2, 4)]
    x8 = r8["to_um"][0]                                 # host_ep pin column (379.123)
    win8 = [round(x8 - WIN_W / 2, 4), round(x8 + WIN_W / 2, 4)]
    hr0 = H0 - hn
    # L8007: S0 at the S input face, then n7-1 stations to su01's L8007x1 S0 (its input face, (324, 4) su01-local)
    su_in = [(b7["window_um"][0] + b7["window_um"][1]) / 2, hr0 + INSET]
    n7 = len(hi7)
    # the real input bits spread over the WIN_W window: the first hop is measured from the window edge (+WIN_W/2)
    pts7, hop7 = along([[x7 - WIN_W / 2, INSET], [x7, INSET], [x7, hr0], [su_in[0], hr0], su_in], n7)
    regs7 = [[x7, INSET]] + pts7
    # L8008: S0 at the N input face, then stations down to u_host_ep's pin (below the S face in NW_io); one more station
    # than t19's 6 is needed for <= 405-um hops once S0 sits at the input face (t19: su01 last reg -> NW_io reg0 = 719 um)
    pin8 = [x8, -(hn - r8["to_um"][1])]
    n8 = len(hi8) + EXTRA_L8008
    pts8, hop8 = along([[x8, hr0 - INSET], [x8, 0.0], pin8], n8)
    regs8 = [[x8, round(hr0 - INSET, 3)]] + pts8
    s7 = {"name": "L8007x0", "in_face": "S", "out_face": "N", "width": b7["width"], "stations": n7,
          "in_window_um": win7, "in_layers": b7["layers"], "in_order": b7.get("order", "lsb_low"),
          "out_window_um": list(b7["window_um"]), "out_layers": b7["layers"], "out_order": b7.get("order", "lsb_low"),
          "regs_um": regs7,
          "note": f"{TAG}: NW_io L8007_o source stations moved here (count {n7} kept; S0 at the input face, hops {hop7:.0f} um)"}
    s8 = {"name": "L8008x8", "in_face": "N", "out_face": "S", "width": b8["width"], "stations": n8,
          "in_window_um": list(b8["window_um"]), "in_layers": b8["layers"], "in_order": b8.get("order", "lsb_low"),
          "out_window_um": win8, "out_layers": b8["layers"], "out_order": b8.get("order", "lsb_low"),
          "regs_um": regs8,
          "note": f"{TAG}: NW_io L8008_i receiver stations moved here ({len(hi8)} + {EXTRA_L8008}; S0 at the input face, "
                  f"hops {hop8:.0f} um)"}
    T["NW_iorly"] = relay_type("NW_iorly", W0, hr, [s7, s8],
                               f"{TAG}: relay column above NW_io (freed strip of the 648 x 4320 NW_io), transit only")
    b7["window_um"] = win7
    b8["window_um"] = win8
    t = T["NW_io"]
    t["internal_stations"] = [r for r in t["internal_stations"] if r is not r7 and r is not r8]
    t["outline_um"] = [W0, hn]
    t["note"] = str(t.get("note", "")) + f" | {TAG}: outline 648x4320 -> 648x{hn:g} (logic + macro height); the L8007/" \
        f"L8008 face stations moved to NW_iorly (die positions and counts kept)"
    pn = parts["NW_io"]
    new_parts.append({"name": "NW_iorly", "type": "NW_iorly", "origin_um": [pn["origin_um"][0], round(pn["origin_um"][1] + hn, 3)],
                      "orient": "R0"})
    # ports / lanes
    p0 = ports["L8007_0"]
    ports["L8007_0r"] = {"id": "L8007_0r", "src": {"part": "NW_iorly", "bus": "L8007x0_o"}, "dst": dict(p0["dst"]),
                         "width": p0["width"], "kind": p0["kind"]}
    p0["dst"] = {"part": "NW_iorly", "bus": "L8007x0_i"}
    lanes["L8007"]["ports"].insert(1, "L8007_0r")
    p7 = ports["L8008_7"]
    ports["L8008_8"] = {"id": "L8008_8", "src": {"part": "NW_iorly", "bus": "L8008x8_o"}, "dst": dict(p7["dst"]),
                        "width": p7["width"], "kind": p7["kind"]}
    p7["dst"] = {"part": "NW_iorly", "bus": "L8008x8_i"}
    lanes["L8008"]["ports"].append("L8008_8")
    rep["NW"] = dict(H=hn, relay_h=hr, L8007_slot=n7, L8007_hop=round(hop7, 1), L8008_slot=n8, L8008_hop=round(hop8, 1),
                     L8007_window=win7, L8008_window=win8)
    # ---------------- NE
    W0, H0 = T["NE_io"]["outline_um"]
    hr = round(H0 - he, 3)
    r6, lo6, hi6 = split_row("NE_io", "L8006_o", he)
    assert not lo6
    b6 = next(b for b in T["NE_io"]["buses"] if b["name"] == "L8006_o")
    x6 = hi6[0][0]
    w6 = b6["window_um"][1] - b6["window_um"][0]
    win6 = [round(x6 - w6 / 2, 4), round(x6 + w6 / 2, 4)]
    out6 = [0.0, round((b6["window_um"][0] + b6["window_um"][1]) / 2 - he, 3)]
    n6 = len(hi6)
    pts6, hop6 = along([[x6, INSET], [x6, out6[1]], out6], n6)
    regs6 = [[x6, INSET]] + pts6
    s6 = {"name": "L8006x0", "in_face": "S", "out_face": b6["face"], "width": b6["width"], "stations": len(hi6),
          "in_window_um": win6, "in_layers": LAYERS_NS, "in_order": "lsb_low",
          "out_window_um": [round(b6["window_um"][0] - he, 4), round(b6["window_um"][1] - he, 4)],
          "out_layers": b6["layers"], "out_order": b6.get("order", "lsb_low"),
          "regs_um": regs6,
          "note": f"{TAG}: NE_io L8006_o source stations moved here (count {n6} kept; S0 at the input face, hops {hop6:.0f} um)"}
    T["NE_iorly"] = relay_type("NE_iorly", W0, hr, [s6],
                               f"{TAG}: relay column above NE_io (freed strip of the 648 x 4320 NE_io), transit only")
    b6.update(face="N", window_um=win6, layers=LAYERS_NS, order="lsb_low")
    t = T["NE_io"]
    t["internal_stations"] = [r for r in t["internal_stations"] if r is not r6]
    t["outline_um"] = [W0, he]
    t["note"] = str(t.get("note", "")) + f" | {TAG}: outline 648x4320 -> 648x{he:g} (logic + macro height); the L8006 " \
        f"face stations moved to NE_iorly (die positions and count kept), L8006_o now on the N face"
    pn = parts["NE_io"]
    new_parts.append({"name": "NE_iorly", "type": "NE_iorly", "origin_um": [pn["origin_um"][0], round(pn["origin_um"][1] + he, 3)],
                      "orient": "R0"})
    p0 = ports["L8006_0"]
    ports["L8006_0r"] = {"id": "L8006_0r", "src": {"part": "NE_iorly", "bus": "L8006x0_o"}, "dst": dict(p0["dst"]),
                         "width": p0["width"], "kind": p0["kind"]}
    p0["dst"] = {"part": "NE_iorly", "bus": "L8006x0_i"}
    lanes["L8006"]["ports"].insert(1, "L8006_0r")
    rep["NE"] = dict(H=he, relay_h=hr, L8006_slot=n6, L8006_hop=round(hop6, 1), L8006_window=win6)
    # ---------------- type clock / reset taps off the hard cores (GEOM attempt_3: clock_on_macro): the t19 taps sit
    # inside u_ep_N0 / u_ep_N2; move them into the street between the cores (above the PHY PG rect, y >= 1088.64)
    for tn, xy in (("NW_io", [324.0, 1401.84]), ("NE_io", [324.0, 1380.24])):
        t = T[tn]
        for h in t["hard_cores"]:
            (x0, y0), (w, hh) = h["origin_um"], h["outline_um"]
            hal = h.get("halo_um", 0.0)
            assert not (x0 - hal < xy[0] < x0 + w + hal and y0 - hal < xy[1] < y0 + hh + hal), (tn, h["inst"], xy)
        rep[tn + "_tap"] = dict(old=t["clock"]["tap_um"], new=xy)
        t["clock"]["tap_um"] = list(xy)
        if t.get("reset", {}).get("tap_um") == rep[tn + "_tap"]["old"]:
            t["reset"]["tap_um"] = list(xy)
    # ---------------- latency bookkeeping: stations +k, fixed -k, cycles unchanged
    for lid, k, add in (("L8007", len(hi7), 0), ("L8008", len(hi8), EXTRA_L8008), ("L8006", len(hi6), 0)):
        ln = lanes[lid]
        ln["fixed_cycles"] = int(ln["fixed_cycles"]) - k
        ln["note"] = str(ln.get("note", "")) + f" | {TAG}: {k} io face stations moved into the relay-column ft slot " \
            f"(fixed_cycles -{k}, ft stations +{k + add}, cycles {'+%d' % add if add else 'unchanged'})"
        L = P["latency"]["lanes"][lid]
        L["stations"] += k + add
        L["fixed"] -= k
        L["cycles"] += add
        L["natural"] += add
        L["faces"] = len(ln["ports"])
        assert L["cycles"] == L["boundary"] + L["stations"] + L["fixed"], (lid, L)
        rep[lid] = dict(L)
    P["ports"].extend([ports["L8007_0r"], ports["L8008_8"], ports["L8006_0r"]])
    P["partitions"].extend(new_parts)
    rl = P["reset"].get("relay_lockup")
    if rl:
        rl["types"] = sorted(set(rl["types"]) | {"NW_iorly", "NE_iorly"})
    json.dump(P, open(argv[1], "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
