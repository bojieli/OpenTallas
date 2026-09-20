#!/usr/bin/env python3
"""Run the focused dual-simulator HC transcendental RTL campaign.

The checked result is arithmetic dependency evidence only.  Simulator wall
time and this conservative certifying engine's controller cycles are not an
architectural token latency and must never be reported as TPOT.
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_hc_transcendental"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_hc_transcendental_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    # The three sequential wide-arithmetic primitives the engine is built from.
    # They carry the multiplies and divisions that used to be single-cycle
    # expressions, and without them yosys never finished this module: an 8-hour
    # synthesis timed out in 1_2_yosys on the unrolled form.
    "rtl/lib/ot_wide_mul_seq.sv",
    "rtl/lib/ot_wide_div_small_seq.sv",
    "rtl/lib/ot_wide_div_seq.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/test/tb_a3_hc_transcendental.sv",
)
ORACLE_SOURCES = (
    "tools/build_a3_hc_transcendental_vectors.py",
    "tools/run_a3_hc_transcendental_rtl_campaign.py",
    "runtime/reference/hyper_connection.py",
)
VECTOR_FILES = ("cases.hex", "index.json")

SUMMARY_RE = re.compile(r"^TRANS_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(r"^PASS a3_hc_transcendental checks=(?P<checks>\d+)$")
KV_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def scrub(value: str, temporary_root: Path | None = None) -> str:
    if temporary_root is not None:
        value = value.replace(str(temporary_root), "<TMP>")
    return value.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def run(
    command: list[str], *, timeout: int, cwd: Path = ROOT
) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"command timed out after {timeout}s: {scrub(' '.join(command))}"
        ) from exc
    return process, time.monotonic() - started


def tool_identity(
    executable: Path,
    arguments: list[str],
    pattern: re.Pattern[str],
    expected: tuple[int, int] | None,
    label: str,
) -> dict[str, str]:
    process, _ = run([str(executable), *arguments], timeout=30)
    output = (process.stdout + process.stderr).strip()
    if process.returncode:
        raise RuntimeError(f"{label} version probe failed: {output}")
    match = pattern.search(output)
    if match is None:
        raise RuntimeError(f"cannot parse {label} version: {output!r}")
    observed = (int(match.group("major")), int(match.group("minor")))
    if expected is not None and observed != expected:
        raise RuntimeError(f"{label} version {observed} is not pinned {expected}")
    return {
        "path": scrub(str(executable.resolve())),
        "sha256": sha256(executable.resolve()),
        "version": output.splitlines()[0],
    }


def resolve_tools() -> tuple[Path, Path, Path, Path]:
    iverilog_name = shutil.which("iverilog")
    vvp_name = shutil.which("vvp")
    if not iverilog_name or not vvp_name:
        raise RuntimeError("Icarus Verilog and vvp are required")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    yosys = TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys"
    if not verilator.is_file():
        raise RuntimeError(f"pinned Verilator is missing: {verilator}")
    if not yosys.is_file():
        raise RuntimeError(f"pinned Yosys is missing: {yosys}")
    return Path(iverilog_name), Path(vvp_name), verilator, yosys


def parse_log(log: str) -> tuple[dict[str, int], int]:
    summary: dict[str, int] | None = None
    checks: int | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = SUMMARY_RE.match(line)
        if match:
            summary = {
                item.group("key"): int(item.group("value"))
                for item in KV_RE.finditer(match.group("body"))
            }
        passed = PASS_RE.match(line)
        if passed:
            checks = int(passed.group("checks"))
    if summary is None or checks is None:
        raise RuntimeError("simulator log lacks the exact summary/PASS markers")
    return summary, checks


def load_cases(path: Path = VECTOR_DIR / "cases.hex") -> list[tuple[int, int, int, int]]:
    words = [int(line, 16) for line in path.read_text().splitlines() if line]
    if len(words) % 4:
        raise RuntimeError("transcendental vector image is not four-word aligned")
    return [tuple(words[index : index + 4]) for index in range(0, len(words), 4)]


def iterative_cycles(operation: int, argument: int, error: int) -> int:
    magnitude = argument & 0x7FFFFFFF
    sign = bool(argument & 0x80000000)
    if error or magnitude == 0:
        return 0
    if operation == 0 and magnitude >= 0x43160000:
        return 0
    if operation == 1 and ((not sign and magnitude >= 0x41C80000) or (sign and magnitude >= 0x43160000)):
        return 0
    return 67 if operation else 66


def expected_summary(manifest: dict[str, Any]) -> tuple[dict[str, int], int]:
    cases = load_cases()
    if len(cases) != manifest["case_count"]:
        raise RuntimeError("vector manifest case count does not match image")
    stalls = sum(
        3 if index % 17 == 0 else 1 if index % 5 == 0 else 0
        for index in range(len(cases))
    )
    cycles = [iterative_cycles(op, arg, error) for op, arg, _, error in cases]
    summary = {
        "cases": len(cases),
        "exp": manifest["counts"]["exp"],
        "sigmoid": manifest["counts"]["sigmoid"],
        "accepted": manifest["counts"]["accepted"],
        "refused": manifest["counts"]["refused"],
        "stalls": stalls,
        "max_cycles": max(cycles),
        "reset_cycles": 23,
    }
    # Active-reset contributes 23 * 2 busy/no-result checks, three reset-value
    # checks and one ready check.  Each regular case contributes five fixed
    # protocol/result checks, one busy check per active cycle, and three checks
    # per output-stall cycle.
    checks = 50 + sum(5 + cycle for cycle in cycles) + 3 * stalls
    return summary, checks


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_hc_transcendental_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=120,
    )
    if process.returncode:
        raise RuntimeError(
            f"vector generation failed:\n{process.stdout}\n{process.stderr}"
        )
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")
    return json.loads((generated / "index.json").read_text())


def validate_observed(
    summary: dict[str, int], checks: int, manifest: dict[str, Any]
) -> None:
    wanted_summary, wanted_checks = expected_summary(manifest)
    if summary != wanted_summary:
        raise RuntimeError(f"simulator summary {summary} != expected {wanted_summary}")
    if checks != wanted_checks:
        raise RuntimeError(f"simulator checks {checks} != expected {wanted_checks}")


def campaign(output: Path) -> dict[str, Any]:
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(
            iverilog, ["-V"], IVERILOG_RE, None, "Icarus Verilog"
        ),
        "vvp": {"path": scrub(str(vvp.resolve())), "sha256": sha256(vvp.resolve())},
        "verilator": tool_identity(
            verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"
        ),
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }

    with tempfile.TemporaryDirectory(prefix="a3-hc-transcendental-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        iverilog_output = temporary / "tb.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_hc_transcendental",
                "-o",
                str(iverilog_output),
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=120,
        )
        if process.returncode:
            raise RuntimeError(
                f"Icarus compile failed:\n{process.stdout}\n{process.stderr}"
            )
        process, iverilog_run_seconds = run(
            [str(vvp), str(iverilog_output), f"+CASES={VECTOR_DIR / 'cases.hex'}"],
            # A request is some 2,850 cycles rather than seventy now that the wide
            # arithmetic is sequential, so 4,200 of them is tens of millions of
            # cycles under an event-driven simulator.
            timeout=36000,
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_summary, iverilog_checks = parse_log(iverilog_log)
        validate_observed(iverilog_summary, iverilog_checks, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator),
                "--binary",
                "--timing",
                "--top-module",
                "tb_a3_hc_transcendental",
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim_a3_hc_transcendental",
                "-Wno-fatal",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                "-Wno-PROCASSINIT",
                "-Wno-UNUSEDSIGNAL",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=180,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(
                f"Verilator compile failed:\n{verilator_compile_log}"
            )
        process, verilator_run_seconds = run(
            [
                str(verilator_dir / "sim_a3_hc_transcendental"),
                f"+CASES={VECTOR_DIR / 'cases.hex'}",
            ],
            # See the Icarus run above: a request is some 2,850 cycles now.
            timeout=7200,
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_summary, verilator_checks = parse_log(verilator_log)
        validate_observed(verilator_summary, verilator_checks, manifest)
        if (iverilog_summary, iverilog_checks) != (
            verilator_summary,
            verilator_checks,
        ):
            raise RuntimeError("Icarus and Verilator normalized results differ")

        # Every design source, not just the first: the engine instantiates three
        # sequential primitives now, and ``hierarchy -check`` fails on a missing
        # module rather than silently blackboxing it.
        design_sources = [
            item for item in RTL_SOURCES if not item.startswith("rtl/test/")
        ]
        yosys_script = (
            "".join(f"read_verilog -sv {ROOT / item}; " for item in design_sources)
            + "hierarchy -check -top ot_a3_fp32_transcendental_cr_rne; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=120
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration/check failed:\n{yosys_log}")

        source_paths = [ROOT / item for item in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_hc_transcendental_campaign.v1",
            "status": "pass",
            "scope": {
                "certifying_fixed_point_interval": True,
                "correctly_rounded_nonpositive_exp_tested": True,
                "correctly_rounded_direct_sigmoid_tested": True,
                "independent_exact_rational_oracle": True,
                "host_floating_point_oracle": False,
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "input_or_output_indexed_lookup_table": False,
                "complete_binary32_exhaustion": False,
                "checkpoint_reachable_domain_complete": False,
                "technology_mapping_or_timing": False,
                "full_hc_pre": False,
                "pc14_integration": False,
                "model_token_generation": False,
                "eos": False,
                "architectural_timing": False,
                "tpot": False,
            },
            "counts": manifest["counts"],
            "checks": iverilog_checks,
            "normalized_summary": iverilog_summary,
            "simulators_agree": True,
            "synthesis_frontend": {
                "top": "ot_a3_fp32_transcendental_cr_rne",
                "check_problems": 0,
                "note": "generic RTLIL elaboration only; no library mapping, PPA, frequency, latency, or TPOT claim",
            },
            "verification_wall_seconds": {
                "iverilog_compile": iverilog_compile_seconds,
                "iverilog_simulation": iverilog_run_seconds,
                "verilator_compile": verilator_compile_seconds,
                "verilator_simulation": verilator_run_seconds,
                "yosys_elaboration": yosys_seconds,
            },
            "tools": tools,
            "source_sha256": {
                str(path.relative_to(ROOT)): sha256(path) for path in source_paths
            },
            "vector_sha256": {
                filename: sha256(VECTOR_DIR / filename) for filename in VECTOR_FILES
            },
            "log_sha256": {
                "iverilog": hashlib.sha256(iverilog_log.encode()).hexdigest(),
                "verilator_compile": hashlib.sha256(
                    verilator_compile_log.encode()
                ).hexdigest(),
                "verilator": hashlib.sha256(verilator_log.encode()).hexdigest(),
                "yosys": hashlib.sha256(yosys_log.encode()).hexdigest(),
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
        problems.append("retained campaign lacks simulator agreement")
    scope = result.get("scope", {})
    for forbidden in (
        "checkpoint_reachable_domain_complete",
        "full_hc_pre",
        "pc14_integration",
        "model_token_generation",
        "eos",
        "architectural_timing",
        "tpot",
    ):
        if scope.get(forbidden) is not False:
            problems.append(f"retained campaign overclaims {forbidden}")
    for name, expected in result.get("source_sha256", {}).items():
        current = ROOT / name
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"source hash is stale: {name}")
    for name, expected in result.get("vector_sha256", {}).items():
        current = VECTOR_DIR / name
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"vector hash is stale: {name}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        problems = validate_retained(args.output.resolve())
        if problems:
            raise SystemExit("\n".join(problems))
        print(f"PASS retained HC transcendental campaign: {args.output.resolve()}")
        return
    result = campaign(args.output.resolve())
    print(
        "PASS HC transcendental RTL campaign: "
        f"{result['counts']['exp']} exp, {result['counts']['sigmoid']} sigmoid, "
        f"{result['checks']} checks, two simulators agree"
    )


if __name__ == "__main__":
    main()
