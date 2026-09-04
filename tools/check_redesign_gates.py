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

    if kind == "frozen_budget":
        field = ev["field"]
        found: list[str] = []
        for pattern in ev["search"]:
            for path in _matches(pattern):
                try:
                    if field in path.read_text():
                        found.append(str(path.relative_to(REPO)))
                except OSError:
                    continue
        if not found:
            return _fail(
                f"no {field} is frozen anywhere in {', '.join(ev['search'])}; "
                "a missing budget is a failed gate, not a deferred one"
            )
        return _pass(f"{field} present in {len(found)} file(s): {found[0]}")

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
        base = _load(REPO / ev["baseline"])
        if base is None:
            return _fail(f"baseline {ev['baseline']} is unreadable")
        if not paths:
            return _fail(f"no candidate matches {ev['glob']}")
        return _fail(
            f"{len(paths)} candidate(s) found but per-MAC comparison needs a declared "
            "MAC count in each pnr.json; none declares one yet"
        )

    if not paths:
        return _fail(f"no artifact matches {ev['glob']}")

    if kind == "artifact_field":
        want = ev["require"]
        for path in paths:
            body = _load(path)
            if body is None:
                continue
            got = _dig(body, want["field"])
            if got == want.get("equals"):
                return _pass(
                    f"{path.relative_to(REPO)}: {want['field']} == {want['equals']}"
                )
        return _fail(
            f"{len(paths)} artifact(s) matched {ev['glob']} and none has "
            f"{want['field']} == {want.get('equals')}"
        )

    if kind == "artifact_threshold":
        best: tuple[float, Path] | None = None
        for path in paths:
            body = _load(path)
            got = _dig(body, ev["field"]) if body else None
            if isinstance(got, (int, float)) and (best is None or got > best[0]):
                best = (float(got), path)
        if best is None:
            return _fail(
                f"{len(paths)} artifact(s) matched and none carries {ev['field']}"
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
