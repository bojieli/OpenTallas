#!/usr/bin/env python3
"""Check the retained VM writeback proof against current source and compiler output.

This collects existing component evidence; it does not simulate or qualify a layer.
The calendar uses tb_sertrade's edge convention; tb_vmwb has one additional rq edge.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import wb_calendar as wc

ROOT = wc.ROOT
PROOF = ROOT / "results/arch/qwen_split_compute_1014/vmwb_1015"
VARIANTS = ("pos", "base", "o3", "smut1", "smut2", "imut1", "imut3", "vpmut1")


def audit(calendar):
    checks = {}
    executed = {}
    for variant in VARIANTS:
        manifest = PROOF / "run2" / ("b_" + variant) / "executed_source.sha256"
        entries = {}
        for line in manifest.read_text().splitlines():
            expected, path = line.split(maxsplit=1)
            actual = hashlib.sha256(subprocess.check_output(
                ["git", "show", "HEAD:" + path], cwd=ROOT)).hexdigest()
            entries[path] = {"sha256": expected, "matches_current_git_source": expected == actual}
        executed[variant] = entries
        checks["sources_" + variant] = len(entries) == 25 and all(
            entry["matches_current_git_source"] for entry in entries.values())
    runs = {}
    for line in (PROOF / "run2/results.txt").read_text().splitlines():
        match = re.fullmatch(r"(\w+) (PC\d+) (\{.*\}) (PASS vmwb|FAIL vmwb errors=\d+)\s*", line)
        if not match:
            raise ValueError("unparsed result line: " + line)
        variant, pc, data, verdict = match.groups()
        key = variant + "/" + pc
        if key in runs:
            raise ValueError("duplicate result: " + key)
        runs[key] = {"observed": json.loads(data), "pass": verdict == "PASS vmwb"}
    expected_keys = {v + "/" + pc for v in VARIANTS for pc in wc.NODE}
    checks["complete_result_matrix"] = set(runs) == expected_keys
    structures = {"pos": "O4_3lanes_compressed", "base": "O1_train24_1lane_24slots", "o3": "O3_3lanes_8slots"}
    for key, run in runs.items():
        variant, pc = key.split("/")
        obs = run["observed"]
        # This VM data-swap mutant is intentionally indistinguishable at PC11;
        # the retained receipt documents equal band-1 and band-2 stimulus there.
        expect_pass = variant in structures or (variant == "vpmut1" and pc == "PC11")
        checks[key + "/verdict"] = run["pass"] == expect_pass
        if variant in structures:
            op = calendar["ops"][pc]
            checks[key + "/measured_landing"] = obs["last_landing_after_go"] == (
                op["structures"][structures[variant]]["last_landing_after_go"] + 1)
            checks[key + "/shape_and_faults"] = (
                obs["bursts"] == 8 * op["fields"]["tiles"] and
                obs["rows"] == op["real_rows"] and obs["errors"] == 0 and
                obs["fault_ser"] == "000" and obs["fault_issue"] == 0 and obs["fault_vm"] == 0)
    checks["compiler_rows_and_conflicts"] = calendar["ok"] and all(
        op.get("row_law_matches_rtl") is True for op in calendar["ops"].values())
    checks["current_successor_price"] = calendar["options"]["O4_3lanes_compressed"] == {
        "face_cycles_per_layer": 148, "face_cycles_per_layer_token_ops": 99,
        "e2e_loss_pct_incl_pc11": 2.091, "e2e_loss_pct_token_ops": 1.409}
    return {"schema": "opentallas.qwen.vmwb_component_audit.v1",
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "scope": "Retained one-rank, one-op common-phase component evidence; actual controller, 24 soft-mul port variants, serializers and mapped SRAM VM. No layer/full-token/physical qualification.",
            "open": ["actual die TRAIN_EDGES including relays", "whole-layer writer and port calendar", "physical views and clock phases", "head programme composition"],
            "checks": checks, "executed_sources": executed, "runs": runs,
            "ok": all(checks.values())}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = audit(json.loads(Path(args.calendar).read_text()))
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print("COMPONENT AUDIT", "PASS" if result["ok"] else "FAIL", "checks", len(result["checks"]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
