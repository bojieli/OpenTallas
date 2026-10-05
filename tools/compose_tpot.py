#!/usr/bin/env python3
"""Compose a TPOT record from measured cycles, or refuse and say why.

Why this exists
---------------
Gate G3 fails six of six rows with "no correctness-qualified measurement", and
the reason is plain: ``results/tpot/`` does not exist.  No TPOT has ever been
measured on this design, so every performance figure the programme has
published is analytical.

The gate's own measurement contract
(``configs/gates/tpot_budget_provisional.json#measurement_contract``) says what
a record must be, and it is deliberately **not** a wall clock:

    tpot_s is architectural and COMPOSED, not wall-clocked: the per-operator
    and per-boundary cycle counts are MEASURED in RTL (the same measurements
    gate G4 calibrates the cycle model against), and they are summed over the
    issue trace gate G1e certified equal to the golden model's, element for
    element, on the admitted target timebase.

That composition is only sound when four things hold at once, and this tool
exists to refuse loudly when any of them does not:

1. the G1 composition certificate passes -- otherwise the rate would be
   published for a token sequence the ladder did not prove;
2. every operator class the certified trace issues has a MEASURED cycle count
   -- otherwise the sum silently omits work;
3. the dependent boundary is measured -- otherwise the boundary term is an
   assumption wearing a measurement's clothes;
4. nothing the record binds has drifted.

A composer that emits a number when any of those is false is exactly the
defect this board was rebuilt to remove: the previous programme's performance
gate had two states, ``not_evaluable`` and ``pass``, with no reachable
``fail``.  So the refusals here are the feature, and the happy path is the
afterthought.  Each refusal names its category, the artifact it read, and what
would have to be true instead -- because "no measurement" is not an answer,
and "which measurement is missing" is.

Usage
-----
    PYTHONPATH=. python3 tools/compose_tpot.py
    PYTHONPATH=. python3 tools/compose_tpot.py --out results/tpot
    PYTHONPATH=. python3 tools/compose_tpot.py --json

Exit status is 1 when no row could be composed, so this can gate a release
without gating ordinary work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BUDGET = REPO / "configs/gates/tpot_budget_provisional.json"
CERTIFICATE = REPO / "results/rtl/abi3_g1_composition_certificate.json"
TRACE = REPO / "results/rtl/abi3_g1e_control_end_to_end.json"
CALIBRATION = REPO / "results/derived/qwen3_n5_design_target_calibration.json"
SCHEMA = "opentallas.tpot.composed.v1"


def _load(path: Path) -> dict[str, Any] | None:
    try:
        body = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _refusal(category: str, artifact: Path, why: str, would_need: str) -> dict[str, Any]:
    """A refusal is evidence too, so it carries the same provenance a record does."""
    return {
        "composed": False,
        "refused": True,
        "category": category,
        "artifact": _rel(artifact),
        "artifact_sha256": _digest(artifact),
        "why": why,
        "would_need": would_need,
    }


def certificate_refusal() -> dict[str, Any] | None:
    """Refuse unless the G1 ladder proved the token sequence being priced."""
    body = _load(CERTIFICATE)
    if body is None:
        return _refusal(
            "certificate_absent", CERTIFICATE,
            "the composition certificate does not exist or is unreadable",
            "a passing results/rtl/abi3_g1_composition_certificate.json",
        )
    cert = body.get("certificate") or {}
    status = body.get("status")
    covered = cert.get("every_issued_instance_covered")
    uncovered = cert.get("uncovered_instance_count")
    ids_match = cert.get("token_ids_match_oracle")
    if status == "pass" and covered is True and uncovered == 0 and ids_match is True:
        return None
    parts = []
    if status != "pass":
        parts.append(f"status is {status!r}")
    if covered is not True:
        parts.append(f"every_issued_instance_covered is {covered!r}")
    if uncovered:
        parts.append(f"{uncovered:,} issued instance(s) are not in a class G1a proved bit-exact")
    if ids_match is not True:
        parts.append(f"token_ids_match_oracle is {ids_match!r}")
    return _refusal(
        "certificate_failing", CERTIFICATE,
        "; ".join(parts),
        "the G1 ladder closed: every issued instance covered by a rung that proved it, "
        "and the emitted token ids equal the oracle's",
    )


def boundary_refusal() -> dict[str, Any] | None:
    """Refuse unless the dependent boundary is an RTL measurement.

    The model charges a boundary whether or not one was measured, so composing
    over an unmeasured boundary would publish an assumption as a measurement --
    rule R13 in the post-mortem, in its purest form.
    """
    body = _load(CALIBRATION)
    if body is None:
        return _refusal(
            "boundary_absent", CALIBRATION,
            "the calibration artifact does not exist or is unreadable",
            "a calibration whose boundary block carries an RTL measurement",
        )
    boundary = (body.get("calibration") or {}).get("boundary") or {}
    if boundary.get("measured") is True and boundary.get("rtl_measured_boundary_cycles"):
        return None
    return _refusal(
        "boundary_unmeasured", CALIBRATION,
        f"calibration.boundary.measured is {boundary.get('measured')!r} and "
        f"rtl_measured_boundary_cycles is {boundary.get('rtl_measured_boundary_cycles')!r}"
        + (f" -- {boundary.get('why_unmeasured')}" if boundary.get("why_unmeasured") else ""),
        "a two-tile dependent chain simulated on both simulators, its measured boundary "
        "replacing both the model's charge and the design's withdrawn figure "
        "(docs/CHIP_ARCHITECTURE_DESIGN.md section 13 item 13)",
    )


def trace_records() -> list[dict[str, Any]]:
    body = _load(TRACE)
    if body is None:
        return []
    records = body.get("records")
    if not isinstance(records, list):
        records = [body.get("record", body)]
    return [r for r in records if isinstance(r, dict)]


def trace_refusal(record: dict[str, Any]) -> dict[str, Any] | None:
    """Refuse unless this store's trace was certified equal to the model's."""
    trace = record.get("trace") or {}
    if trace.get("equals_golden") is True and trace.get("divergence_index") is None:
        return None
    return _refusal(
        "trace_uncertified", TRACE,
        f"trace.equals_golden is {trace.get('equals_golden')!r} and "
        f"divergence_index is {trace.get('divergence_index')!r}",
        "an issue trace equal to the golden model's element for element",
    )


def coverage_refusal(record: dict[str, Any], measured: dict[tuple[int, int, int], int]) -> dict[str, Any] | None:
    """Refuse unless every class the trace issues has a measured cycle count.

    Summing over a trace while silently skipping a class it issues understates
    the total by exactly the work nobody measured, which is the failure mode
    that is hardest to see in a finished number.
    """
    census = record.get("issue_census") or {}
    rows = census.get("rows") or []
    if not rows:
        return _refusal(
            "trace_census_absent", TRACE,
            "the record carries no issue census, so there is nothing to sum over",
            "an issue census enumerating every class the workload issues",
        )
    missing = [
        r for r in rows
        if (int(r.get("family", -1)), int(r.get("sub", -1)), int(r.get("descriptor_id", -1)))
        not in measured
    ]
    if not missing:
        return None
    named = ", ".join(
        f"family {r.get('family')} sub {r.get('sub')} descriptor {r.get('descriptor_id')} "
        f"({r.get('instances')} instance(s))"
        for r in missing[:3]
    )
    total_instances = sum(int(r.get("instances", 0)) for r in missing)
    return _refusal(
        "operator_cycles_unmeasured", TRACE,
        f"{len(missing)} of {len(rows)} issued class(es) have no RTL-measured cycle count, "
        f"covering {total_instances:,} issued instance(s): {named}"
        + ("; ..." if len(missing) > 3 else ""),
        "an RTL measurement of the cycles each issued operator class costs",
    )


def measured_operator_cycles() -> dict[tuple[int, int, int], int]:
    """Per-class measured cycles, keyed by (family, sub, descriptor_id).

    Deliberately empty until a campaign publishes per-class cycles.  An empty
    map is not an error here: it makes ``coverage_refusal`` name every class,
    which is the honest report while the measurement does not exist.
    """
    return {}


def compose(record: dict[str, Any], boundary_cycles: int, clock_hz: float,
            measured: dict[tuple[int, int, int], int]) -> dict[str, Any]:
    """Sum measured cycles over the certified trace.  Reached only when nothing refused."""
    census = record.get("issue_census") or {}
    rows = census.get("rows") or []
    operator_cycles = 0
    for row in rows:
        key = (int(row["family"]), int(row["sub"]), int(row["descriptor_id"]))
        operator_cycles += measured[key] * int(row["instances"])
    boundaries = sum(int(r.get("instances", 0)) for r in rows)
    total = operator_cycles + boundaries * boundary_cycles
    return {
        "composed": True,
        "refused": False,
        "tpot_s": total / clock_hz,
        "total_cycles": total,
        "operator_cycles": operator_cycles,
        "boundary_cycles_total": boundaries * boundary_cycles,
        "boundary_cycles_each": boundary_cycles,
        "boundary_count": boundaries,
        "clock_hz": clock_hz,
    }


def compose_all() -> dict[str, Any]:
    budget = _load(BUDGET) or {}
    contract = budget.get("measurement_contract") or {}
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "contract": {
            "source": _rel(BUDGET),
            "sha256": _digest(BUDGET),
            "required_fields": contract.get("required_fields"),
            "rule": contract.get("rule"),
        },
        "inputs": {
            name: {"path": _rel(p), "sha256": _digest(p), "exists": p.exists()}
            for name, p in (
                ("certificate", CERTIFICATE),
                ("trace", TRACE),
                ("calibration", CALIBRATION),
            )
        },
        "rows": [],
    }

    # The two gate-wide refusals are checked once: neither depends on a store.
    gate_refusals = [r for r in (certificate_refusal(), boundary_refusal()) if r]
    measured = measured_operator_cycles()

    records = {r.get("storage_class"): r for r in trace_records()}
    for row in budget.get("budgets", []):
        model = row.get("model")
        storage = row.get("storage_class")
        entry: dict[str, Any] = {
            "model": model,
            "storage_class": storage,
            "batch_size": row.get("batch_size"),
            "context_tokens": row.get("context_tokens"),
            "budget_tpot_s": row.get("budget_tpot_s"),
            "composition_certificate": _rel(CERTIFICATE),
            "issue_trace_record": _rel(TRACE),
            "cycle_record": _rel(CALIBRATION),
        }
        refusals = list(gate_refusals)
        record = records.get(storage)
        if record is None or record.get("workload_id") is None:
            refusals.append(_refusal(
                "trace_absent_for_storage_class", TRACE,
                f"no certified issue trace for storage class {storage!r}",
                f"a G1e record for {storage!r}",
            ))
        else:
            if model not in str(record.get("workload_id", "")) and model != "Qwen3-8B":
                refusals.append(_refusal(
                    "trace_is_for_another_model", TRACE,
                    f"the certified trace is for workload {record.get('workload_id')!r}, "
                    f"which does not price {model!r}",
                    f"a certified trace for {model!r}",
                ))
            for check in (trace_refusal(record), coverage_refusal(record, measured)):
                if check:
                    refusals.append(check)
        if refusals:
            entry.update({
                "composed": False,
                "correctness_qualified": False,
                "tpot_s": None,
                "refusals": refusals,
            })
        else:
            boundary = (_load(CALIBRATION) or {}).get("calibration", {}).get("boundary", {})
            clock = (_load(CALIBRATION) or {}).get("calibration", {}).get("clock", {})
            entry.update(compose(
                record,
                int(boundary["rtl_measured_boundary_cycles"]),
                float(clock.get("frequency_hz", 1e9)),
                measured,
            ))
            entry["correctness_qualified"] = True
            entry["refusals"] = []
        out["rows"].append(entry)

    out["composed_count"] = sum(1 for r in out["rows"] if r.get("composed"))
    out["refused_count"] = len(out["rows"]) - out["composed_count"]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None,
                        help="directory to write one record per composed row "
                             "(nothing is written for a refused row)")
    parser.add_argument("--json", action="store_true", help="print the whole result")
    args = parser.parse_args(argv)

    result = compose_all()

    print(f"{'model':<24} {'store':<5} {'tpot_s':>12}  verdict")
    print("-" * 92)
    for row in result["rows"]:
        if row.get("composed"):
            print(f"{row['model']:<24} {row['storage_class']:<5} "
                  f"{row['tpot_s']:>12.9f}  composed")
        else:
            first = row["refusals"][0]
            print(f"{row['model']:<24} {row['storage_class']:<5} {'-':>12}  "
                  f"REFUSED [{first['category']}] {first['why'][:60]}")
    print("-" * 92)
    print(f"{result['composed_count']} of {len(result['rows'])} rows composed")

    if result["refused_count"]:
        seen: dict[str, str] = {}
        for row in result["rows"]:
            for refusal in row.get("refusals", []):
                seen.setdefault(refusal["category"], refusal["would_need"])
        print("\nWhat stands between this programme and its first measured TPOT:")
        for category, need in seen.items():
            print(f"  [{category}] {need}")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        for row in result["rows"]:
            if not row.get("composed"):
                continue
            name = f"{row['model']}_{row['storage_class']}.json".replace("/", "_")
            (args.out / name).write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))

    return 0 if result["composed_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
