#!/usr/bin/env python3
"""Analytical whole-die assembly of the DeepSeek-V4.1-Flash ROM array's layer die and head die.

    python3 tools/v41_die_assembly.py [--out results/arch/v41_die_assembly.json]
                                      [--svg results/arch/figures/v41_die_floorplan.svg]

No whole-die physical design of the V4.1 ROM array exists.  This tool assembles one ANALYTICALLY from committed
evidence and says, for each input, what class of evidence it is.  It does four things.

1. AREA LEDGER.  Every adopted block of the design point (results/arch/v41_latency_ladder.json top rung with the
   adopted levers, as tools/arch_lanes_v41.design_point builds it; MTP lane multiplier m = 2) is priced at its ASAP7
   standard-cell area (results/physical_abi3/asap7/**/physical.json; the unit areas of tools/arch_budget_v41.py),
   turned into placed area by a placement utilisation, and tagged routed-closed / routed-not-closed /
   synthesis-only / estimate.  NODE TRANSFER: the repository's rule (docs/ROM_DENSITY_NODE_TRANSFER.md s11,
   docs/CHIP_ARCHITECTURE_DESIGN.md s0) is that an ASAP7 area is never labelled or scaled as an N5 figure -- only
   ratios transfer.  The ledger therefore carries ASAP7 areas UNSCALED (conservative: ASAP7 is a 7 nm-class
   predictive PDK and N5 is denser), and reports a clearly labelled N5-credit SENSITIVITY (nodes.N5.
   logic_density_vs_n7, published 1.8x, applied as if ASAP7 were N7) that is a bound, not an N5 claim.  The ROM
   array is sized for the die's weight capacity at official precision (results/arch/v41_die_placement.json) at the
   model's N5 ROM density (technology.json rom.*, the ROMA-derived quotient; docs/ROM_PHYSICAL_METHODOLOGY.md) with
   the memory compiler's SECDED word (266 / 256); the ASAP7 ROM compiler density and the Taalas HC1 whole-die weight
   density are cross-checks.  SRAM is priced on this repository's ASAP7 SRAM compiler macros; HBM3E PHY on the
   ot_hbm3e_phy abstract (technology.json, assumed); UCIe-A on the published UCIe 1.0 module (388.8 x 1,043 um,
   Hot Chips 2023 UCIe tutorial electrical summary); 112G SerDes lanes at an ASSUMED area per lane (no primary
   source committed).
2. FLOORPLAN.  PHYs on the edges by beachfront (HBM on the long edges, UCIe on the edge facing the package peer,
   SerDes on the package's outer edge), a central control/vector spine, and ROM banks tiled together with the
   lane groups that consume them (weight-stationary: weights never cross the die).  Wire-critical paths are
   priced with the ASAP7-derived buffered-wire model (tools/chip_assembly/floorplans.wire_delay_model: routed
   express-link records, 0.60 ps/um + 190 ps flop overhead) and technology.json latency.global_wire_delay_s_per_mm
   (150 ps/mm, assumed, 100-250) at the design point's 1.087 GHz, and the per-token exposure is counted on the
   design point's own critical path (tools/arch_utilization_v41.solve).  The budget DAG charges no on-die wire.
3. POWER, IR AND CLOCK.  The die power map for power scenarios A and B (results/arch/power_scenarios.json, design
   point, 1M) is spread over the floorplan's regions; the IR drop of the die-level grid is the closed-form drop of
   a uniformly loaded sheet fed by a bump array, on this repository's die grid (tools/chip_assembly/tcl/
   pdn_die.tcl, M8/M9 1.0 um stripes at 40 um) and the ASAP7 layer resistances (ORFS asap7 setRC.tcl); the hot
   spot is compared with the published die-average flux of a shipping air-cooled reticle (power_scenarios cooling
   references).  The clock plan prices a global H-tree on the same wire models, with skew scaled by the routed
   matrix engine's measured skew / insertion ratio.
4. VERDICT.  Area, long-wire timing, power density, IR, clock; the top risks; the missing hierarchical routes.

Everything here is a model on committed inputs.  Nothing is a routed die.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

SCHEMA = "opentallas.v41-die-assembly.v1"
OUT = ROOT / "results/arch/v41_die_assembly.json"
SVG = ROOT / "results/arch/figures/v41_die_floorplan.svg"
TECH = ROOT / "configs/hardware/technology.json"
PLACEMENT = ROOT / "results/arch/v41_die_placement.json"
LADDER = ROOT / "results/arch/v41_latency_ladder.json"
LANES = ROOT / "results/arch/v41_lanes.json"
POWER = ROOT / "results/arch/power_scenarios.json"
BUDGET = ROOT / "results/arch/arch_budget_v41.json"
RACK = ROOT / "results/arch/v41_rack.json"
LEVERS = ROOT / "results/arch/v41_collective_levers.json"
MACROS = ROOT / "physical/asap7_memory_macros/index.json"
HBM_PHY = ROOT / "physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json"
PHYS = ROOT / "results/physical_abi3/asap7"
MATVEC_BLOCK = ROOT / "results/physical_abi3/asap7/chip/blocks/ot_hdc_matvec.json"
PDN_DIE = ROOT / "tools/chip_assembly/tcl/pdn_die.tcl"
CTX = "1048576"
INPUTS = [TECH, PLACEMENT, LADDER, LANES, POWER, BUDGET, RACK, LEVERS, MACROS, HBM_PHY, MATVEC_BLOCK, PDN_DIE]


def J(p):
    return json.loads(Path(p).read_text())


def val(x):
    return x["value"] if isinstance(x, dict) else x


def src(path, sel=""):
    return f"{Path(path).relative_to(ROOT)}" + (f"#{sel}" if sel else "")


# ---------------------------------------------------------------------------------------------------------------------
# constants that are not in a committed record (each carries a grade and a source)
# ---------------------------------------------------------------------------------------------------------------------
CONST = dict(
    die_long_mm=dict(value=31.8, grade="derived",
                     source="configs/hardware/technology.json links.rom_package_ucie.bytes_s note: two ~815 mm2 "
                            "(25.6 x 31.8 mm) dies share the 25.6 mm short edge; the short edge is re-derived as "
                            "reticle.area_mm2 / 31.8"),
    ucie_module_w_um=dict(value=388.8, grade="published",
                          source="UCIe Consortium, Hot Chips 2023 tutorial 'Electrical, Form Factor and Compliance', "
                                 "Electrical Summary: advanced-package PHY dimension width 388.8 um, depth 1,043 um "
                                 "(depth for a 45 um bump pitch), data width 64, 16-32 GT/s, "
                                 "https://www.hc2023.hotchips.org/assets/program/tutorials/ucie/"
                                 "Electrical%20Form%20Factor%20and%20Compliance.pdf"),
    ucie_module_d_um=dict(value=1043.0, grade="published", source="same table"),
    ucie_lane_gtps=dict(value=32.0, grade="published", source="same table: UCIe-A 24/32 GT/s column (1,317 GB/s/mm "
                                                               "shoreline both directions, 658 per direction)"),
    serdes_lane_mm2=dict(value=0.40, range_low=0.25, range_high=0.60, grade="assumed",
                         source="no primary area source for a 112G PAM4 LR lane with DSP is committed in this "
                                "repository (technology.json energy.link_j_per_bit.board_serdes_112g carries power "
                                "only); engineering band pending a sourced PHY datasheet"),
    serdes_strip_depth_mm=dict(value=1.0, grade="assumed", source="PHY strip depth; shoreline = area / depth"),
    bump_pitch_um=dict(value=45.0, range_low=25.0, range_high=55.0, grade="published",
                       source="UCIe advanced package bump pitch 25-55 um; the UCIe-A PHY depth above is quoted at "
                              "45 um (same Hot Chips 2023 table); CoWoS-class micro-bump array over the whole die"),
    power_bump_fraction=dict(value=0.25, grade="assumed",
                             source="one bump in four is VDD (one VSS, two signal/spare): a common area-array "
                                    "allocation; the VDD-bump pitch is bump_pitch / sqrt(fraction)"),
    bump_contact_radius_um=dict(value=10.0, grade="assumed",
                                source="radius of the via stack under a micro-bump pad (~half the ~20 um pad)"),
    vdd_v=dict(value=0.7, grade="measured-ours",
               source="ASAP7 TT library voltage_map (VDD, 0.7) -- the corner every routed record here is timed at"),
    ir_budget_fraction=dict(value=0.05, grade="assumed",
                            source="static IR budget of the die-level grid, 5% of VDD (a common sign-off budget; "
                                   "the local M1-M6 grid needs its own share)"),
    placement_utilisation=dict(value=0.70, range_low=0.37, range_high=0.80, grade="assumed",
                               source="standard-cell area / placed area for large hardened blocks; the low end is "
                                      "the median utilisation of this repository's routed V4.1 blocks (small blocks "
                                      "routed at low density, see ledger.utilisation_evidence)"),
    clock_repeater_cap_factor=dict(value=2.0, grade="assumed",
                                   source="repeater + wire capacitance of a buffered clock spine = 2 x wire cap"),
)


# ---------------------------------------------------------------------------------------------------------------------
# 1. area ledger
# ---------------------------------------------------------------------------------------------------------------------
def phys(rel):
    p = PHYS / rel / "physical.json"
    if not p.exists():
        return None
    d = J(p)["design"]
    return dict(path=str(p.relative_to(ROOT)), area_um2=d.get("area_um2"), fmax_mhz=round(d["fmax_hz"] / 1e6, 1)
                if d.get("fmax_hz") else None, closed=d.get("closed"), routed="place_and_route" in J(p),
                utilisation=d.get("utilization_fraction"))


def evidence_class(rec):
    if rec is None:
        return "estimate"
    if not rec["routed"]:
        return "synthesis-only"
    return "routed-closed" if rec["closed"] else "routed-not-closed"


def design_point():
    """The adopted design point (ladder top with the adopted levers, R-L9 lane split) and its pooled engine areas."""
    import arch_budget_v41 as A
    import arch_lanes_v41 as LN
    import arch_utilization_v41 as U
    dp = LN.design_point()
    areas, asrc = A.unit_areas()
    m1 = U.area_of(dp["sp"], areas, pooled=True, lm=1)
    m2 = U.area_of(dp["sp"], areas, pooled=True, lm=2)
    return dp, areas, asrc, m1, m2


def rom_density(tech, node="N5"):
    """Bits per mm2 of ROM macro at `node`: 1e6 / (6T SRAM bitcell x ROM/SRAM cell ratio / array efficiency)."""
    cell = val(tech["nodes"][node]["sram_hd_bitcell_um2"])
    ratio = val(tech["rom"]["cell_to_sram_cell_area_ratio_by_node"][node])
    eff = val(tech["rom"]["array_efficiency"])
    return 1e6 / (cell * ratio / eff), dict(sram_bitcell_um2=cell, rom_to_sram_cell_ratio=ratio, array_efficiency=eff)


def macro(name):
    m = J(MACROS)["macros"][name]
    return dict(name=name, area_um2=m["area_um2"], capacity_bits=m["capacity_bits"],
                density_mbit_per_mm2=m["density_mb_per_mm2"], fmax_mhz_ss=m["fmax_mhz"]["ss"],
                width_um=m["width_um"], height_um=m["height_um"], leakage_nw_tt=m.get("leakage_nw_tt"))


def ledger(kind, dp, areas, asrc, m1, m2, util=None):
    """Area ledger of one die kind ('layer' or 'head').  Returns rows and totals."""
    tech = J(TECH)
    util = util or CONST["placement_utilisation"]["value"]
    pl = J(PLACEMENT)
    rows = []

    def add(name, group, cell_mm2, cls, basis, placed=None, record=None, count=1, **kw):
        placed = cell_mm2 / util if placed is None else placed
        rows.append(dict(block=name, group=group, count=count, cell_area_mm2=cell_mm2, placed_mm2=placed,
                         evidence=cls, basis=basis, record=record, **kw))

    # -- engines of the design point, MTP core (m = 2) ------------------------------------------------------------
    bd, bf = asrc["blockdot_um2"], asrc["mac_bf16_um2"]
    sp = dp["sp"]
    add("block-dot pool (FP8/FP4 weights + FP4 indexer)", "engine", m2["weight"], "routed-closed (unit) x width",
        f"{int(sp.weight_macs):,} MACs/cycle x m=2 at {areas['fp8_mac_um2']:.1f} um2/MAC (ot_hdc_blockdot / 32, "
        f"closed {bd['fmax_mhz']} MHz); replication of a routed unit, the pool itself is not routed",
        record=bd["path"], lanes=int(sp.weight_macs) * 2)
    add("BF16 pool (BF16 weights, wo_a, attention)", "engine", m2["bf16"], "routed-closed (unit) x width",
        f"{int(sp.bf16_macs):,} MACs/cycle x m=2 at {areas['mac_bf16_um2']:.0f} um2/MAC "
        f"(mac_bf16_fp32_pipe_round_stage, closed {bf['fmax_mhz']} MHz)", record=bf["path"], lanes=int(sp.bf16_macs) * 2)
    add("pool operand muxes", "engine", m2["pool_muxes"], "estimate",
        "10% of the pooled engines (tools/arch_utilization_v41.area_of, ASSUMED, no routed block)")
    add("HC projection (FP32 lanes)", "engine", m2["hc"], "routed-not-closed (units)",
        f"{int(sp.hc_macs):,} FP32 lanes per weight lane x m=2 at fp32 add (closed) + fp32 mul (not closed); "
        "results/rtl/hdc_v41x_hcp_campaign.json bit-exact at 2,048 lanes, block only boundary-characterised",
        record=asrc["fp32_mul_um2"]["path"])
    add("vector unit, light lanes", "vector", m2["su"], "estimate",
        f"{int(sp.su_lanes):,} lanes x m=2 at {areas['su_light_lane_um2']:.0f} um2 (ESTIMATE 1.5 x (2 fp32 mul + "
        "3 fp32 add); no routed light lane)")
    add("vector unit, SFU lanes", "vector", m2["sfu"], "synthesis-only",
        f"{int(sp.sfu_lanes):,} lanes x m=2 at {areas['su_lane_um2']:.0f} um2 (ot_hdc_v41_su_lane, synthesis only)",
        record=asrc["su_lane_um2"]["path"])
    add("streaming select (4 x 16 tselect)", "control", m2["sel"], "routed-not-closed",
        "64 lanes of ot_hdc_tselect_w16 (routed 1,087 MHz, not closed)", record=asrc["tselect16_um2"]["path"])
    # -- the side units the budget prices in time but not in area --------------------------------------------------
    side = [("Sinkhorn units (one per verified position)", "hdc/v41/ot_hdc_sinkhorn", 6, "vector"),
            ("sqrt(softplus)", "hdc/v41/ot_hdc_softplus", 2, "vector"),
            ("top-6 select", "hdc/v41/ot_hdc_select_k6", 2, "control"),
            ("activation quantiser", "hdc/v41/ot_hdc_actquant", 4, "vector"),
            ("FP4 quantise/dequantise", "hdc/v41/ot_hdc_fp4qdq", 4, "vector"),
            ("indexer head-sum", "hdc/v41x/ot_hdc_v41x_idx_hsum", 4, "engine"),
            ("indexer key control", "hdc/v41x/ot_hdc_v41x_idx_kctl", 4, "kv"),
            ("indexer output tail", "hdc/v41x/ot_hdc_v41x_idx_tail", 4, "engine"),
            ("KV / key streamer (one per stack)", "hdc/kv/ot_hdc_kv_stream", 4, "kv"),
            ("one-shot collective engine (128 lanes)", "rom/ot_rom_oneshot_die_d32", 8, "collective"),
            ("package controller", "rom/ot_rom_pkg_ctrl", 2, "control"),
            ("fabric router", "rom/ot_rom_fabric_router", 4, "control"),
            ("package link endpoint", "rom_pkg_link", 4, "collective"),
            ("Engram gather slices (spilled table rows)", "hdc/v41x/ot_hdc_v41x_egather_slice", 24, "control"),
            ("Engram gather assembler", "hdc/v41x/ot_hdc_v41x_egather_asm", 1, "control")]
    for name, rel, n, grp in side:
        r = phys(rel)
        add(name, grp, n * r["area_um2"] / 1e6, evidence_class(r),
            f"{n} x {Path(rel).name} ({r['area_um2']:,.0f} um2, {r['fmax_mhz']} MHz, closed={r['closed']})",
            record=r["path"], count=n)
    # -- SRAM -------------------------------------------------------------------------------------------------------
    s2p = macro("ot_sram_1r1w_1024x256_m2_r2c2")
    s1p = macro("ot_sram_1rw_2048x128_m4_r2c2")
    spec_kv_row_buffer_B = 338e3     # docs/ARCH_SPEC_V41.md s6 item 4: 640 rows, 338 KB per die per layer
    kv_B = 2 * spec_kv_row_buffer_B * 2    # double-buffered (prefetch one layer ahead), x2 for the design point's 2x pools
    hbm_q_B = 4 * 32 * 64 * 32            # 4 stacks x 32 pseudo-channels x 64 beats x 32 B (spec s6 item 11 queues)
    vec_B = 4 * 5120 * 4 * 2 * 6          # residual (4 x 5,120 FP32), two copies, six positions (MTP verify)
    act_B = 2 * 64 * 1024                 # ME/QE output / chaining buffers, 128 KB
    for name, B, mc, basis in [
            ("KV row staging buffer", kv_B, s2p, "spec s6 item 4 338 KB x 2 (prefetch) x 2 (design-point pools)"),
            ("HBM request/beat queues", hbm_q_B, s2p, "spec s6 item 11: >= 64 beats x 32 pseudo-channels x 4 stacks"),
            ("vector memory (residual, MTP positions)", vec_B, s1p, "4 x 5,120 FP32 x 2 copies x 6 positions"),
            ("engine chaining buffers", act_B, s2p, "vector-credit chaining (spec s6 item 10), 128 KB")]:
        n = math.ceil(B * 8 / mc["capacity_bits"])
        add(name, "sram", n * mc["area_um2"] / 1e6, "analytical-macro (ASAP7 compiler)",
            f"{B / 1e3:,.0f} KB = {n} x {mc['name']} ({mc['density_mbit_per_mm2']:.1f} Mbit/mm2); {basis}",
            placed=n * mc["area_um2"] / 1e6 * 1.15, record=src(MACROS, f"macros.{mc['name']}"), count=n, bytes=B)
    q = J(LEVERS)["queue_area_per_die"]
    add("collective queues (adopted levers)", "sram", q["with_levers_mm2"], "estimate", q["kind"],
        placed=q["with_levers_mm2"], record=src(LEVERS, "queue_area_per_die.with_levers_mm2"))
    if kind == "head":
        hf = J(RACK)["head_draft_floorplan"]
        add("DSpark draft-window SRAM (112 macros)", "sram", hf["area"]["macros_mm2"],
            "analytical-macro (ASAP7 compiler)", "rack C10 floorplan: 112 x ot_sram_1r1w_1024x256_m2_r2c2, 1.50 x "
            "1.06 mm", placed=hf["area"]["block_mm2"], record=src(RACK, "head_draft_floorplan.area.block_mm2"))
    # -- ROM ----------------------------------------------------------------------------------------------------------
    cap_B = pl["rom_bytes_per_die"]
    dens, dbasis = rom_density(tech)
    ecc = 266 / 256
    rom_mm2 = cap_B * 8 * ecc / dens
    held = (max(d["weight_bytes"] + d.get("engram_spill_bytes", 0) for d in pl["die_table"] if d["role"] == "layer")
            if kind == "layer" else
            max(d["weight_bytes"] + d.get("engram_spill_bytes", 0) for d in pl["die_table"] if d["role"] != "layer"
                and d["role"] != "engram"))
    add("mask-ROM array (weights at official precision)", "rom", rom_mm2, "derived (model density)",
        f"{cap_B / 1e9:.3f} GB per die (checkpoint / 188) x SECDED 266/256 at {dens / 1e6:.1f} Mbit/mm2 (N5: 6T cell "
        f"{dbasis['sram_bitcell_um2']} um2 x ROM/SRAM {dbasis['rom_to_sram_cell_ratio']} / array efficiency "
        f"{dbasis['array_efficiency']}); holds {held / 1e9:.3f} GB", placed=rom_mm2, record=src(PLACEMENT, "rom_bytes_per_die"),
        bytes=cap_B, held_bytes=held)
    # -- PHYs ----------------------------------------------------------------------------------------------------------
    hp = J(HBM_PHY)["footprint"]
    add("HBM3E PHY + controller", "phy_hbm", 4 * hp["area_mm2"], "assumed (abstract)",
        f"4 x ot_hbm3e_phy {hp['width_um'] / 1e3:.1f} x {hp['height_um'] / 1e3:.3f} mm (technology.json hbm.hbm3e "
        "phy_area_mm2_per_stack 10, assumed 8-15; beachfront 12 mm per stack)", placed=4 * hp["area_mm2"],
        record=src(HBM_PHY, "footprint.area_mm2"), count=4, beachfront_mm=4 * hp["width_um"] / 1e3)
    link_Bps = val(tech["links"]["rom_package_ucie"]["bytes_s"])
    mod_Bps = 64 * CONST["ucie_lane_gtps"]["value"] * 1e9 / 8
    n_mod = math.ceil(link_Bps / mod_Bps)
    mw, md = CONST["ucie_module_w_um"]["value"] / 1e3, CONST["ucie_module_d_um"]["value"] / 1e3
    add("UCIe-A modules (package peer)", "phy_ucie", n_mod * mw * md, "published (module) x derived count",
        f"{n_mod} x64 modules at {CONST['ucie_lane_gtps']['value']:.0f} GT/s ({mod_Bps / 1e9:.0f} GB/s per direction "
        f"each) for technology.json links.rom_package_ucie.bytes_s {link_Bps / 1e12:.1f} TB/s; {mw * 1e3:.1f} x "
        f"{md * 1e3:.0f} um each", placed=n_mod * mw * md, count=n_mod, beachfront_mm=n_mod * mw)
    lanes = J(RACK)["physical_constants"]["lanes_per_package"]["value"] // 2
    sl = CONST["serdes_lane_mm2"]["value"]
    add("112G PAM4 SerDes lanes", "phy_serdes", lanes * sl, "assumed",
        f"{lanes} lanes per die (90 per two-die package, R-L9) x {sl} mm2 (ASSUMED, band "
        f"{CONST['serdes_lane_mm2']['range_low']}-{CONST['serdes_lane_mm2']['range_high']})", placed=lanes * sl,
        count=lanes, beachfront_mm=lanes * sl / CONST["serdes_strip_depth_mm"]["value"])
    # -- fixed overhead ----------------------------------------------------------------------------------------------
    die = val(tech["reticle"]["area_mm2"])
    ovh = val(tech["floorplan"]["overhead_area_fraction"])
    add("overhead: PLLs, clock spine, PDN, DFT/scan, host, test", "overhead", ovh * die, "assumed",
        f"technology.json floorplan.overhead_area_fraction {ovh} x {die} mm2 (sweep 0.06-0.15)", placed=ovh * die)
    tot = sum(r["placed_mm2"] for r in rows)
    by_group = {}
    for r in rows:
        by_group[r["group"]] = by_group.get(r["group"], 0.0) + r["placed_mm2"]
    by_ev = {}
    for r in rows:
        k = r["evidence"].split(" ")[0]
        by_ev[k] = by_ev.get(k, 0.0) + r["placed_mm2"]
    logic_cell = sum(r["cell_area_mm2"] for r in rows if r["group"] in ("engine", "vector", "control", "kv", "collective"))
    return dict(die=kind, die_mm2=die, placement_utilisation=util, rows=rows, placed_total_mm2=tot,
                whitespace_mm2=die - tot, fits=tot <= die, by_group_mm2=by_group, by_evidence_mm2=by_ev,
                logic_cell_mm2=logic_cell, rom_mm2=rom_mm2, rom_density_mbit_per_mm2=dens / 1e6,
                rom_density_basis=dbasis, ecc_factor=ecc)


def ledger_sensitivities(dp, areas, asrc, m1, m2, tech):
    """Closure of the layer die against the inputs that move it."""
    out = {}
    for u in (CONST["placement_utilisation"]["range_low"], 0.6, CONST["placement_utilisation"]["value"],
              CONST["placement_utilisation"]["range_high"]):
        L = ledger("layer", dp, areas, asrc, m1, m2, util=u)
        out[f"utilisation_{u}"] = dict(placed_mm2=L["placed_total_mm2"], whitespace_mm2=L["whitespace_mm2"],
                                       fits=L["fits"])
    base = ledger("layer", dp, areas, asrc, m1, m2)
    logic_placed = sum(r["placed_mm2"] for r in base["rows"] if r["group"] in ("engine", "vector", "control", "kv",
                                                                                "collective"))
    free = base["die_mm2"] - (base["placed_total_mm2"] - logic_placed)
    out["break_even_utilisation"] = base["logic_cell_mm2"] / free if free > 0 else None
    # m = 1 core (no MTP lane multiplier): the engines at half width
    m1rows = sum(m1[k] for k in ("weight", "bf16", "pool_muxes", "hc", "su", "sfu", "sel"))
    m2rows = sum(m2[k] for k in ("weight", "bf16", "pool_muxes", "hc", "su", "sfu", "sel"))
    u = base["placement_utilisation"]
    out["m1_core"] = dict(placed_mm2=base["placed_total_mm2"] - (m2rows - m1rows) / u,
                          whitespace_mm2=base["whitespace_mm2"] + (m2rows - m1rows) / u)
    # N5 logic-density credit (a bound, not an N5 figure)
    k = val(tech["nodes"]["N5"]["logic_density_vs_n7"])
    out["n5_logic_credit"] = dict(factor=k, placed_mm2=base["placed_total_mm2"] - logic_placed * (1 - 1 / k),
                                  whitespace_mm2=base["whitespace_mm2"] + logic_placed * (1 - 1 / k),
                                  note="SENSITIVITY ONLY: nodes.N5.logic_density_vs_n7 applied as if ASAP7 were N7; "
                                       "the repository forbids labelling this an N5 area")
    # ROM density: the ASAP7 compiler macro (data bits) and the HC1 whole-die reference
    mc = macro("ot_rom_16384x266_m16")
    asap7_rom = base["rows"][[r["block"] for r in base["rows"]].index("mask-ROM array (weights at official precision)")]
    rom_asap7_mm2 = asap7_rom["bytes"] * 8 * (266 / 256) / (mc["density_mbit_per_mm2"] * 1e6)
    out["rom_asap7_compiler"] = dict(macro=mc["name"], density_mbit_per_mm2=mc["density_mbit_per_mm2"],
                                     rom_mm2=rom_asap7_mm2, whitespace_mm2=base["whitespace_mm2"] + base["rom_mm2"] - rom_asap7_mm2,
                                     note="analytical macro on the measured DRC-clean ASAP7 bitcell; predictive PDK")
    hc = tech["reference_parts"]["taalas_hc1"]
    hc_B = 8.03e9 * val(hc["weight_bits_per_parameter"]) / 8
    out["hc1_whole_die_weight_density"] = dict(
        hc1_mb_per_mm2=hc_B / 1e6 / val(hc["die_area_mm2"]),
        this_die_mb_per_mm2=J(PLACEMENT)["rom_bytes_per_die"] / 1e6 / base["die_mm2"],
        basis="Llama-3.1-8B (8.03 B parameters) at technology.json reference_parts.taalas_hc1."
              "weight_bits_per_parameter (3.5, assumed 3-6) over its published 815 mm2 die: the only shipping "
              "whole-die weight density; this die stores fewer weight bytes per mm2 of die than HC1")
    lo, hi = CONST["serdes_lane_mm2"]["range_low"], CONST["serdes_lane_mm2"]["range_high"]
    lanes = 45
    out["serdes_area_band"] = dict(whitespace_mm2_low_area=base["whitespace_mm2"] + lanes * (CONST["serdes_lane_mm2"]["value"] - lo),
                                   whitespace_mm2_high_area=base["whitespace_mm2"] - lanes * (hi - CONST["serdes_lane_mm2"]["value"]))
    out["hbm_phy_band"] = dict(whitespace_mm2_at_8=base["whitespace_mm2"] + 4 * 2.0,
                               whitespace_mm2_at_15=base["whitespace_mm2"] - 4 * 5.0)
    return out


def utilisation_evidence():
    us = []
    for rel in ("hdc/v41/ot_hdc_blockdot", "hdc/v41/ot_hdc_softplus", "hdc/v41/ot_hdc_select_k512",
                "hdc/v41/ot_hdc_actquant", "hdc/v41/ot_hdc_fp4qdq", "hdc/v41x/ot_hdc_v41x_idx_hsum",
                "hdc/v41x/ot_hdc_v41x_idx_kctl", "hdc/v41x/ot_hdc_v41x_wgt_qtile", "hdc/v41x/ot_hdc_v41x_egather_asm",
                "rom/ot_rom_fabric_router", "rom/ot_rom_pkg_ctrl", "mac_bf16_fp32_pipe_round_stage"):
        r = phys(rel)
        if r and r["utilisation"]:
            us.append((rel, r["utilisation"]))
    mv = J(MATVEC_BLOCK)["metrics"]
    return dict(blocks={k: v for k, v in us}, median=statistics.median(v for _, v in us),
                matvec_tile_block=mv["stdcell_area_um2"] / mv["core_area_um2"],
                note="ORFS utilisation of routed V4.1 blocks: small blocks are routed on generous floorplans, so the "
                     "median is a pessimistic bound for a die-level placement; the budgeted matvec block (the only "
                     "one hardened on a die-sized floorplan) is the other data point")


# ---------------------------------------------------------------------------------------------------------------------
# 2. floorplan and long wires
# ---------------------------------------------------------------------------------------------------------------------
def floorplan(L):
    """Rectangles (mm, origin lower-left) for one die from its ledger."""
    W = CONST["die_long_mm"]["value"]
    H = L["die_mm2"] / W
    g = {r["block"]: r for r in L["rows"]}
    grp = L["by_group_mm2"]
    rects = []

    def R(name, cls, x, y, w, h, **kw):
        rects.append(dict(name=name, cls=cls, x=round(x, 4), y=round(y, 4), w=round(w, 4), h=round(h, 4), **kw))

    hbm = g["HBM3E PHY + controller"]
    hw, hh = hbm["beachfront_mm"] / 4, hbm["placed_mm2"] / hbm["beachfront_mm"]
    for i, xc in enumerate((0.27 * W, 0.73 * W)):
        R(f"HBM3E PHY {2 * i}", "phy_hbm", xc - hw / 2, 0.0, hw, hh)
        R(f"HBM3E PHY {2 * i + 1}", "phy_hbm", xc - hw / 2, H - hh, hw, hh)
    u = g["UCIe-A modules (package peer)"]
    ud = CONST["ucie_module_d_um"]["value"] / 1e3
    R("UCIe-A (package peer)", "phy_ucie", W - ud, H / 2 - u["beachfront_mm"] / 2, ud, u["beachfront_mm"])
    s = g["112G PAM4 SerDes lanes"]
    sd = CONST["serdes_strip_depth_mm"]["value"]
    R("112G SerDes (TP 26 + stage 14 + switch 2 + spare 3 per die)", "phy_serdes", 0.0, H / 2 - s["beachfront_mm"] / 2, sd,
      s["beachfront_mm"])
    # the core: between the PHY strips
    x0, x1 = sd, W - ud
    y0, y1 = hh, H - hh
    core_w, core_h = x1 - x0, y1 - y0
    # central spine: vector unit, control, select, HC, collectives' tree root
    spine_groups = ("vector", "control")
    spine_mm2 = sum(grp.get(k, 0.0) for k in spine_groups) + g["HC projection (FP32 lanes)"]["placed_mm2"] \
        + sum(r["placed_mm2"] for r in L["rows"] if r["block"] in ("vector memory (residual, MTP positions)",
                                                                   "engine chaining buffers"))
    spine_w = spine_mm2 / core_h
    xs = x0 + core_w / 2 - spine_w / 2
    R("vector unit + HC projection + sequencer/select spine", "vector", xs, y0, spine_w, core_h, mm2=spine_mm2)
    # collective engines at the two link edges and KV streamers at the HBM PHYs
    col = grp.get("collective", 0.0)
    R("one-shot collective (UCIe level)", "collective", x1 - 0.9, H / 2 + u["beachfront_mm"] / 2 + 0.2, 0.9,
      col / 2 / 0.9)
    R("one-shot collective (package-pair level)", "collective", x0, H / 2 + s["beachfront_mm"] / 2 + 0.2, 0.9,
      col / 2 / 0.9)
    kv = grp.get("kv", 0.0) + sum(r["placed_mm2"] for r in L["rows"] if r["block"] in (
        "HBM request/beat queues", "KV row staging buffer"))
    for i, xc in enumerate((0.27 * W, 0.73 * W)):
        for j, yy in enumerate((y0, y1 - kv / 4 / hw)):
            R(f"KV/key streamer + staging {2 * i + j}", "kv", xc - hw / 2, yy, hw, kv / 4 / hw)
    # tiles: ROM banks + the lane groups that read them, left and right of the spine
    eng_mm2 = grp.get("engine", 0.0)
    rom_mm2 = grp.get("rom", 0.0)
    nx, ny = 4, 6
    tiles = 2 * nx * ny
    kv_h = kv / 4 / hw
    tile_region_h = core_h
    left_w = xs - x0
    right_w = x1 - (xs + spine_w)
    tw_l, tw_r = left_w / nx, right_w / nx
    th = tile_region_h / ny
    tile_mm2 = (eng_mm2 + rom_mm2) / tiles
    tile_list = []
    for side, (xa, tw) in enumerate(((x0, tw_l), (xs + spine_w, tw_r))):
        for ix in range(nx):
            for iy in range(ny):
                tx, ty = xa + ix * tw, y0 + iy * th
                f_rom = rom_mm2 / (eng_mm2 + rom_mm2)
                # ROM banks on both sides of the tile's lane column: the weight operand path is at most half a tile
                R(f"tile {side}.{ix}.{iy} ROM a", "rom", tx, ty, tw * f_rom / 2, th, tile=True)
                R(f"tile {side}.{ix}.{iy} lanes", "engine", tx + tw * f_rom / 2, ty, tw * (1 - f_rom), th, tile=True)
                R(f"tile {side}.{ix}.{iy} ROM b", "rom", tx + tw * (1 - f_rom / 2), ty, tw * f_rom / 2, th, tile=True)
                tile_list.append(dict(x=tx + tw / 2, y=ty + th / 2))
    avail_core = core_w * core_h
    need_core = spine_mm2 + eng_mm2 + rom_mm2 + col + kv
    return dict(die_w_mm=W, die_h_mm=H, core=dict(x0=x0, x1=x1, y0=y0, y1=y1, area_mm2=avail_core),
                spine=dict(x=xs, w=spine_w, mm2=spine_mm2), tiles=dict(n=tiles, nx=2 * nx, ny=ny, w_mm=tw_l, h_mm=th,
                                                                       mm2_each=tile_mm2),
                content_mm2=need_core, overfill_mm2=max(0.0, need_core - avail_core),
                note=("tiles are drawn to the core's geometry; when the ledger's content exceeds the core the tiles "
                      "are compressed and overfill_mm2 > 0 (the floorplan does not close)"),
                rects=rects, tile_centres=tile_list,
                edges=dict(hbm_beachfront_mm=hbm["beachfront_mm"], ucie_shoreline_mm=u["beachfront_mm"],
                           serdes_shoreline_mm=s["beachfront_mm"], perimeter_mm=2 * (W + H),
                           edge_utilisation=(hbm["beachfront_mm"] + u["beachfront_mm"] + s["beachfront_mm"]) / (2 * (W + H)),
                           hbm_edge_fraction=hbm["beachfront_mm"] / (2 * (W + H)),
                           hbm_max_beachfront_utilisation=0.6))


def wire_models(clock_hz):
    from chip_assembly import floorplans as F
    fit = F.wire_delay_model()
    tech = J(TECH)
    gw = tech["latency"]["global_wire_delay_s_per_mm"]
    T = 1e12 / clock_hz
    ov = fit["overhead_ps"]
    out = {}
    for name, ps_mm, grade, s in (
            ("asap7_routed_fit", fit["ps_per_um"] * 1e3, "measured-ours", "tools/chip_assembly/floorplans.py "
             "wire_delay_model(): least-squares fit of the routed ot_rom_express_link records"),
            ("tech_global_wire", val(gw) * 1e12, "assumed", "technology.json latency.global_wire_delay_s_per_mm"),
            ("tech_global_wire_high", gw["range_high"] * 1e12, "assumed", "same entry, range_high")):
        reach = (T - ov) / ps_mm
        out[name] = dict(ps_per_mm=ps_mm, flop_overhead_ps=ov, period_ps=T, reach_mm_per_cycle=reach, grade=grade,
                         source=s)
    out["fit_points"] = fit["points"]
    return out


def cycles(d_mm, m):
    return math.ceil(d_mm / m["reach_mm_per_cycle"]) if d_mm > 0 else 0


# The on-die traversals the design-point DAG charges (tools/arch_lanes_v41.wire_mutation), each registered at its
# per-cycle reach.  key -> (distance key, node rule, what, overlap / exposure justification).
TRAVERSALS = {
    "pool_operand_in": dict(dist="far_tile", nodes="matvec + kvscan (pool lanes), wire_in",
                            what="spine (vector unit, chaining buffers) -> the farthest tile: the operand vector of "
                                 "a matvec or of an attention / indexer scan (the pooled lanes live in the tiles)",
                            exposure="latency on the operator's input edge: charged on every such node; the DAG "
                                     "hides it only where the node is off the critical path"),
    "pool_result_out": dict(dist="far_tile", nodes="matvec + kvscan (pool lanes), wire_out",
                            what="the farthest tile -> spine: partial sums / scores back into the reducer tree",
                            exposure="latency on the output edge; charged, exposed where on path"),
    "spine_reduce": dict(dist="spine_half", nodes="reduce (in + out), select (in), hc.fn (in + out)",
                         what="spine lanes -> the reducer / select / HC root at the spine's centre, and the result "
                              "back along the spine (half the spine's length each way)",
                         exposure="charged; the vector unit is one strip the core's height long"),
    "collective_edge": dict(dist="collective_edge", nodes="collective, wire_in + wire_out",
                            what="spine -> the one-shot engine at the UCIe / package-pair edge and back (the two "
                                 "levels run in parallel: the longer is charged)",
                            exposure="charged: the bench-measured tails (behavioural links) contain no on-die wire"),
    "stage_hop_edge": dict(dist="serdes_edge", nodes="hop, wire_in (sender spine -> SerDes) + wire_out (SerDes -> "
                                                     "receiver spine)",
                           what="the residual from the sender's spine to its SerDes edge and from the receiver's "
                                "SerDes edge to its spine",
                           exposure="charged: the RTL hop tails start and end at the link endpoints"),
    "kv_gather_request": dict(dist="hbm_request", nodes="op .gather, wire_in",
                              what="the top-k indices from the select (spine) to the nearest HBM3E controller",
                              exposure=("charged: a data-dependent address exists only after the select; the rows' "
                                        "return PHY -> tile is shorter than the scan's operand broadcast charged "
                                        "on the scan (far_tile >= hbm_to_tile), so it is covered there")),
    "rom_to_lane_in_tile": dict(dist="in_tile", nodes="none",
                                what="the farthest ROM macro -> its tile's lane column (weights never leave the tile)",
                                exposure="HIDDEN: a static-address stream issued ahead of the activation"),
    "kv_static_rows": dict(dist="hbm_to_tile", nodes="none",
                           what="HBM3E PHY -> tiles for window rows, reuse-layer selections and index keys",
                           exposure=("HIDDEN: static addresses, prefetched one layer ahead into the staging buffers "
                                     "(docs/ARCH_SPEC_V41.md s6 item 4; arch_budget_v41 kv_state prefetch)")),
}


_GEOM = {}


def traversal_geometry(sp):
    """Traversal distances (mm) and cycles per wire model of the layer die built for pooled widths `sp` (the
    floorplan depends on the widths only, not on any rate, so the design point can price its own wires)."""
    import arch_budget_v41 as A
    import arch_utilization_v41 as U
    key = (sp.weight_macs, sp.bf16_macs, sp.su_lanes, sp.sfu_lanes, sp.hc_macs, sp.sel_lanes)
    if key in _GEOM:
        return _GEOM[key]
    areas, asrc = A.unit_areas()
    m1 = U.area_of(sp, areas, pooled=True, lm=1)
    m2 = U.area_of(sp, areas, pooled=True, lm=2)
    L = ledger("layer", dict(sp=sp), areas, asrc, m1, m2)
    F = floorplan(L)
    W, H = F["die_w_mm"], F["die_h_mm"]
    xc, yc = F["spine"]["x"] + F["spine"]["w"] / 2, H / 2
    core = F["core"]
    tw, th = F["tiles"]["w_mm"], F["tiles"]["h_mm"]
    phy_x = min(abs(0.27 * W - xc), abs(0.73 * W - xc))
    dist = dict(
        far_tile=max(abs(t["x"] - xc) + abs(t["y"] - yc) for t in F["tile_centres"]),
        spine_half=(core["y1"] - core["y0"]) / 2,
        collective_edge=max(core["x1"] - xc, xc - core["x0"]),
        serdes_edge=xc - core["x0"],
        hbm_request=phy_x + (yc - core["y0"]),
        hbm_to_tile=(H / 2) + tw,
        in_tile=tw / 2 + th / 2)
    wm = wire_models(A._env()["clock"])
    out = dict(distances_mm=dist, models={})
    for name, m in wm.items():
        if name == "fit_points":
            continue
        out["models"][name] = dict(ps_per_mm=m["ps_per_mm"], flop_overhead_ps=m["flop_overhead_ps"],
                                   grade=m["grade"], source=m["source"])
    assert dist["far_tile"] >= dist["hbm_to_tile"], "the gather's row return must be covered by the scan broadcast"
    _GEOM[key] = out
    return out


def traversal_cycles(geo, model, clock_hz):
    """{distance key: registered cycles} at clock_hz: the wire model's per-cycle reach = (period - flop overhead) /
    ps per mm (the same rule as wire_models)."""
    m = geo["models"][model]
    reach = (1e12 / clock_hz - m["flop_overhead_ps"]) / m["ps_per_mm"]
    return {k: (math.ceil(d / reach) if d > 0 else 0) for k, d in geo["distances_mm"].items()}


def path_counts(dp):
    """On-path node kinds of the design point's critical path at 1M, batch 1 (the DAG the rates come from)."""
    import arch_latency_ladder_v41 as LX
    import arch_utilization_v41 as U
    hz = dp["hz"]
    with LX.clock(hz[0]), U.params(**hz[1]):
        r = U.solve(dp["sp"], int(CTX), levers=U.CHAIN_L3, muts=list(dp["muts"]) + [dp["ml"]])
    b = r["_built"]
    g = b.g
    kinds = {}
    for n in g.path(b.sink):
        k = g.nodes[n]["kind"]
        kinds[k] = kinds.get(k, 0) + 1
    return kinds, r["period_s"]


def long_wires(F, dp, clock_hz):
    """The registered on-die traversals as the design point now charges them (tools/arch_lanes_v41.wire_mutation on
    this floorplan's distances, results/arch/v41_lanes.json on_die_wire): per wire model, the traversal classes with
    their length and cycles, the DAG-exposed microseconds per token (1M, batch 1), the same traversals charged in
    full (every on-path node, the no-overlap bound) and the rate.  The ASAP7 routed-wire model is the headline's."""
    wm = wire_models(clock_hz)
    kinds, period_s = path_counts(dp)
    lanes = J(LANES)
    ow = lanes["on_die_wire"]
    geo = traversal_geometry(dp["sp"])
    assert all(math.isclose(geo["distances_mm"][k], v) for k, v in ow["distances_mm"].items()), \
        "v41_lanes.json on_die_wire was priced on another floorplan: regenerate tools/arch_lanes_v41.py"
    head, pre = lanes["design_point"][CTX], ow["design_point_pre_wire"][CTX]
    att = ow["attribution"][CTX]["ar"]
    res = {}
    for key, m in wm.items():
        if key == "fit_points":
            continue
        cyc = traversal_cycles(geo, key, clock_hz)
        rows = {}
        for name, t in TRAVERSALS.items():
            rows[name] = dict(mm=geo["distances_mm"][t["dist"]], cycles=cyc[t["dist"]],
                              ns=cyc[t["dist"]] / clock_hz * 1e9, what=t["what"], nodes=t["nodes"],
                              exposure=t["exposure"], charged=t["nodes"] != "none")
        if key == ow["model"]:
            rate, rate_mtp, T_us = head["ar"], head["mtp"], head["T_us"]
            exposed, full, by = att["exposed_us"], att["charged_in_full_us"], att["exposed_us_by_kind"]
        else:
            sv = ow["sensitivities"][key][CTX]
            rate, rate_mtp, T_us = sv["ar"], sv["mtp"], sv["T_us"]
            exposed, full, by = T_us - pre["T_us"], None, None
        res[key] = dict(paths=rows, exposed_us_per_token=exposed, charged_in_full_us=full,
                        exposed_us_by_node_kind=by, token_us=T_us, fraction_of_token=exposed / T_us,
                        rate=rate, rate_mtp=rate_mtp, rate_pre_wire=pre["ar"], rate_mtp_pre_wire=pre["mtp"],
                        in_tile_single_cycle=geo["distances_mm"]["in_tile"] <= m["reach_mm_per_cycle"])
    return dict(wire_models=wm, on_path_kinds=kinds, solve_period_us=period_s * 1e6, by_model=res,
                headline_model=ow["model"], on_path_nodes_by_kind=att["on_path_nodes_by_kind"],
                budget_charges_on_die_wire_us=att["exposed_us"],
                budget_note=("the design-point DAG (tools/arch_lanes_v41.wire_mutation) charges every registered "
                             "traversal on its node's edges; the DAG exposes a traversal only where its node is on "
                             "the critical path. The 10 ns UCIe hop covers the edge PHY only"))


# ---------------------------------------------------------------------------------------------------------------------
# 3. power map, IR drop, hot spot, clock
# ---------------------------------------------------------------------------------------------------------------------
def power_map(L, F, clock_hz):
    ps = J(POWER)
    cfg_die = J(ROOT / "configs/hardware/power_scenarios.json")["die"]
    bud = J(BUDGET)["power"]["static_w_per_die"]
    lk = cfg_die["leakage_w_per_mm2"]
    ck = val(cfg_die["clock_j_per_mm2_per_cycle"])
    cm = cfg_die["clock_region_multiplier"]
    area = {}
    for r in L["rows"]:
        area[r["group"]] = area.get(r["group"], 0.0) + r["placed_mm2"]
    logic_groups = ("engine", "vector", "control", "kv", "collective", "overhead")
    static = {}
    for gname, a in area.items():
        if gname == "rom":
            static[gname] = a * val(lk["rom_array"]) + ck * clock_hz * a * cm["rom_array"]
        elif gname == "sram":
            static[gname] = a * val(lk["sram_array"]) + ck * clock_hz * a * cm["sram_array"]
        elif gname in logic_groups or gname.startswith("phy"):
            static[gname] = a * val(lk["logic"]) + ck * clock_hz * a * cm["logic"]
    static["phy_hbm"] = static.get("phy_hbm", 0.0) + bud["hbm_interface_idle"]
    static["phy_serdes"] = static.get("phy_serdes", 0.0) + bud["serdes_always_on"]
    static["phy_ucie"] = static.get("phy_ucie", 0.0) + bud["ucie_idle"]
    comp_to_group = dict(mac="engine", weight_read_and_delivery="rom", kv_sram="sram", stream="vector",
                         links="phy_serdes", hbm_controller_phy_io="phy_hbm", draft="engine")
    out = {}
    for sc in ("A_measured_implementation", "B_proposed_production"):
        dpnt = ps["scenarios"][sc]["deepseek_v41_design_point"]
        out[sc] = {}
        for pt in ("ar_batch1", "mtp_batch1", "fill28", "fill28_mtp", "saturated_batch1024", "saturated_batch1024_mtp"):
            p = dpnt["per_context"][CTX][pt]
            # the HOTTEST die (power_scenarios.v41_hottest_die): its own components, over its active window
            per_die = p["hottest_die_window_factor"]
            dyn = {}
            for c, e in p["hottest_die_components_j_per_token"].items():
                gname = comp_to_group[c]
                dyn[gname] = dyn.get(gname, 0.0) + e * per_die * p["design_rate_tokens_s"]
            regions = {}
            for gname in sorted(set(static) | set(dyn)):
                w = static.get(gname, 0.0) + dyn.get(gname, 0.0)
                a = area.get(gname, 1e-9)
                regions[gname] = dict(w=w, mm2=a, w_per_mm2=w / a, static_w=static.get(gname, 0.0),
                                      dynamic_w=dyn.get(gname, 0.0))
            total = sum(v["w"] for v in regions.values())
            core = max((v for k, v in regions.items() if k in ("engine", "vector")), key=lambda v: v["w_per_mm2"])
            core_name = [k for k, v in regions.items() if v is core][0]
            hot = max((v for v in regions.values() if v["mm2"] >= 1.0), key=lambda v: v["w_per_mm2"])
            hot_name = [k for k, v in regions.items() if v is hot][0]
            out[sc][pt] = dict(regions=regions, die_w=total, scenario_hottest_die_w=p["hottest_die_w"],
                               hottest_die=p["hottest_die"], batch=p.get("batch"),
                               design_rate_tokens_s=p["design_rate_tokens_s"],
                               scenario_hottest_die_w_note="power_scenarios' die static carries leakage + clock + "
                                                           "HBM idle on the analytical 815 mm2 split at 1.034 GHz and "
                                                           "the always-on SerDes and UCIe idle (v41_links_static); "
                                                           "this map re-prices static on the ledger's areas at "
                                                           "1.087 GHz and charges the always-on SerDes and UCIe idle "
                                                           "of arch_budget_v41 power",
                               hot_spot=hot_name, hot_spot_w_per_mm2=hot["w_per_mm2"],
                               core_hot_spot=core_name, core_hot_spot_w_per_mm2=core["w_per_mm2"],
                               die_avg_w_per_mm2=total / L["die_mm2"])
    cool = ps["cooling_limits_w"]
    ref = dict(air_die_w=cool["air"]["2"]["die_w"], liquid_die_w=cool["liquid"]["2"]["die_w"],
               h200_die_avg_w_per_mm2=cool["air"]["1"]["reference_die_w_per_mm2"],
               note="no committed source publishes a sustainable hot-spot W/mm2 (configs/hardware/power_scenarios."
                    "json: 'none found'); the screen uses H200's published die-average flux (700 W package less "
                    "its stacks over 814 mm2) as a conservative local limit: a shipping die's hottest region "
                    "sustains at least its average")
    for sc in out:
        for pt, v in out[sc].items():
            v["within_air_die_limit"] = v["die_w"] <= ref["air_die_w"]
            v["within_liquid_die_limit"] = v["die_w"] <= ref["liquid_die_w"]
            v["hot_spot_within_h200_average"] = v["hot_spot_w_per_mm2"] <= ref["h200_die_avg_w_per_mm2"]
            v["core_hot_spot_within_h200_average"] = v["core_hot_spot_w_per_mm2"] <= ref["h200_die_avg_w_per_mm2"]
    return dict(points=out, cooling_reference=ref, clock_hz=clock_hz,
                attribution=("mac -> engine tiles; weight_read_and_delivery -> ROM; stream -> vector spine; kv_sram -> "
                             "SRAM; links -> SerDes strip; hbm_controller_phy_io (power_scenarios' die share of HBM "
                             "energy, 10.19 pJ/b: controller + PHY + I/O) -> the HBM PHY strips, the pessimistic "
                             "placement; static: leakage and clock on each region's placed area plus the always-on "
                             "SerDes, UCIe idle and HBM idle on their PHYs"),
                static_constants=dict(
        leakage_w_per_mm2={k: val(v) for k, v in lk.items()}, clock_j_per_mm2_per_cycle=ck,
        clock_region_multiplier={k: v for k, v in cm.items() if k != "source"},
        always_on=dict(serdes_w=bud["serdes_always_on"], ucie_idle_w=bud["ucie_idle"],
                       hbm_idle_w=bud["hbm_interface_idle"], source=src(BUDGET, "power.static_w_per_die"))))


def asap7_layer_rc():
    p = Path.home() / ".local/opentallas-pdk-asap7-platform/asap7/setRC.tcl"
    # the values are committed here from that file (ORFS asap7 platform, image digest in configs/pdk/
    # asap7_physical_lock.json); kilo-ohm and fF per um, the platform liberty's units
    rc = {"M8": (8.44765e-03, 1.03962e-01), "M9": (8.89556e-03, 9.28446e-02), "clock": (2.14161e-02, 1.45426e-01)}
    if p.exists():
        for line in p.read_text().splitlines():
            t = line.split()
            if len(t) >= 7 and t[0] == "set_layer_rc" and t[2] in ("M8", "M9"):
                rc[t[2]] = (float(t[4]), float(t[6]))
            if len(t) >= 6 and t[0] == "set_wire_rc" and t[1] == "-clock":
                rc["clock"] = (float(t[3]), float(t[5]))
    return rc


def ir_drop(PM):
    rc = asap7_layer_rc()
    w_min = 0.040                                    # um, M8/M9 WIDTH in asap7_tech_1x_201209.lef
    rho = {k: rc[k][0] * 1e3 * w_min for k in ("M8", "M9")}      # ohm per square
    grid = dict(stripe_w_um=1.0, pitch_um=40.0, source=str(PDN_DIE.relative_to(ROOT)) + " (M8/M9 -width 1.0 "
                "-pitch 40.0, VDD and VSS each once per pitch)")
    cov = grid["stripe_w_um"] / grid["pitch_um"]
    r_eff = statistics.mean(rho.values()) / cov                  # per net, per direction, ohm/sq
    V = CONST["vdd_v"]["value"]
    p = CONST["bump_pitch_um"]["value"] / math.sqrt(CONST["power_bump_fraction"]["value"])
    Rcell = p / math.sqrt(math.pi)
    a = CONST["bump_contact_radius_um"]["value"]
    geom = Rcell ** 2 * math.log(Rcell / a) - (Rcell ** 2 - a ** 2) / 2      # um2
    budget = CONST["ir_budget_fraction"]["value"] * V
    out = {}
    for sc, pts in PM["points"].items():
        out[sc] = {}
        for pt, v in pts.items():
            hot = v["regions"][v["core_hot_spot"]]
            Jd = hot["w_per_mm2"] / V * 1e-6                      # A per um2
            dv = Jd * r_eff / 2 * geom * 2                        # VDD and VSS nets each drop
            cov_needed = cov * dv / budget
            I_bump = Jd * p * p
            out[sc][pt] = dict(hot_region=v["core_hot_spot"], j_a_per_mm2=hot["w_per_mm2"] / V, drop_mv=dv * 1e3,
                               budget_mv=budget * 1e3, within_budget=dv <= budget,
                               m8m9_coverage_needed=cov_needed, amps_per_vdd_bump=I_bump,
                               die_current_a=v["die_w"] / V)
    return dict(model=("closed form: a sheet of resistance R per square, loaded uniformly at J A/um2, fed at a "
                       "square array of VDD bumps of pitch p through contacts of radius a; each bump's cell is "
                       "taken as the disk of equal area (radius R = p / sqrt(pi)), which gives a drop of "
                       "J R / 2 x (R^2 ln(R/a) - (R^2 - a^2)/2) from the bump to the cell edge; charged on VDD "
                       "and VSS alike"),
                sheet_ohm_per_sq=rho, grid=grid, grid_coverage_per_net=cov, r_eff_ohm_per_sq=r_eff,
                layer_rc_source="ORFS asap7 platform setRC.tcl (set_layer_rc M8/M9; kOhm/um at 40 nm width)",
                vdd_bump_pitch_um=p, cell_radius_um=Rcell, contact_radius_um=a, vdd_v=V, points=out,
                not_modelled="the local M1-M6 grid, via stacks, the interposer and package; transient (L di/dt) "
                             "droop, which the stage clock gating's wake-up makes the first-order PDN risk")


def htree(W, H, levels):
    """Total length and root-to-leaf length of an H-tree with 2^levels leaves over a W x H rectangle."""
    total, depth = 0.0, 0.0
    w, h = W, H
    n = 1
    for lv in range(levels):
        if lv % 2 == 0:
            seg = w / 2
            w /= 2
        else:
            seg = h / 2
            h /= 2
        total += n * seg
        depth += seg / 2
        n *= 2
    return total, depth


def clock_plan(F, clock_hz, wm, L):
    rc = asap7_layer_rc()
    mv = J(MATVEC_BLOCK)
    ins_ps = mv["routed_clock_insertion_ps"]
    skew_ps = mv["metrics"]["clock_skew_ps"]
    ratio = skew_ps / ins_ps
    W, H = F["die_w_mm"], F["die_h_mm"]
    leaves = F["tiles"]["n"] + 16             # tiles + PHY/edge regions
    lv = math.ceil(math.log2(leaves))
    total_mm, depth_mm = htree(W, H, lv)
    V = CONST["vdd_v"]["value"]
    c_ff_per_um = rc["clock"][1]
    cap_F = total_mm * 1e3 * c_ff_per_um * 1e-15 * CONST["clock_repeater_cap_factor"]["value"]
    p_global = cap_F * V * V * clock_hz
    tech_clock = J(ROOT / "configs/hardware/power_scenarios.json")["die"]["clock_j_per_mm2_per_cycle"]
    rows = {}
    for k in ("asap7_routed_fit", "tech_global_wire"):
        m = wm[k]
        ins = depth_mm * m["ps_per_mm"] + ins_ps
        rows[k] = dict(global_insertion_ps=ins, skew_ps_if_one_tree=ins * ratio,
                       skew_fraction_of_period=ins * ratio / m["period_ps"])
    return dict(
        plan=("one PLL per die from the tray reference; a global H-tree on the top metals to the "
              f"{leaves} regions (the {F['tiles']['n']} tiles, the spine and the edge PHY regions); each region "
              "is its own balanced local tree (as the routed blocks' CTS) with an integrated clock gate at its "
              "boundary for stage clock gating; paths BETWEEN regions are the pipelined long wires of the "
              "floorplan and are timed mesochronously (a region-to-region hop re-times into the receiver's "
              "clock through a small bisynchronous FIFO, or with a per-region delay-locked skew adjust), so the "
              "global tree's skew never sits on a single-cycle path"),
        leaves=leaves, levels=lv, htree_total_mm=total_mm, root_to_leaf_mm=depth_mm,
        global_tree_power_w=p_global,
        global_tree_basis=(f"C = {c_ff_per_um} fF/um (ASAP7 set_wire_rc -clock) x length x "
                           f"{CONST['clock_repeater_cap_factor']['value']} (repeaters), P = C V^2 f"),
        whole_die_clock_w=val(tech_clock) * clock_hz * (L["die_mm2"] - L["rom_mm2"]) +
        val(tech_clock) * clock_hz * L["rom_mm2"] * 0.15,
        whole_die_clock_basis="power_scenarios die.clock_j_per_mm2_per_cycle on the ledger's logic and ROM areas "
                              "(ROM at the 0.15 region multiplier), ungated -- the upper bound stage gating removes",
        measured_local=dict(block="ot_hdc_matvec (budgeted route, 0.4 x 0.4 mm)", insertion_ps=ins_ps,
                            skew_ps=skew_ps, skew_over_insertion=ratio, source=str(MATVEC_BLOCK.relative_to(ROOT))),
        by_wire_model=rows,
        verdict=("a single synchronous tree across the die is not viable: at the skew/insertion ratio the routed "
                 "matrix engine measured, the global tree's skew alone is a large fraction of the 920 ps period; "
                 "regional trees with mesochronous crossings are required (the rack already runs every link "
                 "plesiochronously, results/rtl/v41_link_cdc_campaign.json)"))


# ---------------------------------------------------------------------------------------------------------------------
# 4. verdict
# ---------------------------------------------------------------------------------------------------------------------
MISSING_ROUTES = [
    ("block-dot pool tile (ROM slice + lanes), the die's repeated unit", "one wgt_qtile routed closed (1,090 MHz); no "
     "tile with its ROM banks and read network exists"),
    ("BF16 pool tile", "only the single MAC is routed (1,040 MHz)"),
    ("vector unit (light + SFU lanes, reducer, chaining)", "light lane has no RTL route; SFU lane synthesis only"),
    ("HC projection block", "boundary characterisation only (chip/boundary/ot_hdc_v41_hcproj.json)"),
    ("select, 4 x 16 quartered", "tselect_w16 routed 1,087 MHz, not closed"),
    ("one-shot collective die engine (ot_rom_oneshot_die_px)", "in progress on claude/px-physical; d32 routed "
     "1,006 MHz not closed"),
    ("KV/key streamer", "routed 1,128 MHz, not closed"),
    ("Sinkhorn", "routed 152 MHz, a multicycle path by design; needs a multicycle-constrained route"),
    ("long-wire pipeline (spine <-> tiles, spine <-> PHY edges)", "express-link records exist only at 1-3 mm"),
    ("tile, spine and die assembly (tools/chip_assembly level 2/3 for V4.1)", "no V4.1 tile or die: the superseded wrappers were retired and assemble.py --arch v41_rom rejects the build until ot_hdc_core_v41x is integrated; the flow is reusable"),
    ("ROM and SRAM macros", "abstract views from the compilers, no layout; the HBM3E PHY is an abstract"),
    ("power grid and IR sign-off", "no die-level PDN analysis has run on any design here"),
]


def verdict(Ll, Lh, F, W_, PM, IR, CK, sens):
    area_ok = Ll["fits"] and Lh["fits"]
    wm = W_["by_model"]
    B = PM["points"]["B_proposed_production"]
    A = PM["points"]["A_measured_implementation"]
    worst_B = max(B.values(), key=lambda v: v["die_w"])
    worst_A = max(A.values(), key=lambda v: v["die_w"])
    ir_B = max(IR["points"]["B_proposed_production"].values(), key=lambda v: v["drop_mv"])
    risks = []
    if not area_ok or sens["break_even_utilisation"] > CONST["placement_utilisation"]["value"] - 0.05:
        risks.append(dict(risk="area", detail=(
            f"the layer die needs {Ll['placed_total_mm2']:.0f} mm2 at {Ll['placement_utilisation']:.2f} placement "
            f"utilisation ({Ll['whitespace_mm2']:+.0f} mm2 of whitespace); it closes above "
            f"{sens['break_even_utilisation']:.2f} utilisation, or at m = 1 "
            f"({sens['m1_core']['whitespace_mm2']:+.0f} mm2), or with the N5 logic credit "
            f"({sens['n5_logic_credit']['whitespace_mm2']:+.0f} mm2); the MTP lane multiplier m = 2 is what fills "
            "the die, and 'inside the 328.9 mm2 envelope' compared standard-cell area with a placed-area envelope")))
    risks.append(dict(risk="long wires", detail=(
        f"the design point now charges its registered on-die traversals: "
        f"{wm['asap7_routed_fit']['exposed_us_per_token']:.1f} us per 1M token on the ASAP7 routed-wire model "
        f"({100 * wm['asap7_routed_fit']['fraction_of_token']:.0f}% of the {wm['asap7_routed_fit']['token_us']:.1f} us "
        f"token; {wm['tech_global_wire']['exposed_us_per_token']:.1f} us on technology.json's 150 ps/mm); the 1M rate "
        f"is {wm['asap7_routed_fit']['rate']:,.0f} tok/s/user ({wm['tech_global_wire']['rate']:,.0f} at 150 ps/mm, "
        f"{wm['asap7_routed_fit']['rate_pre_wire']:,.0f} with no wire); the levers are sub-spines and collective "
        "engines at the tile rows")))
    risks.append(dict(risk="power (scenario A)", detail=(
        f"on the measured ASAP7 MAC energy the worst point draws {worst_A['die_w']:,.0f} W per die against the "
        f"{PM['cooling_reference']['air_die_w']} W air / {PM['cooling_reference']['liquid_die_w']} W liquid die "
        f"limits; the engine tiles run at {worst_A['core_hot_spot_w_per_mm2']:.2f} W/mm2")))
    risks.append(dict(risk="power (scenario B, saturated with MTP)", detail=(
        f"the worst production point is {worst_B['die_w']:.0f} W per die "
        f"({'within' if worst_B['within_air_die_limit'] else 'over'} the air limit, "
        f"{'within' if worst_B['within_liquid_die_limit'] else 'over'} liquid); engine tiles "
        f"{worst_B['core_hot_spot_w_per_mm2']:.2f} W/mm2 and the hottest region ({worst_B['hot_spot']}) "
        f"{worst_B['hot_spot_w_per_mm2']:.2f} W/mm2 against the H200 die average "
        f"{PM['cooling_reference']['h200_die_avg_w_per_mm2']:.3f}: the PHY strips, not the engines, are the "
        "thermal hot spots")))
    risks.append(dict(risk="IR / PDN", detail=(
        f"the repository's die grid (M8/M9 1 um at 40 um) on ASAP7's thin top metals drops "
        f"{ir_B['drop_mv']:.0f} mV in the scenario-B hot spot against a {ir_B['budget_mv']:.0f} mV budget "
        f"(needs {100 * ir_B['m8m9_coverage_needed']:.1f}% M8/M9 coverage per net); a production N5 stack's thick "
        "top metal and RDL change this by an order of magnitude, so it is an ASAP7 statement, not an N5 one")))
    risks.append(dict(risk="clock", detail=CK["verdict"]))
    risks.append(dict(risk="SerDes area and PHY evidence", detail=(
        "the 112G lane area is assumed and the HBM3E PHY is an abstract; the UCIe module is the only published "
        "PHY footprint")))
    return dict(
        area_closes_layer=Ll["fits"], area_closes_head=Lh["fits"],
        long_wire_timing=("closes with pipelining (every path is registered at the per-cycle reach); the latency "
                          "is charged in the design point"), long_wire_fraction_asap7=wm["asap7_routed_fit"]["fraction_of_token"],
        long_wire_fraction_tech=wm["tech_global_wire"]["fraction_of_token"],
        power_B_worst_w=worst_B["die_w"], power_B_within_air=worst_B["within_air_die_limit"],
        power_A_worst_w=worst_A["die_w"], power_A_within_air=worst_A["within_air_die_limit"],
        ir_B_worst_mv=ir_B["drop_mv"], ir_B_within_budget=ir_B["within_budget"],
        criteria=dict(
            area=dict(verdict="conditional" if area_ok else "fails",
                      condition=f"placement utilisation >= {sens['break_even_utilisation']:.2f} at MTP m = 2 "
                                f"(ledger assumes {Ll['placement_utilisation']:.2f}); m = 1 or the N5 logic credit "
                                "leave > 150 mm2"),
            long_wire_timing=dict(verdict="closes by pipelining; latency charged in the design point",
                                  condition=f"{wm['asap7_routed_fit']['exposed_us_per_token']:.1f} us per token "
                                            f"(ASAP7 routed-wire model; {wm['tech_global_wire']['exposed_us_per_token']:.1f}"
                                            " at 150 ps/mm) in the headline; floorplan levers would recover it"),
            power=dict(verdict=(("scenario B closes on air at every point" if worst_B["within_air_die_limit"] else
                                 "scenario B closes on liquid, not on air at its worst point"
                                 if worst_B["within_liquid_die_limit"] else
                                 "scenario B exceeds both the air and the liquid die limit at its worst point")
                                + "; scenario A fails"),
                       cooling_by_point={pt: ("air" if v["within_air_die_limit"] else "liquid"
                                              if v["within_liquid_die_limit"] else "neither")
                                         for pt, v in B.items()},
                       condition=f"hottest die (power_scenarios.v41_hottest_die): B worst {worst_B['die_w']:.0f} W "
                                 f"vs air {PM['cooling_reference']['air_die_w']} / liquid "
                                 f"{PM['cooling_reference']['liquid_die_w']} W; A worst {worst_A['die_w']:,.0f} W"),
            ir=dict(verdict="closes with a denser top grid" if not ir_B["within_budget"] else "closes",
                    condition=f"B hot spot {ir_B['drop_mv']:.0f} mV vs {ir_B['budget_mv']:.0f} mV on the repository's "
                              f"2.5% M8/M9 grid; {100 * ir_B['m8m9_coverage_needed']:.1f}% coverage per net closes it"),
            clock=dict(verdict="closes only as regional trees with mesochronous crossings", condition=CK["verdict"])),
        closes=("conditionally" if (area_ok and worst_B["within_liquid_die_limit"]) else
                "not at every operating point" if area_ok else "no"),
        summary=("on the adopted design point the layer die closes CONDITIONALLY: on area only above the stated "
                 "placement utilisation (the MTP lane multiplier is what fills it), on power only in scenario B "
                 + ("(within the air limit at every point)" if worst_B["within_air_die_limit"] else
                    "(liquid cooling at its worst point)" if worst_B["within_liquid_die_limit"] else
                    "(and there not at every operating point: the hottest die -- the stage that holds an uncapped "
                    "index scan -- exceeds even the liquid limit at its worst point)")
                 + ", on IR only with a denser top grid than the "
                 "repository's die grid, on the clock only as regional trees, and on long-wire timing only by "
                 "pipelining every spine/tile/PHY traversal -- whose per-token latency the design point now charges"),
        top_risks=risks,
        missing_routes=[dict(block=a, status=b) for a, b in MISSING_ROUTES],
        next_physical_steps=[
            "route one block-dot tile with its ROM banks and read network at 1.087 GHz (the die's repeated unit; "
            "it fixes the placement utilisation this ledger assumes)",
            "route a 5-10 mm pipelined express link on M8/M9 (the spine <-> tile and spine <-> PHY wire) and "
            "re-fit the wire model beyond 3 mm",
            "recover the charged on-die traversals with floorplan levers (vector sub-spines per half-die, collective "
            "engines at the tile rows) and re-derive the design point",
            "decide m = 2 against the die area: at ASAP7 densities the MTP lane multiplier fills the die",
            "integrate ot_hdc_core_v41x into a V4.1 tile and die, then run them through tools/chip_assembly "
            "(budgets, re-closure) and a die-level PDN/IR analysis on the tile abstracts",
            "source a 112G SerDes lane area and an HBM3E PHY footprint (both assumed here)"])


# ---------------------------------------------------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------------------------------------------------
COLORS = dict(rom=("#dfe7f3", "#3b5b8c"), engine=("#f6dcc7", "#a3531c"), vector=("#e2efd9", "#3f7a2a"),
              collective=("#efd9ee", "#7a2a74"), kv=("#fff1c7", "#8a6d0d"), phy_hbm=("#d6d6d6", "#444444"),
              phy_ucie=("#cfe8e8", "#23706f"), phy_serdes=("#e8d2d2", "#7a2323"), control=("#e2efd9", "#3f7a2a"))


def svg(F, L, W_, PM):
    s = 22.0
    Wd, Hd = F["die_w_mm"], F["die_h_mm"]
    pad, top, right = 30, 64, 350
    Wpx, Hpx = Wd * s + 2 * pad + right, Hd * s + top + 90
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wpx:.0f} {Hpx:.0f}" '
         f'font-family="Helvetica, Arial, sans-serif" font-size="11">',
         f'<rect width="{Wpx:.0f}" height="{Hpx:.0f}" fill="#ffffff"/>',
         f'<text x="{pad}" y="22" font-size="15" font-weight="bold">DeepSeek-V4.1 ROM array: layer die floorplan '
         f'(analytical, {Wd:.1f} x {Hd:.2f} mm = {L["die_mm2"]:.0f} mm2)</text>',
         f'<text x="{pad}" y="40" fill="#555">Areas from the ledger (ASAP7 cell area / {L["placement_utilisation"]:.2f} '
         f'utilisation, N5 ROM density, published UCIe-A module, assumed HBM/SerDes PHY). tools/v41_die_assembly.py</text>',
         f'<text x="{pad}" y="54" fill="#555">Package peer (UCIe) to the right; package outer edge (board SerDes) '
         f'to the left; HBM3E stacks above and below.</text>']

    def X(x):
        return pad + x * s

    def Y(y):
        return top + (Hd - y) * s

    o.append(f'<rect x="{X(0):.1f}" y="{Y(Hd):.1f}" width="{Wd * s:.1f}" height="{Hd * s:.1f}" fill="#fafafa" '
             f'stroke="#000" stroke-width="1.5"/>')
    for r in sorted(F["rects"], key=lambda r: 0 if r.get("tile") else 1):
        fill, stroke = COLORS.get(r["cls"], ("#eeeeee", "#666666"))
        o.append(f'<rect x="{X(r["x"]):.1f}" y="{Y(r["y"] + r["h"]):.1f}" width="{r["w"] * s:.1f}" '
                 f'height="{r["h"] * s:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{0.4 if r.get("tile") else 1}"/>')
        if not r.get("tile") and r["cls"] not in ("kv", "collective"):
            vertical = r["h"] > 2.5 * r["w"]
            cx, cy = X(r["x"] + r["w"] / 2), Y(r["y"] + r["h"] / 2)
            label = r["name"]
            if vertical:
                o.append(f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-size="9" '
                         f'transform="rotate(-90 {cx:.1f} {cy:.1f})">{label}</text>')
            elif r["w"] * s > 60:
                o.append(f'<text x="{cx:.1f}" y="{cy + 3:.1f}" text-anchor="middle" font-size="9">{label}</text>')
    # wire paths: numbered markers, described in the side panel
    xc, yc = F["spine"]["x"] + F["spine"]["w"] / 2, Hd / 2
    far = max(F["tile_centres"], key=lambda t: abs(t["x"] - xc) + abs(t["y"] - yc))
    wa = W_["by_model"]["asap7_routed_fit"]["paths"]
    wt = W_["by_model"]["tech_global_wire"]["paths"]
    wires = [(far["x"], far["y"], "pool_operand_in", "spine to farthest tile (matvec / scan in and out)", "#c0392b"),
             (F["core"]["x1"], yc + 0.6, "collective_edge", "spine to UCIe-level collective", "#7a2a74"),
             (F["core"]["x0"], yc - 0.6, "stage_hop_edge", "spine to SerDes (stage hop, pair collective)", "#7a2323"),
             (0.27 * Wd, F["core"]["y1"], "kv_gather_request", "select to HBM controller (row gather)", "#8a6d0d")]
    for i, (x2, y2, key, _lab, col) in enumerate(wires, 1):
        o.append(f'<polyline points="{X(xc):.1f},{Y(yc):.1f} {X(x2):.1f},{Y(yc):.1f} {X(x2):.1f},{Y(y2):.1f}" '
                 f'fill="none" stroke="{col}" stroke-width="1.8" stroke-dasharray="6,3"/>')
        o.append(f'<circle cx="{X(x2):.1f}" cy="{Y(y2):.1f}" r="8" fill="#ffffff" stroke="{col}" stroke-width="1.5"/>')
        o.append(f'<text x="{X(x2):.1f}" y="{Y(y2) + 3.5:.1f}" text-anchor="middle" font-size="10" '
                 f'font-weight="bold" fill="{col}">{i}</text>')
    # legend + ledger summary
    lx = X(Wd) + 20
    ly = top
    o.append(f'<text x="{lx}" y="{ly}" font-weight="bold">Area ledger (placed mm2)</text>')
    ly += 16
    names = dict(rom="mask-ROM", engine="block-dot + BF16 pools, HC", vector="vector unit, SFU, side units",
                 control="control, select, gather", kv="KV/key streamers", collective="collectives",
                 sram="SRAM buffers", phy_hbm="HBM3E PHY (4)", phy_ucie="UCIe-A", phy_serdes="112G SerDes",
                 overhead="overhead (PLL, PDN, DFT)")
    for gname, v in sorted(L["by_group_mm2"].items(), key=lambda kv: -kv[1]):
        fill, stroke = COLORS.get(gname, ("#eeeeee", "#666666"))
        o.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" fill="{fill}" stroke="{stroke}"/>')
        o.append(f'<text x="{lx + 16}" y="{ly}">{names.get(gname, gname)}: {v:.1f}</text>')
        ly += 15
    ly += 4
    o.append(f'<text x="{lx}" y="{ly}" font-weight="bold">total {L["placed_total_mm2"]:.0f} of {L["die_mm2"]:.0f} mm2 '
             f'({L["whitespace_mm2"]:+.0f})</text>')
    ly += 22
    B = PM["points"]["B_proposed_production"]
    o.append(f'<text x="{lx}" y="{ly}" font-weight="bold">Die power, scenario B (W)</text>')
    ly += 15
    for pt in ("ar_batch1", "mtp_batch1", "fill28_mtp", "saturated_batch1024_mtp"):
        o.append(f'<text x="{lx}" y="{ly}">{pt}: {B[pt]["die_w"]:.0f} (tiles {B[pt]["core_hot_spot_w_per_mm2"]:.2f}, '
                 f'{B[pt]["hot_spot"]} {B[pt]["hot_spot_w_per_mm2"]:.2f} W/mm2)</text>')
        ly += 14
    wm = W_["by_model"]
    ly += 8
    o.append(f'<text x="{lx}" y="{ly}" font-weight="bold">On-die wire per token (1M, charged)</text>')
    ly += 15
    o.append(f'<text x="{lx}" y="{ly}">ASAP7 routed fit: {wm["asap7_routed_fit"]["exposed_us_per_token"]:.1f} us</text>')
    ly += 14
    o.append(f'<text x="{lx}" y="{ly}">150 ps/mm: {wm["tech_global_wire"]["exposed_us_per_token"]:.1f} us '
             f'(token {wm["tech_global_wire"]["token_us"]:.1f} us)</text>')
    ly += 22
    o.append(f'<text x="{lx}" y="{ly}" font-weight="bold">Long wires (mm; cycles ASAP7 / 150 ps/mm)</text>')
    ly += 15
    for i, (_x2, _y2, key, lab, col) in enumerate(wires, 1):
        o.append(f'<text x="{lx}" y="{ly}" fill="{col}">{i}. {lab}: {wa[key]["mm"]:.1f} mm, '
                 f'{wa[key]["cycles"]} / {wt[key]["cycles"]}</text>')
        ly += 14
    o.append(f'<text x="{pad}" y="{Hpx - 40:.0f}" fill="#555">Tiles: {F["tiles"]["n"]} (ROM | lane column | ROM), '
             f'{F["tiles"]["w_mm"]:.2f} x {F["tiles"]["h_mm"]:.2f} mm; weights stay in their tile. Overhead '
             f'(PLL, PDN, DFT) and whitespace are spread through the tiles and channels.</text>')
    o.append(f'<text x="{pad}" y="{Hpx - 24:.0f}" fill="#555">Analytical floorplan, not a routed die. '
             f'ASAP7 block areas are not N5 areas (docs/ROM_DENSITY_NODE_TRANSFER.md s11).</text>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------------------------------------------------------------
def build():
    dp, areas, asrc, m1, m2 = design_point()
    tech = J(TECH)
    clock_hz = dp["hz"][0] or J(LADDER)["clock_hz"]
    Ll = ledger("layer", dp, areas, asrc, m1, m2)
    Lh = ledger("head", dp, areas, asrc, m1, m2)
    sens = ledger_sensitivities(dp, areas, asrc, m1, m2, tech)
    F = floorplan(Ll)
    Fh = floorplan(Lh)
    W_ = long_wires(F, dp, clock_hz)
    PM = power_map(Ll, F, clock_hz)
    IR = ir_drop(PM)
    CK = clock_plan(F, clock_hz, W_["wire_models"], Ll)
    ad = None
    try:
        import decode_critical_path as D
        _pts, ds = D.v41_study_rows()
        ad = ds[D.ARRAY_DESIGN]["area_split_per_device"]
    except Exception:            # pragma: no cover - the analytical design is a comparison only
        pass
    rec = dict(
        schema=SCHEMA, tool="tools/v41_die_assembly.py",
        inputs={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS if p.exists()},
        status="analytical assembly on committed evidence; no routed die exists",
        clock_hz=clock_hz, context=int(CTX),
        design_point=dict(label="ladder top with the adopted levers, R-L9 lanes, MTP m = 2",
                          widths=dict(weight_macs=dp["sp"].weight_macs, bf16_macs=dp["sp"].bf16_macs,
                                      su_lanes=dp["sp"].su_lanes, sfu_lanes=dp["sp"].sfu_lanes,
                                      hc_macs=dp["sp"].hc_macs, sel_lanes=dp["sp"].sel_lanes, lane_mult=2),
                          engine_cell_area_mm2_m1=m1["total"], engine_cell_area_mm2_m2=m2["total"]),
        constants=CONST,
        analytical_split=ad,
        ledger=dict(layer=Ll, head=Lh, sensitivities=sens, utilisation_evidence=utilisation_evidence(),
                    node_transfer=("ASAP7 areas carried unscaled (docs/ROM_DENSITY_NODE_TRANSFER.md s11, "
                                   "docs/CHIP_ARCHITECTURE_DESIGN.md s0); the N5 logic credit is a labelled "
                                   "sensitivity")),
        floorplan=dict(layer=F, head=dict(overfill_mm2=Fh["overfill_mm2"], content_mm2=Fh["content_mm2"],
                                          core=Fh["core"],
                                          note="the head die repeats the layer die's floorplan plus the draft-window "
                                               "SRAM block beside the spine (rack C10)")),
        long_wires=W_, power=PM, ir_drop=IR, clock=CK)
    rec["verdict"] = verdict(Ll, Lh, F, W_, PM, IR, CK, sens)
    rec["proposed_atlas_additions"] = [
        "a 'layer die' panel: the floorplan SVG with the ledger by group and evidence class",
        "the on-die wire term per token (ASAP7 fit and 150 ps/mm) beside the collective and hop terms",
        "the die power map for scenarios A and B with the hot-spot flux and the H200 die-average reference",
        "the m = 2 area caveat: engine cell area vs placed area at the stated utilisation",
        "the missing hierarchical routes list as the K2 (layer/head die P&R) prerequisites"]
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--svg", type=Path, default=SVG)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    a.svg.parent.mkdir(parents=True, exist_ok=True)
    a.svg.write_text(svg(rec["floorplan"]["layer"], rec["ledger"]["layer"], rec["long_wires"], rec["power"]))
    L, v = rec["ledger"]["layer"], rec["verdict"]
    print(f"layer die: {L['placed_total_mm2']:.1f} of {L['die_mm2']:.0f} mm2 (whitespace {L['whitespace_mm2']:+.1f}); "
          f"head die: {rec['ledger']['head']['placed_total_mm2']:.1f}")
    for g, x in sorted(L["by_group_mm2"].items(), key=lambda kv: -kv[1]):
        print(f"  {g:12s} {x:7.1f}")
    print("sensitivities:", json.dumps({k: (round(x["whitespace_mm2"], 1) if isinstance(x, dict) and "whitespace_mm2" in x
                                           else x) for k, x in rec["ledger"]["sensitivities"].items()}, default=str))
    for k, m in rec["long_wires"]["by_model"].items():
        print(f"wire {k}: {m['exposed_us_per_token']:.2f} us/token ({100 * m['fraction_of_token']:.1f}%)")
    for sc, pts in rec["power"]["points"].items():
        for pt, x in pts.items():
            print(f"{sc[:1]} {pt:24s} die {x['die_w']:7.1f} W (scenario {x['scenario_hottest_die_w']:7.1f}) tiles "
                  f"{x['core_hot_spot_w_per_mm2']:.3f}, hot {x['hot_spot']} {x['hot_spot_w_per_mm2']:.3f} W/mm2; IR {rec['ir_drop']['points'][sc][pt]['drop_mv']:.1f} mV")
    print("clock:", {k: round(x["skew_ps_if_one_tree"]) for k, x in rec["clock"]["by_wire_model"].items()},
          "global tree", round(rec["clock"]["global_tree_power_w"], 2), "W")
    print("verdict closes:", v["closes"], json.dumps({k: x["verdict"] for k, x in v["criteria"].items()}))


if __name__ == "__main__":
    main()
