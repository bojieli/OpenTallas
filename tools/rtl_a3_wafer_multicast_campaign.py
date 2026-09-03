#!/usr/bin/env python3
"""Run the focused two-simulator DeepSeek wafer-multicast RTL campaign.

The campaign executes one exact full-payload operation and 37 fail-closed
mutations in Icarus and pinned Verilator, requires identical normalized case
records, and writes a source-hashed evidence artifact.  Reported host wall time
is verification cost only; this time-multiplexed adapter is not a TPOT model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = ROOT / "testdata/rtl/a3_wafer_multicast"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_wafer_multicast_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
MINIMUM_IVERILOG_VERSION = (11, 0)
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/lib/ot_crc_pkg.sv",
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_link_pkg.sv",
    "rtl/abi3/ot_a3_communication_decoder.sv",
    "rtl/abi3/ot_a3_link_channel.sv",
    "rtl/abi3/ot_a3_link_endpoint.sv",
    "rtl/abi3/ot_a3_link_node.sv",
    "rtl/abi3/ot_a3_wafer_multicast_adapter.sv",
    "rtl/test/tb_a3_wafer_multicast.sv",
)
CONTRACT_SOURCES = (
    "spec/abi3/registries.json",
    "spec/abi3/descriptor_payloads.json",
    "spec/abi3/records.json",
    "runtime/abi3/constants.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/records.py",
    "runtime/sim/engines/link.py",
    "runtime/cycle/fabric.py",
    "runtime/cycle/model.py",
)
TOOL_SOURCES = (
    "tools/build_a3_wafer_multicast_vectors.py",
    "tools/rtl_a3_wafer_multicast_campaign.py",
)
VECTOR_FILES = (
    "case_meta.hex",
    "communication.hex",
    "topology.hex",
    "local_object.hex",
    "remote_object.hex",
    "counter.hex",
    "index.json",
)

CASE_RE = re.compile(r"^CASE (?P<index>\d+) (?P<body>.+)$")
PASS_RE = re.compile(r"^PASS a3_wafer_multicast checks=(?P<checks>\d+)$")
KV_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub(text: str, temporary_root: Path | None = None) -> str:
    if temporary_root is not None:
        text = text.replace(str(temporary_root), "<TMP>")
    return text.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def run(
    command: list[str], *, cwd: Path = ROOT, timeout: int = 900
) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timed out after {timeout}s: {command[0]}") from exc
    return proc, time.monotonic() - started


def executable_identity(
    executable: Path, args: list[str], pattern: re.Pattern[str],
    minimum: tuple[int, int], name: str,
) -> dict[str, Any]:
    proc, _ = run([str(executable), *args], timeout=30)
    text = (proc.stdout + proc.stderr).strip()
    if proc.returncode:
        raise RuntimeError(f"{name} version probe failed: {text}")
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"cannot parse {name} version: {text!r}")
    version = (int(match.group("major")), int(match.group("minor")))
    if version < minimum:
        raise RuntimeError(f"{name} {version} is below required {minimum}")
    return {
        "path": scrub(str(executable.resolve())),
        "sha256": sha256(executable.resolve()),
        "version": text.splitlines()[0],
    }


def resolve_tools() -> tuple[Path, Path, Path]:
    iverilog_name = shutil.which("iverilog")
    vvp_name = shutil.which("vvp")
    if not iverilog_name or not vvp_name:
        raise RuntimeError("Icarus Verilog and vvp are required")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    if not verilator.exists():
        raise RuntimeError(f"pinned Verilator is missing: {verilator}")
    return Path(iverilog_name), Path(vvp_name), verilator


def plusargs(vector_root: Path) -> list[str]:
    return [
        f"+META={vector_root / 'case_meta.hex'}",
        f"+COMMUNICATION={vector_root / 'communication.hex'}",
        f"+TOPOLOGY={vector_root / 'topology.hex'}",
        f"+LOCAL={vector_root / 'local_object.hex'}",
        f"+REMOTE={vector_root / 'remote_object.hex'}",
        f"+COUNTER={vector_root / 'counter.hex'}",
    ]


def parse_log(log: str, expected_cases: int) -> tuple[list[dict[str, int]], int]:
    cases: list[dict[str, int]] = []
    checks: int | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = CASE_RE.match(line)
        if match:
            values = {m.group("key"): int(m.group("value")) for m in KV_RE.finditer(match.group("body"))}
            values["index"] = int(match.group("index"))
            cases.append(values)
        passed = PASS_RE.match(line)
        if passed:
            checks = int(passed.group("checks"))
    if [case["index"] for case in cases] != list(range(expected_cases)):
        raise RuntimeError(
            f"simulator emitted case indices {[case['index'] for case in cases]}, "
            f"expected 0..{expected_cases-1}"
        )
    if checks is None:
        raise RuntimeError("simulator did not emit the exact PASS marker")
    return cases, checks


def validate_cases(cases: list[dict[str, int]], manifest: dict[str, Any]) -> None:
    expected = manifest["cases"]
    if len(cases) != len(expected):
        raise RuntimeError("case count mismatch")
    for observed, wanted in zip(cases, expected, strict=True):
        if observed["index"] != wanted["index"]:
            raise RuntimeError("case ordering mismatch")
        if observed.get("admitted") != int(wanted["admitted"]):
            raise RuntimeError(f"case {observed['index']} admission mismatch")
        if observed.get("reason") != wanted["refusal_reason"]:
            raise RuntimeError(f"case {observed['index']} reason mismatch")
    positive = cases[0]
    geometry = manifest["geometry"]
    required = {
        "messages": geometry["messages"],
        "bytes": geometry["payload_bytes"],
        "payload_flits": geometry["payload_flits"],
        "writes": geometry["remote_writes_including_root"],
        "crc_errors": 1,
        "retries": 1,
    }
    for key, wanted in required.items():
        if positive.get(key) != wanted:
            raise RuntimeError(
                f"positive case {key}={positive.get(key)}, expected {wanted}"
            )
    if positive.get("replayed", 0) < 1:
        raise RuntimeError("positive case did not replay a packet")
    for case in cases[1:]:
        if case.get("reads") != 0 or case.get("writes") != 0:
            raise RuntimeError(f"refused case {case['index']} performed memory I/O")


def regenerate_and_compare(temporary_root: Path) -> dict[str, Any]:
    generated = temporary_root / "vectors"
    proc, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_wafer_multicast_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=60,
    )
    if proc.returncode:
        raise RuntimeError(f"vector generation failed:\n{proc.stdout}\n{proc.stderr}")
    for name in VECTOR_FILES:
        if (generated / name).read_bytes() != (VECTOR_DIR / name).read_bytes():
            raise RuntimeError(f"checked-in vector {name} is not source-current")
    return json.loads((generated / "index.json").read_text())


def campaign(output: Path) -> dict[str, Any]:
    iverilog, vvp, verilator = resolve_tools()
    tools = {
        "iverilog": executable_identity(
            iverilog, ["-V"], IVERILOG_RE, MINIMUM_IVERILOG_VERSION, "iverilog"
        ),
        "vvp": {
            "path": scrub(str(vvp.resolve())),
            "sha256": sha256(vvp.resolve()),
        },
        "verilator": executable_identity(
            verilator, ["--version"], VERILATOR_RE, (5, 50), "verilator"
        ),
    }
    if not tools["verilator"]["version"].startswith(
        f"Verilator {PINNED_VERILATOR_VERSION}"
    ):
        raise RuntimeError("resolved Verilator is not the pinned 5.050 build")

    with tempfile.TemporaryDirectory(prefix="a3-wafer-multicast-") as tmp_name:
        tmp = Path(tmp_name)
        manifest = regenerate_and_compare(tmp)
        source_paths = [ROOT / name for name in (*RTL_SOURCES, *CONTRACT_SOURCES, *TOOL_SOURCES)]
        source_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in source_paths}
        vector_hashes = {name: sha256(VECTOR_DIR / name) for name in VECTOR_FILES}

        iverilog_output = tmp / "tb_a3_wafer_multicast.vvp"
        compile_i = [
            str(iverilog), "-g2012", "-s", "tb_a3_wafer_multicast",
            "-o", str(iverilog_output),
            *[str(ROOT / source) for source in RTL_SOURCES],
        ]
        proc, compile_i_seconds = run(compile_i, timeout=300)
        if proc.returncode:
            raise RuntimeError(f"Icarus compile failed:\n{proc.stdout}\n{proc.stderr}")

        proc, run_i_seconds = run(
            [str(vvp), str(iverilog_output), *plusargs(VECTOR_DIR)], timeout=900
        )
        iverilog_log = proc.stdout + proc.stderr
        if proc.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_cases, iverilog_checks = parse_log(
            iverilog_log, manifest["case_count"]
        )
        validate_cases(iverilog_cases, manifest)

        obj = tmp / "obj"
        compile_v = [
            str(verilator), "--binary", "--timing",
            "--top-module", "tb_a3_wafer_multicast",
            "--Mdir", str(obj), "-o", "sim_a3_wafer_multicast",
            "-Wno-fatal", "-Wno-PINMISSING", "-Wno-WIDTHEXPAND",
            "-Wno-WIDTHTRUNC",
            *[str(ROOT / source) for source in RTL_SOURCES],
        ]
        proc, compile_v_seconds = run(compile_v, timeout=300)
        if proc.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{proc.stdout}\n{proc.stderr}")
        proc, run_v_seconds = run(
            [str(obj / "sim_a3_wafer_multicast"), *plusargs(VECTOR_DIR)],
            timeout=300,
        )
        verilator_log = proc.stdout + proc.stderr
        if proc.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_cases, verilator_checks = parse_log(
            verilator_log, manifest["case_count"]
        )
        validate_cases(verilator_cases, manifest)

        if iverilog_cases != verilator_cases:
            raise RuntimeError("Icarus and Verilator normalized case records differ")
        if iverilog_checks != verilator_checks:
            raise RuntimeError("Icarus and Verilator check counts differ")

        result = {
            "schema": "opentallas.rtl.a3_wafer_multicast_campaign.v1",
            "status": "pass",
            "scope": {
                "deployment": manifest["source"]["bundle"],
                "pc": 13,
                "instruction": "LINK.MULTICAST",
                "descriptor_id": 368,
                "exact_full_payload": True,
                "packet_crc_replay_injected": True,
                "time_multiplexed_verification_adapter": True,
                "architectural_tpot_claim": False,
                "host_wall_time_is_verification_cost_only": True,
            },
            "source": manifest["source"],
            "geometry": manifest["geometry"],
            "case_count": manifest["case_count"],
            "checks": iverilog_checks,
            "normalized_cases": iverilog_cases,
            "simulators_agree": True,
            "verification_wall_seconds": {
                "iverilog_compile": compile_i_seconds,
                "iverilog_simulation": run_i_seconds,
                "verilator_compile": compile_v_seconds,
                "verilator_simulation": run_v_seconds,
            },
            "tools": tools,
            "source_sha256": source_hashes,
            "vector_sha256": vector_hashes,
            "log_sha256": {
                "iverilog": hashlib.sha256(iverilog_log.encode()).hexdigest(),
                "verilator": hashlib.sha256(verilator_log.encode()).hexdigest(),
            },
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def validate_retained(path: Path = DEFAULT_OUTPUT) -> list[str]:
    problems: list[str] = []
    try:
        result = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read retained campaign: {exc}"]
    if result.get("status") != "pass":
        problems.append("retained campaign status is not pass")
    if result.get("simulators_agree") is not True:
        problems.append("retained campaign lacks two-simulator agreement")
    scope = result.get("scope", {})
    if scope.get("architectural_tpot_claim") is not False:
        problems.append("retained campaign improperly claims TPOT")
    for name, expected in result.get("source_sha256", {}).items():
        source = ROOT / name
        if not source.exists() or sha256(source) != expected:
            problems.append(f"source hash is stale: {name}")
    for name, expected in result.get("vector_sha256", {}).items():
        vector = VECTOR_DIR / name
        if not vector.exists() or sha256(vector) != expected:
            problems.append(f"vector hash is stale: {name}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        problems = validate_retained(args.output.resolve())
        if problems:
            raise SystemExit("\n".join(problems))
        print(f"PASS retained wafer multicast campaign: {args.output.resolve()}")
        return
    result = campaign(args.output.resolve())
    print(
        f"PASS wafer multicast campaign: {result['case_count']} cases, "
        f"{result['checks']} checks, two simulators agree"
    )


if __name__ == "__main__":
    main()
