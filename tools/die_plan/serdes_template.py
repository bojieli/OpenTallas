#!/usr/bin/env python3
"""HARD-S81-SERDES-1 2026-11-13 (DIEVIEW-S81 F5): ONE layout template for every shore serdes type of a die plan.

Template (type-local frame, um): the KP4 island (hard core ot_s81_kp4_dchn + the two decoder SRAMs + all column logic)
sits directly under the PMA pair at the PMA end nearest the lane port bar; the only other placeable area is a strip at
the port pins.  Four registered lanes (RTL form OT_S81_SERDES_LANE: PIN 3 / TXA 4 / RXI 5 / RXO 3 rows, the same in
every type, so every serdes link has the same latency) connect island <-> PMA face and island <-> port pins; every row
is placed FIRM on its per-bit lane by serdes_lanes.tcl (type key serdes_lanes).

  serdes_template.py PLAN [--types a,b] [--tsv F] [--json F] [--apply OUT_PLAN]

Per type it prints the island box, the hard-core / SRAM moves (move only: shapes and orientations are kept), the lane
hops (centre line and worst bit; FAIL over the reach) and the recovered-clock box.  --apply writes a plan with the moves,
the serdes_lanes key and the define; it does not touch pins, clock taps or reset sites (those stay the die owner's event).
"""
import argparse
import copy
import json
import sys

ISLAND_W, ISLAND_H = 760.0, 304.0
BAND_GAP = 7.5            # island top below the PMA RX face (the RCK band rows sit in this gap)
STRIP = 101.0             # pin strip depth at the port face
REACH = 405.0
ROWS = {"u_lpin": 3, "u_txl": 6, "u_lrxi": 5, "u_lrxo": 3}
DEFINE = "OT_S81_SERDES_LANE"
# SERDES-FIN-2 11-13: the column cone forms that close inside the island (S81-RCK-10 vJ / DIE-S81-85 vB, proven lock-step
# 11-07 / 11-09; LANE over them: bench6vb).  RCK_RELAY4 is not part of it: LANE_RXI carries the PMA -> decoder reach.
CONE_DEFINES = ["OT_S81_SERDES_RST_TREE", "OT_S81_RM_STAGED", "OT_S81_RM_LOCAL4", "OT_S81_RM_WFULL8",
                "OT_S81_KP4_SYN_LOCAL", "OT_S81_KP4_AM_FACE3", "OT_S81_CLAND_WCHK"]
# macro origins relative to the island's lower-left corner (the serdes__t2 proof kit arrangement)
REL = {"u_chn": (36.016, 40.448), "u_dmem": (355.696, 10.172), "u_cmem": (545.776, 10.172)}
GX, GY = 0.432, 2.16      # move grid: keeps every macro pin on its routing track and the origin on the site grid


def _snap(v, g):
    return round(round(v / g) * g, 3)


def _parts(t):
    out = {}
    for c in t.get("contents", []):
        for pp in c.get("physical_parts") or []:
            out[pp["physical_inst"].split(".")[-1]] = pp
        leaf = c.get("inst", "").split(".")[-1]
        if leaf in ("u_dmem", "u_cmem") and "origin_um" in c:
            out[leaf] = c
    for h in t.get("hard_cores") or []:
        out[h["inst"].split(".")[-1]] = h
    return out


def is_serdes(t):
    p = _parts(t)
    return all(k in p for k in ("u_ptx", "u_prx", "u_chn", "u_dmem", "u_cmem"))


def _complement(core, keep):
    """Rectangles covering core minus the keep rectangles (scan-line over the sorted edges)."""
    xs = sorted({core[0], core[2], *[k[0] for k in keep], *[k[2] for k in keep]})
    ys = sorted({core[1], core[3], *[k[1] for k in keep], *[k[3] for k in keep]})
    cells = []
    for j in range(len(ys) - 1):
        run = None
        for i in range(len(xs) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            free = any(k[0] <= cx <= k[2] and k[1] <= cy <= k[3] for k in keep)
            if not free:
                run = [xs[i], ys[j], xs[i + 1], ys[j + 1]] if run is None else [run[0], run[1], xs[i + 1], run[3]]
            elif run is not None:
                cells.append(run); run = None
        if run is not None:
            cells.append(run)
    merged = []
    for c in cells:                      # merge vertically adjacent equal spans
        for m in merged:
            if m[0] == c[0] and m[2] == c[2] and m[3] == c[1]:
                m[3] = c[3]; break
        else:
            merged.append(list(c))
    return [[round(v, 3) for v in m] for m in merged]


def template(name, t):
    W, H = t["outline_um"]
    p = _parts(t)
    px, band = p["u_prx"]["origin_um"]
    plen = 2246.4
    buses = {b["name"]: b for b in t["buses"] if b["name"].startswith("coll_")}
    bi = next(b for n, b in sorted(buses.items()) if b["dir"] == "in")
    bo = next(b for n, b in sorted(buses.items()) if b["dir"] == "out")
    face = bi["face"]
    if bo["face"] != face:
        raise ValueError(f"{name}: coll in / out on different faces")
    ci, co = sum(bi["window_um"]) / 2, sum(bo["window_um"]) / 2
    lo = min(bi["window_um"] + bo["window_um"]); hi = max(bi["window_um"] + bo["window_um"])
    if face in ("E", "W"):
        end = face
        pin_i, pin_o = ((W - 66.0) if face == "E" else 66.0, ci), ((W - 41.0) if face == "E" else 41.0, co)
        strip = [W - STRIP, max(4.32, lo - 30), W - 4.32, hi + 30] if face == "E" else [4.32, max(4.32, lo - 30), STRIP, hi + 30]
    else:
        end = "E" if (ci + co) / 2 > px + plen / 2 else "W"
        y = 66.0 if face == "S" else H - 66.0
        pin_i, pin_o = (ci, y), (co, 41.0 if face == "S" else H - 41.0)
        strip = [max(4.32, lo - 30), 4.32, hi + 30, STRIP] if face == "S" else [max(4.32, lo - 30), H - STRIP, hi + 30, H - 4.32]
    x1 = px + plen if end == "E" else px + ISLAND_W
    x0 = x1 - ISLAND_W
    y1 = band - BAND_GAP; y0 = y1 - ISLAND_H
    island = [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]
    moves = {}
    for leaf, (rx, ry) in REL.items():
        ox, oy = p[leaf]["origin_um"]
        if leaf == "u_chn":                  # plan origin carries the track offset; move it as a delta
            oy_eff = oy
        nx = ox + _snap(x0 + rx - ox, GX); ny = oy + _snap(y0 + ry - oy, GY)
        moves[leaf] = {"from": [ox, oy], "to": [round(nx, 3), round(ny, 3)]}
    # lane ends: island ports on its PMA-side edge (RX / TX) and on its port-side corner (PIN / RXO)
    far = px + 15.0 if end == "E" else px + plen - 15.0          # the PMA bit farthest from the island
    rx_port = (x0 + 170.0, y1 - 44.0) if end == "E" else (x1 - 170.0, y1 - 44.0)
    tx_port = (x0 + 370.0, y1 - 64.0) if end == "E" else (x1 - 370.0, y1 - 64.0)
    if face in ("E", "W"):
        io_x = x1 - 20.0 if face == "E" else x0 + 20.0
    else:                                                       # S / N port bar: the island point nearest the bar centre
        io_x = min(max((ci + co) / 2, x0 + 20.0), x1 - 20.0)
    pin_port = (io_x, y0 + 60.0); rxo_port = (io_x - (20.0 if io_x > x0 + ISLAND_W / 2 else -20.0), y0 + 20.0)
    mid = px + plen / 2
    chains = [
        {"name": "u_lpin", "rows": ROWS["u_lpin"], "kind": "pt", "a_um": [round(pin_i[0], 3), round(pin_i[1], 3)], "b_um": [round(pin_port[0], 3), round(pin_port[1], 3)]},
        {"name": "u_txl", "rows": ROWS["u_txl"], "kind": "txl", "a_um": [round(tx_port[0], 3), round(tx_port[1], 3)], "b_um": [round(mid, 3), round(band - 15.5, 3)]},
        {"name": "u_lrxi", "rows": ROWS["u_lrxi"], "kind": "rxi", "a_um": [round(mid, 3), round(band - 5.5, 3)], "b_um": [round(rx_port[0], 3), round(rx_port[1], 3)]},
        {"name": "u_lrxo", "rows": ROWS["u_lrxo"], "kind": "pt", "a_um": [round(rxo_port[0], 3), round(rxo_port[1], 3)], "b_um": [round(pin_o[0], 3), round(pin_o[1], 3)]},
    ]
    def man(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
    hops = {
        "u_lpin": man(pin_i, pin_port) / (ROWS["u_lpin"] + 1),
        "u_lrxo": man(rxo_port, pin_o) / (ROWS["u_lrxo"] + 1),
        "u_txl": man(tx_port, (far, band - 15.5)) / ROWS["u_txl"],
        "u_lrxi": man((far, band - 5.5), rx_port) / ROWS["u_lrxi"],
    }
    core = [4.32, 4.32, W - 4.32, band - BAND_GAP]
    blocks = _complement(core, [island, strip])
    blocks += [[4.32, round(band - BAND_GAP, 3), round(px - 0.5, 3), H - 4.32], [round(px + plen + 0.5, 3), round(band - BAND_GAP, 3), W - 4.32, H - 4.32]]
    blocks = [b for b in blocks if b[2] - b[0] > 1 and b[3] - b[1] > 1]
    rck_box = [round(min(px, x0), 3), round(y0, 3), round(max(px + plen, x1), 3), round(band, 3)]
    return {"type": name, "end": end, "port_face": face, "island_um": island, "pin_strip_um": [round(v, 3) for v in strip],
            "moves": moves, "serdes_lanes": {"blocks": blocks, "chains": chains},
            "hops_um": {k: round(v, 1) for k, v in hops.items()}, "max_hop_um": round(max(hops.values()), 1),
            "verdict": "PASS" if max(hops.values()) <= REACH else "FAIL", "rck_box_um": rck_box,
            "signature": f"{end}/{face}/px{px:g}"}


def apply(plan, res, cone=True):
    out = copy.deepcopy(plan)
    for r in res:
        t = out["partition_types"][r["type"]]
        for c in t.get("contents", []):
            leaf = c.get("inst", "").split(".")[-1]
            if leaf in r["moves"] and "origin_um" in c:
                c["origin_um"] = r["moves"][leaf]["to"]
            for pp in c.get("physical_parts") or []:          # the SRAMs are physical parts of u_phy on the S81 plan
                pl = pp["physical_inst"].split(".")[-1]
                if pl in r["moves"]:
                    pp["origin_um"] = r["moves"][pl]["to"]
        for h in t.get("hard_cores") or []:
            leaf = h["inst"].split(".")[-1]
            if leaf in r["moves"]:
                h["origin_um"] = r["moves"][leaf]["to"]; h["orient"] = "R180"
        t["serdes_lanes"] = r["serdes_lanes"]
        d = t.setdefault("verilog_defines", [])
        for x in [DEFINE] + (CONE_DEFINES if cone else []):
            if x not in d:
                d.append(x)
    return out


def delta(plan, new):
    """Per-type changes plan -> new for the serdes types (a small JSON for the die plan event)."""
    out = {}
    for n, t in new["partition_types"].items():
        o = plan["partition_types"][n]
        if all(o.get(k) == t.get(k) for k in ("serdes_lanes", "verilog_defines", "hard_cores", "contents")):
            continue
        rec = {}
        if o.get("verilog_defines") != t.get("verilog_defines"):
            rec["verilog_defines"] = {"from": o.get("verilog_defines", []), "to": t["verilog_defines"]}
        if o.get("serdes_lanes") != t.get("serdes_lanes"):
            rec["serdes_lanes"] = t["serdes_lanes"]
        mv = {}
        for key in ("hard_cores", "contents"):
            for a, b in zip(o.get(key) or [], t.get(key) or []):
                if a.get("origin_um") != b.get("origin_um") or a.get("orient") != b.get("orient"):
                    mv[b["inst"]] = {"from": [a.get("origin_um"), a.get("orient")], "to": [b.get("origin_um"), b.get("orient")]}
        for a, b in zip(o.get("contents") or [], t.get("contents") or []):
            for pa, pb in zip(a.get("physical_parts") or [], b.get("physical_parts") or []):
                if pa.get("origin_um") != pb.get("origin_um"):
                    mv[pb["physical_inst"]] = {"from": [pa.get("origin_um"), pa.get("orient")], "to": [pb.get("origin_um"), pb.get("orient")]}
        if mv:
            rec["moves"] = mv
        out[n] = rec
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("--types"); ap.add_argument("--tsv"); ap.add_argument("--json"); ap.add_argument("--apply")
    ap.add_argument("--delta", help="write the per-type changes (moves, serdes_lanes, defines) as JSON")
    ap.add_argument("--no-cone", action="store_true", help="LANE define only (without the island cone forms)")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    want = set(a.types.split(",")) if a.types else None
    res = [template(n, t) for n, t in sorted(plan["partition_types"].items()) if is_serdes(t) and (want is None or n in want)]
    rows = ["type\tend\tface\tisland_um\tdchn_to\tlpin\ttxl\tlrxi\tlrxo\tmax_hop\tverdict"]
    for r in res:
        h = r["hops_um"]
        rows.append("\t".join(str(v) for v in (r["type"], r["end"], r["port_face"], r["island_um"], r["moves"]["u_chn"]["to"],
                                                 h["u_lpin"], h["u_txl"], h["u_lrxi"], h["u_lrxo"], r["max_hop_um"], r["verdict"])))
    txt = "\n".join(rows) + "\n"
    if a.tsv: open(a.tsv, "w").write(txt)
    if a.json: json.dump(res, open(a.json, "w"), indent=1)
    if a.apply or a.delta:
        new = apply(plan, res, cone=not a.no_cone)
        if a.apply: json.dump(new, open(a.apply, "w"), indent=1)
        if a.delta: json.dump(delta(plan, new), open(a.delta, "w"), indent=1, sort_keys=True)
    sys.stdout.write(txt)
    nf = sum(r["verdict"] != "PASS" for r in res)
    print(f"SERDES_TEMPLATE types {len(res)} FAIL {nf} rows {ROWS} define {DEFINE} cone {0 if a.no_cone else len(CONE_DEFINES)}")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
