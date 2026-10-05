#!/usr/bin/env python3
"""What the measured boundary does, and does not, license for ``technology.json``.

Gate G4's failure names three unmet items, and one of them is
``technology.json#latency not re-derived``.  That reads like undone work.  It
is not: the re-derivation is *refused*, and this tool exists so the reason is
an artifact rather than an argument someone has to reconstruct.

The question
------------
``latency.pipeline_fill_drain_s`` is graded ``assumed`` at 32 fabric cycles
with a band of [16, 128].  Two RTL records now measure a dependent boundary:
``abi3_boundary_chain_measured.json`` (the datapath half, 99 cycles at the
headline adder depth L=3) and ``abi3_boundary_control.json`` (the control
half, 8 cycles).  The obvious move is to replace 32 with their sum.

Why the obvious move is wrong
-----------------------------
``tools/derive_cycle_machine.py`` spends ``pipeline_fill_drain_s`` as
``engine.<family>.fixed_latency_cycles`` -- a fixed LATENCY charged once per
engine instruction.  The datapath record's own ``establishes`` list says, in
its third entry, that the measured boundary

    "does not scale with the depth of the reduction and does scale with the
    endpoint's pipeline depth by exactly 1 + 3L: it is a SERVICE term, not a
    latency term, which is the opposite of what a fixed per-boundary charge
    assumes"

So the measurement and the model disagree about what KIND of quantity this is,
not merely about its size.  Substituting 107 for 32 would put a service number
into a latency slot: a second modelling error wearing the first one's clothes,
and one that would be harder to find because the number would now look
measured.  R14 does not apply -- there is no consumer to follow, because the
consumer is charging a different kind of thing than the producer measured.

Three further reasons the substitution is not licensed, each checked below
against the records rather than asserted:

  1. the measured pair is purpose-built for the measurement, not lifted from a
     compiled deployment, so it is not the shipped array-pass boundary the
     model charges;
  2. three of section 3.6's five terms are outside the measured span by
     construction, so the composed figure is arithmetic over two records
     rather than one measurement -- the datapath record says so itself; and
  3. the two halves were measured on different vehicles, so their sum is a
     bound, not a boundary.

What IS licensed
----------------
The measurement bounds the assumption FROM BELOW, and that is a real finding
rather than a null result.  The datapath half alone is 99 cycles against a
32-cycle point value: the assumption is optimistic by 3.1x on a term the model
charges to BOTH storage classes, once per engine instruction.  The composed
node-local figure lands at 107, inside the declared band but at its 81st
percentile, so the band's own high end -- not its centre -- is where the
evidence sits.

This tool reports that, computes the sensitivity of the frozen ROM-vs-HBM
budget to it, and refuses to write a new value.  Nothing here edits
``technology.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

TECHNOLOGY = ROOT / "configs/hardware/technology.json"
DATAPATH = ROOT / "results/rtl/abi3_boundary_chain_measured.json"
CONTROL = ROOT / "results/rtl/abi3_boundary_control.json"
CALIBRATION = ROOT / "results/derived/qwen3_n5_design_target_calibration.json"
BUDGET = ROOT / "configs/gates/tpot_budget_provisional.json"

DEFAULT_OUTPUT = ROOT / "results/derived/boundary_technology_rederivation_audit.json"

# The key the model spends and the name it spends it under.  Both are read
# back from the source below rather than trusted from this comment.
TECH_KEY = "pipeline_fill_drain_s"
MODEL_SITE = "tools/derive_cycle_machine.py"
MODEL_SYMBOL = "array_pass_boundary_s"
MODEL_CHARGE = "fixed_latency_cycles"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    dirty = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD") or None,
        "worktree_dirty": bool(dirty),
        "scope": (
            "the tree THIS artifact was derived in.  It is not a claim about "
            "the tree any measurement it reads was taken in; each of those "
            "records carries its own."
        ),
    }


def _walk(node: Any, key: str) -> Any:
    """First value for ``key`` anywhere in ``node``, else None."""

    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _walk(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _walk(item, key)
            if found is not None:
                return found
    return None


def read_assumption() -> dict[str, Any]:
    tech = json.loads(TECHNOLOGY.read_text())
    entry = tech["latency"][TECH_KEY]
    cycles = entry["derived_in_fabric_cycles"]
    return {
        "key": f"latency.{TECH_KEY}",
        "grade": entry.get("grade"),
        "source": entry.get("source"),
        "value_s": entry.get("value"),
        "cycles": {
            "value": cycles["value"],
            "range_low": cycles["range_low"],
            "range_high": cycles["range_high"],
        },
        "fabric_clock_hz": float(tech["power"]["fabric_clock_hz"]["value"]),
    }


def read_measurements() -> dict[str, Any]:
    datapath = json.loads(DATAPATH.read_text())
    control = json.loads(CONTROL.read_text())

    d_boundary = datapath["boundary"]
    c_boundary = control["boundary"]

    return {
        "datapath": {
            "artifact": "results/rtl/abi3_boundary_chain_measured.json",
            "artifact_sha256": sha256(DATAPATH),
            "cycles": d_boundary["cycles"],
            "per_adder_depth": d_boundary["adder_depth"]["per_stages"],
            "headline_stages": d_boundary["adder_depth"]["headline_stages"],
            "decomposition": d_boundary["decomposition"],
            "simulators_agree": _walk(datapath, "simulators_agree"),
            "is_the_section_13_item_13_boundary": d_boundary.get(
                "is_the_section_13_item_13_boundary"
            ),
            "why_not": d_boundary.get("why_not"),
            "establishes": datapath["claim_boundary"]["establishes"],
        },
        "control": {
            "artifact": "results/rtl/abi3_boundary_control.json",
            "artifact_sha256": sha256(CONTROL),
            "cycles": c_boundary["cycles"],
            "decomposition": c_boundary["decomposition"],
            "simulators_agree": c_boundary.get("simulators_agree"),
            "why_not": c_boundary.get("why_not"),
        },
    }


def kind_mismatch(measurements: dict[str, Any]) -> dict[str, Any]:
    """The refusal that does the work: measured KIND != charged KIND."""

    establishes = measurements["datapath"]["establishes"]
    service = [line for line in establishes if "SERVICE term" in line]
    model_source = (ROOT / MODEL_SITE).read_text()
    charges_as_latency = MODEL_CHARGE in model_source and MODEL_SYMBOL in model_source

    return {
        "the_model_charges": {
            "site": MODEL_SITE,
            "symbol": MODEL_SYMBOL,
            "as": f"engine.<family>.{MODEL_CHARGE}",
            "per": "one engine instruction",
            "kind": "latency",
            "verified_in_source": charges_as_latency,
        },
        "the_measurement_reports": {
            "kind": "service",
            "quoted_from_the_record": service[0] if service else None,
            "scales_with": "the endpoint's pipeline depth, by exactly 1 + 3L",
            "does_not_scale_with": "the depth of the reduction",
        },
        "holds": bool(service) and charges_as_latency,
        "consequence": (
            "substituting the measured cycles for the assumed value would put "
            "a service number into a latency slot.  That is a second modelling "
            "error, and a worse one than the first, because the number would "
            "then look measured."
        ),
    }


def other_refusals(measurements: dict[str, Any]) -> list[dict[str, Any]]:
    d = measurements["datapath"]
    c = measurements["control"]
    return [
        {
            "id": "not-the-shipped-boundary",
            "why": (
                "the measured pair is built for the measurement rather than "
                "taken from a compiled deployment, so it is not the array-pass "
                "boundary of a shipped program, which is what the model charges"
            ),
            "evidence": "the datapath record's claim_boundary.does_not_establish",
            "holds": d["is_the_section_13_item_13_boundary"] is False,
        },
        {
            "id": "three-of-five-terms-outside",
            "why": (
                "three of section 3.6's five terms -- mesh transfer, queue "
                "admission and acknowledged completion -- are outside the "
                "datapath span by construction, so any composed total is "
                "arithmetic over two records rather than one measurement"
            ),
            "evidence": d["why_not"],
            "holds": bool(d["why_not"]),
        },
        {
            "id": "two-vehicles-one-sum",
            "why": (
                "the datapath and control halves were measured on different "
                "vehicles, so their sum bounds the boundary rather than "
                "measuring it"
            ),
            "evidence": c["why_not"],
            "holds": bool(c["why_not"]),
        },
    ]


def sensitivity(assumption: dict[str, Any], measurements: dict[str, Any]) -> dict[str, Any]:
    """What the frozen budget would do IF the term moved.  Not a proposal."""

    assumed = float(assumption["cycles"]["value"])
    datapath = float(measurements["datapath"]["cycles"])
    control = float(measurements["control"]["cycles"])
    composed = datapath + control

    low = float(assumption["cycles"]["range_low"])
    high = float(assumption["cycles"]["range_high"])
    percentile = (composed - low) / (high - low) * 100.0

    calibration = json.loads(CALIBRATION.read_text())
    case = calibration["calibration"]["control_plane"]["cases"][0]
    engine_steps = int(case["instruction_mix"]["engine_steps"])
    clock_hz = float(assumption["fabric_clock_hz"])

    delta_cycles = (composed - assumed) * engine_steps
    delta_s = delta_cycles / clock_hz

    # The budget's live rows are `budgets`; the superseded Qwen rows are kept
    # under their own key and are deliberately not read here.  One model's
    # pair is compared, not a mix: the ratio is only meaningful within a model
    # at one batch size and context length.
    budget = json.loads(BUDGET.read_text())
    pair_model = "Qwen3-8B"
    frozen: dict[str, dict[str, Any]] = {}
    for row in budget.get("budgets", []):
        if not isinstance(row, dict) or row.get("model") != pair_model:
            continue
        store = row.get("storage_class")
        value = row.get("budget_tpot_s")
        if store in {"rom", "hbm"} and value and store not in frozen:
            frozen[store] = {
                "budget_tpot_s": float(value),
                "batch_size": row.get("batch_size"),
                "context_tokens": row.get("context_tokens"),
            }

    projected = None
    if {"rom", "hbm"} <= set(frozen):
        rom, hbm = frozen["rom"], frozen["hbm"]
        comparable = (
            rom["batch_size"] == hbm["batch_size"]
            and rom["context_tokens"] == hbm["context_tokens"]
        )
        rom_s = rom["budget_tpot_s"]
        hbm_s = hbm["budget_tpot_s"]
        projected = {
            "model": pair_model,
            "batch_size": rom["batch_size"],
            "context_tokens": rom["context_tokens"],
            "rows_are_comparable": comparable,
            "frozen_rom_s": rom_s,
            "frozen_hbm_s": hbm_s,
            "frozen_ratio": hbm_s / rom_s,
            "shifted_rom_s": rom_s + delta_s,
            "shifted_hbm_s": hbm_s + delta_s,
            "shifted_ratio": (hbm_s + delta_s) / (rom_s + delta_s),
        }
        if not comparable:
            projected["refused"] = (
                "the two rows differ in batch size or context length, so "
                "their ratio is not a like-for-like comparison and the "
                "shifted figures must not be quoted"
            )

    return {
        "assumed_cycles": assumed,
        "measured_datapath_cycles": datapath,
        "measured_control_cycles": control,
        "composed_node_local_cycles": composed,
        "optimism_factor_datapath_only": datapath / assumed,
        "optimism_factor_composed": composed / assumed,
        "inside_declared_band": low <= composed <= high,
        "band_percentile_of_composed": percentile,
        "engine_steps_per_transaction": engine_steps,
        "engine_steps_source": (
            "results/derived/qwen3_n5_design_target_calibration.json "
            "calibration.control_plane.cases[0].instruction_mix.engine_steps"
        ),
        "delta_cycles_per_transaction": delta_cycles,
        "delta_seconds_at_fabric_clock": delta_s,
        "projected": projected,
        "this_is_not_a_proposal": (
            "the term is charged to BOTH storage classes once per engine "
            "instruction, so moving it adds the same seconds to each and "
            "compresses the ratio rather than reversing it.  This arithmetic "
            "shows the SENSITIVITY of the frozen budget to a term the "
            "refusals above say must not be moved on this evidence.  It is "
            "not a corrected budget and must not be quoted as one."
        ),
        "double_counting_caveat": (
            "do not add this to the control-plane gap without checking for "
            "overlap.  The cosimulation that measured the control plane ran "
            "STUB engines that complete the cycle after acceptance, so the "
            "engine fixed-latency term was not active in that comparison and "
            "the two look separable -- but neither record was designed to "
            "establish that, and no measurement here does."
        ),
    }


def audit() -> dict[str, Any]:
    assumption = read_assumption()
    measurements = read_measurements()
    mismatch = kind_mismatch(measurements)
    refusals = other_refusals(measurements)

    licensed = all(not r["holds"] for r in refusals) and not mismatch["holds"]

    return {
        "schema": "opentallas.derived.boundary_technology_rederivation_audit.v1",
        "question": (
            "does the measured dependent boundary license re-deriving "
            f"technology.json#latency.{TECH_KEY}?"
        ),
        "verdict": "licensed" if licensed else "refused",
        "assumption": assumption,
        "measurements": measurements,
        "kind_mismatch": mismatch,
        "refusals": refusals,
        "what_is_licensed": {
            "claim": (
                "the measurement bounds the assumption from below: the "
                "datapath half ALONE exceeds the assumed point value, on a "
                "term charged to both storage classes once per engine "
                "instruction"
            ),
            "not_licensed": (
                "replacing the value, narrowing the band, or reporting any "
                "composed figure as a measurement of the boundary"
            ),
        },
        "sensitivity": sensitivity(assumption, measurements),
        "g4_item": (
            "G4's reason line reads 'technology.json#latency not re-derived'. "
            "This artifact is why it stays not-re-derived.  A refused "
            "re-derivation with a stated reason is a different state from an "
            "undone one, and the gate should keep failing either way: the "
            "model still charges a term whose grade is 'assumed' and whose "
            "kind the RTL now contradicts."
        ),
        "generated_by": "tools/audit_boundary_technology_rederivation.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--json", action="store_true", help="print the whole record")
    args = parser.parse_args(argv)

    record = audit()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    s = record["sensitivity"]
    print(f"verdict: {record['verdict']}")
    print(
        f"  assumed {s['assumed_cycles']:g} cycles; measured datapath "
        f"{s['measured_datapath_cycles']:g}, control {s['measured_control_cycles']:g}, "
        f"composed {s['composed_node_local_cycles']:g} "
        f"({s['optimism_factor_composed']:.2f}x the assumption, "
        f"{'inside' if s['inside_declared_band'] else 'OUTSIDE'} the band at its "
        f"{s['band_percentile_of_composed']:.0f}th percentile)"
    )
    print(f"  kind mismatch holds: {record['kind_mismatch']['holds']}")
    for refusal in record["refusals"]:
        print(f"  refusal {refusal['id']}: {refusal['holds']}")
    if s["projected"]:
        p = s["projected"]
        print(
            f"  SENSITIVITY ONLY (not a proposal): frozen ratio "
            f"{p['frozen_ratio']:.2f}x would become {p['shifted_ratio']:.2f}x"
        )
    print(f"wrote {out.relative_to(ROOT)}")
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
