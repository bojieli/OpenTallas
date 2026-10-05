#!/usr/bin/env python3
"""Iso-area throughput per mm2 against the A100, at THREE levels of inclusion.

WHAT THIS ANSWERS, AND WHY IT REFUSES ONE NUMBER
------------------------------------------------
The design goal is "match performance in iso-area of modern GPUs (eg A100) in the
similar technology node". There is no single honest ratio for that, and this tool
will not print one. ``tools/audit_mac_array_density.py`` established why: an
array's standard-cell area against a whole GPU die flatters the array by every
square millimetre of cache, register file, scheduler and PHY the array does not
have, and a comparison built that way always looks like a win. So three levels of
inclusion are reported, each against the A100 comparator matched to it:

  L1 array_level   the MAC array alone -- multipliers, adders, accumulators and
                   the operand broadcast tree. No operand storage. Compared with
                   the A100's throughput over its STANDARD-CELL LOGIC area,
                   because that is the narrower and therefore less flattering of
                   the two available denominators. An UPPER BOUND: nothing a
                   complete design adds can raise it.
  L2 unit_level    one ot_compute_unit: the same 16-lane array PLUS the operand
                   delivery it cannot run without -- two ganged weight SRAM
                   macros, the activation register file, the K-walking sequencer
                   and the interconnect between them. Still compared with the
                   A100's logic area. This is where a multiplier count stops
                   being a density figure.
  L3 device_level  a whole chip assembled from routed blocks for one declared
                   capability, compared with the A100's WHOLE 826 mm2 die. The
                   only level at which both sides are charged for a product.

L1 > L2 > L3 is not a defect of the measurement, it is the cost of inclusion, and
the three numbers are what say WHERE the cost lands.

PEAK IS NOT SUSTAINED, AND THIS REPOSITORY HAS THE MEASUREMENT
--------------------------------------------------------------
All three densities are PEAK ARITHMETIC: lanes x 2 x clock, every lane retiring a
MAC every cycle. That assumption is independently measured here and it does not
hold. ``rtl/test/tb_kernel_dispatch_throughput.sv``, driven at the control plane's
own measured issue rate, reports the array starved for half its cycles. The
sustained de-rating is reported beside the peak figures rather than folded into
them, because a de-rated peak is still not a workload measurement.

EVIDENCE CLASSES, WHICH ARE NOT INTERCHANGEABLE
-----------------------------------------------
Every figure carries the class it was measured at. A pre-layout setup report is
not a routed one -- this repository has recorded a pre-layout 8,691 MHz against a
post-route 4,092 MHz on the same block, 2.12x optimistic -- so a record counts as
routed here only if its acceptance block carries a place_and_route check whose
scope is "post-route, extracted parasitics". CLOSED is a stricter thing again: the
routed netlist must additionally carry zero max-slew, max-cap and max-fanout
violations and the engineering verdict must be pass. Both are reported per block
and neither is inferred from the other.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import datetime
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TECH_INPUTS = ROOT / "configs/hardware/technology_inputs.json"
TECHNOLOGY = ROOT / "configs/hardware/technology.json"
ASAP7_DIR = ROOT / "results/physical_abi3/asap7"
CHIP_AUDIT = ROOT / "tools/audit_chip_level_density.py"
CONTROL_RECORD = ROOT / "results/rtl/abi3_g1e_control_end_to_end.json"

#: One MAC retires a multiply and an add, matching how dense BF16 is quoted.
FLOPS_PER_MAC = 2

POST_ROUTE_SCOPE = "post-route, extracted parasitics"


def run(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=False).stdout.strip()


def git_state() -> dict[str, Any]:
    return {
        "commit": run("rev-parse", "HEAD") or None,
        "branch": run("rev-parse", "--abbrev-ref", "HEAD") or None,
        "worktree_dirty": bool(run("status", "--porcelain")),
        "dirty_paths": run("status", "--porcelain").splitlines() or [],
    }


def _dig(body: Any, *keys: str) -> Any:
    for k in keys:
        body = body[k]
    return body


def comparator() -> dict[str, Any]:
    """Every A100 figure read from a recorded config key, none hardcoded here."""
    facts = json.loads(TECH_INPUTS.read_text())["source_facts"]["a100_sxm_80gb"]
    tech = json.loads(TECHNOLOGY.read_text())
    die_entry = _dig(tech, "reference_parts", "a100_sxm_80gb", "die_area_mm2")
    frac_entry = _dig(tech, "power", "gpu_logic_area_fraction")

    ops = float(facts["bf16_dense_ops_s"])
    die_mm2 = float(die_entry["value"])
    frac = float(frac_entry["value"])
    logic_mm2 = die_mm2 * frac
    power_w = float(facts["power_w"])
    return {
        "part": "a100_sxm_80gb",
        "process": facts["process"],
        "bf16_dense_ops_s": ops,
        "bf16_source": "configs/hardware/technology_inputs.json"
                       " :: source_facts.a100_sxm_80gb.bf16_dense_ops_s",
        "bf16_evidence": facts["evidence"],
        "die_area_mm2": die_mm2,
        "die_area_source": "configs/hardware/technology.json"
                           " :: reference_parts.a100_sxm_80gb.die_area_mm2.value",
        "die_area_grade": die_entry.get("grade"),
        "logic_area_fraction": frac,
        "logic_area_fraction_source": "configs/hardware/technology.json"
                                      " :: power.gpu_logic_area_fraction.value",
        "logic_area_fraction_grade": frac_entry.get("grade"),
        "logic_area_mm2": logic_mm2,
        "device_level_ops_s_per_mm2": ops / die_mm2,
        "logic_level_ops_s_per_mm2": ops / logic_mm2,
        "power_w": power_w,
        "ops_s_per_w": ops / power_w,
    }


def source_currency(design: dict[str, Any]) -> dict[str, Any]:
    """Has the RTL the record was built from changed since?"""
    rows = []
    for src in design.get("sources") or []:
        path = ROOT / src["path"]
        cur = (hashlib.sha256(path.read_bytes()).hexdigest()
               if path.exists() else None)
        rows.append({"path": src["path"], "recorded_sha256": src["sha256"],
                     "current_sha256": cur,
                     "current": cur == src["sha256"]})
    return {"all_current": all(r["current"] for r in rows) if rows else None,
            "drifted": [r["path"] for r in rows if not r["current"]],
            "files": rows}


def routed_inventory() -> list[dict[str, Any]]:
    """Every asap7 record whose place-and-route stage actually ran."""
    out = []
    for path in sorted(ASAP7_DIR.rglob("*.json")):
        try:
            body = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(body, dict):
            continue
        metrics = (body.get("place_and_route") or {}).get("metrics") or {}
        if not metrics.get("fmax_hz"):
            continue
        checks = {c.get("stage"): c
                  for c in ((body.get("acceptance") or {}).get("checks") or [])}
        pr = checks.get("place_and_route") or {}
        if POST_ROUTE_SCOPE not in str(pr.get("scope")):
            continue
        design = body.get("design") or {}
        out.append({
            "record": str(path.relative_to(ROOT)),
            "top": design.get("top"),
            "parameters": design.get("parameters"),
            "evidence_class": "post-route, extracted parasitics",
            "post_route_scope": pr.get("scope"),
            "target_clock_period_ns": design.get("clock_period_ns"),
            "post_route_fmax_hz": float(metrics["fmax_hz"]),
            "fmax_basis": design.get("fmax_basis"),
            "standard_cell_count": metrics.get("standard_cell_count"),
            "cells_basis": design.get("cells_basis"),
            "standard_cell_area_um2": metrics.get("standard_cell_area_um2"),
            "macro_count": metrics.get("macro_count"),
            "macro_area_um2": metrics.get("macro_area_um2"),
            "core_area_um2": metrics.get("core_area_um2"),
            "die_area_um2": metrics.get("die_area_um2"),
            "utilization_fraction": metrics.get("utilization_fraction"),
            "power_total_w_default_activity": metrics.get("power_total_w"),
            "setup_wns_ns": metrics.get("setup_wns_ns"),
            "hold_wns_ns": metrics.get("hold_wns_ns"),
            "drc_errors": metrics.get("drc_errors"),
            "antenna_violating_nets": metrics.get("antenna_violating_nets"),
            "signal_integrity_violations":
                design.get("signal_integrity_violations"),
            "closed": design.get("closed"),
            "closed_basis": design.get("closed_basis"),
            "acceptance_status": (body.get("acceptance") or {}).get("status"),
            "acceptance_reason": (body.get("acceptance") or {}).get("reason"),
            "source_currency": source_currency(design),
        })
    return out


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text())


def derived_lane_count(rel_source: str, pattern: str, record: dict) -> dict[str, Any]:
    """Read a width out of the RTL the record was built from, never a constant."""
    src = ROOT / rel_source
    text = src.read_text()
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(f"{rel_source}: no match for {pattern!r}")
    recorded = {s["path"]: s["sha256"] for s in (record["design"]["sources"])}
    cur = hashlib.sha256(src.read_bytes()).hexdigest()
    return {"value": int(m.group(1)), "source": rel_source,
            "pattern": pattern,
            "source_matches_record": recorded.get(rel_source) == cur}



def prelayout_modules(paths: list[Path]) -> list[dict[str, Any]]:
    """Per-module synth+STA of the control plane. PRE-LAYOUT, not routed.

    These exist to attribute the full control plane's non-closure to a
    structure. They are deliberately NOT mixed into any density: a pre-layout
    setup report is a different evidence class from a routed one, and this
    repository has been caught by exactly that confusion before.
    """
    out = []
    for path in paths:
        body = json.loads(path.read_text())
        syn = body.get("synthesis") or {}
        sta = body.get("static_timing") or {}
        design = body.get("design") or {}
        search = sta.get("fmax_search") or {}
        out.append({
            "top": design.get("top"),
            "evidence_class": "PRE-LAYOUT: pinned Yosys map plus pinned OpenSTA "
                              "on the mapped netlist, no placement, no routing, "
                              "no extracted parasitics. NOT comparable with any "
                              "post-route fmax in this artifact.",
            "stages_completed": body.get("stages_completed"),
            "acceptance_status": body.get("status"),
            "target_clock_period_ns": body.get("target_clock_period_ns"),
            "standard_cell_count": syn.get("cell_count"),
            "combinational_cell_count": syn.get("combinational_cell_count"),
            "sequential_area_um2": syn.get("sequential_area_um2"),
            "standard_cell_area_um2": syn.get("cell_area_um2"),
            "prelayout_critical_path_ns": sta.get("critical_path_ns"),
            "prelayout_fmax_hz": sta.get("fmax_hz"),
            "prelayout_fmax_period_independent_hz": search.get("fmax_hz"),
            "prelayout_fmax_search_method": search.get("method"),
            "fmax_definition_caveat": sta.get("fmax_definition"),
            "sources": [{"path": s["path"], "sha256": s["sha256"]}
                        for s in design.get("sources") or []],
            "source_currency": source_currency(design),
            "reproduce": "python3 tools/run_abi3_physical.py --view asap7 --top "
                         + str(design.get("top")) + " "
                         + " ".join(f"--source {s['path']}"
                                    for s in design.get("sources") or [])
                         + f" --clock-period-ns {body.get('target_clock_period_ns')}"
                           " --stages synth,sta --purpose characterization"
                           " --output <path>",
        })
    return out

def density(record: dict[str, Any], macs_per_cycle: int) -> dict[str, Any]:
    m = record["place_and_route"]["metrics"]
    d = record["design"]
    core_mm2 = float(m["core_area_um2"]) / 1e6
    cell_mm2 = float(m["standard_cell_area_um2"]) / 1e6
    macro_mm2 = float(m.get("macro_area_um2") or 0.0) / 1e6
    ops = macs_per_cycle * FLOPS_PER_MAC * float(m["fmax_hz"])
    return {
        "macs_per_cycle": macs_per_cycle,
        "post_route_fmax_hz": float(m["fmax_hz"]),
        "peak_bf16_ops_s": ops,
        "core_area_mm2": core_mm2,
        "standard_cell_area_mm2": cell_mm2,
        "macro_area_mm2": macro_mm2,
        "occupied_area_mm2": cell_mm2 + macro_mm2,
        "utilization_fraction": m.get("utilization_fraction"),
        "area_basis": "place_and_route.metrics.core_area_um2 (the placed core, "
                      "not cell area: cell area ignores the utilisation a real "
                      "floorplan must leave, and excludes SRAM macros entirely)",
        "ops_s_per_mm2_core": ops / core_mm2,
        "ops_s_per_mm2_occupied": ops / (cell_mm2 + macro_mm2),
        "closed": d.get("closed"),
        "acceptance_status": record.get("acceptance", {}).get("status"),
        "acceptance_reason": record.get("acceptance", {}).get("reason"),
        "signal_integrity_violations": d.get("signal_integrity_violations"),
        "power_total_w_default_activity": m.get("power_total_w"),
    }


def chip_level() -> dict[str, Any]:
    """Delegate L3 to the existing chip assembler rather than re-deriving it."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "chip.json"
        proc = subprocess.run(
            ["python3", str(CHIP_AUDIT), "--output", str(out)],
            cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not out.exists():
            raise SystemExit(f"chip audit failed: {proc.stderr[-2000:]}")
        return json.loads(out.read_text())


def control_starvation(comp_fmax_hz: float) -> dict[str, Any]:
    """How much of the peak survives the control plane's measured issue rate."""
    ctrl = json.loads(CONTROL_RECORD.read_text())
    rec = ctrl["records"][0]
    cycles = int(rec["cost"]["simulated_cycles"])
    commands = int(rec["issue_census"]["instances"])
    per_cmd = cycles / commands

    seq_full = load("results/physical_abi3/asap7/a3_microsequencer/pnr.json")
    seq_front = load(
        "results/physical_abi3/asap7/a3_microsequencer/pnr_frontend_only.json")

    def seq(body: dict, label: str) -> dict[str, Any]:
        m = body["place_and_route"]["metrics"]
        f = float(m["fmax_hz"])
        interval = per_cmd * comp_fmax_hz / f
        return {
            "variant": label,
            "modules": [s["path"].split("/")[-1]
                        for s in body["design"]["sources"]],
            "module_count": len(body["design"]["sources"]),
            "post_route_fmax_hz": f,
            "standard_cell_count": m.get("standard_cell_count"),
            "core_area_um2": m.get("core_area_um2"),
            "closed": body["design"].get("closed"),
            "signal_integrity_violations":
                body["design"].get("signal_integrity_violations"),
            "descriptor_interval_datapath_cycles": interval,
        }

    return {
        "control_cost": {
            "record": str(CONTROL_RECORD.relative_to(ROOT)),
            "rung": ctrl.get("rung"),
            "rung_status": ctrl.get("status"),
            "evidence_class": "cycle-accurate RTL run of the shipped program "
                              "through the real control plane, checked against "
                              "an independent Python golden model",
            "simulated_cycles": cycles,
            "engine_commands": commands,
            "control_cycles_per_command": per_cmd,
        },
        "datapath_clock_hz": comp_fmax_hz,
        "sequencer_variants": [seq(seq_full, "full_12_module"),
                               seq(seq_front, "frontend_only_7_module")],
        "descriptor_work_datapath_cycles": {
            "value": 270,
            "kernel_depth_k": 256,
            "basis": "measured by rtl/test/tb_kernel_dispatch_throughput.sv on "
                     "the real ot_kernel_dispatcher driving the real "
                     "ot_compute_unit; busy/kernel printed as 270.0 at K=256, "
                     "which is K plus 14 cycles of pipeline fill and drain",
            "measured_with": "Verilator 5.050 "
                             "($HOME/.local/opentallas-tools/verilator-5.050)",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--utilisation-sweep", type=Path, required=True,
                    help="JSON produced from the measured "
                         "tb_kernel_dispatch_throughput sweep")
    ap.add_argument("--control-module-record", type=Path, action="append",
                    default=[],
                    help="a synth+sta record for one control-plane module, used "
                         "to attribute the control plane's non-closure")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    ref = comparator()
    inv = routed_inventory()
    sweep = json.loads(args.utilisation_sweep.read_text())

    # ---- L1: the MAC array alone -------------------------------------------
    tile = load("results/physical_abi3/asap7/mac_tile/pnr_lanes16.json")
    tile_lanes = int(tile["design"]["parameters"]["LANES"])
    l1 = density(tile, tile_lanes)
    l1_variants = []
    for rel, pattern, src in (
        ("results/physical_abi3/asap7/mac_lanes/lane_bf16.json",
         None, None),
        ("results/physical_abi3/asap7/mac_lanes/lane_bf16_packed8.json",
         r"\.PACK\((\d+)\)", "rtl/abi3/ot_probe_packed8_bf16.sv"),
    ):
        rec = load(rel)
        if pattern:
            n = derived_lane_count(src, pattern, rec)
            macs = n["value"]
            basis = n
        else:
            macs = 1
            basis = {"value": 1, "source": "rtl/abi3/ot_probe_lane_bf16.sv",
                     "pattern": "one ot_mac_lane_fmt instance, one MAC per cycle",
                     "source_matches_record": True}
        v = density(rec, macs)
        v["record"] = rel
        v["macs_per_cycle_basis"] = basis
        v["source_currency"] = source_currency(rec["design"])
        l1_variants.append(v)

    # ---- L2: the compute unit ----------------------------------------------
    cu = load("results/physical_abi3/asap7/compute_unit/pnr.json")
    cu_lanes = derived_lane_count("rtl/proto/ot_compute_unit.sv",
                                  r"parameter integer LANES\s*=\s*(\d+)", cu)
    l2 = density(cu, cu_lanes["value"])

    # ---- L3: the assembled chip --------------------------------------------
    chip = chip_level()

    # ---- operand-delivery attribution, two independent subtractions ---------
    lane = load("results/physical_abi3/asap7/mac_lanes/lane_bf16.json")
    lane_p = float(lane["place_and_route"]["metrics"]["power_total_w"])
    tile_p = float(tile["place_and_route"]["metrics"]["power_total_w"])
    cu_p = float(cu["place_and_route"]["metrics"]["power_total_w"])
    cu_cell = float(cu["place_and_route"]["metrics"]["standard_cell_area_um2"])
    cu_macro = float(cu["place_and_route"]["metrics"]["macro_area_um2"])
    tile_cell = float(tile["place_and_route"]["metrics"]["standard_cell_area_um2"])

    attribution = {
        "question": "inside one compute unit, how much is arithmetic and how "
                    "much is getting operands to it?",
        "power_by_lane_probe_subtraction": {
            "compute_unit_w": cu_p,
            "arithmetic_w": cu_lanes["value"] * lane_p,
            "operand_delivery_w": cu_p - cu_lanes["value"] * lane_p,
            "operand_delivery_fraction":
                (cu_p - cu_lanes["value"] * lane_p) / cu_p,
            "basis": f"{cu_lanes['value']} x ot_probe_lane_bf16 at "
                     f"{lane['place_and_route']['metrics']['fmax_hz']/1e6:.0f} MHz "
                     f"subtracted from ot_compute_unit at "
                     f"{cu['place_and_route']['metrics']['fmax_hz']/1e6:.0f} MHz",
            "caveat": "the lane probe wraps ot_mac_lane_fmt while the tile "
                      "instantiates ot_mac_lane, and the two records were routed "
                      "at different clocks, so this is a cross-record "
                      "subtraction rather than a hierarchical power report",
        },
        "power_by_tile_subtraction": {
            "compute_unit_w": cu_p,
            "arithmetic_w": tile_p,
            "operand_delivery_w": cu_p - tile_p,
            "operand_delivery_fraction": (cu_p - tile_p) / cu_p,
            "basis": "the routed 16-lane ot_mac_tile's own power subtracted "
                     "from the routed compute unit's",
            "caveat": "the tile was routed at a LOWER clock "
                      f"({tile['place_and_route']['metrics']['fmax_hz']/1e6:.0f} "
                      "MHz) than the unit, so its power is understated and this "
                      "figure OVERSTATES the delivery share",
        },
        "area_by_tile_subtraction": {
            "compute_unit_occupied_um2": cu_cell + cu_macro,
            "compute_unit_standard_cell_um2": cu_cell,
            "compute_unit_macro_um2": cu_macro,
            "compute_unit_macro_count":
                cu["place_and_route"]["metrics"]["macro_count"],
            "array_standard_cell_um2": tile_cell,
            "operand_delivery_um2": cu_cell + cu_macro - tile_cell,
            "operand_delivery_fraction":
                (cu_cell + cu_macro - tile_cell) / (cu_cell + cu_macro),
            "basis": "occupied area is standard cells plus SRAM macros, which "
                     "is what the utilisation fraction is computed over; the "
                     "16-lane tile's own routed cell area is the arithmetic term",
        },
        "weight_reuse": {
            "weight_bits_per_sram_word": 16 * cu_lanes["value"],
            "macs_per_weight_sram_read": cu_lanes["value"],
            "basis": "rtl/proto/ot_compute_unit.sv: WGT_BITS = 16 * LANES, one "
                     "SRAM word read per K column, one column consumed per "
                     "cycle by LANES lanes",
        },
    }

    # ---- the three ratios ---------------------------------------------------
    levels = [
        {
            "level": "L1_array_level",
            "what_is_in": "ot_mac_tile: 16 MAC lanes, the operand broadcast "
                          "tree, the accumulators and the exponent-window logic",
            "what_is_out": "all operand storage, all control, everything else",
            "record": "results/physical_abi3/asap7/mac_tile/pnr_lanes16.json",
            "macs_per_cycle_basis": {
                "value": tile_lanes,
                "source": "the record's own design.parameters.LANES",
            },
            "measurement": l1,
            "source_currency": source_currency(tile["design"]),
            "ours_ops_s_per_mm2": l1["ops_s_per_mm2_core"],
            "comparator_level": "a100_logic_level",
            "comparator_ops_s_per_mm2": ref["logic_level_ops_s_per_mm2"],
            "ratio": l1["ops_s_per_mm2_core"] / ref["logic_level_ops_s_per_mm2"],
            "evidence_class": "ROUTED, NOT CLOSED",
            "closure_note":
                "post-route setup and hold met with zero DRC and zero antenna "
                "violations, but the routed netlist carries 13 max-slew "
                "violations and the pre-layout STA leg did not meet, so the "
                "record's own verdict is not_met and closed is false. The "
                "closed variants below bracket it.",
            "closed_variants": l1_variants,
        },
        {
            "level": "L2_unit_level",
            "what_is_in": "ot_compute_unit: the same 16-lane array plus two "
                          "ganged fakeram_256x128 weight macros, the activation "
                          "register file, the K-walking sequencer and the "
                          "interconnect between them",
            "what_is_out": "vector and reduction engines, the cluster "
                           "dispatcher, the microsequencer, KV cache, activation "
                           "buffer, HBM PHY, clock and power distribution, pads",
            "record": "results/physical_abi3/asap7/compute_unit/pnr.json",
            "macs_per_cycle_basis": cu_lanes,
            "measurement": l2,
            "source_currency": source_currency(cu["design"]),
            "ours_ops_s_per_mm2": l2["ops_s_per_mm2_core"],
            "comparator_level": "a100_logic_level",
            "comparator_ops_s_per_mm2": ref["logic_level_ops_s_per_mm2"],
            "ratio": l2["ops_s_per_mm2_core"] / ref["logic_level_ops_s_per_mm2"],
            "evidence_class": "ROUTED AND CLOSED",
            "closure_note":
                "setup and hold met, zero violating paths, zero DRC, zero "
                "antenna, zero max-slew/cap/fanout violations at a 0.8 ns target",
        },
        {
            "level": "L3_device_level",
            "what_is_in": "every capability's declared engine counts, "
                          "instantiated out of routed blocks: tensor compute "
                          "units with their weight SRAM, vector units, reduction "
                          "endpoints, cluster dispatchers and the microsequencer",
            "what_is_out": list(chip["area_excludes"]),
            "record": "tools/audit_chip_level_density.py (delegated)",
            "comparator_level": "a100_device_level",
            "comparator_ops_s_per_mm2": ref["device_level_ops_s_per_mm2"],
            "evidence_class": "ROUTED; one instantiated block NOT CLOSED",
            "closure_note":
                "every datapath block is routed and closed; the microsequencer "
                "instance is the full 12-module control plane, which is routed "
                "but NOT closed -- 3,204 max-slew and 3 max-cap violations in "
                "the routed netlist. It is 17.5% of a 256-lane chip's area and "
                "0.7% of an 8,192-lane chip's, and the closed alternative is a "
                "7-module frontend-only subset that omits the shared divider, "
                "symbol file, resolver bank, issue-record store and dependence "
                "table, so using it would understate the area.",
            "per_capability": [
                {
                    "capability": c["capability"],
                    "tensor_lanes": c["tensor_lanes"],
                    "chip_area_mm2": c["chip_area_mm2"],
                    "datapath_clock_hz": c["datapath_clock_hz"],
                    "datapath_clock_binding_block":
                        c["datapath_clock_binding_block"],
                    "peak_bf16_ops_s": c["bf16_ops_s"],
                    "ours_ops_s_per_mm2": c["device_level_ops_s_per_mm2"],
                    "ratio": (c["device_level_ops_s_per_mm2"]
                              / ref["device_level_ops_s_per_mm2"]),
                    "chip_power_w_default_activity": c["chip_power_w"],
                    "ops_s_per_w": c["ops_s_per_w"],
                    "energy_ratio_vs_a100": (c["ops_s_per_w"]
                                             / ref["ops_s_per_w"]),
                    "components": [
                        {"name": p["name"], "instances": p["instances"],
                         "record": p["record"], "closed": p["closed"],
                         "post_route_fmax_hz": p["fmax_hz"],
                         "core_area_um2_each": p["core_area_um2"],
                         "area_um2_total": p["area_um2_total"],
                         "area_share": p["area_um2_total"]
                                       / (c["chip_area_mm2"] * 1e6)}
                        for p in c["components"]
                    ],
                }
                for c in chip["chips"]
            ],
        },
    ]
    l3_ratios = [c["ratio"] for c in levels[2]["per_capability"]]
    levels[2]["ratio_min"] = min(l3_ratios)
    levels[2]["ratio_max"] = max(l3_ratios)
    levels[2]["ratio"] = min(l3_ratios)
    levels[2]["ratio_basis"] = ("the WORST capability, so the headline is not " 
                                "carried by the most favourable configuration")
    levels[2]["ours_ops_s_per_mm2"] = min(
        c["ours_ops_s_per_mm2"] for c in levels[2]["per_capability"])

    starve = control_starvation(l2["post_route_fmax_hz"])
    full = next(s for s in starve["sequencer_variants"]
                if s["variant"] == "full_12_module")
    front = next(s for s in starve["sequencer_variants"]
                 if s["variant"] == "frontend_only_7_module")

    def util_at(interval: float) -> dict[str, Any] | None:
        pts = [p for p in sweep["points"] if p.get("burst") in (None, 1)]
        best = min(pts, key=lambda p: abs(p["interval"] - interval))
        return best

    u_full = util_at(full["descriptor_interval_datapath_cycles"])
    u_front = util_at(front["descriptor_interval_datapath_cycles"])

    sustained = {
        "question": "how much of the peak survives the control plane's own "
                    "measured issue rate?",
        "control": starve,
        "measured_utilisation_sweep": sweep,
        "with_full_control_plane": {
            "descriptor_interval_datapath_cycles":
                full["descriptor_interval_datapath_cycles"],
            "nearest_measured_point": u_full,
            "array_utilisation": u_full["util_percent"] / 100.0,
        },
        "with_frontend_only_control_plane": {
            "descriptor_interval_datapath_cycles":
                front["descriptor_interval_datapath_cycles"],
            "nearest_measured_point": u_front,
            "array_utilisation": u_front["util_percent"] / 100.0,
        },
        "sustained_L3_ratio_min": levels[2]["ratio_min"]
                                  * u_full["util_percent"] / 100.0,
        "sustained_L3_ratio_max": levels[2]["ratio_max"]
                                  * u_full["util_percent"] / 100.0,
        "de_rating_is_reported_not_folded_in":
            "the three headline ratios above are PEAK. This block says what the "
            "measured control plane does to them. It is not folded into the "
            "headline because a de-rated peak is still not a workload "
            "measurement, and because the de-rating is a property of the "
            "control plane's closure rather than of the datapath's area.",
    }

    # Upper bound on what killing operand-delivery power alone could buy:
    # the whole chip's watts minus every compute unit's delivery share.
    _c0 = levels[2]["per_capability"][0]
    _cu_instances = next(p["instances"] for p in _c0["components"]
                         if p["name"] == "tensor_compute_unit")
    _delivery_w = (attribution["power_by_lane_probe_subtraction"]
                   ["operand_delivery_w"]) * _cu_instances
    _floor_w = _c0["chip_power_w_default_activity"] - _delivery_w
    _delivery_free_energy_ratio = (_c0["peak_bf16_ops_s"] / _floor_w
                                   / ref["ops_s_per_w"])

    mods = prelayout_modules(args.control_module_record)
    by_top = {m["top"]: m for m in mods}
    table = by_top.get("ot_a3_dependence_table")

    cell_delta = (full["standard_cell_count"] - front["standard_cell_count"])
    leverage = {
        "claim": "pipeline (or bound) the dependence table's single-cycle "
                 "128-range conflict check so the control plane's clock stops "
                 "being set by one combinational reduction.",
        "why_this_and_not_operand_delivery":
            "operand delivery is the larger share of POWER, but its measured "
            "ceiling is smaller and it costs area. Driving compute-unit operand "
            "delivery to zero watts would take the chip from "
            f"{levels[2]['per_capability'][0]['energy_ratio_vs_a100']:.3f}x to "
            "an upper bound of "
            f"{_delivery_free_energy_ratio:.3f}x of the A100 on ops per joule, "
            "so it cannot reach parity on its own, and a 16x-reuse array needs a "
            "larger weight SRAM per unit. Closing the control plane costs no "
            "datapath area at all and is worth 2.00x on the unit this audit "
            "measures.",
        "measurements": {
            "full_control_plane_post_route": {
                "fmax_hz": full["post_route_fmax_hz"],
                "standard_cell_count": full["standard_cell_count"],
                "core_area_um2": full["core_area_um2"],
                "closed": full["closed"],
                "signal_integrity_violations":
                    full["signal_integrity_violations"],
                "modules": full["modules"],
            },
            "frontend_only_control_plane_post_route": {
                "fmax_hz": front["post_route_fmax_hz"],
                "standard_cell_count": front["standard_cell_count"],
                "core_area_um2": front["core_area_um2"],
                "closed": front["closed"],
                "signal_integrity_violations":
                    front["signal_integrity_violations"],
                "modules": front["modules"],
            },
            "cell_count_added_by_the_five_omitted_modules": cell_delta,
            "dependence_table_prelayout": table,
            "dependence_table_share_of_added_cells":
                (table["standard_cell_count"] / cell_delta) if table else None,
            "utilisation_at_full_control_plane": u_full,
            "utilisation_at_frontend_only_clock": u_front,
            "burst_does_not_help": [p for p in sweep["points"]
                                    if (p.get("burst") or 1) > 1],
        },
        "sizing": {
            "sustained_throughput_gain":
                (u_front["util_percent"] / u_full["util_percent"]),
            "sustained_L3_ratio_now": sustained["sustained_L3_ratio_min"],
            "sustained_L3_ratio_after":
                levels[2]["ratio_min"] * u_front["util_percent"] / 100.0,
            "datapath_area_cost_mm2": 0.0,
            "control_area_cost":
                "pipelining a combinational reduction adds pipeline registers "
                "to a block that is 17.5% of a 256-lane chip and 0.7% of an "
                "8,192-lane one. NOT MEASURED: no routed record exists for a "
                "pipelined table, and this audit does not model one.",
        },
        "what_would_settle_it":
            "place-and-route the full 12-module control plane at HEAD with the "
            "dependence table's check path split across 2 to 4 cycles, and show "
            "a closed record at or above 534 MHz with zero max-slew violations. "
            "Until that record exists, the 2.00x is a sizing from two measured "
            "endpoints, not a result.",
        "refusals": [
            "the-two-frequency-measurements-do-not-reconcile: the dependence "
            "table alone reports a 16.10 ns PRE-LAYOUT critical path (62.1 MHz) "
            "while the full control plane containing it reports 264.8 MHz "
            "POST-ROUTE. Both are recorded above. They are not reconciled here, "
            "and the sequencer record is the weaker of the two: it is NOT closed "
            "(3,204 max-slew and 3 max-cap violations, so its delay calculation "
            "runs on badly driven nets) and 7 of its 12 sources have drifted "
            "since it was routed. Resolving this needs a fresh routed record of "
            "the full control plane at HEAD, which was not run because the "
            "machine was already saturated with place-and-route jobs.",
            "the-sizing-is-not-a-result: 2.00x is the ratio of two MEASURED "
            "utilisation points, one at each of two MEASURED sequencer clocks. "
            "No design change was made and no record exists for a pipelined "
            "dependence table.",
        ],
    }

    body = {
        "schema": "opentallas.audit.abi3_iso_area_three_level.v1",
        "question": ("At three matched levels of inclusion, how does this "
                     "design's BF16 throughput per mm2 on ASAP7 compare with "
                     "the A100 on TSMC N7?"),
        "unit": "ops_s_per_mm2, BF16 dense, one MAC counted as two operations",
        "git": git_state(),
        "snapshot_taken_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
        "comparator": ref,
        "levels": levels,
        "headline": {
            "L1_array_level_vs_a100_logic": levels[0]["ratio"],
            "L2_unit_level_vs_a100_logic": levels[1]["ratio"],
            "L3_device_level_vs_a100_device": levels[2]["ratio"],
            "refusal": "there is no single ratio. The three levels answer "
                       "different questions and collapsing them is the failure "
                       "mode this audit exists to prevent.",
        },
        "sustained": sustained,
        "attribution": attribution,
        "control_plane_module_characterization": mods,
        "control_plane_module_characterization_note":
            "PRE-LAYOUT synth+STA only. These attribute the full control "
            "plane's non-closure to a structure; they are never mixed into a "
            "density and must not be compared with any post-route fmax here.",
        "highest_leverage_change": leverage,
        "operand_delivery_energy_ceiling": {
            "chip": _c0["capability"],
            "chip_power_w_default_activity":
                _c0["chip_power_w_default_activity"],
            "compute_unit_instances": _cu_instances,
            "operand_delivery_w_total": _delivery_w,
            "power_floor_if_delivery_were_free_w": _floor_w,
            "energy_ratio_now": _c0["energy_ratio_vs_a100"],
            "energy_ratio_if_delivery_were_free": _delivery_free_energy_ratio,
            "conclusion": "even at zero operand-delivery power the chip does "
                          "not reach the A100's ops per joule, so operand "
                          "delivery is necessary but not sufficient for the "
                          "energy gap.",
        },
        "routed_inventory": inv,
        "routed_inventory_note":
            "every asap7 record whose acceptance block carries a "
            f"place_and_route check with scope {POST_ROUTE_SCOPE!r}. Records "
            "with only synth and sta stages are EXCLUDED: a pre-layout setup "
            "report is not a routed one, and this repository has recorded a "
            "pre-layout 8,691 MHz against a post-route 4,092 MHz on the same "
            "block, 2.12x optimistic.",
        "refusals": [
            "no-single-headline-ratio: three levels of inclusion are reported "
            "and they are not collapsed. L1 has no operand storage and is an "
            "upper bound; L2 has no vector, reduction or control; only L3 "
            "charges both sides for a product.",
            "asap7-is-not-tsmc-n7: the comparator is fabricated silicon on a "
            "foundry node. This design is on ASAP7, a predictive and explicitly "
            "NON-MANUFACTURABLE academic PDK, and a foundry N7 PDK is not "
            "obtainable to close the gap. The node family matches; the "
            "confidence does not.",
            "peak-arithmetic-only: all three densities are lanes x 2 x clock. "
            "The sustained block measures that the array is starved for about "
            "half its cycles at the full control plane's own issue rate, and "
            "that de-rating is NOT included in the three headline ratios.",
            "L1-is-routed-but-not-closed: the 16-lane array record's verdict is "
            "not_met -- 13 max-slew violations and a failed pre-layout STA leg. "
            "It is reported because it is the array the chip actually "
            "instantiates, with its closure state stated and closed variants "
            "beside it. It must not be quoted as a closed result.",
            "L3-instantiates-one-non-closed-block: the full 12-module "
            "microsequencer is routed but not closed (3,204 max-slew, 3 "
            "max-cap). The closed alternative is a frontend-only subset, so "
            "substituting it would understate area rather than fix the gap.",
            "area-inclusion-is-incomplete-even-at-L3: the summed chip area omits "
            "KV-cache SRAM, a global activation buffer, HBM PHY and controller, "
            "the mask-ROM array itself, clock and power distribution and the pad "
            "ring. Every one is real silicon, so L3 OVERSTATES a finished part.",
            "low-utilisation-floorplans: the routed blocks sit at 32-38% core "
            "utilisation where a production floorplan targets 70-80%. Core area "
            "is used as the denominator anyway, because cell area excludes the "
            "SRAM macros and ignores the space a real floorplan must leave. "
            "This makes the three ratios conservative by roughly the ratio of "
            "those utilisations, and that correction is NOT applied.",
            "power-is-a-default-activity-estimate: every watt here is ORFS "
            "power on the routed netlist under the flow's default switching "
            "activity, not a workload trace. A MAC array under a dense GEMM "
            "switches far more, so these watts are an OPTIMISTIC lower bound "
            "and the energy ratios are upper bounds on this design's standing.",
            "energy-comparison-is-against-a-tdp: the A100 figure is 312 TFLOP/s "
            "inside a 400 W package that includes HBM, PHY and everything the "
            "area list excludes. The two sides are not charged for the same "
            "components on the power axis any more than on the area axis.",
            "attribution-is-a-cross-record-subtraction: the operand-delivery "
            "split comes from subtracting one routed record from another, not "
            "from a hierarchical power report. Two independent subtractions are "
            "given and they bracket the answer; neither is a per-instance "
            "measurement.",
            "no-thermal-ir-drop-or-yield-analysis: nothing here checks power "
            "density, IR drop, thermal feasibility or defect tolerance, all of "
            "which bound a real part.",
            "worktree-was-dirty-and-orfs-was-running: this artifact was written "
            "while place-and-route jobs for five V4.1 blocks were in flight and "
            "rewriting their own records. Those five blocks contribute no FLOPs "
            "to any level here, but the inventory is a SNAPSHOT and the dirty "
            "path list is recorded so it can be re-derived.",
        ],
    }

    print(f"comparator: {ref['part']} on {ref['process']}, "
          f"{ref['bf16_dense_ops_s']/1e12:.0f} TFLOP/s over "
          f"{ref['die_area_mm2']:.0f} mm2")
    print(f"  logic level  {ref['logic_level_ops_s_per_mm2']/1e12:.3f} "
          f"TFLOP/s per mm2  (die x {ref['logic_area_fraction']})")
    print(f"  device level {ref['device_level_ops_s_per_mm2']/1e12:.3f} "
          f"TFLOP/s per mm2\n")
    print(f"  {'level':<18} {'ours T/s/mm2':>13} {'vs':>22} {'ratio':>7}  class")
    for lv in levels:
        print(f"  {lv['level']:<18} {lv['ours_ops_s_per_mm2']/1e12:>13.3f} "
              f"{lv['comparator_level']:>22} {lv['ratio']:>6.2f}x  "
              f"{lv['evidence_class']}")
    print(f"\nL3 spans {levels[2]['ratio_min']:.2f}x to "
          f"{levels[2]['ratio_max']:.2f}x across "
          f"{len(levels[2]['per_capability'])} capabilities; the headline is the "
          f"worst.")
    print(f"\nSUSTAINED, not folded into the above: the full control plane "
          f"issues one descriptor\n  every "
          f"{full['descriptor_interval_datapath_cycles']:.0f} datapath cycles "
          f"against {starve['descriptor_work_datapath_cycles']['value']} cycles "
          f"of work per descriptor,\n  and the measured array utilisation there "
          f"is {u_full['util_percent']:.1f}%. That puts sustained L3 at "
          f"{sustained['sustained_L3_ratio_min']:.2f}x-"
          f"{sustained['sustained_L3_ratio_max']:.2f}x.")
    print(f"  The frontend-only sequencer closes at "
          f"{front['post_route_fmax_hz']/1e6:.0f} MHz, which is one descriptor "
          f"every\n  {front['descriptor_interval_datapath_cycles']:.0f} cycles "
          f"and {u_front['util_percent']:.1f}% measured utilisation.")
    a = attribution
    print(f"\nATTRIBUTION inside one compute unit:")
    print(f"  operand delivery is "
          f"{a['power_by_lane_probe_subtraction']['operand_delivery_fraction']*100:.1f}% "
          f"of power by lane subtraction, "
          f"{a['power_by_tile_subtraction']['operand_delivery_fraction']*100:.1f}% "
          f"by tile subtraction,")
    print(f"  and {a['area_by_tile_subtraction']['operand_delivery_fraction']*100:.1f}% "
          f"of occupied area. Weight reuse is "
          f"{a['weight_reuse']['macs_per_weight_sram_read']} MACs per SRAM read.")
    print(f"  Even at ZERO delivery power the chip reaches only "
          f"{_delivery_free_energy_ratio:.2f}x the A100 on ops per joule "
          f"(now {_c0['energy_ratio_vs_a100']:.2f}x),")
    print(f"  so operand delivery is necessary but NOT sufficient for the "
          f"energy gap.")
    if table:
        print(f"\nHIGHEST LEVERAGE (sized, not implemented): the dependence "
              f"table is {table['standard_cell_count']:,} cells "
              f"({table['combinational_cell_count']:,} combinational)")
        print(f"  with a {table['prelayout_critical_path_ns']:.2f} ns PRE-LAYOUT "
              f"critical path, {leverage['measurements']['dependence_table_share_of_added_cells']*100:.1f}% of the "
              f"{cell_delta:,} cells the five omitted")
        print(f"  control modules add. Closing the control plane at the "
              f"frontend's {front['post_route_fmax_hz']/1e6:.0f} MHz is worth "
              f"{leverage['sizing']['sustained_throughput_gain']:.2f}x sustained,")
        print(f"  sustained L3 "
              f"{leverage['sizing']['sustained_L3_ratio_now']:.2f}x -> "
              f"{leverage['sizing']['sustained_L3_ratio_after']:.2f}x, at zero "
              f"datapath area. Bursting descriptors does NOT help: "
              f"{max(p['util_percent'] for p in leverage['measurements']['burst_does_not_help']):.1f}% at burst=8.")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        try:
            shown = args.output.relative_to(ROOT)
        except ValueError:
            shown = args.output
        print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
