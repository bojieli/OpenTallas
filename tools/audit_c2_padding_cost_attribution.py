#!/usr/bin/env python3
"""Which of gate C2's unexplained asymmetries are measured on a free quantity.

Gate C2 asks that the compiled deployments "hand neither side an advantage in
tile shape, column group, tile depth or DMA tile count", and fails when "any
asymmetry is unexplained".  Eight of fifteen machine pairs fail, and the
DeepSeek Flash array pair reports fourteen unexplained asymmetries.  Four of
them -- ``attention.tile_rows``, ``reduction.tile_rows``, ``route.tile_rows``
and ``vector.tile_rows`` -- are reported as "favours hbm 2.0x" on the strength
of ``issued_work``.

This tool measures whether ``issued_work`` is a cost at all in the cycle model
that C2 charges with, and records the answer.  It changes nothing.

The finding
-----------
``issued_work`` is padded work: ``tiles * tile_work`` where
``tile_work = tile_rows * tile_cols * tile_depth``
(``runtime/cycle/model.py``, ``TileMapping.issued_work``).  A wider tile pads
more, so a 1024-row tile has twice the ``issued_work`` of a 512-row tile over
the same useful work.  That is what the audit reports.

But the cycle model does not charge it.  In the generic branch of
``_compute_cycles``::

    per_tile = ceil(tile_work * _work_scale(step, family, mapping)
                    / (lanes * work_per_lane_cycle))

and ``_work_scale`` returns ``work_units / issued_work``.  Since
``issued_work == tiles * tile_work``::

    tile_work * work/(tiles * tile_work)  ==  work/tiles

so ``tile_work`` -- and with it ``tile_rows`` and every padded coordinate --
CANCELS IDENTICALLY.  The charge depends on the useful work and the tile
COUNT, not on the tile shape.

The cancellation is conditional, and that is the defect
------------------------------------------------------
``_work_scale`` returns ``1.0`` when the family's work counter is absent::

    work = self._work_units(step, family)
    if work <= 0:
        return 1.0

and only then does ``tile_work`` survive into the charge.

``FAMILY_WORK_COUNTERS`` (``runtime/cycle/machine.py``) gives attention
``attention.score_multiplications`` and ``attention.value_multiplications``,
vector ``vector.elements``, route ``route.topk_candidates``, reduction
``reduction.elements`` -- and the functional device records all of them.  The
AUDIT's synthetic step does not.  It sets ``attention.context_positions``,
which is not a work counter (it is there to give the model its reduction
depth), and for tensor operators it sets the real ``tensor.multiplications``
and ``tensor.additions``.

So in the audit the tensor family's padding correctly costs nothing, and the
other four families' padding appears to cost exactly its own ratio -- 2.0x --
because the scale silently fell back to 1.0.

What this does NOT license
--------------------------
It does not license an allowlist entry.  ``DEPLOYMENT_AUDIT_ALLOWLIST`` is
empty and ``tests/test_derive_cycle_machine.py`` pins it empty, which is the
guard against turning C2 green by citation.  An entry here would also be
reasoning from the wrong direction: the right statement is not "this
asymmetry is permitted", it is "this asymmetry was never measured on a cost".
The audit should set the work counters its own model reads, and then score
these families on cycles -- the quantity that actually costs -- instead of on
a proxy that cancels.

Nor does it clear C2.  ``comparable`` is
``not unexplained and not program_mismatch and not tile_errors``, and
``program_mismatch`` is true on this pair for a reason no allowlist and no
re-lowering can touch: 58 HBM-only ``DMA.TRANSFER`` operators carrying 99.7%
of that side's DMA payload are weight loads from HBM, and the ROM machine
reads weights in place and has no counterpart.  That is the design under
test, not an asymmetry the deployments chose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MODEL_SITE = ROOT / "runtime/cycle/model.py"
MACHINE_SITE = ROOT / "runtime/cycle/machine.py"
AUDIT_SITE = ROOT / "tools/derive_cycle_machine.py"
DEFAULT_OUTPUT = ROOT / "results/derived/c2_padding_cost_attribution_audit.json"

# The four entries reported as "favours hbm 2.0x" on issued_work.
PROXY_SCORED_FIELDS = (
    "attention.tile_rows",
    "reduction.tile_rows",
    "route.tile_rows",
    "vector.tile_rows",
)


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


def demonstrate_cancellation() -> dict[str, Any]:
    """Run the model's own arithmetic at two tile widths, counter on and off.

    This is a measurement, not an argument: the same expression the model
    evaluates, at 512 and 1024 rows, with the family work counter present and
    absent.
    """

    lanes, work_per_lane_cycle, tile_issue_cycles = 64, 1.0, 1
    tiles, tile_cols, tile_depth = 200, 64, 128
    work_units = 19_200_000 * lanes

    def charge(tile_rows: int, work: int) -> tuple[int, int]:
        tile_work = tile_rows * tile_cols * tile_depth
        issued = tiles * tile_work
        scale = 1.0 if work <= 0 else work / issued
        per_tile = max(
            math.ceil(tile_work * scale / (lanes * work_per_lane_cycle)), 1
        )
        return issued, tiles * max(per_tile, tile_issue_cycles)

    rows: list[dict[str, Any]] = []
    for tile_rows in (512, 1024):
        for present in (False, True):
            issued, cycles = charge(tile_rows, work_units if present else 0)
            rows.append(
                {
                    "tile_rows": tile_rows,
                    "family_work_counter_present": present,
                    "issued_work": issued,
                    "cycles": cycles,
                }
            )

    off = [r for r in rows if not r["family_work_counter_present"]]
    on = [r for r in rows if r["family_work_counter_present"]]
    return {
        "held_equal": {
            "useful_work_units": work_units,
            "tiles": tiles,
            "tile_cols": tile_cols,
            "tile_depth": tile_depth,
            "lanes": lanes,
            "work_per_lane_cycle": work_per_lane_cycle,
        },
        "rows": rows,
        "with_the_counter_absent": {
            "cycles_512": off[0]["cycles"],
            "cycles_1024": off[1]["cycles"],
            "ratio": off[1]["cycles"] / off[0]["cycles"],
            "reading": (
                "doubling tile_rows doubles the charge, so padding looks "
                "exactly as costly as the audit reports"
            ),
        },
        "with_the_counter_present": {
            "cycles_512": on[0]["cycles"],
            "cycles_1024": on[1]["cycles"],
            "ratio": on[1]["cycles"] / on[0]["cycles"],
            "reading": (
                "tile_work cancels and the charge is identical, so padding "
                "costs nothing"
            ),
        },
        "issued_work_doubled_either_way": (
            off[1]["issued_work"] == 2 * off[0]["issued_work"]
            and on[1]["issued_work"] == 2 * on[0]["issued_work"]
        ),
    }


def read_sources() -> dict[str, Any]:
    """Confirm each link of the chain against the source that carries it."""

    model = MODEL_SITE.read_text()
    machine = MACHINE_SITE.read_text()
    audit = AUDIT_SITE.read_text()
    return {
        "issued_work_is_tiles_times_tile_work": (
            "return self.tiles * self.tile_work" in model
        ),
        "work_scale_divides_by_issued_work": (
            "return work / issued" in model
        ),
        "work_scale_falls_back_to_one_when_the_counter_is_absent": (
            "if work <= 0:" in model and "return 1.0" in model
        ),
        "per_tile_multiplies_tile_work_by_the_scale": (
            "mapping.tile_work" in model and "self._work_scale(" in model
        ),
        "attention_work_counters": [
            "attention.score_multiplications",
            "attention.value_multiplications",
        ],
        "attention_work_counters_declared": (
            "attention.score_multiplications" in machine
        ),
        "audit_sets_context_positions_not_a_work_counter": (
            'step.counter_delta["attention.context_positions"]' in audit
        ),
        "audit_sets_the_tensor_work_counters": (
            'step.counter_delta["tensor.multiplications"]' in audit
            and 'step.counter_delta["tensor.additions"]' in audit
        ),
        "audit_sets_no_attention_work_counter": (
            'counter_delta["attention.score_multiplications"]' not in audit
        ),
        "audit_sets_no_vector_work_counter": (
            'counter_delta["vector.elements"]' not in audit
        ),
        "audit_sets_no_route_work_counter": (
            'counter_delta["route.topk_candidates"]' not in audit
        ),
        "audit_sets_no_reduction_work_counter": (
            'counter_delta["reduction.elements"]' not in audit
        ),
        "digests": {
            "runtime/cycle/model.py": sha256(MODEL_SITE),
            "runtime/cycle/machine.py": sha256(MACHINE_SITE),
            "tools/derive_cycle_machine.py": sha256(AUDIT_SITE),
        },
    }


def survey_pairs() -> dict[str, Any]:
    """How many C2 cells carry these four entries, and on what metric."""

    cells: list[dict[str, Any]] = []
    for path in sorted((ROOT / "results/derived").glob("*_machine_pair.json")):
        body = json.loads(path.read_text())
        audit = body.get("deployment_audit") or {}
        if audit.get("comparable") is not False:
            continue
        unexplained = list(audit.get("unexplained_asymmetries") or [])
        proxy = [f for f in PROXY_SCORED_FIELDS if f in unexplained]
        by_field = {
            f"{a.get('family')}.{a.get('field')}": a
            for a in (audit.get("asymmetries") or [])
        }
        cells.append(
            {
                "artifact": str(path.relative_to(ROOT)),
                "reason": audit.get("reason"),
                "unexplained_count": len(unexplained),
                "proxy_scored_present": proxy,
                "metric_each_entry_was_scored_on": {
                    f: by_field.get(f, {}).get("enters")
                    for f in proxy
                },
                "magnitude_each_entry_reports": {
                    f: by_field.get(f, {}).get("magnitude_x") for f in proxy
                },
            }
        )
    with_proxy = [c for c in cells if c["proxy_scored_present"]]
    return {
        "failing_cells": len(cells),
        "cells_carrying_the_four_proxy_scored_entries": len(with_proxy),
        "cells": cells,
    }


def build() -> dict[str, Any]:
    demo = demonstrate_cancellation()
    sources = read_sources()
    survey = survey_pairs()
    counter_absent_doubles = (
        abs(demo["with_the_counter_absent"]["ratio"] - 2.0) < 1e-9
    )
    counter_present_cancels = (
        abs(demo["with_the_counter_present"]["ratio"] - 1.0) < 1e-9
    )
    established = bool(
        counter_absent_doubles
        and counter_present_cancels
        and sources["issued_work_is_tiles_times_tile_work"]
        and sources["work_scale_falls_back_to_one_when_the_counter_is_absent"]
        and sources["audit_sets_no_attention_work_counter"]
    )
    return {
        "schema": "opentallas.derived.c2_padding_cost_attribution.v1",
        "gate": "C2 (configs/gates/redesign_gates.json)",
        "generated_by": "tools/audit_c2_padding_cost_attribution.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
        "question": (
            "are C2's attention/reduction/route/vector tile_rows asymmetries "
            "measured on a quantity the cycle model charges for?"
        ),
        "answer": "no" if established else "not established by this run",
        "verdict": "measured-on-a-free-quantity" if established else "inconclusive",
        "cancellation_demonstrated": demo,
        "chain": sources,
        "c2_survey": survey,
        "refusals": [
            {
                "id": "no-allowlist-entry",
                "what": (
                    "these four entries must not be added to "
                    "DEPLOYMENT_AUDIT_ALLOWLIST"
                ),
                "why": (
                    "the allowlist is empty and a test pins it empty, which is "
                    "the guard against turning C2 green by citation; and the "
                    "true statement is not 'this asymmetry is permitted' but "
                    "'this asymmetry was never measured on a cost'"
                ),
            },
            {
                "id": "not-a-clearance-of-c2",
                "what": "this does not make the failing pair comparable",
                "why": (
                    "comparable ANDs in program_mismatch, which is true here "
                    "because 58 HBM-only DMA.TRANSFER operators carrying 99.7% "
                    "of that side's DMA payload are weight loads the ROM "
                    "machine does not need -- the design under test, not a "
                    "lowering choice"
                ),
            },
        ],
        "what_would_fix_it": (
            "set the family work counters the model already reads "
            "(attention.score_multiplications and "
            "attention.value_multiplications, vector.elements, "
            "route.topk_candidates, reduction.elements) on the audit's "
            "synthetic step, so _work_scale is meaningful and these families "
            "are scored on cycles instead of on issued_work"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    body = build()
    rendered = json.dumps(body, indent=2, sort_keys=True) + "\n"

    print(f"verdict: {body['verdict']}")
    demo = body["cancellation_demonstrated"]
    print(
        "  counter absent : {:,} -> {:,} cycles ({:.1f}x)".format(
            demo["with_the_counter_absent"]["cycles_512"],
            demo["with_the_counter_absent"]["cycles_1024"],
            demo["with_the_counter_absent"]["ratio"],
        )
    )
    print(
        "  counter present: {:,} -> {:,} cycles ({:.1f}x)".format(
            demo["with_the_counter_present"]["cycles_512"],
            demo["with_the_counter_present"]["cycles_1024"],
            demo["with_the_counter_present"]["ratio"],
        )
    )
    survey = body["c2_survey"]
    print(
        f"  failing cells: {survey['failing_cells']}, carrying the four "
        f"proxy-scored entries: "
        f"{survey['cells_carrying_the_four_proxy_scored_entries']}"
    )
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
