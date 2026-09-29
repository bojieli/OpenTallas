#!/usr/bin/env python3
"""Floorplans of the two GPU-organised HBM comparator dies (Qwen3-8B TP-2 die, DeepSeek-V4.1 die).

    python3 tools/hbm_gpu_floorplan.py [--out-dir results/floorplan/hbm_gpu]

Each die is the 815 mm2 outline of W1/W5 with four HBM3E PHY+controller abstracts (ot_hbm3e_phy LEF,
12.0 x 0.83 mm) on 48 mm of the long edges, the W5 service bands behind them, and the model-sized compute
(tools/uarch_model.hbm_gpu_design):
  * an 8 x 4 array of SM elements, each a tile of its own SRAM macros (x store, weight staging, scratch;
    real ot_sram_1r1w_1024x256 views, placed) over its logic at the model's placement density; one
    quadrant of 8 SMs per HBM stack, so every SM's weights come from its own stack (no weight byte
    crosses the die);
  * one L2 slice per stack (64 SRAM macros each, placed) between the stack's service band and its quadrant;
  * the barrier network: a node per quadrant, the root at the array centre, with the x-broadcast hub;
  * V4.1 only: the dedicated units (indexer, attention, stream unit, SFU, mHC, select; W11) as a central hub
    between the two SM half-arrays;
  * the die-to-die link reservations (UCIe; V4.1 also the switched-fabric SerDes, ASSUMED area).
It checks legality (inside the die, on the macro lattice, no overlap with halos, regions disjoint), sizes the
NoC channels from their wire counts against the M5-M9 tracks, and prices every crossing -- barrier leaf and
trunk, weight path, x broadcast, TP exchange, SM <-> dedicated hub -- in register cycles at the design
clock with the loaded channel constant (uarch_model.WIRE_PS_PER_UM_LOADED).  The barrier distances feed
uarch_model.barrier_network and the barrier bench (rtl/test/tb_gpu_barrier.sv).

Not established: routability, timing of any path (only distances are priced), power integrity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_o4_floorplan as QF  # noqa: E402
import uarch_model as U  # noqa: E402

OUT_DIR = ROOT / "results/floorplan/hbm_gpu"
SRAM = "ot_sram_1r1w_1024x256_m2_r2c2"
DIE_W, DIE_H = QF.DIE_W, QF.DIE_H
EDGE = QF.EDGE_KEEP
SVC_DEPTH = 630.72            # W5 service band behind each PHY row (HBM controllers, PC arbiters, stream heads)
UCIE_MM2 = 10.0               # qwen3_budget ucie.link.phy_mm2_per_die
FABRIC_SERDES_MM2 = 18.0      # ASSUMED: V4.1 switched-fabric SerDes (NVL-class, 18 links) -- no view exists
UPPER_TRACKS_V = sum(1000.0 / QF.UPPER_PITCH_NM[l] for l in ("M5", "M7", "M9")) * QF.SIGNAL_SHARE  # per um
UPPER_TRACKS_H = sum(1000.0 / QF.UPPER_PITCH_NM[l] for l in ("M6", "M8")) * QF.SIGNAL_SHARE
INPUTS = ["tools/uarch_model.py", "tools/qwen_o4_floorplan.py", "physical/asap7_memory_macros/index.json",
          "physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.lef",
          f"physical/asap7_memory_macros/{SRAM}/{SRAM}.lef"]


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def load_views():
    cat = json.loads((ROOT / "physical/asap7_memory_macros/index.json").read_text())
    for n, m in cat["macros"].items():
        QF.MV[n] = (m["width_um"], m["height_um"])
    QF.MV["ot_hbm3e_phy"] = (12000.096, 833.49)


def snap(v, q):
    return QF.snap(v, q)


def sm_tile(design):
    """SM tile: its SRAM macros in rows along the tile's north edge, logic below at the model density."""
    a = design["sm_area"]
    n_sram = sum(a["sram_macros"].values())
    mw, mh = QF.MV[SRAM]
    px, py = snap(mw + 2 * QF.HALO_X, QF.SNAP_X), snap(mh + 2 * QF.HALO_Y, QF.SNAP_Y)
    per_row = 9
    rows = -(-n_sram // per_row)
    w = snap(per_row * px, QF.SNAP_X)
    logic_h = snap(a["footprint_logic_mm2"] * 1e6 / w, QF.SNAP_Y)
    h = snap(logic_h + rows * py, QF.SNAP_Y)
    return dict(w=w, h=h, logic_h=logic_h, sram=n_sram, per_row=per_row, px=px, py=py,
                footprint_mm2=round(w * h / 1e6, 3), model_mm2=a["total_mm2"])


def place_sm(p, name, x, y, tile):
    p.region(name, "sm", x, y, tile["w"], tile["h"])
    for i in range(tile["sram"]):
        r, c = divmod(i, tile["per_row"])
        p.macro(f"{name}_sram{i}", SRAM, snap(x + c * tile["px"] + QF.HALO_X, QF.SNAP_X),
                snap(y + tile["logic_h"] + r * tile["py"] + QF.HALO_Y, QF.SNAP_Y), "R0", name)


def place_l2(p, name, cx, y0, north, n_macros=64, per_row=16):
    mw, mh = QF.MV[SRAM]
    px, py = snap(mw + 2 * QF.HALO_X, QF.SNAP_X), snap(mh + 2 * QF.HALO_Y, QF.SNAP_Y)
    rows = -(-n_macros // per_row)
    w, h = per_row * px, rows * py + 120.0          # + tag/controller logic band
    x0 = snap(cx - w / 2, QF.SNAP_X)
    y = y0 if not north else y0 - h
    p.region(name, "l2", x0, y, w, h)
    for i in range(n_macros):
        r, c = divmod(i, per_row)
        yy = y + 120.0 + r * py + QF.HALO_Y if not north else y + r * py + QF.HALO_Y
        p.macro(f"{name}_m{i}", SRAM, snap(x0 + c * px + QF.HALO_X, QF.SNAP_X), snap(yy, QF.SNAP_Y), "R0", name)
    return dict(x=x0, y=y, w=w, h=h)


def build(model):
    d = U.hbm_gpu_design(model)
    clock = d["clock_hz"]
    tile = sm_tile(d)
    p = QF.Plan(f"{model}_hbm_gpu_die")
    p.region("die", "die", 0, 0, DIE_W, DIE_H)
    QF.MV.setdefault("ot_hbm3e_phy", (12000.096, 833.49))
    ph = QF.phy_strips(p)
    y_s0 = snap(EDGE + ph + 4 * QF.SNAP_Y, QF.SNAP_Y)
    y_n1 = snap(DIE_H - EDGE - ph - 4 * QF.SNAP_Y, QF.SNAP_Y)
    p.region("svc_south", "service", EDGE, y_s0, DIE_W - 2 * EDGE, SVC_DEPTH,
             holds="HBM3E controllers, 64 PC arbiters and the bulk-copy request/response heads of two stacks")
    p.region("svc_north", "service", EDGE, y_n1 - SVC_DEPTH, DIE_W - 2 * EDGE, SVC_DEPTH,
             holds="as svc_south")
    core_y0 = y_s0 + SVC_DEPTH + QF.CORRIDOR_UM
    core_y1 = y_n1 - SVC_DEPTH - QF.CORRIDOR_UM
    ucie_w = UCIE_MM2 * 1e6 / 12000.0
    p.region("ucie_phy", "reservation", EDGE, DIE_H / 2 - 6000, ucie_w, 12000,
             note="10 mm2 ledger (qwen3_budget ucie.link.phy_mm2_per_die); no LEF view")
    west = EDGE + ucie_w + QF.CORRIDOR_UM
    east = DIE_W - EDGE
    if model == "v41":
        fw = FABRIC_SERDES_MM2 * 1e6 / 12000.0
        p.region("fabric_serdes", "reservation", DIE_W - EDGE - fw, DIE_H / 2 - 6000, fw, 12000,
                 note="ASSUMED 18 mm2 switched-fabric SerDes (v41_hbm_switched NVL-class links); no view")
        east = DIE_W - EDGE - fw - QF.CORRIDOR_UM
    # ---- channels between SMs sized by their wires ----
    # vertical channel between SM columns: the weight links of the column's SMs in the quadrant (2 each side
    # share it) + result gather; horizontal channel: x broadcast + barrier + result gather
    e = d["element"]
    w_link = d["noc"]["weight_port_bits_per_sm"]
    ch_v_wires = 2 * w_link + 2 * 256 + 8
    ch_x = snap(max(QF.CORRIDOR_UM, ch_v_wires / UPPER_TRACKS_V), QF.SNAP_X)
    ch_h_wires = d["noc"]["x_broadcast_bits"] + 8 * 256 + 8
    ch_y = snap(max(QF.CORRIDOR_UM, ch_h_wires / UPPER_TRACKS_H), QF.SNAP_Y)
    cols, rows = 8, 4
    cx, cy = (west + east) / 2, (core_y0 + core_y1) / 2
    sm_pos = []
    hub = None
    if model == "qwen":
        aw = cols * tile["w"] + (cols - 1) * ch_x
        ah = rows * tile["h"] + (rows - 1) * ch_y
        x0, y0 = snap(cx - aw / 2, QF.SNAP_X), snap(cy - ah / 2, QF.SNAP_Y)
        for r in range(rows):
            for c in range(cols):
                sm_pos.append((c, r, x0 + c * (tile["w"] + ch_x), y0 + r * (tile["h"] + ch_y)))
        array = dict(x=x0, y=y0, w=aw, h=ah)
    else:
        hub_mm2 = d["dedicated_units_footprint_mm2"]
        half_c = cols // 2
        ah = rows * tile["h"] + (rows - 1) * ch_y
        hub_h = min(core_y1 - core_y0 - 2 * QF.CORRIDOR_UM, max(ah, 1.0))
        hub_w = snap(hub_mm2 * 1e6 / hub_h, QF.SNAP_X)
        if hub_w > 12000:                            # taller hub rather than a wider die centre
            hub_h = min(core_y1 - core_y0 - 2 * QF.CORRIDOR_UM, hub_mm2 * 1e6 / 12000)
            hub_w = snap(hub_mm2 * 1e6 / hub_h, QF.SNAP_X)
        hw = half_c * tile["w"] + (half_c - 1) * ch_x
        aw = 2 * hw + 2 * ch_x + hub_w
        x0, y0 = snap(cx - aw / 2, QF.SNAP_X), snap(cy - ah / 2, QF.SNAP_Y)
        hx = snap(x0 + hw + ch_x, QF.SNAP_X)
        hub = dict(x=hx, y=snap(cy - hub_h / 2, QF.SNAP_Y), w=hub_w, h=hub_h)
        p.region("dedicated_hub", "logic", hub["x"], hub["y"], hub["w"], hub["h"],
                 holds=", ".join(f"{k} {v} mm2" for k, v in d["dedicated_units_mm2"].items()),
                 note="W11 dedicated units at the model's spec widths, logic at the model density")
        for r in range(rows):
            for c in range(cols):
                xx = x0 + c * (tile["w"] + ch_x) if c < half_c else \
                    hx + hub_w + ch_x + (c - half_c) * (tile["w"] + ch_x)
                sm_pos.append((c, r, xx, y0 + r * (tile["h"] + ch_y)))
        array = dict(x=x0, y=y0, w=aw, h=ah)
    for i, (c, r, x, y) in enumerate(sm_pos):
        place_sm(p, f"sm{i}", snap(x, QF.SNAP_X), snap(y, QF.SNAP_Y), tile)
    # ---- quadrants, barrier nodes, root, L2 slices ----
    root = (cx, cy)
    quads = {}
    for i, (c, r, x, y) in enumerate(sm_pos):
        q = (0 if c < cols // 2 else 1) + (0 if r < rows // 2 else 2)     # 0 SW, 1 SE, 2 NW, 3 NE
        quads.setdefault(q, []).append((i, x + tile["w"] / 2, y + tile["h"] / 2))
    nodes = {}
    for q, sms in quads.items():
        # node at the quadrant's inner corner channel crossing nearest the root: minimises max(leaf) + trunk
        xs = [s[1] for s in sms]
        ys = [s[2] for s in sms]
        nodes[q] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])  # noqa: E731
    leaf = max(man((s[1], s[2]), nodes[q]) for q, sms in quads.items() for s in sms)
    trunk = max(man(nodes[q], root) for q in quads)
    phy_x = {0: DIE_W / 4, 1: 3 * DIE_W / 4, 2: DIE_W / 4, 3: 3 * DIE_W / 4}
    l2 = {}
    for q in quads:
        north = q >= 2
        xq = (min(s[1] for s in quads[q]) + max(s[1] for s in quads[q])) / 2
        ya = core_y1 if north else core_y0
        l2[q] = place_l2(p, f"l2_{'ns'[0 if north else 1]}{q % 2}", xq, ya, north)
    wc = lambda um: U.wire_cycles(um, clock, U.WIRE_PS_PER_UM_LOADED)  # noqa: E731
    # weight path: stack PHY -> service band -> L2 slice -> farthest SM of the quadrant (latency only; the
    # stream is prefetched, so these cycles add to the bulk-copy loaded latency, not to the token)
    wpath = max(abs(s[1] - phy_x[q]) + abs(s[2] - (l2[q]["y"] + (0 if q >= 2 else l2[q]["h"])))
                + l2[q]["h"] + SVC_DEPTH for q, sms in quads.items() for s in sms)
    xb = max(man((s[1], s[2]), root) for sms in quads.values() for s in sms)
    tp = man(root, (EDGE + ucie_w, DIE_H / 2))
    conns = [
        dict(name="barrier_leaf", distance_um=round(leaf, 1), bits=2, per_token_crossings=2 * d.get("token", {}).get("boundaries", 629)),
        dict(name="barrier_trunk", distance_um=round(trunk, 1), bits=2, per_token_crossings=2 * d.get("token", {}).get("boundaries", 629)),
        dict(name="x_broadcast_root_to_sm", distance_um=round(xb, 1), bits=d["noc"]["x_broadcast_bits"],
             per_token_crossings=d.get("token", {}).get("boundaries", 629)),
        dict(name="weight_phy_to_sm", distance_um=round(wpath, 1), bits=w_link, per_token_crossings=0,
             note="prefetched stream: adds to the bulk-copy loaded latency (in-flight bytes), not to the token"),
        dict(name="tp_root_to_ucie", distance_um=round(tp, 1), bits=512, per_token_crossings=146 if model == "qwen" else 0),
    ]
    if hub:
        hsm = max(abs(s[1] - (hub["x"] + hub["w"] / 2)) - hub["w"] / 2 + abs(s[2] - (hub["y"] + hub["h"] / 2))
                  for sms in quads.values() for s in sms)
        conns.append(dict(name="sm_to_dedicated_hub_edge", distance_um=round(hsm, 1), bits=1024,
                          per_token_crossings=0, note="activation exchange with attention / SU / indexer"))
    for c in conns:
        c["cycles_one_way"] = wc(c["distance_um"])
    leg = QF.legality(p)
    core_mm2 = (east - west) * (core_y1 - core_y0) / 1e6
    used = dict(sm_array_mm2=round(len(sm_pos) * tile["w"] * tile["h"] / 1e6, 2),
                l2_mm2=round(sum(v["w"] * v["h"] for v in l2.values()) / 1e6, 2),
                hub_mm2=round(hub["w"] * hub["h"] / 1e6, 2) if hub else 0.0)
    fits = (array["w"] <= east - west and array["h"] <= core_y1 - core_y0 - 2 * 700 and leg["legal"])
    rec = dict(
        design=f"{model}_hbm_gpu_die", model=model, clock_hz=clock,
        die_um=[DIE_W, DIE_H], core_um=dict(x0=round(west, 1), y0=round(core_y0, 1), x1=round(east, 1),
                                            y1=round(core_y1, 1), area_mm2=round(core_mm2, 2)),
        sm_tile=tile, sm_count=len(sm_pos), array=array, channels_um=dict(x=ch_x, y=ch_y,
                                                                         v_wires=ch_v_wires, h_wires=ch_h_wires,
                                                                         tracks_per_um_v=round(UPPER_TRACKS_V, 2),
                                                                         tracks_per_um_h=round(UPPER_TRACKS_H, 2)),
        quadrants={str(q): [s[0] for s in sms] for q, sms in quads.items()},
        barrier_network=dict(max_leaf_um=round(leaf, 1), max_trunk_um=round(trunk, 1), levels=2,
                             fan_in=[8, 4], nodes={str(q): [round(v, 1) for v in n] for q, n in nodes.items()},
                             root=[round(root[0], 1), round(root[1], 1)],
                             leaf_cycles=wc(leaf), trunk_cycles=wc(trunk)),
        l2_slices={k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in l2.items()},
        dedicated_hub=hub, crossings=conns, area_used=used, fits=bool(fits), legality=leg,
        macro_counts={mn: sum(1 for m in p.macros if m["macro"] == mn) for mn in sorted({m["macro"] for m in p.macros})},
        regions=p.regions)
    return p, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    a = ap.parse_args(argv)
    load_views()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for model in ("qwen", "v41"):
        p, rec = build(model)
        stem = a.out_dir / f"{model}_hbm_die"
        rec["def_sha256"] = QF.write_def(p, str(stem) + "_macros.def")
        QF.write_svg(p, str(stem) + ".svg")
        rec.update(schema="opentallas.floorplan.hbm_gpu.v1", tool="tools/hbm_gpu_floorplan.py",
                   source_sha256={s: sha(s) for s in INPUTS + ["tools/hbm_gpu_floorplan.py"]},
                   claim_boundary="placement legality, fit and priced distances only; no route, timing or "
                                  "power claim")
        (a.out_dir / f"{model}_hbm_die.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
        b = rec["barrier_network"]
        print(f"{model}: SM tile {rec['sm_tile']['w']:.0f} x {rec['sm_tile']['h']:.0f} um, array "
              f"{rec['array']['w']:.0f} x {rec['array']['h']:.0f}, legal={rec['legality']['legal']} fits={rec['fits']}"
              f"  leaf {b['max_leaf_um']} um/{b['leaf_cycles']} cyc, trunk {b['max_trunk_um']} um/{b['trunk_cycles']} cyc")
        for c in rec["crossings"]:
            print(f"   {c['name']:26s} {c['distance_um']:9.1f} um  {c['cycles_one_way']:3d} cycles")


if __name__ == "__main__":
    main()
