#!/usr/bin/env python3
"""What the reduced regression configuration still needs, and what it costs.

Rung G1f has one blocker left: no vehicle runs the reduced program end to end.
Three things had to be true before that blocker could even be approached, and
all three now are:

  * the reduced model exports Kernel IR (a second pinned source contract);
  * both stores lower it (ROM to 14 regions over 3,607,040 payload bytes, HBM
    to 74 instructions and 225 descriptors from 88 kernels, verifier ADMITTED);
  * the integrated vehicle elaborates at the reduced attention geometry, and
    every engine the run touches admits the reduced shapes.

This tool records the state of the remaining chain, measured rather than
guessed, so the next step is a decision about cost and not a rediscovery.

What was measured here
----------------------
The reduced ROM deployment was put through the SHIPPED ROM schedule campaign,
against the shipped ``rom_qwen3`` capability -- not a reduced one, deliberately,
because if the shipped capability refused it that would be worth knowing.  It
does not refuse it: **63 of 63 checks pass**, ``verifier.admitted`` is true, over
74 instructions and 19 schedules.  Every structural check the shipped
deployments face is included -- ``layer_loop_count``, ``layer_loop_trip``,
``kernel_coverage``, ``rom_shard_coverage``, ``capability_identity``,
``exact_retired_work_bound``, ``memory_capacity``.

So the first link of the chain holds.  The chain is walkable.

What it costs, and why that is not done here
--------------------------------------------
``tools/build_abi3_deployment_rtl_vectors.py``'s ``TARGETS`` cites
``ROM_SCHEDULE_EVIDENCE`` by case name, so a reduced target needs its case in
the COMMITTED ``results/abi3/rom_schedule_checks.json``.  Adding a fourth case
changes that artifact's bytes, and **18 artifacts under results/derived bind its
digest**.  Regenerating it therefore stales all eighteen.

That is a deliberate cascade to schedule, not a side effect to incur while
proving a link works.  ``tools/check_rom_schedules.py`` already takes
``--case NAME KERNEL_IR DEPLOYMENT CAPABILITY`` on the command line, which is
how the measurement above was taken without touching the committed artifact.

The rest of the chain, in order, with what each needs:

  1. the reduced case in the committed ROM schedule artifact (cascade: 18);
  2. a ``TARGETS`` entry, which also needs an HBM deployment certificate for
     the HBM side's ``evidence``;
  3. per-target ``BOUNDARY_IDENTITIES`` and ``expected_counts`` in
     ``tools/build_abi3_shipped_prefix_vectors.py``.  These cannot be written
     ahead of time: they are what the builder REPORTS on a first run and are
     then pinned, so this step is a bootstrap;
  4. a golden write stream for the reduced program -- the reduced analogue of
     p3_writes.hex and p3_expect.hex;
  5. the run itself, with ``ENABLE_RESULT_INJECTION=0``.  G1e's trick of
     injecting golden engine results is not available here: G1f requires
     ``golden_injected_operation_count`` to be 0, so the engines must compute.

Nothing here edits a committed artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/derived/g1f_reduced_vector_readiness.json"

ROM_SCHEDULE = ROOT / "results/abi3/rom_schedule_checks.json"
REDUCED_ROM = ROOT / "build/abi3/qwen3-reduced-rom"
REDUCED_HBM = ROOT / "build/abi3/qwen3-reduced-hbm"
REDUCED_IR = ROOT / "build/ir-v3/qwen3-reduced-v1/kernel_ir.v3.json"

# Measured by:
#   python3 tools/check_rom_schedules.py --case qwen3-reduced-rom \
#     build/ir-v3/qwen3-reduced-v1/kernel_ir.v3.json \
#     build/abi3/qwen3-reduced-rom \
#     configs/hardware/abi3_capability/rom_qwen3.json
ROM_SCHEDULE_MEASUREMENT = {
    "case": "qwen3-reduced-rom",
    "capability": "configs/hardware/abi3_capability/rom_qwen3.json",
    "capability_is_the_shipped_one": True,
    "status": "pass",
    "checks_passed": 63,
    "checks_failed": 0,
    "instructions": 74,
    "schedules": 19,
    "verifier_admitted": True,
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
    }


def cascade_cost() -> dict[str, Any]:
    """How many committed artifacts bind the ROM schedule campaign."""

    # Excluding this audit's OWN output is load-bearing, not tidiness: it names
    # results/abi3/rom_schedule_checks.json in the cascade field below, so it
    # lands in results/derived containing the very string this scan matches.
    # Counting itself made the answer change every time it ran -- 15 of the 16
    # leaves that moved between two runs were this list shifting by one entry.
    binders = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "results/derived").glob("*.json")
        if path.resolve() != DEFAULT_OUTPUT.resolve()
        and "rom_schedule_checks" in path.read_text()
    )
    return {
        "artifact_that_would_change": "results/abi3/rom_schedule_checks.json",
        "current_case_count": len(
            json.loads(ROM_SCHEDULE.read_text()).get("cases") or []
        )
        if ROM_SCHEDULE.exists()
        else None,
        "derived_artifacts_binding_it": len(binders),
        "binders": binders,
        "why_it_matters": (
            "TARGETS cites ROM_SCHEDULE_EVIDENCE by case name, so the reduced "
            "case has to be in the committed artifact; adding it changes that "
            "artifact's digest and stales every binder"
        ),
    }


def lowering_state() -> dict[str, Any]:
    def deployment(path: Path) -> dict[str, Any]:
        record = path / "deployment.json"
        if not record.is_file():
            return {"present": False, "path": str(path.relative_to(ROOT))}
        body = json.loads(record.read_text())
        return {
            "present": True,
            "path": str(path.relative_to(ROOT)),
            "deployment_sha256": sha256(record),
            "instruction_count": len(body.get("program") or [])
            or body.get("instruction_count"),
        }

    return {
        "kernel_ir": {
            "present": REDUCED_IR.is_file(),
            "path": str(REDUCED_IR.relative_to(ROOT)),
            "sha256": sha256(REDUCED_IR) if REDUCED_IR.is_file() else None,
        },
        "rom": deployment(REDUCED_ROM),
        "hbm": deployment(REDUCED_HBM),
    }


def build() -> dict[str, Any]:
    return {
        "schema": "opentallas.derived.g1f_reduced_vector_readiness.v1",
        "gate": "G1f (configs/gates/redesign_gates.json)",
        "generated_by": "tools/audit_g1f_reduced_vector_readiness.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
        "question": (
            "is the chain that ends at a reduced vector set walkable, and what "
            "does walking it cost?"
        ),
        "answer": "walkable; the first link is measured and passes",
        "rom_schedule_measurement": ROM_SCHEDULE_MEASUREMENT,
        "lowering": lowering_state(),
        "cascade": cascade_cost(),
        "remaining_chain": [
            {
                "step": 1,
                "what": "the reduced case in the committed ROM schedule artifact",
                "blocked_by": "a cascade over the artifacts that bind its digest",
                "kind": "bookkeeping with a measured cost",
            },
            {
                "step": 2,
                "what": "a TARGETS entry in build_abi3_deployment_rtl_vectors.py",
                "blocked_by": (
                    "the HBM side's evidence field needs a deployment "
                    "certificate for the reduced model"
                ),
                "kind": "new evidence",
            },
            {
                "step": 3,
                "what": (
                    "per-target BOUNDARY_IDENTITIES and expected_counts in "
                    "build_abi3_shipped_prefix_vectors.py"
                ),
                "blocked_by": (
                    "nothing, but they cannot be written ahead of time: they "
                    "are what a first run reports and are then pinned"
                ),
                "kind": "bootstrap",
            },
            {
                "step": 4,
                "what": (
                    "a golden write stream for the reduced program, the "
                    "analogue of p3_writes.hex and p3_expect.hex"
                ),
                "blocked_by": "step 3",
                "kind": "builder work",
            },
            {
                "step": 5,
                "what": "the run, with ENABLE_RESULT_INJECTION=0",
                "blocked_by": "step 4",
                "kind": "campaign",
                "note": (
                    "G1e's injection shortcut is unavailable: G1f requires "
                    "golden_injected_operation_count == 0, so the engines must "
                    "compute"
                ),
            },
        ],
        "already_closed": [
            "the compiler exports the reduced Kernel IR (second source contract)",
            "both stores lower it, verifier ADMITTED",
            "ot_a3_vector_rms_norm admits the reduced widths, bit-exact",
            "ot_a3_qwen_gqa and its reference take a geometry, bit-exact",
            "the integrated vehicle elaborates at the reduced geometry",
        ],
        "refusals": [
            {
                "id": "not-a-pass",
                "what": "this does not advance G1f's verdict",
                "why": (
                    "G1f fails on token ids [] against the oracle's "
                    "[1073, 382, 93], and nothing here runs the program"
                ),
            },
            {
                "id": "no-silent-cascade",
                "what": (
                    "the reduced case was NOT added to the committed ROM "
                    "schedule artifact"
                ),
                "why": (
                    "18 derived artifacts bind its digest; incurring that while "
                    "proving a link works would leave the tree in drift for a "
                    "measurement that did not need it"
                ),
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    body = build()
    rendered = json.dumps(body, indent=2, sort_keys=True) + "\n"
    measurement = body["rom_schedule_measurement"]
    print("G1f reduced vector-set readiness")
    print(f"  answer: {body['answer']}")
    print(
        f"  reduced ROM schedule: {measurement['status']}, "
        f"{measurement['checks_passed']} checks, "
        f"admitted={measurement['verifier_admitted']}, "
        f"against the shipped capability"
    )
    print(
        f"  cascade if wired in: "
        f"{body['cascade']['derived_artifacts_binding_it']} derived artifacts"
    )
    print(f"  closed already: {len(body['already_closed'])}")
    print(f"  remaining chain: {len(body['remaining_chain'])} steps")
    for refusal in body["refusals"]:
        print(f"  refusal {refusal['id']}")

    if args.check:
        # Compare CONTENT, not provenance.  The question --check asks is
        # "does this artifact still reproduce from its inputs", and the commit
        # it was taken at is history rather than an input -- comparing it made
        # the check fail on every later commit, which is a check that can only
        # ever be red.
        if not args.output.exists():
            print(f"{args.output} does not exist")
            return 1
        retained = json.loads(args.output.read_text())
        retained.pop("git", None)
        candidate = json.loads(rendered)
        candidate.pop("git", None)
        if retained != candidate:
            print(f"{args.output} does not match a fresh audit")
            return 1
        print(f"{args.output} reproduces (provenance excluded)")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"wrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
