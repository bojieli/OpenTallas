#!/usr/bin/env python3
"""What the measured front end does, and does not, license for ``technology.json``.

Gate G4's failure names ``technology.json#latency not re-derived``, and this is
the second of the two keys that phrase covers.
``tools/audit_boundary_technology_rederivation.py`` already recorded the refusal
for ``pipeline_fill_drain_s``; this records it for
``sequencer_issue_decode_s``, so that neither reads as undone work.

The question
------------
``latency.sequencer_issue_decode_s`` is graded ``assumed`` at 3 ns, described as
"instruction fetch, decode and operand setup for one layer's command stream ...
a few cycles at a ~1 GHz fabric clock".  A per-state census of
``ot_a3_microsequencer`` has now measured that front end: it costs a FIXED
**14 cycles per instruction** with the shipped defaults, and 8.66 with the two
fixes ``b641c86`` landed switched on.  A 14-cycle front end is 14 ns even at
the model's own assumed 1 GHz -- 4.7x the assumed value.  The obvious move is
to substitute.

Why the obvious move is wrong
-----------------------------
There is no clock with which to convert RTL cycles into an N5 second.

  * The measured RTL is a NON-PIPELINED control plane elaborated for an open
    PDK.  The design point this key serves is an N5 pipelined machine at five
    token slots.  They are different machines, and the key is a second, not a
    cycle count.
  * ``calibration.clock.calibrated`` is false, and the calibration record says
    in as many words that no routed record at N5 exists.  The control plane DOES
    have its own ASAP7 route -- ``results/physical_abi3/asap7/a3_microsequencer/
    pnr.json``, 264.8 MHz at 4.4 ns -- and it does not close: ``closed`` is
    false with 3,204 max-slew and 3 max-cap violations.  (An earlier draft of
    this file cited the g2 cluster's 216.7 MHz and 8 slew violations here, which
    is a different and much larger vehicle; the microsequencer's own record is
    the right evidence and makes the point more strongly.)
  * ``derive_cycle_machine.py`` (line ~818) hardcodes ``front_end_cycles = 3``
    and then sets ``clock_hz = front_end_cycles / sequencer_issue_decode_s``.
    The key and the cycle count are two ends of one identity.  Substituting a
    measured cycle count into it does not calibrate the model; it republishes
    the clock.  The counterfactual is measured in the audit below: at front ends
    of 3, 14 and 38 cycles the model's predicted TIME is bit-identical and only
    the published clock moves, 1 -> 4.667 -> 12.667 GHz.

So the same reasoning as the boundary refusal applies, for a different reason.
There the mismatch was of KIND -- a service term spent as a latency.  Here it is
of MACHINE and of CLOCK: a cycle count measured on one implementation cannot be
divided by a clock that has never been measured on the other.

What IS licensed
----------------
A BOUND on an assumed analytical parameter, which is a real finding rather than
a null result.  The RTL establishes that a statically scheduled front end of
this shape costs 14 cycles, not "a few", and that 8.66 is reachable by two
changes already in the tree.  Whatever clock the N5 machine eventually
declares, 3 ns buys 3 cycles at 1 GHz and the shipped RTL needs 14 -- so either
the N5 front end must be pipelined in a way this RTL is not, or the assumed
value is optimistic by something close to the ratio measured here.  That is
worth recording against the parameter and is not worth pretending is a
measurement of it.

This tool reports that and refuses to write a new value.  Nothing here edits
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
CALIBRATION = ROOT / "results/derived/qwen3_n5_design_target_calibration.json"
MODEL_SITE = ROOT / "tools/derive_cycle_machine.py"
MICROSEQ_ROUTE = ROOT / "results/physical_abi3/asap7/a3_microsequencer/pnr.json"
BOUNDARY_AUDIT = ROOT / "results/derived/boundary_technology_rederivation_audit.json"

DEFAULT_OUTPUT = ROOT / "results/derived/sequencer_technology_rederivation_audit.json"

TECH_KEY = "sequencer_issue_decode_s"

# Measured by a per-state census of ot_a3_microsequencer.state over 65 real
# ABI3 cases (452 instructions, Icarus), both builds passing identically.
MEASURED = {
    "front_end_cycles_per_instruction_knobs_off": 13.97,
    "front_end_cycles_per_instruction_knobs_on": 8.66,
    "census_cases": 65,
    "census_instructions": 452,
    "what_knobs": "CRC_CACHE and FAST_FRONT_END, landed off by default in b641c86",
    "vehicle": "ot_a3_microsequencer, non-pipelined front end, open-PDK elaboration",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("rev-parse", "HEAD") or None,
        "worktree_dirty": bool(run("status", "--porcelain")),
        "scope": (
            "the tree THIS artifact was derived in; each measurement it cites "
            "carries its own provenance"
        ),
    }


def _microsequencer_route() -> dict[str, Any]:
    """The control plane's OWN routed record, not the cluster's.

    Cited because the distinction matters: the microsequencer routes at 264.8
    MHz and does NOT close, with 3,204 max-slew violations.  A draft of this
    audit cited the g2 cluster instead -- a 699k-cell vehicle containing the
    array and five memory macro types -- which is a different machine and a
    weaker fact.
    """

    if not MICROSEQ_ROUTE.exists():
        return {"present": False}
    d = json.loads(MICROSEQ_ROUTE.read_text())
    m = d["place_and_route"]["metrics"]
    return {
        "present": True,
        "artifact": "results/physical_abi3/asap7/a3_microsequencer/pnr.json",
        "fmax_mhz": round(m.get("fmax_hz", 0) / 1e6, 1),
        "clock_period_ns": d["place_and_route"].get("clock_period_ns"),
        "closed": (d.get("design") or {}).get("closed"),
        "max_slew_violations": m.get("max_slew_violations"),
        "max_cap_violations": m.get("max_cap_violations"),
        "why_it_matters": (
            "the one routed period the control plane has does not close, so "
            "there is no closed period on ANY node with which to convert its "
            "cycles into seconds"
        ),
    }


def read_assumption() -> dict[str, Any]:
    tech = json.loads(TECHNOLOGY.read_text())
    entry = tech["latency"][TECH_KEY]
    return {
        "key": f"latency.{TECH_KEY}",
        "grade": entry.get("grade"),
        "source": entry.get("source"),
        "value_s": entry.get("value"),
        "note": entry.get("note"),
        "fabric_clock_hz": float(tech["power"]["fabric_clock_hz"]["value"]),
    }


def identity_coupling() -> dict[str, Any]:
    """The key and the model's cycle unit are two ends of one equation."""

    src = MODEL_SITE.read_text()
    hardcodes = "front_end_cycles = 3" in src
    divides = "clock_hz = front_end_cycles / seq_s" in src or (
        "front_end_cycles /" in src and "seq_s" in src
    )
    return {
        "site": "tools/derive_cycle_machine.py",
        "hardcodes_front_end_cycles_3": hardcodes,
        "derives_clock_from_the_key": divides,
        "identity": "clock_hz = front_end_cycles / latency.sequencer_issue_decode_s",
        "consequence": (
            "the front-end cycle count and this key are not independent.  "
            "Substituting a measured cycle count republishes the clock rather "
            "than calibrating the model -- and the model's predicted TIME does "
            "not move when it changes, so nothing about the design point tests "
            "which value is right."
        ),
        "measured_counterfactual": {
            "front_end_3_cycles": {"clock_ghz": 1.0},
            "front_end_14_cycles": {"clock_ghz": 4.667},
            "front_end_38_cycles": {"clock_ghz": 12.667},
            "predicted_compute_time_s": "bit-identical at all three (1.586170097639e-04)",
            "anchor_reproduced": "True at all three, relative error 0.000e+00",
        },
    }


def refusals(assumption: dict[str, Any]) -> list[dict[str, Any]]:
    cal = json.loads(CALIBRATION.read_text())
    clock = (cal.get("calibration") or {}).get("clock") or {}
    return [
        {
            "id": "different-machine",
            "why": (
                "the measurement is of a NON-PIPELINED control plane elaborated "
                "for an open PDK; the key serves an N5 pipelined design point at "
                "five token slots.  A cycle count on one is not a second on the "
                "other."
            ),
            "holds": True,
        },
        {
            "id": "no-clock-to-convert-with",
            "the_control_planes_own_route": _microsequencer_route(),
            "why": (
                "calibration.clock.calibrated is false and the record states no "
                "routed N5 record exists, so there is no measured period with "
                "which to turn 14 cycles into a second"
            ),
            "evidence": str(clock.get("note"))[:400] or None,
            "holds": clock.get("calibrated") is not True,
        },
        {
            "id": "the-key-is-half-an-identity",
            "why": (
                "derive_cycle_machine.py sets clock_hz = front_end_cycles / this "
                "key, so a substitution moves the published clock and changes no "
                "prediction the model makes"
            ),
            "holds": True,
        },
    ]


def audit() -> dict[str, Any]:
    assumption = read_assumption()
    coupling = identity_coupling()
    refs = refusals(assumption)
    clock = assumption["fabric_clock_hz"]
    assumed_cycles = assumption["value_s"] * clock

    return {
        "schema": "opentallas.derived.sequencer_technology_rederivation_audit.v1",
        "question": (
            "does the measured microsequencer front end license re-deriving "
            f"technology.json#latency.{TECH_KEY}?"
        ),
        "verdict": "refused",
        "assumption": assumption,
        "assumed_cycles_at_fabric_clock": assumed_cycles,
        "measured": MEASURED,
        "optimism_factor_knobs_off": MEASURED[
            "front_end_cycles_per_instruction_knobs_off"
        ] / assumed_cycles,
        "optimism_factor_knobs_on": MEASURED[
            "front_end_cycles_per_instruction_knobs_on"
        ] / assumed_cycles,
        "identity_coupling": coupling,
        "refusals": refs,
        "what_is_licensed": {
            "claim": (
                "a BOUND on an assumed parameter: a statically scheduled front "
                "end of this shape costs 14 cycles rather than 'a few', and "
                "8.66 is reachable with two changes already in the tree.  "
                "Either the N5 front end must be pipelined in a way this RTL is "
                "not, or 3 ns is optimistic by close to the measured ratio."
            ),
            "not_licensed": (
                "replacing the value, or reporting any cycles-to-seconds "
                "conversion as a measurement of this key"
            ),
        },
        "companion": {
            "artifact": "results/derived/boundary_technology_rederivation_audit.json",
            "sha256": sha256(BOUNDARY_AUDIT) if BOUNDARY_AUDIT.exists() else None,
            "note": (
                "the other half of G4's 'technology.json#latency not re-derived'. "
                "That one is refused on a mismatch of KIND -- a service term "
                "spent as a fixed latency.  This one is refused on machine and "
                "clock.  Both are refusals with stated reasons, not omissions."
            ),
        },
        "g4_item": (
            "G4's reason line reads 'technology.json#latency not re-derived'. "
            "With this artifact and the boundary audit, both keys that phrase "
            "covers are refused with reasons rather than left undone.  G4 should "
            "keep failing: the model still charges assumed values, and the "
            "dominant unmodelled cost is not a parameter at all -- view "
            "resolution alone is 9.51 cycles per instruction and "
            "CycleModel._time_steps prices no term for it."
        ),
        "generated_by": "tools/audit_sequencer_technology_rederivation.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    record = audit()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    print(f"verdict: {record['verdict']}")
    print(
        f"  assumed {record['assumed_cycles_at_fabric_clock']:.1f} cycles "
        f"({record['assumption']['value_s']:g} s at "
        f"{record['assumption']['fabric_clock_hz']:g} Hz); measured "
        f"{MEASURED['front_end_cycles_per_instruction_knobs_off']:.2f} knobs off "
        f"({record['optimism_factor_knobs_off']:.2f}x), "
        f"{MEASURED['front_end_cycles_per_instruction_knobs_on']:.2f} knobs on "
        f"({record['optimism_factor_knobs_on']:.2f}x)"
    )
    for r in record["refusals"]:
        print(f"  refusal {r['id']}: {r['holds']}")
    print(f"wrote {out.relative_to(ROOT)}")
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
