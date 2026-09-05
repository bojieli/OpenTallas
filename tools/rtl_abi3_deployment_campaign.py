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

*The front end is asynchronous and the checkers are the engines.*  Every
accepted issue is completed by the checker after a seeded pseudo-random
delay, in a seeded pseudo-random order (docs/CHIP_ARCHITECTURE_DESIGN.md
section 11.5, L1-CP: "engines active and randomised run-ahead").  The
baseline pair runs at zero run-ahead -- every operation completes in the
cycle after its acceptance -- and is the regression: its marker and every
per-case observation must be exactly the retained ones.  ``--run-ahead-seeds``
adds one Icarus + Verilator pair per seed at ``--run-ahead-max-delay`` cycles
of completion delay (``--run-ahead-reorder`` draws the completion order too),
and ``--deep-seed`` / ``--deep-max-delay`` one more pair with delays long
enough to fill the issue record store.  Every pair must print the same marker
and the same per-case projection as the baseline; the run-ahead depth reached
(the issue record store's high-water mark) is recorded per case and per
simulator and is the one field that is *not* required to agree, because the
two checkers apply different acceptance patterns by design.

*The checkers are the management processor.*  The wrapper holds no image and
runs no $readmemh (section 13 item 12): each checker writes the program and
descriptor stores through the design's host load path once, binds the
sixteen request symbols per case through it, and streams the program header
through the admission beat port.

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
    "rtl/abi3/ot_a3_shared_divider.sv",
    "rtl/abi3/ot_a3_symbol_file.sv",
    "rtl/abi3/ot_a3_loop_stack.sv",
    "rtl/abi3/ot_a3_view_resolver.sv",
    "rtl/abi3/ot_a3_resolver_bank.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_issue_record_store.sv",
    "rtl/abi3/ot_a3_dependence_table.sv",
    "rtl/abi3/ot_a3_state_controller.sv",
    "rtl/abi3/ot_a3_microsequencer.sv",
    "rtl/abi3/ot_a3_device_top.sv",
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
    "runtime/sim/run_ahead.py",
    "runtime/sim/memory.py",
)
TOOL_SOURCES = (
    "tools/build_abi3_deployment_rtl_vectors.py",
    "tools/rtl_abi3_deployment_campaign.py",
)
# All nine are read by the checkers: the first four are the device images the
# checkers load into the design through its host path (the wrapper holds no
# image), the other five the golden observation they compare against.
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
    49: "issue record store protocol error (a completion of an empty slot)",
    50: "operations outstanding at done",
}

CASE_RE = re.compile(
    r"^CASE (?P<index>\d+) tag=(?P<tag>[0-9a-f]+) (?P<verdict>OK|DIVERGE) "
    r"code=(?P<code>\d+) rtl=(?P<rtl>\d+) golden=(?P<golden>\d+) "
    r"issues=(?P<issues>\d+)/(?P<issues_expected>\d+) "
    r"views=(?P<views>\d+)/(?P<views_expected>\d+) "
    r"predicates=(?P<predicates>\d+)/(?P<predicates_expected>\d+) "
    r"fetched=(?P<fetched>\d+) retired=(?P<retired>\d+) trap=(?P<trap>\d+) "
    r"fault=(?P<fault>\d+) sigerr=(?P<sigerr>\d+) applyovf=(?P<applyovf>\d+) "
    r"depth=(?P<depth>\d+) completions=(?P<completions>\d+)$",
    re.MULTILINE,
)
DEPLOY_RE = re.compile(
    r"^DEPLOY (?P<index>\d+) cases=(?P<cases>\d+) diverged=(?P<diverged>\d+) "
    r"issues=(?P<issues>\d+) views=(?P<views>\d+) "
    r"predicates=(?P<predicates>\d+) depth=(?P<depth>\d+)$",
    re.MULTILINE,
)
STALLS_RE = re.compile(
    r"^STALLS case=(?P<index>\d+) wait=(?P<wait>\d+) dep=(?P<dep>\d+)$",
    re.MULTILINE,
)
HOST_LOAD_RE = re.compile(
    r"^HOST_LOAD program_rows=(?P<program>\d+) descriptor_rows=(?P<desc>\d+) "
    r"writes=(?P<writes>\d+) refused=(?P<refused>\d+)$",
    re.MULTILINE,
)
RUN_AHEAD_RE = re.compile(
    r"^RUN_AHEAD seed=(?P<seed>\d+) max_delay=(?P<max_delay>\d+) "
    r"reorder=(?P<reorder>\d+)$",
    re.MULTILINE,
)
MAX_DEPTH_RE = re.compile(r"max_depth=(\d+)")
CHECKS_RE = re.compile(r"checks=(\d+)")
# The front end's live bounds, read from the package so the artifact says
# what the RTL held rather than restating it.
LIVE_BOUND_RE = re.compile(
    r"localparam\s+integer\s+(A3_EVENT_COUNT|A3_OUTSTANDING|A3_QUEUE_DEPTH|"
    r"A3_QUEUE_COUNT|A3_IRS_ENTRIES|A3_DEP_RANGES)\s*=\s*(\w+)\s*;"
)
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


def git_identity() -> dict[str, Any]:
    """The commit the artifact was produced at, and whether the tree was clean.

    Recorded beside the source digests, not instead of them: the digests bind
    the artifact to its inputs, the commit says where those inputs came from.
    """
    def run(args: list[str]) -> str:
        try:
            result = subprocess.run(
                args, cwd=ROOT, capture_output=True, text=True, check=False
            )
        except OSError:
            return ""
        return result.stdout if result.returncode == 0 else ""

    head = run(["git", "rev-parse", "HEAD"]).strip()
    status = run(["git", "status", "--porcelain"]).strip()
    return {"commit": head or None, "worktree_dirty": bool(status)}


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
            # Timing, per simulator: the issue record store's high-water
            # mark and the completions the checker's engines reported.
            "run_ahead_depth": int(m.group("depth")),
            "completions": int(m.group("completions")),
        }
        for m in CASE_RE.finditer(log)
    ]
    stalls = {
        int(m.group("index")): {
            "wait_stall_cycles": int(m.group("wait")),
            "dependence_stall_cycles": int(m.group("dep")),
        }
        for m in STALLS_RE.finditer(log)
    }
    for case in cases:
        case.update(stalls.get(case["index"], {}))
    deployments = [
        {
            "deployment_index": int(m.group("index")),
            "cases": int(m.group("cases")),
            "diverged": int(m.group("diverged")),
            "issues_compared": int(m.group("issues")),
            "views_compared": int(m.group("views")),
            "predicates_compared": int(m.group("predicates")),
            "run_ahead_depth": int(m.group("depth")),
        }
        for m in DEPLOY_RE.finditer(log)
    ]
    checks = CHECKS_RE.search(log)
    signal_flags = SIGNAL_FLAG_RE.search(log)
    apply_overflow = APPLY_OVERFLOW_RE.search(log)
    max_depth = MAX_DEPTH_RE.search(log)
    host_load = HOST_LOAD_RE.search(log)
    run_ahead = RUN_AHEAD_RE.search(log)
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
        "max_run_ahead_depth": int(max_depth.group(1)) if max_depth else None,
        "host_load": (
            {key: int(value) for key, value in host_load.groupdict().items()}
            if host_load
            else None
        ),
        "run_ahead_reported": (
            {key: int(value) for key, value in run_ahead.groupdict().items()}
            if run_ahead
            else None
        ),
    }


def run_ahead_plusargs(config: dict[str, Any]) -> list[str]:
    """The checkers' plusargs for one run-ahead configuration."""
    return [
        f"+run_ahead_seed={int(config['seed'])}",
        f"+run_ahead_max_delay={int(config['max_delay'])}",
        f"+run_ahead_reorder={1 if config['reorder'] else 0}",
    ]


BASELINE_RUN_AHEAD = {"seed": 0, "max_delay": 0, "reorder": False}


def simulator_case(
    name: str,
    compile_command: list[str] | None,
    run_command: list[str],
    build: Path,
    marker: str,
    run_ahead: dict[str, Any] | None = None,
    compiled: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile (once) and run one checker under one run-ahead configuration.

    ``compiled`` carries a previous compile stage of the same binary so the
    run-ahead pairs re-run the executable the baseline built rather than
    rebuilding it; the compile log is kept once, on the baseline record.
    """
    config = dict(run_ahead or BASELINE_RUN_AHEAD)
    if compiled is None:
        assert compile_command is not None
        compiled = run_stage(f"{name}.compile", compile_command, build, timeout=1800)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(
            f"{name}.run",
            [*run_command, *run_ahead_plusargs(config)],
            build,
            timeout=14400,
        )
    log = compiled["log"] + (executed["log"] if executed else "")
    observation = parse_observation(executed["log"] if executed else "")
    reported = observation["run_ahead_reported"]
    configuration_echoed = reported is not None and (
        reported["seed"] == int(config["seed"])
        and reported["max_delay"] == int(config["max_delay"])
        and reported["reorder"] == (1 if config["reorder"] else 0)
    )
    passed = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] == 0
        and marker in executed["log"]
        and PROFILE_MARKER in executed["log"]
        and configuration_echoed
        and observation["host_load"] is not None
        and observation["host_load"]["refused"] == 0
    )
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "run_ahead": config,
        "run_ahead_echoed_by_checker": configuration_echoed,
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
        "max_run_ahead_depth": observation["max_run_ahead_depth"],
        "host_load": observation["host_load"],
        "observed_cases": observation["cases"],
        "observed_deployments": observation["deployments"],
        "_compiled": compiled,
    }


OBSERVATION_KEYS = (
    "index", "tag", "verdict", "divergence_code", "rtl_value",
    "golden_value", "issues_compared", "views_compared",
    "predicates_compared", "predicates_expected", "rtl_fetched",
    "rtl_retired", "rtl_trap_class", "rtl_first_fault",
    "rtl_event_signal_error", "rtl_state_apply_overflow",
)


def projection(entry: dict[str, Any]) -> list[tuple[Any, ...]]:
    """One checker's observation of every case, without its timing fields."""
    return [
        tuple(case[key] for key in OBSERVATION_KEYS)
        for case in entry["observed_cases"]
    ]


def compare_simulators(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Require the two simulators to have observed the same thing.

    Not only the same verdict: the same divergence site, the same values on
    both sides of it, and the same number of issues, views and data-dependent
    predicate reads reached before it.  Two engines agreeing on where the RTL
    stopped is what makes a divergence a finding rather than one simulator's
    opinion.  The run-ahead depth and the stall cycles are timing, per
    simulator, and are deliberately outside the projection.
    """
    projections = [projection(entry) for entry in cases]
    agree = len(set(map(tuple, projections))) == 1 and bool(projections[0])
    return {
        "simulators_observed_the_same_cases": agree,
        "compared_fields": list(OBSERVATION_KEYS),
        "case_count_per_simulator": [len(p) for p in projections],
    }


def live_bounds() -> dict[str, Any]:
    """The front end's bounds as rtl/abi3/ot_a3_pkg.sv holds them now.

    The vector set records the bounds it was built against
    (``rtl_implementation_bounds``); the RTL may only have widened since (AM-C1
    took A3_EVENT_COUNT to 2,048), and a wider bound admits everything the
    narrower one did.  Both are recorded so the artifact says which is which.
    """
    text = (ROOT / "rtl/abi3/ot_a3_pkg.sv").read_text(encoding="utf-8")
    found: dict[str, Any] = {}
    for name, value in LIVE_BOUND_RE.findall(text):
        found[name] = int(value) if value.isdigit() else value
    for name, value in list(found.items()):
        if isinstance(value, str) and value in found:
            found[name] = found[value]
    return {
        "source": "rtl/abi3/ot_a3_pkg.sv",
        "values": found,
        "note": (
            "A3_EVENT_COUNT is the scoreboard's event space (AM-C1: 2,048); "
            "A3_OUTSTANDING and A3_QUEUE_DEPTH are the per-die and per-queue "
            "outstanding bounds at which issue stalls (section 3.2 item 2); "
            "the capability records still publish max_event_id 1,023 because "
            "they are certificate inputs of the bound deployments, so "
            "re-publishing them is AM-C1's separate step"
        ),
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


def run(
    build_root: Path | None = None,
    run_ahead: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The campaign: the zero-run-ahead baseline pair, then the run-ahead pairs.

    ``run_ahead`` is ``{"seeds": [...], "max_delay": N, "reorder": bool,
    "deep_seed": N | None, "deep_max_delay": N | None}``; None runs the
    baseline only.
    """
    vectors = load_vectors()
    marker = vectors["required_marker"]
    run_ahead = dict(run_ahead or {})
    configurations: list[dict[str, Any]] = []
    for seed in run_ahead.get("seeds") or []:
        configurations.append(
            {
                "label": f"seed_{seed}_delay_{run_ahead['max_delay']}",
                "seed": int(seed),
                "max_delay": int(run_ahead["max_delay"]),
                "reorder": bool(run_ahead.get("reorder", False)),
            }
        )
    if run_ahead.get("deep_seed") is not None:
        configurations.append(
            {
                "label": f"deep_seed_{run_ahead['deep_seed']}_delay_{run_ahead['deep_max_delay']}",
                "seed": int(run_ahead["deep_seed"]),
                "max_delay": int(run_ahead["deep_max_delay"]),
                "reorder": bool(run_ahead.get("reorder", False)),
            }
        )

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
        iverilog_run = [str(executables["vvp"]), "a3_deploy.vvp"]
        verilator_run = ["./obj_a3_deploy/Vot_a3_microsequencer_top"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    simulator_case, "iverilog", iverilog_compile, iverilog_run,
                    build, marker,
                ),
                pool.submit(
                    simulator_case, "verilator", verilator_compile,
                    verilator_run, build, marker,
                ),
            ]
            cases = [future.result() for future in futures]
        # The run-ahead pairs, one after the other, each pair in parallel,
        # on the binaries the baseline built.
        run_ahead_runs: list[dict[str, Any]] = []
        for config in configurations:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(
                        simulator_case, "iverilog", None, iverilog_run, build,
                        marker, config, cases[0]["_compiled"],
                    ),
                    pool.submit(
                        simulator_case, "verilator", None, verilator_run,
                        build, marker, config, cases[1]["_compiled"],
                    ),
                ]
                pair = [future.result() for future in futures]
            for entry in pair:
                entry.pop("_compiled", None)
                entry.pop("compile_log", None)
            run_ahead_runs.append(
                {
                    "label": config["label"],
                    "seed": config["seed"],
                    "max_delay": config["max_delay"],
                    "reorder": config["reorder"],
                    "cases": pair,
                    "cross_simulator_agreement": compare_simulators(pair),
                    "max_run_ahead_depth": max(
                        (entry["max_run_ahead_depth"] or 0) for entry in pair
                    ),
                }
            )
        for entry in cases:
            entry.pop("_compiled", None)

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
    # Rule 1: every run-ahead pair must observe exactly what the baseline
    # observed, on every case, under both simulators; the site of any
    # difference is named.
    baseline_projection = projection(cases[0])
    run_ahead_differences: list[dict[str, Any]] = []
    for run_entry in run_ahead_runs:
        for entry in run_entry["cases"]:
            observed = projection(entry)
            if observed == baseline_projection:
                continue
            for base_case, ra_case in zip(baseline_projection, observed):
                for key, base_value, ra_value in zip(
                    OBSERVATION_KEYS, base_case, ra_case
                ):
                    if base_value != ra_value:
                        run_ahead_differences.append(
                            {
                                "run": run_entry["label"],
                                "simulator": entry["name"],
                                "case_index": base_case[0],
                                "field": key,
                                "baseline": base_value,
                                "run_ahead": ra_value,
                            }
                        )
                        break
            if len(observed) != len(baseline_projection):
                run_ahead_differences.append(
                    {
                        "run": run_entry["label"],
                        "simulator": entry["name"],
                        "case_index": None,
                        "field": "case_count",
                        "baseline": len(baseline_projection),
                        "run_ahead": len(observed),
                    }
                )
    run_ahead_block = {
        "baseline": {
            "seed": 0,
            "max_delay": 0,
            "reorder": False,
            "meaning": (
                "every accepted operation completes in the cycle after its "
                "acceptance, oldest first: the zero-run-ahead regression of "
                "the retained observation (rule 1)"
            ),
            "checks_per_simulator": [entry["checks"] for entry in cases],
            "max_run_ahead_depth_per_simulator": [
                entry["max_run_ahead_depth"] for entry in cases
            ],
            "marker_present_per_simulator": [
                entry["marker_present"] for entry in cases
            ],
        },
        "runs": run_ahead_runs,
        "seeds": sorted({run_entry["seed"] for run_entry in run_ahead_runs}),
        "seed_count": len({run_entry["seed"] for run_entry in run_ahead_runs}),
        "max_run_ahead_exercised": max(
            [run_entry["max_run_ahead_depth"] for run_entry in run_ahead_runs]
            + [entry["max_run_ahead_depth"] or 0 for entry in cases]
        ),
        "checks_total": sum(
            (entry["checks"] or 0)
            for run_entry in run_ahead_runs
            for entry in run_entry["cases"]
        )
        + sum((entry["checks"] or 0) for entry in cases),
        "observation_identical_to_baseline": not run_ahead_differences,
        "differences_from_baseline": run_ahead_differences,
        "completion_model": (
            "xorshift32 seeded per case with (seed ^ ((case_index + 1) * "
            "0x9E3779B9)) | 1; delay 0 when max_delay is 0, else 1 + rand % "
            "max_delay cycles after acceptance; with reorder the completion "
            "reported each cycle is drawn by rand % count among the due "
            "operations, else the oldest; written independently in "
            "rtl/test/tb_a3_deployment.sv and rtl/test/a3_deployment_harness.cpp"
        ),
        "depth_is_per_simulator": (
            "run_ahead_depth is the issue record store's high-water mark "
            "(dbg_max_outstanding); it is timing, differs between the two "
            "checkers' acceptance patterns by design, and is never required to "
            "agree across simulators, only reported; the maximum over every "
            "run and simulator is max_run_ahead_exercised"
        ),
        "counters_that_may_differ": [
            "queue.max_occupancy (group 0x02, 0x0200000a): the RTL exposes it "
            "as dbg_max_outstanding and the golden model writes it only under "
            "a RunAheadPolicy; it is timing and is not compared",
            "instructions.retired timing: counted at completion rather than "
            "at issue (section 3.2 item 3); its value at done is identical "
            "and is compared",
            "wait and dependence stall cycles (dbg_wait_stalls, "
            "dbg_dep_stalls): reported per case and simulator, never compared",
        ],
    }
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
        and all(
            entry["status"] == "pass"
            and run_entry["cross_simulator_agreement"][
                "simulators_observed_the_same_cases"
            ]
            for run_entry in run_ahead_runs
            for entry in run_entry["cases"]
        )
        and not run_ahead_differences
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
        "rtl_live_bounds": live_bounds(),
        "run_ahead": run_ahead_block,
        "front_end": {
            "issue_to_completion": "asynchronous (section 3.2 item 2)",
            "retirement": "at completion without fault (section 3.2 item 3)",
            "structures": [
                "issue record store 32 entries, queues 23 x 16 "
                "(rtl/abi3/ot_a3_issue_record_store.sv)",
                "dependence table 32 entries x 4 ranges "
                "(rtl/abi3/ot_a3_dependence_table.sv)",
                "event scoreboard 2,048 x {pending, signalled, published}, "
                "four read ports (rtl/abi3/ot_a3_event_scoreboard.sv, AM-C1, "
                "AM-C10)",
                "six resolver lanes on one shared divider "
                "(rtl/abi3/ot_a3_resolver_bank.sv, "
                "rtl/abi3/ot_a3_shared_divider.sv)",
                "runtime symbol file 16 x 64-bit with bound bits, host-written "
                "(rtl/abi3/ot_a3_symbol_file.sv)",
            ],
            "not_pipelined_across_instructions": (
                "the front end resolves and issues one instruction at a time; "
                "only issue to completion is asynchronous, so section 3.3's "
                "per-stage occupancy is not claimed by this campaign"
            ),
        },
        "host_load": {
            "path": "ot_a3_device_top host_* (program store, descriptor store, "
                    "symbol file) and hdr_in_* (program header)",
            "wrapper_readmemh_of_control_images": False,
            "per_simulator": [entry["host_load"] for entry in cases],
        },
        "tools": tools,
        "git": git_identity(),
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
                "fit is refused at admission rather than discovered here",
                "the front end is asynchronous: an engine operation leaves at "
                "issue with a serial and an issue-record slot and is completed "
                "by the checker's engines after a seeded delay, in a seeded "
                "order; the observation stream (issues, views, predicate "
                "reads, counters, retire counts, trap class, first fault) is "
                "identical to the zero-run-ahead baseline on every case, "
                "under both simulators, for every run in run_ahead.runs",
                "the control stores and the symbol file are loaded through "
                "the design's own host path by the checkers and the program "
                "header through the admission beat port; the wrapper holds "
                "no image and runs no $readmemh (section 13 item 12)"
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
                "the selection engine, or the 32-node agreement logic",
                "engine_faults_under_run_ahead": "the checker's engines never "
                "fault, so the asynchronous fault path (section 3.2 item 5: "
                "stop issue in the cycle a fault is reported, drain, restore "
                "the counters from the faulting operation's snapshot) is "
                "exercised only at depth 1 by the shipped-prefix campaign's "
                "capability faults, not here",
                "predicate_reads_under_run_ahead": "a BOOLEAN_OBJECT or "
                "EOS_MEMBER read of an instruction after an outstanding "
                "operation is requested before that operation completes; "
                "under an engine fault of that operation the golden model "
                "would never have made the read. The RTL cancels the request "
                "at the fault; no case here faults, so the side effect is "
                "stated, not observed",
                "run_ahead_depth_on_the_shipped_programs": "the depth the "
                "shipped programs reach is bounded by their own wait sets "
                "(every engine instruction's successor waits on its event, "
                "and a wait whose producer was re-issued on the current loop "
                "trip stalls while it is pending, AM-C10) and by the "
                "dependence table's conservative ranges, not by the 16-per-"
                "queue and 32-per-die bounds; see run_ahead.max_run_ahead_"
                "exercised for the depth reached and the per-case stall "
                "cycles for why",
                "frontier_streaming": "not implemented: every dependence "
                "entry exposes frontier 0, so a consumer waits for its "
                "producer's completion (section 3.6, non-architectural)"
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
    parser.add_argument(
        "--run-ahead-seeds",
        default="",
        help="comma-separated seeds; one Icarus + Verilator pair per seed "
             "at --run-ahead-max-delay",
    )
    parser.add_argument("--run-ahead-max-delay", type=int, default=64)
    parser.add_argument(
        "--run-ahead-reorder",
        action="store_true",
        help="draw the completion order as well as the delay",
    )
    parser.add_argument("--deep-seed", type=int, default=None)
    parser.add_argument("--deep-max-delay", type=int, default=1024)
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        print(
            f"refusing to overwrite {args.output}; pass --force to replace it",
            file=sys.stderr,
        )
        return 2

    run_ahead = {
        "seeds": [int(seed) for seed in args.run_ahead_seeds.split(",") if seed],
        "max_delay": args.run_ahead_max_delay,
        "reorder": args.run_ahead_reorder,
        "deep_seed": args.deep_seed,
        "deep_max_delay": args.deep_max_delay,
    }
    summary = run(args.build_dir, run_ahead)
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
    block = summary["run_ahead"]
    for run_entry in block["runs"]:
        print(
            f"  run-ahead {run_entry['label']}: "
            + ", ".join(
                f"{entry['name']} {entry['status'].upper()} checks={entry['checks']} "
                f"depth={entry['max_run_ahead_depth']}"
                for entry in run_entry["cases"]
            )
        )
    print(
        f"  run-ahead seeds={block['seed_count']} "
        f"max_depth={block['max_run_ahead_exercised']} "
        f"checks_total={block['checks_total']} "
        f"identical_to_baseline={block['observation_identical_to_baseline']}"
    )
    print(f"abi3 deployment rtl campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
