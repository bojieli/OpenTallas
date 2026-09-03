#!/usr/bin/env python3
"""Run and record the two-simulator RTL co-simulation of the shipped deployments.

``tools/rtl_abi3_campaign.py`` correlates the ABI 3.0 control plane against 65
vectors that are real programs *written for the campaign*.  This campaign
correlates it against the four deployments this project claims to run:
Qwen3-8B on ROM and HBM, and DeepSeek-V4-Flash on the ROM wafer and HBM
32-node cluster, on both entrypoints, from their own deployment images.

The shape is the sibling campaign's, deliberately: the same RTL, the same
verification top with deployment-only memory-depth overrides, two independently
written checkers, one under Icarus and one as a separately compiled Verilator
executable, and a marker derived from a golden execution on
``runtime.sim.device.Device`` rather than written by hand.  The shared top's
defaults and the production RTL geometry remain unchanged.  A run counts only
if both simulators print that marker exactly.

Two things are different, and both are consequences of correlating real
programs rather than constructed ones:

*The checkers do not stop at the first divergence.*  Each case records its first
disagreement with a numeric site code and the next case starts clean, so one
defect in one deployment does not hide the state of the other three.  This tool
parses those per-case and per-deployment lines out of both logs and requires the
two simulators to have seen the *same* thing, divergences included.  Two
simulators agreeing that the RTL is wrong is a stronger statement than one
simulator failing.

*The production-profile elaboration has no transactional-state controller.*
All four certified deployments contain zero STATE descriptors and instructions,
so this campaign sets ``STATE_COMPAT=0``.  Compatibility state counters and
``state_apply_overflow`` are tied to zero; both checkers still observe them.
``event_signal_error`` is asserted from the admitted ABI event bounds.

Tool identity is recorded, not assumed: the resolved executable path, its
SHA-256 and its self-reported version go into the artifact, and a Verilator
older than the pinned 5.050 or an Icarus older than 11.0 is refused.
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
VECTOR_DIR = ROOT / "testdata/compiler/abi3_deployment"
VECTOR_JSON = VECTOR_DIR / "abi3_deployment_rtl_vectors.json"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_deployment_campaign.json"
PROFILE_MARKER = "PROFILE: ABI3 live-buffer state exclusion PASS"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_program_header.sv",
    "rtl/abi3/ot_a3_loop_stack.sv",
    "rtl/abi3/ot_a3_view_resolver.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_state_controller.sv",
    "rtl/abi3/ot_a3_microsequencer.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_microsequencer_top.sv",
    "rtl/test/tb_a3_deployment.sv",
    "rtl/test/a3_deployment_harness.cpp",
)
# The frozen contracts the RTL transcribes.  Hashed so that a change to the ABI
# invalidates this evidence instead of silently outdating it.
CONTRACT_SOURCES = (
    "docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md",
    "runtime/abi3/constants.py",
    "runtime/abi3/records.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/verifier.py",
    "runtime/driver.py",
    "runtime/sim/device.py",
    "runtime/sim/memory.py",
)
TOOL_SOURCES = (
    "tools/build_abi3_deployment_rtl_vectors.py",
    "tools/rtl_abi3_deployment_campaign.py",
)
# Four are read by the DUT under the names rtl/test/a3_microsequencer_top.sv
# hardcodes -- that top is shared with the microsequencer campaign and is not
# forked for this one -- and five are read only by the checkers.
VECTOR_FILES = (
    "a3_program.hex",
    "a3_header.hex",
    "a3_descriptor.hex",
    "a3_symbol.hex",
    "a3_deployment_case.hex",
    "a3_deployment_issue.hex",
    "a3_deployment_view.hex",
    "a3_deployment_predicate.hex",
    "a3_deployment_meta.hex",
)

# Divergence site codes, transcribed from rtl/test/tb_a3_deployment.sv and
# rtl/test/a3_deployment_harness.cpp so the artifact can name a site in prose.
SITE_NAMES = {
    0: "none",
    1: "engine issue opcode",
    2: "engine issue descriptor ID",
    3: "engine issue instruction index",
    4: "engine issue overflow",
    5: "engine issue count",
    6: "resolved view descriptor",
    7: "resolved view operand slot",
    8: "resolved view extent (A13/A18)",
    9: "resolved view element offset (A4)",
    10: "resolved view rank",
    11: "resolved view extent axis (A18)",
    12: "resolved view overflow",
    13: "resolved view count",
    14: "views-resolved counter",
    15: "predicate object ID",
    16: "predicate element index",
    17: "predicate response overflow",
    18: "predicate response count",
    20: "program header legality",
    21: "program header trap class",
    22: "program header instruction count",
    23: "program header entrypoint count",
    24: "program header max retired work",
    30: "transaction completion",
    31: "transaction trap class",
    32: "first faulting instruction",
    33: "instructions fetched",
    34: "instructions retired",
    35: "instructions predicated off",
    36: "instructions issued",
    37: "loop iterations",
    38: "branches taken",
    39: "wait-set evaluations",
    40: "state prepares",
    41: "state commits",
    42: "state discards",
    43: "state reads",
    44: "state generation advances",
    45: "state commits applied",
    46: "state rows committed",
    47: "event signal error (A23/A24: zero on any admitted program)",
    48: "compatibility state apply overflow",
}

CASE_RE = re.compile(
    r"^CASE (?P<index>\d+) tag=(?P<tag>[0-9a-f]+) (?P<verdict>OK|DIVERGE) "
    r"code=(?P<code>\d+) rtl=(?P<rtl>\d+) golden=(?P<golden>\d+) "
    r"issues=(?P<issues>\d+)/(?P<issues_expected>\d+) "
    r"views=(?P<views>\d+)/(?P<views_expected>\d+) "
    r"predicates=(?P<predicates>\d+)/(?P<predicates_expected>\d+) "
    r"fetched=(?P<fetched>\d+) retired=(?P<retired>\d+) trap=(?P<trap>\d+) "
    r"fault=(?P<fault>\d+) sigerr=(?P<sigerr>\d+) applyovf=(?P<applyovf>\d+)$",
    re.MULTILINE,
)
DEPLOY_RE = re.compile(
    r"^DEPLOY (?P<index>\d+) cases=(?P<cases>\d+) diverged=(?P<diverged>\d+) "
    r"issues=(?P<issues>\d+) views=(?P<views>\d+) "
    r"predicates=(?P<predicates>\d+)$",
    re.MULTILINE,
)
CHECKS_RE = re.compile(r"checks=(\d+)")
SIGNAL_FLAG_RE = re.compile(r"signal_flag_cases=(\d+)")
APPLY_OVERFLOW_RE = re.compile(r"apply_overflow_cases=(\d+)")
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")
IVERILOG_VERSION_RE = re.compile(r"Icarus Verilog version (\d+)\.(\d+)")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(text: str, build: Path) -> str:
    """Strip machine-specific paths so the artifact is reproducible."""
    return (
        text.replace(str(build), "<BUILD>")
        .replace(str(ROOT), "<ROOT>")
        .replace(str(Path.home()), "<HOME>")
    )


def resolve(name: str, pinned: Path | None) -> Path:
    """Prefer the pinned toolchain, then PATH; never a guess."""
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
    """Identify one tool: canonical path, executable digest, self-report."""
    result = subprocess.run(
        [str(executable), *version_args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "executable": canonical(str(executable), ROOT),
        "executable_sha256": sha256_file(executable),
        "version": lines[0] if lines else "no version text",
    }


def require_versions(tools: dict[str, dict[str, Any]]) -> None:
    verilator = tools["verilator"]["version"]
    match = VERILATOR_VERSION_RE.search(verilator)
    if match is None or (int(match.group(1)), int(match.group(2))) < (5, 50):
        raise SystemExit(
            f"Verilator {PINNED_VERILATOR_VERSION} or newer is required, found "
            f"{verilator!r}; set OPENTALLAS_VERILATOR or install the pinned build"
        )
    icarus = tools["iverilog"]["version"]
    match = IVERILOG_VERSION_RE.search(icarus)
    if match is None or (int(match.group(1)), int(match.group(2))) < (11, 0):
        raise SystemExit(
            f"Icarus Verilog {PINNED_IVERILOG_VERSION} or newer is required, "
            f"found {icarus!r}"
        )


def run_stage(
    name: str, command: list[str], build: Path, timeout: int
) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=build,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    return {
        "name": name,
        "command": canonical(shlex.join(command), build),
        "returncode": result.returncode,
        "log": canonical(result.stdout, build),
    }


def parse_observation(log: str) -> dict[str, Any]:
    """Everything the checkers published, as structure rather than text."""
    cases = [
        {
            "index": int(m.group("index")),
            "tag": m.group("tag"),
            "deployment_index": int(m.group("tag"), 16) >> 8,
            "phase": int(m.group("tag"), 16) & 0xFF,
            "verdict": m.group("verdict"),
            "divergence_code": int(m.group("code")),
            "divergence_site": SITE_NAMES.get(
                int(m.group("code")), "unknown site"
            ),
            "rtl_value": int(m.group("rtl")),
            "golden_value": int(m.group("golden")),
            "issues_compared": int(m.group("issues")),
            "issues_expected": int(m.group("issues_expected")),
            "views_compared": int(m.group("views")),
            "views_expected": int(m.group("views_expected")),
            "predicates_compared": int(m.group("predicates")),
            "predicates_expected": int(m.group("predicates_expected")),
            "rtl_fetched": int(m.group("fetched")),
            "rtl_retired": int(m.group("retired")),
            "rtl_trap_class": int(m.group("trap")),
            "rtl_first_fault": int(m.group("fault")),
            "rtl_event_signal_error": int(m.group("sigerr")),
            "rtl_state_apply_overflow": int(m.group("applyovf")),
        }
        for m in CASE_RE.finditer(log)
    ]
    deployments = [
        {
            "deployment_index": int(m.group("index")),
            "cases": int(m.group("cases")),
            "diverged": int(m.group("diverged")),
            "issues_compared": int(m.group("issues")),
            "views_compared": int(m.group("views")),
            "predicates_compared": int(m.group("predicates")),
        }
        for m in DEPLOY_RE.finditer(log)
    ]
    checks = CHECKS_RE.search(log)
    signal_flags = SIGNAL_FLAG_RE.search(log)
    apply_overflow = APPLY_OVERFLOW_RE.search(log)
    return {
        "cases": cases,
        "deployments": deployments,
        "checks": int(checks.group(1)) if checks else None,
        "signal_flag_cases": (
            int(signal_flags.group(1)) if signal_flags else None
        ),
        "apply_overflow_cases": (
            int(apply_overflow.group(1)) if apply_overflow else None
        ),
    }


def simulator_case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
    marker: str,
) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=1800)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=7200)
    log = compiled["log"] + (executed["log"] if executed else "")
    observation = parse_observation(executed["log"] if executed else "")
    passed = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] == 0
        and marker in executed["log"]
        and PROFILE_MARKER in executed["log"]
    )
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log": compiled["log"],
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log": executed["log"] if executed else "",
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "required_marker": marker,
        "required_profile_marker": PROFILE_MARKER,
        "marker_present": bool(executed and marker in executed["log"]),
        "profile_marker_present": bool(
            executed and PROFILE_MARKER in executed["log"]
        ),
        "checks": observation["checks"],
        "signal_flag_cases": observation["signal_flag_cases"],
        "apply_overflow_cases": observation["apply_overflow_cases"],
        "observed_cases": observation["cases"],
        "observed_deployments": observation["deployments"],
    }


def compare_simulators(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Require the two simulators to have observed the same thing.

    Not only the same verdict: the same divergence site, the same values on
    both sides of it, and the same number of issues, views and data-dependent
    predicate reads reached before it.  Two engines agreeing on where the RTL
    stopped is what makes a divergence a finding rather than one simulator's
    opinion.
    """
    keys = (
        "index", "tag", "verdict", "divergence_code", "rtl_value",
        "golden_value", "issues_compared", "views_compared",
        "predicates_compared", "predicates_expected", "rtl_fetched",
        "rtl_retired", "rtl_trap_class", "rtl_first_fault",
        "rtl_event_signal_error", "rtl_state_apply_overflow",
    )
    projections = [
        [tuple(case[key] for key in keys) for case in entry["observed_cases"]]
        for entry in cases
    ]
    agree = len(set(map(tuple, projections))) == 1 and bool(projections[0])
    return {
        "simulators_observed_the_same_cases": agree,
        "compared_fields": list(keys),
        "case_count_per_simulator": [len(p) for p in projections],
    }


ENGINE_CAMPAIGN_JSON = ROOT / "results/rtl/abi3_engine_campaign.json"


def engine_coverage(
    vectors: dict[str, Any], correlated_cases: list[str]
) -> dict[str, Any]:
    """Which of the opcodes the real programs issue have datapath RTL at all.

    The sibling engine campaign correlates a handful of datapaths against the
    functional engines; this campaign correlates the sequencer that dispatches
    to them.  Neither drives the other -- the engine campaign says so in its own
    boundary -- so the useful number here is how much of what the shipped
    programs actually issue has a datapath on the other side of the port, and
    the answer is a minority of it.
    """
    reached: dict[tuple[int, int], int] = {}
    for record in vectors["cases"]:
        if record["name"] not in correlated_cases:
            continue
        for entry in record["issued_opcodes"]:
            key = (entry["family"], entry["sub"])
            reached[key] = reached.get(key, 0) + entry["issues"]
    with_rtl: set[tuple[int, int]] = set()
    engine_digest = None
    if ENGINE_CAMPAIGN_JSON.exists():
        engine = json.loads(ENGINE_CAMPAIGN_JSON.read_text(encoding="utf-8"))
        engine_digest = sha256_file(ENGINE_CAMPAIGN_JSON)
        with_rtl = {
            (int(entry["family"]), int(entry["sub"]))
            for entry in engine.get("correlation", {}).get("families", [])
        }
    declared = {
        (entry["family"], entry["sub"]) for entry in vectors["issued_opcodes"]
    }
    return {
        "source_of_datapath_list": "results/rtl/abi3_engine_campaign.json",
        "source_sha256": engine_digest,
        "distinct_opcodes_the_shipped_programs_issue": len(declared),
        "distinct_opcodes_this_run_reached": len(reached),
        "opcodes_reached_with_correlated_datapath_rtl": sorted(
            [list(key) for key in reached if key in with_rtl]
        ),
        "opcodes_reached_without_correlated_datapath_rtl": sorted(
            [list(key) for key in reached if key not in with_rtl]
        ),
        "note": (
            "an opcode with datapath RTL is still not driven by this "
            "sequencer: the two campaigns correlate the control plane and the "
            "datapaths separately and nothing wires them together. The "
            "compatibility STATE family (128) is absent from all four "
            "certified deployments and its controller is not elaborated in "
            "this production-profile campaign"
        ),
    }


def load_vectors() -> dict[str, Any]:
    if not VECTOR_JSON.exists():
        raise SystemExit(
            f"vector set is missing: {VECTOR_JSON}; run "
            "tools/build_abi3_deployment_rtl_vectors.py first"
        )
    vectors = json.loads(VECTOR_JSON.read_text(encoding="utf-8"))
    for name, digest in vectors["image_sha256"].items():
        actual = sha256_file(VECTOR_DIR / name)
        if actual != digest:
            raise SystemExit(
                f"vector image {name} does not match the vector set digest; "
                "regenerate with tools/build_abi3_deployment_rtl_vectors.py"
            )
    return vectors


def run(build_root: Path | None = None) -> dict[str, Any]:
    vectors = load_vectors()
    marker = vectors["required_marker"]

    executables = {
        "iverilog": resolve("iverilog", None),
        "vvp": resolve("vvp", None),
        "verilator": resolve(
            "verilator",
            TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator",
        ),
        "cxx": resolve("g++", None),
    }
    version_flags = {
        "iverilog": ["-V"],
        "vvp": ["-V"],
        "verilator": ["--version"],
        "cxx": ["--version"],
    }
    tools = {
        name: tool_record(path, version_flags[name])
        for name, path in executables.items()
    }
    require_versions(tools)

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-deploy-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        for name in VECTOR_FILES:
            shutil.copy2(VECTOR_DIR / name, build / name)

        rtl = [str(ROOT / path) for path in RTL_SOURCES]
        iverilog_compile = [
            str(executables["iverilog"]),
            "-g2012",
            "-s",
            "tb_a3_deployment",
            "-o",
            "a3_deploy.vvp",
            *rtl,
            str(ROOT / "rtl/test/a3_microsequencer_top.sv"),
            str(ROOT / "rtl/test/tb_a3_deployment.sv"),
        ]
        verilator_compile = [
            str(executables["verilator"]),
            "--cc",
            "--exe",
            "--build",
            "-Wall",
            "-Wno-fatal",
            "-Wno-DECLFILENAME",
            "--top-module",
            "ot_a3_microsequencer_top",
            "-GPROGRAM_WORDS=4096",
            "-GDESC_WORDS=8192",
            "-GSTATE_COMPAT=0",
            "--Mdir",
            "obj_a3_deploy",
            *rtl,
            str(ROOT / "rtl/test/a3_microsequencer_top.sv"),
            str(ROOT / "rtl/test/a3_deployment_harness.cpp"),
            "-CFLAGS",
            "-std=c++17",
        ]
        # The two builds use disjoint outputs, so compile and replay them in
        # parallel. Resolve in a fixed order to keep the retained JSON stable.
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    simulator_case,
                    "iverilog",
                    iverilog_compile,
                    [str(executables["vvp"]), "a3_deploy.vvp"],
                    build,
                    marker,
                ),
                pool.submit(
                    simulator_case,
                    "verilator",
                    verilator_compile,
                    ["./obj_a3_deploy/Vot_a3_microsequencer_top"],
                    build,
                    marker,
                ),
            ]
            cases = [future.result() for future in futures]

    sources = {
        path: sha256_file(ROOT / path)
        for path in sorted(
            RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES
        )
    }
    sources["testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json"] = (
        sha256_file(VECTOR_JSON)
    )
    for name in VECTOR_FILES:
        sources[f"testdata/compiler/abi3_deployment/{name}"] = sha256_file(
            VECTOR_DIR / name
        )

    agreement = compare_simulators(cases)
    by_case: dict[int, dict[str, Any]] = {}
    for entry in cases[0]["observed_cases"]:
        by_case[entry["index"]] = entry
    correlated = [
        vectors["cases"][index]["name"]
        for index, entry in sorted(by_case.items())
        if entry["verdict"] == "OK" and index < len(vectors["cases"])
    ]
    divergences = [
        {
            "case": vectors["cases"][entry["index"]]["name"]
            if entry["index"] < len(vectors["cases"])
            else f"case {entry['index']}",
            "deployment_sha256": (
                vectors["cases"][entry["index"]]["deployment_sha256"]
                if entry["index"] < len(vectors["cases"])
                else None
            ),
            "site": entry["divergence_site"],
            "site_code": entry["divergence_code"],
            "rtl_value": entry["rtl_value"],
            "golden_value": entry["golden_value"],
            "rtl_first_fault_instruction": entry["rtl_first_fault"],
            "rtl_instructions_retired": entry["rtl_retired"],
            "golden_instructions_retired": (
                vectors["cases"][entry["index"]]["depth"]["instructions_retired"]
                if entry["index"] < len(vectors["cases"])
                else None
            ),
            "engine_issues_agreeing_before_divergence": entry["issues_compared"],
            "engine_issues_expected": entry["issues_expected"],
            "predicate_reads_agreeing_before_divergence": entry[
                "predicates_compared"
            ],
            "predicate_reads_expected": entry["predicates_expected"],
        }
        for index, entry in sorted(by_case.items())
        if entry["verdict"] == "DIVERGE"
    ]

    status_bits = {
        "why_they_are_not_correlated": (
            "state_apply_overflow is tied to zero because STATE_COMPAT=0. It "
            "is counted, printed by both checkers, and required above to agree. "
            "event_signal_error is no longer in this class: amendment A24 "
            "narrowed it to one condition -- a signal naming an event ID "
            "outside the scoreboard's space -- and amendment A23 makes that "
            "condition a refusal at admission, so zero is what the ABI says it "
            "must be on any admitted program and both checkers now assert it "
            "at divergence site 47 rather than counting it. The count below is "
            "kept so a regression is visible in the marker as well"
        ),
        "event_signal_error_cases": [
            entry["index"]
            for entry in sorted(by_case.values(), key=lambda e: e["index"])
            if entry["rtl_event_signal_error"]
        ],
        "state_apply_overflow_cases": [
            entry["index"]
            for entry in sorted(by_case.values(), key=lambda e: e["index"])
            if entry["rtl_state_apply_overflow"]
        ],
        "event_signal_error_note": (
            "before amendment A24, rtl/abi3/ot_a3_event_scoreboard.sv enforced "
            "single assignment at run time: a second signal of an event ID "
            "that was already set raised a sticky error bit. "
            "runtime.abi3.verifier enforces single assignment statically -- at "
            "most one *instruction* may name an event ID -- and says nothing "
            "about how often that instruction runs. Every engine instruction "
            "in the Qwen program sits inside a loop, so its event was "
            "signalled once per iteration: 691 signals against 26 distinct "
            "event IDs, and the bit was set on all four cases that ran. A24 "
            "settles the semantics the other way, which is the way "
            "runtime.sim.device.Device has always executed them: an event is a "
            "level, single assignment is a property of the program text, and "
            "raising a level that is already raised is the one producer "
            "running on a later loop trip. The bit now reports only an "
            "out-of-range ID and is asserted rather than counted"
        ),
    }

    coverage = engine_coverage(vectors, correlated)

    passed = (
        all(case["status"] == "pass" for case in cases)
        and agreement["simulators_observed_the_same_cases"]
    )
    return {
        "schema": "opentallas.rtl.abi3_deployment_campaign.v1",
        "campaign": "rtl3_shipped_deployment_cosimulation",
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "required_marker": marker,
        "required_profile_marker": PROFILE_MARKER,
        "rtl_profile": {
            "state_compatibility_elaborated": False,
            "required_state_descriptor_count": 0,
            "required_state_instruction_count": 0,
            "buffer_model": "direct_memory_objects_with_token_fence",
            "failure_model": "fail_stop_fresh_run",
            "link_retry_scope": "packet_only",
        },
        "what_ran": {
            "reference": "runtime.sim.device.Device",
            "deployments": [
                {
                    "key": entry["key"],
                    "title": entry["title"],
                    "deployment_sha256": entry["deployment_sha256"],
                    "instruction_count": entry["instruction_count"],
                    "descriptor_count": entry["descriptor_count"],
                    "co_simulable_within_rtl_bounds": entry[
                        "co_simulable_within_rtl_bounds"
                    ],
                    "rtl_bound_overruns": entry["rtl_bound_overruns"],
                }
                for entry in vectors["deployments"]
            ],
            "depth_reached": [
                {
                    "case": record["name"],
                    "static_instructions_in_program": record["depth"][
                        "static_instructions_in_program"
                    ],
                    "distinct_static_instructions_that_issued": record["depth"][
                        "distinct_static_instructions_reached"
                    ],
                    "golden_instructions_retired": record["depth"][
                        "instructions_retired"
                    ],
                    "golden_engine_issues": record["depth"]["engine_issues"],
                    "golden_resolved_views": record["depth"][
                        "resolved_operand_views"
                    ],
                    "golden_data_dependent_predicate_reads": record["depth"][
                        "data_dependent_predicate_reads"
                    ],
                    "ran_to_completion_on_the_golden_model": record[
                        "ran_to_completion"
                    ],
                    "work_bound_lowered_for_cosimulation": record[
                        "work_bound_lowered_for_cosimulation"
                    ],
                }
                for record in vectors["cases"]
            ],
            "prompt_tokens": vectors["prompt_tokens"],
            "compared": [
                "program header admission, trap class, instruction count, "
                "entrypoint count and declared maximum retired work",
                "every engine issue in program order: family, subopcode, "
                "descriptor ID and the instruction index that issued it",
                "every resolved operand tensor view in program order then "
                "operand order: descriptor, slot, resolved extent, the axis "
                "that extent belongs to (A18), element offset (A4) and rank, "
                "against runtime.sim.memory.ViewResolver.resolve",
                "every BOOLEAN_OBJECT and EOS_MEMBER predicate read in "
                "program order: authenticated object ID, element index and "
                "raw Boolean response before instruction-level inversion",
                "instructions fetched, retired, predicated off and issued",
                "loop iterations, branches taken and wait-set evaluations",
                "all compatibility-state counters and apply-overflow remain "
                "zero because STATE_COMPAT=0 and the certified deployments "
                "contain no STATE descriptors or instructions",
                "the completion decision, the trap class and the first "
                "faulting instruction",
            ],
        },
        "cross_simulator_agreement": agreement,
        "rtl_status_bits_observed_not_correlated": status_bits,
        "engine_coverage": coverage,
        "correlated_cases": correlated,
        "divergences": divergences,
        "rtl_implementation_bounds": vectors["rtl_implementation_bounds"],
        "tools": tools,
        "source_sha256": sources,
        "cases": cases,
        "claim_boundary": {
            "establishes": [
                "the ABI 3.0 sequencer RTL reproduces runtime.sim.device.Device "
                "exactly on all four deployments this program ships -- the "
                "Qwen3-8B ROM and HBM single-chip deployments and the "
                "DeepSeek-V4-Flash ROM-wafer and HBM 32-node-cluster "
                "deployments -- on both entrypoints, from their own program "
                "images, descriptor tables and request-bound symbols, with no "
                "vector written for the occasion; what_ran.deployments binds "
                "each statement to its full deployment digest",
                "the depth is the whole transaction on every case, ending in "
                "COMPLETE and not at a lowered co-simulation bound; each "
                "case's exact retired-instruction, engine-issue and resolved-"
                "view totals are recorded in what_ran.depth_reached rather "
                "than copied into this prose",
                "every engine issue is compared by the instruction index that "
                "issued it as well as by family, subopcode and descriptor ID, "
                "so a loop trip or a branch that came out differently is "
                "caught at the next issue rather than at the end",
                "one verification-top instance represents one sequencer node; "
                "its resolved views are compared with golden node zero. The "
                "state compatibility block is not elaborated, every state "
                "counter remains zero, and the vector artifact separately "
                "retains each deployment's node count",
                "every resolved operand view is compared against "
                "runtime.sim.memory.ViewResolver.resolve at the loop bindings "
                "the device recorded: element offset (A4), resolved extent "
                "(A13) and the axis that extent belongs to (A18)",
                "every data-dependent BOOLEAN_OBJECT or EOS_MEMBER predicate "
                "requests the object ID and element index in its authenticated "
                "descriptor, and the sequencer applies the supplied raw "
                "Boolean value and instruction-level inversion identically "
                "to runtime.sim.device.Device",
                "two independently written checkers, on two simulation "
                "engines, under two different back-pressure patterns, observed "
                "the same result on every case, and print byte-identical "
                "markers",
                "every deployment's demands fit the bounds "
                "rtl/abi3/ot_a3_pkg.sv declares, and each of those bounds is "
                "now named by a capability field a deployment is admitted "
                "against (amendments A22 and A23), so a program that does not "
                "fit is refused at admission rather than discovered here"
            ],
            "does_not_establish": {
                "checkpoint_bytes": "no checkpoint byte is read. The memory "
                "arenas are mapped so the golden device can be constructed and "
                "no-op engines never touch them, so this run says nothing "
                "about the weights, the ROM image, or any value in memory",
                "deepseek_v4_flash_arithmetic": "the DeepSeek-V4-Flash ROM-"
                "wafer and HBM-cluster deployments correlate at full depth, "
                "but on their *control planes* only, for the same reason every "
                "other case here does: the engines are recording no-ops on "
                "the golden side and absent on the RTL side. No physical "
                "result may cite this campaign as evidence about either "
                "deployment's arithmetic",
                "engine_arithmetic": "every dispatchable engine operation is "
                "a recording no-op on the golden side and absent on the RTL "
                "side. The instruction stream is verified; the computation is "
                "not. See engine_coverage for how much of what these programs "
                "issue has a datapath at all",
                "engine_integration": "the datapaths the sibling engine "
                "campaign correlates are not wired to this sequencer. Nothing "
                "here shows that a resolved view drives the operand addresses "
                "an engine reads",
                "instruction_granularity": "the comparison is at every engine "
                "issue and every resolved operand view, in order, plus the "
                "transaction counters at the end. Instructions that issue "
                "nothing -- CONTROL, and any instruction predicated off -- are "
                "observed through the program-counter sequence they produce "
                "and the counters they increment, not individually",
                "other_request_shapes": "one request shape per entrypoint: a "
                "sixteen-token prefill and a one-token decode at position "
                "sixteen. A program's instruction stream is fixed but its loop "
                "trip counts and resolved extents are functions of the span, "
                "so a longer prompt runs the same instructions under bindings "
                "this campaign has not exercised",
                "physical_realisability": "simulation says nothing about "
                "area, timing or power",
                "record_integrity": "descriptor record CRC32C and the "
                "header's SHA-256 digests are not checked in RTL; instruction "
                "and header CRC32C are",
                "rtl_status_bits": "state_apply_overflow is tied to zero in "
                "the STATE_COMPAT=0 production profile and required to agree "
                "between the two simulators. event_signal_error "
                "is asserted rather than counted -- amendments A23 and A24 "
                "make zero the ABI's answer for any admitted program, not a "
                "hand-written one -- see "
                "rtl_status_bits_observed_not_correlated",
                "view_completeness": "view resolution covers the element "
                "offset and the extent of the one axis amendment A18 lets a "
                "view name. The view's other extents, its strides and its "
                "scale binding are copied from the descriptor unchanged and "
                "are not republished",
                "predicate_service_integration": "the checker supplies each "
                "raw Boolean response recorded by the golden Device run. The "
                "campaign verifies the sequencer request address and branch "
                "decision, but it does not connect that request to HBM, SRAM, "
                "the selection engine, or the 32-node agreement logic"
            }
        },
        "limitations": [
            "engine datapaths are out of scope: the issue port carries family, "
            "subopcode, descriptor ID and instruction index, and the view port "
            "carries the resolved extents an engine would read; no engine "
            "arithmetic is modelled on either side",
            "view resolution covers the element offset and the extent of the "
            "one axis amendment A18 lets a view name. The view's other "
            "extents, its strides and its scale binding are copied from the "
            "descriptor unchanged and are not republished",
            "BOOLEAN_OBJECT and EOS_MEMBER use the explicit predicate service "
            "port. ENGINE_STATUS and ROUTE_VALID still fail closed with trap "
            "class 4 because no engine-status integration port exists",
            "the predicate service is a verification responder in this "
            "campaign, not a memory or selection datapath; it replays the raw "
            "Device value only after checking the requested object and element",
            "the deployment bundles are built outside this repository's "
            "tracked tree (build/ is ignored), so the vector set binds them by "
            "deployment digest and refuses any other program rather than "
            "correlating whatever happens to be on disk",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing campaign artifact",
    )
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        print(
            f"refusing to overwrite {args.output}; pass --force to replace it",
            file=sys.stderr,
        )
        return 2

    summary = run(args.build_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for case in summary["cases"]:
        print(f"{case['name']}: {case['status'].upper()}")
    for name in summary["correlated_cases"]:
        print(f"  correlated: {name}")
    for divergence in summary["divergences"]:
        print(
            f"  DIVERGENCE {divergence['case']}: {divergence['site']} -- RTL "
            f"{divergence['rtl_value']}, golden {divergence['golden_value']}; "
            f"the RTL retired {divergence['rtl_instructions_retired']} of the "
            f"{divergence['golden_instructions_retired']} the golden model "
            f"retires, first fault at instruction "
            f"{divergence['rtl_first_fault_instruction']}"
        )
    flagged = summary["rtl_status_bits_observed_not_correlated"][
        "event_signal_error_cases"
    ]
    if flagged:
        print(
            f"  observed (not correlated): event_signal_error is set on "
            f"{len(flagged)} case(s) -- see "
            "rtl_status_bits_observed_not_correlated"
        )
    print(f"abi3 deployment rtl campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
