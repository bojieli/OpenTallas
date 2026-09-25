"""Tile and die floorplans of the three architectures.

Everything the physical flow places is declared here: the hardened blocks
(sizes, pin edges), the placeholder memories and PHYs, and where each sits in
its parent.  Coordinates are micrometres from the parent's lower-left corner.

Chip clock: 1.0 ns (1 GHz), the target the architecture assumes; every
block was routed at 0.85-1.0 ns flat with its I/O false-pathed, so 1.0 ns
leaves the boundary budgets something to divide.

The tile (rtl/chip/ot_chip_hdc_tile.sv) is one mesh node:

    y ^
      |  +------------------------------------------+-----+
      |  | weight store (ROM bank / HBM prefetch)    | N   |
      |  |                                           | link|
      |  |                                           | chan|
      |  +------+--------------+------+-------------+-----+
      |  | KVS  |              |      |             |
      |  | win  |     ME       | vmem |    SU       |
      |  | tail |              |      |             |
      |  +------+--+------+----+------+--+----------+
      |  |router|ctrl| glue (sequencer, links)| prog | crom |
      |  +--------------------------------------------------+   --> x

The die is a mesh of tiles mirrored in alternate columns (MY) and rows (MX)
so that neighbours face each other with the same edge, the standard
tile-flipping arrangement, with PHY and link placeholders on the die edges.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import macros as mc

ROOT = Path(__file__).resolve().parents[2]
CLOCK_PERIOD_NS = 1.0


# --------------------------------------------------------------------------
# Wire delay model, measured
# --------------------------------------------------------------------------

EXPRESS_LINK_RECORDS = [
    "results/physical_abi3/asap7/rom/ot_rom_express_link/d0_w64_L1000/physical.json",
    "results/physical_abi3/asap7/rom/ot_rom_express_link/d0_w64_L2000/physical.json",
    "results/physical_abi3/asap7/rom/ot_rom_express_link/d0_w64_L3000/physical.json",
]


def wire_delay_model() -> dict[str, Any]:
    """Least-squares fit of the routed express-link period against length.

    Each record is a register-to-register link of LINK_UM with no intermediate
    register (SPACING_UM = LINK_UM), routed at ASAP7; its fmax period is the
    flop overhead plus the buffered wire.  The slope is ps per um of buffered
    wire, the intercept the clock-to-q + setup + boundary overhead.
    """
    xs, ys, used = [], [], []
    for rel in EXPRESS_LINK_RECORDS:
        rec = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        length = rec["design"]["parameters"]["LINK_UM"]
        period_ps = 1e12 / rec["design"]["fmax_hz"]
        xs.append(length)
        ys.append(period_ps)
        used.append({"record": rel, "link_um": length, "period_ps": round(period_ps, 1)})
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return {
        "ps_per_um": round(slope, 4),
        "overhead_ps": round(my - slope * mx, 1),
        "points": used,
        "basis": "least-squares fit of routed fmax period vs LINK_UM over the express-link records",
    }


# --------------------------------------------------------------------------
# Hardened blocks
# --------------------------------------------------------------------------


@dataclass
class Block:
    """A block hardened into a macro: its RTL, its size and its pin edges."""
    name: str                      # macro (= module) name
    sources: list[str]
    width_um: float
    height_um: float
    # (port regex, edge[, first bit, last bit]); first match wins, "S" otherwise
    pin_edges: list[tuple]
    params: dict[str, Any] = field(default_factory=dict)
    default_edge: str = "S"
    place_density: float = 0.60
    record: str | None = None      # the flat routed record this block came from
    notes: str = ""

    @property
    def core_area_um2(self) -> float:
        return (self.width_um - 4) * (self.height_um - 4)


HDC_ME_SOURCES = [
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_matvec.sv",
]
HDC_SU_SOURCES = [
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_reduce.sv",
    "rtl/hdc/ot_hdc_stream.sv",
]

BLOCKS: dict[str, Block] = {
    "ot_hdc_matvec": Block(
        "ot_hdc_matvec", HDC_ME_SOURCES, 400.0, 400.0,
        [(r"^wrom_", "N"), (r"^(x_|o_|ov$)", "E")],
        record="results/physical_abi3/asap7/hdc/ot_hdc_matvec/physical.json",
        notes="64-lane matrix-vector engine; 68.6k um2 of cells flat, so ~43% utilisation"),
    "ot_hdc_stream": Block(
        "ot_hdc_stream", HDC_SU_SOURCES, 320.0, 320.0,
        [(r"^wrom_", "N"), (r"^(va_|vb_|vc_|vm_|red_)", "W")],
        record="results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json",
        notes="stream unit with its reducer; 42.4k um2 of cells flat"),
    "ot_hdc_kv_stream": Block(
        "ot_hdc_kv_stream", ["rtl/hdc/kv/ot_hdc_kv_walk.sv", "rtl/hdc/kv/ot_hdc_kv_stream.sv"],
        200.0, 200.0,
        [(r"^(hq_|hr_)", "S"), (r"^(win_|tl_)", "E")],
        default_edge="N",
        record="results/physical_abi3/asap7/hdc/kv/ot_hdc_kv_stream/physical.json",
        notes="KV streaming engine; 6.5k um2 of cells but ~7,500 pins, so pin-limited"),
    "ot_chip_pkg_ctrl": Block(
        "ot_chip_pkg_ctrl", ["rtl/rom/ot_rom_pkg_ctrl.sv", "rtl/chip/ot_chip_pkg_ctrl.sv"],
        140.0, 140.0,
        [(r"^(in_|out_)", "W"), (r"^vm_", "E"), (r"^core_", "N")],
        default_edge="N",
        record="results/physical_abi3/asap7/rom/ot_rom_pkg_ctrl/physical.json",
        notes="package controller, superset role; 3.4k um2 of cells, ~2,200 pins"),
    "ot_chip_router": Block(
        "ot_chip_router", ["rtl/rom/ot_rom_fabric_router.sv", "rtl/chip/ot_chip_router.sv"],
        200.0, 200.0,
        # port p of the 5-port router is bits [p*512, p*512+511] of in_/out_data
        [(r"^(in_data|out_data)$", "E", 0, 511), (r"^(in_data|out_data)$", "N", 512, 1023),
         (r"^(in_data|out_data)$", "E", 1024, 1535), (r"^(in_data|out_data)$", "S", 1536, 2047),
         (r"^(in_data|out_data)$", "W", 2048, 2559), (r"^cfg_", "W")],
        default_edge="E",
        record="results/physical_abi3/asap7/rom/ot_rom_fabric_router/physical.json",
        notes="5-port 512-bit mesh router; 10.1k um2 of cells, ~5,200 pins"),
}


V41_COMMON = [
    "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/proto/ot_fp32_mul_rne_pipe.sv", "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_sfu.sv",
    "rtl/hdc/ot_hdc_reduce.sv",
]
BLOCKS.update({
    "ot_hdc_v41_stream": Block(
        "ot_hdc_v41_stream", V41_COMMON + [
            "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv", "rtl/hdc/v41/ot_hdc_softplus.sv",
            "rtl/hdc/v41/ot_hdc_v41_stream.sv"],
        460.0, 460.0,
        [(r"^(vm_|vi_|red_)", "W"), (r"^(wrom_|cr_)", "N"), (r"^kv_", "W")],
        notes="V4.1 four-operand stream unit; 88.1k um2 of cells flat (routed at 848 MHz flat)"),
    "ot_hdc_v41_qe": Block(
        "ot_hdc_v41_qe", V41_COMMON + [
            "rtl/hdc/v41/ot_hdc_blockdot.sv", "rtl/hdc/v41/ot_hdc_actquant.sv", "rtl/hdc/v41/ot_hdc_fp4qdq.sv",
            "rtl/hdc/v41/ot_hdc_v41_qe.sv"],
        420.0, 420.0,
        [(r"^qr_", "N"), (r"^(vi_|xr_|w_)", "W")],
        notes="V4.1 quantised block-dot engine; 53.8k um2 of cells after synthesis"),
    "ot_hdc_v41_xu": Block(
        "ot_hdc_v41_xu", V41_COMMON + [
            "rtl/hdc/v41/ot_hdc_engram_tables_pkg.sv", "rtl/hdc/v41/ot_hdc_engram_hash.sv",
            "rtl/hdc/v41/ot_hdc_select.sv", "rtl/hdc/v41/ot_hdc_sk_arith.sv",
            "rtl/hdc/v41/ot_hdc_sk_recip_rom.sv", "rtl/hdc/v41/ot_hdc_sinkhorn.sv",
            "rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv", "rtl/hdc/v41/ot_hdc_v41_xu.sv"],
        480.0, 480.0,
        [(r"^er_", "N"), (r"^(vr_|xr_|vw_|w_)", "W")],
        notes="V4.1 select / Sinkhorn / Engram unit; the Sinkhorn runs on a divided clock (1/7)"),
    "ot_hdc_v41_hcproj": Block(
        "ot_hdc_v41_hcproj", V41_COMMON + ["rtl/hdc/v41/ot_hdc_v41_hcproj.sv"],
        160.0, 160.0,
        [(r"^hr_", "N"), (r"^(x_|o_)", "W")],
        notes="V4.1 hyper-connection projection (3 FP32 lanes)"),
})


def edge_of(block: Block, port: str, bit: int | None) -> str:
    import re
    for rule in block.pin_edges:
        pattern, edge, *rng = rule
        if re.search(pattern, port):
            if rng and bit is not None and not (rng[0] <= bit <= rng[1]):
                continue
            if rng and bit is None:
                continue
            return edge
    return block.default_edge


# --------------------------------------------------------------------------
# Placeholder memories of the tile
# --------------------------------------------------------------------------

def tile_memories(arch: str) -> dict[str, mc.MacroSpec]:
    """The placeholder memories of the HDC tile for one architecture."""
    P = mc.pins
    out: dict[str, mc.MacroSpec] = {}

    def fit(name, bits, pins_, kind, factor=1.0, rom=False, aspect=1.0, min_w=0.0, min_h=0.0,
            basis=""):
        area = mc.rom_area_um2(bits) if rom else mc.sram_area_um2(bits, factor)
        w, h = mc.square_for_area(area, aspect)
        w, h = max(w, mc.snap(min_w, mc.SITE_W)), max(h, mc.snap(min_h, mc.SITE_H))
        spec = mc.MacroSpec(name, w, h, pins_, kind=kind, basis=basis,
                            extra={"capacity_bits": bits, "port_factor": factor})
        mc.pin_rects(spec)  # raises when the pins do not fit the edges
        out[name] = spec

    fit("ot_mem_prog", 4096 * 1024,
        P(("re", "input", 1, "S"), ("addr", "input", 12, "S"), ("q", "output", 1024, "S")),
        "rom", rom=True, aspect=200 / 272, min_w=200,
        basis="program ROM, 4,096 x 1,024-bit instructions, via-programmed ROM density")
    fit("ot_mem_crom", 4096 * 64,
        P(("re", "input", 1, "W"), ("addr", "input", 12, "W"), ("q", "output", 64, "W")),
        "rom", rom=True, basis="constant ROM, 4,096 x 64 bits")
    fit("ot_mem_vmem", 16384 * 32,
        P(("x_re", "input", 4, "W"), ("x_addr", "input", 56, "W"), ("x_q", "output", 128, "W"),
          ("me_we", "input", 4, "W"), ("me_addr", "input", 40, "W"), ("me_mask", "input", 64, "W"),
          ("me_data", "input", 2048, "W"),
          ("a_re", "input", 1, "E"), ("a_addr", "input", 14, "E"), ("a_q", "output", 32, "E"),
          ("b_re", "input", 1, "E"), ("b_addr", "input", 14, "E"), ("b_q", "output", 32, "E"),
          ("c_re", "input", 1, "E"), ("c_addr", "input", 14, "E"), ("c_q", "output", 32, "E"),
          ("su_we", "input", 1, "E"), ("su_addr", "input", 14, "E"), ("su_data", "input", 32, "E"),
          ("rd_we", "input", 1, "E"), ("rd_addr", "input", 14, "E"), ("rd_data", "input", 32, "E"),
          ("w_we", "input", 1, "S"), ("w_addr", "input", 10, "S"), ("w_data", "input", 512, "S"),
          ("r_re", "input", 1, "S"), ("r_addr", "input", 10, "S"), ("r_q", "output", 512, "S")),
        "sram", factor=2.5, aspect=140 / 400, min_h=400,
        basis=("vector memory, 16,384 FP32 elements; 7 element read ports, 4 masked word and "
               "2 element write ports, 1 word read and 1 word write port for the controller; "
               "fakeram7 bit density x 2.5 for the ports"))
    fit("ot_mem_kvwin", 4 * 256 * 256,
        P(("we", "input", 4, "W"), ("waddr", "input", 32, "W"), ("wdata", "input", 1024, "W"),
          ("re", "input", 1, "W"), ("raddr", "input", 8, "W"), ("q", "output", 1024, "W")),
        "sram", factor=1.3, aspect=70 / 200, min_h=200,
        basis="KV window, 4 banks x 256 x 256 bits, one read and one write port (x1.3)")
    fit("ot_mem_kvtail", 2 * 128 * 256,
        P(("we", "input", 2, "W"), ("waddr", "input", 14, "W"), ("wmask", "input", 32, "W"),
          ("wdata", "input", 512, "W"), ("re", "input", 2, "W"), ("raddr", "input", 14, "W"),
          ("q", "output", 512, "W")),
        "sram", factor=1.3, aspect=25 / 200, min_h=200,
        basis="KV tail, 2 banks x 128 x 256 bits with a 16-bit lane write mask (x1.3)")
    if arch in ("qwen_rom", "v41_rom"):
        cap_bits = WEIGHT_STORE_BITS[arch]
        fit("ot_mem_wstore", cap_bits,
            P(("re", "input", 1, "S"), ("addr", "input", 17, "S"), ("q", "output", 1024, "S")),
            "rom", rom=True, aspect=990 / 1760,
            basis=(f"weight ROM bank, {cap_bits / 8 / 2**20:.1f} MiB per tile, one 1,024-bit "
                   "read port, via-programmed ROM density; a real bank is sub-banked behind "
                   "this 1-cycle port"))
    else:
        fit("ot_mem_wstore", 2 * 64 * 1024 * 8,
            P(("re", "input", 1, "S"), ("addr", "input", 17, "S"), ("q", "output", 1024, "S")),
            "sram", factor=1.3, aspect=990 / 140,
            basis=("HBM weight prefetch buffer, 2 x 64 KiB double buffer; its HBM fill port is "
                   "not in the RTL (no weight streamer exists yet)"))
    return out


# Per-tile weight capacity (bits): model bytes / tiles on the full die.
# Qwen3-8B: 8.19e9 parameters at 4 bits (HC1-class ROM formats) over 256
# tiles (16,384 lanes of 64-lane cores, docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md).
QWEN_PARAMS = 8.19e9
QWEN_WEIGHT_BITS = 4
QWEN_TILES_FULL = 256
WEIGHT_STORE_BITS = {
    "qwen_rom": int(QWEN_PARAMS * QWEN_WEIGHT_BITS / QWEN_TILES_FULL),
    "v41_rom": int(QWEN_PARAMS * QWEN_WEIGHT_BITS / QWEN_TILES_FULL),
}


# --------------------------------------------------------------------------
# The tile floorplan
# --------------------------------------------------------------------------

@dataclass
class Placement:
    inst: str          # instance path in the flattened parent netlist
    master: str
    x: float
    y: float
    orient: str = "R0"


@dataclass
class TileFloorplan:
    arch: str
    width_um: float
    height_um: float
    placements: list[Placement]
    glue_center: tuple[float, float]      # where the flat glue logic is expected
    pin_groups: list[dict[str, Any]]      # tile pins: {"regex", "edge", "range", "bits"?}
    notes: str = ""

    def placement(self, master: str) -> Placement:
        return next(p for p in self.placements if p.master == master)


def hdc_tile(arch: str) -> TileFloorplan:
    """The HDC tile (Qwen ROM die, HBM die): see the module docstring's sketch."""
    mem = tile_memories(arch)
    ws = mem["ot_mem_wstore"]
    place = [
        Placement("u_router", "ot_chip_router", 10, 10),
        Placement("u_ctrl", "ot_chip_pkg_ctrl", 230, 40),
        Placement("u_kvs", "ot_hdc_kv_stream", 620, 20),
        Placement("u_kvwin", "ot_mem_kvwin", 840, 20),
        Placement("u_kvtail", "ot_mem_kvtail", 930, 20),
        Placement("u_crom", "ot_mem_crom", 1080, 20),
        Placement("u_prog", "ot_mem_prog", 10, 330),
        Placement("u_core.u_me", "ot_hdc_matvec", 230, 270),
        Placement("u_vmem", "ot_mem_vmem", 650, 270),
        Placement("u_core.u_su", "ot_hdc_stream", 810, 310),
        Placement("u_wstore", "ot_mem_wstore", 10, 690),
    ]
    width = 1160.0
    height = round(690 + ws.height_um + 12, 1)
    return TileFloorplan(
        arch=arch, width_um=width, height_um=height, placements=place,
        glue_center=(500.0, 140.0),
        pin_groups=[
            # mesh port p: [0] N, [1] E, [2] S, [3] W, 512-bit data per port
            {"regex": r"^m_(out|in)_data$", "bits": (0, 511), "edge": "N", "range": (995, 1150)},
            {"regex": r"^m_(out|in)_(valid|last|cr)$", "bits": (0, 0), "edge": "N", "range": (995, 1150)},
            {"regex": r"^m_(out|in)_data$", "bits": (512, 1023), "edge": "E", "range": (250, 680)},
            {"regex": r"^m_(out|in)_(valid|last|cr)$", "bits": (1, 1), "edge": "E", "range": (250, 680)},
            {"regex": r"^m_(out|in)_data$", "bits": (1024, 1535), "edge": "S", "range": (10, 580)},
            {"regex": r"^m_(out|in)_(valid|last|cr)$", "bits": (2, 2), "edge": "S", "range": (10, 580)},
            {"regex": r"^m_(out|in)_data$", "bits": (1536, 2047), "edge": "W", "range": (10, 260)},
            {"regex": r"^m_(out|in)_(valid|last|cr)$", "bits": (3, 3), "edge": "W", "range": (10, 260)},
            {"regex": r"^(hq_|hr_)", "edge": "S", "range": (600, 1150)},
            {"regex": r".", "edge": "W", "range": (270, 680)},
        ],
        notes=("router, controller and KV streamer in the south row; the weight store fills the "
               "north; the north mesh port runs up the east channel beside it"),
    )


# --------------------------------------------------------------------------
# The reduced (2 x 2) die
# --------------------------------------------------------------------------

GAP_UM = 20.0
EDGE_UM = 10.0
PHY_STRIP_UM = 900.0                       # south / north PHY strip depth
UCIE_W_UM = 560.0                          # UCIe-A x64 module: ~0.5 mm2, folded to the tile's S port
HBM_SLICE_W_UM = 550.0                     # HBM3E PHY + controller slice serving one tile
SERDES_W_UM, SERDES_H_UM = 600.0, 260.0   # 8-lane board SerDes slice
PHY_CLK_TO_Q_NS = 0.100                    # registered digital interface of a PHY
PHY_SETUP_NS = 0.050


@dataclass
class DieFloorplan:
    arch: str
    width_um: float
    height_um: float
    placements: list[Placement]
    phys: dict[str, mc.MacroSpec]
    tile: TileFloorplan
    notes: str = ""


def _link_pins(span: tuple[float, float] | None, edge: str) -> list[mc.Pin]:
    return mc.pins(("tx_valid", "input", 1, edge), ("tx_data", "input", 512, edge),
                   ("tx_last", "input", 1, edge), ("tx_cr", "output", 1, edge),
                   ("rx_valid", "output", 1, edge), ("rx_data", "output", 512, edge),
                   ("rx_last", "output", 1, edge), ("rx_cr", "input", 1, edge)) if span is None else [
        mc.Pin(n, d, w, edge, span=span) for n, d, w in (
            ("tx_valid", "input", 1), ("tx_data", "input", 512), ("tx_last", "input", 1),
            ("tx_cr", "output", 1), ("rx_valid", "output", 1), ("rx_data", "output", 512),
            ("rx_last", "output", 1), ("rx_cr", "input", 1))]


def die2x2(arch: str) -> DieFloorplan:
    """The reduced die: 2 x 2 mirrored tiles; south and north PHY strips
    holding, under each tile, a UCIe module (its S mesh port) and an HBM
    slice (its KV request/response port); board SerDes on the west and east
    edges beside each tile's W mesh port."""
    tile = hdc_tile(arch)
    tw, th = tile.width_um, tile.height_um
    x0 = EDGE_UM + SERDES_W_UM + GAP_UM
    x1 = x0 + tw + GAP_UM
    y0 = EDGE_UM + PHY_STRIP_UM + GAP_UM
    y1 = y0 + th + GAP_UM
    die_w = x1 + tw + GAP_UM + SERDES_W_UM + EDGE_UM
    die_h = y1 + th + GAP_UM + PHY_STRIP_UM + EDGE_UM
    rng = {g.get("bits", g["regex"]): g["range"] for g in tile.pin_groups}
    s_lo, s_hi = rng[(1024, 1535)]
    w_lo, w_hi = rng[(1536, 2047)]
    h_lo, h_hi = rng[r"^(hq_|hr_)"]
    hbm_pins = [mc.Pin(n, d, w, "N", span=(5.0, HBM_SLICE_W_UM - 5.0)) for n, d, w in (
        ("hq_v", "input", 1), ("hq_rdy", "output", 1), ("hq_we", "input", 1), ("hq_addr", "input", 24),
        ("hq_len", "input", 5), ("hq_tag", "input", 14), ("hq_wdata", "input", 256),
        ("hr_v", "output", 4), ("hr_rdy", "input", 4), ("hr_tag", "output", 56),
        ("hr_beat", "output", 16), ("hr_data", "output", 1024))]
    phys = {
        "ot_phy_hbm": mc.MacroSpec(
            "ot_phy_hbm", HBM_SLICE_W_UM, PHY_STRIP_UM, hbm_pins,
            clk_to_q_ns=PHY_CLK_TO_Q_NS, setup_ns=PHY_SETUP_NS, kind="phy",
            basis=("HBM3E PHY and controller slice serving one tile's KV request/response port, "
                   "0.55 mm x 0.9 mm; the full die's PHY area is in the full-die floorplan")),
        "ot_phy_ucie": mc.MacroSpec(
            "ot_phy_ucie", UCIE_W_UM, PHY_STRIP_UM, _link_pins((5.0, UCIE_W_UM - 5.0), "N"),
            clk_to_q_ns=PHY_CLK_TO_Q_NS, setup_ns=PHY_SETUP_NS, kind="phy",
            basis="UCIe-A x64 die-to-die module (package link), ~0.5 mm2, 0.56 mm x 0.9 mm here"),
        "ot_phy_serdes": mc.MacroSpec(
            "ot_phy_serdes", SERDES_W_UM, SERDES_H_UM, _link_pins((w_lo + 5, w_hi - 5), "E"),
            clk_to_q_ns=PHY_CLK_TO_Q_NS, setup_ns=PHY_SETUP_NS, kind="phy",
            basis="8-lane board SerDes slice (package-to-package ring link), 0.6 mm x 0.26 mm"),
    }
    for spec in phys.values():
        mc.pin_rects(spec)
    ex = EDGE_UM
    top = die_h - ex - PHY_STRIP_UM

    def col_x(c: int, lo: float, width: float) -> float:
        # column 1 is mirrored (MY): a tile-local x maps to x1 + tw - x
        return x0 + lo if c == 0 else x1 + tw - lo - width

    place = [
        Placement("g_tile[0].u_tile", "ot_chip_hdc_tile", x0, y0, "R0"),
        Placement("g_tile[1].u_tile", "ot_chip_hdc_tile", x1, y0, "MY"),
        Placement("g_tile[2].u_tile", "ot_chip_hdc_tile", x0, y1, "MX"),
        Placement("g_tile[3].u_tile", "ot_chip_hdc_tile", x1, y1, "R180"),
    ]
    orients = {(0, 0): "R0", (1, 0): "MY", (0, 1): "MX", (1, 1): "R180"}
    for t, (c, r) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
        orient = orients[(c, r)]
        y_strip = ex if r == 0 else top
        u_mid = (s_lo + s_hi) / 2
        place.append(Placement("g_edge[%d].u_ucie" % t, "ot_phy_ucie",
                               col_x(c, u_mid - UCIE_W_UM / 2, UCIE_W_UM), y_strip, orient))
        h_mid = (h_lo + h_hi) / 2
        place.append(Placement("g_hbm[%d].u_hbm" % t, "ot_phy_hbm",
                               col_x(c, h_mid - HBM_SLICE_W_UM / 2, HBM_SLICE_W_UM), y_strip, orient))
        xs = ex if c == 0 else die_w - ex - SERDES_W_UM
        ys = y0 if r == 0 else y1 + th - SERDES_H_UM
        place.append(Placement("g_edge[%d].u_serdes" % t, "ot_phy_serdes", xs, ys, orient))
    return DieFloorplan(arch, round(die_w, 3), round(die_h, 3), place, phys, tile,
                        notes="tiles mirrored MY in column 1 and MX in row 1 (tile flipping)")
