#!/usr/bin/env python3
"""Macro-packed floorplan of one DeepSeek-V4.1 ROM layer die (rung 3).

Places every ROM/SRAM macro of the integer macro map
(results/floorplan/v41_die_macromap.json, all 112 layer dies) plus the PHY
abstracts on the 31.8 x 25.63 mm layer die with real LEF geometry from
physical/asap7_memory_macros, and emits:

* results/floorplan/v41_pack_<variant>.json   placement + legality + report
* <outdir>/v41_pack_<variant>.def              DEF COMPONENTS / REGIONS (on request)
* <outdir>/v41_pack_<variant>_macros.tcl       place_inst commands (on request)
* results/floorplan/v41_pack_<variant>.svg     drawing

Structure (single-user latency first):

* HBM3E PHY abstracts, two per long edge, pins facing the core; an HBM service
  band above each (KV staging and request/beat queue SRAMs, K arbitration).
* Package links: UCIe-A modules on the east edge (two-die package peer), SerDes
  lanes on the west edge.  Neither has a LEF in the catalog; both are
  rectangular *assumed* abstracts from the analytical ledger.
* A central hub (VM, attention/BF16 engines, SU/vector, HC, collective, index)
  so the farthest ROM/MAC neighborhood is as close as possible to the
  activation source and reduction sink.
* ROM/MAC neighborhoods: column pairs ``[ROM R0 | MAC strip | ROM MY]`` so each
  ROM's output pins (east edge of the LEF) face their MAC strip; address pins
  face the narrow inter-pair gap.  Slots are filled by distance to the hub:
  ME (wo_a), dense QE, constant pool, Engram spill, then routed experts.
* Registered transport corridors: one horizontal spine corridor every
  ``SPINE_EVERY`` macro rows and one vertical corridor per HBM stack.

Legality rules enforced (and re-checked by tests/test_v41_floorplan_pack.py):
macro origins on the joint site/track grid (x multiple of 0.432 um: 0.054 site
and 0.048 M5 track; y multiple of 2.16 um: 0.27 row and 0.048 M4 track, since
every catalog SRAM/ROM M4 pin center is 0.012 mod 0.048 and M4 tracks are
0.012 mod 0.048), only R0/MY orientations for M4-edge-pin macros (MX would put
the pins 12 nm off track), no overlap including halos, everything inside the
die, soft regions disjoint from hard macros.

Logic areas are the analytical ledger's ASAP7 placed areas (routed/synthesised
units x width, results/floorplan/v41_resource_inventory.json rows); the die RTL
does not instantiate those widths (discrepancy D2), so the ROM/MAC strip and hub
are reservations sized from that engine profile, labelled as such.  The
N5-density ROM row of that ledger is NOT used; ROM is integer macros only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chip_assembly import floorplans as FP  # noqa: E402

CATALOG = ROOT / "physical/asap7_memory_macros/index.json"
MACRO_DIR = ROOT / "physical/asap7_memory_macros"
INVENTORY = ROOT / "results/floorplan/v41_resource_inventory.json"
CONNECTIVITY = ROOT / "results/contracts/v41_floorplan_connectivity.json"
MACROMAP = {"expanded_woa": ROOT / "results/floorplan/v41_die_macromap_expanded_woa.json",
            "compact_woa": ROOT / "results/floorplan/v41_die_macromap_compact_woa.json"}
HBM_PHY = "ot_hbm3e_phy_v41x_aw30"
WIDE, NARROW = "ot_rom_8192x274_m8", "ot_rom_8192x104_m8"

# ---- grid / technology (ASAP7 platform, see module docstring) -------------
X_STEP = 0.432          # lcm(0.054 site, 0.048 M5 track)
Y_STEP = 2.16           # lcm(0.270 row, 0.048 M4 track)
M4_OFF, M4_PITCH = 0.012, 0.048
M5_OFF, M5_PITCH = 0.012, 0.048
CLOCK_PS = 920.0        # adopted V4.1 target period
UNCERTAINTY_PS = 60.0
# Routing layers usable above macros (catalog OBS covers M1-M4) and in corridors.
TRACKS_PER_UM = {"M2": 1 / 0.036, "M3": 1 / 0.036, "M4": 1 / 0.048, "M5": 1 / 0.048,
                 "M6": 1 / 0.064, "M7": 1 / 0.064, "M8": 1 / 0.080, "M9": 1 / 0.080}
HORIZ = ("M2", "M4", "M6", "M8")
VERT = ("M3", "M5", "M7", "M9")
# ORFS asap7 pdn (grid_strategy-M1-M2-M5-M6.tcl): M5 0.12w/0.072s pair per 2.16,
# M6 0.288w/0.096s pair per 4.32.  M7-M9 die-level grid is an ASSUMPTION (no IR
# analysis yet): reserve 25% of M8/M9 and 0 of M7.
PDN_FRACTION = {"M5": (2 * 0.12 + 0.072) / 2.16, "M6": (2 * 0.288 + 0.096) / 4.32,
                "M7": 0.0, "M8": 0.25, "M9": 0.25, "M2": 0.0, "M3": 0.0, "M4": 0.0}
ROUTE_UTIL = 0.5        # usable fraction of free tracks for global signal routing

# ---- die and placement parameters ------------------------------------------
DIE_W = 73611 * X_STEP        # 31,799.952 um  (<= 31.8 mm)
DIE_H = 11865 * Y_STEP        # 25,628.400 um  (<= 815 mm2 / 31.8)
EDGE_KEEPOUT = 21.6           # seal ring / IO keepout
ROM_V_PITCH = 56 * Y_STEP     # 120.96 um, macro 119.34 tall: 1.62 um vertical halo
PAIR_GAP = 20 * X_STEP        # 8.64 um address-side gap between column pairs
PIN_HALO = 5 * X_STEP         # 2.16 um (>= ORFS MACRO_ROWS_HALO_X 2 um) std-cell keepout on each MAC-strip side
SPINE_EVERY = 16              # macro rows between horizontal spine corridors
# W10 re-fit (tools/v41_floorplan_refit.py): the MAC strip of a pair column sized from a PLACED element pair
# instead of the analytical reservation, with BF16-capable pair columns of their own width.
#   REFIT = dict(strip_q_um=..., strip_bf_um=..., bf_pairs=..., basis=...)
REFIT = None
SPINE_H = 15 * Y_STEP         # 32.4 um
VCORR_W = 100 * X_STEP        # 43.2 um vertical HBM corridor
SERVICE_H = 100 * Y_STEP      # 216 um HBM service band
HUB_HALO = 20 * Y_STEP        # 43.2 um ring between hub and ROM/MAC
HUB_SLACK = 1.02              # placement slack on hub partitions (snap losses)


def snap_up(v: float, step: float) -> float:
    return math.ceil(round(v / step, 6)) * step


def snap_dn(v: float, step: float) -> float:
    return math.floor(round(v / step, 6)) * step


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lef_signal_pins(name: str) -> list[tuple[str, float, float]]:
    """(layer, x_center, y_center) of every signal pin rectangle in a catalog LEF."""
    text = (MACRO_DIR / name / f"{name}.lef").read_text()
    out = []
    for pin, body in re.findall(r"\n  PIN (\S+)\n(.*?)\n  END \1", text, re.S):
        if "USE POWER" in body or "USE GROUND" in body:
            continue
        for layer, rects in re.findall(r"LAYER (\S+) ;\n((?:\s+RECT.*\n?)+)", body):
            for r in re.findall(r"RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)", rects):
                x0, y0, x1, y1 = map(float, r)
                out.append((layer, (x0 + x1) / 2, (y0 + y1) / 2))
    return out


def lef_size(name: str) -> tuple[float, float]:
    text = (MACRO_DIR / name / f"{name}.lef").read_text()
    m = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", text)
    return float(m.group(1)), float(m.group(2))


def pin_on_track(layer: str, xc: float, yc: float) -> bool:
    if layer in ("M4",):
        return round((yc - M4_OFF) * 1000) % round(M4_PITCH * 1000) == 0
    if layer in ("M5",):
        return round((xc - M5_OFF) * 1000) % round(M5_PITCH * 1000) == 0
    return True


def oriented_pin(xc, yc, w, h, orient):
    if orient == "R0":
        return xc, yc
    if orient == "MY":
        return w - xc, yc
    if orient == "MX":
        return xc, h - yc
    if orient == "R180":
        return w - xc, h - yc
    raise ValueError(orient)


# ---------------------------------------------------------------------------
def engine_profile(inv: dict) -> dict:
    """Soft-logic reservations (placed mm2) from the analytical ASAP7 rows."""
    rows = {r["block"]: r for r in inv["analytical_assembly_reference"]["rows"]}

    def a(key):
        return next(r for b, r in rows.items() if b.startswith(key))

    bd, bf, mux = a("block-dot pool"), a("BF16 pool"), a("pool operand muxes")
    share_bd = bd["placed_mm2"] / (bd["placed_mm2"] + bf["placed_mm2"])
    prof = {
        "ROM_MAC_strip": dict(mm2=bd["placed_mm2"] + share_bd * mux["placed_mm2"],
                              basis="block-dot pool + its share of pool operand muxes, distributed beside ROM",
                              evidence=[bd["evidence"], mux["evidence"]]),
        "ATTENTION": dict(mm2=bf["placed_mm2"] + (1 - share_bd) * mux["placed_mm2"],
                          basis="BF16 pool (wo_a, attention) + its share of muxes",
                          evidence=[bf["evidence"], mux["evidence"]]),
        "SU_VECTOR": dict(mm2=sum(a(k)["placed_mm2"] for k in (
            "vector unit, light", "vector unit, SFU", "Sinkhorn", "sqrt(softplus)", "activation quantiser",
            "FP4 quantise", "streaming select", "top-6")), basis="vector light+SFU lanes, Sinkhorn, softplus, "
                                                                  "select, quantisers", evidence=["estimate", "synthesis-only", "routed"]),
        "HC": dict(mm2=a("HC projection")["placed_mm2"], basis="HC projection FP32 lanes",
                   evidence=[a("HC projection")["evidence"]]),
        "COLLECTIVE": dict(mm2=sum(a(k)["placed_mm2"] for k in (
            "one-shot collective", "package controller", "fabric router", "package link endpoint",
            "collective queues")), basis="analytical counts 8 one-shot / 2 ctrl / 4 router (D1 open)",
                           evidence=["routed", "estimate"]),
        "GATHER": dict(mm2=sum(a(k)["placed_mm2"] for k in ("Engram gather",)),
                       basis="Engram gather slices + assembler (hub, beside VM)", evidence=["routed-closed"]),
        "HBM_SERVICE_logic": dict(mm2=sum(a(k)["placed_mm2"] for k in (
            "indexer key control", "KV / key streamer", "indexer head-sum", "indexer output tail")),
                                  basis="per-stack indexer key control/head-sum/tail + KV streamer, one set per "
                                        "stack (ledger count 4); K-arbiter partition not sized (W2)",
                                  evidence=["routed"]),
    }
    srams = {
        "KV_staging": (a("KV row staging")["count"], "ot_sram_1r1w_1024x256_m2_r2c2", "HBM_SERVICE"),
        "HBM_queues": (a("HBM request/beat")["count"], "ot_sram_1r1w_1024x256_m2_r2c2", "HBM_SERVICE"),
        "VM": (a("vector memory")["count"], "ot_sram_1rw_2048x128_m4_r2c2", "VM"),
        "chaining": (a("engine chaining")["count"], "ot_sram_1r1w_1024x256_m2_r2c2", "VM"),
        # RTL qwin: 17 banks x 1024 words x 256 bits (v41_resource_inventory rtl_behavioral_memories)
        "QE_window": (17, "ot_sram_1r1w_1024x256_m2_r2c2", "ATTENTION"),
    }
    phys = {"UCIe": a("UCIe-A"), "SerDes": a("112G PAM4"), "overhead": a("overhead")}
    return dict(soft=prof, srams=srams, phys=phys)


def required_slots(mm: dict) -> dict:
    """Max macros per (group, view) over every layer die: the template must hold all."""
    need: dict[str, dict[str, int]] = {}
    for d in mm["layer_dies"]:
        for g, views in d["macros_by_group"].items():
            for v, n in views.items():
                cur = need.setdefault(g, {})
                cur[v] = max(cur.get(v, 0), n)
    return need


class Plan:
    def __init__(self):
        self.hard: list[dict] = []    # name, master, x, y, w, h, orient, group, halo
        self.soft: list[dict] = []    # name, x, y, w, h, kind, area_req
        self.channels: list[dict] = []

    def add_hard(self, name, master, x, y, w, h, orient, group, halo=0.0):
        self.hard.append(dict(name=name, master=master, x=round(x, 3), y=round(y, 3), w=w, h=h,
                              orient=orient, group=group, halo=halo))


def build(variant: str) -> dict:
    cat = json.loads(CATALOG.read_text())["macros"]
    inv = json.loads(INVENTORY.read_text())
    mm = json.loads(MACROMAP[variant].read_text())
    prof = engine_profile(inv)
    need = required_slots(mm)
    wmac, hmac = lef_size(WIDE)
    wnar, hnar = lef_size(NARROW)
    P = Plan()

    # ---------------- edge I/O --------------------------------------------
    pw, ph = lef_size(HBM_PHY)
    phy_x = [snap_dn(DIE_W / 4 - pw / 2, X_STEP), snap_dn(3 * DIE_W / 4 - pw / 2, X_STEP)]
    for i, x in enumerate(phy_x):
        P.add_hard(f"hbm_s{i}", HBM_PHY, x, 0.0, pw, ph, "R0", "HBM_PHY")
        P.add_hard(f"hbm_n{i}", HBM_PHY, x, snap_dn(DIE_H - ph, Y_STEP), pw, ph, "MX", "HBM_PHY")
    ser, uc = prof["phys"]["SerDes"], prof["phys"]["UCIe"]
    ser_len = ser["beachfront_mm"] * 1000 / ser["count"]            # 400 um along the edge
    ser_d = ser["placed_mm2"] / ser["count"] * 1e6 / ser_len        # 1000 um deep
    ser_len, ser_d = snap_up(ser_len, Y_STEP), snap_up(ser_d, X_STEP)
    y0 = snap_dn((DIE_H - ser["count"] * ser_len) / 2, Y_STEP)
    for i in range(ser["count"]):
        P.add_hard(f"serdes_{i}", "ASSUMED_serdes_112g_lane", 0.0, y0 + i * ser_len, ser_d, ser_len, "R0", "SERDES")
    uc_len = uc["beachfront_mm"] * 1000 / uc["count"]               # 388.8 um
    uc_d = uc["placed_mm2"] / uc["count"] * 1e6 / uc_len             # 1043 um
    uc_len, uc_d = snap_up(uc_len, Y_STEP), snap_up(uc_d, X_STEP)
    y0 = snap_dn((DIE_H - uc["count"] * uc_len) / 2, Y_STEP)
    for i in range(uc["count"]):
        P.add_hard(f"ucie_{i}", "ASSUMED_ucie_a_x64", snap_dn(DIE_W - uc_d, X_STEP), y0 + i * uc_len,
                   uc_d, uc_len, "R0", "UCIE")

    # ---------------- HBM service bands ----------------------------------
    s_w = cat["ot_sram_1r1w_1024x256_m2_r2c2"]
    kv_n, kv_m, _ = prof["srams"]["KV_staging"]
    q_n, q_m, _ = prof["srams"]["HBM_queues"]
    per = [kv_n // 4 + (i < kv_n % 4) for i in range(4)]
    stacks = [("s", 0), ("s", 1), ("n", 0), ("n", 1)]
    svc_logic = prof["soft"]["HBM_SERVICE_logic"]["mm2"] / 4 * 1e6
    service_rects = []
    for si, (side, i) in enumerate(stacks):
        x = phy_x[i]
        if side == "s":
            yb = snap_up(ph + EDGE_KEEPOUT, Y_STEP)
        else:
            yb = snap_dn(DIE_H - ph - EDGE_KEEPOUT - SERVICE_H, Y_STEP)
        service_rects.append((x, yb, pw, SERVICE_H))
        cx = x + 2 * X_STEP * 10
        n_sram = per[si] + q_n // 4
        srw = snap_up(s_w["width_um"] + 2.0, X_STEP)
        sy = yb + (SERVICE_H - s_w["height_um"]) / 2
        sy = snap_dn(sy, Y_STEP)
        for k in range(n_sram):
            nm = f"hbm{side}{i}_kvstage_{k}" if k < per[si] else f"hbm{side}{i}_queue_{k - per[si]}"
            # Spread across the band so each pseudo-channel window has local staging.
            sx = snap_dn(x + (k + 0.5) * pw / n_sram - s_w["width_um"] / 2, X_STEP)
            P.add_hard(nm, "ot_sram_1r1w_1024x256_m2_r2c2", sx, sy, s_w["width_um"], s_w["height_um"],
                       "R0", "HBM_SERVICE", halo=1.728)
        P.soft.append(dict(name=f"HBM_SERVICE_{side}{i}", x=x, y=yb, w=pw, h=SERVICE_H, kind="HBM_SERVICE",
                           area_req_um2=svc_logic, note="band minus SRAMs holds K-arb/KV streamer/idx key ctrl"))

    # ---------------- core rectangle -------------------------------------
    core_x0 = snap_up(max(ser_d, 0) + EDGE_KEEPOUT, X_STEP)
    core_x1 = snap_dn(DIE_W - uc_d - EDGE_KEEPOUT, X_STEP)
    core_y0 = snap_up(ph + EDGE_KEEPOUT + SERVICE_H + EDGE_KEEPOUT, Y_STEP)
    core_y1 = snap_dn(DIE_H - ph - EDGE_KEEPOUT - SERVICE_H - EDGE_KEEPOUT, Y_STEP)

    # ---------------- hub ------------------------------------------------
    # Columns, west to east: ATTENTION | VM column (COLLECTIVE, VM, GATHER) | SU_VECTOR | HC.
    # The VM column (activation source and reduction sink) is centred on the core so the
    # farthest ROM/MAC neighborhood is as near as the die allows; the attention P buffer and
    # window stage sit on ATTENTION's east edge, abutting VM.
    hub_srams = [(k, v) for k, v in prof["srams"].items() if v[2] in ("VM", "ATTENTION")]
    sram_mm2 = {g: sum(n * cat[m]["area_um2"] for _, (n, m, gg) in hub_srams if gg == g) / 1e6
                for g in ("VM", "ATTENTION")}
    need_mm2 = {
        "ATTENTION": prof["soft"]["ATTENTION"]["mm2"] + 1.25 * sram_mm2["ATTENTION"],
        "VM": 2.0 * sram_mm2["VM"],
        "COLLECTIVE": prof["soft"]["COLLECTIVE"]["mm2"],
        "GATHER": prof["soft"]["GATHER"]["mm2"],
        "SU_VECTOR": prof["soft"]["SU_VECTOR"]["mm2"],
        "HC": prof["soft"]["HC"]["mm2"],
    }
    if REFIT and REFIT.get("hub_mm2"):
        need_mm2.update(REFIT["hub_mm2"])          # hub parts sized from the model / hardened units
    if REFIT:
        for k, f in REFIT.get("hub_scale", {}).items():    # power-switch area on gated partitions
            need_mm2[k] *= f
        for k, v in REFIT.get("hub_add_mm2", {}).items():  # always-on island in the VM column
            need_mm2[k] += v
    hub_area = sum(need_mm2.values()) * 1e6 * HUB_SLACK
    core_w, core_h = core_x1 - core_x0, core_y1 - core_y0
    # Equal ROM/MAC ring depth d on all sides: (W - 2d)(H - 2d) = hub_area.
    d = ((core_w + core_h) - math.sqrt((core_w - core_h) ** 2 + 4 * hub_area)) / 4
    hub_h = snap_up(core_h - 2 * d, Y_STEP)
    widths = {k: snap_up(v * 1e6 * HUB_SLACK / hub_h, X_STEP) for k, v in need_mm2.items()}
    # VM sits at mid-height, so COLLECTIVE (below) and GATHER (above) each get half of the
    # remaining column height: width = (2 * larger neighbour + VM) / hub height.
    # 1.3: routing allowance for loose VM SRAM macros; a measured VM block (REFIT vm_factor) carries its own network.
    vm_factor = (REFIT or {}).get("vm_factor", 1.3)
    vm_col_w = max(snap_up((2 * max(need_mm2["COLLECTIVE"], need_mm2["GATHER"]) * HUB_SLACK
                            + need_mm2["VM"] * vm_factor) * 1e6 / hub_h, X_STEP),
                   snap_up(2 * cat["ot_sram_1rw_2048x128_m4_r2c2"]["width_um"] + 24, X_STEP))
    hub_w = widths["ATTENTION"] + vm_col_w + widths["SU_VECTOR"] + widths["HC"]
    cx = core_x0 + core_w / 2
    hub_x = snap_dn(cx - vm_col_w / 2 - widths["ATTENTION"], X_STEP)
    hub_y = snap_dn(core_y0 + (core_h - hub_h) / 2, Y_STEP)
    hub = (hub_x, hub_y, hub_w, hub_h)
    parts = []
    x = hub_x
    parts.append(("ATTENTION", x, hub_y, widths["ATTENTION"], hub_h, need_mm2["ATTENTION"]))
    x += widths["ATTENTION"]
    # VM column: VM centred vertically (on the core centre), COLLECTIVE below, GATHER above.
    vm_h = snap_up(need_mm2["VM"] * 1e6 * vm_factor / vm_col_w, Y_STEP)
    vm_y = snap_dn(core_y0 + core_h / 2 - vm_h / 2, Y_STEP)
    parts.append(("COLLECTIVE", x, hub_y, vm_col_w, vm_y - hub_y, need_mm2["COLLECTIVE"]))
    parts.append(("VM", x, vm_y, vm_col_w, vm_h, need_mm2["VM"]))
    parts.append(("GATHER", x, vm_y + vm_h, vm_col_w, hub_y + hub_h - vm_y - vm_h, need_mm2["GATHER"]))
    x += vm_col_w
    parts.append(("SU_VECTOR", x, hub_y, widths["SU_VECTOR"], hub_h, need_mm2["SU_VECTOR"]))
    x += widths["SU_VECTOR"]
    parts.append(("HC", x, hub_y, widths["HC"], hub_h, need_mm2["HC"]))
    for k, x, y, w, h, a in parts:
        P.soft.append(dict(name=f"HUB_{k}", x=round(x, 3), y=round(y, 3), w=round(w, 3), h=round(h, 3),
                           kind=k, area_req_um2=a * 1e6))
    # Hub SRAMs on a grid inside their partition (ATTENTION: along its east edge, beside VM).
    for g in ("VM", "ATTENTION"):
        part = next(p for p in parts if p[0] == g)
        _, px, py, pwid, phgt, _ = part
        items = [(k, m) for k, (n, m, gg) in hub_srams if gg == g for _ in range(n)]
        cursor_x = px + pwid - 4.32 if g == "ATTENTION" else px + 4.32
        cursor_y = py + 4.32
        count = {}
        for k, m in items:
            mw, mh = cat[m]["width_um"], cat[m]["height_um"]
            if cursor_y + mh > py + phgt - 4.32:
                cursor_y = py + 4.32
                cursor_x = cursor_x - snap_up(mw + 4.32, X_STEP) if g == "ATTENTION" else cursor_x + snap_up(mw + 4.32, X_STEP)
            sx = snap_dn(cursor_x - mw, X_STEP) if g == "ATTENTION" else snap_up(cursor_x, X_STEP)
            sy = snap_up(cursor_y, Y_STEP)
            j = count.get(k, 0)
            count[k] = j + 1
            P.add_hard(f"{g.lower()}_{k.lower()}_{j}", m, sx, sy, mw, mh, "R0", f"HUB_{g}", halo=1.728)
            cursor_y = sy + mh + 4.32

    # ---------------- vertical HBM corridors -----------------------------
    vcorr = []
    for side, i in stacks:
        cx = snap_dn(phy_x[i] + pw / 2 - VCORR_W / 2, X_STEP)
        if side == "s":
            vcorr.append(dict(name=f"vcorr_s{i}", x=cx, y=core_y0, w=VCORR_W, h=hub_y - HUB_HALO - core_y0))
        else:
            y = hub_y + hub_h + HUB_HALO
            vcorr.append(dict(name=f"vcorr_n{i}", x=cx, y=y, w=VCORR_W, h=core_y1 - y))

    # ---------------- ROM/MAC column pairs ------------------------------
    total_need = sum(n for g in need.values() for v, n in g.items() if v == WIDE)
    nar_need = sum(n for g in need.values() for v, n in g.items() if v == NARROW)
    # MAC strip width from the logic reservation spread over all wide-macro pair rows.
    pair_rows = math.ceil(total_need / 2) + math.ceil(nar_need / 2)
    strip_area = prof["soft"]["ROM_MAC_strip"]["mm2"] * 1e6
    strip_w = snap_up(strip_area / (pair_rows * hmac) + 2 * PIN_HALO, X_STEP)
    if REFIT:
        strip_w = snap_up(REFIT["strip_q_um"] + 2 * PIN_HALO, X_STEP)
        strip_bf = snap_up(REFIT["strip_bf_um"] + 2 * PIN_HALO, X_STEP)
    else:
        strip_bf = strip_w
    pair_w = 2 * wmac + strip_w
    pair_pitch = snap_up(pair_w + PAIR_GAP, X_STEP)
    pair_w_bf = 2 * wmac + strip_bf
    pair_pitch_bf = snap_up(pair_w_bf + PAIR_GAP, X_STEP)
    hub_box = (hub_x - HUB_HALO, hub_y - HUB_HALO, hub_w + 2 * HUB_HALO, hub_h + 2 * HUB_HALO)
    blockers = [hub_box] + [(c["x"], c["y"], c["w"], c["h"]) for c in vcorr]

    def free(x, y, w, h):
        for bx, by, bw, bh in blockers:
            if x < bx + bw and bx < x + w and y < by + bh and by < y + h:
                return False
        return True

    slots = []   # (x_pair, y, strip width) per pair row
    spines = []
    span = core_x1 - core_x0 + PAIR_GAP
    ncols = int(span // pair_pitch)
    col_type = ["q"] * ncols
    if REFIT and REFIT.get("bf_pairs"):
        # BF16 columns nearest the hub's x centre; add them (each replaces enough q width) until their free
        # pair rows cover the BF16 pairs
        hub_cx = hub_x + hub_w / 2
        nbf = 0
        while True:
            nbf += 1
            nq = int((span - nbf * pair_pitch_bf) // pair_pitch)
            ncols = nq + nbf
            widths = None
            # centre-out order of column indices
            order_c = sorted(range(ncols), key=lambda c: abs(c - (ncols - 1) / 2))
            col_type = ["q"] * ncols
            for c in order_c[:nbf]:
                col_type[c] = "bf"
            xs, x = [], 0.0
            for t in col_type:
                xs.append(x)
                x += pair_pitch_bf if t == "bf" else pair_pitch
            x0 = snap_dn(core_x0 + (span - x) / 2, X_STEP)
            band_h0 = SPINE_EVERY * ROM_V_PITCH
            ys0, y0_, r0 = [], core_y0, 0
            while y0_ + ROM_V_PITCH <= core_y1 + 1e-6:
                ys0.append(y0_)
                r0 += 1
                y0_ += ROM_V_PITCH
                if r0 % SPINE_EVERY == 0:
                    y0_ += SPINE_H
            bf_rows = 0
            for c, t in enumerate(col_type):
                if t != "bf":
                    continue
                xp_ = snap_dn(x0 + xs[c], X_STEP)
                bf_rows += sum(1 for yy in ys0 if all(not (xp_ < bx + bw and bx < xp_ + pair_w_bf and yy < by + bh
                                                           and by < yy + hmac) for bx, by, bw, bh in blockers))
            if bf_rows >= REFIT["bf_pairs"] or nq <= 0:
                break
        col_x = [snap_dn(x0 + xx, X_STEP) for xx in xs]
    else:
        x_start = snap_dn(core_x0 + (span - ncols * pair_pitch) / 2, X_STEP)
        col_x = [x_start + c * pair_pitch for c in range(ncols)]
    # Horizontal rows: bands of SPINE_EVERY macro rows separated by a spine corridor.
    band_h = SPINE_EVERY * ROM_V_PITCH
    ys = []
    y = core_y0
    r = 0
    while y + ROM_V_PITCH <= core_y1 + 1e-6:
        ys.append(y)
        r += 1
        y += ROM_V_PITCH
        if r % SPINE_EVERY == 0:
            spines.append(y)
            y += SPINE_H
    for c in range(ncols):
        xp = col_x[c]
        sw = strip_bf if col_type[c] == "bf" else strip_w
        for y in ys:
            if free(xp, y, 2 * wmac + sw, hmac):
                slots.append((xp, y, sw))
    # Order slots by Manhattan distance of their MAC strip center to the VM center
    # (activation source / reduction sink).
    vm_part = next(p for p in parts if p[0] == "VM")
    hcx, hcy = vm_part[1] + vm_part[3] / 2, vm_part[2] + vm_part[4] / 2
    slots.sort(key=lambda s: (abs(s[0] + (2 * wmac + s[2]) / 2 - hcx) + abs(s[1] + hmac / 2 - hcy), s[0], s[1]))
    capacity_wide = 2 * len(slots)
    # Narrow (compact wo_a) macros use their own pair rows (2 per row, same strip).
    order = ["ROM_MAC.ME", "ROM_MAC.dense_QE", "VM.CONSTANT_HE", "ENGRAM.spill", "ROM_MAC.expert"]
    groups = sorted(need, key=lambda g: order.index(g) if g in order else 99)
    si = 0
    placed_by_group: dict[str, dict[str, int]] = {}
    overflow = {}
    for g in groups:
        for view in (NARROW, WIDE):
            n = need[g].get(view, 0)
            k = 0
            while k < n:
                if si >= len(slots):
                    overflow.setdefault(g, {})[view] = n - k
                    break
                xp, y, strip_w_s = slots[si]
                si += 1
                w_view = wnar if view == NARROW else wmac
                h_view = hnar if view == NARROW else hmac
                # left ROM: R0 (outputs on its east edge) against the strip
                P.add_hard(f"rom_{len(P.hard)}", view, xp + (wmac - w_view), y, w_view, h_view, "R0", g)
                k += 1
                if k < n:
                    P.add_hard(f"rom_{len(P.hard)}", view, xp + wmac + strip_w_s, y, w_view, h_view, "MY", g)
                    k += 1
                placed_by_group.setdefault(g, {})[view] = placed_by_group.get(g, {}).get(view, 0) + min(2, n - k + 2)
                P.soft.append(dict(name=f"MAC_{g}_{si}", x=round(xp + wmac + PIN_HALO, 3), y=round(y, 3),
                                   w=round(strip_w_s - 2 * PIN_HALO, 3), h=round(hmac, 3), kind="ROM_MAC_strip",
                                   area_req_um2=None, merge=True))
    used_rows = si
    # Merge per-row MAC strips into column runs for compactness of the record.
    P.soft = [s for s in P.soft if not s.get("merge")] + merge_strips([s for s in P.soft if s.get("merge")])
    for y in spines:
        P.channels.append(dict(name=f"spine_{len(P.channels)}", kind="horizontal_spine", x=core_x0, y=round(y, 3),
                               w=round(core_x1 - core_x0, 3), h=SPINE_H))
    for c in vcorr:
        P.channels.append(dict(kind="vertical_hbm_corridor", **{k: round(v, 3) if isinstance(v, float) else v
                                                                 for k, v in c.items()}))
    P.channels.append(dict(name="hub_ring", kind="hub_ring", x=hub_box[0], y=hub_box[1], w=hub_box[2], h=hub_box[3]))

    geometry = dict(die_w_um=round(DIE_W, 3), die_h_um=round(DIE_H, 3), die_mm2=round(DIE_W * DIE_H / 1e6, 4),
                    core=[core_x0, core_y0, round(core_x1, 3), round(core_y1, 3)],
                    hub=[round(v, 3) for v in hub], strip_w_um=strip_w, pair_pitch_um=pair_pitch,
                    strip_bf_w_um=strip_bf, pair_pitch_bf_um=pair_pitch_bf,
                    bf_columns=sum(t == "bf" for t in col_type), refit=REFIT,
                    rom_v_pitch_um=ROM_V_PITCH, pair_columns=ncols, rom_rows=len(ys),
                    spine_every_rows=SPINE_EVERY, spine_h_um=SPINE_H, vcorr_w_um=VCORR_W,
                    service_h_um=SERVICE_H, hub_halo_um=HUB_HALO, pair_gap_um=PAIR_GAP, pin_halo_um=PIN_HALO)
    bf_slots = sum(1 for s_ in slots if s_[2] == strip_bf and REFIT)
    bf_used = sum(1 for s_ in slots[:used_rows] if s_[2] == strip_bf and REFIT)
    capacity = dict(pair_row_slots=len(slots), bf_pair_row_slots=bf_slots, bf_pair_rows_used=bf_used,
                    bf_pairs_required=(REFIT or {}).get("bf_pairs", 0),
                    bf_closes=bool(not REFIT or bf_used >= REFIT.get("bf_pairs", 0)),
                    wide_slot_capacity=capacity_wide, used_pair_rows=used_rows,
                    spare_pair_rows=len(slots) - used_rows, required_by_group=need, overflow=overflow,
                    closes=not overflow)
    return dict(P=P, geometry=geometry, capacity=capacity, prof=prof, mm=mm, cat=cat,
                hub_parts=parts, slots=slots, pair_w=pair_w, service_rects=service_rects,
                core=(core_x0, core_y0, core_x1, core_y1))


def merge_strips(strips):
    by_col: dict[float, list] = {}
    for s in strips:
        by_col.setdefault((s["x"], s["name"].split("_")[1]), []).append(s)
    out = []
    for (x, g), ss in sorted(by_col.items()):
        ss.sort(key=lambda s: s["y"])
        run = dict(ss[0])
        for s in ss[1:]:
            if abs(s["y"] - (run["y"] + run["h"])) < 3.0:
                run["h"] = round(s["y"] + s["h"] - run["y"], 3)
            else:
                out.append(run)
                run = dict(s)
        out.append(run)
    for i, s in enumerate(out):
        s["name"] = f"MAC_strip_{i}"
        s.pop("merge", None)
        s["group"] = "ROM_MAC"
    return out


# ---------------------------------------------------------------------------
def legality(P: Plan, geometry: dict) -> dict:
    """Overlap (with halos), die containment, grid and pin-track checks."""
    errs = []
    W, H = geometry["die_w_um"], geometry["die_h_um"]
    pins = {}
    for m in P.hard:
        x, y, w, h = m["x"], m["y"], m["w"], m["h"]
        if x < -1e-6 or y < -1e-6 or x + w > W + 1e-6 or y + h > H + 1e-6:
            errs.append(f"outside_die:{m['name']}")
        if m["master"].startswith("ot_"):
            xi, yi = round(x * 1000), round(y * 1000)
            if m["group"] != "HBM_PHY" and (xi % round(X_STEP * 1000) or yi % round(Y_STEP * 1000)):
                errs.append(f"off_joint_grid:{m['name']}")
            if m["group"] == "HBM_PHY" and (xi % 54 or yi % 270):
                errs.append(f"off_site_grid:{m['name']}")
            if m["master"] not in pins:
                pins[m["master"]] = lef_signal_pins(m["master"])
    # Sweep for overlaps with halos (halo counts once per side of each macro).
    boxes = sorted(((m["x"] - m["halo"], m["y"] - m["halo"], m["x"] + m["w"] + m["halo"],
                     m["y"] + m["h"] + m["halo"], m["name"]) for m in P.hard))
    active = []
    overlaps = 0
    for b in boxes:
        active = [a for a in active if a[2] > b[0] + 1e-6]
        for a in active:
            if a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                overlaps += 1
                if overlaps <= 20:
                    errs.append(f"overlap:{a[4]}:{b[4]}")
        active.append(b)
    # Soft regions must not intersect hard macros (except HBM service / hub SRAM owners).
    soft_hits = 0
    grid: dict[tuple[int, int], list] = {}
    cell = 500.0
    for m in P.hard:
        for gx in range(int(m["x"] // cell), int((m["x"] + m["w"]) // cell) + 1):
            for gy in range(int(m["y"] // cell), int((m["y"] + m["h"]) // cell) + 1):
                grid.setdefault((gx, gy), []).append(m)
    for s in P.soft:
        if s["kind"] != "ROM_MAC_strip":
            continue
        seen = set()
        for gx in range(int(s["x"] // cell), int((s["x"] + s["w"]) // cell) + 1):
            for gy in range(int(s["y"] // cell), int((s["y"] + s["h"]) // cell) + 1):
                for m in grid.get((gx, gy), []):
                    if m["name"] in seen:
                        continue
                    seen.add(m["name"])
                    if m["x"] < s["x"] + s["w"] - 1e-6 and s["x"] < m["x"] + m["w"] - 1e-6 and \
                            m["y"] < s["y"] + s["h"] - 1e-6 and s["y"] < m["y"] + m["h"] - 1e-6:
                        soft_hits += 1
                        if soft_hits <= 5:
                            errs.append(f"strip_overlaps_macro:{s['name']}:{m['name']}")
    # Hub / service SRAMs must sit inside their owning soft region.
    owners = {s_["name"]: s_ for s_ in P.soft}
    for m in P.hard:
        own = None
        if m["group"].startswith("HUB_"):
            own = owners.get(m["group"])
        elif m["group"] == "HBM_SERVICE":
            own = owners.get("HBM_SERVICE_" + m["name"][3:5])
        if own and not (own["x"] - 1e-6 <= m["x"] and m["x"] + m["w"] <= own["x"] + own["w"] + 1e-6 and
                        own["y"] - 1e-6 <= m["y"] and m["y"] + m["h"] <= own["y"] + own["h"] + 1e-6):
            errs.append(f"outside_owner_region:{m['name']}:{own['name']}")
    # Pin-on-track check per placed macro (distinct (master, orient, x mod, y mod) classes).
    classes = {}
    for m in P.hard:
        if m["master"] not in pins:
            continue
        key = (m["master"], m["orient"], round(m["x"] * 1000) % 48, round(m["y"] * 1000) % 48)
        classes.setdefault(key, 0)
        classes[key] += 1
    track = []
    for (master, orient, xm, ym), n in sorted(classes.items()):
        w, h = lef_size(master)
        bad = 0
        tot = 0
        for layer, xc, yc in pins[master]:
            px, py = oriented_pin(xc, yc, w, h, orient)
            tot += 1
            if not pin_on_track(layer, px + xm / 1000, py + ym / 1000):
                bad += 1
        track.append(dict(master=master, orient=orient, x_mod48_nm=xm, y_mod48_nm=ym, instances=n,
                          signal_pins=tot, off_track_pins=bad))
    off_track = [t for t in track if t["off_track_pins"]]
    abstract_defects = []
    for t in off_track:
        msg = f"pins_off_track:{t['master']}:{t['orient']}:{t['off_track_pins']}/{t['signal_pins']}"
        # A pin phase that no origin can fix is a defect of the abstract, not of this placement.
        phases = {round(xc * 1000) % 48 for layer, xc, yc in pins[t["master"]] if layer == "M5"} | \
                 {round(yc * 1000) % 48 for layer, xc, yc in pins[t["master"]] if layer == "M4"}
        (abstract_defects if len(phases) > 1 else errs).append(msg + (f" (abstract has {len(phases)} pin phases)"
                                                                      if len(phases) > 1 else ""))
    return dict(errors=errs, abstract_defects=abstract_defects, overlaps=overlaps, strip_macro_overlaps=soft_hits,
                pin_track_classes=track, legal=not errs, pin_access_legal=not errs and not abstract_defects)


# ---------------------------------------------------------------------------
def report(B: dict) -> dict:
    P, g, prof = B["P"], B["geometry"], B["prof"]
    die = g["die_w_um"] * g["die_h_um"]
    hard_area = sum(m["w"] * m["h"] for m in P.hard)
    by_group: dict[str, float] = {}
    for m in P.hard:
        by_group[m["group"]] = by_group.get(m["group"], 0.0) + m["w"] * m["h"] / 1e6
    strip_area = sum(s["w"] * s["h"] for s in P.soft if s["kind"] == "ROM_MAC_strip")
    hub = g["hub"]
    hub_area = hub[2] * hub[3]
    svc_area = sum(r[2] * r[3] for r in B["service_rects"])
    svc_sram = sum(m["w"] * m["h"] for m in P.hard if m["group"] == "HBM_SERVICE")
    hub_sram = sum(m["w"] * m["h"] for m in P.hard if m["group"].startswith("HUB_"))
    chan_area = sum(c["w"] * c["h"] for c in P.channels if c["kind"] != "hub_ring") + \
        (hub[2] + 2 * HUB_HALO) * (hub[3] + 2 * HUB_HALO) - hub_area
    rom_hard = sum(m["w"] * m["h"] for m in P.hard if m["master"] in (WIDE, NARROW))
    # Pair-row footprint actually used, including gaps.
    used = B["capacity"]["used_pair_rows"]
    pair_foot = used * g["pair_pitch_um"] * g["rom_v_pitch_um"]
    free_pairs = B["capacity"]["spare_pair_rows"] * g["pair_pitch_um"] * g["rom_v_pitch_um"]
    io = sum(m["w"] * m["h"] for m in P.hard if m["group"] in ("HBM_PHY", "SERDES", "UCIE"))
    accounted = io + svc_area + hub_area + chan_area + pair_foot
    whitespace = die - accounted
    logic_req = sum(v["mm2"] for v in prof["soft"].values()) * 1e6
    soft_fit = []
    for s in P.soft:
        if s.get("area_req_um2"):
            # Hub requirements already include their SRAMs; service bands subtract theirs.
            avail = s["w"] * s["h"] - sum(m["w"] * m["h"] * 1.25 for m in P.hard
                                          if s["kind"] == "HBM_SERVICE" and m["group"] == "HBM_SERVICE"
                                          and s["x"] <= m["x"] < s["x"] + s["w"] and s["y"] <= m["y"] < s["y"] + s["h"])
            soft_fit.append(dict(region=s["name"], required_mm2=round(s["area_req_um2"] / 1e6, 4),
                                 available_mm2=round(avail / 1e6, 4), fits=avail >= s["area_req_um2"]))
    strip_req = prof["soft"]["ROM_MAC_strip"]["mm2"] * 1e6
    soft_fit.append(dict(region="ROM_MAC strips (all)", required_mm2=round(strip_req / 1e6, 4),
                         available_mm2=round(strip_area / 1e6, 4), fits=strip_area >= strip_req))
    return dict(
        die_mm2=round(die / 1e6, 3),
        hard_macro_mm2=round(hard_area / 1e6, 3),
        hard_macro_mm2_by_group={k: round(v, 3) for k, v in sorted(by_group.items())},
        rom_macro_mm2=round(rom_hard / 1e6, 3),
        rom_mac_pair_footprint_mm2=round(pair_foot / 1e6, 3),
        rom_mac_strip_mm2=round(strip_area / 1e6, 3),
        hub_mm2=round(hub_area / 1e6, 3), hub_sram_mm2=round(hub_sram / 1e6, 3),
        hbm_service_mm2=round(svc_area / 1e6, 3), hbm_service_sram_mm2=round(svc_sram / 1e6, 3),
        channels_mm2=round(chan_area / 1e6, 3), edge_io_mm2=round(io / 1e6, 3),
        unused_rom_pair_slots_mm2=round(free_pairs / 1e6, 3),
        whitespace_mm2=round(whitespace / 1e6, 3),
        whitespace_note=("die minus edge I/O, HBM service bands, hub, channels/rings and used ROM/MAC pair rows; "
                         "includes unused pair slots and edge slivers.  Compare against the ledger's 81.5 mm2 "
                         "overhead ASSUMPTION (PLL, clock spine, DFT, host), which is not otherwise reserved."),
        overhead_assumption_mm2=prof["phys"]["overhead"]["placed_mm2"],
        overhead_fits_in_whitespace=whitespace / 1e6 >= prof["phys"]["overhead"]["placed_mm2"],
        logic_reservation_mm2=round(logic_req / 1e6, 3),
        soft_region_fit=soft_fit)


def crossings(B: dict) -> dict:
    """Longest inter-region crossings -> ASAP7 wire delay -> registered stages."""
    P, g = B["P"], B["geometry"]
    wd = FP.wire_delay_model()
    budget = CLOCK_PS - UNCERTAINTY_PS - wd["overhead_ps"]
    seg_um = budget / wd["ps_per_um"]
    if REFIT and REFIT.get("reach_um"):
        seg_um = REFIT["reach_um"]              # measured register-to-register reach (e.g. W15 at SS, 0.833 ns)
    parts = {p[0]: p for p in B["hub_parts"]}

    def ctr(p):
        _, x, y, w, h, _ = p
        return x + w / 2, y + h / 2

    def near(p, qx, qy):
        _, x, y, w, h, _ = p
        return min(max(qx, x), x + w), min(max(qy, y), y + h)

    rows = []

    def add(name, a, b, bits, basis, ledger=None):
        L = abs(a[0] - b[0]) + abs(a[1] - b[1])
        stages = max(0, math.ceil(L / seg_um) - 1)
        rows.append(dict(crossing=name, from_um=[round(a[0], 1), round(a[1], 1)], to_um=[round(b[0], 1), round(b[1], 1)],
                         manhattan_um=round(L, 1), unregistered_delay_ps=round(wd["ps_per_um"] * L + wd["overhead_ps"], 1),
                         added_pipeline_registers=stages, added_cycles_one_way=stages + 1 if stages else 0,
                         data_bits=bits, bits_basis=basis, ledger_edge=ledger))

    roms = [m for m in P.hard if m["master"] in (WIDE, NARROW)]

    def far(group, src):
        ms = [m for m in roms if m["group"] == group]
        if not ms:
            return None
        return max(((m["x"] + (m["w"] if m["orient"] == "R0" else 0), m["y"] + m["h"] / 2) for m in ms),
                   key=lambda q: abs(q[0] - src[0]) + abs(q[1] - src[1]))

    vm_c = ctr(parts["VM"])
    if REFIT and REFIT.get("xroot") in parts:
        # distributed VM (W11): the ROM field's x-broadcast root / result-return sink sits at the middle of the
        # named hub region's edge nearest the core centre (lane-group-local VM banks live inside it)
        _, rx, ry, rw, rh, _ = parts[REFIT["xroot"]]
        c0x, c0y, c1x, c1y = B["core"]
        cxc = (c0x + c1x) / 2
        vm_c = (rx + rw if rx + rw / 2 < cxc else rx, ry + rh / 2)
    att = parts["ATTENTION"]
    for m in P.hard:
        if m["group"] == "HBM_PHY":
            px = m["x"] + m["w"] / 2
            py = m["y"] + (m["h"] if m["orient"] == "R0" else 0)
            add(f"HBM {m['name']} pins -> ATTENTION window stage", (px, py), near(att, px, py),
                256, "hbm_window data_bits per stack", "hbm_window")
    for grp, bits, basis, led in (
            ("ROM_MAC.expert", 512, "ASSUMED activation spine: 2 x 256-bit K-slice per column pair (not in ledger)", None),
            ("ROM_MAC.dense_QE", 512, "ASSUMED activation spine (dense QE)", None),
            ("ROM_MAC.ME", 128, "vm_me data_bits", "vm_me"),
            ("ENGRAM.spill", 264, "one 264-bit gather word per read", None),
            ("VM.CONSTANT_HE", 256, "vm_he data_bits (HE operand path)", "vm_he")):
        f = far(grp, vm_c)
        if f:
            add(f"VM (hub) -> farthest {grp} ROM/MAC strip", vm_c, f, bits, basis, led)
    coll = parts["COLLECTIVE"]
    if REFIT and REFIT.get("xroot") in parts:
        # the collective endpoint sits at the distributed VM's port (W15's measured die-centre placement)
        coll = ("COLLECTIVE", vm_c[0], vm_c[1], 0.0, 0.0, 0.0)
    ucie = [m for m in P.hard if m["group"] == "UCIE"]
    ser = [m for m in P.hard if m["group"] == "SERDES"]
    cc = ctr(coll)
    if ucie:
        u = max(ucie, key=lambda m: abs(m["y"] - cc[1]))
        add("COLLECTIVE -> farthest UCIe module (package peer)", near(coll, u["x"], u["y"] + u["h"] / 2),
            (u["x"], u["y"] + u["h"] / 2), 512, "vm_collective flit width", "vm_collective")
    if ser:
        s = max(ser, key=lambda m: abs(m["y"] - cc[1]) + abs(m["x"] - cc[0]))
        add("COLLECTIVE -> farthest SerDes lane (external)", near(coll, s["x"] + s["w"], s["y"]),
            (s["x"] + s["w"], s["y"] + s["h"] / 2), 512, "vm_collective flit width", "vm_collective")
    add("VM -> COLLECTIVE (hub-internal)", vm_c, near(coll, *vm_c), 2048, "collective_vm transpose width", "collective_vm")
    add("VM -> ATTENTION P buffer (east edge, hub-internal)", vm_c, near(att, *vm_c), 128, "vm_pv_preload", "vm_pv_preload")
    for m in P.hard:
        if m["group"] == "HBM_PHY":
            px = m["x"] + m["w"] / 2
            py = m["y"] + (m["h"] if m["orient"] == "R0" else 0)
            add(f"INDEX partial top-k {m['name']} service -> SU_VECTOR selector", (px, py),
                near(parts["SU_VECTOR"], px, py), 32, "selected_kv index/score width", "index_select")
    g_ = parts["GATHER"]
    fs = far("ENGRAM.spill", ctr(g_))
    if fs:
        add("GATHER -> farthest Engram spill macro", ctr(g_), fs, 264, "one 264-bit gather word per read", None)
    rows.sort(key=lambda r: -r["manhattan_um"])
    return dict(wire_model=wd, clock_ps=CLOCK_PS, uncertainty_ps=UNCERTAINTY_PS,
                reach_basis=(REFIT or {}).get("reach_basis", "TT wire model at the adopted period"),
                register_segment_um=round(seg_um, 1),
                rule="registers = ceil(L / segment) - 1; segment = (period - uncertainty - flop overhead) / ps_per_um; "
                     "one-way added cycles = registers + 1 when registers > 0 (a register-to-register hop is 1 cycle)",
                crossings=rows)


def channel_util(B: dict) -> dict:
    """Edge bit-width demand vs tracks available across each channel cut."""
    P, g = B["P"], B["geometry"]
    out = []

    def cap(width_um, layers, corridor=True):
        t = 0.0
        for L in layers:
            if not corridor and L in ("M2", "M3", "M4"):
                continue
            t += width_um * TRACKS_PER_UM[L] * (1 - PDN_FRACTION[L])
        return t * ROUTE_UTIL

    # Vertical HBM corridor: per stack hbm_window 256 + request/ctrl, both directions.
    # Crossing ROM rows on M5/M7/M9 over the macros is also available; count the corridor only.
    hbm_bits = 2 * (256 + 64)
    for c in P.channels:
        if c["kind"] == "vertical_hbm_corridor":
            t = cap(c["w"], VERT)
            out.append(dict(channel=c["name"], demand_wires=hbm_bits, tracks=round(t), utilization=round(hbm_bits / t, 3),
                            demand_basis="2 x (256-bit hbm_window + 64 request/ctrl), corridor std-cell layers M3/M5/M7/M9"))
    # Horizontal spine: per column pair, activation 512 + result 256 bits; a spine carries
    # the bus for its band's pairs on one shared registered bus (broadcast + ordered return).
    spine_bits = 512 + 256 + 64
    for c in P.channels:
        if c["kind"] == "horizontal_spine":
            t = cap(c["h"], HORIZ)
            out.append(dict(channel=c["name"], demand_wires=spine_bits, tracks=round(t),
                            utilization=round(spine_bits / t, 3),
                            demand_basis="ASSUMED shared registered spine: 512 activation + 256 result + 64 ctrl"))
            break  # identical for every spine
    # Hub abutments carrying the widest ledger edges (must be local, not corridors).
    for name, bits, edge_um in (("window_stage_merge (ATTENTION internal)", 16896, None),
                                ("merged_kv_attn (ATTENTION internal)", 16960, None)):
        need_um = bits / cap(1.0, HORIZ + VERT)
        out.append(dict(channel=name, demand_wires=bits, min_abutting_edge_um=round(need_um, 1),
                        demand_basis="ledger data_bits; must abut inside ATTENTION partition"))
    # Over-the-ROM capacity for a vertical cut through the whole ROM/MAC field (M5-M9 above OBS).
    field_w = g["core"][2] - g["core"][0]
    out.append(dict(channel="over-ROM horizontal capacity per 100 um of height (M6/M8)",
                    tracks=round(cap(100.0, ("M6", "M8"), corridor=False)),
                    demand_basis="available to any horizontal net crossing ROM columns; macros OBS M1-M4 only"))
    return dict(route_util=ROUTE_UTIL, pdn_fraction=PDN_FRACTION, channels=out,
                max_utilization=max((c.get("utilization", 0) for c in out), default=0),
                overflow=[c["channel"] for c in out if c.get("utilization", 0) > 1.0])


# ---------------------------------------------------------------------------
def write_def(B: dict, path: Path):
    P, g = B["P"], B["geometry"]
    dbu = 1000
    L = ["VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', "DESIGN ot_v41_rom_layer_die_fp ;",
         f"UNITS DISTANCE MICRONS {dbu} ;",
         f"DIEAREA ( 0 0 ) ( {round(g['die_w_um'] * dbu)} {round(g['die_h_um'] * dbu)} ) ;"]
    regions = [s for s in P.soft]
    L.append(f"REGIONS {len(regions)} ;")
    for s in regions:
        L.append(f"- {s['name']} ( {round(s['x'] * dbu)} {round(s['y'] * dbu)} ) "
                 f"( {round((s['x'] + s['w']) * dbu)} {round((s['y'] + s['h']) * dbu)} ) + TYPE FENCE ;")
    L.append("END REGIONS")
    orient = {"R0": "N", "MY": "FN", "MX": "FS", "R180": "S"}
    L.append(f"COMPONENTS {len(P.hard)} ;")
    for m in P.hard:
        L.append(f"- {m['name']} {m['master']} + FIXED ( {round(m['x'] * dbu)} {round(m['y'] * dbu)} ) {orient[m['orient']]} ;")
    L.append("END COMPONENTS")
    L.append(f"BLOCKAGES {len(P.channels)} ;")
    for c in P.channels:
        if c["kind"] == "hub_ring":
            continue
        L.append(f"- PLACEMENT + SOFT RECT ( {round(c['x'] * dbu)} {round(c['y'] * dbu)} ) "
                 f"( {round((c['x'] + c['w']) * dbu)} {round((c['y'] + c['h']) * dbu)} ) ;")
    L.append("END BLOCKAGES")
    L.append("END DESIGN")
    path.write_text("\n".join(L) + "\n")


def write_tcl(B: dict, path: Path):
    L = ["# MACRO_PLACEMENT_TCL for ORFS / OpenROAD: fixed macro origins on the joint site/track grid",
         "# generated by tools/v41_floorplan_pack.py"]
    for m in B["P"].hard:
        L.append(f"place_inst -name {m['name']} -location {{{m['x']:.3f} {m['y']:.3f}}} -orientation {m['orient']} -status FIRM")
    path.write_text("\n".join(L) + "\n")


def write_svg(B: dict, path: Path):
    P, g = B["P"], B["geometry"]
    s = 1 / 40.0   # 40 um per px
    W, H = g["die_w_um"] * s, g["die_h_um"] * s
    col = {"ROM_MAC.expert": "#8fb3d9", "ROM_MAC.dense_QE": "#3b6fb0", "ROM_MAC.ME": "#1f3f73",
           "ENGRAM.spill": "#b58ad6", "VM.CONSTANT_HE": "#6aa06a", "HBM_PHY": "#c46a3c", "SERDES": "#d9a24a",
           "UCIE": "#d9c04a", "HBM_SERVICE": "#e0a080", "HUB_VM": "#4a9a4a", "HUB_ATTENTION": "#b03b3b"}
    soft_col = {"ATTENTION": "#f2c4c4", "VM": "#cfe8cf", "SU_VECTOR": "#f5e0b5", "HC": "#e0d5f0",
                "COLLECTIVE": "#f0d0e8", "INDEX": "#d0e8f0", "HBM_SERVICE": "#f6dccd", "ROM_MAC_strip": "#e6ecf5"}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {H:.1f}" width="{W:.0f}" height="{H:.0f}" '
           f'font-family="sans-serif">', f'<rect width="{W:.1f}" height="{H:.1f}" fill="#ffffff" stroke="#000"/>']

    def rect(x, y, w, h, fill, extra=""):
        out.append(f'<rect x="{x * s:.2f}" y="{H - (y + h) * s:.2f}" width="{max(w * s, 0.3):.2f}" '
                   f'height="{max(h * s, 0.3):.2f}" fill="{fill}" {extra}/>')

    for c in P.channels:
        if c["kind"] != "hub_ring":
            rect(c["x"], c["y"], c["w"], c["h"], "#fff2a8")
    for so in P.soft:
        rect(so["x"], so["y"], so["w"], so["h"], soft_col.get(so["kind"], "#eee"), 'stroke="#999" stroke-width="0.3"')
    # Collapse ROM macros into runs per column for drawing.
    runs = {}
    for m in P.hard:
        if m["master"] in (WIDE, NARROW):
            runs.setdefault((m["x"], m["group"]), []).append(m)
        else:
            rect(m["x"], m["y"], m["w"], m["h"], col.get(m["group"], "#888"), 'stroke="#333" stroke-width="0.2"')
    for (x, grp), ms in runs.items():
        ms.sort(key=lambda m: m["y"])
        start = ms[0]
        prev = ms[0]
        for m in ms[1:] + [None]:
            if m is None or m["y"] - (prev["y"] + prev["h"]) > 3.0:
                rect(x, start["y"], start["w"], prev["y"] + prev["h"] - start["y"], col.get(grp, "#888"))
                start = m
            prev = m if m is not None else prev
    for so in P.soft:
        if so["kind"] in ("ATTENTION", "VM", "SU_VECTOR", "HC", "COLLECTIVE", "INDEX"):
            out.append(f'<text x="{(so["x"] + so["w"] / 2) * s:.1f}" y="{H - (so["y"] + so["h"] / 2) * s:.1f}" '
                       f'font-size="9" text-anchor="middle">{so["kind"]}</text>')
    lx = 8
    for k, c in list(col.items())[:6]:
        out.append(f'<rect x="{lx}" y="4" width="8" height="8" fill="{c}"/><text x="{lx + 10}" y="11" font-size="7">{k}</text>')
        lx += 95
    out.append("</svg>")
    path.write_text("\n".join(out) + "\n")


def run(variant: str, outdir: Path | None = None, write_views: bool = False) -> dict:
    B = build(variant)
    P = B["P"]
    leg = legality(P, B["geometry"])
    rep = report(B)
    cr = crossings(B)
    ch = channel_util(B)
    mm = B["mm"]
    rec = dict(
        schema="opentallas.v41.floorplan_pack.v1",
        variant=variant,
        status="macro_packed_floorplan_proposal_not_routed",
        claim_boundary=("Legal macro origins, halos, grid and capacity for the integer macro map with analytical ASAP7 "
                        "logic reservations; no placement of standard cells, no route, no timing, no IR/EM."),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                       [CATALOG, INVENTORY, CONNECTIVITY, MACROMAP[variant], Path(__file__).resolve(),
                        ROOT / "tools/chip_assembly/floorplans.py"] +
                       sorted({MACRO_DIR / m["master"] / f"{m['master']}.lef" for m in P.hard
                               if m["master"].startswith("ot_")})},
        macromap_summary=mm["summary"],
        engine_profile={k: dict(mm2=round(v["mm2"], 4), basis=v["basis"]) for k, v in B["prof"]["soft"].items()},
        engine_profile_status="analytical m=2 width-scaled ASAP7 ledger (not RTL-instantiated; D2 open)",
        assumed_abstracts={"ASSUMED_serdes_112g_lane": "0.4 mm2/lane, 400 um beachfront (ledger ASSUMED)",
                           "ASSUMED_ucie_a_x64": "388.8 x 1043 um per x64 module (ledger, published module)"},
        geometry=B["geometry"],
        capacity=B["capacity"],
        legality=leg,
        area=rep,
        channels=ch,
        latency_crossings=cr,
        bank_binding_rule=("The k-th macro of a group in a die's bank map (results/floorplan/v41_die_bankmap_busiest_*.json "
                           "entries, in order) binds to the k-th instance of that group in `instances`; instances "
                           "of a group are listed nearest-to-VM first."),
        instances=[[m["name"], m["master"], m["x"], m["y"], m["orient"], m["group"]] for m in P.hard],
        soft_regions=[[s["name"], s["kind"], s["x"], s["y"], s["w"], s["h"]] for s in P.soft],
        channel_rects=[[c["name"], c["kind"], c["x"], c["y"], c["w"], c["h"]] for c in P.channels],
    )
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        write_svg(B, outdir / f"v41_pack_{variant}.svg")
        if write_views:
            write_def(B, outdir / f"v41_pack_{variant}.def")
            write_tcl(B, outdir / f"v41_pack_{variant}_macros.tcl")
            rec["views_sha256"] = {n: sha(outdir / n) for n in
                                   (f"v41_pack_{variant}.def", f"v41_pack_{variant}_macros.tcl")}
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=sorted(MACROMAP), default="expanded_woa")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--svg-dir", type=Path, default=ROOT / "results/floorplan")
    ap.add_argument("--views-dir", type=Path, help="also write DEF and MACRO_PLACEMENT_TCL here")
    a = ap.parse_args()
    rec = run(a.variant, a.svg_dir, write_views=False)
    if a.views_dir:
        B = build(a.variant)
        a.views_dir.mkdir(parents=True, exist_ok=True)
        write_def(B, a.views_dir / f"v41_pack_{a.variant}.def")
        write_tcl(B, a.views_dir / f"v41_pack_{a.variant}_macros.tcl")
        rec["views_sha256"] = {n: sha(a.views_dir / n) for n in
                               (f"v41_pack_{a.variant}.def", f"v41_pack_{a.variant}_macros.tcl")}
    a.output.write_text(json.dumps(rec, separators=(",", ":")) + "\n")
    s = dict(capacity={k: v for k, v in rec["capacity"].items() if k != "required_by_group"},
             legal=rec["legality"]["legal"], errors=rec["legality"]["errors"][:10], area=rec["area"],
             max_channel_util=rec["channels"]["max_utilization"],
             crossings=[(c["crossing"], c["manhattan_um"], c["added_cycles_one_way"]) for c in rec["latency_crossings"]["crossings"]])
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
