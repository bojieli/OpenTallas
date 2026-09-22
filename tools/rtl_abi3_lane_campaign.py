#!/usr/bin/env python3
"""Run and record the two-simulator campaign for the pipelined lane gates.

Gates D1, D2 and D5 of ``docs/OPENTALLAS_REDESIGN_PLAN.md`` (evaluators in
``configs/gates/redesign_gates.json``) read one artifact family,
``results/rtl/*pipelined_lane*.json``:

    D1  bit_identity.equal == true
    D2  measured.mac_per_lane_cycle >= 1.0
    D5  failure_modes.all_distinct == true

This tool produces them.  It regenerates the vector images deterministically
(``tools/build_abi3_lane_vectors.py``), checks their digests against the
committed manifest, compiles the same RTL twice -- Icarus Verilog 11 through
``rtl/test/tb_a3_lane_pipelined.sv`` and the pinned Verilator 5.050 through
``rtl/test/a3_lane_pipelined_harness.cpp`` -- for every adder depth requested,
and requires both to print the same marker, the same check count and the same
rate lines.  Two checkers that disagree are not a result.

Every number in the artifact is one a run produced: the rate is lane-ops
divided by the cycles between the first and the last retired lane-op of the
steady-state case, as both checkers counted them; the identity is the checkers'
own element-by-element comparison of the two lanes; the failure modes are the
(class, detail) pairs both simulators observed on each fault case.  Tool
identity, source digests, and the git state (commit and whether the tree was
dirty) are recorded so the evidence is bound to what produced it.
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
MANIFEST_DIR = ROOT / "testdata/rtl/abi3_lane_pipelined"
DEFAULT_OUTPUTS = {
    "d1": ROOT / "results/rtl/abi3_pipelined_lane.json",
    "groups": ROOT / "results/rtl/abi3_pipelined_lane_groups.json",
}

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools"))

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/proto/ot_fp32_mul_rne_pipe.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    "rtl/abi3/ot_a3_lane_pipelined.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_lane_pipelined_top.sv",
    "rtl/test/tb_a3_lane_pipelined.sv",
    "rtl/test/a3_lane_pipelined_harness.cpp",
)
CONTRACT_SOURCES = (
    "runtime/abi3/constants.py",
    "runtime/reference/formats.py",
    "runtime/sim/formats.py",
    "runtime/sim/backend.py",
    "runtime/sim/engines/tensor.py",
    "docs/CHIP_ARCHITECTURE_DESIGN.md",
)
TOOL_SOURCES = (
    "tools/am_e1_lane_reference.py",
    "tools/build_abi3_lane_vectors.py",
    "tools/rtl_abi3_lane_campaign.py",
)
VECTOR_FILES = ("lane_m0.hex", "lane_m1.hex", "lane_m2.hex", "lane_m3.hex",
                "lane_case.hex", "lane_expect.hex", "lane_meta.hex")

CHECKS_RE = re.compile(r"checks=(\d+)")
MARKER_RE = re.compile(r"^PASS: ABI3 pipelined lane (.*)$", re.MULTILINE)
RATE_RE = re.compile(
    r"^RATE: case=(\d+) lane_ops=(\d+) products=(\d+) total_cycles=(\d+) "
    r"window_cycles=(\d+) first_retire=(-?\d+) last_retire=(-?\d+)$", re.MULTILINE)
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
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
                            timeout=60)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "executable": canonical(str(executable), ROOT),
        "executable_sha256": sha256_file(executable),
        "version": lines[0] if lines else "no version text",
    }


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
    return {
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(status),
        "dirty_paths": sorted(line[3:] for line in status.splitlines()) if status else [],
    }


def run_stage(name: str, command: list[str], build: Path, timeout: int,
              env: dict[str, str] | None = None) -> dict[str, Any]:
    result = subprocess.run(command, cwd=build, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, timeout=timeout, env=env)
    return {
        "name": name,
        "command": canonical(shlex.join(command), build),
        "returncode": result.returncode,
        "log": canonical(result.stdout, build),
    }


def parse_marker(log: str) -> dict[str, int] | None:
    match = MARKER_RE.search(log)
    if match is None:
        return None
    fields: dict[str, int] = {}
    for item in match.group(1).split():
        key, value = item.split("=")
        fields[key] = int(value)
    return fields


def parse_rates(log: str) -> list[dict[str, int]]:
    keys = ("case", "lane_ops", "products", "total_cycles", "window_cycles",
            "first_retire", "last_retire")
    return [dict(zip(keys, (int(v) for v in match.groups())))
            for match in RATE_RE.finditer(log)]


def simulator_case(name: str, compile_command: list[str], run_command: list[str],
                   build: Path, marker_prefix: str) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=3600)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=6 * 3600)
    log = compiled["log"] + (executed["log"] if executed else "")
    run_log = executed["log"] if executed else ""
    marker = parse_marker(run_log)
    marker_present = marker is not None and run_log.find(marker_prefix) >= 0
    passed = (compiled["returncode"] == 0 and executed is not None
              and executed["returncode"] == 0 and marker_present)
    checks = CHECKS_RE.search(run_log) if executed else None
    tail = "\n".join(run_log.strip().splitlines()[-60:])
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log_sha256": hashlib.sha256(compiled["log"].encode("utf-8")).hexdigest(),
        "compile_log_tail": "\n".join(compiled["log"].strip().splitlines()[-40:]),
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log_sha256": hashlib.sha256(run_log.encode("utf-8")).hexdigest(),
        "run_log_tail": tail,
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "required_marker_prefix": marker_prefix,
        "marker_present": marker_present,
        "marker": marker,
        "checks": int(checks.group(1)) if checks else None,
        "rates": parse_rates(run_log),
        "first_failure": next((line.strip() for line in run_log.splitlines()
                               if line.strip().startswith(("FAIL:", "FAILURES:"))), None),
    }


def build_vectors(suite: str, profile: str, adder_stages: int, out_dir: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    stage = run_stage(
        f"vectors.L{adder_stages}",
        [sys.executable, str(ROOT / "tools/build_abi3_lane_vectors.py"), "--suite", suite,
         "--profile", profile, "--adder-stages", str(adder_stages), "--out-dir", str(out_dir)],
        ROOT, timeout=3 * 3600, env=env,
    )
    if stage["returncode"] != 0:
        raise SystemExit(f"vector build failed for L={adder_stages}:\n{stage['log'][-4000:]}")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    for name in VECTOR_FILES:
        actual = sha256_file(out_dir / name)
        if actual != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    committed_path = MANIFEST_DIR / suite / f"manifest_{profile}_L{adder_stages}.json"
    committed = json.loads(committed_path.read_text(encoding="utf-8")) if committed_path.exists() else None
    manifest["_committed_manifest"] = canonical(str(committed_path), ROOT)
    manifest["_committed_manifest_matches"] = (
        committed is not None and committed["image_sha256"] == manifest["image_sha256"]
    )
    manifest["_build_log"] = stage["log"][-2000:]
    return manifest


def run_one_depth(suite: str, profile: str, adder_stages: int, build: Path,
                  executables: dict[str, Path]) -> dict[str, Any]:
    vectors_dir = build / f"vectors_L{adder_stages}"
    manifest = build_vectors(suite, profile, adder_stages, vectors_dir)
    marker_prefix = manifest["required_marker_prefix"]
    rtl = [str(ROOT / path) for path in RTL_SOURCES]
    sim_dir = build / f"sim_L{adder_stages}"
    sim_dir.mkdir(parents=True, exist_ok=True)
    for name in VECTOR_FILES:
        shutil.copy2(vectors_dir / name, sim_dir / name)
    iverilog_compile = [
        str(executables["iverilog"]), "-g2012", "-s", "tb_a3_lane_pipelined",
        f"-Ptb_a3_lane_pipelined.ADDER_STAGES={adder_stages}",
        "-o", "lane_sim.vvp", *rtl,
        str(ROOT / "rtl/test/a3_lane_pipelined_top.sv"),
        str(ROOT / "rtl/test/tb_a3_lane_pipelined.sv"),
    ]
    verilator_compile = [
        str(executables["verilator"]), "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
        "-Wno-DECLFILENAME", "--top-module", "ot_a3_lane_pipelined_top",
        f"-GADDER_STAGES={adder_stages}", "--Mdir", "obj_lane", *rtl,
        str(ROOT / "rtl/test/a3_lane_pipelined_top.sv"),
        str(ROOT / "rtl/test/a3_lane_pipelined_harness.cpp"),
        "-CFLAGS", "-std=c++17 -O2",
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(simulator_case, "iverilog", iverilog_compile,
                        [str(executables["vvp"]), "lane_sim.vvp"], sim_dir, marker_prefix),
            pool.submit(simulator_case, "verilator", verilator_compile,
                        ["./obj_lane/Vot_a3_lane_pipelined_top"], sim_dir, marker_prefix),
        ]
        simulators = [future.result() for future in futures]
    agree = (
        all(s["status"] == "pass" for s in simulators)
        and len({json.dumps(s["marker"], sort_keys=True) for s in simulators}) == 1
        and len({s["checks"] for s in simulators}) == 1
        and len({json.dumps(s["rates"], sort_keys=True) for s in simulators}) == 1
    )
    return {
        "adder_stages": adder_stages,
        "status": "pass" if agree else "fail",
        "simulators_agree": agree,
        "vectors": {
            "manifest_sha256": sha256_file(vectors_dir / "manifest.json"),
            "committed_manifest": manifest["_committed_manifest"],
            "committed_manifest_matches": manifest["_committed_manifest_matches"],
            "image_sha256": manifest["image_sha256"],
            "geometry": manifest["geometry"],
            "totals": manifest["totals"],
            "case_count": len(manifest["cases"]),
            "sweep_products": manifest.get("sweep_products"),
            "sweep_plan": manifest.get("sweep_plan"),
            "reference": manifest["reference"],
            "failure_modes": manifest["failure_modes"],
            "rate_cases": manifest["rate_cases"],
            "cases": [
                {k: c[k] for k in ("id", "name", "note", "rows", "cols", "depth", "dtype_a",
                                   "dtype_b", "group", "scaled_a", "scaled_b", "out_fp32",
                                   "run_reference", "rate", "products", "mode_name", "expected",
                                   "extras")}
                for c in manifest["cases"]
            ],
        },
        "simulators": simulators,
    }


def rate_from(depth_result: dict[str, Any], manifest_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per rate case, the measured rates (identical on both simulators when agree)."""
    by_id = {c["id"]: c for c in manifest_cases}
    rates: list[dict[str, Any]] = []
    for sim in depth_result["simulators"]:
        for entry in sim["rates"]:
            case = by_id.get(entry["case"], {})
            window = entry["window_cycles"]
            total = entry["total_cycles"]
            rates.append({
                "simulator": sim["name"],
                "case": entry["case"],
                "name": case.get("name"),
                "group": case.get("group"),
                "lane_ops": entry["lane_ops"],
                "products": entry["products"],
                "window_cycles": window,
                "total_cycles": total,
                "first_retire_cycle": entry["first_retire"],
                "last_retire_cycle": entry["last_retire"],
                "lane_ops_per_window_cycle": (entry["lane_ops"] / window) if window else None,
                "products_per_window_cycle": (entry["products"] / window) if window else None,
                "lane_ops_per_total_cycle": (entry["lane_ops"] / total) if total else None,
            })
    return rates


def run(suite: str, profile: str, depths: list[int], build_root: Path | None) -> dict[str, Any]:
    executables = {
        "iverilog": resolve("iverilog", None),
        "vvp": resolve("vvp", None),
        "verilator": resolve("verilator", TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"),
        "cxx": resolve("g++", None),
        "python": Path(sys.executable),
    }
    version_flags = {"iverilog": ["-V"], "vvp": ["-V"], "verilator": ["--version"],
                     "cxx": ["--version"], "python": ["--version"]}
    tools = {name: tool_record(path, version_flags[name]) for name, path in executables.items()}
    require_versions(tools)
    git = git_state()

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-lane-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        # Each depth is an independent build; run them side by side (two
        # simulator processes each) and keep the requested order.
        with ThreadPoolExecutor(max_workers=max(1, len(depths))) as pool:
            depth_results = list(pool.map(
                lambda depth: run_one_depth(suite, profile, depth, build, executables), depths))

    sources = {path: sha256_file(ROOT / path)
               for path in sorted(RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES)}
    for depth in depths:
        committed = MANIFEST_DIR / suite / f"manifest_{profile}_L{depth}.json"
        if committed.exists():
            sources[canonical(str(committed), ROOT).replace("<ROOT>/", "")] = sha256_file(committed)

    all_pass = all(d["status"] == "pass" for d in depth_results)
    manifests_match = all(d["vectors"]["committed_manifest_matches"] for d in depth_results)

    # -- D1: bit identity ---------------------------------------------------------------
    identity_counts = {}
    reference_counts = {}
    for d in depth_results:
        markers = [s["marker"] for s in d["simulators"] if s["marker"]]
        identity_counts[f"L{d['adder_stages']}"] = markers[0].get("identity") if markers else None
        reference_counts[f"L{d['adder_stages']}"] = markers[0].get("reference_cases") if markers else None
    if suite == "d1":
        identity_equal = (all_pass and manifests_match
                          and all(v and v > 0 for v in identity_counts.values())
                          and all(v and v > 0 for v in reference_counts.values()))
        identity_basis = (
            "every case is run on rtl/abi3/ot_a3_lane_pipelined.sv and on the untouched "
            "rtl/abi3/ot_a3_mac_lane.sv from one operand image; both checkers compare, element by "
            "element, the BF16 output word and the binary32 accumulator of the two lanes directly, "
            "and each lane against the exact expectation; error classes and counters are compared "
            "as well; one differing bit fails the marker"
        )
    else:
        identity_equal = all_pass and manifests_match
        identity_basis = (
            "no RTL reference exists for the AM-E1 association; every element is compared against "
            "the exact Python reference tools/am_e1_lane_reference.py on both simulators, and the "
            "two simulators must agree on every observation.  The D1 gate proper is the BF16 g = 1 "
            "artifact results/rtl/abi3_pipelined_lane.json"
        )

    # -- D2: measured rate ---------------------------------------------------------------
    rates_by_depth = {f"L{d['adder_stages']}": rate_from(d, d["vectors"]["cases"]) for d in depth_results}
    primary_depth = f"L{depths[0]}"
    primary_rates = [r for r in rates_by_depth[primary_depth] if r["simulator"] == "verilator"] or \
                    rates_by_depth[primary_depth]
    gate_rate = None
    for r in primary_rates:
        if r["lane_ops_per_window_cycle"] is not None:
            gate_rate = r["lane_ops_per_window_cycle"] if gate_rate is None else min(gate_rate, r["lane_ops_per_window_cycle"])
    products_by_group = {}
    for r in primary_rates:
        if r["products_per_window_cycle"] is not None:
            products_by_group[f"g{r['group']}"] = r["products_per_window_cycle"]
    if not all_pass:
        gate_rate = 0.0 if gate_rate is None else gate_rate

    # -- D5: distinct failure modes --------------------------------------------------------
    mode_table = depth_results[0]["vectors"]["failure_modes"] if depth_results else {}
    fault_cases_passed = all_pass
    observed = {}
    for name, entry in mode_table.items():
        observed[name] = {
            "case": entry["case"], "case_name": entry["name"],
            "error_code": entry["error_code"], "error_detail": entry["error_detail"],
            "detail_name": entry["detail_name"],
            "observed_on": ["iverilog", "verilator"] if fault_cases_passed else [],
        }
    detail_pairs = [(e["error_code"], e["error_detail"]) for e in mode_table.values()]
    preserved = ("nonfinite_bf16_operand_a", "nonfinite_bf16_operand_b",
                 "reserved_e4m3fn_operand_a", "reserved_e4m3fn_operand_b",
                 "reserved_e8m0_scale_a", "reserved_e8m0_scale_b",
                 "scale_application_range_a", "scale_application_range_b",
                 "product_range", "accumulate_range", "shape") if suite == "d1" else (
                 "reserved_e4m3fn_operand_a", "reserved_e4m3fn_operand_b",
                 "reserved_e8m0_scale_a", "reserved_e8m0_scale_b",
                 "scale_application_range_a", "scale_application_range_b",
                 "product_range", "accumulate_range", "shape")
    all_present = all(name in mode_table for name in preserved)
    all_distinct = (fault_cases_passed and all_present and len(set(detail_pairs)) == len(detail_pairs)
                    and all(e["error_code"] != 0 for e in mode_table.values()))

    status = "pass" if (all_pass and manifests_match and identity_equal
                        and gate_rate is not None and gate_rate >= 1.0 and all_distinct) else "fail"

    return {
        "schema": "opentallas.rtl.abi3_pipelined_lane.v1",
        "campaign": f"rtl3_abi3_pipelined_lane_{suite}",
        "suite": suite,
        "profile": profile,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "design": {
            "module": "rtl/abi3/ot_a3_lane_pipelined.sv",
            "reference": "rtl/abi3/ot_a3_mac_lane.sv (untouched)",
            "numeric_package": "rtl/abi3/ot_a3_lane_pkg.sv",
            "adder_stages_run": depths,
            "acc_slots": 8,
            "association": "AM-E1: g products exact, summed exactly, one RNE32 per group; g = 1 is bf16_bf16_fp32_sequential_rne_v1 with K_BLOCK = K",
            "group_aligner_bits": 48,
            "adder_frame_bits": 52,
        },
        "git": git,
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "all_depths_pass": all_pass,
        "vector_manifests_match_committed": manifests_match,
        "bit_identity": {
            "equal": identity_equal,
            "basis": identity_basis,
            "reference": "rtl/abi3/ot_a3_mac_lane.sv" if suite == "d1" else "tools/am_e1_lane_reference.py",
            "identity_element_pairs_per_depth": identity_counts,
            "reference_cases_per_depth": reference_counts,
            "checks_per_depth": {f"L{d['adder_stages']}": {s["name"]: s["checks"] for s in d["simulators"]}
                                 for d in depth_results},
            "markers_per_depth": {f"L{d['adder_stages']}": {s["name"]: s["marker"] for s in d["simulators"]}
                                  for d in depth_results},
            "sweep_products": depth_results[0]["vectors"]["sweep_products"] if depth_results else None,
            "sweep_plan": depth_results[0]["vectors"]["sweep_plan"] if depth_results else None,
        },
        "measured": {
            "mac_per_lane_cycle": gate_rate,
            "definition": (
                "lane-ops retired divided by the clock cycles from the first to the last retired "
                "lane-op (inclusive) of the steady-state case, as counted by both checkers on the "
                f"L = {depths[0]} build; a lane-op is one multiply-accumulate of g products.  The "
                "minimum over the suite's rate cases is reported.  The same lane-ops divided by the "
                "whole run's cycles (fill and drain included) is beside it"
            ),
            "products_per_lane_cycle_by_group": products_by_group,
            "primary_adder_stages": depths[0],
            "rates_by_depth": rates_by_depth,
        },
        "failure_modes": {
            "all_distinct": all_distinct,
            "policy": (
                "every fault case is run on both simulators; the lane must stop with the expected "
                "error class (the sequential lane's code) and the expected error detail (one per "
                "mode), write exactly the elements of the passes completed before the faulting "
                "pass and nothing after, and the (class, detail) pairs of the preserved modes must "
                "be pairwise distinct"
            ),
            "preserved_modes": list(preserved),
            "modes": observed,
            "fault_cases_pass_on_both_simulators": fault_cases_passed,
        },
        "tools": tools,
        "source_sha256": sources,
        "depths": depth_results,
        "claim_boundary": {
            "establishes": [
                ("the pipelined lane retires one lane-op per cycle in steady state and, for BF16 at "
                 "g = 1 and K_BLOCK = K, produces bit-identical binary32 accumulators, BF16 outputs, "
                 "counters and error classes to the untouched sequential lane over the swept space, "
                 "under two independently written checkers on two simulators")
                if suite == "d1" else
                ("the pipelined lane's FP8 g = 2 and MXFP4 g = 4 group modes produce, on both "
                 "simulators, exactly the binary32 accumulators the exact AM-E1 reference computes, "
                 "including directed cases that differ from the sequential association, and refuse "
                 "every preserved failure mode with a distinct detail"),
                "the fault commit order is the issue order, so the written set on a refusal is deterministic and was checked element by element",
            ],
            "does_not_establish": {
                "physical_realisability": "simulation says nothing about area, timing or power; gates D3 and D4 are separate artifacts",
                "k_block_tree": "K_BLOCK = K here; the pairwise tree over K-blocks (AM-E1 item 2) is outside the lane",
                "bf16_in_group_modes": "a BF16 operand in a group mode is refused fail-closed because the exact aligner is sized for the block formats' exponent ranges; E2M1 x BF16 at g = 4 is not implemented",
                "integration": "the lane is driven directly by the checkers; no tile sequencer, staging SRAM or H-tree is modelled",
                "exhaustive_arithmetic": "the sweep is seeded and directed, not exhaustive over the operand space",
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("d1", "groups"), required=True)
    parser.add_argument("--profile", choices=("quick", "full"), default="full")
    parser.add_argument("--adder-stages", default="3,2,1",
                        help="comma-separated adder depths to run; the first is the gate's primary")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    output = args.output or DEFAULT_OUTPUTS[args.suite]
    if output.exists() and not args.force:
        print(f"refusing to overwrite {output}; pass --force to replace it", file=sys.stderr)
        return 2
    depths = [int(v) for v in args.adder_stages.split(",") if v.strip()]
    summary = run(args.suite, args.profile, depths, args.build_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for depth in summary["depths"]:
        for sim in depth["simulators"]:
            print(f"L={depth['adder_stages']} {sim['name']}: {sim['status'].upper()} checks={sim['checks']}"
                  + (f" first_failure={sim['first_failure']}" if sim["first_failure"] else ""))
    print(f"bit_identity.equal={summary['bit_identity']['equal']} "
          f"measured.mac_per_lane_cycle={summary['measured']['mac_per_lane_cycle']} "
          f"failure_modes.all_distinct={summary['failure_modes']['all_distinct']}")
    print(f"abi3 pipelined lane campaign ({args.suite}): {summary['status'].upper()} -> {output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
