#!/usr/bin/env python3
"""Run and record the two-simulator campaign for ROUTE.BLOCK_MAX.

The artifact is ``results/rtl/a3_v41_block_max_campaign.json``: every expected
block score comes from the independent reference
``runtime.reference.candidate_pool.block_max_rows``, and every one of them is
checked by TWO independently written checkers over the SAME RTL --
``rtl/test/tb_a3_route_block_max.sv`` on Icarus Verilog 11 and
``rtl/test/a3_route_block_max_harness.cpp`` on the PINNED Verilator 5.050 (the
Verilator on PATH is 4.038 and is never used) -- which must print the same
marker, the same check count and the same rate lines.

Seven elaborated shapes are run, not one: the V4.1 candidate pool (binary32,
BLOCK = 8, 2,048 blocks per row, one register stage per comparator level), a
deeper pipelining factor, a non-power-of-two block, a wider block, the
degenerate BLOCK = 1, a BF16 score and an FP16 score with three stages per
level.  The point of the sweep is the acceptance criterion that no model
geometry is frozen into the block: the same RTL and the same builder produce
all seven.

Every number in the artifact is one a run produced.  Tool identity, source
digests and the git state are recorded, and ``claim_boundary`` states what the
run does NOT establish.
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
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_v41_block_max_campaign.json"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools"))

RTL_SOURCES = (
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_route_block_max.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_route_block_max_top.sv",
    "rtl/test/tb_a3_route_block_max.sv",
    "rtl/test/a3_route_block_max_harness.cpp",
)
REFERENCE_SOURCES = (
    "runtime/reference/candidate_pool.py",
)
CONTRACT_SOURCES = (
    "compiler/ir/v3/kernel_ir.py",
    "compiler/ir/v3/lowering.py",
    "runtime/abi3/constants.py",
    "rtl/abi3/ot_a3_pkg.sv",
    "docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md",
)
TOOL_SOURCES = (
    "tools/build_a3_v41_block_max_vectors.py",
    "tools/run_a3_v41_block_max_rtl_campaign.py",
)
IMAGE_FILES = ("bm_meta.hex", "bm_case.hex", "bm_vec.hex", "bm_expect.hex")

#: the elaborated shapes.  The first is the V4.1 candidate pool; the rest exist
#: to show that the block's geometry is parameters and not constants.
CONFIGURATIONS: tuple[dict[str, Any], ...] = (
    {"name": "v41_binary32_block8", "block": 8, "exponent_bits": 8, "mantissa_bits": 23,
     "max_blocks": 2048, "cmp_stages": 1, "rate_blocks": 256,
     "note": "the DeepSeek-V4.1-Flash candidate pool: binary32 scores, blocks of 8, "
             "2,048 blocks per row, one register stage per comparator level"},
    {"name": "binary32_block8_cmp2", "block": 8, "exponent_bits": 8, "mantissa_bits": 23,
     "max_blocks": 2048, "cmp_stages": 2, "rate_blocks": 256,
     "note": "the same pool with two register stages per comparator level: the latency "
             "changes, no value does, and the initiation interval stays 1"},
    {"name": "binary32_block6_rows64", "block": 6, "exponent_bits": 8, "mantissa_bits": 23,
     "max_blocks": 64, "cmp_stages": 1, "rate_blocks": 64,
     "note": "a NON-POWER-OF-TWO block and a small row bound: the tree is built over 8 "
             "leaves with two of them held at the padding value"},
    {"name": "binary32_block16", "block": 16, "exponent_bits": 8, "mantissa_bits": 23,
     "max_blocks": 128, "cmp_stages": 1, "rate_blocks": 128,
     "note": "a wider block: four comparator levels"},
    {"name": "binary32_block1", "block": 1, "exponent_bits": 8, "mantissa_bits": 23,
     "max_blocks": 32, "cmp_stages": 1, "rate_blocks": 32,
     "note": "the degenerate block: no comparator level at all, the block score is the "
             "position's score, and the stream still sustains one per cycle"},
    {"name": "bf16_block4", "block": 4, "exponent_bits": 8, "mantissa_bits": 7,
     "max_blocks": 512, "cmp_stages": 1, "rate_blocks": 256,
     "note": "BF16 scores: the order is the format's, not binary32's"},
    {"name": "fp16_block8_cmp3", "block": 8, "exponent_bits": 5, "mantissa_bits": 10,
     "max_blocks": 64, "cmp_stages": 3, "rate_blocks": 64,
     "note": "FP16 scores with three register stages per level: a different exponent "
             "field and a deeper pipeline"},
)

MARKER_RE = re.compile(r"^PASS: A3 V41 BLOCK_MAX (.*)$", re.MULTILINE)
CHECKS_RE = re.compile(r"checks=(\d+)")
RATE_RE = re.compile(
    r"^RATE: case=(\d+) outputs=(\d+) window=(\d+) first=(-?\d+) last=(-?\d+)$", re.MULTILINE)
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
    if pinned is not None:
        if not pinned.exists():
            raise SystemExit(f"the pinned {name} is not installed at {pinned}")
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
        raise SystemExit(f"Verilator {PINNED_VERILATOR_VERSION} is required, found "
                         f"{tools['verilator']['version']!r}")
    match = IVERILOG_VERSION_RE.search(tools["iverilog"]["version"])
    if match is None or (int(match.group(1)), int(match.group(2))) < (11, 0):
        raise SystemExit(f"Icarus Verilog {PINNED_IVERILOG_VERSION} or newer is required, "
                         f"found {tools['iverilog']['version']!r}")


def git_state() -> dict[str, Any]:
    def run(*argv: str) -> str:
        return subprocess.run(["git", *argv], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=False).stdout.strip()
    status = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(status),
        "dirty_paths": sorted(line[3:] for line in status.splitlines()) if status else [],
    }


def run_stage(name: str, command: list[str], cwd: Path, timeout: int,
              env: dict[str, str] | None = None) -> dict[str, Any]:
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, timeout=timeout, env=env)
    return {
        "name": name,
        "command": canonical(shlex.join(command), cwd),
        "returncode": result.returncode,
        "log": canonical(result.stdout, cwd),
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
    keys = ("case", "outputs", "window", "first", "last")
    return [dict(zip(keys, (int(value) for value in match.groups())))
            for match in RATE_RE.finditer(log)]


def simulator_case(name: str, compile_command: list[str], run_command: list[str], cwd: Path,
                   marker_prefix: str) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, cwd, timeout=3600)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, cwd, timeout=3 * 3600)
    run_log = executed["log"] if executed else ""
    marker = parse_marker(run_log)
    marker_present = marker is not None and marker_prefix in run_log
    passed = (compiled["returncode"] == 0 and executed is not None
              and executed["returncode"] == 0 and marker_present)
    checks = CHECKS_RE.search(run_log)
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log_sha256": hashlib.sha256(compiled["log"].encode("utf-8")).hexdigest(),
        "compile_log_tail": "\n".join(compiled["log"].strip().splitlines()[-20:]),
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log_sha256": hashlib.sha256(run_log.encode("utf-8")).hexdigest(),
        "run_log_tail": "\n".join(run_log.strip().splitlines()[-20:]),
        "required_marker_prefix": marker_prefix,
        "marker_present": marker_present,
        "marker": marker,
        "checks": int(checks.group(1)) if checks else None,
        "rates": parse_rates(run_log),
        "first_failure": next((line.strip() for line in run_log.splitlines()
                               if line.strip().startswith(("FAIL:", "FAILURES:"))), None),
    }


def build_vectors(config: dict[str, Any], out_dir: Path, seed: int) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    stage = run_stage(
        f"vectors.{config['name']}",
        [sys.executable, str(ROOT / "tools/build_a3_v41_block_max_vectors.py"),
         "--out-dir", str(out_dir),
         "--block", str(config["block"]),
         "--exponent-bits", str(config["exponent_bits"]),
         "--mantissa-bits", str(config["mantissa_bits"]),
         "--max-blocks", str(config["max_blocks"]),
         "--cmp-stages", str(config["cmp_stages"]),
         "--rate-blocks", str(config["rate_blocks"]),
         "--seed", str(seed)],
        ROOT, timeout=3600, env=env)
    if stage["returncode"] != 0:
        raise SystemExit(f"vector build failed for {config['name']}:\n{stage['log'][-4000:]}")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    for name in IMAGE_FILES:
        text = (out_dir / name).read_text(encoding="ascii")
        actual = hashlib.sha256(text.encode("ascii")).hexdigest()
        if actual != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    return manifest


def image_words(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="ascii").splitlines() if line.strip())


def run_configuration(config: dict[str, Any], build: Path, executables: dict[str, Path],
                      seed: int) -> dict[str, Any]:
    work = build / config["name"]
    work.mkdir(parents=True, exist_ok=True)
    manifest = build_vectors(config, work, seed)
    geometry = manifest["geometry"]
    marker_prefix = manifest["required_marker_prefix"]
    rtl = [str(ROOT / path) for path in RTL_SOURCES]
    top = str(ROOT / "rtl/test/a3_route_block_max_top.sv")

    score_w = geometry["score_w"]
    parameters = {
        "BLOCK": geometry["block"],
        "SCORE_W": score_w,
        "EXP_W": geometry["exponent_bits"],
        "MANT_W": geometry["mantissa_bits"],
        "MAX_BLOCKS": geometry["max_blocks"],
        "CMP_STAGES": geometry["cmp_stages"],
    }
    icarus_dir = work / "icarus"
    verilator_dir = work / "verilator"
    for directory in (icarus_dir, verilator_dir):
        directory.mkdir(parents=True, exist_ok=True)
        for name in IMAGE_FILES:
            shutil.copy2(work / name, directory / name)

    iverilog_compile = [
        str(executables["iverilog"]), "-g2012", "-s", "tb_a3_route_block_max",
        *[f"-Ptb_a3_route_block_max.{key}={value}" for key, value in parameters.items()],
        f"-Ptb_a3_route_block_max.VEC_WORDS={image_words(work / 'bm_vec.hex')}",
        f"-Ptb_a3_route_block_max.CASE_WORDS={image_words(work / 'bm_case.hex')}",
        f"-Ptb_a3_route_block_max.EXP_WORDS={image_words(work / 'bm_expect.hex')}",
        "-o", "bm_sim.vvp", *rtl, top, str(ROOT / "rtl/test/tb_a3_route_block_max.sv"),
    ]
    verilator_compile = [
        str(executables["verilator"]), "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
        "-Wno-DECLFILENAME", "-Wno-MULTIDRIVEN", "-Wno-UNUSEDPARAM",
        "--top-module", "ot_a3_route_block_max_top",
        *[f"-G{key}={value}" for key, value in parameters.items()],
        "--Mdir", "obj_bm", *rtl, top,
        str(ROOT / "rtl/test/a3_route_block_max_harness.cpp"),
        "-CFLAGS", "-std=c++17 -O2", "-j", "4",
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(simulator_case, "iverilog", iverilog_compile,
                        [str(executables["vvp"]), "bm_sim.vvp"], icarus_dir, marker_prefix),
            pool.submit(simulator_case, "verilator", verilator_compile,
                        ["./obj_bm/Vot_a3_route_block_max_top", "+bmdir=."], verilator_dir,
                        marker_prefix),
        ]
        simulators = [future.result() for future in futures]

    agree = (
        all(simulator["status"] == "pass" for simulator in simulators)
        and len({json.dumps(simulator["marker"], sort_keys=True)
                 for simulator in simulators}) == 1
        and len({simulator["checks"] for simulator in simulators}) == 1
        and len({json.dumps(simulator["rates"], sort_keys=True)
                 for simulator in simulators}) == 1
    )
    marker = simulators[0]["marker"] or {}
    rates = simulators[0]["rates"]
    #: II = 1 means the retirement window of a back-to-back stream equals the
    #: number of blocks in it.
    initiation_interval = [
        {"case": rate["case"], "blocks": rate["outputs"], "window_cycles": rate["window"],
         "cycles_per_block": (rate["window"] / rate["outputs"]) if rate["outputs"] else None}
        for rate in rates
    ]
    return {
        "name": config["name"],
        "note": config["note"],
        "status": "pass" if agree else "fail",
        "simulators_agree": agree,
        "geometry": geometry,
        "elaboration_parameters": parameters,
        "checks_per_simulator": {simulator["name"]: simulator["checks"]
                                 for simulator in simulators},
        "marker": marker,
        "required_marker_prefix": marker_prefix,
        "initiation_interval": initiation_interval,
        "vectors": {
            "image_sha256": manifest["image_sha256"],
            "manifest_sha256": sha256_file(work / "manifest.json"),
            "counts": manifest["counts"],
            "totals": manifest["totals"],
            "seed": manifest["seed"],
            "reference": manifest["reference"],
            "numeric_contract": manifest["numeric_contract"],
            "cases": manifest["cases"],
        },
        "simulators": simulators,
    }


def lint_gate(build: Path, verilator: Path) -> dict[str, Any]:
    """A strict Verilator lint of the block and its verification top."""

    command = [
        str(verilator), "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-MULTIDRIVEN",
        "-Wno-UNUSEDPARAM", "--top-module", "ot_a3_route_block_max_top",
        *[str(ROOT / path) for path in RTL_SOURCES],
        str(ROOT / "rtl/test/a3_route_block_max_top.sv"),
    ]
    stage = run_stage("verilator.lint", command, build, timeout=600)
    warnings = [line for line in stage["log"].splitlines()
                if line.startswith(("%Warning", "%Error"))]
    return {
        "command": stage["command"],
        "returncode": stage["returncode"],
        "warnings": warnings,
        "clean": stage["returncode"] == 0 and not warnings,
        "suppressed": ["DECLFILENAME (the verification top is not its own file name)",
                       "MULTIDRIVEN (pipeline stages of one array are written by the "
                       "per-stage generate blocks, disjoint elements each)",
                       "UNUSEDPARAM (ot_a3_engine_pkg declares every engine's classes)"],
        "log_tail": "\n".join(stage["log"].strip().splitlines()[-20:]),
    }


def claim_boundary(configurations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "checks_block_max_against_an_independent_python_reference": True,
        "runs_both_icarus_and_the_pinned_verilator_over_the_same_vectors": True,
        "compares_every_output_word_score_block_id_row_last_and_tag": True,
        "measures_initiation_interval_and_per_output_latency": True,
        "establishes_the_numeric_contract_block_max_ordered_ieee_v1": True,
        "exercises_every_structural_refusal_of_the_block": True,
        "reference_derived_from_the_rtl": False,
        "executes_a_real_abi3_descriptor_or_engine_issue": False,
        "wired_into_ot_a3_engine_array_or_reachable_from_a_program": False,
        "integrates_the_shipped_deployment_sequencer": False,
        "establishes_operand_fetch_result_writeback_or_any_memory_port": False,
        "establishes_the_candidate_pool_end_to_end_with_candidate_mask_or_index_topk": False,
        "establishes_any_agreement_with_the_vendor_checkpoint_or_its_own_scores": False,
        "is_placed_or_routed": False,
        "establishes_a_frequency_a_period_or_any_physical_number": False,
        "establishes_an_area_or_a_power_number": False,
        "contains_or_models_a_rom_or_sram_macro": False,
        "establishes_the_functional_simulator_engine_for_route_block_max": False,
        "establishes_the_ir_lowering_or_the_admission_predicate_for_sub_opcode_0x08": False,
        "covers_nan_scores_on_a_real_lane_as_a_value": False,
        "covers_score_formats_other_than_the_seven_elaborated_shapes": False,
        "geometry_shapes_run": [configuration["name"] for configuration in configurations],
        "note": (
            "This run establishes that one parameterised RTL block computes the "
            "reference's blockwise maximum, bit for bit, on two simulators, at one block "
            "per cycle, for seven elaborated shapes, and that it fails closed on every "
            "refusal it defines.  It establishes nothing about the block inside the "
            "engine array, nothing about the rest of the candidate pool, and nothing "
            "physical: BLOCK_MAX is not reachable from a descriptor in this run, and the "
            "frequency claim in the module header is an intent about the pipeline "
            "structure, not a measurement -- WP-M's routed record is the measurement."
        ),
    }


def run(output: Path, build_root: Path | None, names: list[str] | None, seed: int) -> dict[str, Any]:
    executables = {
        "iverilog": resolve("iverilog", None),
        "vvp": resolve("vvp", None),
        "verilator": resolve("verilator",
                             TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"),
        "cxx": resolve("g++", None),
        "python": Path(sys.executable),
    }
    version_flags = {"iverilog": ["-V"], "vvp": ["-V"], "verilator": ["--version"],
                     "cxx": ["--version"], "python": ["--version"]}
    tools = {name: tool_record(path, version_flags[name]) for name, path in executables.items()}
    require_versions(tools)
    git = git_state()

    selected = [configuration for configuration in CONFIGURATIONS
                if names is None or configuration["name"] in names]
    if not selected:
        raise SystemExit("no configuration selected")

    with tempfile.TemporaryDirectory(prefix="opentallas-a3-block-max-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        lint = lint_gate(build, executables["verilator"])
        with ThreadPoolExecutor(max_workers=min(4, len(selected))) as pool:
            results = list(pool.map(
                lambda configuration: run_configuration(configuration, build, executables, seed),
                selected))

    sources = {path: sha256_file(ROOT / path) for path in sorted(
        RTL_SOURCES + TESTBENCH_SOURCES + REFERENCE_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES)}
    passing = all(result["status"] == "pass" for result in results) and lint["clean"]
    total_checks = sum(
        sum(value for value in result["checks_per_simulator"].values() if value)
        for result in results)
    return {
        "schema": "opentallas.rtl.a3_v41_block_max_campaign.v1",
        "campaign": "rtl_a3_v41_route_block_max",
        "engine": "ROUTE.BLOCK_MAX",
        "sub_opcode": "0x08 (ot_a3_pkg::A3_ROUTE_BLOCK_MAX, runtime.abi3.constants.Route.BLOCK_MAX)",
        "ir_kind": "BLOCK_MAX(scores, block) -> block_scores",
        "work_package": "WP-K, docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md section 13",
        "evidence_class": "public_open_tool_rtl_simulation",
        "status": "pass" if passing else "fail",
        "simulators_agree": all(result["simulators_agree"] for result in results),
        "reference": "runtime.reference.candidate_pool.block_max_rows",
        "numeric_contract": "block_max_ordered_ieee_v1",
        "reference_independence": (
            "the reference orders scores by their EXACT value, computed from the format's "
            "sign, exponent and mantissa fields with fractions.Fraction and no host "
            "floating point; the RTL realises the same order with a monotone bit map and a "
            "registered comparator tree.  Neither was derived from the other."
        ),
        "pipeline": {
            "stage_count_formula": "CMP_STAGES * ceil(log2(BLOCK)) + 2",
            "initiation_interval_blocks_per_cycle": 1,
            "output_latency_cycles_formula": "stage count - 1 (the accepting edge is the "
                                            "input stage's own edge)",
            "registered_boundary": "one comparator between registers at every tree level; "
                                   "no combinational path walks the block",
            "measured": [
                {"configuration": result["name"],
                 "stage_count": result["geometry"]["pipeline_depth"],
                 "output_latency_cycles": result["geometry"]["output_latency_cycles"],
                 "initiation_interval": result["initiation_interval"]}
                for result in results
            ],
        },
        "total_checks_across_simulators": total_checks,
        "configurations": results,
        "verilator_lint": lint,
        "claim_boundary": claim_boundary(results),
        "limitations": [
            "BLOCK_MAX is not instantiated in ot_a3_engine_array in this run: the block is "
            "driven by the two checkers, not by an ABI3 descriptor.",
            "No operand fetch or result writeback exists: scores arrive on a port and "
            "block scores leave on a port.",
            "The frequency style claim (the mac-lane and tree-endpoint pipelining style "
            "that closes above 500 MHz on ASAP7) is structural, not measured here.",
            "The candidate pool is not exercised end to end: CANDIDATE_MASK and the "
            "INDEX_TOPK mask slot are other units' work.",
            "A NaN score is refused rather than ordered, so no NaN semantics is qualified.",
        ],
        "tools": tools,
        "git": git,
        "source_sha256": sources,
        "output": canonical(str(output), ROOT),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-root", type=Path, default=None,
                        help="keep the build tree here instead of a temporary directory")
    parser.add_argument("--configuration", action="append", default=None,
                        help="run only this configuration; repeatable")
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args(argv)

    record = run(args.output, args.build_root, args.configuration, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "status": record["status"],
        "simulators_agree": record["simulators_agree"],
        "configurations": [
            {"name": result["name"], "status": result["status"],
             "checks": result["checks_per_simulator"]} for result in record["configurations"]],
        "total_checks_across_simulators": record["total_checks_across_simulators"],
        "output": str(args.output),
    }, indent=2))
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
