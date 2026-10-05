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
import re
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


def _source_worktree_dirty(*generated_outputs: Path) -> bool:
    """Report source/input drift without counting this generator's outputs."""

    pathspecs = ["."]
    for output in generated_outputs:
        try:
            relative = output.resolve().relative_to(REPO)
        except ValueError:
            continue
        pathspecs.append(f":(exclude){relative.as_posix()}")
    return bool(_git("status", "--porcelain", "--", *pathspecs))


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


#: Paths under results/physical_abi3 that are not single-run P&R records.
#: Reported rather than dropped, because this document's own header promises
#: that "an absent artifact is reported as absent rather than omitted", and a
#: file skipped in silence is the same defect in the other direction.
PHYSICAL_NON_RUN_RECORDS: list[str] = []


def _is_physical_run(body: dict[str, Any]) -> bool:
    """Does this artifact describe ONE physical run?

    The tree also holds sweep records, which carry a whole campaign rather than
    a run: their ``corner`` is a bare string like "TT" where a run's is an
    object with a ``name``.  Treating one as the other used to raise
    ``AttributeError: 'str' object has no attribute 'get'`` and take the whole
    document down with it -- so PROGRAM_STATUS.md could not be regenerated at
    all, and stayed pinned at whatever commit last produced it.
    """

    return any(
        isinstance(body.get(section), dict)
        for section in ("synthesis", "static_timing", "routing", "place_and_route")
    )


def _corner_name(body: dict[str, Any]) -> Any:
    """The corner, whichever shape the record states it in."""

    corner = body.get("corner")
    if isinstance(corner, dict):
        return corner.get("name")
    return corner


def physical_results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    PHYSICAL_NON_RUN_RECORDS.clear()
    root = REPO / "results" / "physical_abi3"
    for path in sorted(root.rglob("*.json")) if root.exists() else []:
        body = _load(path)
        if not isinstance(body, dict):
            continue
        if not _is_physical_run(body):
            PHYSICAL_NON_RUN_RECORDS.append(str(path.relative_to(REPO)))
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
            "corner": _corner_name(body),
            "cell_count": synth.get("cell_count"),
            "cell_area_um2": synth.get("cell_area_um2"),
            "macro_count": synth.get("macro_count"),
            "fmax_hz": timing.get("fmax_hz"),
            "setup_wns_ns": timing.get("setup_wns_ns"),
            "hold_wns_ns": timing.get("hold_wns_ns"),
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


def rtl_deployment_correlation() -> dict[str, Any]:
    body = _load(REPO / "results" / "rtl" / "abi3_deployment_campaign.json")
    if not body:
        return {"present": False}
    simulator_rows = body.get("cases", [])
    observed = simulator_rows[0].get("observed_cases", []) if simulator_rows else []
    what_ran = body.get("what_ran", {})
    profile = body.get("rtl_profile", {})
    return {
        "present": True,
        "status": body.get("status"),
        "evidence_class": body.get("evidence_class"),
        "deployments": len(what_ran.get("deployments", [])),
        "cases": len(body.get("correlated_cases", [])),
        "correlated": sum(row.get("verdict") == "OK" for row in observed),
        # A correlated case is one the RTL reproduced, trap included; a
        # completion is one the golden model ran to its terminal fence.
        "completions": sum(
            bool(row.get("ran_to_completion_on_the_golden_model"))
            for row in what_ran.get("depth_reached", [])
        ),
        "issue_events": sum(row.get("issues_compared", 0) for row in observed),
        "resolved_views": sum(row.get("views_compared", 0) for row in observed),
        "predicates": sum(row.get("predicates_compared", 0) for row in observed),
        "checks_per_simulator": {
            row.get("name", "unknown"): row.get("checks") for row in simulator_rows
        },
        "simulators": body.get("simulators_counted", []),
        "state_compatibility_elaborated": profile.get(
            "state_compatibility_elaborated"
        ),
        "required_state_descriptors": profile.get(
            "required_state_descriptor_count"
        ),
        "required_state_instructions": profile.get(
            "required_state_instruction_count"
        ),
        "limitations": body.get("limitations", []),
    }


def rtl_engine_correlation() -> dict[str, Any]:
    body = _load(REPO / "results" / "rtl" / "abi3_engine_campaign.json")
    if not body:
        return {"present": False}
    correlation = body.get("correlation", {})
    sensitivity = body.get("mutation_sensitivity", {})
    boundary = body.get("claim_boundary", {}).get("does_not_establish", {})
    return {
        "present": True,
        "status": body.get("status"),
        "evidence_class": body.get("evidence_class"),
        "cases": correlation.get("case_count"),
        "families": correlation.get("family_count"),
        "result_words": correlation.get("result_word_count"),
        "macs": correlation.get("mac_count"),
        "faults": correlation.get("fault_case_count"),
        "decode_probes": correlation.get("decode_probe_count"),
        "arithmetic_probes": correlation.get("arith_probe_count"),
        "checks_per_simulator": body.get("checks_per_simulator", {}),
        "simulators": body.get("simulators_counted", []),
        "mutations": sensitivity.get("mutation_count"),
        "all_mutations_caught": sensitivity.get("all_caught_by_both_simulators"),
        "integration_limit": boundary.get("integration_with_the_control_plane"),
    }


def rtl_shipped_prefix_correlation() -> dict[str, Any]:
    body = _load(REPO / "results" / "rtl" / "abi3_shipped_prefix_campaign.json")
    if not body:
        return {"present": False}
    return {
        "present": True,
        "status": body.get("status"),
        "evidence_class": body.get("evidence_class"),
        "cases": body.get("case_count"),
        "real_engine_launches": body.get("real_engine_launch_count"),
        "dma_gather_launches": body.get("dma_gather_launch_count"),
        "embedding_launches": body.get("embedding_launch_count"),
        "rms_norm_launches": body.get("rms_norm_launch_count"),
        "dma_transfer_launches": body.get("dma_transfer_launch_count"),
        "result_words": body.get("result_word_count"),
        "rope_result_words": body.get("rope_result_word_count"),
        "embedding_result_words": body.get("embedding_result_word_count"),
        "rms_norm_result_words": body.get("rms_norm_result_word_count"),
        "dma_transfer_result_words": body.get("dma_transfer_result_word_count"),
        "resolved_views": body.get("resolved_view_count"),
        "selected_checkpoint_bytes": body.get("selected_checkpoint_byte_count"),
        "selected_embedding_checkpoint_bytes": body.get(
            "selected_embedding_checkpoint_byte_count"
        ),
        "selected_rms_checkpoint_bytes": body.get(
            "selected_rms_checkpoint_byte_count"
        ),
        "selected_checkpoint_rows": len(body.get("checkpoint_rows", [])),
        "selected_checkpoint_gains": len(body.get("checkpoint_gains", [])),
        "capability_faults": body.get("capability_fault_count"),
        "simulator_checks": body.get("simulator_checks", {}),
        "simulators_agree": body.get("simulators_agree"),
        "state_compat": body.get("state_compat"),
        "post_fault_writes": body.get("post_fault_write_count"),
        "fault_sites": body.get("fault_sites", []),
        "scope": body.get("scope", {}),
    }


def checklist_progress() -> dict[str, Any]:
    path = REPO / "docs" / "UNIFIED_EXECUTION_CHECKLIST.md"
    if not path.exists():
        return {"present": False}
    rows = re.findall(
        r"^- \[(x|~| |!)\] W\d+\.\d+\b",
        path.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return {
        "present": True,
        "scope": "top_level_Wn.m_rows_only",
        "done": rows.count("x"),
        "in_progress": rows.count("~"),
        "not_started": rows.count(" "),
        "blocked": rows.count("!"),
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
        "worktree_dirty": _source_worktree_dirty(
            args.output,
            args.markdown,
            REPO / "results" / "abi3" / "prose_figure_coverage.json",
        ),
        "worktree_dirty_scope": (
            "repository_except_generated_status_and_prose_coverage_outputs"
        ),
        "checklist": checklist_progress(),
        "engine_coverage": engine_coverage(),
        "neutral_ir": ir_artifacts(),
        "workloads": workloads(),
        "reference_oracle": oracle_results(),
        "physical": physical_results(),
        "physical_non_run_records": list(PHYSICAL_NON_RUN_RECORDS),
        "campaigns": campaign_results(),
        "rtl_correlation": rtl_correlation(),
        "rtl_deployment_correlation": rtl_deployment_correlation(),
        "rtl_shipped_prefix_correlation": rtl_shipped_prefix_correlation(),
        "rtl_engine_correlation": rtl_engine_correlation(),
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
        "## Functional simulator engine coverage",
        "",
        f"{status['engine_coverage']['implemented']} of "
        f"{status['engine_coverage']['implemented'] + status['engine_coverage']['missing']}"
        " dispatched functional engine operations implemented; "
        f"{status['engine_coverage']['sequencer_executed']} families are executed by "
        "the microsequencer itself.",
        "",
    ]
    if status["engine_coverage"]["missing_operations"]:
        lines.append("Missing: " + ", ".join(
            f"`{name}`" for name in status["engine_coverage"]["missing_operations"]
        ))
        lines.append("")

    lines += [
        "## Neutral IR",
        "",
        "The `Legacy state declarations` column counts semantic declarations in",
        "the retained source IR. They are not ABI state members: every current",
        "four-target deployment lowers mutable values to ordinary live buffers and",
        "emits zero ABI `STATE` descriptors and instructions.",
        "",
        "| Model | Kernels | Tensors | Legacy state declarations | Bound weights | graph_id |",
        "|---|---:|---:|---:|---:|---|",
    ]
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

    lines += ["## RTL 3.0 correlation", ""]
    rtl = status["rtl_correlation"]
    if rtl.get("present"):
        lines += [
            "### Generic microsequencer fixtures",
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
    else:
        lines += ["### Generic microsequencer fixtures", "", "Artifact absent.", ""]

    deployment_rtl = status["rtl_deployment_correlation"]
    if deployment_rtl.get("present"):
        compatibility = deployment_rtl["state_compatibility_elaborated"]
        compatibility_text = (
            "disabled" if compatibility is False else str(compatibility)
        )
        checks = ", ".join(
            f"{name} {count:,}"
            for name, count in deployment_rtl["checks_per_simulator"].items()
            if isinstance(count, int)
        )
        lines += [
            "### Shipped-deployment control plane",
            "",
            f"{deployment_rtl['deployments']} deployments, "
            f"{deployment_rtl['cases']} prefill/decode cases, "
            f"{deployment_rtl['correlated']} correlated, "
            f"{deployment_rtl['completions']} completions, "
            f"{deployment_rtl['issue_events']:,} engine issues, "
            f"{deployment_rtl['resolved_views']:,} resolved views and "
            f"{deployment_rtl['predicates']:,} predicates matched on "
            f"{len(deployment_rtl['simulators'])} independent simulators "
            f"({checks}).",
            "",
            "The production profile elaborates with compatibility state "
            f"{compatibility_text} "
            f"and requires {deployment_rtl['required_state_descriptors']} `STATE` "
            f"descriptors and {deployment_rtl['required_state_instructions']} "
            "`STATE` instructions.",
            "",
        ]
    else:
        lines += ["### Shipped-deployment control plane", "", "Artifact absent.", ""]

    prefix_rtl = status["rtl_shipped_prefix_correlation"]
    if prefix_rtl.get("present"):
        checks = ", ".join(
            f"{name} {count:,}"
            for name, count in prefix_rtl["simulator_checks"].items()
            if isinstance(count, int)
        )
        fault_sites = ", ".join(
            f"{site.get('case')} {site.get('opcode')} PC {site.get('pc')} "
            f"descriptor {site.get('descriptor_id')}"
            for site in prefix_rtl["fault_sites"]
        )
        lines += [
            "### Integrated shipped-program engine prefix",
            "",
            f"{prefix_rtl['cases']} shipped decode cases launched "
            f"{prefix_rtl['real_engine_launches']} real engine operations, "
            f"split into {prefix_rtl['dma_gather_launches']} FP32 `DMA.GATHER` "
            f"launches and {prefix_rtl['embedding_launches']} exact BF16 "
            f"`TENSOR.EMBED_LOOKUP`, {prefix_rtl['rms_norm_launches']} exact "
            f"BF16 `VECTOR.RMS_NORM`, and "
            f"{prefix_rtl['dma_transfer_launches']} stride-zero BF16 "
            "`DMA.TRANSFER` launches. They compared "
            f"{prefix_rtl['result_words']:,} result words "
            f"({prefix_rtl['rope_result_words']:,} generated-RoPE FP32 words "
            f"plus {prefix_rtl['embedding_result_words']:,} embedding, "
            f"{prefix_rtl['rms_norm_result_words']:,} RMSNorm, and "
            f"{prefix_rtl['dma_transfer_result_words']:,} transfer BF16 "
            f"codes) and resolved {prefix_rtl['resolved_views']} views. The "
            f"simulators agree = {prefix_rtl['simulators_agree']} ({checks}).",
            "",
            f"Embedding reads cover {prefix_rtl['selected_checkpoint_rows']} "
            f"selected checkpoint rows "
            f"({prefix_rtl['selected_embedding_checkpoint_bytes']:,} bytes); "
            f"RMSNorm reads {prefix_rtl['selected_checkpoint_gains']} selected "
            f"gain ranges ({prefix_rtl['selected_rms_checkpoint_bytes']:,} bytes), "
            f"for {prefix_rtl['selected_checkpoint_bytes']:,} authenticated bytes "
            "in total. Legal token ID 0 is a bounded synthetic address probe, not "
            "a natural-language decoded token. Each selected range is rehashed "
            "and bound to its certified deployment and declared segment; the "
            "complete segment is not rehashed in this campaign.",
            "",
            f"Precise capability boundaries: {fault_sites}. Production "
            f"`STATE_COMPAT={prefix_rtl['state_compat']}`; post-fault writes = "
            f"{prefix_rtl['post_fault_writes']}.",
            "",
            "This is a bounded data-bearing decode prefix, not prefill, a whole "
            "transaction, token generation, EOS, or physical closure.",
            "",
        ]
    else:
        lines += [
            "### Integrated shipped-program engine prefix",
            "",
            "Artifact absent.",
            "",
        ]

    engine_rtl = status["rtl_engine_correlation"]
    if engine_rtl.get("present"):
        checks = ", ".join(
            f"{name} {count:,}"
            for name, count in engine_rtl["checks_per_simulator"].items()
            if isinstance(count, int)
        )
        lines += [
            "### Standalone engine datapaths",
            "",
            f"{engine_rtl['cases']} cases across {engine_rtl['families']} bounded "
            f"opcode pairs compared {engine_rtl['result_words']:,} result words, "
            f"{engine_rtl['macs']:,} MACs, {engine_rtl['faults']} faults, "
            f"{engine_rtl['decode_probes']:,} format-decode probes and "
            f"{engine_rtl['arithmetic_probes']:,} arithmetic probes on "
            f"{len(engine_rtl['simulators'])} independent simulators ({checks}).",
            "",
            f"Mutation sensitivity: {engine_rtl['mutations']} mutations; "
            f"all caught by both simulators = {engine_rtl['all_mutations_caught']}.",
            "",
        ]
        if engine_rtl.get("integration_limit"):
            lines += [
                "Integration boundary: " + engine_rtl["integration_limit"],
                "",
            ]
    else:
        lines += ["### Standalone engine datapaths", "", "Artifact absent.", ""]

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
