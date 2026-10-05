#!/usr/bin/env python3
"""Run source-bound Icarus and Verilator lane-mapper qualification."""

from __future__ import annotations

import argparse
import hashlib
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

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)

from tools import build_abi3_tensor_lane_mapper_vectors as builder  # noqa: E402


SCHEMA = "opentallas.abi3.tensor_lane_mapper_campaign.v1"
PINNED_VERILATOR_VERSION = "5.050"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)
DEFAULT_VECTORS = ROOT / "testdata/rtl/abi3_tensor_lane_mapper_vectors.json"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_tensor_lane_mapper_campaign.json"
RTL_SOURCES = (
    ROOT / "rtl/abi3/ot_a3_engine_pkg.sv",
    ROOT / "rtl/abi3/ot_a3_tensor_lane_mapper.sv",
    ROOT / "rtl/test/tb_a3_tensor_lane_mapper.sv",
)
CAMPAIGN_SOURCES = (
    ROOT / "tools/build_abi3_tensor_lane_mapper_vectors.py",
    ROOT / "tools/run_abi3_tensor_lane_mapper_campaign.py",
)
OBSERVATION_RE = re.compile(
    r"PASS: ABI3 tensor lane mapper cases=(?P<cases>[0-9]+) "
    r"waves=(?P<waves>[0-9]+) "
    r"logical_outputs=(?P<logical_outputs>[0-9]+) "
    r"checks=(?P<checks>[0-9]+)"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _body_id(value: dict[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _version(command: list[str]) -> str:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0 or not output:
        raise RuntimeError(f"cannot identify tool: {command[0]}")
    return output.splitlines()[0]


def _resolve_tools() -> tuple[Path, Path, Path]:
    iverilog = Path(shutil.which("iverilog") or "")
    vvp = Path(shutil.which("vvp") or "")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    if not iverilog.is_file() or not vvp.is_file():
        raise RuntimeError("Icarus iverilog/vvp are unavailable")
    if not verilator.is_file():
        raise RuntimeError(f"pinned Verilator is unavailable: {verilator}")
    return iverilog, vvp, verilator


def _validate_vectors(vectors: dict[str, Any]) -> None:
    if vectors.get("schema") != builder.SCHEMA:
        raise ValueError("lane-mapper vector schema differs")
    if vectors.get("vector_set_id") != _body_id(vectors, "vector_set_id"):
        raise ValueError("lane-mapper vector identity differs")
    sources = vectors.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("lane-mapper vectors have no source bindings")
    for name, source in sources.items():
        path = Path(source["path"])
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file() or _sha256_file(path) != source["sha256"]:
            raise ValueError(f"lane-mapper source binding differs: {name}")


def _write_memories(vectors: dict[str, Any], build: Path) -> dict[str, Any]:
    case_words: list[int] = []
    wave_words: list[int] = []
    masks: list[int] = []
    wave_start = 0
    for case_index, case in enumerate(vectors["cases"]):
        config = case["config"]
        expected = case["expected"]
        waves = expected["waves"]
        case_words.extend(
            (
                config["rows"],
                config["cols"],
                config["tile_rows"],
                config["tile_cols"],
                config["issue_window"],
                expected["error_code"],
                wave_start,
                expected["wave_count"],
                expected["logical_output_count"],
                expected["active_lane_slots"],
                expected["masked_lane_slots"],
                expected["row_folded_output_count"],
            )
        )
        for wave in waves:
            packed_groups = sum(
                count << (group * 7)
                for group, count in enumerate(wave["group_active_counts"])
            )
            wave_words.extend(
                (
                    case_index,
                    wave["row_base"],
                    wave["col_base"],
                    wave["rows"],
                    wave["cols_per_row"],
                    wave["active_lanes"],
                    packed_groups,
                    int(wave["last"]),
                )
            )
            masks.append(int(wave["lane_valid_hex"], 16))
        wave_start += len(waves)

    if wave_start != vectors["coverage"]["wave_count"]:
        raise ValueError("flattened wave count differs from vector coverage")
    case_path = build / "lane_mapper_cases.hex"
    wave_path = build / "lane_mapper_waves.hex"
    mask_path = build / "lane_mapper_masks.hex"
    case_path.write_text(
        "".join(f"{value:016x}\n" for value in case_words), encoding="ascii"
    )
    wave_path.write_text(
        "".join(f"{value:016x}\n" for value in wave_words), encoding="ascii"
    )
    mask_path.write_text(
        "".join(f"{value:064x}\n" for value in masks), encoding="ascii"
    )
    return {
        "case_count": len(vectors["cases"]),
        "case_path": case_path,
        "mask_path": mask_path,
        "wave_count": wave_start,
        "wave_path": wave_path,
    }


def _normalize(text: str, build: Path) -> str:
    return text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>")


def _execute(
    *,
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    compiled = subprocess.run(
        compile_command,
        cwd=build,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    compile_log = _normalize(compiled.stdout + compiled.stderr, build)
    run_returncode: int | None = None
    run_log = ""
    if compiled.returncode == 0:
        executed = subprocess.run(
            run_command,
            cwd=build,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        run_returncode = executed.returncode
        run_log = _normalize(executed.stdout + executed.stderr, build)
    match = OBSERVATION_RE.search(run_log)
    observation = (
        {key: int(value) for key, value in match.groupdict().items()} if match else None
    )
    retained_log = compile_log + run_log
    passed = (
        compiled.returncode == 0 and run_returncode == 0 and observation is not None
    )
    return {
        "command": _normalize(
            f"{shlex.join(compile_command)} && {shlex.join(run_command)}", build
        ),
        "compile_log": compile_log,
        "compile_returncode": compiled.returncode,
        "host_verification_seconds": round(time.monotonic() - started, 6),
        "log_sha256": _sha256(retained_log.encode("utf-8")),
        "name": name,
        "observation": observation,
        "run_log": run_log,
        "run_returncode": run_returncode,
        "status": "pass" if passed else "fail",
    }


def run(vectors_path: Path) -> dict[str, Any]:
    vectors_path = vectors_path.resolve()
    vectors = load_strict_json(vectors_path)
    _validate_vectors(vectors)
    iverilog, vvp, verilator = _resolve_tools()

    with tempfile.TemporaryDirectory(prefix="opentallas-lane-mapper-") as raw:
        build = Path(raw)
        memories = _write_memories(vectors, build)
        plusargs = [
            f"+case_path={memories['case_path']}",
            f"+wave_path={memories['wave_path']}",
            f"+mask_path={memories['mask_path']}",
            f"+case_count={memories['case_count']}",
            f"+wave_count={memories['wave_count']}",
        ]
        iverilog_binary = build / "lane_mapper.vvp"
        iverilog_compile = [
            str(iverilog),
            "-g2012",
            "-s",
            "tb_a3_tensor_lane_mapper",
            "-o",
            str(iverilog_binary),
            *(str(path) for path in RTL_SOURCES),
        ]
        verilator_dir = build / "verilator"
        verilator_compile = [
            str(verilator),
            "--binary",
            "--timing",
            "-j",
            "2",
            "-Wall",
            "-Wno-fatal",
            "--top-module",
            "tb_a3_tensor_lane_mapper",
            "--Mdir",
            str(verilator_dir),
            *(str(path) for path in RTL_SOURCES),
        ]
        cases = [
            _execute(
                name="iverilog",
                compile_command=iverilog_compile,
                run_command=[str(vvp), str(iverilog_binary), *plusargs],
                build=build,
            ),
            _execute(
                name="verilator",
                compile_command=verilator_compile,
                run_command=[
                    str(verilator_dir / "Vtb_a3_tensor_lane_mapper"),
                    *plusargs,
                ],
                build=build,
            ),
        ]

    expected_observation = {
        "cases": vectors["coverage"]["case_count"],
        "logical_outputs": vectors["coverage"]["logical_output_count"],
        "waves": vectors["coverage"]["wave_count"],
    }
    observations = [case["observation"] for case in cases]
    observations_match = (
        all(case["status"] == "pass" for case in cases)
        and all(observation is not None for observation in observations)
        and len({canonical_json_bytes(item) for item in observations}) == 1
        and all(
            observation[key] == value
            for observation in observations
            for key, value in expected_observation.items()
        )
    )
    sources = {
        str(path.relative_to(ROOT)): _sha256_file(path)
        for path in (*RTL_SOURCES, *CAMPAIGN_SOURCES)
    }
    value: dict[str, Any] = {
        "campaign_id": "",
        "claim_boundary": {
            "complete_model_token_generated": False,
            "host_verification_time_is_target_tpot": False,
            "integrated_tensor_datapath": False,
            "standalone_lane_control_rtl": True,
            "target_tpot": False,
        },
        "coverage": vectors["coverage"],
        "observations_identical": observations_match,
        "schema": SCHEMA,
        "simulators": cases,
        "sources": sources,
        "status": "pass" if observations_match else "fail",
        "tools": {
            "iverilog": _version([str(iverilog), "-V"]),
            "verilator": _version([str(verilator), "--version"]),
            "vvp": _version([str(vvp), "-V"]),
        },
        "vector_file_sha256": _sha256_file(vectors_path),
        "vector_set_id": vectors["vector_set_id"],
    }
    value["campaign_id"] = _body_id(value, "campaign_id")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--vectors", type=Path, default=DEFAULT_VECTORS)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return result


def main() -> int:
    args = parser().parse_args()
    value = run(args.vectors)
    write_canonical_json(args.output, value)
    print(
        f"wrote {args.output}: status={value['status']} "
        f"campaign_id={value['campaign_id']}"
    )
    return 0 if value["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
