#!/usr/bin/env python3
"""Correlate the frozen shipped-prefix multicast integration in two simulators.

Pinned Verilator executes all four shipped-prefix cases.  Icarus executes the
DeepSeek ROM case only, avoiding the interpreted cost of Qwen's complete QKV
MATMULs while still covering the same sequencer-to-multicast integration.  The
unchanged multicast adapter is additionally bound to its retained 38-case
dual-simulator qualification.  Simulator runtime is verification cost, never
architectural TPOT.
"""

from __future__ import annotations

import argparse
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
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import rtl_abi3_shipped_prefix_campaign as base_campaign  # noqa: E402


EXTENSION_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix_multicast"
EXTENSION_JSON = EXTENSION_DIR / "abi3_shipped_prefix_multicast_vectors.json"
MULTICAST_CAMPAIGN = ROOT / "results/rtl/a3_wafer_multicast_campaign.json"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_shipped_prefix_multicast_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

# Retained exact counts from the independent checkers below.
EXPECTED_VERILATOR_CHECKS = 12_756_659
EXPECTED_IVERILOG_CHECKS = 12_587_599

RTL_SOURCES = (
    "rtl/lib/ot_crc_pkg.sv",
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/ot_ta_command_decoder.sv",
    "rtl/ot_ta_rope_bf16_sram_engine.sv",
    "rtl/abi3/ot_a3_link_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
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
    "rtl/abi3/ot_a3_mac_lane.sv",
    "rtl/abi3/ot_a3_selection_argmax.sv",
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    "rtl/abi3/ot_a3_vector_add.sv",
    "rtl/abi3/ot_a3_vector_convert.sv",
    "rtl/abi3/ot_a3_vector_scale.sv",
    "rtl/abi3/ot_a3_vector_hadamard.sv",
    "rtl/abi3/ot_a3_vector_index_score.sv",
    "rtl/abi3/ot_a3_vector_compress_project.sv",
    "rtl/abi3/ot_a3_vector_mhc_post.sv",
    "rtl/abi3/ot_a3_engine_array.sv",
    "rtl/abi3/ot_a3_vector_rms_norm.sv",
    "rtl/abi3/ot_a3_vector_rope.sv",
    "rtl/abi3/ot_a3_engine_issue_bridge.sv",
    "rtl/abi3/ot_a3_communication_decoder.sv",
    "rtl/abi3/ot_a3_link_channel.sv",
    "rtl/abi3/ot_a3_link_endpoint.sv",
    "rtl/abi3/ot_a3_link_node.sv",
    "rtl/abi3/ot_a3_wafer_multicast_adapter.sv",
)
TEST_SOURCES = (
    "rtl/test/a3_shipped_prefix_multicast_adapter_wrapper.sv",
    "rtl/test/a3_engine_completion_adapter.sv",
    "rtl/test/a3_shipped_prefix_top.sv",
    "rtl/test/a3_shipped_prefix_harness.cpp",
    "rtl/test/tb_a3_shipped_prefix_deepseek_rom.sv",
)
CONTRACT_SOURCES = base_campaign.CONTRACT_SOURCES
TOOL_SOURCES = (
    "tools/build_abi3_deployment_rtl_vectors.py",
    "tools/build_abi3_shipped_prefix_vectors.py",
    "tools/rtl_abi3_shipped_prefix_campaign.py",
    "tools/build_abi3_shipped_prefix_multicast_vectors.py",
    "tools/rtl_abi3_shipped_prefix_multicast_campaign.py",
)
BASE_VECTOR_FILES = (
    "p3_case.hex",
    "p3_issue.hex",
    "p3_index.hex",
    "p3_source.hex",
    "p3_expect.hex",
    "p3_meta.hex",
)

CASE_RE = re.compile(
    r"^CASE (?P<index>\d+) OK launches=(?P<launches>\d+) "
    r"words=(?P<words>\d+) responses=(?P<responses>\d+) "
    r"trap=(?P<trap>\d+) fault=(?P<fault>\d+) "
    r"fetched=(?P<fetched>\d+) retired=(?P<retired>\d+) "
    r"issued=(?P<issued>\d+) views=(?P<views>\d+) "
    r"multicasts=(?P<multicast_launches>\d+)$",
    re.MULTILINE,
)
CHECK_RE = re.compile(r"checks=(\d+)")


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


def canonical(text: str, build: Path | None = None) -> str:
    if build is not None:
        text = text.replace(str(build), "<BUILD>")
    return text.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def load_extension(base: dict[str, Any]) -> dict[str, Any]:
    if not EXTENSION_JSON.is_file():
        raise SystemExit(f"missing frozen multicast overlay: {EXTENSION_JSON}")
    body = json.loads(EXTENSION_JSON.read_text(encoding="utf-8"))
    if (
        body.get("schema") != "opentallas.rtl.abi3_shipped_prefix_multicast_vectors.v1"
        or body.get("abi") != {"major": 3, "minor": 0}
        or body.get("status") != "source_current_rtl_integration_only"
        or body.get("promotion_status") != "source_current_bounded_prefix_only"
    ):
        raise SystemExit("the frozen multicast overlay has an unknown status")
    for name, expected in body["image_sha256"].items():
        if sha256_file(EXTENSION_DIR / name) != expected:
            raise SystemExit(f"frozen multicast overlay image changed: {name}")
    base_record = body["base_vector_set"]
    if (
        sha256_file(base_campaign.VECTOR_JSON) != base_record["sha256"]
        or base["schema"] != base_record["schema"]
        or base["image_sha256"] != base_record["image_sha256"]
        or base["input_deployment_vectors"] != base_record["input_deployment_vectors"]
    ):
        raise SystemExit("the frozen shipped-prefix base identity changed")
    qualification = body["multicast_qualification"]
    for key in ("vector_manifest", "campaign", "adapter_source"):
        path = ROOT / qualification[key]
        if sha256_file(path) != qualification[f"{key}_sha256"]:
            raise SystemExit(f"multicast qualification binding changed: {key}")
    return body


def load_multicast_qualification(extension: dict[str, Any]) -> dict[str, Any]:
    body = json.loads(MULTICAST_CAMPAIGN.read_text(encoding="utf-8"))
    expected_source = extension["multicast_qualification"]["source"]
    positive = body.get("normalized_cases", [{}])[0]
    if (
        body.get("schema") != "opentallas.rtl.a3_wafer_multicast_campaign.v1"
        or body.get("status") != "pass"
        or body.get("simulators_agree") is not True
        or body.get("checks") != 12_583_553
        or body.get("source") != expected_source
        or body.get("source_sha256", {}).get(
            "rtl/abi3/ot_a3_wafer_multicast_adapter.sv"
        )
        != sha256_file(ROOT / "rtl/abi3/ot_a3_wafer_multicast_adapter.sv")
        or positive.get("index") != 0
        or positive.get("admitted") != 1
        or positive.get("messages") != 255
        or positive.get("payload_flits") != 4_177_920
        or positive.get("writes") != 4_194_304
        or positive.get("crc_errors") != 1
        or positive.get("replayed") != 4
        or positive.get("retries") != 1
    ):
        raise SystemExit("the retained multicast qualification changed")
    return {
        "artifact": str(MULTICAST_CAMPAIGN.relative_to(ROOT)),
        "artifact_sha256": sha256_file(MULTICAST_CAMPAIGN),
        "schema": body["schema"],
        "status": body["status"],
        "simulators_agree": True,
        "checks_per_simulator": body["checks"],
        "adapter_source_sha256": body["source_sha256"][
            "rtl/abi3/ot_a3_wafer_multicast_adapter.sv"
        ],
        "exact_case": positive,
        "composition_boundary": (
            "the unchanged adapter and complete records are qualified in 38 "
            "cases under both Icarus and Verilator; this campaign separately "
            "correlates its integration into the shipped sequencer prefix"
        ),
    }


def tool_record(path: Path, args: list[str]) -> dict[str, str]:
    proc = subprocess.run(
        [str(path), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if proc.returncode != 0:
        raise SystemExit(f"tool probe failed: {path}")
    return {
        "executable": canonical(str(path.resolve())),
        "executable_sha256": sha256_file(path.resolve()),
        "version": lines[0] if lines else "no version text",
    }


def run_stage(
    name: str, command: list[str], build: Path, timeout: int
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=build,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        returncode = proc.returncode
        output = proc.stdout
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        output = (exc.stdout or "") + (exc.stderr or "") + "\nTIMEOUT\n"
    return {
        "name": name,
        "command": canonical(shlex.join(command), build),
        "returncode": returncode,
        "log": canonical(output, build),
        "verification_wall_seconds": time.monotonic() - started,
    }


def observation(log: str) -> dict[str, Any]:
    cases = [
        {key: int(value) for key, value in match.groupdict().items()}
        for match in CASE_RE.finditer(log)
    ]
    checks = CHECK_RE.findall(log)
    return {"cases": cases, "checks": int(checks[-1]) if checks else None}


def simulate(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
    marker: str,
    expected_case_count: int,
    timeout: int,
) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, build, 1800)
    executed = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout)
    log = executed["log"] if executed else ""
    parsed = observation(log)
    passed = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] == 0
        and marker in log
        and len(parsed["cases"]) == expected_case_count
        and parsed["checks"] is not None
    )
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log": compiled["log"],
        "compile_verification_wall_seconds": compiled["verification_wall_seconds"],
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log": log,
        "run_verification_wall_seconds": (
            executed["verification_wall_seconds"] if executed else None
        ),
        "required_marker": marker,
        "marker_present": marker in log,
        "checks": parsed["checks"],
        "observed_cases": parsed["cases"],
        "log_sha256": hashlib.sha256(
            (compiled["log"] + log).encode("utf-8")
        ).hexdigest(),
    }


def run(build_root: Path | None = None) -> dict[str, Any]:
    base = base_campaign.load_vectors()
    extension = load_extension(base)
    lane = base_campaign.load_lane_qualification()
    rope = base_campaign.load_rope_qualification()
    multicast_qualification = load_multicast_qualification(extension)

    resolved = {
        "iverilog": Path(shutil.which("iverilog") or ""),
        "vvp": Path(shutil.which("vvp") or ""),
        "verilator": TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator",
        "cxx": Path(shutil.which("g++") or ""),
    }
    if any(not path.is_file() for path in resolved.values()):
        raise SystemExit("Icarus, vvp, pinned Verilator, and g++ are required")
    tools = {
        "iverilog": tool_record(resolved["iverilog"], ["-V"]),
        "vvp": tool_record(resolved["vvp"], ["-V"]),
        "verilator": tool_record(resolved["verilator"], ["--version"]),
        "cxx": tool_record(resolved["cxx"], ["--version"]),
    }
    if not tools["verilator"]["version"].startswith(
        f"Verilator {PINNED_VERILATOR_VERSION}"
    ):
        raise SystemExit("the pinned Verilator 5.050 build is required")

    temporary = None
    if build_root is None:
        temporary = tempfile.TemporaryDirectory(
            prefix="opentallas-abi3-prefix-multicast-"
        )
        build = Path(temporary.name)
    else:
        build = build_root
        build.mkdir(parents=True, exist_ok=True)
    try:
        for name in base_campaign.DEPLOYMENT_IMAGES:
            shutil.copy2(base_campaign.DEPLOYMENT_VECTOR_DIR / name, build / name)
        for name in BASE_VECTOR_FILES:
            shutil.copy2(base_campaign.VECTOR_DIR / name, build / name)
        for name in extension["image_sha256"]:
            shutil.copy2(EXTENSION_DIR / name, build / name)
        staged_matmul_weight = base_campaign.stage_matmul_weight(
            base, build / "p3_matmul_weight.bin"
        )

        rtl = [str(ROOT / path) for path in RTL_SOURCES]
        verilator = simulate(
            "verilator_full_four_case",
            [
                str(resolved["verilator"]),
                "--cc",
                "--exe",
                "--build",
                "-Wall",
                "-Wno-fatal",
                "-Wno-DECLFILENAME",
                "-Wno-PINMISSING",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                "-GENABLE_EXACT_MULTICAST=1",
                "--top-module",
                "ot_a3_shipped_prefix_top",
                "--Mdir",
                "obj_p3_multicast",
                *rtl,
                str(ROOT / "rtl/test/a3_engine_completion_adapter.sv"),
                str(ROOT / "rtl/test/a3_shipped_prefix_multicast_adapter_wrapper.sv"),
                str(ROOT / "rtl/test/a3_shipped_prefix_top.sv"),
                str(ROOT / "rtl/test/a3_shipped_prefix_harness.cpp"),
                "-CFLAGS",
                "-std=c++17",
            ],
            ["./obj_p3_multicast/Vot_a3_shipped_prefix_top"],
            build,
            extension["required_marker"],
            4,
            5400,
        )
        iverilog = simulate(
            "iverilog_deepseek_rom_only",
            [
                str(resolved["iverilog"]),
                "-g2012",
                "-s",
                "tb_a3_shipped_prefix_deepseek_rom",
                "-o",
                "deepseek_rom_multicast.vvp",
                *rtl,
                str(ROOT / "rtl/test/a3_engine_completion_adapter.sv"),
                str(ROOT / "rtl/test/a3_shipped_prefix_multicast_adapter_wrapper.sv"),
                str(ROOT / "rtl/test/a3_shipped_prefix_top.sv"),
                str(ROOT / "rtl/test/tb_a3_shipped_prefix_deepseek_rom.sv"),
            ],
            [str(resolved["vvp"]), "./deepseek_rom_multicast.vvp"],
            build,
            "PASS: ABI3 shipped-prefix DeepSeek-ROM multicast integration",
            1,
            1800,
        )
    finally:
        if temporary is not None:
            temporary.cleanup()

    expected_cases = extension["expected_cases"]
    verilator_cases_match = verilator["observed_cases"] == [
        {key: value for key, value in case.items() if key != "name"}
        for case in expected_cases
    ]
    iverilog_case_match = (
        iverilog["observed_cases"] == [verilator["observed_cases"][2]]
        if len(verilator["observed_cases"]) == 4
        else False
    )
    exact_checks = (
        EXPECTED_VERILATOR_CHECKS > 0
        and EXPECTED_IVERILOG_CHECKS > 0
        and verilator["checks"] == EXPECTED_VERILATOR_CHECKS
        and iverilog["checks"] == EXPECTED_IVERILOG_CHECKS
    )
    passed = (
        verilator["status"] == "pass"
        and iverilog["status"] == "pass"
        and verilator_cases_match
        and iverilog_case_match
        and exact_checks
    )

    source_paths = (
        *RTL_SOURCES,
        *TEST_SOURCES,
        *CONTRACT_SOURCES,
        *TOOL_SOURCES,
    )
    source = {
        path: {
            "sha256": sha256_file(ROOT / path),
            "bytes": (ROOT / path).stat().st_size,
        }
        for path in source_paths
    }
    return {
        "schema": "opentallas.rtl.abi3_shipped_prefix_multicast_campaign.v1",
        "status": "pass" if passed else "fail",
        "evidence_class": "frozen_identity_public_open_tool_rtl_simulation",
        "evidence_mode": (
            "four_case_verilator_plus_deepseek_rom_icarus_correlation_plus_"
            "retained_multicast_mac_lane_and_rope_qualification"
        ),
        "abi": {"major": 3, "minor": 0},
        "promotion_status": extension["promotion_status"],
        "promotion_blocker": extension["promotion_blocker"],
        "scope": {
            "establishes": [
                "the frozen DeepSeek ROM shipped program retires exact PC-13 LINK.MULTICAST and then traps precisely at PC-15 VECTOR.MHC",
                "all 4,194,304 destination writes reproduce the independent nonzero live-buffer payload in ascending order for every one of 256 participants",
                "every non-root destination observes the exact binomial-tree parent relation",
                "one injected CRC error causes bounded packet replay and exact final replication under deterministic source and destination backpressure",
                "the normalized DeepSeek ROM case record agrees between Icarus and pinned Verilator",
                "the full four-case replay preserves all 91,136 prior compact result words, including 10,240 exact Qwen RoPE codes, and every other precise unsupported boundary",
            ],
            "does_not_establish": extension["does_not_establish"],
            "host_wall_time_is_verification_cost_only": True,
            "architectural_tpot_claim": False,
            "decoded_token_correctness_claim": False,
        },
        "frozen_vector_overlay": {
            "path": str(EXTENSION_JSON.relative_to(ROOT)),
            "sha256": sha256_file(EXTENSION_JSON),
            "schema": extension["schema"],
            "base_vector_set": extension["base_vector_set"],
            "image_sha256": extension["image_sha256"],
        },
        "staged_matmul_weight": staged_matmul_weight,
        "compositional_mac_lane_qualification": lane,
        "compositional_rope_qualification": rope,
        "compositional_multicast_qualification": multicast_qualification,
        "expected_cases": expected_cases,
        "case_count": 4,
        "real_launch_count": 29,
        "multicast_launch_count": 1,
        "result_word_count": 91_136,
        "resolved_view_count": 100,
        "capability_fault_count": 4,
        "next_unsupported": extension["exact_multicast"]["next_unsupported"],
        "integrated_replay_passed": passed,
        "simulator_correlation": {
            "verilator_cases_match": verilator_cases_match,
            "deepseek_rom_cases_agree": iverilog_case_match,
            "exact_check_counts_match_retained_constants": exact_checks,
        },
        "integrated_simulator_checks": {
            "verilator_full_four_case": verilator["checks"],
            "iverilog_deepseek_rom_only": iverilog["checks"],
        },
        "tools": tools,
        "git": git_identity(),
        "source": source,
        "cases": [verilator, iverilog],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 2
    summary = run(args.build_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for case in summary["cases"]:
        print(f"{case['name']}: {case['status'].upper()} checks={case['checks']}")
    print(
        f"ABI3 shipped-prefix multicast campaign: {summary['status'].upper()} "
        f"promotion={summary['promotion_status']}"
    )
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
