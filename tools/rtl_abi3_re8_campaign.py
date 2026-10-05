#!/usr/bin/env python3
"""Run and record the two-simulator campaign for the RE8 pairwise-tree endpoint.

The artifact is ``results/rtl/abi3_re8.json``: the binary32 pairwise endpoint
``rtl/abi3/ot_a3_tree_endpoint_fp32.sv`` checked vector by vector against the
exact K-block tree reference (``tools/am_e1_lane_reference.py``, itself
asserted against ``runtime/sim/engines/reduction.py::ordered_sum`` in
``ReductionOrder.PAIRWISE_TREE``), over the chained shapes section 4.4 names
(K = 4,096: 32 leaves; K = 12,288: 96 leaves), every leaf count 1..8, the
directed numeric corners, every fault class at every level, and a
back-to-back stream that measures throughput and latency -- on Icarus
Verilog 11 and the pinned Verilator 5.050 through two independently written
checkers that must print the same marker, the same check count and the same
rate lines, at adder depths L = 3, 2 and 1.

Every number in the artifact is one a run produced.  Tool identity, source
digests and the git state (commit and whether the tree was dirty) are recorded
so the evidence is bound to what produced it.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "testdata/rtl/abi3_re8"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_re8.json"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools"))
LEAVES = 8

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_tree_endpoint_fp32.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_re8_top.sv",
    "rtl/test/tb_a3_re8.sv",
    "rtl/test/a3_re8_harness.cpp",
)
CONTRACT_SOURCES = (
    "runtime/abi3/constants.py",
    "runtime/reference/formats.py",
    "runtime/sim/engines/reduction.py",
    "docs/CHIP_ARCHITECTURE_DESIGN.md",
)
TOOL_SOURCES = (
    "tools/am_e1_lane_reference.py",
    "tools/build_abi3_re8_vectors.py",
    "tools/rtl_abi3_re8_campaign.py",
)
VECTOR_FILES = ("re8_vec.hex", "re8_case.hex", "re8_meta.hex")

CHECKS_RE = re.compile(r"checks=(\d+)")
MARKER_RE = re.compile(r"^PASS: ABI3 re8 (.*)$", re.MULTILINE)
RATE_RE = re.compile(
    r"^RATE: case=(\d+) vectors=(\d+) outputs=(\d+) first_in=(-?\d+) first_out=(-?\d+) "
    r"last_out=(-?\d+) latency_cycles=(-?\d+) window_cycles=(\d+)$", re.MULTILINE)
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")
IVERILOG_VERSION_RE = re.compile(r"Icarus Verilog version (\d+)\.(\d+)")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(text: str, build: Path) -> str:
    return (text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>")
            .replace(str(Path.home()), "<HOME>"))


def resolve(name: str, pinned: Path | None) -> Path:
    override = os.environ.get(f"OPENTALLAS_{name.upper()}")
    if override:
        return Path(override)
    if pinned is not None and pinned.exists():
        return pinned
    found = shutil.which(name)
    if found is None:
        raise SystemExit(f"required tool is unavailable: {name}")
    return Path(found)


def tool_record(executable: Path, version_args: list[str]) -> dict[str, Any]:
    result = subprocess.run([str(executable), *version_args], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {"executable": canonical(str(executable), ROOT), "executable_sha256": sha256_file(executable),
            "version": lines[0] if lines else "no version text"}


def require_versions(tools: dict[str, dict[str, Any]]) -> None:
    match = VERILATOR_VERSION_RE.search(tools["verilator"]["version"])
    if match is None or (int(match.group(1)), int(match.group(2))) < (5, 50):
        raise SystemExit(f"Verilator {PINNED_VERILATOR_VERSION} or newer is required, found "
                         f"{tools['verilator']['version']!r}")
    match = IVERILOG_VERSION_RE.search(tools["iverilog"]["version"])
    if match is None or (int(match.group(1)), int(match.group(2))) < (11, 0):
        raise SystemExit(f"Icarus Verilog {PINNED_IVERILOG_VERSION} or newer is required, found "
                         f"{tools['iverilog']['version']!r}")


def git_state() -> dict[str, Any]:
    def run(*argv: str) -> str:
        return subprocess.run(["git", *argv], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=False).stdout.strip()
    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(status),
            "dirty_paths": sorted(line[3:] for line in status.splitlines()) if status else []}


def run_stage(name: str, command: list[str], build: Path, timeout: int,
              env: dict[str, str] | None = None) -> dict[str, Any]:
    result = subprocess.run(command, cwd=build, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, timeout=timeout, env=env)
    return {"name": name, "command": canonical(shlex.join(command), build),
            "returncode": result.returncode, "log": canonical(result.stdout, build)}


def parse_marker(log: str) -> dict[str, int] | None:
    match = MARKER_RE.search(log)
    if match is None:
        return None
    return {k: int(v) for k, v in (item.split("=") for item in match.group(1).split())}


def parse_rates(log: str) -> list[dict[str, int]]:
    keys = ("case", "vectors", "outputs", "first_in", "first_out", "last_out", "latency_cycles",
            "window_cycles")
    return [dict(zip(keys, (int(v) for v in match.groups()))) for match in RATE_RE.finditer(log)]


def simulator_case(name: str, compile_command: list[str], run_command: list[str], build: Path,
                   marker_prefix: str) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=3600)
    executed = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=4 * 3600)
    log = compiled["log"] + (executed["log"] if executed else "")
    run_log = executed["log"] if executed else ""
    marker = parse_marker(run_log)
    marker_present = marker is not None and run_log.find(marker_prefix) >= 0
    passed = (compiled["returncode"] == 0 and executed is not None and executed["returncode"] == 0
              and marker_present)
    checks = CHECKS_RE.search(run_log) if executed else None
    return {
        "name": name, "status": "pass" if passed else "fail",
        "compile_command": compiled["command"], "compile_returncode": compiled["returncode"],
        "compile_log_sha256": hashlib.sha256(compiled["log"].encode("utf-8")).hexdigest(),
        "compile_log_tail": "\n".join(compiled["log"].strip().splitlines()[-40:]),
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log_sha256": hashlib.sha256(run_log.encode("utf-8")).hexdigest(),
        "run_log_tail": "\n".join(run_log.strip().splitlines()[-60:]),
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "required_marker_prefix": marker_prefix, "marker_present": marker_present, "marker": marker,
        "checks": int(checks.group(1)) if checks else None, "rates": parse_rates(run_log),
        "first_failure": next((line.strip() for line in run_log.splitlines()
                               if line.strip().startswith(("FAIL:", "FAILURES:"))), None),
    }


def build_vectors(profile: str, adder_stages: int, out_dir: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    stage = run_stage(f"vectors.L{adder_stages}",
                      [sys.executable, str(ROOT / "tools/build_abi3_re8_vectors.py"), "--profile", profile,
                       "--adder-stages", str(adder_stages), "--out-dir", str(out_dir)], ROOT, timeout=3600, env=env)
    if stage["returncode"] != 0:
        raise SystemExit(f"vector build failed for L={adder_stages}:\n{stage['log'][-4000:]}")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    for name in VECTOR_FILES:
        if sha256_file(out_dir / name) != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    committed_path = MANIFEST_DIR / f"manifest_{profile}_L{adder_stages}.json"
    committed = json.loads(committed_path.read_text(encoding="utf-8")) if committed_path.exists() else None
    manifest["_committed_manifest"] = canonical(str(committed_path), ROOT)
    manifest["_committed_manifest_matches"] = (committed is not None
                                               and committed["image_sha256"] == manifest["image_sha256"])
    return manifest


def run_one_depth(profile: str, adder_stages: int, build: Path, executables: dict[str, Path]) -> dict[str, Any]:
    vectors_dir = build / f"vectors_L{adder_stages}"
    manifest = build_vectors(profile, adder_stages, vectors_dir)
    marker_prefix = manifest["required_marker_prefix"]
    rtl = [str(ROOT / path) for path in RTL_SOURCES]
    sim_dir = build / f"sim_L{adder_stages}"
    sim_dir.mkdir(parents=True, exist_ok=True)
    for name in VECTOR_FILES:
        shutil.copy2(vectors_dir / name, sim_dir / name)
    iverilog_compile = [str(executables["iverilog"]), "-g2012", "-s", "tb_a3_re8",
                        f"-Ptb_a3_re8.ADDER_STAGES={adder_stages}", f"-Ptb_a3_re8.LEAVES={LEAVES}",
                        "-o", "re8_sim.vvp", *rtl, str(ROOT / "rtl/test/a3_re8_top.sv"),
                        str(ROOT / "rtl/test/tb_a3_re8.sv")]
    verilator_compile = [str(executables["verilator"]), "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
                         "-Wno-DECLFILENAME", "--top-module", "ot_a3_re8_top",
                         f"-GADDER_STAGES={adder_stages}", f"-GLEAVES={LEAVES}", "--Mdir", "obj_re8", *rtl,
                         str(ROOT / "rtl/test/a3_re8_top.sv"), str(ROOT / "rtl/test/a3_re8_harness.cpp"),
                         "-CFLAGS", "-std=c++17 -O2", "-j", "8"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(simulator_case, "iverilog", iverilog_compile,
                               [str(executables["vvp"]), "re8_sim.vvp"], sim_dir, marker_prefix),
                   pool.submit(simulator_case, "verilator", verilator_compile,
                               ["./obj_re8/Vot_a3_re8_top"], sim_dir, marker_prefix)]
        simulators = [future.result() for future in futures]
    agree = (all(s["status"] == "pass" for s in simulators)
             and len({json.dumps(s["marker"], sort_keys=True) for s in simulators}) == 1
             and len({s["checks"] for s in simulators}) == 1
             and len({json.dumps(s["rates"], sort_keys=True) for s in simulators}) == 1)
    return {
        "adder_stages": adder_stages, "status": "pass" if agree else "fail", "simulators_agree": agree,
        "vectors": {
            "manifest_sha256": sha256_file(vectors_dir / "manifest.json"),
            "committed_manifest": manifest["_committed_manifest"],
            "committed_manifest_matches": manifest["_committed_manifest_matches"],
            "image_sha256": manifest["image_sha256"], "totals": manifest["totals"],
            "case_count": len(manifest["cases"]), "reference": manifest["reference"],
            "failure_modes": manifest["failure_modes"], "rate_cases": manifest["rate_cases"],
            "cases": [{k: c[k] for k in ("id", "name", "note", "vectors", "stream", "rate", "mode_name",
                                         "leaves_in_chain", "shape", "expected", "extras")}
                      for c in manifest["cases"]],
        },
        "simulators": simulators,
    }


def run(profile: str, depths: list[int], build_root: Path | None) -> dict[str, Any]:
    executables = {
        "iverilog": resolve("iverilog", None), "vvp": resolve("vvp", None),
        "verilator": resolve("verilator", TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"),
        "cxx": resolve("g++", None), "python": Path(sys.executable),
    }
    version_flags = {"iverilog": ["-V"], "vvp": ["-V"], "verilator": ["--version"], "cxx": ["--version"],
                     "python": ["--version"]}
    tools = {name: tool_record(path, version_flags[name]) for name, path in executables.items()}
    require_versions(tools)
    git = git_state()

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-re8-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=max(1, len(depths))) as pool:
            depth_results = list(pool.map(lambda d: run_one_depth(profile, d, build, executables), depths))

    sources = {path: sha256_file(ROOT / path)
               for path in sorted(RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES)}
    for depth in depths:
        committed = MANIFEST_DIR / f"manifest_{profile}_L{depth}.json"
        if committed.exists():
            sources[canonical(str(committed), ROOT).replace("<ROOT>/", "")] = sha256_file(committed)

    all_pass = all(d["status"] == "pass" for d in depth_results)
    manifests_match = all(d["vectors"]["committed_manifest_matches"] for d in depth_results)

    # -- throughput and latency per depth -----------------------------------------------------
    rates_by_depth: dict[str, list[dict[str, Any]]] = {}
    for d in depth_results:
        rows = []
        for sim in d["simulators"]:
            for entry in sim["rates"]:
                window = entry["window_cycles"]
                rows.append(dict(entry, simulator=sim["name"],
                                 combines_per_cycle=(entry["outputs"] / window) if window else None,
                                 adds_per_cycle=(7 * entry["outputs"] / window) if window else None))
        rates_by_depth[f"L{d['adder_stages']}"] = rows
    primary = f"L{depths[0]}"
    primary_rows = [r for r in rates_by_depth[primary] if r["simulator"] == "verilator"] or rates_by_depth[primary]
    combines_per_cycle = min((r["combines_per_cycle"] for r in primary_rows if r["combines_per_cycle"]), default=None)
    latency = {f"L{d['adder_stages']}": (d["simulators"][0]["rates"][0]["latency_cycles"]
                                         if d["simulators"] and d["simulators"][0]["rates"] else None)
               for d in depth_results}
    if not all_pass:
        combines_per_cycle = 0.0 if combines_per_cycle is None else combines_per_cycle

    # -- fail-closed modes ---------------------------------------------------------------------
    mode_table = depth_results[0]["vectors"]["failure_modes"] if depth_results else {}
    observed = {name: dict(entry, observed_on=["iverilog", "verilator"] if all_pass else [])
                for name, entry in mode_table.items()}
    preserved = ("add_range_level1", "add_range_tie_level1", "add_range_level2", "add_range_level3",
                 "leaf_nonfinite_nan", "leaf_nonfinite_infinity", "leaf_count_zero", "leaf_count_over",
                 "fault_mid_stream", "fault_single_step")
    all_present = all(name in mode_table for name in preserved)
    class_pairs = {(e["error_code"], e["error_detail"]) for e in mode_table.values()}
    three_classes = class_pairs == {(1, 24), (3, 25), (7, 26)}
    all_distinct = all_pass and all_present and three_classes

    status = "pass" if (all_pass and manifests_match and combines_per_cycle is not None
                        and combines_per_cycle >= 1.0 and all_distinct) else "fail"

    return {
        "schema": "opentallas.rtl.abi3_re8.v1",
        "campaign": "rtl3_abi3_re8",
        "profile": profile,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "design": {
            "module": "rtl/abi3/ot_a3_tree_endpoint_fp32.sv",
            "leaves": LEAVES,
            "levels": 3,
            "adders": 7,
            "adder": ("rtl/abi3/ot_a3_lane_pkg.sv acc_align / acc_sum_normalise / acc_round_pack, the lane's "
                      "binary32 RNE cut, with the right operand in the lane's group form (an exact shift)"),
            "association": ("ReductionOrder.PAIRWISE_TREE over ascending block index: fold adjacent pairs, "
                            "odd tail carried (a mux); three levels per endpoint over one aligned group of "
                            "at most 8 nodes; endpoints chained stage by stage"),
            "adder_stages_run": depths,
            "columns_per_cycle": 1,
            "pipeline_registers": {f"L{d}": 1 + 3 * d + 1 for d in depths},
            "signed_zero": "a -0.0 leaf is canonicalised to +0.0 at the input; no lane partial is ever -0.0",
            "fault_policy": ("sticky, in input order: a nonfinite valid leaf (class 1, detail 24), an add "
                             "reaching 2**128 (class 3, detail 25), a leaf count of 0 or above 8 (class 7, "
                             "detail 26); the faulting vector and everything after it emit nothing until clear"),
        },
        "git": git,
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "all_depths_pass": all_pass,
        "vector_manifests_match_committed": manifests_match,
        "bit_identity": {
            "equal": all_pass and manifests_match,
            "basis": ("every vector's output is compared, code for code, with tools/am_e1_lane_reference.py's "
                      "re8_combine, which is asserted equal to pairwise_tree, which is asserted equal to "
                      "runtime/sim/engines/reduction.py::ordered_sum(PAIRWISE_TREE) on numpy float32 leaves; "
                      "both checkers must print the same marker and check count; one differing bit fails"),
            "reference": "tools/am_e1_lane_reference.py (re8_combine / re8_chain / pairwise_tree)",
            "checks_per_depth": {f"L{d['adder_stages']}": {s["name"]: s["checks"] for s in d["simulators"]}
                                 for d in depth_results},
            "markers_per_depth": {f"L{d['adder_stages']}": {s["name"]: s["marker"] for s in d["simulators"]}
                                  for d in depth_results},
        },
        "measured": {
            "combines_per_cycle": combines_per_cycle,
            "adds_per_cycle": (7.0 * combines_per_cycle) if combines_per_cycle else combines_per_cycle,
            "latency_cycles_by_depth": latency,
            "definition": (
                "combines_per_cycle: full 8-leaf vectors committed by the endpoint divided by the clock cycles "
                "from the first to the last output (inclusive) of the back-to-back stream case, as counted by "
                f"both checkers on the L = {depths[0]} build; adds_per_cycle is 7 x that (4 + 2 + 1 binary32 "
                "RNE adds per full combine).  latency_cycles: rising edges from the edge that samples a vector "
                "to the edge at which its result is registered (1 + 3 L)"),
            "primary_adder_stages": depths[0],
            "rates_by_depth": rates_by_depth,
        },
        "failure_modes": {
            "all_distinct": all_distinct,
            "policy": ("every fault case is run on both simulators; the endpoint must report the expected class, "
                       "detail, level and tag, emit exactly the vectors before the fault, ignore input until clear, "
                       "and the three (class, detail) pairs must be the three the module declares"),
            "preserved_modes": list(preserved),
            "modes": observed,
            "fault_cases_pass_on_both_simulators": all_pass,
        },
        "tools": tools,
        "source_sha256": sources,
        "depths": depth_results,
        "claim_boundary": {
            "establishes": [
                "the endpoint produces, on both simulators, exactly the binary32 codes reduction.py's PAIRWISE_TREE "
                "recurrence produces on the same leaves, for every leaf count 1..8, over the chained shapes of "
                "K = 4,096 and K = 12,288 and the directed numeric corners",
                "one 8-leaf combine per cycle in steady state (measured) and the pipeline latency per depth (measured)",
                "the three fault classes trap distinctly, sticky, in input order, and clear restarts the endpoint",
            ],
            "does_not_establish": {
                "physical_realisability": "simulation says nothing about area or timing; results/physical_abi3/asap7/a3_re8/pnr.json is the routed record",
                "tree_latency": "the design's 25-35 cycle tree latency at N5 includes hop cycles this endpoint does not model",
                "tile_integration": "the tile-side chaining over captured partials is the T64 campaign's (results/rtl/abi3_tile64.json)",
                "signed_zero_tail": "a -0.0 leaf is canonicalised; reduction.py would carry it as -0.0; the case never arises from a lane partial",
                "exhaustive_arithmetic": "the vectors are seeded and directed, not exhaustive over the operand space",
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("quick", "full"), default="full")
    parser.add_argument("--adder-stages", default="3,2,1")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force to replace it", file=sys.stderr)
        return 2
    depths = [int(v) for v in args.adder_stages.split(",") if v.strip()]
    summary = run(args.profile, depths, args.build_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for depth in summary["depths"]:
        for sim in depth["simulators"]:
            print(f"L={depth['adder_stages']} {sim['name']}: {sim['status'].upper()} checks={sim['checks']}"
                  + (f" first_failure={sim['first_failure']}" if sim["first_failure"] else ""))
    print(f"measured.combines_per_cycle={summary['measured']['combines_per_cycle']} "
          f"latency={summary['measured']['latency_cycles_by_depth']} "
          f"failure_modes.all_distinct={summary['failure_modes']['all_distinct']}")
    print(f"abi3 re8 campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
