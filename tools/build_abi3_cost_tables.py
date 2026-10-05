#!/usr/bin/env python3
"""Derive the characterized ABI 3.0 cost tables from the physical evidence.

W9.5 is the step that feeds characterized capability back into the cycle model.
Doing that by editing JSON by hand puts a quotient in a table whose derivation
lives only in a note, which is the shape ``docs/METHODOLOGY.md`` section 0
forbids.  So the derived tables are *generated* from the artifacts that measure
them, and ``--check`` fails when a generated table has drifted from the
evidence.  The base table supplies structure; this tool replaces only the
parameters some run on disk actually measured, and states, for each one, the
file and field it came from and the arithmetic that produced it.

Two kinds of value are derived.

``clock.frequency_hz`` -- only for a view where a block of this machine has
actually been routed
    the minimum post-route fmax over the blocks routed in that PDK view *that
    implement a modelled engine family*.  A core clock is bounded by the
    slowest block that has to run at it; taking the minimum over a wider set
    (an exploration point that the machine does not instantiate) would import a
    design-space probe into the machine definition, and taking a maximum would
    be a claim no run supports.  Which families still have no routed block at
    all is recorded on the parameter, because that is the direction the number
    can still move.  The cluster and wafer views get no clock from here at all:
    nothing of those machines has been routed, and borrowing a single chip's
    frequency for them would be exactly the view-mixing ADR-003 section 3.5
    forbids, with the label filed off.

``engine.{tensor,vector,reduction}.work_per_lane_cycle``
    measured work over measured cycles for one engine instance, from the
    dual-simulator RTL campaigns and from the dedicated engine-rate bench.  The
    table keeps both operands and the cycle model does the division
    (``convert: work_over_cycles``), so a reader can check the rate against the
    campaign without trusting this tool.  A rate is the RTL's own cycle
    behaviour and does not depend on the node, so every view gets it.

Usage::

    PYTHONPATH=. python3 tools/build_abi3_cost_tables.py
    PYTHONPATH=. python3 tools/build_abi3_cost_tables.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.cycle.machine import COST_TABLE_SCHEMA  # noqa: E402

HARDWARE = REPO / "configs" / "hardware"

#: A routed block, the engine family it implements, and where its fmax lives.
#: ``family`` is ``None`` for a block that is a proxy or an exploration point
#: rather than an engine the modelled machine instantiates; such a block is
#: reported but never allowed to set the core clock.
ROUTED_BLOCKS: tuple[dict[str, Any], ...] = (
    {
        "view": "asap7",
        "block": "add_bf16_sram_engine",
        "family": None,
        "path": "results/physical_abi3/asap7/add_bf16_sram_engine/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
        "note": (
            "SUPERSEDED as the vector engine by ot_vector_add_unit.  This block "
            "retires ONE element per cycle through a combinational BF16 adder "
            "whose normalise step is a ten-deep cascade of conditional shifts, "
            "and closes at 239 MHz.  Reported because it was routed; excluded "
            "because the machine no longer instantiates it"
        ),
    },
    {
        "view": "asap7",
        "block": "vector_add_unit",
        "family": "vector",
        "path": "results/physical_abi3/asap7/vector_add_unit/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
        "note": (
            "eight lanes of five-stage pipelined BF16 add under one issue port, "
            "credit-based flow control so no datapath register carries an enable"
        ),
    },
    {
        "view": "asap7",
        "block": "matmul_bf16_sram_engine",
        "family": None,
        "path": "results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
        "note": (
            "SUPERSEDED as the tensor engine by ot_compute_unit.  This block is "
            "an unpipelined datapath: its multiply-accumulate is combinational "
            "from operand to accumulator, so its cycle time is a whole "
            "multiply-add and it closes at 58 MHz.  It set this view's core "
            "clock, and therefore the whole cycle model, to that figure.  It is "
            "reported here because it was routed and the number is real, and it "
            "is excluded because the machine no longer instantiates it"
        ),
    },
    {
        "view": "asap7",
        "block": "compute_unit",
        "family": "tensor",
        "path": "results/physical_abi3/asap7/compute_unit/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
        "note": (
            "16-lane block-floating-point MAC tile with its weight SRAM, "
            "activation register file and sequencer, fully pipelined"
        ),
    },
    {
        "view": "asap7",
        "block": "reduction_s8_g2",
        "family": "reduction",
        "path": "results/physical_abi3/asap7/reduction_s8_g2/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
    },
    {
        "view": "asap7",
        "block": "numeric_e1_l16_tc",
        "family": None,
        "path": "results/asap7_physical/physical.json",
        "field": "cases.numeric_e1_l16_tc.metrics.fmax_hz",
        "note": (
            "signed integer-DV dot product; the campaign's own claim boundary "
            "says it is not an MXFP4/FP8/BF16 datapath, so it is a proxy and "
            "not the tensor engine this machine instantiates"
        ),
    },
    {
        "view": "asap7",
        "block": "numeric_e4_l16_tc",
        "family": None,
        "path": "results/asap7_physical/physical.json",
        "field": "cases.numeric_e4_l16_tc.metrics.fmax_hz",
        "note": "four-expert width-scaling exploration point, not an instantiated engine",
    },
    {
        "view": "sky130",
        "block": "add_bf16_sram_engine",
        "family": None,
        "path": "results/physical_abi3/sky130hd/add_bf16_sram_engine/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
        "note": (
            "SUPERSEDED as the vector engine by ot_vector_add_unit, on this view "
            "as well as on asap7.  One element per cycle through a combinational "
            "BF16 adder, 38.8 MHz.  Reported because it was routed; excluded "
            "because the machine no longer instantiates it"
        ),
    },
    {
        "view": "sky130",
        "block": "vector_add_unit",
        "family": "vector",
        "path": "results/physical_abi3/sky130hd/vector_add_unit/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
        "note": (
            "the same RTL routed on asap7 and on sky130, so this view's vector "
            "engine is the redesigned one on both nodes rather than only on the "
            "predictive PDK"
        ),
    },
    {
        "view": "sky130",
        "block": "reduction_s8_g2",
        "family": "reduction",
        "path": "results/physical_abi3/sky130hd/reduction_s8_g2/pnr.json",
        "field": "place_and_route.metrics.fmax_hz",
    },
    {
        "view": "ihp_sg13g2",
        "block": "add_bf16_sram_engine",
        "family": "vector",
        "path": "results/tensor_accelerator/qwen3_rtl_ihp_sg13g2_physical_campaign.json",
        "field": "metrics.timing.aggregate_extracted.core_clock_fmax_hz",
    },
)

#: The five DeepSeek-V4.1-Flash engine blocks plan section 13 WP-J says this
#: tool "gains entries for ... once routed", with the family each implements and
#: where its routed record has to appear.  THEY ARE NOT IN ``ROUTED_BLOCKS`` AND
#: MUST NOT BE UNTIL THERE IS A POST-ROUTE NUMBER TO READ.
#:
#: Why a declaration instead of an entry:
#:
#: * An entry needs ``place_and_route.metrics.fmax_hz``.  What is on disk today
#:   is the in-flight ``physical.json`` of the characterization runs, and for
#:   three of the ten (view, block) pairs the only frequency in it is
#:   ``static_timing.fmax_hz``, labelled ``(pre-layout)`` by the campaign
#:   itself.  A pre-layout number in this table would be a synthesis estimate
#:   wearing a routed number's provenance -- and would set a CORE CLOCK, which
#:   every time in the cycle model then divides by.
#: * ``routed_clock`` takes the MINIMUM fmax over the routed blocks that
#:   implement a modelled family.  Four of these five blocks are the first
#:   routed blocks of the ``route`` and ``dma`` families, which
#:   ``engine_families_with_no_routed_block`` currently names as the reason the
#:   clock is an upper bound.  Adding them can therefore only LOWER the asap7
#:   and sky130 clocks, and by how much is a question only their own closure
#:   answers.  Guessing it would corrupt every table the program reads.
#:
#: So the tool declares what it is waiting for, reports the state of each on
#: every run, and says out loud when one becomes readable.  Plan section 4.6
#: names the records under ``a3_{fp4kv_dequant,block_max,candidate_mask,
#: ngram_hash,engram_gate}``; the campaign in flight writes them under the block
#: name instead, exactly as ``vector_add_unit`` and ``reduction_s8_g2`` above,
#: so both filenames are looked for and neither is invented.
PENDING_ROUTED_BLOCKS: tuple[dict[str, Any], ...] = tuple(
    {
        "view": view,
        "block": block,
        "family": family,
        "rtl": f"rtl/abi3/ot_a3_{block}.sv",
        "records": (
            f"results/physical_abi3/{directory}/{block}/pnr.json",
            f"results/physical_abi3/{directory}/{block}/physical.json",
        ),
        "field": "place_and_route.metrics.fmax_hz",
        "produced_by": (
            "plan section 13 WP-M (DS41-PHY10): tools/run_abi3_physical.py "
            f"--view {directory} --top ot_a3_{block}"
        ),
    }
    for view, directory in (("asap7", "asap7"), ("sky130", "sky130hd"))
    for block, family in (
        ("vector_fp4kv_dequant", "vector"),
        ("route_block_max", "route"),
        ("route_candidate_mask", "route"),
        ("dma_ngram_hash", "dma"),
        ("vector_engram_gate", "vector"),
    )
)


def pending_state(entry: dict[str, Any]) -> dict[str, Any]:
    """Is this pending block's routed fmax readable yet, and if not, why not?

    Reads whatever is on disk at the moment of the run: these records are
    produced by a campaign that may be running right now, so a state baked into
    this file would be wrong by the time anyone read it.
    """
    for relative in entry["records"]:
        path = REPO / relative
        if not path.exists():
            continue
        body = json.loads(path.read_text())
        pnr = body.get("place_and_route") or {}
        metrics = pnr.get("metrics") or {}
        fmax = metrics.get("fmax_hz")
        design = body.get("design") or {}
        detail = {
            "record": relative,
            "flow_completed": body.get("flow_completed"),
            "closed": design.get("closed"),
            "fmax_basis": design.get("fmax_basis"),
            "error": body.get("error"),
        }
        if fmax is None:
            detail["state"] = "no_post_route_fmax"
            detail["why"] = (
                f"{relative} carries no {entry['field']}; the only frequency in "
                f"it is {design.get('fmax_hz')!r} on basis "
                f"{design.get('fmax_basis')!r}"
            )
            return detail
        if not body.get("flow_completed"):
            detail["state"] = "flow_incomplete"
            detail["why"] = (
                f"{relative} has a {entry['field']} of {fmax!r} but "
                f"flow_completed is {body.get('flow_completed')!r}"
            )
            return detail
        # ``closed`` is the campaign's own stricter word: place-and-route ran
        # AND the routed netlist carries no max-slew, max-cap or max-fanout
        # violation.  ROUTED_BLOCKS' existing entries do not require it, so it
        # does not change the state here, but DS41-PHY10 does require it and a
        # reader must not have to open the record to find out.
        detail["state"] = "routed" if design.get("closed") else "routed_not_closed"
        detail["fmax_hz"] = fmax
        detail["why"] = (
            f"{relative}#{entry['field']} is {fmax!r}, the flow completed and "
            f"design.closed is {design.get('closed')!r}"
        )
        return detail
    return {
        "record": None,
        "state": "absent",
        "why": "neither " + " nor ".join(entry["records"]) + " exists",
    }


def pending_report() -> list[dict[str, Any]]:
    """Every pending block with the state of its record right now."""
    return [{**entry, **pending_state(entry)} for entry in PENDING_ROUTED_BLOCKS]


#: Engine families the cycle model times.  A family with no routed block is
#: named on the clock parameter, because it is the reason the clock can still
#: fall.
MODELLED_FAMILIES = (
    "dma",
    "tensor",
    "vector",
    "attention",
    "route",
    "reduction",
    "selection",
    "state",
    "link",
)

#: Measured (work, cycles) pairs from the executed dual-simulator campaigns.
#: ``reference`` is the simulator whose count the table carries; ``second`` is
#: the independent one, and the spread between them is recorded rather than
#: averaged away.
MEASURED_RATES: tuple[dict[str, Any], ...] = (
    {
        "parameter": "engine.tensor.work_per_lane_cycle",
        "path": "results/tensor_accelerator/qwen3_rtl_q_proj_campaign.json",
        "work_fields": ("matmul_multiply_count", "matmul_add_count"),
        "reference_case": "q_proj_iverilog",
        "second_case": "q_proj_verilator",
        "engine": "ot_ta_matmul_bf16_sram_engine",
        "replicated_by": (
            "results/tensor_accelerator/qwen3_rtl_kv_proj_campaign.json",
            "kv_proj_iverilog",
        ),
        "counters": "tensor.multiplications + tensor.additions",
    },
    {
        "parameter": "engine.vector.work_per_lane_cycle",
        "path": "results/tensor_accelerator/qwen3_rtl_head_rmsnorm_campaign.json",
        "work_fields": ("element_count",),
        "reference_case": "head_rmsnorm_iverilog",
        "second_case": "head_rmsnorm_verilator",
        "engine": "ot_ta_head_rmsnorm_bf16_sram_engine",
        "replicated_by": None,
        "cross_check": (
            "results/tensor_accelerator/qwen3_rtl_rope_campaign.json",
            "rope_iverilog",
            ("element_count",),
            "ot_ta_rope_bf16_sram_engine",
        ),
        "counters": "vector.elements",
    },
)

#: Rates measured by the dedicated two-simulator engine-rate campaign, which
#: reports its own work and cycle counts rather than leaving them to be dug out
#: of an operator campaign.
ENGINE_RATE_CAMPAIGN = "results/rtl/abi3_engine_rate.json"

ENGINE_RATE_CASES: tuple[dict[str, Any], ...] = (
    {
        "parameter": "engine.reduction.work_per_lane_cycle",
        "case": "reduction_endpoint_s8_g2",
    },
)


#: view -> (base table, output file, cost table id, description prefix)
DERIVED: dict[str, dict[str, str]] = {
    "asap7": {
        "base": "abi3_cost_asap7_v1.json",
        "out": "abi3_cost_asap7_v2.json",
        "cost_table_id": "abi3-cost-asap7-v2",
        "version": "2.0.0",
        "lineage": (
            "ASAP7 predictive-7nm view, v2.  Supersedes abi3-cost-asap7-v1: "
            "its clock came from the ot_numeric_dot proxy, and a routed "
            "engine of this machine has since closed slower on the same "
            "platform and corner.  ASAP7 is a predictive research PDK with no "
            "calibrated error bar against any foundry node, and ADR-003 "
            "section 3.5 forbids mixing it with the SKY130 view."
        ),
    },
    "sky130": {
        "base": "abi3_cost_sky130_rom_v1.json",
        "out": "abi3_cost_sky130_rom_v2.json",
        "cost_table_id": "abi3-cost-sky130-rom-v2",
        "version": "2.0.0",
        "lineage": (
            "SKY130 130 nm ROM view, v2.  Supersedes abi3-cost-sky130-rom-v1, "
            "whose 100 MHz clock was an assumption; a routed engine of this "
            "machine closes at 38.8 MHz on the same open foundry PDK.  The "
            "ROM read latency is still an ngspice measurement of a three-"
            "bitline slice, not a macro."
        ),
    },
    "ihp_sg13g2": {
        "base": "abi3_cost_baseline_v1.json",
        "out": "abi3_cost_ihp_sg13g2_v1.json",
        "cost_table_id": "abi3-cost-ihp-sg13g2-v1",
        "version": "1.0.0",
        "lineage": (
            "IHP SG13G2 130 nm open *foundry* view.  New: the repository had "
            "no cost table for the PDK docs/OPEN_PDK_SELECTION.md names as the "
            "independent replication vehicle, even though an engine of this "
            "machine has been routed in it.  Structure comes from the "
            "development baseline; only the clock is characterized."
        ),
    },
    # The engine rates are the RTL's own cycle behaviour and are the same
    # number at any node, so the cluster and wafer views get them too.  Their
    # clocks stay assumed, because no block of a multi-node or on-wafer machine
    # has been routed at all: a measured rate under an invented clock is still
    # an invented time, and the table has to keep saying so.
    "cluster32": {
        "base": "abi3_cost_cluster32_v1.json",
        "out": "abi3_cost_cluster32_v2.json",
        "cost_table_id": "abi3-cost-cluster32-v2",
        "version": "2.0.0",
        "routed_clock": False,
        "lineage": (
            "32-node conventional-chip cluster, v2.  Supersedes "
            "abi3-cost-cluster32-v1 in its engine rates only: the tensor, "
            "vector and reduction rates are measured, and every fabric "
            "parameter, the clock, and the whole memory hierarchy remain "
            "assumptions.  No link, switch or endpoint of this machine has "
            "been routed or simulated at cycle level."
        ),
    },
    "rom_array": {
        "base": "abi3_cost_rom_array_v1.json",
        "out": "abi3_cost_rom_array_v2.json",
        "cost_table_id": "abi3-cost-rom-array-v2",
        "version": "2.0.0",
        "routed_clock": False,
        "lineage": (
            "32-node reticle-class ROM array, v2.  Supersedes "
            "abi3-cost-rom-array-v1 in its engine rates only, exactly as the "
            "cluster table does: the tensor, vector and reduction rates are "
            "measured, and every fabric parameter, the clock, and the whole "
            "memory hierarchy remain assumptions.  The fabric section is the "
            "32-node HBM cluster's, on purpose."
        ),
    },
    "wafer": {
        "base": "abi3_cost_wafer_v1.json",
        "out": "abi3_cost_wafer_v2.json",
        "cost_table_id": "abi3-cost-wafer-v2",
        "version": "2.0.0",
        "routed_clock": False,
        "lineage": (
            "Wafer-scale logical device, v2.  Supersedes abi3-cost-wafer-v1 in "
            "its engine rates only.  The on-wafer mesh parameters are still "
            "the repository's own NoC estimates rather than post-layout "
            "timing, and the clock is still an assumption."
        ),
    },
}


def _dig(body: Any, dotted: str) -> Any:
    node = body
    for key in dotted.split("."):
        node = node[key]
    return node


def _case_cycles(body: dict[str, Any], name: str) -> int:
    for case in body["cases"]:
        if case["name"] == name:
            return int(case["observation"]["cycles"])
    raise KeyError(f"campaign has no case named {name!r}")


def routed_clock(view: str) -> dict[str, Any]:
    """The core clock this view's routed blocks permit, and why."""
    binding: list[dict[str, Any]] = []
    reported: list[dict[str, Any]] = []
    for entry in ROUTED_BLOCKS:
        if entry["view"] != view:
            continue
        body = json.loads((REPO / entry["path"]).read_text())
        fmax = float(_dig(body, entry["field"]))
        row = {
            "block": entry["block"],
            "family": entry["family"],
            "fmax_hz": fmax,
            "source": f"{entry['path']}#{entry['field']}",
            "note": entry.get("note", ""),
        }
        reported.append(row)
        if entry["family"] is not None:
            binding.append(row)
    if not binding:
        raise SystemExit(f"view {view!r} has no routed block for a modelled engine")
    slowest = min(binding, key=lambda row: row["fmax_hz"])
    covered = sorted({row["family"] for row in binding})
    uncovered = [f for f in MODELLED_FAMILIES if f not in covered]
    excluded = [row for row in reported if row["family"] is None]
    note_parts = [
        "minimum post-route fmax over the routed blocks that implement a "
        f"modelled engine family: "
        + ", ".join(
            f"{row['block']} ({row['family']}) {row['fmax_hz']:.6g} Hz"
            for row in sorted(binding, key=lambda r: r["fmax_hz"])
        )
        + ".",
    ]
    for row in excluded:
        note_parts.append(
            f"{row['block']} closes at {row['fmax_hz']:.6g} Hz and is excluded: "
            f"{row['note']}."
        )
    #: A view whose binding blocks are all newer than a superseded one is
    #: reporting a redesign, not a measurement error.  Say so, so that a reader
    #: comparing this table against an older one can see why the clock moved by
    #: more than an order of magnitude.
    if excluded and any("SUPERSEDED" in (row.get("note") or "") for row in excluded):
        note_parts.append(
            "The excluded blocks marked SUPERSEDED were the previous "
            "implementations of engine families that have since been redesigned; "
            "this view's clock moved because the design changed, not because the "
            "same design was re-measured."
        )
    if uncovered:
        note_parts.append(
            "No block has been routed for engine "
            + ", ".join(uncovered)
            + ", so this clock is an upper bound on the machine's core clock "
            "and can only fall as those engines are routed."
        )
    else:
        note_parts.append(
            "Every modelled engine family now has a routed block, so this is "
            "the slowest of them and not an upper bound standing in for the "
            "ones nobody has built."
        )
    return {
        "value": slowest["fmax_hz"],
        "source": slowest["source"],
        "note": "  ".join(note_parts),
        "binding_block": slowest["block"],
        "uncovered_families": uncovered,
    }


def measured_rate(spec: dict[str, Any]) -> dict[str, Any]:
    body = json.loads((REPO / spec["path"]).read_text())
    correlation = body["program_correlation"]
    work = sum(int(correlation[f]) for f in spec["work_fields"])
    cycles = _case_cycles(body, spec["reference_case"])
    second = _case_cycles(body, spec["second_case"])
    rate = work / cycles
    second_rate = work / second
    spread = abs(second_rate - rate) / rate
    note = (
        f"one {spec['engine']} instance retired {work} work units "
        f"({spec['counters']}) in {cycles} cycles under "
        f"{spec['reference_case']}; the independent {spec['second_case']} run "
        f"of the same campaign took {second} cycles, a "
        f"{spread * 100:.2f}% spread on the rate."
    )
    cross = spec.get("cross_check")
    if cross is not None:
        cross_path, cross_case, cross_fields, cross_engine = cross
        other = json.loads((REPO / cross_path).read_text())
        other_work = sum(int(other["program_correlation"][f]) for f in cross_fields)
        other_cycles = _case_cycles(other, cross_case)
        other_rate = other_work / other_cycles
        note += (
            f"  This is not one rate for the whole family: a different "
            f"{spec['parameter'].split('.')[1]}-family engine, {cross_engine}, "
            f"measures {other_rate:.9f} work/lane/cycle in {cross_path} "
            f"({other_work} work units in {other_cycles} cycles), "
            f"{other_rate / rate:.2f}x this one.  The table carries the slower "
            "of the measured operators, because a family rate that is faster "
            "than an operator the family has to run is a rate no run supports."
        )
        if other_rate < rate:
            raise SystemExit(
                f"{spec['parameter']}: the cross-check operator is slower "
                f"({other_rate}) than the one the table carries ({rate}); "
                "the table must carry the slower one"
            )
    if spec["replicated_by"] is not None:
        rep_path, rep_case = spec["replicated_by"]
        rep = json.loads((REPO / rep_path).read_text())
        rep_work = sum(int(rep["program_correlation"][f]) for f in spec["work_fields"])
        rep_cycles = _case_cycles(rep, rep_case)
        note += (
            f"  Replicated on a second operator: {rep_path} retires "
            f"{rep_work} work units in {rep_cycles} cycles, "
            f"{rep_work / rep_cycles:.9f} work/lane/cycle."
        )
    note += (
        "  The campaign's memories are behavioural, so this rate is the RTL's "
        "own cycle behaviour under that memory model and not a post-layout "
        "timing result; it is a rate, so it is independent of the clock."
    )
    return {
        "value": rate,
        "work_units": work,
        "cycles": cycles,
        "source": (
            f"{spec['path']}#cases[name={spec['reference_case']}]"
            f".observation.cycles and #program_correlation."
            + "+".join(spec["work_fields"])
        ),
        "note": note,
    }


def campaign_rate(spec: dict[str, Any]) -> dict[str, Any]:
    body = json.loads((REPO / ENGINE_RATE_CAMPAIGN).read_text())
    for case in body["cases"]:
        if case["name"] == spec["case"]:
            break
    else:
        raise SystemExit(f"{ENGINE_RATE_CAMPAIGN} has no case {spec['case']!r}")
    if not case["simulators_agree"]:
        raise SystemExit(f"{spec['case']}: the two simulators do not agree")
    simulators = ", ".join(run["simulator"] for run in case["runs"])
    return {
        "value": case["work_units"] / case["cycles"],
        "work_units": case["work_units"],
        "cycles": case["cycles"],
        "source": (
            f"{ENGINE_RATE_CAMPAIGN}#cases[name={case['name']}]"
            ".work_units and .cycles"
        ),
        "note": (
            f"one {case['design']} instance accepted {case['work_units']} "
            f"{case['work_counter']} in {case['cycles']} clocks, measured "
            f"identically on {simulators}.  {case['note']}  This block has a "
            "full place-and-route result in both physical views ("
            + ", ".join(case["routed_in"]) + ") from the same source file the "
            "bench compiled, so its rate and its frequency are the same "
            "design and not two.  The hand-written table "
            "assumed 1.0 here; the measurement says the assumption was very "
            "nearly right, which is a result and not a correction."
        ),
    }


def build(view: str) -> dict[str, Any]:
    plan = DERIVED[view]
    body = json.loads((HARDWARE / plan["base"]).read_text())
    if body.get("schema") != COST_TABLE_SCHEMA:
        raise SystemExit(f"base table {plan['base']} has an unexpected schema")
    parameters = body["parameters"]

    if plan.get("routed_clock", True):
        clock = routed_clock(view)
        parameters["clock.frequency_hz"] = {
            "value": clock["value"],
            "unit": "Hz",
            "provenance": "characterized",
            "source": clock["source"],
            "note": clock["note"],
        }
        uncovered = clock["uncovered_families"]
    else:
        # No block of this machine has been routed, so the clock stays whatever
        # the base table assumed and every family is uncovered.  Saying that
        # here, rather than quietly borrowing a clock from a view that does
        # have one, is the whole point: ADR-003 section 3.5 forbids mixing
        # views, and a borrowed clock is a mixed view with the label filed off.
        uncovered = list(MODELLED_FAMILIES)

    # Both kinds of measured rate land in the same shape: the two operands the
    # cycle model divides, plus where they were measured.  The difference is
    # only which artifact reports them.
    for spec, derive in (
        *((spec, measured_rate) for spec in MEASURED_RATES),
        *((spec, campaign_rate) for spec in ENGINE_RATE_CASES),
    ):
        measured = derive(spec)
        parameters[spec["parameter"]] = {
            "value": measured["value"],
            "unit": "work/lane/cycle",
            "provenance": "characterized",
            "source": measured["source"],
            "note": measured["note"],
            "convert": "work_over_cycles",
            "work_units": measured["work_units"],
            "cycles": measured["cycles"],
        }

    body["cost_table_id"] = plan["cost_table_id"]
    body["version"] = plan["version"]
    body["technology_view"] = view
    body["description"] = plan["lineage"] + (
        "  Generated by tools/build_abi3_cost_tables.py from the artifacts each "
        "characterized parameter cites; run that tool with --check to verify "
        "this file still matches them."
    )
    body["derived_from"] = {
        "generator": "tools/build_abi3_cost_tables.py",
        "base_table": plan["base"],
        "characterized_parameters": sorted(
            name
            for name, entry in parameters.items()
            if entry.get("provenance") == "characterized"
        ),
        "engine_families_with_no_routed_block": uncovered,
        "clock_is_routed": bool(plan.get("routed_clock", True)),
    }
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit non-zero if a generated table has drifted",
    )
    parser.add_argument(
        "--view",
        action="append",
        choices=sorted(DERIVED),
        help="build only this view (repeatable); default is all of them",
    )
    args = parser.parse_args(argv)
    views = args.view or sorted(DERIVED)

    drifted: list[str] = []
    for view in views:
        body = build(view)
        target = HARDWARE / DERIVED[view]["out"]
        payload = canonical_json(body)
        if args.check:
            if not target.exists():
                drifted.append(f"{target} does not exist")
            elif target.read_bytes() != payload:
                drifted.append(f"{target} differs from the artifacts it cites")
            continue
        target.write_bytes(payload)
        clock = body["parameters"]["clock.frequency_hz"]["value"]
        print(
            f"wrote {target.relative_to(REPO)}  "
            f"clock {clock:,.0f} Hz  "
            f"characterized {len(body['derived_from']['characterized_parameters'])}"
            f"/{len(body['parameters'])}"
        )
    report = pending_report()
    readable = [row for row in report
                if row["state"] in ("routed", "routed_not_closed")]
    print(
        f"pending V4.1 blocks (plan WP-J/WP-M): {len(readable)} of "
        f"{len(report)} (view, block) pairs have a post-route fmax; "
        f"{len(report) - len(readable)} have none, so no cost-table entry is "
        f"added for them"
    )
    for row in report:
        print(f"  {row['state']:20s} {row['view']:8s} {row['block']:22s} "
              f"({row['family']})  {row['why']}")
    if readable:
        # Not a drift and not a failure of this run: the tables on disk are
        # still exactly what their cited artifacts say.  It IS the one moment
        # the five entries may be added, and the entry that adds them has to be
        # reviewed, because four of them are the first routed blocks of their
        # families and the view's core clock is a minimum over those.
        print(
            "ACTION REQUIRED: "
            + ", ".join(f"{r['view']}/{r['block']}" for r in readable)
            + " now carry a post-route fmax ("
            + ", ".join(f"{r['fmax_hz']:.6g} Hz" for r in readable)
            + ").  Move them from PENDING_ROUTED_BLOCKS into ROUTED_BLOCKS and "
            "re-run this tool without --check: the affected views' "
            "clock.frequency_hz is the MINIMUM over routed blocks of modelled "
            "families, so the clock can only fall and every derived time moves "
            "with it.  DS41-PHY10 also requires DRC 0, antenna 0 and a clean "
            "worktree on the record before it is evidence.",
            file=sys.stderr,
        )
    if drifted:
        for line in drifted:
            print(f"DRIFT: {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
