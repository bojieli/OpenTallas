#!/usr/bin/env python3
"""Run dual-simulator exact Qwen ABI 3.0 KV-scatter RTL evidence.

Simulator cycles in this campaign are verification cost only.  They are not
architectural token-commit ticks and cannot qualify TPOT because GQA and every
later model operation remain outside the executed RTL path.
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_qwen_kv_scatter"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_qwen_kv_scatter_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_descriptor_record_validator.sv",
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    "rtl/abi3/ot_a3_qwen_kv_scatter_adapter.sv",
    "rtl/test/tb_a3_qwen_kv_scatter.sv",
)
SYNTH_SOURCES = RTL_SOURCES[:-1]
ORACLE_SOURCES = (
    "tools/build_a3_qwen_kv_scatter_vectors.py",
    "tools/run_a3_qwen_kv_scatter_rtl_campaign.py",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json",
    "testdata/compiler/abi3_shipped_prefix/p3_expect.hex",
    "testdata/compiler/abi3_shipped_prefix/p3_writes.hex",
    "results/rtl/abi3_shipped_prefix_campaign.json",
)
VECTOR_FILES = (
    "cases.hex",
    "instruction.hex",
    "operator.hex",
    "view0.hex",
    "view1.hex",
    "view2.hex",
    "view3.hex",
    "output.hex",
    "numeric.hex",
    "source.hex",
    "index.json",
)

CASE_RE = re.compile(r"^CASE_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(
    r"^PASS a3_qwen_kv_scatter cases=(?P<cases>\d+) "
    r"scatters=(?P<scatters>\d+) next_pc=(?P<next_pc>\d+) "
    r"checks=(?P<checks>\d+)$"
)
KV_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
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
    resolved = executable.resolve()
    return {
        "path": scrub(str(resolved)),
        "sha256": sha256(resolved),
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


def plusargs(vector_root: Path) -> list[str]:
    return [
        f"+CASES={vector_root / 'cases.hex'}",
        f"+INSTRUCTION={vector_root / 'instruction.hex'}",
        f"+OPERATOR={vector_root / 'operator.hex'}",
        f"+VIEW0={vector_root / 'view0.hex'}",
        f"+VIEW1={vector_root / 'view1.hex'}",
        f"+VIEW2={vector_root / 'view2.hex'}",
        f"+VIEW3={vector_root / 'view3.hex'}",
        f"+OUTPUT={vector_root / 'output.hex'}",
        f"+NUMERIC={vector_root / 'numeric.hex'}",
        f"+SOURCE={vector_root / 'source.hex'}",
    ]


def parse_log(log: str) -> tuple[list[dict[str, int]], dict[str, int]]:
    cases: list[dict[str, int]] = []
    passed: dict[str, int] | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = CASE_RE.match(line)
        if match:
            cases.append(
                {
                    item.group("key"): int(item.group("value"))
                    for item in KV_RE.finditer(match.group("body"))
                }
            )
        match = PASS_RE.match(line)
        if match:
            passed = {key: int(value) for key, value in match.groupdict().items()}
    if passed is None:
        raise RuntimeError("simulator did not emit the exact PASS marker")
    return cases, passed


def expected_observation(manifest: dict[str, Any]) -> list[dict[str, int]]:
    result = []
    for index, case in enumerate(manifest["cases"]):
        expected = case["expected"]
        result.append(
            {
                "index": index,
                "failed": int(expected["failed"]),
                "trap": int(expected["trap_class"]),
                "refusal": int(expected["refusal_reason"]),
                "records": int(expected["records_checked"]),
                "moved": int(expected["moved_elements"]),
                "checked": int(expected["indices_checked"]),
                "writes": int(expected["write_count"]),
                "gqa": int(expected["gqa_boundary"]),
            }
        )
    return result


def validate_observed(
    observed: list[dict[str, int]], passed: dict[str, int], manifest: dict[str, Any]
) -> None:
    expected = expected_observation(manifest)
    normalized = [
        {key: value for key, value in case.items() if key != "verification_cycles"}
        for case in observed
    ]
    if normalized != expected:
        raise RuntimeError("simulator case summaries differ from vector manifest")
    if passed != {
        "cases": len(expected),
        "scatters": 4,
        "next_pc": 38,
        "checks": 209_076,
    }:
        raise RuntimeError(f"simulator PASS summary differs: {passed}")


def regenerate_and_compare(temporary_root: Path) -> dict[str, Any]:
    generated = temporary_root / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_qwen_kv_scatter_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=60,
    )
    if process.returncode:
        raise RuntimeError(
            f"vector generation failed:\n{process.stdout}\n{process.stderr}"
        )
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")
    return json.loads((generated / "index.json").read_text())


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

    with tempfile.TemporaryDirectory(prefix="a3-qwen-kv-scatter-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        iverilog_output = temporary / "tb_a3_qwen_kv_scatter.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_qwen_kv_scatter",
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
            [str(vvp), str(iverilog_output), *plusargs(VECTOR_DIR)], timeout=120
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_cases, iverilog_pass = parse_log(iverilog_log)
        validate_observed(iverilog_cases, iverilog_pass, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator),
                "--binary",
                "--timing",
                "--top-module",
                "tb_a3_qwen_kv_scatter",
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim_a3_qwen_kv_scatter",
                "-Wno-fatal",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=180,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{verilator_compile_log}")
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim_a3_qwen_kv_scatter"), *plusargs(VECTOR_DIR)],
            timeout=120,
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_cases, verilator_pass = parse_log(verilator_log)
        validate_observed(verilator_cases, verilator_pass, manifest)
        if iverilog_cases != verilator_cases or iverilog_pass != verilator_pass:
            raise RuntimeError("Icarus and Verilator normalized results differ")

        # Pinned Yosys 0.68 does not parse package imports in the already
        # qualified instruction decoder.  The adapter and its descriptor/DMA
        # datapaths are checked with a tiny synthesis-only decoder interface;
        # Icarus and Verilator above execute the real decoder and CRC logic.
        decoder_stub = temporary / "ot_a3_instruction_decoder_stub.sv"
        decoder_stub.write_text(
            """module ot_a3_instruction_decoder(
input clk,input rst_n,input in_valid,output in_ready,input [255:0] in_record,
input [31:0] in_index,input [31:0] in_instruction_count,output out_valid,
input out_ready,output out_legal,output [3:0] out_error,
output [15:0] out_trap_class,output [31:0] out_index,
output [7:0] out_major,output [7:0] out_sub,output [15:0] out_flags,
output [31:0] out_predicate_id,output [31:0] out_descriptor_id,
output [31:0] out_wait_set_id,output [31:0] out_signal_event_id,
output [31:0] out_control_id,output [31:0] out_source_operation_id);
assign in_ready=1'b0; assign out_valid=1'b0; assign out_legal=1'b0;
assign out_error=4'd0; assign out_trap_class=16'd0; assign out_index=32'd0;
assign out_major=8'd0; assign out_sub=8'd0; assign out_flags=16'd0;
assign out_predicate_id=32'd0; assign out_descriptor_id=32'd0;
assign out_wait_set_id=32'd0; assign out_signal_event_id=32'd0;
assign out_control_id=32'd0; assign out_source_operation_id=32'd0;
endmodule
""",
            encoding="ascii",
        )
        synthesis_paths = [
            ROOT / "rtl/abi3/ot_a3_pkg.sv",
            ROOT / "rtl/abi3/ot_a3_engine_pkg.sv",
            decoder_stub,
            ROOT / "rtl/abi3/ot_a3_descriptor_record_validator.sv",
            ROOT / "rtl/abi3/ot_a3_dma_index_mover.sv",
            ROOT / "rtl/abi3/ot_a3_qwen_kv_scatter_adapter.sv",
        ]
        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(path) for path in synthesis_paths)
            + "; hierarchy -check -top ot_a3_qwen_kv_scatter_adapter; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=180
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration/check failed:\n{yosys_log}")

        scatter_cases = [
            case for case in manifest["cases"] if case["expected"]["compare_output"]
        ]
        negative_cases = [
            case
            for case in manifest["cases"]
            if case["expected"]["failed"]
            and not case["expected"]["gqa_boundary"]
        ]
        source_paths = [ROOT / item for item in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_qwen_kv_scatter_campaign.v1",
            "status": "pass",
            "abi": {"major": 3, "minor": 0},
            "scope": {
                "exact_rom_pc32_pc35_scatter": True,
                "exact_hbm_pc32_pc35_scatter": True,
                "exact_instruction_crc_admission": True,
                "exact_descriptor_crc_and_semantic_admission": True,
                "upstream_key_is_pc29_rope_result": True,
                "upstream_value_is_pc17_projection_result": True,
                "all_active_span_words_compared": True,
                "prior_rows_preserved": True,
                "position_16_replaced": True,
                "exact_pc38_gqa_metadata_admitted": True,
                "pc38_gqa_returns_capability_before_write": True,
                "fail_closed_no_partial_write": True,
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "authentic_prior_context_kv": False,
                "gqa_arithmetic": False,
                "complete_layer": False,
                "model_token_generation": False,
                "independent_oracle_token_match": False,
                "eos_and_no_post_eos": False,
                "architectural_token_commit_ticks": False,
                "tpot": False,
                "simulator_cycles_are_verification_cost_only": True,
            },
            "boundary": {
                "previous_first_unsupported_pc": 32,
                "new_first_unsupported_pc": 38,
                "new_first_unsupported_opcode": "ATTENTION.GQA",
                "rom_operator_descriptor_id": 127,
                "hbm_operator_descriptor_id": 131,
            },
            "aggregate": {
                "case_count": len(manifest["cases"]),
                "scatter_case_count": len(scatter_cases),
                "gqa_boundary_case_count": manifest["gqa_boundary_case_count"],
                "negative_case_count": len(negative_cases),
                "records_checked": sum(
                    int(case["expected"]["records_checked"])
                    for case in manifest["cases"]
                ),
                "moved_elements": sum(
                    int(case["expected"]["moved_elements"])
                    for case in scatter_cases
                ),
                "indices_checked": sum(
                    int(case["expected"]["indices_checked"])
                    for case in manifest["cases"]
                ),
                "destination_words_compared": len(scatter_cases) * 17 * 1024,
                "preserved_words_compared": len(scatter_cases) * 16 * 1024,
                "replaced_words_compared": len(scatter_cases) * 1024,
                "rtl_write_beats": sum(
                    int(case["expected"]["write_count"])
                    for case in scatter_cases
                ),
                "checks_per_simulator": 209_076,
            },
            "source_binding": manifest["source_binding"],
            "plane_binding": manifest["plane_binding"],
            "upstream_dependency": manifest["upstream_dependency"],
            "normalized_cases": [
                {
                    **{
                        key: value
                        for key, value in case.items()
                        if key != "verification_cycles"
                    },
                    "verification_cycles": case["verification_cycles"],
                }
                for case in iverilog_cases
            ],
            "simulators_agree": True,
            "verification_wall_seconds": {
                "iverilog_compile": iverilog_compile_seconds,
                "iverilog_simulation": iverilog_run_seconds,
                "verilator_compile": verilator_compile_seconds,
                "verilator_simulation": verilator_run_seconds,
                "yosys_elaboration": yosys_seconds,
            },
            "synthesis_frontend": {
                "top": "ot_a3_qwen_kv_scatter_adapter",
                "check_problems": 0,
                "instruction_decoder_interface_stubbed": True,
                "note": (
                    "generic RTLIL elaboration of the adapter, descriptor CRC, "
                    "and DMA mover with the instruction-decoder interface "
                    "stubbed because pinned Yosys cannot parse that qualified "
                    "module's package import; both RTL simulators execute the "
                    "real decoder. No library mapping, PPA, token latency, "
                    "output-token correctness, or TPOT claim"
                ),
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
    if not path.is_file():
        return [f"missing retained campaign: {path}"]
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read retained campaign: {exc}"]
    if value.get("schema") != "opentallas.rtl.a3_qwen_kv_scatter_campaign.v1":
        problems.append("campaign schema differs")
    if value.get("status") != "pass":
        problems.append("campaign status is not pass")
    if not value.get("simulators_agree"):
        problems.append("simulators do not agree")
    if value.get("boundary", {}).get("new_first_unsupported_pc") != 38:
        problems.append("next unsupported PC is not 38")
    aggregate = value.get("aggregate", {})
    if aggregate.get("checks_per_simulator") != 209_076:
        problems.append("campaign check count differs")
    for source, expected in value.get("source_sha256", {}).items():
        candidate = ROOT / source
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"source changed: {source}")
    for filename, expected in value.get("vector_sha256", {}).items():
        candidate = VECTOR_DIR / filename
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"vector changed: {filename}")
    return problems


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument("--validate-retained", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.validate_retained:
        problems = validate_retained(args.output)
        if problems:
            for problem in problems:
                print(f"FAIL: {problem}")
            return 1
        print("PASS: retained ABI3 Qwen KV-scatter campaign is source-current")
        return 0
    result = campaign(args.output)
    print(
        "PASS: ABI3 Qwen KV-scatter RTL "
        f"checks={result['aggregate']['checks_per_simulator']} next_pc=38"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
