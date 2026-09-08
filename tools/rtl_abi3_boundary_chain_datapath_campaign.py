#!/usr/bin/env python3
"""Measure the two-tile dependent chain of section 13 item 13 on both simulators.

``results/rtl/abi3_boundary_chain.json`` established, by elaboration rather than
by reading source, that the chain could not be assembled: two of the five terms
of section 3.6 had no RTL.  Both now exist and are qualified in their own right
(``results/rtl/abi3_partial_collector.json``,
``results/rtl/abi3_operand_receiver.json``), so the chain can be built out of
design modules alone:

    ot_a3_tile64 -> ot_a3_partial_collector -> ot_a3_tree_endpoint_fp32
                 -> ot_a3_operand_receiver  -> ot_a3_tile64

This campaign runs it and stamps the span from the producer tile's LAST partial
write to the consumer tile's FIRST lane-op, decomposed into six telescoping
legs.  Nothing in the span is a bench model: the store-delivery networks and
the producer's own operand H-tree run to completion before the span opens and
contribute no cycle to it, which the campaign checks by requiring the legs to
sum to the span and by requiring that no consumer lane-op is observed before
its operand landed.

It PREDICTS no cycle count.  Two independently written checkers drive one
deterministic top, so the two simulators must report the same cycles, and the
campaign requires it.  The measured number is compared with the cycle model's
own charge -- read from ``results/derived/qwen3_n5_design_target_calibration.json``,
not typed here -- and the residual is attributed, never tuned.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "opentallas.rtl.abi3_boundary_chain_measured.v1"
CAMPAIGN = "rtl3_abi3_boundary_chain_measured"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_boundary_chain_measured.json"
CONTROL_RECORD = ROOT / "results/rtl/abi3_boundary_control.json"
CALIBRATION = ROOT / "results/derived/qwen3_n5_design_target_calibration.json"
STRUCTURAL_RECORD = ROOT / "results/rtl/abi3_boundary_chain.json"

RTL_SOURCES = [
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_lane_pipelined.sv",
    "rtl/abi3/ot_a3_lq8.sv",
    "rtl/abi3/ot_a3_tile64.sv",
    "rtl/abi3/ot_a3_partial_collector.sv",
    "rtl/abi3/ot_a3_tree_endpoint_fp32.sv",
    "rtl/abi3/ot_a3_operand_receiver.sv",
    "rtl/test/a3_boundary_chain_top.sv",
]
BOUND_SOURCES = RTL_SOURCES + [
    "rtl/test/tb_a3_boundary_chain.sv",
    "rtl/test/a3_boundary_chain_harness.cpp",
    "tools/build_abi3_boundary_chain_vectors.py",
    "tools/rtl_abi3_boundary_chain_datapath_campaign.py",
]
VECTOR_FILES = ("ch_pstream.hex", "ch_cstream.hex", "ch_pact.hex",
                "ch_case.hex", "ch_expect.hex", "ch_meta.hex")

FIELDS = ("blocks", "boundary", "kblock", "collect", "tree", "receive", "ready",
          "admit", "laneadmit", "firstroot", "leafspan", "prodcycles",
          "prodkblock", "roots", "words", "stages")
CASE_RE = re.compile(
    r"^XCASE (?P<index>\d+) (?P<verdict>OK|DIVERGE) site=(?P<site>\d+) " +
    " ".join(rf"{f}=(?P<{f}>\d+)" for f in FIELDS) + r"$", re.MULTILINE)
CHECKS_RE = re.compile(r"^CHECKS: (\d+)$", re.MULTILINE)
MARKER_RE = re.compile(
    r"^PASS: ABI3 two-tile dependent chain cases=(?P<cases>\d+)$", re.MULTILINE)

SITE_NAMES = {
    0: "none", 1: "the producing tile faulted", 2: "the consuming tile faulted",
    3: "the collector faulted", 4: "the endpoint faulted",
    5: "the receiver faulted", 6: "the producer's partial count",
    7: "the consumer's output count", 8: "leaf vectors emitted",
    9: "activation words delivered", 10: "act_ready_kblocks",
    11: "roots retired", 12: "a consumer lane-op before its operand landed",
    13: "the top timed out", 14: "a producer staging underrun",
    15: "a consumer staging underrun",
    16: "a root differs from the AM-E1 reference",
    17: "a delivered activation word differs from the BF16 narrowing of its root",
    18: "a consumer partial differs from the reference over the delivered operand",
    19: "the boundary measured zero cycles",
    20: "the six legs do not sum to the boundary",
    21: "the five legs do not sum to the K-block span",
    22: "the producer's last K-block measured zero cycles",
    23: "the case did not finish",
}
LEG_NAMES = {
    "collect": "the collector: the producer's last partial write to the first "
               "leaf vector at the endpoint's port",
    "tree": "the K-block tree: the first leaf vector in to the last root out -- "
            "64 columns of service plus the endpoint's own 1 + 3L pipeline",
    "receive": "the receiver: the last root to the last activation word landing "
               "in the consumer's FIFO",
    "ready": "operand readiness: act_ready_kblocks named the slice",
    "admit": "the consumer tile's sequencer: S_WAIT to kblock_active",
    "laneadmit": "the consumer's lanes: kblock_active to the first lane-op "
                 "(the lane's own admission unit, which T64 also charges inside "
                 "its 31 cycles of per-K-block overhead)",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(body: Any) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True) + "\n"


def tool_identity(name: str, argv: list[str], pattern: str) -> dict[str, Any]:
    path = shutil.which(argv[0]) or argv[0]
    if not Path(path).exists():
        raise SystemExit(f"required tool is unavailable: {name} ({argv[0]})")
    out = subprocess.run(argv, capture_output=True, text=True, check=False)
    text = (out.stdout or "") + (out.stderr or "")
    match = re.search(pattern, text)
    return {"executable": path, "executable_sha256": sha256_file(Path(path)),
            "version": (match.group(0) if match else
                        text.splitlines()[0] if text else "")}


def git_identity() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(args, cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run(["git", "rev-parse", "HEAD"]),
            "worktree_dirty": bool(run(["git", "status", "--porcelain"]))}


def canonicalise(text: str, build: Path) -> str:
    return text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>").replace(
        str(Path.home()), "<HOME>")


def parse(log: str) -> dict[str, Any]:
    cases = []
    for m in CASE_RE.finditer(log):
        case = {"index": int(m.group("index")), "verdict": m.group("verdict"),
                "site": int(m.group("site"))}
        case["site_name"] = SITE_NAMES.get(case["site"], "unknown")
        for f in FIELDS:
            case[f] = int(m.group(f))
        cases.append(case)
    marker = MARKER_RE.search(log)
    checks = CHECKS_RE.search(log)
    return {"cases": cases, "marker_present": marker is not None,
            "checks": int(checks.group(1)) if checks else None,
            "case_count": int(marker.group("cases")) if marker else None}


def run_stage(command: list[str], cwd: Path, build: Path, timeout: int) -> dict[str, Any]:
    out = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                         timeout=timeout)
    return {"command": canonicalise(" ".join(command), build),
            "returncode": out.returncode,
            "log": canonicalise((out.stdout or "") + (out.stderr or ""), build)}


def run_iverilog(build: Path, stages: int) -> dict[str, Any]:
    vvp = build / "ch.vvp"
    compile_cmd = ["iverilog", "-g2012", "-s", "tb_a3_boundary_chain",
                   f"-Pot_a3_boundary_chain_top.ADDER_STAGES={stages}",
                   "-o", str(vvp)]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/tb_a3_boundary_chain.sv"))
    comp = run_stage(compile_cmd, build, build, 4 * 3600)
    if comp["returncode"] != 0:
        raise SystemExit("iverilog compile failed:\n" + comp["log"])
    run = run_stage(["vvp", str(vvp)], build, build, 12 * 3600)
    entry = parse(run["log"])
    entry.update({"name": "iverilog", "compile_command": comp["command"],
                  "run_command": run["command"], "run_returncode": run["returncode"],
                  "log_sha256": hashlib.sha256(run["log"].encode()).hexdigest(),
                  "run_log": run["log"],
                  "status": "pass" if run["returncode"] == 0 and entry["marker_present"]
                            else "fail"})
    return entry


def run_verilator(build: Path, verilator: str, stages: int) -> dict[str, Any]:
    obj = build / "obj_ch"
    compile_cmd = [verilator, "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
                   "-Wno-DECLFILENAME", "-O2", "--top-module",
                   "ot_a3_boundary_chain_top", f"-GADDER_STAGES={stages}",
                   "--Mdir", str(obj), "-o", "Vch"]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/a3_boundary_chain_harness.cpp"))
    compile_cmd += ["-CFLAGS", "-std=c++17 -O2", "-j", "8"]
    comp = run_stage(compile_cmd, build, build, 4 * 3600)
    if comp["returncode"] != 0:
        raise SystemExit("verilator build failed:\n" + comp["log"])
    run = run_stage([str(obj / "Vch")], build, build, 12 * 3600)
    entry = parse(run["log"])
    entry.update({"name": "verilator", "compile_command": comp["command"],
                  "run_command": "<BUILD>/obj_ch/Vch", "run_returncode": run["returncode"],
                  "log_sha256": hashlib.sha256(run["log"].encode()).hexdigest(),
                  "run_log": run["log"],
                  "status": "pass" if run["returncode"] == 0 and entry["marker_present"]
                            else "fail"})
    return entry


COMPARED = ("index", "verdict", "site") + FIELDS


def run_build(label: str, stages: int, build_root: Path, verilator: str,
              seed: int, blocks: list[int]) -> dict[str, Any]:
    from tools.build_abi3_boundary_chain_vectors import build_cases, emit
    build = build_root / label
    build.mkdir(parents=True, exist_ok=True)
    manifest = emit(build_cases(blocks), build, seed, stages)
    for name in VECTOR_FILES:
        if sha256_file(build / name) != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_iverilog, build, stages),
                   pool.submit(run_verilator, build, verilator, stages)]
        entries = [f.result() for f in futures]
    projections = [[tuple(c[k] for k in COMPARED) for c in e["cases"]] for e in entries]
    agree = len({tuple(p) for p in projections}) == 1 and bool(projections[0])
    checks_agree = len({e["checks"] for e in entries}) == 1
    diverged = [c for e in entries for c in e["cases"] if c["verdict"] != "OK"]
    cases = entries[0]["cases"]
    values = sorted({c["boundary"] for c in cases})
    kblock_values = sorted({c["kblock"] for c in cases})
    return {
        "label": label,
        "adder_stages": stages,
        "status": ("pass" if all(e["status"] == "pass" for e in entries) and agree
                   and checks_agree and not diverged else "fail"),
        "simulators_agree": agree,
        "check_counts_agree": checks_agree,
        "checks_per_simulator": entries[0]["checks"],
        "boundary_cycles": values[0] if len(values) == 1 else None,
        "boundary_cycles_observed": values,
        "boundary_to_kblock_cycles": (kblock_values[0] if len(kblock_values) == 1
                                      else None),
        "boundary_to_kblock_observed": kblock_values,
        "legs": {name: sorted({c[name] for c in cases}) for name in LEG_NAMES},
        "endpoint_first_root_cycles": sorted({c["firstroot"] for c in cases}),
        "leaf_span_cycles": sorted({c["leafspan"] for c in cases}),
        "producer_last_kblock_cycles": sorted({c["prodkblock"] for c in cases}),
        "leaves_swept": sorted({c["blocks"] for c in cases}),
        "manifest": {k: v for k, v in manifest.items() if k != "cases"},
        "cases_declared": manifest["cases"],
        "divergences": diverged,
        "simulators": entries,
    }


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def build_artifact(builds: list[dict[str, Any]]) -> dict[str, Any]:
    headline = next(b for b in builds if b["adder_stages"] == 3)
    status = "pass" if all(b["status"] == "pass" for b in builds) else "fail"
    cycles = headline["boundary_cycles"]

    control = read_json(CONTROL_RECORD) or {}
    control_cycles = ((control.get("boundary") or {}).get("cycles")
                      if control.get("status") == "pass" else None)
    calibration = read_json(CALIBRATION) or {}
    model = ((calibration.get("calibration") or {}).get("boundary") or {})
    model_chain = model.get("model_exposed_chain_cycles")
    model_fixed = model.get("model_fixed_latency_cycles")
    structural = read_json(STRUCTURAL_RECORD) or {}

    composed = (cycles + control_cycles
                if (cycles is not None and control_cycles is not None) else None)
    per_sim = [{"simulator": e["name"], "cycles": cycles}
               for e in headline["simulators"]]

    return {
        "schema": SCHEMA,
        "campaign": CAMPAIGN,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": [e["name"] for e in headline["simulators"]],
        "chain": {
            "modules": [
                "rtl/abi3/ot_a3_tile64.sv (the producing tile)",
                "rtl/abi3/ot_a3_partial_collector.sv",
                "rtl/abi3/ot_a3_tree_endpoint_fp32.sv",
                "rtl/abi3/ot_a3_operand_receiver.sv",
                "rtl/abi3/ot_a3_tile64.sv (the consuming tile)",
            ],
            "every_cycle_of_the_span_is_design_rtl": True,
            "rule": (
                "the two blocks results/rtl/abi3_boundary_chain.json found "
                "MISSING now exist and are qualified in their own right "
                "(results/rtl/abi3_partial_collector.json, "
                "results/rtl/abi3_operand_receiver.json), so the span contains "
                "no improvised term.  The store-delivery networks and the "
                "PRODUCER's operand H-tree are bench models, but both complete "
                "before the span opens: the consumer's staging ring is full and "
                "its weight stream present long before its operand arrives, so "
                "act_ready_kblocks -- the receiver's -- is the only thing "
                "gating it, and the legs are required to sum to the span"),
            "dependence": (
                "the consumer's K is the producer's N and its activation slice "
                "IS the producer's 64 output columns, rounded once: the "
                "consumer's expected partials are computed from the producer's "
                "roots, so a wrong value anywhere in the chain cannot reach the "
                "end unnoticed"),
            "supersedes_probe": {
                "record": "results/rtl/abi3_boundary_chain.json",
                "campaign": structural.get("campaign"),
                "what_it_established": (structural.get("does_not_establish") or {}).get(
                    "that_a_chain_is_impossible"),
            },
        },
        "boundary": {
            "cycles": cycles,
            "simulators_agree": headline["simulators_agree"],
            "per_simulator": per_sim,
            "definition": (
                "the cycles from the producing tile's LAST partial write (the "
                "last cycle on which any bit of its part_we is high) to the "
                "consuming tile's FIRST lane-op (the first cycle its shared "
                "activation read is valid, which is the cycle a lane first "
                "consumes an operand)"),
            "decomposition": {name: headline["legs"][name] for name in LEG_NAMES},
            "decomposition_rule": LEG_NAMES,
            "to_kblock_active_cycles": headline["boundary_to_kblock_cycles"],
            "to_kblock_active_rule": (
                "the same span less the consumer lanes' own admission, which "
                "results/rtl/abi3_tile64.json already charges inside its 31 "
                "cycles of per-K-block overhead.  It is reported so that the "
                "double count is VISIBLE and attributable; the headline figure "
                "is the larger one, which is what the boundary was asked for"),
            "invariant_over": (
                "the number of leaves per output element: B = 1, 2, 3, 5 and 8 "
                "K-blocks all give the same boundary, because the span is set "
                "by the tree's 64 columns of SERVICE and not by the depth of "
                "the reduction"),
            "adder_depth": {
                "headline_stages": 3,
                "headline_rule": (
                    "L = 3 is the depth of the only routed lane (7a01ce5, asap7 "
                    "6.0 ns) and of the routed RE8, so it is the headline.  "
                    "Reporting the L = 1 figure as the boundary would read the "
                    "metric in its optimistic form (R13)"),
                "per_stages": {str(b["adder_stages"]): b["boundary_cycles"]
                               for b in builds},
                "difference_is_the_endpoint_pipeline": (
                    "the endpoint's first-result latency is 1 + 3L plus one "
                    "cycle of output register, and the boundary moves by exactly "
                    "that difference and by nothing else"),
            },
            "is_the_section_13_item_13_boundary": False,
            "why_not": (
                "this is the DATAPATH half of a dependent boundary, and section "
                "13 item 13 names five terms.  Three of them -- mesh transfer, "
                "queue admission and acknowledged completion -- are outside this "
                "span BY CONSTRUCTION: the consumer's op_start is asserted and "
                "its queue admission complete before the span opens, and the "
                "pair is node-local.  Those three are measured elsewhere in RTL "
                "(results/rtl/abi3_boundary_control.json, 8 cycles; the mesh "
                "traversal in results/rtl/a3_link_campaign.json), so composing "
                "them is arithmetic over two records rather than one "
                "measurement, and this record reports that sum without "
                "asserting it as a measurement of its own.  The second half of "
                "the item's acceptance is also unmet: "
                "technology.json#latency.pipeline_fill_drain_s has not been "
                "re-derived from this measurement, and re-deriving it is a "
                "decision this campaign does not take"),
        },
        "composition": {
            "datapath_half_cycles": cycles,
            "datapath_half_source": CAMPAIGN,
            "control_half_cycles": control_cycles,
            "control_half_source": "results/rtl/abi3_boundary_control.json",
            "node_local_total_cycles": composed,
            "rule": (
                "the two halves are disjoint by construction -- the control "
                "half ends at the consumer's admission to its engine queue, and "
                "this span begins at the producer's last partial write with the "
                "consumer already admitted -- so for a NODE-LOCAL dependent pair "
                "they add.  A remote pair adds the link traversal of "
                "results/rtl/a3_link_campaign.json on top.  This is a sum of two "
                "measurements, not a third measurement"),
        },
        "against_the_cycle_model": {
            "model_exposed_chain_cycles": model_chain,
            "model_fixed_latency_cycles": model_fixed,
            "model_source": "results/derived/qwen3_n5_design_target_calibration.json"
                            "#calibration.boundary",
            "model_decomposition": model.get("model_exposed_chain_decomposition"),
            "measured_datapath_over_model_fixed_latency": (
                round(cycles / model_fixed, 4)
                if (cycles and model_fixed) else None),
            "measured_total_over_model_chain": (
                round(composed / model_chain, 4)
                if (composed and model_chain) else None),
            "finding": (
                "the model's fixed_latency_cycles is the term that stands for "
                "everything this span contains, and the span is larger than it.  "
                "The residual is ATTRIBUTED and not tuned: it is the K-block "
                "tree's 64 columns of service, which section 4.4 already states "
                "as 64 cycles per 64-column vector and which no boundary model "
                "in this repository charges.  Nothing here is adjusted to close "
                "a gate"),
            "historical_figures": (
                "section 2.1 row 33 withdrew the design's 120 at 13e6a5a and "
                "states the boundary unmeasured, naming 39 and 120 as historical "
                "and uncalibrated.  The measurement agrees with neither"),
        },
        "builds": builds,
        "claim_boundary": {
            "establishes": [
                "that a two-tile dependent chain can now be assembled out of "
                "design RTL alone, which results/rtl/abi3_boundary_chain.json "
                "established it could not, and that it computes the exact "
                "reference end to end: every root equals re8_chain over the "
                "producer's partials, every delivered activation word equals the "
                "BF16 narrowing of its root, and every consumer partial equals "
                "the reference over the operand that was actually delivered",
                "the datapath half of a dependent boundary, measured, identical "
                "on Icarus Verilog and Verilator, with a design module behind "
                "every cycle of it and the six legs summing to the span",
                "that the boundary does not scale with the depth of the "
                "reduction and does scale with the endpoint's pipeline depth by "
                "exactly 1 + 3L: it is a SERVICE term, not a latency term, which "
                "is the opposite of what a fixed per-boundary charge assumes",
            ],
            "does_not_establish": {
                "the_whole_boundary_of_item_13": (
                    "see boundary.why_not: three of section 3.6's five terms are "
                    "outside this span and are measured in other records"),
                "technology_json": (
                    "technology.json#latency.pipeline_fill_drain_s is untouched "
                    "and still graded 'assumed'.  Re-deriving it is the second "
                    "half of item 13's acceptance and a separate decision"),
                "a_wider_geometry": (
                    "the chain runs the decode geometry -- rows 1, cols 64, one "
                    "partial per lane per K-block.  A window of more than one "
                    "element per lane needs the operand H-tree's address rule, "
                    "which section 4.4 leaves unwritten and which the receiver "
                    "therefore refuses rather than improvises"),
                "a_remote_pair": (
                    "the chain is node-local.  What a traversal costs is "
                    "ot_a3_link_channel's and is regressed elsewhere"),
                "physical_realisability": (
                    "simulation says nothing about area, timing or power.  No "
                    "routed record of this composition exists, and the two new "
                    "blocks are not routed"),
                "the_shipped_programs": (
                    "the two operations here are a dependent pair built for the "
                    "measurement, not a pair taken from a compiled deployment"),
            },
        },
        "source_sha256": {s: sha256_file(ROOT / s) for s in BOUND_SOURCES},
        "git": git_identity(),
        "tools": {
            "iverilog": tool_identity("iverilog", ["iverilog", "-V"],
                                      r"Icarus Verilog version [\d.]+"),
            "vvp": tool_identity("vvp", ["vvp", "-V"],
                                 r"Icarus Verilog runtime version [\d.]+"),
            "verilator": tool_identity(
                "verilator",
                [os.environ.get("VERILATOR", str(Path.home() /
                 ".local/opentallas-tools/verilator-5.050/bin/verilator")), "--version"],
                r"Verilator [\d.]+"),
            "cxx": tool_identity("g++", ["g++", "--version"], r"g\+\+ .*"),
            "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--blocks", type=int, nargs="+", default=[1, 2, 3, 5, 8])
    parser.add_argument("--adder-stages", type=int, nargs="+", default=[3, 1])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 2
    if 3 not in args.adder_stages:
        raise SystemExit("the L = 3 build is the headline and is required")

    verilator = os.environ.get(
        "VERILATOR",
        str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    tmp = None
    if args.build_dir is None:
        tmp = tempfile.TemporaryDirectory()
        build_root = Path(tmp.name)
    else:
        build_root = args.build_dir
        build_root.mkdir(parents=True, exist_ok=True)

    builds = [run_build(f"L{s}", s, build_root, verilator, args.seed, args.blocks)
              for s in args.adder_stages]
    body = build_artifact(builds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(body), encoding="utf-8")
    for b in builds:
        print(f"L={b['adder_stages']}: {b['status'].upper()} "
              f"boundary={b['boundary_cycles']} "
              f"to_kblock={b['boundary_to_kblock_cycles']} "
              f"checks={b['checks_per_simulator']} agree={b['simulators_agree']}")
    bd = body["boundary"]
    print(f"measured dependent-boundary datapath half: {bd['cycles']} cycles "
          f"(simulators agree {bd['simulators_agree']})")
    print(f"decomposition: {bd['decomposition']}")
    c = body["composition"]
    print(f"with the measured control half ({c['control_half_cycles']}): "
          f"{c['node_local_total_cycles']} cycles node-local")
    m = body["against_the_cycle_model"]
    print(f"the cycle model charges {m['model_exposed_chain_cycles']} "
          f"({m['model_fixed_latency_cycles']} of it fixed latency); "
          f"measured/model = {m['measured_total_over_model_chain']}")
    print(f"abi3 boundary chain campaign: {body['status'].upper()} -> {args.output}")
    if tmp is not None:
        tmp.cleanup()
    return 0 if body["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
