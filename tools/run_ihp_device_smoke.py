#!/usr/bin/env python3
"""Compile and smoke-test the official IHP SG13G2 ngspice devices.

This closes only the governed device/toolchain gate.  Generated OSDI modules
are always written outside the immutable PDK checkout, compiled twice, and
required to be byte-identical before the official 1.2-V CMOS wrappers are run.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "spice" / "ihp_sg13g2" / "device_smoke" / "device_smoke_contract.json"
)
PDK_VERIFIER = ROOT / "tools" / "verify_ihp_pdk.py"


class SmokeError(RuntimeError):
    """A governed input, identity, compilation, or electrical gate failed."""


def strict_json(path: Path) -> Any:
    duplicates: list[str] = []

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise SmokeError(f"duplicate JSON keys in {path}: {sorted(set(duplicates))}")
    return parsed


def repository_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise SmokeError(f"repository path must be relative and contained: {value}")
    resolved = (ROOT / relative).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SmokeError(f"repository path escapes the repository: {value}") from exc
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_contract(contract: dict[str, Any], lock: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise SmokeError("device-smoke contract schema_version must be 1")
    if contract.get("experiment_id") != "ihp_sg13g2_official_device_smoke_v1":
        raise SmokeError("unexpected device-smoke experiment_id")
    if lock.get("schema_version") != 1:
        raise SmokeError("IHP PDK lock schema_version must be 1")
    if lock.get("pdk", {}).get("variant") != "ihp-sg13g2":
        raise SmokeError("device smoke requires the locked IHP SG13G2 release")
    if repository_path(contract["pdk_lock"]) != repository_path(
        "configs/pdk/ihp_sg13g2_physical_lock.json"
    ):
        raise SmokeError("device smoke must use the governed IHP PDK lock")

    if set(contract.get("inputs", {})) != {"spice_init", "deck"}:
        raise SmokeError("device smoke must declare its init file and deck")
    for value in contract["inputs"].values():
        if not repository_path(value).is_file():
            raise SmokeError(f"missing governed device-smoke input: {value}")

    compile_contract = contract.get("model_compile", {})
    expected_models = list(lock.get("osdi_models", {}).get("models", {}))
    if compile_contract.get("models") != expected_models:
        raise SmokeError("contract model order must exactly match the PDK lock")
    if (
        compile_contract.get("define") != "__NGSPICE__"
        or compile_contract.get("target_cpu") != "generic"
        or compile_contract.get("replays") != 2
        or compile_contract.get("require_byte_identical_replay") is not True
        or compile_contract.get("require_output_outside_pdk") is not True
    ):
        raise SmokeError("portable two-pass OSDI compilation is mandatory")

    acceptance = contract.get("acceptance", {})
    metric_names = {
        "dc_out_low_v",
        "dc_out_high_v",
        "tran_out_low_v",
        "tran_out_high_v",
        "tphl_s",
        "tplh_s",
    }
    for name in metric_names:
        bounds = acceptance.get(name)
        if not isinstance(bounds, dict) or "max" not in bounds:
            raise SmokeError(f"missing finite acceptance bounds for {name}")
        for value in bounds.values():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise SmokeError(f"non-finite acceptance bound for {name}")
    if acceptance.get("unexpected_errors_max") != 0:
        raise SmokeError("device smoke must reject all unexpected errors")

    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class") != "public_pdk_official_device_model_smoke"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise SmokeError("device-smoke claim boundary is incomplete")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for marker in ("ROM topology", "N7 or N4", "GPU speedup", "silicon"):
        if marker not in forbidden:
            raise SmokeError(f"claim boundary does not cover {marker}")

    reports = contract.get("reports", {})
    if set(reports) != {"artifacts", "json", "markdown"}:
        raise SmokeError("device-smoke report destinations are incomplete")
    for value in reports.values():
        repository_path(value)


def first_existing(candidates: list[Path], description: str) -> Path:
    checked: list[str] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        checked.append(str(resolved))
        if resolved.exists():
            return resolved
    raise SmokeError(f"cannot find {description}; checked {checked}")


def locate_pdk(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    override = os.environ.get("OPENTALLAS_IHP_PDK_ROOT")
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            ROOT / ".cache" / "ihp-open-pdk-v0.3.0",
            Path.home() / ".local" / "opentallas-pdk" / "ihp-open-pdk-v0.3.0",
        ]
    )
    pdk = first_existing(candidates, "pinned IHP Open PDK v0.3.0 checkout")
    required = [
        pdk / "ihp-sg13g2" / "libs.tech" / "ngspice" / "models" / "cornerMOSlv.lib",
        pdk / "ihp-sg13g2" / "libs.tech" / "magic" / "ihp-sg13g2.magicrc",
        pdk / "ihp-sg13g2" / "libs.tech" / "netgen" / "ihp-sg13g2_setup.tcl",
    ]
    if not all(path.is_file() for path in required):
        raise SmokeError(f"incomplete IHP SG13G2 checkout under {pdk}")
    return pdk


def locate_tool(explicit: Path | None, environment: str, default: Path, name: str) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    override = os.environ.get(environment)
    if override:
        candidates.append(Path(override))
    candidates.append(default)
    tool = first_existing(candidates, name)
    if not tool.is_file() or not os.access(tool, os.X_OK):
        raise SmokeError(f"{name} is not an executable file: {tool}")
    return tool


def completed_output(
    command: list[str], *, cwd: Path | None = None, environment: dict[str, str] | None = None,
    timeout: int = 120
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise SmokeError(
            f"command failed ({completed.returncode}): {command!r}\n{completed.stdout}"
        )
    return completed.stdout


def verify_pdk(pdk: Path) -> dict[str, Any]:
    output = completed_output(["python3", str(PDK_VERIFIER), str(pdk)], timeout=180)
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        raise SmokeError(f"IHP PDK verifier emitted invalid JSON: {output}") from exc
    if parsed.get("status") != "pass":
        raise SmokeError(f"IHP PDK verifier did not pass: {parsed}")
    return parsed


def verify_tool(path: Path, expected_hash: str, expected_size: int, version_command: list[str], marker: str) -> dict[str, Any]:
    digest = sha256_file(path)
    size = path.stat().st_size
    if digest != expected_hash or size != expected_size:
        raise SmokeError(
            f"tool identity mismatch for {path}: sha256={digest}, size={size}"
        )
    version = completed_output([str(path), *version_command])
    if marker not in version:
        raise SmokeError(f"unexpected tool version for {path}: {version}")
    return {
        "path": str(path),
        "sha256": digest,
        "size_bytes": size,
        "version_output": version.strip(),
    }


def compile_models(
    pdk: Path,
    compiler: Path,
    output_root: Path,
    log_root: Path,
    lock: dict[str, Any],
    contract: dict[str, Any],
    phase: str,
) -> dict[str, Any]:
    phase_root = output_root / phase
    phase_root.mkdir(parents=True)
    records: dict[str, Any] = {}
    for name in contract["model_compile"]["models"]:
        model_lock = lock["osdi_models"]["models"][name]
        source = pdk / model_lock["source"]
        if not source.is_file() or sha256_file(source) != model_lock["source_sha256"]:
            raise SmokeError(f"official Verilog-A source identity mismatch: {source}")
        output = phase_root / f"{name}.osdi"
        command = [
            str(compiler),
            f"-D{contract['model_compile']['define']}",
            "--target_cpu",
            contract["model_compile"]["target_cpu"],
            "-o",
            str(output),
            source.name,
        ]
        log_text = completed_output(command, cwd=source.parent, timeout=180)
        log_path = log_root / f"compile_{phase}_{name}.log"
        log_path.write_text(log_text, encoding="utf-8")
        detailed_warnings = len(re.findall(r"(?m)^warning\[[^]]+\]:", log_text))
        expected_warnings = int(model_lock.get("expected_compile_warnings", 0))
        if detailed_warnings != expected_warnings:
            raise SmokeError(
                f"{name} {phase} compile warnings: expected {expected_warnings}, "
                f"observed {detailed_warnings}\n{log_text}"
            )
        digest = sha256_file(output)
        size = output.stat().st_size
        if digest != model_lock["output_sha256"] or size != model_lock["output_size_bytes"]:
            raise SmokeError(
                f"{name} {phase} OSDI identity mismatch: sha256={digest}, size={size}"
            )
        header = completed_output(["readelf", "-h", str(output)])
        if "DYN (Shared object file)" not in header or "Advanced Micro Devices X86-64" not in header:
            raise SmokeError(f"unexpected OSDI ELF target for {output}:\n{header}")
        records[name] = {
            "command": command,
            "cwd": str(source.parent),
            "source": str(source),
            "source_sha256": model_lock["source_sha256"],
            "output_sha256": digest,
            "output_size_bytes": size,
            "detailed_warnings": detailed_warnings,
            "log": log_path.name,
            "elf": "ELF64 DYN x86-64",
        }
    return records


def enforce_replay(primary_root: Path, replay_root: Path, model_names: list[str]) -> dict[str, Any]:
    per_model: dict[str, Any] = {}
    for name in model_names:
        primary = primary_root / f"{name}.osdi"
        replay = replay_root / f"{name}.osdi"
        byte_identical = primary.read_bytes() == replay.read_bytes()
        if not byte_identical:
            raise SmokeError(f"OSDI replay is not byte-identical for {name}")
        per_model[name] = {
            "byte_identical": True,
            "sha256": sha256_file(primary),
        }
    return {"status": "pass", "models": per_model}


def parse_metrics(log_text: str, contract: dict[str, Any]) -> dict[str, float]:
    names = {
        "dc_out_low": "dc_out_low_v",
        "dc_out_high": "dc_out_high_v",
        "tran_out_low": "tran_out_low_v",
        "tran_out_high": "tran_out_high_v",
        "tphl": "tphl_s",
        "tplh": "tplh_s",
    }
    metrics: dict[str, float] = {}
    for emitted, governed in names.items():
        matches = re.findall(
            rf"(?m)^\s*{re.escape(emitted)}\s*=\s*([-+0-9.eE]+)", log_text
        )
        if len(matches) != 1:
            raise SmokeError(f"expected exactly one {emitted} measure, observed {matches}")
        value = float(matches[0])
        if not math.isfinite(value):
            raise SmokeError(f"non-finite ngspice measure {emitted}: {value}")
        bounds = contract["acceptance"][governed]
        if "min" in bounds and value < bounds["min"]:
            raise SmokeError(f"{governed}={value} is below {bounds['min']}")
        if "min_exclusive" in bounds and value <= bounds["min_exclusive"]:
            raise SmokeError(f"{governed}={value} is not above {bounds['min_exclusive']}")
        if value > bounds["max"]:
            raise SmokeError(f"{governed}={value} is above {bounds['max']}")
        metrics[governed] = value
    return metrics


def simulate(
    pdk: Path,
    ngspice: Path,
    osdi_root: Path,
    work_root: Path,
    log_root: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    simulation_root = work_root / "simulation"
    simulation_root.mkdir()
    init_source = repository_path(contract["inputs"]["spice_init"])
    deck_source = repository_path(contract["inputs"]["deck"])
    shutil.copy2(init_source, simulation_root / ".spiceinit")
    deck = simulation_root / deck_source.name
    shutil.copy2(deck_source, deck)
    environment = os.environ.copy()
    environment["OPENTALLAS_IHP_PDK_ROOT"] = str(pdk)
    environment["OPENTALLAS_IHP_OSDI_ROOT"] = str(osdi_root)
    log_text = completed_output(
        [str(ngspice), "-b", deck.name],
        cwd=simulation_root,
        environment=environment,
        timeout=180,
    )
    log_path = log_root / "ngspice_device_smoke.log"
    log_path.write_text(log_text, encoding="utf-8")
    warnings = [line.strip() for line in log_text.splitlines() if line.startswith("Warning")]
    if warnings != contract["acceptance"]["expected_ngspice_warnings"]:
        raise SmokeError(f"unexpected ngspice warning set: {warnings}")
    errors = [
        line.strip()
        for line in log_text.splitlines()
        if re.match(r"^(Error|Fatal|ERROR|FATAL)(:|\s)", line.strip())
    ]
    if errors or "ngspice-43 done" not in log_text:
        raise SmokeError(f"ngspice did not close cleanly: errors={errors}\n{log_text}")
    return {
        "status": "pass",
        "metrics": parse_metrics(log_text, contract),
        "expected_warnings": warnings,
        "unexpected_errors": errors,
        "log": log_path.name,
        "analyses": ["DC transfer", "transient"],
        "official_subcircuits": contract["simulation"]["official_subcircuits"],
        "model_corner": contract["simulation"]["model_corner"],
        "supply_v": contract["simulation"]["supply_v"],
        "temperature_c": contract["simulation"]["temperature_c"],
    }


def artifact_records(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(paths):
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return records


def write_report(result: dict[str, Any], path: Path) -> None:
    metrics = result["simulation"]["metrics"]
    models = result["model_compilation"]["primary"]
    lines = [
        "# IHP SG13G2 official-device and portable-OSDI smoke campaign",
        "",
        "**Status:** PASS  ",
        "**Evidence class:** public-PDK official-device model smoke; not ROM PPA or silicon  ",
        "**PDK:** IHP Open PDK v0.3.0 / SG13G2 public preview",
        "",
        "## Portable model compilation",
        "",
        "| Model | Source SHA-256 | OSDI bytes | OSDI SHA-256 | Compile warnings | Replay |",
        "|---|---|---:|---|---:|---|",
    ]
    for name, record in models.items():
        lines.append(
            f"| `{name}` | `{record['source_sha256']}` | "
            f"{record['output_size_bytes']:,} | `{record['output_sha256']}` | "
            f"{record['detailed_warnings']} | byte-identical |"
        )
    lines.extend(
        [
            "",
            "All modules were compiled twice with `-D__NGSPICE__ --target_cpu generic` ",
            "outside the immutable PDK checkout. The three R3_CMC diagnostics are the ",
            "declared upstream `$simparam` constant warnings; no other compile warning is accepted.",
            "",
            "## Official low-voltage CMOS smoke result",
            "",
            "| Measure | Value |",
            "|---|---:|",
            f"| DC output, input low | {metrics['dc_out_low_v']:.9g} V |",
            f"| DC output, input high | {metrics['dc_out_high_v']:.9g} V |",
            f"| Transient output low | {metrics['tran_out_low_v']:.9g} V |",
            f"| Transient output high | {metrics['tran_out_high_v']:.9g} V |",
            f"| High-to-low delay | {metrics['tphl_s'] * 1e12:.6g} ps |",
            f"| Low-to-high delay | {metrics['tplh_s'] * 1e12:.6g} ps |",
            "",
            "The simple 10-fF inverter uses the official `sg13_lv_nmos` and ",
            "`sg13_lv_pmos` wrappers at the public `mos_tt` corner, 1.2 V and 27 °C. ",
            "These values are a tool/model sanity check only.",
            "",
            "## Claim boundary",
            "",
            "This establishes a pristine, reproducible IHP device-model path before the ",
            "independent physical ROM replication. It does not establish a ROM cell, compact ",
            "array, density, read path, yield, target-node scaling, wafer behavior, or GPU speedup. ",
            "No result may be scaled into N7 or N4.",
            "",
            "Exact commands, identities, hashes, thresholds, replay status, and logs are in ",
            "`results/spice/ihp_device_smoke/device_smoke.json` and its `artifacts/` directory.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--openvaf", type=Path)
    parser.add_argument("--ngspice", type=Path)
    args = parser.parse_args()

    try:
        contract = strict_json(CONTRACT_PATH)
        lock = strict_json(repository_path(contract["pdk_lock"]))
        validate_contract(contract, lock)
        if args.validate_only:
            print("IHP DEVICE SMOKE CONTRACT PASS")
            return 0

        pdk = locate_pdk(args.pdk_root)
        compiler = locate_tool(
            args.openvaf,
            "OPENTALLAS_OPENVAF",
            Path.home()
            / ".local"
            / "opentallas-tools"
            / "openvaf-23.5.0-target-cpu-fix"
            / "bin"
            / "openvaf",
            "patched OpenVAF 23.5.0",
        )
        ngspice = locate_tool(
            args.ngspice,
            "OPENTALLAS_NGSPICE",
            Path.home()
            / ".local"
            / "opentallas-tools"
            / "ngspice-43-osdi"
            / "bin"
            / "ngspice",
            "ngspice 43 with OSDI",
        )

        pdk_before = verify_pdk(pdk)
        compiler_record = verify_tool(
            compiler,
            lock["tools"]["openvaf"]["executable_sha256"],
            lock["tools"]["openvaf"]["executable_size_bytes"],
            ["--version"],
            "openvaf 23.5.0",
        )
        ngspice_record = verify_tool(
            ngspice,
            lock["tools"]["ngspice"]["executable_sha256"],
            lock["tools"]["ngspice"]["executable_size_bytes"],
            ["--version"],
            "ngspice-43",
        )

        with tempfile.TemporaryDirectory(prefix="opentallas-ihp-smoke-") as temporary:
            temporary_root = Path(temporary)
            output_root = temporary_root / "osdi"
            log_root = temporary_root / "logs"
            output_root.mkdir()
            log_root.mkdir()
            primary = compile_models(
                pdk, compiler, output_root, log_root, lock, contract, "primary"
            )
            replay = compile_models(
                pdk, compiler, output_root, log_root, lock, contract, "replay"
            )
            replay_result = enforce_replay(
                output_root / "primary",
                output_root / "replay",
                contract["model_compile"]["models"],
            )
            simulation = simulate(
                pdk,
                ngspice,
                output_root / "primary",
                temporary_root,
                log_root,
                contract,
            )
            pdk_after = verify_pdk(pdk)
            if pdk_before != pdk_after:
                raise SmokeError("PDK semantic identity changed during the generated-model run")

            artifact_directory = repository_path(contract["reports"]["artifacts"])
            if artifact_directory.exists():
                shutil.rmtree(artifact_directory)
            artifact_directory.mkdir(parents=True)
            archived_logs: list[Path] = []
            for source in sorted(log_root.iterdir()):
                destination = artifact_directory / source.name
                shutil.copy2(source, destination)
                archived_logs.append(destination)

        result_path = repository_path(contract["reports"]["json"])
        report_path = repository_path(contract["reports"]["markdown"])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result: dict[str, Any] = {
            "schema_version": 1,
            "experiment_id": contract["experiment_id"],
            "status": "pass",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "pdk": pdk_after,
            "tools": {
                "openvaf": compiler_record,
                "ngspice": ngspice_record,
            },
            "model_compilation": {
                "define": contract["model_compile"]["define"],
                "target_cpu": contract["model_compile"]["target_cpu"],
                "output_location": "ephemeral directory outside immutable PDK",
                "primary": primary,
                "replay": replay,
                "semantic_replay": replay_result,
            },
            "simulation": simulation,
            "inputs": {
                "contract": {
                    "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
                    "sha256": sha256_file(CONTRACT_PATH),
                },
                "pdk_lock": {
                    "path": repository_path(contract["pdk_lock"])
                    .relative_to(ROOT)
                    .as_posix(),
                    "sha256": sha256_file(repository_path(contract["pdk_lock"])),
                },
                "spice_init": {
                    "path": contract["inputs"]["spice_init"],
                    "sha256": sha256_file(repository_path(contract["inputs"]["spice_init"])),
                },
                "deck": {
                    "path": contract["inputs"]["deck"],
                    "sha256": sha256_file(repository_path(contract["inputs"]["deck"])),
                },
                "runner": {
                    "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
                    "sha256": sha256_file(Path(__file__).resolve()),
                },
            },
            "artifacts": artifact_records(archived_logs),
            "claim_boundary": contract["claim_boundary"],
        }
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        write_report(result, report_path)
        print(
            f"PASS: 4/4 official IHP models compiled twice byte-identically; "
            f"DC/transient official-device smoke passed; wrote {result_path}"
        )
        return 0
    except (OSError, SmokeError, subprocess.TimeoutExpired) as exc:
        print(f"IHP device smoke failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
