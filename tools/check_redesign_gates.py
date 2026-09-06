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
import fnmatch
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


def _oracle_of(ev: dict[str, Any]) -> tuple[Any, str | None, str | None]:
    """Read the reference oracle a rung compares against, or (None, None, None).

    Returned as (token ids, sha256 of the file on disk, the configured path).
    The digest is recomputed here rather than trusted from the record, so a
    record cannot claim agreement with an oracle that has since moved.
    """
    oracle_path = ev.get("oracle")
    if not oracle_path:
        return None, None, None
    import hashlib

    opath = REPO / oracle_path
    if not opath.exists():
        return "MISSING", None, oracle_path
    digest = hashlib.sha256(opath.read_bytes()).hexdigest()
    body = _load(opath) or {}
    ids = _dig(body, ev.get("oracle_token_field", "generated_token_ids"))
    if not isinstance(ids, list) or not ids:
        return "EMPTY", digest, oracle_path
    return ids, digest, oracle_path


def _rtl_record_problems(
    rec: dict[str, Any], ev: dict[str, Any], oracle_ids: Any, oracle_digest: str | None
) -> list[str]:
    """Every check a rung of the RTL verification ladder must survive.

    Provenance first, because a record that does not say a simulator ran, or
    that was written from a dirty tree, is not evidence whatever it claims.
    Then the rung's own required fields.  Absence of a field is a problem, not
    a pass -- that inversion is the whole point of this tool.
    """
    why: list[str] = []
    workload = ev.get("workload")
    if workload and rec.get("workload_id") != workload:
        why.append(f"workload_id {rec.get('workload_id')!r} != {workload!r}")

    execution = rec.get("execution") or {}
    if not execution.get("simulator"):
        why.append("execution.simulator absent -- nothing states that RTL ran")
    cycles = execution.get("simulated_cycles")
    if not isinstance(cycles, int) or cycles <= 0:
        why.append(f"execution.simulated_cycles is {cycles!r}, must be a positive int")
    evidence = str(execution.get("evidence_class", ""))
    if "rtl" not in evidence.lower():
        why.append(f"execution.evidence_class {evidence!r} does not name RTL simulation")
    if _dig(rec, "git.worktree_dirty") is not False:
        why.append("git.worktree_dirty is not false -- the record is not source-bound")

    if oracle_ids is not None:
        # A rung may certify only a prefix of the gold sequence -- the head and
        # token rung emits the first generated id, the reduced end-to-end rung
        # emits all of them.  The count is declared per rung so a rung can
        # never quietly certify fewer tokens than it claims.
        count = ev.get("oracle_token_count")
        if isinstance(count, int) and count > 0:
            oracle_ids = list(oracle_ids)[:count]
        oracle = rec.get("oracle") or {}
        if oracle.get("agreement") is not True:
            why.append(f"oracle.agreement is {oracle.get('agreement')!r}")
        if oracle_digest and oracle.get("artifact_sha256") != oracle_digest:
            why.append("oracle.artifact_sha256 does not match the oracle on disk")
        emitted = rec.get("record_token_ids")
        if emitted is None:
            why.append("record_token_ids absent -- no RTL-emitted ids to compare")
            emitted = oracle.get("generated_token_ids")
        if list(emitted or []) != list(oracle_ids):
            why.append(f"token ids {emitted!r} != oracle {oracle_ids!r}")

    for req in ev.get("require_fields", []):
        got = _dig(rec, req["field"])
        if got != req.get("equals"):
            why.append(f"{req['field']} is {got!r}, want {req.get('equals')!r}")
    for req in ev.get("require_min", []):
        got = _dig(rec, req["field"])
        if not isinstance(got, (int, float)) or got < req["at_least"]:
            why.append(f"{req['field']} is {got!r}, want >= {req['at_least']}")
    return why


def evaluate(gate: dict[str, Any], board: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ev = gate.get("evaluator") or {}
    kind = ev.get("type")

    if kind == "gate_rollup":
        # G1 is a roll-up, not a run.  The industry does not sign off an
        # accelerator by simulating a whole network; it closes a verification
        # pyramid and composes.  So this gate passes only when every named rung
        # passes AND a composition certificate binds them together.  Each rung
        # is re-evaluated here rather than read from a stored board, so the
        # roll-up can never be greener than the evidence under it right now.
        required = list(ev.get("requires", []))
        by_id = {g["id"]: g for g in (board or [])}
        missing_spec = [rid for rid in required if rid not in by_id]
        if missing_spec:
            return _fail(f"roll-up names gate(s) that do not exist: {missing_spec}")
        failing = []
        for rid in required:
            outcome = evaluate(by_id[rid], board)
            if outcome["status"] != "pass":
                failing.append(f"{rid}: {outcome['why'][:110]}")
        cert = ev.get("certificate")
        if cert:
            cbody = _load(REPO / cert)
            if cbody is None:
                failing.append(f"composition certificate {cert} is absent or unreadable")
            else:
                for req in ev.get("certificate_requires", []):
                    got = _dig(cbody, req["field"])
                    if got != req.get("equals"):
                        failing.append(
                            f"{cert}: {req['field']} is {got!r}, want {req.get('equals')!r}"
                        )
        if failing:
            # The certificate contributes one requirement per certificate_requires
            # entry, not one in total, so the denominator has to count them.  It
            # read "9 of 7" while three certificate fields were failing.
            total = len(required) + len(ev.get("certificate_requires", []) if cert else [])
            return _fail(
                f"{len(failing)} of {total} requirement(s) unmet: "
                + "; ".join(failing[:3])
                + ("; ..." if len(failing) > 3 else "")
            )
        return _pass(
            f"all {len(required)} rung(s) pass and {cert} binds them"
            if cert else f"all {len(required)} rung(s) pass"
        )

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

    if "glob" in ev:
        paths = _matches(ev["glob"])
    elif "artifact" in ev:
        # A rung that names ONE artifact by path.  Named rather than globbed so
        # a rung cannot be satisfied by some other file that happens to match.
        one = REPO / ev["artifact"]
        paths = [one] if one.exists() else []
    else:
        paths = []

    if kind == "routed_netlist_contains":
        # G2 names three things that must sit in ONE routed netlist: the
        # datapath array, the memory system and the microsequencer, with DRC 0
        # and antenna 0.  The first evaluator passed on a directory NAME
        # containing "microsequencer", so the day the front-end block alone
        # was routed (results/physical_abi3/asap7/a3_microsequencer) it would
        # have gone green on a third of its statement -- the not_evaluable
        # defect again.  This one reads each record: the sources it was
        # synthesised from must cover every named component, the memory
        # system must be present as placed macros (the vehicle memories are
        # macro abstracts, docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2), and
        # the route must be clean.  A block that is only part of the control
        # plane fails, and says which parts it lacks.
        if not paths:
            return _fail(f"no routed block matches {ev['glob']}")
        groups: dict[str, list[str]] = ev["require_sources_matching"]
        macros_min = int(ev.get("require_macro_count_min", 1))
        reasons: list[str] = []
        for path in paths:
            rel = path.relative_to(REPO)
            body = _load(path)
            if body is None:
                reasons.append(f"{rel}: unreadable")
                continue
            pnr = body.get("place_and_route")
            if not isinstance(pnr, dict) or body.get("flow_completed") is not True:
                reasons.append(f"{rel}: no completed place-and-route stage")
                continue
            sources = [
                entry.get("path", "")
                for entry in ((body.get("design") or {}).get("sources") or [])
                if isinstance(entry, dict)
            ]
            missing = [
                name
                for name, patterns in groups.items()
                if not any(
                    fnmatch.fnmatch(src, pattern)
                    for src in sources
                    for pattern in patterns
                )
            ]
            metrics = pnr.get("metrics") or {}

            def number(key: str) -> float | None:
                value = metrics.get(key)
                return float(value) if isinstance(value, (int, float)) else None

            macro_count = number("macro_count")
            lacks: list[str] = []
            if missing:
                lacks.append("no " + ", no ".join(missing) + " among its sources")
            if macro_count is None or macro_count < macros_min:
                lacks.append(
                    f"no memory system (macro_count {macro_count}, need >= {macros_min})"
                )
            drc = number("drc_errors")
            ant_nets = number("antenna_violating_nets")
            ant_pins = number("antenna_violating_pins")
            if drc != 0 or ant_nets != 0 or ant_pins != 0:
                lacks.append(
                    f"not clean (drc {drc}, antenna nets {ant_nets}, pins {ant_pins})"
                )
            if lacks:
                reasons.append(f"{rel}: " + "; ".join(lacks))
                continue
            return _pass(
                f"{rel}: one routed netlist with {', '.join(groups)} among its "
                f"sources, {macro_count:g} placed macro(s), DRC 0, antenna 0"
            )
        return _fail(
            f"{len(paths)} routed block(s) and none holds {', '.join(groups)} and "
            "the memory system in one clean netlist: "
            + "; ".join(reasons[:4])
            + ("; ..." if len(reasons) > 4 else "")
        )

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
        return _fail(
            f"no artifact matches {ev['glob']}"
            if "glob" in ev
            else f"artifact {ev.get('artifact')} does not exist"
        )

    if kind in ("token_record", "rtl_records"):
        # A rung of the RTL verification ladder.  G1's first evaluator was
        # artifact_field over results/rtl/*token*.json requiring only
        # record.oracle.agreement == true: it checked neither storage class,
        # nor the workload, nor that any RTL ran, so any file matching that
        # glob would have turned a terminal gate green.  That is the
        # not_evaluable defect the redesign plan exists to remove, and the
        # third instance on this board -- G2 passed on a directory NAME, G4 on
        # half its statement.
        #
        # Every rung carries the same provenance spine (a named simulator, a
        # positive simulated_cycles, an evidence_class naming RTL simulation, a
        # clean worktree) plus whatever that rung asserts, and must do so for
        # EACH declared storage class.  Records live one per file or several in
        # a "records" list.
        want_classes = [str(c) for c in ev.get("require_storage_classes", [])]
        oracle_ids, oracle_digest, oracle_path = _oracle_of(ev)
        if oracle_ids == "MISSING":
            return _fail(f"oracle artifact {oracle_path} does not exist")
        if oracle_ids == "EMPTY":
            return _fail(
                f"oracle artifact {oracle_path} carries no token id list at "
                f"{ev.get('oracle_token_field', 'generated_token_ids')}"
            )
        found: dict[str, list[str]] = {}
        problems: list[str] = []
        for path in paths:
            body = _load(path)
            if body is None:
                problems.append(f"{path.relative_to(REPO)}: unreadable")
                continue
            records = body.get("records")
            if not isinstance(records, list):
                records = [body.get("record", body)]
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                rel = str(path.relative_to(REPO))
                klass = rec.get("storage_class")
                if klass not in want_classes:
                    problems.append(
                        f"{rel}: storage_class {klass!r} is not one of {want_classes}"
                    )
                    continue
                why = _rtl_record_problems(rec, ev, oracle_ids, oracle_digest)
                if why:
                    problems.append(f"{rel} [{klass}]: " + "; ".join(why))
                else:
                    found.setdefault(klass, []).append(rel)
        missing = [c for c in want_classes if c not in found]
        if missing or not found:
            detail = "; ".join(problems[:3]) if problems else "no conforming record"
            return _fail(
                f"no conforming record for storage class(es) {missing or want_classes}: "
                + detail
                + ("; ..." if len(problems) > 3 else "")
            )
        return _pass(
            "conforming records on "
            + ", ".join(f"{c} ({found[c][0]})" for c in want_classes)
            + (f"; ids match {oracle_path}" if oracle_path else "")
        )

    if kind == "artifact_field":
        want = ev["require"]
        also = ev.get("also_require")
        # An optional second field carrying the artifact's own reason.  When
        # it is configured, an artifact that CARRIES the required field with
        # the wrong value fails the gate on that evidence -- the reason it
        # states -- rather than on the absence message below, which is for
        # artifacts that never wrote the field at all.
        reason_field = ev.get("reason_field")
        if ev.get("require_all"):
            # Every matched artifact must satisfy the field, not the first
            # that does.  Without this, C2 would go green the day ONE derived
            # pair is re-emitted comparable while fourteen others are not --
            # the verifier of the C2 audit named that exactly.
            failing: list[str] = []
            for path in paths:
                body = _load(path)
                got = _dig(body, want["field"]) if body else None
                ok = got == want.get("equals") and (
                    not also or _dig(body, also["field"]) == also.get("equals")
                )
                if not ok:
                    reason = (
                        _dig(body, reason_field) if body and reason_field else None
                    )
                    failing.append(
                        f"{path.relative_to(REPO)}"
                        + (f": {str(reason)[:120]}" if reason else "")
                    )
            if failing:
                # Lead with a verdict that examined evidence; an artifact whose
                # reason is that nothing was built is a weaker witness than one
                # that compared two deployments and found them unequal.  The
                # single-artifact path below sorts the same way.
                failing.sort(key=lambda text: ("no deployment built" in text, text))
                return _fail(
                    f"{len(failing)} of {len(paths)} artifact(s) fail "
                    f"{want['field']} == {want.get('equals')}: "
                    + "; ".join(failing[:2])
                    + ("; ..." if len(failing) > 2 else "")
                )
            return _pass(
                f"all {len(paths)} artifact(s) have {want['field']} == {want.get('equals')}"
            )
        verdicts: list[tuple[Path, Any, Any]] = []
        for path in paths:
            body = _load(path)
            if body is None:
                continue
            got = _dig(body, want["field"])
            if got != want.get("equals"):
                if reason_field and got is not None:
                    verdicts.append((path, got, _dig(body, reason_field)))
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
        if verdicts:
            # Lead with a verdict that examined evidence; an artifact whose
            # reason is that nothing was built is a weaker witness than one
            # that compared two deployments and found them unequal.
            verdicts.sort(
                key=lambda v: (
                    "no deployment built" in str(v[2] or ""),
                    str(v[0]),
                )
            )
            path, got, reason = verdicts[0]
            text = f"{path.relative_to(REPO)}: {want['field']} == {got!r}"
            if reason:
                text += f" -- {str(reason)[:1200]}"
            if len(verdicts) > 1:
                text += f"; {len(verdicts) - 1} more artifact(s) carry a failing verdict"
            absent = len(paths) - len(verdicts)
            if absent:
                text += f"; {absent} artifact(s) lack {want['field']}"
            return _fail(text)
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
        outcome = evaluate(gate, spec["gates"])
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
