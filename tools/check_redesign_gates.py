#!/usr/bin/env python3
"""Evaluate the redesign plan's gates, and fail when they are not met.

Why this exists
---------------
``docs/PERFORMANCE_DESIGN_POSTMORTEM.md`` establishes that the previous
programme's performance gate had two states, ``not_evaluable`` and ``pass``,
with no reachable ``fail``.  It stayed ``not_evaluable`` for the life of the
project while the machine drifted four orders of magnitude from the north star,
and every other gate stayed green.  A gate that cannot fail is a note.

So the single rule this tool enforces is the inversion of that defect:

    **Absence of evidence is FAIL, never not_evaluable.**

A gate with no artifact fails.  A gate whose artifact lacks the field fails.  A
gate whose budget was never frozen fails, and says so in those words rather than
reporting itself unevaluable and moving on.  The board is expected to be mostly
red today; that is the point, and a red board that is true is worth more than a
green one that is not.

Usage
-----
    PYTHONPATH=. python3 tools/check_redesign_gates.py
    PYTHONPATH=. python3 tools/check_redesign_gates.py --out results/gates/redesign_gates.json

Exit status is 1 when any TERMINAL gate fails, so this can gate a release
without gating ordinary work.  ``--strict`` extends that to every gate.
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_GATES = REPO / "configs/gates/redesign_gates.json"
SCHEMA = "opentallas.gates.redesign_result.v1"


def _dig(body: Any, dotted: str) -> Any:
    """Follow a dotted path, returning ``None`` rather than raising."""
    node = body
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _matches(pattern: str) -> list[Path]:
    return sorted(Path(p) for p in glob.glob(str(REPO / pattern), recursive=True))


def _load(path: Path) -> dict[str, Any] | None:
    try:
        body = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _fail(why: str) -> dict[str, Any]:
    return {"status": "fail", "why": why}


def _pass(why: str) -> dict[str, Any]:
    return {"status": "pass", "why": why}


def evaluate(gate: dict[str, Any]) -> dict[str, Any]:
    ev = gate.get("evaluator") or {}
    kind = ev.get("type")

    if kind == "command":
        argv = list(ev["argv"])
        try:
            done = subprocess.run(
                argv, cwd=REPO, capture_output=True, text=True, timeout=600
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return _fail(f"{' '.join(argv)} could not run: {exc}")
        if done.returncode != int(ev.get("expect_exit", 0)):
            tail = (done.stderr or done.stdout or "").strip().splitlines()
            return _fail(
                f"{' '.join(argv)} exited {done.returncode}"
                + (f": {tail[-1][:160]}" if tail else "")
            )
        return _pass(f"{' '.join(argv)} exited 0")

    if kind == "tpot_budget":
        # The first version of this gate searched for the budget field's NAME
        # and passed on finding its own specification file.  This one reads
        # values, and every row needs both a budget and a qualified
        # measurement inside tolerance.  Nothing here can pass on absence.
        budget = _load(REPO / ev["budget"])
        if budget is None:
            return _fail(f"budget file {ev['budget']} is unreadable")
        tolerance = float(budget.get("tolerance_x", 1.0))
        contract = budget.get("measurement_contract", {})
        records = []
        for path in _matches(contract.get("record_glob", "results/tpot/*.json")):
            body = _load(path)
            if body is None:
                continue
            missing = [f for f in contract.get("required_fields", []) if f not in body]
            if missing or body.get("correctness_qualified") is not True:
                continue
            records.append((path, body))
        rows = budget.get("budgets", [])
        unbudgeted = [r for r in rows if r.get("budget_tpot_s") in (None, 0)]
        failures: list[str] = []
        passes: list[str] = []
        for row in rows:
            key = f"{row.get('model')}/{row.get('storage_class')}"
            if row in unbudgeted:
                failures.append(f"{key}: no budget")
                continue
            matching = [
                (p, b) for p, b in records
                if b.get("model") == row.get("model")
                and b.get("storage_class") == row.get("storage_class")
                and int(b.get("batch_size", -1)) == int(row.get("batch_size", -2))
            ]
            if not matching:
                failures.append(f"{key}: no correctness-qualified measurement")
                continue
            limit = float(row["budget_tpot_s"]) * tolerance
            best = min(float(b["tpot_s"]) for _, b in matching)
            if best > limit:
                failures.append(
                    f"{key}: measured {best*1e6:.1f} us over {limit*1e6:.1f} us"
                )
            else:
                passes.append(f"{key}: {best*1e6:.1f} us <= {limit*1e6:.1f} us")
        status = budget.get("status", "frozen")
        if failures:
            return _fail(
                f"{len(failures)} of {len(rows)} rows fail ({status} budget): "
                + "; ".join(failures[:3])
                + ("; ..." if len(failures) > 3 else "")
            )
        return _pass(
            f"all {len(rows)} rows within {tolerance:g}x of the {status} budget: "
            + "; ".join(passes[:3])
        )

    paths = _matches(ev["glob"]) if "glob" in ev else []

    if kind == "routed_blocks_include":
        if not paths:
            return _fail(f"no routed block matches {ev['glob']}")
        names = {p.parent.name for p in paths}
        wanted = [w for w in ev["require_any_named"] if any(w in n for n in names)]
        if not wanted:
            return _fail(
                f"{len(names)} routed block(s) ({', '.join(sorted(names))}) and none "
                f"is one of {', '.join(ev['require_any_named'])}"
            )
        return _pass(f"routed: {', '.join(sorted(names))}")

    if kind == "per_mac_improvement":
        # Per-MAC figures are compared only inside one view (METHODOLOGY
        # section 9: nothing is scaled across nodes), only between closed
        # routed results, and only when the candidate declares them itself
        # (tools/run_abi3_physical.py --lanes/--mac-per-cycle writes the
        # ``design`` block).  The baseline predates that block, so its figures
        # are derived here from its routed record with the MAC rate the gate
        # names -- the same arithmetic as docs/CHIP_ARCHITECTURE_DESIGN.md
        # section 8.4 (standard-cell area / MAC per cycle; closed target
        # period / MAC per cycle).
        base = _load(REPO / ev["baseline"])
        if base is None:
            return _fail(f"baseline {ev['baseline']} is unreadable")
        if not paths:
            return _fail(f"no candidate matches {ev['glob']}")
        base_view = _dig(base, "view.name")
        base_design = base.get("design") or {}
        base_mpc = base_design.get("mac_per_cycle", ev.get("baseline_mac_per_cycle"))
        try:
            base_mpc = float(base_mpc)
        except (TypeError, ValueError):
            return _fail("baseline declares no MAC per cycle and the gate names none")
        if base.get("status") != "pass" or "place_and_route" not in base:
            return _fail(f"baseline {ev['baseline']} is not a closed routed result")
        base_area = base_design.get("per_mac_area_um2")
        base_period = base_design.get("per_mac_period_ns")
        if base_area is None:
            cell_area = _dig(base, "place_and_route.metrics.standard_cell_area_um2")
            base_area = None if cell_area is None else float(cell_area) / base_mpc
        if base_period is None:
            period = _dig(base, "place_and_route.clock_period_ns")
            base_period = None if period is None else float(period) / base_mpc
        if base_area is None or base_period is None:
            return _fail(f"baseline {ev['baseline']} carries no per-MAC figures")
        reasons: list[str] = []
        best: tuple[float, float, Path] | None = None
        for path in paths:
            rel = path.relative_to(REPO)
            body = _load(path)
            if body is None:
                reasons.append(f"{rel}: unreadable")
                continue
            view = _dig(body, "view.name")
            if view != base_view:
                reasons.append(f"{rel}: view {view} is not the baseline's {base_view}")
                continue
            design = body.get("design") or {}
            area = design.get("per_mac_area_um2")
            period = design.get("per_mac_period_ns")
            if not isinstance(area, (int, float)) or not isinstance(period, (int, float)):
                reasons.append(f"{rel}: declares no per-MAC figures")
                continue
            if "place_and_route" not in body:
                reasons.append(f"{rel}: no place-and-route stage")
                continue
            if body.get("status") != "pass" or design.get("closed") is not True:
                reasons.append(
                    f"{rel}: not closed (status {body.get('status')}); "
                    f"{area:,.1f} um2 and {period:.3f} ns per MAC are what it "
                    "achieved, not a result"
                )
                continue
            area_ok = float(area) < base_area
            period_ok = float(period) < base_period
            if area_ok and period_ok:
                if best is None or float(area) < best[0]:
                    best = (float(area), float(period), path)
            else:
                reasons.append(
                    f"{rel}: per-MAC area {area:,.1f} um2 vs {base_area:,.0f}, "
                    f"period {period:.3f} ns vs {base_period:.1f}: "
                    + ("area" if not area_ok else "period")
                    + " regresses"
                )
        if best is not None:
            return _pass(
                f"{best[2].relative_to(REPO)}: per-MAC area {best[0]:,.1f} um2 < "
                f"baseline {base_area:,.0f} um2 and per-MAC period {best[1]:.3f} ns < "
                f"baseline {base_period:.1f} ns, both routed at {base_view}"
            )
        return _fail(
            f"{len(paths)} candidate(s) and none improves on the baseline's "
            f"{base_area:,.0f} um2 and {base_period:.1f} ns per MAC: "
            + "; ".join(reasons[:3])
            + ("; ..." if len(reasons) > 3 else "")
        )

    if not paths:
        return _fail(f"no artifact matches {ev['glob']}")

    if kind == "artifact_field":
        want = ev["require"]
        also = ev.get("also_require")
        for path in paths:
            body = _load(path)
            if body is None:
                continue
            got = _dig(body, want["field"])
            if got != want.get("equals"):
                continue
            # A second field that must hold in the SAME artifact.  Both halves
            # of a reconciliation must agree; passing on one target's regime
            # while the other's is absent would be the missing-key defect again.
            if also and _dig(body, also["field"]) != also.get("equals"):
                continue
            return _pass(
                f"{path.relative_to(REPO)}: {want['field']} == {want['equals']}"
                + (f" and {also['field']} == {also['equals']}" if also else "")
            )
        return _fail(
            f"{len(paths)} artifact(s) matched {ev['glob']} and none has "
            f"{want['field']} == {want.get('equals')}"
            + (f" with {also['field']} == {also.get('equals')}" if also else "")
        )

    if kind == "artifact_threshold":
        also = ev.get("also_require")
        rejected: list[str] = []
        best: tuple[float, Path] | None = None
        for path in paths:
            body = _load(path)
            got = _dig(body, ev["field"]) if body else None
            if not isinstance(got, (int, float)):
                continue
            if also and _dig(body, also["field"]) != also.get("equals"):
                rejected.append(
                    f"{path.relative_to(REPO)}: {also['field']} != {also.get('equals')}"
                )
                continue
            if best is None or got > best[0]:
                best = (float(got), path)
        if best is None:
            return _fail(
                f"{len(paths)} artifact(s) matched and none carries {ev['field']}"
                + (
                    f" with {also['field']} == {also.get('equals')}: " + "; ".join(rejected[:3])
                    if rejected
                    else ""
                )
            )
        if best[0] < float(ev["min"]):
            return _fail(
                f"{best[1].relative_to(REPO)}: {ev['field']} = {best[0]:g}, "
                f"below the required {ev['min']:g}"
            )
        return _pass(f"{best[1].relative_to(REPO)}: {ev['field']} = {best[0]:g}")

    if kind == "plausibility_ceiling":
        worst: tuple[float, Path] | None = None
        seen = 0
        for path in paths:
            body = _load(path)
            got = _dig(body, ev["field"]) if body else None
            if isinstance(got, (int, float)):
                seen += 1
                if worst is None or got > worst[0]:
                    worst = (float(got), path)
        if seen == 0:
            return _fail(
                f"{len(paths)} cycle artifact(s) and none carries {ev['field']}; "
                "a run that cannot state its own bandwidth floor cannot be believed"
            )
        if worst and worst[0] > float(ev["max"]):
            return _fail(
                f"{worst[1].relative_to(REPO)} sits {worst[0]:,.0f}x above its own "
                f"floor, over the {ev['max']:g}x ceiling"
            )
        return _pass(
            f"{seen} of {len(paths)} artifact(s) state a floor; worst is "
            f"{worst[0]:,.2f}x" if worst else f"{seen} artifact(s) checked"
        )

    return _fail(f"gate has no runnable evaluator (type {kind!r})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gates", type=Path, default=DEFAULT_GATES)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--strict", action="store_true",
        help="exit nonzero when ANY gate fails, not only a terminal one",
    )
    args = parser.parse_args(argv)

    spec = json.loads(args.gates.read_text())
    results = []
    for gate in spec["gates"]:
        outcome = evaluate(gate)
        results.append({
            "id": gate["id"], "kind": gate["kind"],
            "statement": gate["statement"], "fails_when": gate["fails_when"],
            **outcome,
        })

    width = max(len(r["statement"]) for r in results)
    width = min(width, 78)
    print(f"{'gate':>4}  {'kind':<10} {'status':<6}  why")
    print("-" * 100)
    for r in results:
        print(f"{r['id']:>4}  {r['kind']:<10} {r['status']:<6}  {r['why'][:78]}")

    terminal = [r for r in results if r["kind"] == "terminal"]
    failed_terminal = [r for r in terminal if r["status"] == "fail"]
    failed_any = [r for r in results if r["status"] == "fail"]
    print("-" * 100)
    print(
        f"{len(results) - len(failed_any)} of {len(results)} gates pass; "
        f"{len(terminal) - len(failed_terminal)} of {len(terminal)} terminal gates pass"
    )
    if failed_terminal:
        print(
            "TERMINAL GATES FAILING: "
            + ", ".join(r["id"] for r in failed_terminal)
            + " -- the release criteria of docs/OPENTALLAS_REDESIGN_PLAN.md are not met"
        )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "schema": SCHEMA,
            "plan": spec["plan"],
            "principle": spec["principle"],
            "gate_count": len(results),
            "passing": len(results) - len(failed_any),
            "terminal_passing": len(terminal) - len(failed_terminal),
            "gates": results,
        }, indent=2, sort_keys=True) + "\n")
        print(f"wrote {args.out}")

    if args.strict:
        return 1 if failed_any else 0
    return 1 if failed_terminal else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
