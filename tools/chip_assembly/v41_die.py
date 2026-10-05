#!/usr/bin/env python3
"""Die-level assembly (rung 5) of the DeepSeek-V4.1 ROM layer die and its HBM-only comparator die.

The die is assembled hierarchically: every cluster (ROM/MAC tile, vector/VM hub, HBM service slice,
attention+index, collective, PHYs and links) is a black-box abstract placed where the floorplan puts it,
and the top level holds only the channel nets between cluster pins.  No flat synthesis of the die is
attempted (the retired attempt, ot_chip_v41x_pdie with the monolithic K arbiter flattened into the top,
spent 24 h in yosys/ABC on a 1.45 M-gate netlist and was stopped).

Inputs (all sha256-pinned into the record):
  results/floorplan/v41_reservation_plan.json      regions and transport channels (root's geometry)
  results/contracts/v41_floorplan_connectivity.json edge widths (the connectivity ledger)
  results/arch/v41_die_assembly.json                PHY rects, analytical area rows, long-wire budgets
  results/floorplan/v41_stage17_bankmap.json        ROM macro reservation of the busiest candidate stage
  results/arch/v41_hbm_best.json                    comparator: 4 stacks/die, 3.6 TB/s/die
Cluster abstracts are PARAMETERISED PLACEHOLDERS sized from those rows until W1 (inventory, bank map,
floorplan generator) and W2 (hardened cluster abstracts) land; ``--cluster-lef NAME=path`` substitutes a
real abstract for a placeholder master of the same name.

Global route at die scale.  OpenROAD's global router fixes its GCell at 15 routing pitches (0.54 um on
ASAP7), which at 815 mm^2 is 2.8e9 GCells (a 2 x 1.6 mm test already takes 11 GB).  The die-level route
therefore uses a BUNDLED technology: every routing layer's pitch, width and spacing is multiplied by
``k`` (default 32), and every bus is routed as ceil(bits / k) bundle nets.  Track capacity per layer and
per channel is preserved exactly (a channel of width w holds w / (k p) bundles = w / p wires / k), and a
bundle's route length is its bits' route length.  What the bundled route does not resolve is sub-bundle
pin access and via capacity; those belong to the real-technology corridor runs (``corridor`` mode).

Power grid at the die level is modelled as routing capacity reserved on M8/M9 (the die mesh) and the
platform's layer derating on M2-M7; the clock is a regional tree with mesochronous crossings
(results/arch/v41_die_assembly.json clock.verdict), so inter-cluster crossings are timed as registered
channels priced with the routed ASAP7 wire model (tools/chip_assembly/floorplans.wire_delay_model()).

    python3 tools/chip_assembly/v41_die.py plan --arch v41_rom            # floorplan + edges, no run
    python3 tools/chip_assembly/v41_die.py run  --arch v41_rom --work W   # bundled floorplan+GRT (docker)
    python3 tools/chip_assembly/v41_die.py record --arch v41_rom --work W # parse and write the record
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARCHS = ("v41_rom", "v41_hbm")
RESULTS = ROOT / "results/physical_abi3/asap7/chip/dies"
ORFS_IMAGE = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest")

INPUTS = {
    "reservation": "results/floorplan/v41_reservation_plan.json",
    "connectivity": "results/contracts/v41_floorplan_connectivity.json",
    "assembly": "results/arch/v41_die_assembly.json",
    "bankmap": "results/floorplan/v41_stage17_bankmap.json",
    "hbm_best": "results/arch/v41_hbm_best.json",
}

# Timing basis (briefing: ASAP7 0.92 ns, 60 ps uncertainty; wire model = routed express-link fit).
PERIOD_PS = 920.0
UNCERTAINTY_PS = 60.0

# ASAP7 routing layers: (name, direction, pitch um, width um, spacing um, offset um).  M2's 7 tracks per
# 0.270 um row give it an effective 0.0386 um pitch; the bundled tech uses that.
ASAP7_LAYERS = [
    ("M1", "VERTICAL", 0.036, 0.018, 0.018, 0.009),
    ("M2", "HORIZONTAL", 0.270 / 7, 0.018, 0.018, 0.009),
    ("M3", "VERTICAL", 0.036, 0.018, 0.018, 0.009),
    ("M4", "HORIZONTAL", 0.048, 0.024, 0.024, 0.012),
    ("M5", "VERTICAL", 0.048, 0.024, 0.024, 0.012),
    ("M6", "HORIZONTAL", 0.064, 0.032, 0.032, 0.016),
    ("M7", "VERTICAL", 0.064, 0.032, 0.032, 0.016),
    ("M8", "HORIZONTAL", 0.080, 0.040, 0.040, 0.116),
    ("M9", "VERTICAL", 0.080, 0.040, 0.040, 0.116),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def wire_model() -> dict[str, Any]:
    if __package__ in (None, ""):
        sys.path.insert(0, str(ROOT / "tools"))
    from chip_assembly import floorplans  # noqa: WPS433
    m = floorplans.wire_delay_model()
    reach = (PERIOD_PS - UNCERTAINTY_PS - m["overhead_ps"]) / (m["ps_per_um"] * 1000.0)
    reach0 = (PERIOD_PS - m["overhead_ps"]) / (m["ps_per_um"] * 1000.0)
    return {**m, "period_ps": PERIOD_PS, "uncertainty_ps": UNCERTAINTY_PS,
            "reach_mm_per_cycle": round(reach, 4), "reach_mm_per_cycle_no_uncertainty": round(reach0, 4)}


# ---------------------------------------------------------------------------------------------------
# Inventory and floorplan
# ---------------------------------------------------------------------------------------------------


@dataclass
class Cluster:
    inst: str
    master: str
    kind: str
    x: float          # lower-left, mm
    y: float
    w: float
    h: float
    orient: str = "R0"
    basis: str = ""
    region: str | None = None

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class Bus:
    id: str
    src: str
    dst: str
    bits: int
    ledger_edges: list[str]
    budget_path: str | None
    basis: str


@dataclass
class Params:
    arch: str
    tile_cols: int = 4
    tile_rows: int = 3
    n_attn: int = 1              # RTL instantiates one attention/index path
    n_coll: int = 1              # RTL: 1 collective (ledger 8), 1 controller (2), 1 router (4)
    coll_place: str = "edge"     # edge: at the UCIe / SerDes strips (ledger rects); center: channel crossing
    svc_h_mm: float = 0.30       # HBM service slice depth beside each PHY (W2 karb local partition pending)
    attn_w_mm: float = 2.40
    attn_h_mm: float = 1.70
    coll_w_mm: float = 0.90
    coll_h_mm: float = 0.44
    edge_gap_mm: float = 0.02    # keep-out from a region boundary
    result_bits: int = 512       # ASSUMED tile -> hub partial-sum word (one VM word)
    ring_bits: int = 512         # ASSUMED cross-region reduction word
    attn_out_bits: int = 512     # ASSUMED attention output word to the VM
    extra: dict[str, Any] = field(default_factory=dict)


def area_rows(asm: dict[str, Any]) -> dict[str, float]:
    return {r["block"]: float(r.get("placed_mm2") or 0.0) for r in asm["ledger"]["layer"]["rows"]}


ENGINE_ROWS = ("block-dot pool (FP8/FP4 weights + FP4 indexer)", "BF16 pool (BF16 weights, wo_a, attention)",
               "pool operand muxes", "HC projection (FP32 lanes)")
HUB_ROWS = ("vector unit, light lanes", "vector unit, SFU lanes", "streaming select (4 x 16 tselect)",
            "Sinkhorn units (one per verified position)", "sqrt(softplus)", "top-6 select", "activation quantiser",
            "FP4 quantise/dequantise", "vector memory (residual, MTP positions)", "engine chaining buffers")


def build(params: Params) -> dict[str, Any]:
    arch = params.arch
    res = load(INPUTS["reservation"])
    asm = load(INPUTS["assembly"])
    bank = load(INPUTS["bankmap"])
    hbm = load(INPUTS["hbm_best"])
    conn = {e["id"]: e for e in load(INPUTS["connectivity"])["edges"]}
    rows = area_rows(asm)
    die_w, die_h = res["die_mm"]
    regions = {r["name"]: r for r in res["regions"]}
    notes: list[str] = []

    engine_mm2 = sum(rows[b] for b in ENGINE_ROWS)
    hub_mm2 = sum(rows[b] for b in HUB_ROWS)
    rom_mm2 = float(bank["reservation"]["area_mm2"])
    n_regions = 4
    n_tiles = n_regions * params.tile_cols * params.tile_rows
    if arch == "v41_rom":
        tile_mm2 = (rom_mm2 + engine_mm2) / n_tiles
        tile_basis = (f"({rom_mm2:.2f} mm2 ROM = stage-17 reservation {bank['reservation']['macros']} x "
                      f"{bank['reservation']['macro_type']} + {engine_mm2:.2f} mm2 pooled engines, ledger placed_mm2) / "
                      f"{n_tiles} tiles")
    else:
        staging = 0.2
        tile_mm2 = engine_mm2 / n_tiles + staging
        tile_basis = (f"{engine_mm2:.2f} mm2 pooled engines / {n_tiles} tiles + {staging} mm2 weight staging "
                      "(ASSUMED); no weight ROM")
    hub_each = hub_mm2 / n_regions

    clusters: list[Cluster] = []
    # PHYs and links at the analytical positions.
    rects = asm["floorplan"]["layer"]["rects"]
    phys = [r for r in rects if r["cls"] == "phy_hbm"]
    for i, r in enumerate(phys):
        north = r["y"] > die_h / 2
        clusters.append(Cluster(f"u_hbm_phy{i}", "ot_v41d_hbm_phy", "phy_hbm", r["x"], r["y"], r["w"], r["h"],
                                "MX" if north else "R0", "HBM3E PHY + controller 12.0 x 0.8335 mm (ledger rect)"))
    uc = next(r for r in rects if r["cls"] == "phy_ucie")
    clusters.append(Cluster("u_ucie", "ot_v41d_ucie", "phy_ucie", die_w - uc["w"], uc["y"], uc["w"], uc["h"], "R0",
                            "17 UCIe-A modules, 1.043 mm published depth (ledger rect)"))
    east = regions["east_package_link"]
    if uc["w"] > east["w_mm"]:
        notes.append(f"UCIe-A depth {uc['w']} mm exceeds the east link strip ({east['w_mm']} mm) by "
                     f"{(uc['w'] - east['w_mm']) * 1000:.0f} um; the strip must widen or the adjacent regions lose it")
    se = next(r for r in rects if r["cls"] == "phy_serdes")
    clusters.append(Cluster("u_serdes", "ot_v41d_serdes", "phy_serdes", 0.0, se["y"], se["w"], se["h"], "R0",
                            "45 x 112G SerDes lanes (ledger rect)"))
    # HBM service slices beside each PHY (on the core side).
    for i, r in enumerate(phys):
        north = r["y"] > die_h / 2
        y = r["y"] - params.svc_h_mm if north else r["y"] + r["h"]
        clusters.append(Cluster(f"u_hbm_svc{i}", "ot_v41d_hbm_svc" if arch == "v41_rom" else "ot_v41d_hbm_svc_w",
                                "hbm_svc", r["x"], y, r["w"], params.svc_h_mm, "MX" if north else "R0",
                                "per-PC local HBM service strip (placeholder until W2's karb local partition)"))
    # Attention + index: in the gap between the two PHYs of an edge, at the vertical transport channel.
    south_phys = sorted([r for r in phys if r["y"] < die_h / 2], key=lambda r: r["x"])
    north_phys = sorted([r for r in phys if r["y"] > die_h / 2], key=lambda r: r["x"])
    gap_x0 = south_phys[0]["x"] + south_phys[0]["w"]
    gap_x1 = south_phys[1]["x"]
    ax = (gap_x0 + gap_x1) / 2 - params.attn_w_mm / 2
    if params.attn_w_mm > gap_x1 - gap_x0:
        notes.append("attention cluster wider than the PHY gap")
    south_io = regions["south_HBM_and_controller_reservation"]
    for a in range(params.n_attn):
        north = a == 1
        y = die_h - params.attn_h_mm - 0.1 if north else 0.1
        if params.attn_h_mm + 0.1 > south_io["h_mm"]:
            notes.append("attention cluster deeper than the HBM/controller reservation")
        clusters.append(Cluster(f"u_attn{a}", "ot_v41d_attn", "attention", ax, y, params.attn_w_mm, params.attn_h_mm,
                                "MX" if north else "R0",
                                "window stage + merger + QK/softmax/PV + probability buffer + index scorer/selector "
                                "(placeholder size; W2 attention neighbourhood pending)"))
    # Collective (+ package controller + router) in the east link strip above the UCIe modules.
    coll_positions = [(die_w - params.coll_w_mm - 0.05, uc["y"] + uc["h"] + 0.3),
                      (1.0 - params.coll_w_mm + 0.0, se["y"] + se["h"] + 0.3)]
    hch = regions["horizontal_registered_transport"]
    vch = regions["vertical_registered_transport"]
    for c in range(params.n_coll):
        cw, chh = params.coll_w_mm, params.coll_h_mm
        if params.coll_place == "center":
            # at the transport-channel crossing, adjacent to all four hubs (square: pins on four edges)
            side = min(vch["w_mm"], hch["h_mm"]) - 2 * params.edge_gap_mm
            cw = chh = side
            x = vch["x_mm"] + (vch["w_mm"] - side) / 2
            y = hch["y_mm"] + (hch["h_mm"] - side) / 2
        else:
            x, y = coll_positions[c % 2]
            if c >= 2:
                y += 0.6 * (c // 2)
        clusters.append(Cluster(f"u_coll{c}", "ot_v41d_coll", "collective", max(x, 0.0), y, cw,
                                chh, "R0",
                                "one-shot collective + collective DMA + package controller + fabric router "
                                "(ledger rect 0.9 x 0.4424 mm)"))
    # Regions: a hub strip on the side facing the vertical transport channel, tiles in a grid.
    comp = sorted([r for r in res["regions"] if r["kind"] == "compute"], key=lambda r: r["name"])
    vchan_x = regions["vertical_registered_transport"]["x_mm"]
    tile_w = tile_h = None
    slack = []
    for ri, reg in enumerate(comp):
        x0, y0 = reg["x_mm"] + params.edge_gap_mm, reg["y_mm"] + params.edge_gap_mm
        x1 = min(reg["x_mm"] + reg["w_mm"], die_w - uc["w"]) - params.edge_gap_mm
        y1 = reg["y_mm"] + reg["h_mm"] - params.edge_gap_mm
        rh = y1 - y0
        hub_w = hub_each / rh
        hub_east = reg["x_mm"] + reg["w_mm"] / 2 < vchan_x
        hx = x1 - hub_w if hub_east else x0
        clusters.append(Cluster(f"u_hub{ri}", "ot_v41d_hub", "hub", hx, y0, hub_w, rh, "R0",
                                f"vector unit + VM + select/Sinkhorn/SFU share: {hub_mm2:.2f} mm2 ledger rows / 4",
                                reg["name"]))
        tx0, tx1 = (x0, hx) if hub_east else (hx + hub_w, x1)
        slot_w = (tx1 - tx0) / params.tile_cols
        slot_h = rh / params.tile_rows
        scale = math.sqrt(tile_mm2 / (slot_w * slot_h))
        if scale >= 1.0:
            notes.append(f"{reg['name']}: tile content {tile_mm2:.2f} mm2 exceeds its slot "
                         f"{slot_w * slot_h:.2f} mm2 (overfill)")
        tile_w, tile_h = slot_w * scale, slot_h * scale
        slack.append({"region": reg["name"], "slot_mm": [round(slot_w, 4), round(slot_h, 4)],
                      "tile_mm": [round(tile_w, 4), round(tile_h, 4)],
                      "gap_x_um": round((slot_w - tile_w) * 1000, 1), "gap_y_um": round((slot_h - tile_h) * 1000, 1),
                      "fill": round(scale * scale, 4)})
        for row in range(params.tile_rows):
            for col in range(params.tile_cols):
                tx = tx0 + col * slot_w + (slot_w - tile_w) / 2
                ty = y0 + row * slot_h + (slot_h - tile_h) / 2
                clusters.append(Cluster(f"u_tile{ri}_{row}_{col}",
                                        "ot_v41d_rommac" if arch == "v41_rom" else "ot_v41d_mac",
                                        "tile", tx, ty, tile_w, tile_h, "R0", tile_basis, reg["name"]))

    buses = edges(params, clusters, conn, hbm)
    return {"params": params, "die_mm": [die_w, die_h], "clusters": clusters, "buses": buses,
            "tile_slots": slack, "notes": notes,
            "areas": {"engine_mm2": round(engine_mm2, 3), "hub_mm2": round(hub_mm2, 3), "rom_mm2": round(rom_mm2, 3),
                      "tile_mm2": round(tile_mm2, 4)}}


def edges(params: Params, clusters: list[Cluster], conn: dict[str, Any], hbm: dict[str, Any]) -> list[Bus]:
    by_kind: dict[str, list[Cluster]] = {}
    for c in clusters:
        by_kind.setdefault(c.kind, []).append(c)
    hubs = sorted(by_kind["hub"], key=lambda c: c.inst)
    tiles = by_kind["tile"]
    svcs = sorted(by_kind["hbm_svc"], key=lambda c: c.inst)
    attns = by_kind.get("attention", [])
    colls = by_kind.get("collective", [])
    ucie = by_kind["phy_ucie"][0]
    serdes = by_kind["phy_serdes"][0]
    w = lambda eid: int(conn[eid]["data_bits"])  # noqa: E731
    out: list[Bus] = []
    act_bits = w("vm_me") + w("vm_he")
    for t in tiles:
        hub = next(h for h in hubs if h.region == t.region)
        out.append(Bus(f"act.{t.inst}", hub.inst, t.inst, act_bits, ["vm_me", "vm_he"], "pool_operand_in",
                       "VM activation operands to the tile's local ME (128) and HE (256), ledger widths"))
        out.append(Bus(f"res.{t.inst}", t.inst, hub.inst, params.result_bits, [], "pool_result_out",
                       "ASSUMED: one 512-bit VM word of partial sums back to the hub"))
    ring = [0, 1, 3, 2]
    for i, r in enumerate(ring):
        nxt = ring[(i + 1) % 4]
        out.append(Bus(f"ring.hub{r}_hub{nxt}", hubs[r].inst, hubs[nxt].inst, params.ring_bits, [], "spine_reduce",
                       "ASSUMED: cross-region reduction ring word"))
    def near_coll(h: Cluster) -> list[Cluster]:
        if len(colls) <= 1:
            return colls
        return [min(colls, key=lambda c: abs(c.cx - h.cx) + abs(c.cy - h.cy))]

    for c in colls:
        for h in [h for h in hubs if c in near_coll(h)]:
            out.append(Bus(f"vm_coll.{h.inst}.{c.inst}", h.inst, c.inst, w("vm_collective"), ["vm_collective"],
                           "collective_edge", "VM -> collective, ledger width"))
            out.append(Bus(f"coll_vm.{c.inst}.{h.inst}", c.inst, h.inst, w("collective_vm"), ["collective_vm"],
                           "collective_edge", "collective transpose -> VM (4 x 512), ledger width"))
        links = ((ucie, "collective_edge"), (serdes, "stage_hop_edge"))
        if len(colls) > 1:  # each collective terminates the link PHY on its own edge
            links = tuple(l for l in links if min(colls, key=lambda q: abs(q.cx - l[0].cx)) is c)
        for phy, path in links:
            out.append(Bus(f"link_tx.{c.inst}.{phy.inst}", c.inst, phy.inst, 512, [], path,
                           "ASSUMED: 512-bit flit to the link PHY"))
            out.append(Bus(f"link_rx.{phy.inst}.{c.inst}", phy.inst, c.inst, 512, [], path,
                           "ASSUMED: 512-bit flit from the link PHY"))
    if len(colls) > 1:
        for a_, b_ in zip(colls, colls[1:] + colls[:1]):
            if a_ is b_:
                continue
            out.append(Bus(f"coll_bridge.{a_.inst}.{b_.inst}", a_.inst, b_.inst, 512, [], "collective_edge",
                           "ASSUMED: 512-bit bridge between the die's collective engines"))
    idx_sectors = conn["index_select"]["service"]["reader_sectors"] / conn["index_select"]["service"]["reader_cycles"]
    idx_bits = int(math.ceil(idx_sectors / len(svcs))) * 256
    for s in svcs:
        a = min(attns, key=lambda a: abs(a.cy - s.cy) + abs(a.cx - s.cx))
        out.append(Bus(f"hbm_window.{s.inst}", s.inst, a.inst, w("hbm_window"), ["hbm_window"], "kv_static_rows",
                       "HBM window sectors to the window stage, ledger width"))
        out.append(Bus(f"idx_keys.{s.inst}", s.inst, a.inst, idx_bits, ["index_select"], "kv_static_rows",
                       f"index keys at the measured reader rate: {idx_sectors:.2f} sectors/cycle over "
                       f"{len(svcs)} stacks x 256 bits"))
        out.append(Bus(f"selected_kv.{s.inst}", a.inst, s.inst, w("selected_kv"), ["selected_kv"],
                       "kv_gather_request", "global KV source IDs to the stack's service, ledger width"))
    for a in attns:
        h = min(hubs, key=lambda h: abs(h.cy - a.cy) + abs(h.cx - a.cx))
        out.append(Bus(f"pv_preload.{a.inst}", h.inst, a.inst, w("vm_pv_preload"), ["vm_pv_preload"],
                       "pool_operand_in", "VM -> probability buffer preload, ledger width"))
        out.append(Bus(f"q.{a.inst}", h.inst, a.inst, w("vm_he"), ["vm_he"], "pool_operand_in",
                       "query/operand vector to attention and index heads (vm_he width)"))
        out.append(Bus(f"attn_out.{a.inst}", a.inst, h.inst, params.attn_out_bits, [], "pool_result_out",
                       "ASSUMED: attention output word to the VM"))
    if params.arch == "v41_hbm":
        bw = float(hbm["comparator"]["bw_Bps_per_die"])
        stacks = int(hbm["comparator"]["stacks_per_die"])
        f_hz = 1e12 / PERIOD_PS
        per_stack_bits = bw / stacks / f_hz * 8
        # each stack feeds the tiles of the region it borders
        for s in svcs:
            region_tiles = [t for t in tiles if t.region == nearest_region(s, tiles)]
            bits = int(math.ceil(per_stack_bits / len(region_tiles)))
            for t in region_tiles:
                out.append(Bus(f"weights.{s.inst}.{t.inst}", s.inst, t.inst, bits, [], "kv_static_rows",
                               f"weight stream: {bw / 1e12:.1f} TB/s per die / {stacks} stacks at "
                               f"{f_hz / 1e9:.3f} GHz = {per_stack_bits:.0f} bits/cycle/stack over "
                               f"{len(region_tiles)} tiles"))
    return out


def nearest_region(s: Cluster, tiles: list[Cluster]) -> str:
    t = min(tiles, key=lambda t: abs(t.cx - s.cx) + abs(t.cy - s.cy))
    return t.region or ""


# ---------------------------------------------------------------------------------------------------
# Bundled views, netlist and scripts
# ---------------------------------------------------------------------------------------------------


def bundled_tech_lef(k: int) -> str:
    out = ["# Bundled ASAP7 routing technology (tools/chip_assembly/v41_die.py): every routing layer's",
           f"# pitch, width, spacing and offset multiplied by k = {k}; one routing track = {k} ASAP7 tracks.",
           "VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;',
           "UNITS", "  DATABASE MICRONS 1000 ;", "END UNITS", "MANUFACTURINGGRID 0.001 ;"]
    for i, (name, d, p, wd, sp, off) in enumerate(ASAP7_LAYERS):
        out += [f"LAYER {name}", "  TYPE ROUTING ;", f"  DIRECTION {d} ;", f"  PITCH {p * k:.3f} ;",
                f"  WIDTH {wd * k:.3f} ;", f"  SPACING {sp * k:.3f} ;", f"  OFFSET {off * k:.3f} ;", f"END {name}"]
        if i + 1 < len(ASAP7_LAYERS):
            out += [f"LAYER V{i + 1}", "  TYPE CUT ;", f"  SPACING {sp * k:.3f} ;", f"  WIDTH {wd * k:.3f} ;",
                    f"END V{i + 1}"]
    for i in range(len(ASAP7_LAYERS) - 1):
        lo, hi = ASAP7_LAYERS[i], ASAP7_LAYERS[i + 1]
        a, b, c = lo[3] * k / 2, hi[3] * k / 2, min(lo[3], hi[3]) * k / 2
        out += [f"VIA VIA{i + 1}{i + 2} DEFAULT", f"  LAYER {lo[0]} ;", f"    RECT {-a:.3f} {-a:.3f} {a:.3f} {a:.3f} ;",
                f"  LAYER V{i + 1} ;", f"    RECT {-c:.3f} {-c:.3f} {c:.3f} {c:.3f} ;",
                f"  LAYER {hi[0]} ;", f"    RECT {-b:.3f} {-b:.3f} {b:.3f} {b:.3f} ;", f"END VIA{i + 1}{i + 2}"]
    row_h = 0.270 * k
    out += ["SITE bsite", "  CLASS CORE ;", "  SYMMETRY Y ;", f"  SIZE {0.054 * k:.3f} BY {row_h:.3f} ;",
            "END bsite", "END LIBRARY", ""]
    return "\n".join(out)


def bundle_count(bits: int, k: int) -> int:
    return max(1, math.ceil(bits / k))


def facing_edge(c: Cluster, peer: Cluster) -> str:
    dx, dy = peer.cx - c.cx, peer.cy - c.cy
    # a cluster's peer beyond its own extent on one axis decides; otherwise the dominant axis
    if abs(dx) - c.w / 2 > abs(dy) - c.h / 2:
        return "E" if dx > 0 else "W"
    return "N" if dy > 0 else "S"


def pin_plan(model: dict[str, Any], k: int) -> dict[str, dict[str, list[tuple[str, str, float]]]]:
    """inst -> edge -> [(port bundle name, direction, sort key)] in placement order along the edge."""
    cl = {c.inst: c for c in model["clusters"]}
    plan: dict[str, dict[str, list[tuple[str, str, float]]]] = {}
    for b in model["buses"]:
        n = bundle_count(b.bits, k)
        for inst, peer, d in ((b.src, b.dst, "OUTPUT"), (b.dst, b.src, "INPUT")):
            c, p = cl[inst], cl[peer]
            e = facing_edge(c, p)
            key = p.cy if e in ("E", "W") else p.cx
            port = port_name(b, inst == b.src)
            for i in range(n):
                plan.setdefault(inst, {}).setdefault(e, []).append((f"{port}[{i}]", d, key + i * 1e-6))
    for inst in plan:
        for e in plan[inst]:
            plan[inst][e].sort(key=lambda t: t[2])
    return plan


def port_name(b: Bus, is_src: bool) -> str:
    return ("o_" if is_src else "i_") + re.sub(r"[^A-Za-z0-9]", "_", b.id)


SPREAD_KINDS = ("hbm_svc",)


def cluster_lef(c: Cluster, pins: dict[str, list[tuple[str, str, float]]], k: int, obs_top: int,
                master: str) -> tuple[str, int]:
    """One placeholder abstract per INSTANCE (pins differ per instance): OBS M1..M<obs_top>, pins on
    M4 (E/W) and M5 (N/S) at bundled pitch.  Returns (lef text, pins)."""
    w, h = c.w * 1000, c.h * 1000
    p4, p5 = 0.048 * k, 0.048 * k
    depth, half = 0.192 * k, 0.012 * k
    out = [f"MACRO {master}", "  CLASS BLOCK ;", f"  FOREIGN {master} 0 0 ;", f"  SIZE {w:.3f} BY {h:.3f} ;",
           "  SYMMETRY X Y ;"]
    count = 0
    for e, lst in pins.items():
        length = h if e in ("E", "W") else w
        pitch = p4 if e in ("E", "W") else p5
        tracks = int((length - 2 * pitch) / pitch)
        if len(lst) > tracks:
            raise ValueError(f"{c.inst} edge {e}: {len(lst)} bundle pins exceed {tracks} bundled tracks")
        origin = (c.y if e in ("E", "W") else c.x) * 1000
        # ALIGNED pins: each bus's block of bundle pins is centred on its peer's centre projected onto this
        # edge, then the blocks are legalised left to right (and pushed back from the far end if needed).
        groups: dict[str, list[tuple[str, str, float]]] = {}
        for item in lst:
            groups.setdefault(item[0].split("[")[0], []).append(item)
        blocks = sorted(groups.values(), key=lambda g: g[0][2])
        slots: list[int] = []
        cursor = 1
        for g in blocks:
            want = int(round((g[0][2] * 1000 - origin) / pitch - len(g) / 2))
            start = max(want, cursor)
            slots.append(start)
            cursor = start + len(g)
        over = cursor - 1 - tracks
        if over > 0:
            limit = tracks + 1
            for bi in range(len(blocks) - 1, -1, -1):
                slots[bi] = min(slots[bi], limit - len(blocks[bi]))
                limit = slots[bi]
        placed = []
        for g, st in zip(blocks, slots):
            for i, item in enumerate(g):
                placed.append((item, (st + i) * pitch))
        if c.kind in SPREAD_KINDS:
            # the HBM service strip's data enters and leaves at its 32 pseudo-channel windows along the
            # whole PHY edge: every bus is spread over the full edge (round-robin), never bunched at an end
            order = []
            queues = [list(g) for g in blocks]
            while any(queues):
                for q in queues:
                    if q:
                        order.append(q.pop(0))
            step = tracks / len(order)
            placed = [(item, (1 + int(i * step)) * pitch) for i, item in enumerate(order)]
        for (name, d, _), pos in placed:
            if e in ("E", "W"):
                x0 = 0.0 if e == "W" else w - depth
                rect, layer = (x0, pos - half, x0 + depth, pos + half), "M4"
            else:
                y0 = 0.0 if e == "S" else h - depth
                rect, layer = (pos - half, y0, pos + half, y0 + depth), "M5"
            out += [f"  PIN {name}", f"    DIRECTION {d} ;", "    USE SIGNAL ;", "    PORT", f"      LAYER {layer} ;",
                    "      RECT {:.3f} {:.3f} {:.3f} {:.3f} ;".format(*rect), "    END", f"  END {name}"]
            count += 1
    out.append("  OBS")
    for i in range(1, obs_top + 1):
        out += [f"    LAYER M{i} ;", f"      RECT 0 0 {w:.3f} {h:.3f} ;"]
    out += ["  END", f"END {master}", ""]
    return "\n".join(out), count


def write_case(model: dict[str, Any], work: Path, k: int, obs_top: int, m89_reserve: float,
               low_adjust: float) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    plan = pin_plan(model, k)
    # A cluster whose facing edge cannot hold its bus pins (one pin layer per edge at the ASAP7 pitch) is
    # PIN-LIMITED: grow it along that edge and record the growth -- its size is set by wires, not logic.
    growth = []
    for c in model["clusters"]:
        for e, lst in plan.get(c.inst, {}).items():
            need_um = (len(lst) + 4) * 0.048 * k
            have_um = (c.h if e in ("E", "W") else c.w) * 1000
            if need_um > have_um:
                if e in ("E", "W"):
                    c.h = need_um / 1000
                else:
                    c.w = need_um / 1000
                growth.append({"inst": c.inst, "edge": e, "bundle_pins": len(lst), "wires": len(lst) * k,
                               "edge_needed_mm": round(need_um / 1000, 3), "edge_had_mm": round(have_um / 1000, 3)})
    model["pin_limited_growth"] = growth
    lefs = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    ports_by_inst: dict[str, dict[str, tuple[str, int]]] = {}
    pin_total = 0
    masters = {}
    for c in model["clusters"]:
        master = f"{c.master}__{c.inst}"
        masters[c.inst] = master
        text, n = cluster_lef(c, plan.get(c.inst, {}), k, obs_top, master)
        pin_total += n
        lefs.append(text)
    lefs.append("END LIBRARY\n")
    (work / "clusters.lef").write_text("\n".join(lefs), encoding="utf-8")
    (work / "tech.lef").write_text(bundled_tech_lef(k), encoding="utf-8")
    # structural netlist
    v = ["// Die-level glue of the V4.1 die assembly (tools/chip_assembly/v41_die.py): channel nets only.",
         f"// Bundled: one net = {k} wires of a bus."]
    for c in model["clusters"]:
        ports = []
        for e, lst in plan.get(c.inst, {}).items():
            for name, d, _ in lst:
                ports.append((name, d))
        buses: dict[str, tuple[str, int]] = {}
        for name, d in ports:
            base, idx = name[:-1].split("[")
            prev = buses.get(base, (d, -1))
            buses[base] = (d, max(prev[1], int(idx)))
        ports_by_inst[c.inst] = buses
        # masters are LEF blocks (no Verilog module): link_design binds instances to them
    top = model["params"].arch
    v.append(f"module ot_v41d_die_{top} ();")
    conns: dict[str, list[str]] = {c.inst: [] for c in model["clusters"]}
    for b in model["buses"]:
        n = bundle_count(b.bits, k)
        net = "n_" + re.sub(r"[^A-Za-z0-9]", "_", b.id)
        v.append(f"  wire [{n - 1}:0] {net};")
        conns[b.src].append(f".{port_name(b, True)}({net})")
        conns[b.dst].append(f".{port_name(b, False)}({net})")
    for c in model["clusters"]:
        v.append(f"  {masters[c.inst]} {c.inst} (" + ", ".join(conns[c.inst]) + ");")
    v.append("endmodule\n")
    (work / "die.v").write_text("\n".join(v), encoding="utf-8")
    die_w, die_h = model["die_mm"]
    W, H = die_w * 1000, die_h * 1000
    tracks = []
    for name, d, p, *_rest in ASAP7_LAYERS:
        off = _rest[2] * k
        tracks.append(f"make_tracks {name} -x_offset {off:.3f} -x_pitch {p * k:.3f} "
                      f"-y_offset {off:.3f} -y_pitch {p * k:.3f}")
    place = []
    for c in model["clusters"]:
        g = 0.054 * k
        x = round(round(c.x * 1000 / g) * g, 3)
        y = round(round(c.y * 1000 / g) * g, 3)
        place.append(f"place_inst -name {c.inst} -location {{{x} {y}}} -orientation {c.orient} -status FIRM")
    adj = []
    for name, *_ in ASAP7_LAYERS[1:]:
        a = m89_reserve if name in ("M8", "M9") else low_adjust
        adj.append(f"set_global_routing_layer_adjustment {name} {a}")
    tcl = f"""# Die-level floorplan, macro placement and global route (bundled k={k}).
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef /work/tech.lef
read_lef /work/clusters.lef
read_verilog /work/die.v
link_design ot_v41d_die_{top}
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site bsite
{chr(10).join(tracks)}
{chr(10).join(place)}
mem placed
{chr(10).join(adj)}
set_routing_layers -signal M2-M9
global_route -verbose -allow_congestion -congestion_iterations 50 -congestion_report_file /work/grt_congestion.rpt
mem grt
report_wire_length -net * -global_route -file /work/wirelength.csv
set blk [ord::get_db_block]
set out [open /work/gcell_usage.txt w]
set grid [$blk getGCellGrid]
if {{$grid ne "NULL"}} {{
  set gx [$grid getGridX]
  set gy [$grid getGridY]
  puts $out "GRIDX [join $gx ,]"
  puts $out "GRIDY [join $gy ,]"
  set tech [ord::get_db_tech]
  foreach ln {{M2 M3 M4 M5 M6 M7 M8 M9}} {{
    set layer [$tech findLayer $ln]
    set nx [llength $gx]; set ny [llength $gy]
    for {{set j 0}} {{$j < $ny}} {{incr j 4}} {{
      set row {{}}
      for {{set i 0}} {{$i < $nx}} {{incr i 4}} {{
        set cap 0; set use 0
        for {{set jj $j}} {{$jj < min($j+4,$ny)}} {{incr jj}} {{
          for {{set ii $i}} {{$ii < min($i+4,$nx)}} {{incr ii}} {{
            set cap [expr {{$cap + [$grid getCapacity $layer $ii $jj]}}]
            set use [expr {{$use + [$grid getUsage $layer $ii $jj]}}]
          }}
        }}
        lappend row "$cap/$use"
      }}
      puts $out "L $ln $j [join $row {{ }}]"
    }}
  }}
}}
close $out
mem done
"""
    (work / "run.tcl").write_text(tcl, encoding="utf-8")
    # Baseline (no nets): GRT books obstructions and layer adjustments as usage, so the wire demand of a
    # GCell is its routed usage minus this baseline.
    # one short bundle keeps GRT populating the GCell grid; its usage (one bundle) is negligible
    b0 = min(model["buses"], key=lambda b: bundle_count(b.bits, k))
    n0 = "n_" + re.sub(r"[^A-Za-z0-9]", "_", b0.id)
    empty = [f"module ot_v41d_die_{top} ();", f"  wire [{bundle_count(b0.bits, k) - 1}:0] {n0};"]
    for c in model["clusters"]:
        pc = [f".{port_name(b0, c.inst == b0.src)}({n0})"] if c.inst in (b0.src, b0.dst) else []
        empty.append(f"  {masters[c.inst]} {c.inst} (" + ", ".join(pc) + ");")
    (work / "die_empty.v").write_text("\n".join(empty + ["endmodule", ""]), encoding="utf-8")
    base = tcl.replace("/work/die.v", "/work/die_empty.v").replace("/work/gcell_usage.txt", "/work/gcell_base.txt")
    base = base.replace("-congestion_report_file /work/grt_congestion.rpt", "")
    base = base.replace("report_wire_length -net * -global_route -file /work/wirelength.csv", "")
    (work / "run_base.tcl").write_text(base, encoding="utf-8")
    manifest = {"pin_limited_growth": growth, "bundle_k": k, "obs_top_layer": f"M{obs_top}", "m8_m9_reserve": m89_reserve,
                "m2_m7_adjustment": low_adjust, "bundle_pins": pin_total,
                "bundle_nets": sum(bundle_count(b.bits, k) for b in model["buses"]),
                "wires": sum(b.bits for b in model["buses"])}
    (work / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def run_case(work: Path, timeout: int, mem_gb: int) -> int:
    """Routed run (run.tcl -> grt.log) then the no-net baseline (run_base.tcl -> base.log)."""
    rc = 0
    for script, logname in (("run.tcl", "grt.log"), ("run_base.tcl", "base.log")):
        cmd = ["docker", "run", "--rm", f"--memory={mem_gb}g", "-v", f"{work}:/work", "-w", "/work", ORFS_IMAGE,
               "bash", "-lc", "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
               f"openroad -no_init -exit /work/{script}; chmod -R a+rwX /work"]
        with (work / logname).open("w") as log:
            t0 = time.time()
            p = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            log.write(f"\nOT_ELAPSED {time.time() - t0:.1f}\n")
        rc = rc or p.returncode
    return rc


# ---------------------------------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------------------------------


def parse_log(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {"layers": {}}
    m = re.search(r"GRT-0096\] Final congestion report:(.*?)Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)",
                  text, re.S)
    if m:
        for line in m.group(1).splitlines():
            f = line.split()
            if len(f) >= 8 and re.match(r"^M\d$", f[0]):
                out["layers"][f[0]] = {"resource": int(f[1]), "demand": int(f[2]), "usage_pct": float(f[3].rstrip("%")),
                                       "overflow_h": int(f[4]), "overflow_v": int(f[6]), "overflow_total": int(f[8])}
        out["total"] = {"resource": int(m.group(2)), "demand": int(m.group(3)), "usage_pct": float(m.group(4)),
                        "overflow_h": int(m.group(5)), "overflow_v": int(m.group(6)), "overflow_total": int(m.group(7))}
    m = re.search(r"GRT-0018\] Total wirelength: ([\d.]+) um", text)
    out["total_wirelength_bundle_um"] = float(m.group(1)) if m else None
    m = re.search(r"GRT-0303\] Global routing runtime = (\S+)", text)
    out["grt_runtime"] = m.group(1) if m else None
    out["errors"] = re.findall(r"\[ERROR [^\]]+\].*", text)[:10]
    out["mem"] = re.findall(r"OTMEM (\S+) (\d+) MB", text)
    m = re.search(r"OT_ELAPSED ([\d.]+)", text)
    out["elapsed_s"] = float(m.group(1)) if m else None
    return out


def parse_wirelength(path: Path) -> dict[str, float]:
    """report_wire_length -global_route -file: lines 'grt: <net> <um> <pins>'."""
    lens: dict[str, float] = {}
    if not path.is_file():
        return lens
    for line in path.read_text().splitlines():
        f = line.replace(",", " ").split()
        if len(f) >= 3 and f[0] == "grt:" and f[1].startswith("n_"):
            try:
                lens[f[1]] = float(f[2])
            except ValueError:
                continue
    return lens


def _read_usage(path: Path) -> dict[str, list[list[tuple[float, float]]]]:
    out: dict[str, list[list[tuple[float, float]]]] = {}
    for line in path.read_text().splitlines():
        if line.startswith("L "):
            f = line.split()
            out.setdefault(f[1], []).append([tuple(float(x) for x in c.split("/")) for c in f[3:]])
    return out


def congestion_map(path: Path, base_path: Path) -> dict[str, Any]:
    """Per 4 x 4-GCell window wire utilisation per layer: (usage - baseline usage) / (capacity - baseline
    usage).  GRT books obstructions and layer adjustments as usage, which the no-net baseline run measures;
    windows with no free capacity after the baseline (inside clusters on M2..M7) are excluded."""
    if not (path.is_file() and base_path.is_file()):
        return {}
    routed, base = _read_usage(path), _read_usage(base_path)
    grid: dict[str, list[list[float | None]]] = {}
    summary = {}
    for ln, rows in routed.items():
        g = []
        vals = []
        for j, row in enumerate(rows):
            r = []
            for i, (cap, use) in enumerate(row):
                b = base[ln][j][i][1]
                free = cap - b
                dem = use - b
                if free <= 0.5:
                    r.append(None if dem <= 0 else 9.99)
                else:
                    u = round(dem / free, 3)
                    r.append(u)
                    vals.append(u)
            g.append(r)
        grid[ln] = g
        over = sum(1 for row in g for v in row if v is not None and v > 1.0)
        summary[ln] = {"open_windows": len(vals), "max_util": max(vals) if vals else None,
                       "mean_util": round(sum(vals) / len(vals), 4) if vals else None,
                       "windows_over_0p5": sum(1 for v in vals if v > 0.5),
                       "windows_over_0p8": sum(1 for v in vals if v > 0.8),
                       "windows_over_1": over}
    return {"window_gcells": 4, "summary": summary, "grid": grid}


def make_record(model: dict[str, Any], work: Path, k: int) -> dict[str, Any]:
    wm = wire_model()
    log = parse_log((work / "grt.log").read_text()) if (work / "grt.log").is_file() else {}
    lens = parse_wirelength(work / "wirelength.csv")
    manifest = json.loads((work / "manifest.json").read_text())
    cmap = congestion_map(work / "gcell_usage.txt", work / "gcell_base.txt")
    for g in manifest.get("pin_limited_growth", []):  # the geometry the case was written with
        c = next(c for c in model["clusters"] if c.inst == g["inst"])
        if g["edge"] in ("E", "W"):
            c.h = max(c.h, g["edge_needed_mm"])
        else:
            c.w = max(c.w, g["edge_needed_mm"])
    asm = load(INPUTS["assembly"])
    budgets = asm["long_wires"]["by_model"]["asap7_routed_fit"]["paths"]
    cl = {c.inst: c for c in model["clusters"]}
    reach = wm["reach_mm_per_cycle"]
    per_bus = []
    for b in model["buses"]:
        net = "n_" + re.sub(r"[^A-Za-z0-9]", "_", b.id)
        n = bundle_count(b.bits, k)
        ls = [lens.get(f"{net}[{i}]") for i in range(n)] if n > 1 else [lens.get(net, lens.get(f"{net}[0]"))]
        ls = [x for x in ls if x is not None]
        s, d = cl[b.src], cl[b.dst]
        manh = abs(s.cx - d.cx) + abs(s.cy - d.cy)
        L = max(ls) / 1000 if ls else None
        cyc = math.ceil(L / reach) if L is not None else None
        budget = budgets.get(b.budget_path or "", {})
        per_bus.append({
            "id": b.id, "src": b.src, "dst": b.dst, "bits": b.bits, "bundles": n, "ledger_edges": b.ledger_edges,
            "basis": b.basis, "centre_manhattan_mm": round(manh, 3),
            "routed_max_mm": round(L, 3) if L is not None else None,
            "routed_mean_mm": round(sum(ls) / len(ls) / 1000, 3) if ls else None,
            "crossing_cycles": cyc, "pipeline_registers": (cyc - 1) if cyc else None,
            "budget_path": b.budget_path, "budget_cycles": budget.get("cycles"), "budget_mm": budget.get("mm"),
            "over_budget_cycles": (cyc - budget["cycles"]) if (cyc is not None and budget.get("cycles")) else None,
        })
    classes: dict[str, dict[str, Any]] = {}
    for r in per_bus:
        cls = r["id"].split(".")[0]
        c = classes.setdefault(cls, {"buses": 0, "wires": 0, "max_mm": 0.0, "max_cycles": 0, "budget_path": r["budget_path"],
                                     "budget_cycles": r["budget_cycles"], "wire_mm_total": 0.0})
        c["buses"] += 1
        c["wires"] += r["bits"]
        if r["routed_max_mm"] is not None:
            c["max_mm"] = max(c["max_mm"], r["routed_max_mm"])
            c["max_cycles"] = max(c["max_cycles"], r["crossing_cycles"])
            c["wire_mm_total"] += r["routed_mean_mm"] * r["bits"]
    for c in classes.values():
        c["wire_mm_total"] = round(c["wire_mm_total"], 1)
        c["registers_total_est"] = None
    for r in per_bus:
        cls = classes[r["id"].split(".")[0]]
        if r["pipeline_registers"] is not None:
            cls["registers_total_est"] = (cls["registers_total_est"] or 0) + r["pipeline_registers"] * r["bits"]
    routed = bool(log.get("total")) and len(lens) > 0
    overflow = (log.get("total") or {}).get("overflow_total")
    p = model["params"]
    rec = {
        "schema": "opentallas.v41.die_assembly_grt.v1",
        "arch": p.arch,
        "status": "bundled_die_global_route" if routed else "not_routed",
        "claim_boundary": ("die-level floorplan + placement of PLACEHOLDER cluster abstracts + bundled global route "
                           "of the inter-cluster channel nets; not detailed route, not extracted timing, not real "
                           "cluster abstracts; PDN as routing capacity reservation"),
        "die_mm": model["die_mm"],
        "params": {k_: v for k_, v in p.__dict__.items()},
        "areas": model["areas"],
        "tile_slots": model["tile_slots"],
        "floorplan_notes": model["notes"],
        "pin_limited_growth": manifest.get("pin_limited_growth"),
        "clusters": [{"inst": c.inst, "kind": c.kind, "region": c.region, "x_mm": round(c.x, 4), "y_mm": round(c.y, 4),
                      "w_mm": round(c.w, 4), "h_mm": round(c.h, 4), "orient": c.orient, "basis": c.basis}
                     for c in model["clusters"]],
        "route_model": {**manifest,
                        "gcell_um": round(15 * 0.270 / 7 * k, 3),
                        "basis": "bundled ASAP7 layers (pitch x k); OBS over clusters on M1..obs_top; M8/M9 reserve "
                                 "for the die power mesh; M2-M7 platform derating"},
        "global_route": {k_: v for k_, v in log.items() if k_ != "mem"},
        "peak_rss_mb": max((int(m[1]) for m in log.get("mem", [])), default=None),
        "congestion_map": {"summary": cmap.get("summary"), "window_gcells": cmap.get("window_gcells")},
        "overflow_total": overflow,
        "routable": (overflow == 0) if overflow is not None else None,
        "wire_model": wm,
        "classes": classes,
        "buses": per_bus,
        "sources": {rel: sha256_file(ROOT / rel) for rel in INPUTS.values()},
        "tool_sha256": sha256_file(Path(__file__)),
        "git": git_identity(),
    }
    (work / "congestion_grid.json").write_text(json.dumps(cmap.get("grid", {})) + "\n")
    return rec


def git_identity() -> dict[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    st = subprocess.run(["git", "status", "--porcelain", "--", "tools", "rtl", "results/floorplan",
                         "results/contracts", "results/arch"], cwd=ROOT, capture_output=True, text=True, check=False)
    return {"commit": head.stdout.strip() or None, "inputs_dirty": [l for l in st.stdout.splitlines() if l.strip()][:20]}


def svg(rec: dict[str, Any], grid: dict[str, list[list[float]]], layer: str | None = None) -> str:
    W, H = rec["die_mm"]
    s = 30.0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * s:.0f}" height="{H * s:.0f}" '
           f'viewBox="0 0 {W * s:.0f} {H * s:.0f}" font-family="sans-serif" font-size="9">',
           f'<rect width="{W * s:.0f}" height="{H * s:.0f}" fill="#fff" stroke="#000"/>']
    if grid:
        layers = [layer] if layer else list(grid)
        rows = grid[layers[0]]
        ny, nx = len(rows), len(rows[0]) if rows else 0
        cw, ch = W * s / max(nx, 1), H * s / max(ny, 1)
        for j in range(ny):
            for i in range(nx):
                u = max((grid[ln][j][i] or 0.0) for ln in layers if j < len(grid[ln]) and i < len(grid[ln][j]))
                if u <= 0.05:
                    continue
                col = "#d7301f" if u > 1.0 else ("#fc8d59" if u > 0.8 else ("#fdcc8a" if u > 0.5 else "#fef0d9"))
                out.append(f'<rect x="{i * cw:.1f}" y="{H * s - (j + 1) * ch:.1f}" width="{cw + .2:.1f}" '
                           f'height="{ch + .2:.1f}" fill="{col}"/>')
    for c in rec["clusters"]:
        out.append(f'<rect x="{c["x_mm"] * s:.1f}" y="{(H - c["y_mm"] - c["h_mm"]) * s:.1f}" width="{c["w_mm"] * s:.1f}" '
                   f'height="{c["h_mm"] * s:.1f}" fill="none" stroke="#1f4e79" stroke-width="0.8"/>')
        if c["w_mm"] > 1.5 and c["h_mm"] > 0.3:
            out.append(f'<text x="{(c["x_mm"] + 0.1) * s:.1f}" y="{(H - c["y_mm"] - c["h_mm"] + 0.35) * s:.1f}">'
                       f'{c["inst"]}</text>')
    out.append("</svg>\n")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["plan", "write", "run", "record"])
    ap.add_argument("--arch", required=True, choices=ARCHS)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--k", type=int, default=32, help="bundle factor (wires per routed net)")
    ap.add_argument("--obs-top", type=int, default=7, help="clusters obstruct M1..M<obs-top>")
    ap.add_argument("--m89-reserve", type=float, default=0.30, help="M8/M9 fraction reserved for the power mesh")
    ap.add_argument("--low-adjust", type=float, default=0.25, help="M2-M7 derating (ORFS asap7 default 0.25)")
    ap.add_argument("--n-attn", type=int, default=1)
    ap.add_argument("--n-coll", type=int, default=1)
    ap.add_argument("--coll-place", default="edge", choices=["edge", "center"])
    ap.add_argument("--tag", default="asbuilt")
    ap.add_argument("--mem-gb", type=int, default=100)
    ap.add_argument("--timeout", type=int, default=6 * 3600)
    ap.add_argument("--out", type=Path, help="record path (default results/.../chip/dies/<arch>_<tag>_grt.json)")
    a = ap.parse_args(argv)
    params = Params(arch=a.arch, n_attn=a.n_attn, n_coll=a.n_coll, coll_place=a.coll_place)
    model = build(params)
    if a.mode == "plan":
        print(json.dumps({"areas": model["areas"], "tile_slots": model["tile_slots"], "notes": model["notes"],
                          "clusters": len(model["clusters"]), "buses": len(model["buses"]),
                          "wires": sum(b.bits for b in model["buses"])}, indent=1))
        return 0
    if a.work is None:
        ap.error("--work required")
    work = a.work.resolve()
    if a.mode in ("write", "run"):
        man = write_case(model, work, a.k, a.obs_top, a.m89_reserve, a.low_adjust)
        print(json.dumps(man))
        if a.mode == "write":
            return 0
        rc = run_case(work, a.timeout, a.mem_gb)
        print(f"openroad rc={rc}")
    rec = make_record(model, work, a.k)
    rec["tag"] = a.tag
    out = a.out or RESULTS / f"{a.arch}_{a.tag}_grt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    grid = json.loads((work / "congestion_grid.json").read_text()) if (work / "congestion_grid.json").is_file() else {}
    out.with_suffix(".svg").write_text(svg(rec, grid), encoding="utf-8")
    print(json.dumps({"record": str(out), "overflow": rec["overflow_total"],
                      "classes": {k_: (v["max_mm"], v["max_cycles"], v["budget_cycles"]) for k_, v in rec["classes"].items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
