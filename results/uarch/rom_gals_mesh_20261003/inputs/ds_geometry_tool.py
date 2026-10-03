#!/usr/bin/env python3
"""Die-level feasibility runs for the DeepSeek-V4.1 ROM die (DS4096-TP4-S58-PAR2-NP2048, shard 0).

The die is the literal parent map of results/uarch/dsrom_noECC_complete_parent_map_20261002/r2 (Maxwell's
reticle placement: 2,048 field element frames, 14,336 cfg ROM macros, four field bands, fourteen service
rectangles, 33 x 26 mm) plus the capture home and the recorded stage-link shores.  Every element and
service is a BLACK BOX; nothing inside an element is re-implemented here.  Four job kinds:

  legal   real ASAP7 tech: every instance placed at its map origin, checked in OpenROAD for die
          containment, overlap, site/row grid, signal-pin-on-track per orientation, and DRT pin access.
          Variants: as-mapped origins, and origins snapped to the joint 54/48 nm grid.
  pdn     real ASAP7 tech: die mesh M8/M9 over the element M7 straps and cfg-band macro grids; static IR
          (PSM) with every black box carrying its share of the die power as liberty leakage, C4 bumps.
  grt     bundled tech (tools/chip_assembly/v41_die.py: pitches x k, buses as ceil(bits/k) nets):
          broadcast trunk + region relays, return tree (local-in-field or in-band), cfg word paths, root
          return to the VM, stage links, PAR2 UCIe, collective links, reset trunk; per-layer overflow.
  cts     real ASAP7 tech: one 1.2 GHz clock from a die-centre root to every element, cfg macro, band
          tile, service and the capture-home relay sites; insertion delay and skew at SS.

    python3 tools/dsrom_die_feasibility.py prepare --job grt --frame C --ret local --k 16 --out DIR
    python3 tools/dsrom_die_feasibility.py analyse --out FILE      # python-only legality screen
    python3 tools/dsrom_die_feasibility.py record --job grt --work DIR --out FILE
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "chip_assembly"))

MAP = "results/uarch/dsrom_noECC_complete_parent_map_20261002/r2"
CAPTURE_HOME = "results/uarch/dsrom_capture_home_20261002/handoff.json"
SPATIAL = "results/uarch/dsrom_capture_home_20261002/inputs/budget.json.gz"
RELAY_SITES = "results/uarch/dsrom_c9_clock_branch_site_binding_20261003/inputs/selected_shard0_sites.json.gz"
CFG_LEF = "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef"
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"

DIE_UM = (33000.0, 26000.0)
# q-element frames: C = original W10 frame (qframe C runs), D = enlarged WAKE-priced envelope (qframe D hook).
FRAMES = {"C": (510.84, 126.9), "D": (510.84, 151.2)}
BF_FRAME = (1002.89, 157.68)          # frames.json BF_priced_outline_um (map slot height)
Q_PIN_SPAN = (136.08, 374.76)         # qframe launch receipts: --pin-region top/bottom 136.08-374.76
HOTTEST_DIE_W = 204.0                 # user-assigned S58 hottest-die power for the IR run
VDD = 0.7
IR_BUDGET = 0.05                      # results/arch/v41_die_assembly.json constants.ir_budget_fraction
BUMP_PITCH_UM = 90.0                  # results/arch/v41_die_assembly.json vdd_bump_pitch_um

# Port widths (bits).  Element ports: rtl/v41rom/ot_v41_rom_elem_q_w10.sv and the field
# (dsrom_parallel_owner_binding_20261002/r1/ot_v41_field_w17w10.sv).
XS_BOT = 1 + 8 + 3 + 2 + 256 + 10 + 3          # xs_v xs_p xs_b xs_sv xs_q0 xs_e0 xs_pos  (bottom edge)
XS_TOP = 256 + 10                              # xs_q1 xs_e1                              (top edge)
XB = 3 + 1 + 3 + 4 + 32 + 1024                 # xb_pos xb_v xb_b xb_sv xb_u xb_d       (BF pairs only)
CTL = 1 + 1 + 1 + 6 + 3                        # rst_n go go_bf cfg_go cfg_ph cfg_np (field broadcast)
CFG = 1 + 5 + 48                               # cfg_v cfg_a cfg_d (local word path)
LEAF = 1 + 32 + 32 + 1                         # ret node port: v, t(32), d(32), e
PAIR_RET = 2 * LEAF                            # an element pair's two leaves
ROOT_OUT = 69                                  # ret_root: r_v r_row r_pos r_fp32 r_bf16 r_e
CFG_MACRO_OUT, CFG_MACRO_IN = 72, 12 + 1       # ot_rom_4096x72_m8 rd_out / addr_in + ce_in
LINK_BITS = 684                                # S58-NN stage link full duplex (budget.boundary)
PAR2_BITS = 4416 + 1681                        # dsrom_par2_boundary_20261003: return port + activation
N_COLL = 3                                     # TP4 fc4 quad: three peer links per rank die


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jload(rel: str):
    p = ROOT / rel
    return json.load(gzip.open(p)) if rel.endswith(".gz") else json.loads(p.read_text())


# ---------------------------------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------------------------------

class Inst:
    __slots__ = ("name", "master", "x", "y", "w", "h", "kind", "meta")

    def __init__(self, name, master, x, y, w, h, kind, **meta):
        self.name, self.master, self.x, self.y, self.w, self.h, self.kind = name, master, x, y, w, h, kind
        self.meta = meta

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


def snap(v: float, g_nm: int) -> float:
    return round(math.floor(round(v * 1000) / g_nm) * g_nm / 1000, 3)


def geometry(frame: str, snapped: bool) -> dict:
    """Instances from the literal parent map.  Element origins are the map origins; with snapped=True they
    move down to the joint 432 nm grid (lcm of the 54 nm site and the 48 nm M5 track), which the 8.64 um
    inter-frame gaps absorb."""
    qw, qh = FRAMES[frame]
    field = jload(f"{MAP}/field.json.gz")
    cfg = jload(f"{MAP}/cfg.json.gz")
    bands = jload(f"{MAP}/bands.json.gz")
    services = jload(f"{MAP}/services.json.gz")
    elems, cfgs, blocks = [], [], []
    for e in field:
        x0, y0, x1, y1 = (v / 1000 for v in e["bbox_DBU"])
        if snapped:
            x0 = snap(x0, 432)
        if e["source_class"] == "q_pair":
            elems.append(Inst(f"e{e['local_pair']}", f"dsq_elem_{frame}", x0, y0, qw, qh, "q",
                              pair=e["local_pair"], root=e["source_root"]))
        else:
            elems.append(Inst(f"e{e['local_pair']}", "dsbf_elem", x0, y0, BF_FRAME[0], BF_FRAME[1], "bf",
                              pair=e["local_pair"], root=e["source_root"]))
    cfg_w, cfg_h = 38.040, 62.952      # v2 aligned abstract (map slots are v1 38.016 x 62.910, pitch 47.52 x 73.44)
    for i, c in enumerate(cfg):
        x0, y0 = c["bbox_DBU"][0] / 1000, c["bbox_DBU"][1] / 1000
        cfgs.append(Inst(f"cfg{i}", "ot_rom_4096x72_m8", x0, y0, cfg_w, cfg_h, "cfg"))
    for b in bands:
        x0, y0, x1, y1 = (v / 1000 for v in b["bbox_DBU"])
        blocks.append(Inst(b["name"], "band_" + b["name"].lower(), x0, y0, x1 - x0, y1 - y0, "band"))
    for s in services:
        x0, y0, x1, y1 = (v / 1000 for v in s["bbox_DBU"])
        blocks.append(Inst(s["name"], "svc_" + s["name"].lower(), x0, y0, x1 - x0, y1 - y0, "svc"))
    ch = jload(CAPTURE_HOME)
    home = None
    for k in ("model_selected_capture_home_DBU",):
        if k in ch:
            home = ch[k]
    if home is None:   # initial_coordinate_fixture_FAIL.json actual_grid_derived_home_DBU (source-derived)
        home = jload("results/uarch/dsrom_capture_home_20261002/initial_coordinate_fixture_FAIL.json")[
            "actual_grid_derived_home_DBU"]
    x0, y0, x1, y1 = (v / 1000 for v in home)
    blocks.append(Inst("CAPTURE_HOME", "svc_capture_home", x0, y0, x1 - x0, y1 - y0, "svc"))
    sp = jload(SPATIAL)["spatial"]["proposed_east_west_strips_mm"]
    for nm, r in (("WEST_STAGE_PHY", sp["west"]), ("EAST_STAGE_PHY", sp["east"])):
        blocks.append(Inst(nm, "phy_stage", r[0] * 1000, r[1] * 1000, (r[2] - r[0]) * 1000, (r[3] - r[1]) * 1000,
                           "phy"))
    # Not in the parent map (assumptions, recorded): PAR2 UCIe PHY on the north edge above the hub, and
    # three TP4 collective PHYs east of it.  0.5 mm deep shore strips like the stage-link strips.
    blocks.append(Inst("PAR2_UCIE_PHY", "phy_ucie", 11000.0, 25500.0, 6000.0, 500.0, "phy"))
    for i in range(N_COLL):
        blocks.append(Inst(f"COLL_PHY{i}", "phy_coll", 17500.0 + 2000.0 * i, 25500.0, 1500.0, 500.0, "phy"))
    return {"elems": elems, "cfgs": cfgs, "blocks": blocks, "frame": frame, "snapped": snapped}


def overlaps(insts: list[Inst]) -> list[tuple[str, str]]:
    B = 500.0
    buckets = defaultdict(list)
    for i in insts:
        for gx in range(int(i.x // B), int((i.x + i.w) // B) + 1):
            for gy in range(int(i.y // B), int((i.y + i.h) // B) + 1):
                buckets[(gx, gy)].append(i)
    seen = set()
    for lst in buckets.values():
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                p, q = lst[a], lst[b]
                if p.x < q.x + q.w - 1e-6 and q.x < p.x + p.w - 1e-6 and p.y < q.y + q.h - 1e-6 and q.y < p.y + p.h - 1e-6:
                    seen.add(tuple(sorted((p.name, q.name))))
    return sorted(seen)


def analyse(out: Path) -> dict:
    """Python-only screen (seconds): containment, overlaps, site grid, M5/M4 track residues per frame."""
    rec = {"schema": "opentallas.dsrom.die_feasibility.legality_screen.v1", "variants": {}}
    for frame in FRAMES:
        for snapped in (False, True):
            g = geometry(frame, snapped)
            allx = g["elems"] + g["cfgs"] + g["blocks"]
            outside = [i.name for i in allx if i.x < 0 or i.y < 0 or i.x + i.w > DIE_UM[0] + 1e-6 or i.y + i.h > DIE_UM[1] + 1e-6]
            ov = overlaps(allx)
            ex = Counter((round(e.x * 1000) % 54 == 0, round(e.x * 1000) % 48 == 0, round(e.y * 1000) % 270 == 0)
                         for e in g["elems"])
            cx = Counter((round(c.x * 1000) % 54 == 0, round(c.y * 1000) % 270 == 0) for c in g["cfgs"])
            # cfg M4 pins: centre y = origin + 0.780 + n*0.096 (R0) -> on the M4 track (12 mod 48) iff origin y % 48 == 0
            cfg_m4 = Counter(round(c.y * 1000) % 48 == 0 for c in g["cfgs"])
            gaps = sorted({round(b.x - (a.x + a.w), 3) for a, b in zip(sorted(g["elems"], key=lambda e: (e.y, e.x)),
                                                                       sorted(g["elems"], key=lambda e: (e.y, e.x))[1:])
                           if abs(a.y - b.y) < 1e-6})
            rec["variants"][f"{frame}_{'snapped' if snapped else 'asmapped'}"] = {
                "instances": len(allx), "elements": len(g["elems"]), "cfg_macros": len(g["cfgs"]),
                "blocks": len(g["blocks"]), "outside_die": outside, "overlaps": len(ov), "overlap_examples": ov[:8],
                "element_grid_site54_track48_row270": {str(k): v for k, v in ex.items()},
                "element_on_joint_grid": sum(v for k, v in ex.items() if all(k)),
                "cfg_grid_site54_row270": {str(k): v for k, v in cx.items()},
                "cfg_M4_pins_on_track": cfg_m4.get(True, 0), "cfg_M4_pins_off_track": cfg_m4.get(False, 0),
                "min_same_row_element_gap_um": gaps[:3]}
    rec["inputs"] = {p: sha(ROOT / p) for p in (f"{MAP}/field.json.gz", f"{MAP}/cfg.json.gz", f"{MAP}/bands.json.gz",
                                                f"{MAP}/services.json.gz", SPATIAL, CFG_LEF)}
    out.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


# ---------------------------------------------------------------------------------------------------
# LEF writers
# ---------------------------------------------------------------------------------------------------

def lef_header() -> list[str]:
    return ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']


def rect(x0, y0, x1, y1) -> str:
    return f"      RECT {x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f} ;"


def pg_straps(w: float, h: float, pitch=10.8, off=1.0, width=0.288, space=0.096):
    """VDD/VSS M7 straps of the element PDN (tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl)."""
    vdd, vss = [], []
    x = off
    while x + 2 * width + space <= w - 0.2:
        vdd.append((x, 0.0, x + width, h))
        vss.append((x + width + space, 0.0, x + 2 * width + space, h))
        x += pitch
    return vdd, vss


def real_block_lef(name: str, w: float, h: float, pins: list[tuple], obs_top: int = 7) -> str:
    """Real-tech black box: signal pins [(name, dir, layer, x0, y0, x1, y1)], M7 VDD/VSS straps, OBS
    M1..M(obs_top) with the pin keep-outs and strap slots left open."""
    vdd, vss = pg_straps(w, h)
    L = lef_header() + [f"MACRO {name}", "  CLASS BLOCK ;", f"  FOREIGN {name} 0 0 ;", "  ORIGIN 0 0 ;",
                        f"  SIZE {w:.3f} BY {h:.3f} ;", "  SYMMETRY X Y ;"]
    for nm, d, lay, x0, y0, x1, y1 in pins:
        L += [f"  PIN {nm}", f"    DIRECTION {d} ;", "    USE SIGNAL ;", "    PORT", f"      LAYER {lay} ;",
              rect(x0, y0, x1, y1), "    END", f"  END {nm}"]
    for nm, rs, use in (("VDD", vdd, "POWER"), ("VSS", vss, "GROUND")):
        L += [f"  PIN {nm}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M7 ;"]
        L += [rect(*r) for r in rs] + ["    END", f"  END {nm}"]
    L += ["  OBS"]
    keep = defaultdict(list)
    for _nm, _d, lay, x0, y0, x1, y1 in pins:
        keep[lay].append((x0, y0, x1, y1))
    for li in range(1, obs_top + 1):
        lay = f"M{li}"
        L.append(f"    LAYER {lay} ;")
        if lay == "M7":
            straps = sorted(vdd + vss)
            x = 0.0
            for s in straps:
                if s[0] - 0.064 > x:
                    L.append(rect(x, 0, s[0] - 0.064, h))
                x = s[2] + 0.064
            if x < w:
                L.append(rect(x, 0, w, h))
        elif keep.get(lay):
            # edge pins: leave a 0.6 um band along the edges that carry pins; OBS covers the interior
            ys = [r[1] for r in keep[lay]] + [r[3] for r in keep[lay]]
            lo = 0.6 if min(ys) < 0.3 else 0.0
            hi = h - 0.6 if max(ys) > h - 0.3 else h
            L.append(rect(0, lo, w, hi))
            pins_bot = [r for r in keep[lay] if r[1] < 0.3]
            pins_top = [r for r in keep[lay] if r[3] > h - 0.3]
            for grp, (ya, yb) in ((pins_bot, (0, lo)), (pins_top, (hi, h))):
                if not grp or ya == yb:
                    continue
                xs = sorted(grp)
                cur = 0.0
                for r in xs:
                    if r[0] - 0.048 > cur:
                        L.append(rect(cur, ya, r[0] - 0.048, yb))
                    cur = r[2] + 0.048
                if cur < w:
                    L.append(rect(cur, ya, w, yb))
        else:
            L.append(rect(0, 0, w, h))
    L += ["  END", f"END {name}", "END LIBRARY", ""]
    return "\n".join(L)


def edge_pins_real(names_dirs: list[tuple[str, str]], w: float, h: float, edge: str, span: tuple[float, float]):
    """Signal pins on M5 tracks (element-local 0.012 + 0.048 n) spread evenly over the edge span."""
    n = len(names_dirs)
    t0 = math.ceil((span[0] - 0.012) / 0.048)
    t1 = math.floor((span[1] - 0.012) / 0.048)
    step = (t1 - t0) / max(1, n)
    if step < 2:
        raise ValueError(f"{n} pins exceed the {span} edge span at 2 tracks per pin")
    out = []
    for i, (nm, d) in enumerate(names_dirs):
        xc = 0.012 + 0.048 * (t0 + int(i * step))
        y0, y1 = (0.0, 0.192) if edge == "bottom" else (h - 0.192, h)
        out.append((nm, d, "M5", xc - 0.012, y0, xc + 0.012, y1))
    return out


def bus(nm: str, n: int) -> list[str]:
    return [f"{nm}[{i}]" for i in range(n)]


def element_ports(kind: str):
    bot = [(p, "INPUT") for p in ["clk"] + bus("xs_bot", XS_BOT) + bus("ctl", CTL) + bus("cfg", CFG)]
    if kind == "bf":
        bot += [(p, "INPUT") for p in bus("xb", XB)]
    top = [(p, "INPUT") for p in bus("xs_top", XS_TOP)] + [(p, "OUTPUT") for p in bus("ret", PAIR_RET) + ["busy", "fault"]]
    return bot, top


def element_real_lef(name: str, kind: str, w: float, h: float) -> str:
    bot, top = element_ports(kind)
    if kind == "q":
        span = Q_PIN_SPAN
    else:   # BF pair: same relative span as q scaled to the wider frame, widened to fit 1,616+ input pins
        span = (0.05 * w, 0.95 * w)
    pins = edge_pins_real(bot, w, h, "bottom", span) + edge_pins_real(top, w, h, "top", span)
    return real_block_lef(name, w, h, pins)


def area_pins_real(names_dirs, w, h, layer="M8"):
    """Synthetic service/band blocks: pins on M8 over the block area on the 0.080 um M8 track grid."""
    n = len(names_dirs)
    if n == 0:
        return []
    cols = max(1, int(math.sqrt(n * w / h)))
    rows = math.ceil(n / cols)
    out = []
    for i, (nm, d) in enumerate(names_dirs):
        c, r = i % cols, i // cols
        x = (c + 0.5) * w / cols
        y = (r + 0.5) * h / rows
        yt = 0.116 + 0.080 * round((y - 0.116) / 0.080)
        out.append((nm, d, layer, round(x - 0.2, 3), round(yt - 0.020, 3), round(x + 0.2, 3), round(yt + 0.020, 3)))
    return out


# ---------------------------------------------------------------------------------------------------
# Bundled GRT case
# ---------------------------------------------------------------------------------------------------

class Net:
    __slots__ = ("id", "bits", "src", "dsts", "cls")

    def __init__(self, id, bits, src, dsts, cls):
        self.id, self.bits, self.src, self.dsts, self.cls = id, bits, src, dsts, cls


def build_grt(g: dict, ret: str) -> tuple[list[Inst], list[Net]]:
    """Top-level connectivity.  (inst, port) endpoints; every Net is one bus of `bits` wires."""
    elems = sorted(g["elems"], key=lambda e: e.meta["pair"])
    blocks = {b.name: b for b in g["blocks"]}
    insts: list[Inst] = list(elems) + list(g["cfgs"]) + list(g["blocks"])
    nets: list[Net] = []
    byroot = defaultdict(list)
    for e in elems:
        byroot[e.meta["root"]].append(e)
    rows = sorted({e.y for e in elems})
    row_top = {y: y + BF_FRAME[1] for y in rows}        # channel above a field row: [y+157.68, y+166.32)
    vm = "HUB_VM"
    band = blocks["DECLARED_RETURN_FF50"]
    occupied = defaultdict(list)                         # channel y -> [(x0, x1)]

    def chan_place(name, master, x, y_chan, w, h, kind, **meta):
        """Place a small block in the channel row y_chan near x without overlapping earlier ones."""
        x = max(0.0, min(DIE_UM[0] - w, x - w / 2))
        for _ in range(4000):
            if all(x + w <= a or x >= b for a, b in occupied[y_chan]):
                break
            x += w
            if x + w > DIE_UM[0]:
                x = 0.0
        occupied[y_chan].append((x, x + w))
        i = Inst(name, master, round(x, 3), round(y_chan, 3), w, h, kind, **meta)
        insts.append(i)
        return i

    # -- broadcast: VM -> 64 region relays -> elements (xs both edges, ctl; xb only to BF pairs) --------
    relays = {}
    for r, es in sorted(byroot.items()):
        y = min(e.y for e in es)
        xs = sorted(e.cx for e in es if e.y == y)
        relays[r] = chan_place(f"relay{r}", "ds_relay", xs[len(xs) // 2], row_top[y] + 0.0, 86.4, 8.64, "relay", root=r)
    nets.append(Net("bc_xs", XS_BOT + XS_TOP, (vm, "bc_xs"), [(relays[r].name, "i_xs") for r in relays], "broadcast_trunk"))
    nets.append(Net("bc_xb", XB, (vm, "bc_xb"), [(relays[r].name, "i_xb") for r in relays], "broadcast_trunk"))
    nets.append(Net("bc_ctl", CTL, (vm, "bc_ctl"), [(relays[r].name, "i_ctl") for r in relays], "reset_ctl_trunk"))
    for r, es in byroot.items():
        nets.append(Net(f"r{r}_xs_bot", XS_BOT, (relays[r].name, "o_xs_bot"), [(e.name, "xs_bot") for e in es], "broadcast_region"))
        nets.append(Net(f"r{r}_xs_top", XS_TOP, (relays[r].name, "o_xs_top"), [(e.name, "xs_top") for e in es], "broadcast_region"))
        nets.append(Net(f"r{r}_ctl", CTL, (relays[r].name, "o_ctl"), [(e.name, "ctl") for e in es], "reset_ctl_region"))
        bfs = [(e.name, "xb") for e in es if e.kind == "bf"]
        if bfs:
            nets.append(Net(f"r{r}_xb", XB, (relays[r].name, "o_xb"), bfs, "broadcast_region"))
    # -- return tree: pair leaves -> binary tree per region -> root -> return band tile -> VM ---------
    tiles = {}
    for r in byroot:
        tw = DIE_UM[0] / 64
        tiles[r] = Inst(f"rtile{r}", "ds_rtile", round(r * tw + 2.0, 3), band.y + 2.0, round(tw - 4.0, 3),
                        band.h - 4.0, "rtile", root=r)
        insts.append(tiles[r])
    band_slot = (band.h - 4.0) / 64
    for r, es in sorted(byroot.items()):
        es = sorted(es, key=lambda e: e.meta["pair"])

        def node_pos(xc, ych):
            if ret == "band":
                return xc, band.y + 2.0 + r * band_slot
            return xc, ych
        level = []
        for e in es:               # level-0 node: the pair's two leaves
            xc, yc = node_pos(e.cx, row_top[e.y])
            if ret == "band":
                n = Inst(f"n{r}_0_{e.meta['pair']}", "ds_retn", round(xc - 4.32, 3), round(yc, 3), 8.64, min(8.64, band_slot), "retn")
                insts.append(n)
            else:
                n = chan_place(f"n{r}_0_{e.meta['pair']}", "ds_retn", xc, yc, 8.64, 8.64, "retn")
            nets.append(Net(f"{e.name}_ret", PAIR_RET, (e.name, "ret"), [(n.name, "a")], "return_leaf"))
            level.append(n)
        lv = 1
        while len(level) > 1:
            nxt = []
            for j in range(0, len(level), 2):
                a, b = level[j], level[j + 1]
                xc, yc = node_pos((a.cx + b.cx) / 2, a.y)
                if ret == "band":
                    n = Inst(f"n{r}_{lv}_{j // 2}", "ds_retn", round(xc - 4.32, 3), round(yc, 3), 8.64, min(8.64, band_slot), "retn")
                    insts.append(n)
                else:
                    n = chan_place(f"n{r}_{lv}_{j // 2}", "ds_retn", xc, yc, 8.64, 8.64, "retn")
                nets.append(Net(f"{a.name}_o", LEAF, (a.name, "o"), [(n.name, "a")], "return_tree"))
                nets.append(Net(f"{b.name}_o", LEAF, (b.name, "o"), [(n.name, "b")], "return_tree"))
                nxt.append(n)
            level, lv = nxt, lv + 1
        top = level[0]
        nets.append(Net(f"root{r}", ROOT_OUT, (top.name, "o"), [(tiles[r].name, "i")], "return_root"))
        nets.append(Net(f"rtile{r}_vm", ROOT_OUT, (tiles[r].name, "o"), [(vm, f"ret{r}")], "return_to_vm"))
    # -- cfg: 7 cfg macros -> word-mux slot -> element ------------------------------------------------
    wm = blocks["CFG_LOCAL_WORDMUX"]
    cfgs = sorted(g["cfgs"], key=lambda c: (round(c.x, 1), c.y))
    es_x = sorted(elems, key=lambda e: (e.cx, e.y))
    per = len(cfgs) // len(es_x)
    slot_w = DIE_UM[0] / len(es_x)
    for k, e in enumerate(es_x):
        grp = cfgs[k * per:(k + 1) * per]
        s = Inst(f"wm{k}", "ds_wmux", round(k * slot_w, 3), wm.y, round(slot_w - 0.1, 3), wm.h, "wmux")
        insts.append(s)
        for j, c in enumerate(grp):
            nets.append(Net(f"{c.name}_d", CFG_MACRO_OUT, (c.name, "rd_out"), [(s.name, f"d{j}")], "cfg_macro_to_wordmux"))
            nets.append(Net(f"{c.name}_a", CFG_MACRO_IN, (s.name, f"a{j}"), [(c.name, "addr_in")], "cfg_macro_to_wordmux"))
        nets.append(Net(f"{e.name}_cfg", CFG, (s.name, "o"), [(e.name, "cfg")], "cfg_word_to_element"))
    # -- links ------------------------------------------------------------------------------------------
    nets.append(Net("stage_in", LINK_BITS, ("WEST_STAGE_PHY", "l"), [(vm, "stage_in")], "stage_link"))
    nets.append(Net("stage_out", LINK_BITS, (vm, "stage_out"), [("EAST_STAGE_PHY", "l")], "stage_link"))
    nets.append(Net("par2", PAR2_BITS, ("PAR2_UCIE_PHY", "l"), [(vm, "par2")], "par2_ucie"))
    for i in range(N_COLL):
        nets.append(Net(f"coll{i}", LINK_BITS, ("HUB_COLLECTIVE", f"c{i}"), [(f"COLL_PHY{i}", "l")], "collective_link"))
    return [i for i in insts if i.name not in ("CFG_LOCAL_WORDMUX", "DECLARED_RETURN_FF50")], nets


def write_grt_case(work: Path, frame: str, ret: str, k: int, m89_reserve: float, low_adjust: float, snapped: bool):
    import v41_die as VD
    work.mkdir(parents=True, exist_ok=True)
    g = geometry(frame, snapped)
    insts, nets = build_grt(g, ret)
    nb = lambda bits: max(1, math.ceil(bits / k))
    # ports per instance: name -> [(port, nbundles, dir)]
    ports = defaultdict(dict)
    for n in nets:
        ports[n.src[0]][n.src[1]] = (nb(n.bits), "OUTPUT")
        for d in n.dsts:
            ports[d[0]][d[1]] = (nb(n.bits), "INPUT")
    byname = {i.name: i for i in insts}
    for nm in ports:
        if nm not in byname:
            raise KeyError(nm)
    # one master per instance class; element/macro masters share a port set, others get per-instance masters
    lefs, masters = [], {}
    pk = 0.048 * k
    for i in insts:
        pl = ports.get(i.name, {})
        if i.kind in ("q", "bf", "cfg"):
            key = i.master + "_b"
        else:
            key = f"b_{i.name}"
        masters[i.name] = key
        if any(l.startswith(f"MACRO {key}\n") for l in lefs):
            continue
        L = [f"MACRO {key}", "  CLASS BLOCK ;", f"  FOREIGN {key} 0 0 ;", "  ORIGIN 0 0 ;",
             f"  SIZE {i.w:.3f} BY {i.h:.3f} ;", "  SYMMETRY X Y ;"]
        pins = []
        if i.kind in ("q", "bf"):
            bot = [p for p in pl if p in ("xs_bot", "ctl", "cfg", "xb")]
            topp = [p for p in pl if p in ("xs_top", "ret")]
            span = Q_PIN_SPAN if i.kind == "q" else (0.05 * i.w, 0.95 * i.w)
            for edge, plist in (("bottom", bot), ("top", topp)):
                names = [(f"{p}[{b}]", pl[p][1]) for p in plist for b in range(pl[p][0])]
                t0 = math.ceil(span[0] / pk)
                t1 = math.floor(span[1] / pk)
                step = (t1 - t0) / max(1, len(names))
                if step < 1:
                    raise ValueError(f"{key}: {len(names)} bundle pins exceed {t1 - t0} bundled tracks")
                for j, (nm, d) in enumerate(names):
                    xc = (t0 + int(j * step) + 0.25) * pk
                    y0, y1 = (0.0, pk) if edge == "bottom" else (i.h - pk, i.h)
                    pins.append((nm, d, "M5", xc - pk / 4, y0, xc + pk / 4, y1))
        elif i.kind == "cfg":    # real pins: M4 on the left (inputs) and right (outputs) edges, low y
            for p, (n, d) in pl.items():
                for b in range(n):
                    yc = 0.768 + (b + 0.5) * 0.048 * k
                    x0, x1 = (0.0, pk) if d == "INPUT" else (i.w - pk, i.w)
                    pins.append((f"{p}[{b}]", d, "M4", x0, yc - pk / 4, x1, yc + pk / 4))
        else:                    # synthetic blocks: M8 area pins on the bundled M8 grid
            names = [(f"{p}[{b}]", d) for p, (n, d) in pl.items() for b in range(n)]
            p8 = 0.080 * k
            cols = max(1, int(i.w / p8) - 1)
            rows_ = max(1, int(i.h / p8) - 1)
            if len(names) > cols * rows_:
                raise ValueError(f"{key}: {len(names)} pins > {cols * rows_} M8 grid points")
            # spread over the area
            stepc = max(1, int(math.sqrt(cols * rows_ / max(1, len(names)))))
            pts = [(c, r) for r in range(0, rows_, stepc) for c in range(0, cols, stepc)]
            if len(pts) < len(names):
                pts = [(c, r) for r in range(rows_) for c in range(cols)]
            for (nm, d), (c, r) in zip(names, pts):
                xc, yc = (c + 1) * p8, (r + 1) * p8
                pins.append((nm, d, "M8", xc - p8 / 4, yc - p8 / 4, xc + p8 / 4, yc + p8 / 4))
        for nm, d, lay, x0, y0, x1, y1 in pins:
            L += [f"  PIN {nm}", f"    DIRECTION {d} ;", "    USE SIGNAL ;", "    PORT", f"      LAYER {lay} ;",
                  rect(x0, y0, x1, y1), "    END", f"  END {nm}"]
        obs_top = 4 if i.kind == "cfg" else 7
        L += ["  OBS"]
        for li in range(1, obs_top + 1):
            lay = f"M{li}"
            if i.kind in ("q", "bf") and lay == "M5":
                L += [f"    LAYER {lay} ;", rect(0, 2 * pk, i.w, i.h - 2 * pk)]
            elif i.kind == "cfg" and lay == "M4":
                L += [f"    LAYER {lay} ;", rect(2 * pk, 0, i.w - 2 * pk, i.h)]
            else:
                L += [f"    LAYER {lay} ;", rect(0, 0, i.w, i.h)]
        L += ["  END", f"END {key}", ""]
        lefs.append("\n".join(L))
    (work / "tech.lef").write_text(VD.bundled_tech_lef(k))
    (work / "blocks.lef").write_text("\n".join(lef_header() + lefs + ["END LIBRARY", ""]))
    # netlist
    V = ["module ds_die ();"]
    conn = defaultdict(list)
    for n in nets:
        w = nb(n.bits)
        nm = "n_" + re.sub(r"[^A-Za-z0-9_]", "_", n.id)
        V.append(f"  wire [{w - 1}:0] {nm};")
        conn[n.src[0]].append(f".{n.src[1]}({nm})")
        for d in n.dsts:
            conn[d[0]].append(f".{d[1]}({nm})")
    for i in insts:
        V.append(f"  {masters[i.name]} {i.name} (" + ", ".join(conn.get(i.name, [])) + ");")
    V.append("endmodule")
    (work / "die.v").write_text("\n".join(V) + "\n")
    # placement
    gstep = 0.054 * k
    P = []
    for i in insts:
        P.append(f"place_inst -name {i.name} -location {{{i.x:.3f} {i.y:.3f}}} -orientation R0 -status FIRM")
    (work / "place.tcl").write_text("\n".join(P) + "\n")
    tracks = []
    for name, d, p, wd, sp, off in VD.ASAP7_LAYERS:
        tracks.append(f"make_tracks {name} -x_offset {off * k:.3f} -x_pitch {p * k:.3f} -y_offset {off * k:.3f} -y_pitch {p * k:.3f}")
    adj = [f"set_global_routing_layer_adjustment {n} {m89_reserve if n in ('M8', 'M9') else low_adjust}"
           for n, *_ in VD.ASAP7_LAYERS[1:]]
    W, H = DIE_UM
    tcl = f"""# DSROM die-level bundled global route (k={k}, frame {frame}, return tree {ret}).
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef /work/tech.lef
read_lef /work/blocks.lef
read_verilog /work/die.v
link_design ds_die
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site bsite
{chr(10).join(tracks)}
source /work/place.tcl
mem placed
{chr(10).join(adj)}
set_routing_layers -signal M2-M9
global_route -verbose -allow_congestion -congestion_iterations 30 -congestion_report_file /work/grt_congestion.rpt
mem grt
report_wire_length -net * -global_route -file /work/wirelength.csv
set blk [ord::get_db_block]
set out [open /work/gcell_usage.txt w]
set grid [$blk getGCellGrid]
set gx [$grid getGridX]
set gy [$grid getGridY]
puts $out "GRIDX [join $gx ,]"
puts $out "GRIDY [join $gy ,]"
set tech [ord::get_db_tech]
foreach ln {{M2 M3 M4 M5 M6 M7 M8 M9}} {{
  set layer [$tech findLayer $ln]
  set nx [llength $gx]; set ny [llength $gy]
  for {{set j 0}} {{$j < $ny}} {{incr j 8}} {{
    set row {{}}
    for {{set i 0}} {{$i < $nx}} {{incr i 8}} {{
      set cap 0; set use 0
      for {{set jj $j}} {{$jj < min($j+8,$ny)}} {{incr jj}} {{
        for {{set ii $i}} {{$ii < min($i+8,$nx)}} {{incr ii}} {{
          set cap [expr {{$cap + [$grid getCapacity $layer $ii $jj]}}]
          set use [expr {{$use + [$grid getUsage $layer $ii $jj]}}]
        }}
      }}
      lappend row "$cap/$use"
    }}
    puts $out "L $ln $j [join $row {{ }}]"
  }}
}}
close $out
write_db /work/grt.odb
mem done
"""
    (work / "run.tcl").write_text(tcl)
    cls = Counter()
    wires = Counter()
    for n in nets:
        cls[n.cls] += nb(n.bits)
        wires[n.cls] += n.bits * len(n.dsts) if False else n.bits
    manifest = {"schema": "opentallas.dsrom.die_feasibility.grt_case.v1", "frame": frame, "return_tree": ret, "k": k,
                "snapped": snapped, "m8_m9_adjustment": m89_reserve, "m2_m7_adjustment": low_adjust,
                "instances": len(insts), "nets_buses": len(nets), "bundle_nets": sum(nb(n.bits) for n in nets),
                "wires": sum(n.bits for n in nets), "bundle_nets_by_class": dict(cls), "wires_by_class": dict(wires),
                "kinds": dict(Counter(i.kind for i in insts))}
    (work / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyse")
    a.add_argument("--out", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--job", choices=("grt", "legal", "pdn", "cts"), required=True)
    p.add_argument("--frame", choices=tuple(FRAMES), default="C")
    p.add_argument("--ret", choices=("local", "band"), default="local")
    p.add_argument("--k", type=int, default=16)
    p.add_argument("--m89", type=float, default=0.15)
    p.add_argument("--low", type=float, default=0.25)
    p.add_argument("--snapped", action="store_true")
    p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "analyse":
        print(json.dumps(analyse(Path(args.out))["variants"], indent=1)[:4000])
        return 0
    if args.job == "grt":
        print(json.dumps(write_grt_case(Path(args.out), args.frame, args.ret, args.k, args.m89, args.low, args.snapped), indent=1))
        return 0
    raise SystemExit(f"job {args.job}: see write_real_case")


if __name__ == "__main__":
    sys.exit(main())
