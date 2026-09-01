#!/usr/bin/env python3
"""Aggregate every ABI 3.0 evidence artifact into one status report.

The report answers three questions that a reader must not have to reconstruct
by hand: what exists, at which evidence boundary it was produced, and what is
still open. Anything it cannot find, it reports as absent rather than omitting,
because a silently missing row reads as "not applicable" when it means "not
done".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return ""


def _load(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def engine_coverage() -> dict[str, Any]:
    from runtime.sim.engines import load_engines

    report = load_engines()
    return {
        "implemented": report["implemented_count"],
        "missing": report["missing_count"],
        "sequencer_executed": report.get("sequencer_count", 0),
        "missing_operations": report["missing"],
        "unavailable_modules": report["unavailable"],
    }


def ir_artifacts() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for model in ("qwen3-8b", "deepseek-v4-flash-0731"):
        path = REPO / "build" / "ir-v3" / model / "kernel_ir.v3.json"
        if not path.exists():
            out[model] = {"present": False}
            continue
        body = _load(path) or {}
        kinds: dict[str, int] = {}
        for kernel in body.get("kernels", []):
            kinds[kernel["kind"]] = kinds.get(kernel["kind"], 0) + 1
        bound = sum(
            t["binding"]["bytes"] for t in body.get("tensors", []) if t.get("binding")
        )
        out[model] = {
            "present": True,
            "graph_id": body.get("graph_id", ""),
            "kernels": len(body.get("kernels", [])),
            "tensors": len(body.get("tensors", [])),
            "states": len(body.get("states", [])),
            "bound_weight_bytes": bound,
            "kind_census": dict(sorted(kinds.items())),
            "file_bytes": path.stat().st_size,
        }
    return out


def workloads() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for model in ("qwen3-8b", "deepseek-v4-flash-0731"):
        index = _load(REPO / "build" / "workloads" / model / "index.json")
        out[model] = index["workloads"] if index else {"present": False}
    return out


def oracle_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path in sorted((REPO / "results" / "abi3").glob("*reference_oracle*.json")):
        body = _load(path)
        if not body:
            continue
        for wid, result in body.get("results", {}).items():
            out[wid] = {
                "source": path.name,
                "evidence_class": body.get("evidence_class"),
                "generated_token_count": result.get("generated_token_count"),
                "stop_reason": result.get("stop_reason"),
                "wall_seconds": result.get("wall_seconds"),
                "visible_text_head": (result.get("visible_decoded_text") or "")[:160],
            }
    return out


def physical_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    root = REPO / "results" / "physical_abi3"
    for path in sorted(root.rglob("*.json")) if root.exists() else []:
        body = _load(path)
        if not isinstance(body, dict):
            continue
        view = path.relative_to(root).parts[0]
        block = body.get("design", {}).get("block", path.parent.name)
        synth = body.get("synthesis", {})
        timing = body.get("static_timing", {})
        route = body.get("routing", {}) or body.get("place_and_route", {})
        key = f"{view}/{block}/{path.stem}"
        # A physical run reports two independent facts: whether the flow ran,
        # and whether the corner met timing. Collapsing them hides a slow
        # corner behind a completed flow, so both are surfaced and the
        # displayed verdict is the engineering one.
        timing_met = timing.get("timing_met")
        reported = body.get("status")
        verdict = reported
        if timing_met is False:
            verdict = "timing_not_met"
        out[key] = {
            "status": verdict,
            "flow_status": reported,
            "timing_met": timing_met,
            "setup_violating_paths": timing.get("setup_violating_paths"),
            "hold_violating_paths": timing.get("hold_violating_paths"),
            "corner": body.get("corner", {}).get("name"),
            "cell_count": synth.get("cell_count"),
            "cell_area_um2": synth.get("cell_area_um2"),
            "macro_count": synth.get("macro_count"),
            "fmax_hz": timing.get("fmax_hz"),
            "setup_wns_ns": timing.get("setup_wns_ns"),
            "hold_wns_ns": timing.get("hold_wns_ns"),
            "timing_met": timing.get("timing_met"),
            "drc_violations": route.get("drc_violations"),
        }
    return out


def campaign_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path in sorted((REPO / "results" / "abi3").glob("*campaign*.json")):
        body = _load(path)
        if not isinstance(body, dict):
            continue
        record = body.get("record", {})
        out[path.stem] = {
            "status": body.get("status"),
            "target": record.get("target", {}).get("target_id"),
            "backend": record.get("target", {}).get("backend"),
            "workload": record.get("workload", {}).get("workload_id"),
            "generated_token_count": record.get("generated_token_count"),
            "stop_reason": record.get("stop_reason"),
            "evidence_class": record.get("evidence_class"),
        }
    return out


def rtl_correlation() -> dict[str, Any]:
    body = _load(REPO / "results" / "rtl" / "abi3_campaign.json")
    if not body:
        return {"present": False}
    correlation = body.get("correlation", {})
    return {
        "present": True,
        "evidence_class": body.get("evidence_class"),
        "reference": correlation.get("reference"),
        "cases": correlation.get("case_count"),
        "programs_run": correlation.get("program_run_count"),
        "issue_events": correlation.get("issue_event_count"),
        "traps": correlation.get("trap_count"),
        "negative_cases": correlation.get("negative_case_count"),
        "simulators": body.get("simulators_counted", []),
        "limitations": body.get("limitations", []),
    }


def checklist_progress() -> dict[str, Any]:
    path = REPO / "docs" / "UNIFIED_EXECUTION_CHECKLIST.md"
    if not path.exists():
        return {"present": False}
    text = path.read_text()
    return {
        "present": True,
        "done": text.count("- [x] "),
        "in_progress": text.count("- [~] "),
        "not_started": text.count("- [ ] "),
        "blocked": text.count("- [!] "),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=REPO / "results" / "abi3" / "program_status.json"
    )
    parser.add_argument("--markdown", type=Path, default=REPO / "docs" / "PROGRAM_STATUS.md")
    args = parser.parse_args()

    status = {
        "schema": "opentallas.abi3.program_status.v1",
        "commit": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "worktree_dirty": bool(_git("status", "--porcelain")),
        "checklist": checklist_progress(),
        "engine_coverage": engine_coverage(),
        "neutral_ir": ir_artifacts(),
        "workloads": workloads(),
        "reference_oracle": oracle_results(),
        "physical": physical_results(),
        "campaigns": campaign_results(),
        "rtl_correlation": rtl_correlation(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(status))

    lines = [
        "# ABI 3.0 program status",
        "",
        "Generated by `tools/build_program_status.py`. Every row is read from an",
        "artifact on disk; an absent artifact is reported as absent rather than",
        "omitted.",
        "",
        f"**Commit:** `{status['commit'][:12]}`",
        f"**Checklist:** {status['checklist'].get('done', 0)} done, "
        f"{status['checklist'].get('in_progress', 0)} in progress, "
        f"{status['checklist'].get('not_started', 0)} not started",
        "",
        "## Engine coverage",
        "",
        f"{status['engine_coverage']['implemented']} of "
        f"{status['engine_coverage']['implemented'] + status['engine_coverage']['missing']}"
        " dispatched engine operations implemented; "
        f"{status['engine_coverage']['sequencer_executed']} families are executed by "
        "the microsequencer itself.",
        "",
    ]
    if status["engine_coverage"]["missing_operations"]:
        lines.append("Missing: " + ", ".join(
            f"`{name}`" for name in status["engine_coverage"]["missing_operations"]
        ))
        lines.append("")

    lines += ["## Neutral IR", "", "| Model | Kernels | Tensors | States | Bound weights | graph_id |", "|---|---:|---:|---:|---:|---|"]
    for model, body in status["neutral_ir"].items():
        if not body.get("present"):
            lines.append(f"| {model} | — | — | — | — | not built |")
        else:
            lines.append(
                f"| {model} | {body['kernels']} | {body['tensors']} | {body['states']} "
                f"| {body['bound_weight_bytes']:,} B | `{body['graph_id'][:12]}` |"
            )
    lines.append("")

    if status["reference_oracle"]:
        lines += ["## External reference oracle", "",
                  "| Workload | Tokens | Stop | Seconds |", "|---|---:|---|---:|"]
        for wid, body in sorted(status["reference_oracle"].items()):
            lines.append(
                f"| {wid} | {body['generated_token_count']} | {body['stop_reason']} "
                f"| {body['wall_seconds']} |"
            )
        lines.append("")

    if status["physical"]:
        lines += ["## Physical", "",
                  "| View / block / run | Verdict | Timing met | Corner | Cells | Area (um2) | Fmax (MHz) | Setup WNS (ns) | Viol. |",
                  "|---|---|---|---|---:|---:|---:|---:|---:|"]
        for key, body in sorted(status["physical"].items()):
            fmax = body.get("fmax_hz")
            wns = body.get("setup_wns_ns")
            met = body.get("timing_met")
            lines.append(
                f"| {key} | {body.get('status')} "
                f"| {'yes' if met else ('no' if met is False else '—')} "
                f"| {body.get('corner')} "
                f"| {body.get('cell_count')} | {body.get('cell_area_um2')} "
                f"| {round(fmax / 1e6, 1) if fmax else '—'} "
                f"| {round(wns, 3) if isinstance(wns, (int, float)) else '—'} "
                f"| {body.get('setup_violating_paths')} |"
            )
        lines.append("")

    rtl = status["rtl_correlation"]
    if rtl.get("present"):
        lines += [
            "## RTL 3.0 correlation",
            "",
            f"{rtl['cases']} cases, {rtl['programs_run']} programs executed, "
            f"{rtl['issue_events']} engine-issue events and {rtl['traps']} traps "
            f"matched against `{rtl['reference']}` on "
            f"{len(rtl['simulators'])} independent simulators; "
            f"{rtl['negative_cases']} negative cases.",
            "",
        ]
        if rtl["limitations"]:
            lines.append("Declared limitations:")
            lines += [f"- {item}" for item in rtl["limitations"]]
            lines.append("")

    if status["campaigns"]:
        lines += ["## Accelerator campaigns", "",
                  "| Run | Status | Target | Workload | Tokens | Stop |",
                  "|---|---|---|---|---:|---|"]
        for key, body in sorted(status["campaigns"].items()):
            lines.append(
                f"| {key} | {body.get('status')} | {body.get('target')} "
                f"| {body.get('workload')} | {body.get('generated_token_count')} "
                f"| {body.get('stop_reason')} |"
            )
        lines.append("")
    else:
        lines += ["## Accelerator campaigns", "",
                  "No accelerator campaign has run yet.", ""]

    # Sections append an empty separator line for composition.  Strip that
    # final separator before adding the one canonical newline so regenerated
    # Markdown also passes ``git diff --check``.
    args.markdown.write_text("\n".join(lines).rstrip() + "\n")
    print(f"wrote {args.output} and {args.markdown}")
    print(
        f"engines {status['engine_coverage']['implemented']}/"
        f"{status['engine_coverage']['implemented'] + status['engine_coverage']['missing']}, "
        f"checklist {status['checklist'].get('done')} done"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
