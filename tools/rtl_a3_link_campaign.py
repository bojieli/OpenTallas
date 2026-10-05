#!/usr/bin/env python3
"""Run and record the two-simulator campaign for the ABI 3.0 link endpoint.

The campaign elaborates the mesh once per declared geometry, replays the same
vector set under Icarus Verilog and under a separately compiled Verilator
binary, and requires:

* the exact PASS marker the vector generator derived from the functional model;
* byte-identical per-case measurement lines from the two simulators -- a
  disagreement between two independent simulators on a cycle count is a defect
  in the RTL, not a tolerance;
* the measured serial traversal count of every collective, which is what
  `src/opentallas/roofline.py` charges as `collective_traversals` and what this
  program has never measured.

Tool identity is recorded, not assumed: resolved path, SHA-256 and self-reported
version, with a Verilator older than the pinned 5.050 or an Icarus older than
11.0 refused rather than silently accepted.
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
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = ROOT / "testdata/rtl/a3_link"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_link_campaign.json"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/lib/ot_crc_pkg.sv",
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_link_pkg.sv",
    "rtl/abi3/ot_a3_communication_decoder.sv",
    "rtl/abi3/ot_a3_link_channel.sv",
    "rtl/abi3/ot_a3_mesh_router.sv",
    "rtl/abi3/ot_a3_collective_engine.sv",
    "rtl/abi3/ot_a3_link_node.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_link_mesh_top.sv",
    "rtl/test/tb_a3_link.sv",
)
#: The frozen contracts and the executed model this RTL is checked against.
#: They are hashed so a change to either invalidates this evidence instead of
#: silently outdating it.
CONTRACT_SOURCES = (
    "spec/abi3/registries.json",
    "spec/abi3/descriptor_payloads.json",
    "spec/abi3/records.json",
    "runtime/abi3/crc.py",
    "runtime/abi3/constants.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/records.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/engines/link.py",
    "runtime/sim/engines/reduction.py",
    "src/opentallas/roofline.py",
)
TOOL_SOURCES = (
    "tools/build_a3_link_vectors.py",
    "tools/rtl_a3_link_campaign.py",
)

CASE_RE = re.compile(
    r"^CASE (?P<index>\d+) op=(?P<op>\d+) alg=(?P<alg>\d+) order=(?P<order>\d+) "
    r"cycles=(?P<cycles>\d+) traversals=(?P<traversals>\d+) "
    r"engine_flits=(?P<engine_flits>\d+) crossings=(?P<crossings>\d+) "
    r"retries=(?P<retries>\d+) crc_errors=(?P<crc_errors>\d+) "
    r"credit_stalls=(?P<credit_stalls>\d+) replayed=(?P<replayed>\d+) "
    r"trap=(?P<trap>\d+) trap_class=(?P<trap_class>\d+) "
    r"record_valid=(?P<record_valid>\d+) "
    r"numeric_valid=(?P<numeric_valid>\d+) "
    r"numeric_supported=(?P<numeric_supported>\d+) "
    r"admitted=(?P<admitted>\d+) reason=(?P<reason>\d+)$"
)
CHECKS_RE = re.compile(r"checks=(\d+)")
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")
IVERILOG_VERSION_RE = re.compile(r"Icarus Verilog version (\d+)\.(\d+)")
VVP_VERSION_RE = re.compile(r"Icarus Verilog runtime version (\d+)\.(\d+)")

TOOL_TIMEOUT_SECONDS = 30
COMPILE_TIMEOUT_SECONDS = 300
SIMULATION_TIMEOUT_SECONDS = 300
TIMEOUT_RETURN_CODE = 124

CANONICAL_CONFIGURATIONS = (
    "mesh4x4_vec16_hop1",
    "mesh4x4_vec16_hop2",
    "mesh4x4_vec16_hop4",
    "mesh4x4_vec16_hop8",
    "mesh8x8_vec64_hop1",
    "mesh2x2_vec4_hop1",
    "mesh8x4_vec32_credit32_hop1",
)
CANONICAL_SYNTHETIC_CASES = (
    "synthetic_allreduce_sum_recursive_doubling",
    "synthetic_allreduce_sum_halving_doubling",
    "synthetic_sum_halving_pairwise_order_refused",
    "synthetic_sum_recursive_blocked_order_refused",
    "synthetic_allreduce_max",
    "synthetic_allreduce_min",
    "synthetic_broadcast",
    "synthetic_barrier",
    "synthetic_allreduce_sum_crc_replay",
    "synthetic_sum_sequential_order_refused",
    "synthetic_sum_overflow_trap",
    "synthetic_max_nonfinite_trap",
    "synthetic_min_nonfinite_trap",
    "synthetic_max_signed_zero",
    "synthetic_min_signed_zero",
    "synthetic_tile_scope_refused",
    "synthetic_selected_group_refused",
    "synthetic_broadcast_root_out_of_range_refused",
    "synthetic_extent_mismatch_refused",
    "synthetic_chunk_mismatch_refused",
    "synthetic_data_offset_refused",
    "synthetic_control_metadata_refused",
    "synthetic_algorithm_unregistered_refused",
    "synthetic_numeric_stale_crc_refused",
    "synthetic_numeric_sideband_order_mismatch_refused",
)
CANONICAL_HBM_CASES = CANONICAL_SYNTHETIC_CASES + (
    "certified_hbm_sum_exact",
    "certified_hbm_sum_exact_decode_repeat",
    "certified_hbm_barrier_exact",
    "certified_hbm_all_gather_refused",
    "certified_hbm_concat_refused",
    "certified_rom_p2p_refused",
    "reduce_scatter_refused",
    "bad_magic",
    "bad_type",
    "bad_version",
    "bad_total_bytes",
    "bad_payload_geometry",
    "header_reserved_nonzero",
    "payload_reserved_nonzero",
    "stale_record_crc",
    "permissions_reserved",
    "collective_op_unregistered",
    "ordering_unregistered",
    "integrity_mode_unregistered",
    "participant_scope_unregistered",
    "integrity_ecc_unsupported",
    "virtual_channel_out_of_range",
    "credit_bound_mismatch",
    "retry_bound_mismatch",
    "timeout_class_mismatch",
    "participant_count_mismatch",
    "object_binding_mismatch",
    "barrier_nonzero_extent",
)


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


def run(command: list[str], cwd: Path,
        timeout: int = SIMULATION_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command, cwd=str(cwd), capture_output=True, text=True,
            check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        stderr += f"\nTIMEOUT after {timeout} seconds"
        return subprocess.CompletedProcess(
            command, TIMEOUT_RETURN_CODE, stdout=stdout, stderr=stderr
        )


def resolve_verilator() -> Path:
    pinned = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    if pinned.exists():
        return pinned
    found = shutil.which("verilator")
    if found is None:
        raise SystemExit("verilator is not installed")
    return Path(found)


def tool_identity(path: Path, version_args: list[str], pattern: re.Pattern,
                  minimum: tuple[int, int], name: str) -> dict[str, Any]:
    proc = run([str(path)] + version_args, ROOT, TOOL_TIMEOUT_SECONDS)
    if proc.returncode == TIMEOUT_RETURN_CODE:
        raise SystemExit(f"{name} version probe timed out")
    if proc.returncode != 0:
        raise SystemExit(f"{name} version probe exited {proc.returncode}")
    text = (proc.stdout + proc.stderr).strip()
    match = pattern.search(text)
    if match is None:
        raise SystemExit(f"cannot read {name} version from {text!r}")
    version = (int(match.group(1)), int(match.group(2)))
    if version < minimum:
        raise SystemExit(
            f"{name} {version[0]}.{version[1]} is older than the pinned "
            f"{minimum[0]}.{minimum[1]}"
        )
    return {
        "executable": scrub(str(path)),
        "executable_sha256": sha256(path),
        "version": text.splitlines()[0],
    }


def parse_cases(log: str, expected_count: int | None = None) -> list[dict[str, int]]:
    cases = []
    for line in log.splitlines():
        match = CASE_RE.match(line.strip())
        if match:
            cases.append({k: int(v) for k, v in match.groupdict().items()})
    if expected_count is not None:
        indices = [case["index"] for case in cases]
        expected = list(range(expected_count))
        if len(cases) != expected_count:
            raise ValueError(
                f"parsed {len(cases)} CASE lines, expected {expected_count}"
            )
        if indices != expected:
            raise ValueError(
                f"CASE indices are {indices}, expected exactly {expected}"
            )
    return cases


def validate_canonical_index(index: dict[str, Any]) -> None:
    """Refuse a canonical artifact if its ordered matrix is incomplete."""
    configurations = index.get("configurations", [])
    names = tuple(entry.get("name") for entry in configurations)
    if names != CANONICAL_CONFIGURATIONS:
        raise ValueError(
            f"canonical configurations are {names}, expected "
            f"{CANONICAL_CONFIGURATIONS}"
        )
    for entry in configurations:
        expected = (
            CANONICAL_HBM_CASES
            if entry["name"] == "mesh8x4_vec32_credit32_hop1"
            else CANONICAL_SYNTHETIC_CASES
        )
        labels = tuple(case.get("label") for case in entry.get("cases", []))
        if labels != expected:
            raise ValueError(
                f"{entry['name']} canonical cases are {labels}, expected {expected}"
            )


def evaluate_simulator_result(
    result: dict[str, Any], marker: str, expected_count: int
) -> list[dict[str, int]]:
    """Apply all process, marker, cardinality and index gates to one run."""
    log = result.get("run_log", "")
    result["marker_present"] = marker in log.splitlines()
    checks = CHECKS_RE.search(log)
    result["checks"] = int(checks.group(1)) if checks else 0
    parse_error = None
    try:
        parsed = parse_cases(log, expected_count)
    except ValueError as exc:
        parsed = []
        parse_error = str(exc)
    result["case_parse_error"] = parse_error
    run_ok = result.get("run_returncode") == 0
    if result.get("status") not in {
        "compile_failed", "compile_timeout", "run_timeout"
    }:
        result["status"] = "pass" if (
            run_ok and result["marker_present"] and parse_error is None
        ) else "fail"
    return parsed


def run_iverilog(config: dict, vec_dir: Path, work: Path,
                 iverilog: Path, vvp: Path) -> dict[str, Any]:
    out = work / "a3_link.vvp"
    compile_cmd = [
        str(iverilog), "-g2012", "-s", "tb_a3_link",
        f"-Ptb_a3_link.MESH_X={config['mesh_x']}",
        f"-Ptb_a3_link.MESH_Y={config['mesh_y']}",
        f"-Ptb_a3_link.VEC_LEN={config['vec_len']}",
        f"-Ptb_a3_link.CREDITS={config['credits']}",
        f"-Ptb_a3_link.RETRY_MAX={config['retry_max']}",
        f"-Ptb_a3_link.TIMEOUT_CLASS={config['timeout_class']}",
        f"-Ptb_a3_link.HOP_CYCLES={config['hop_cycles']}",
        f"-Ptb_a3_link.MAX_CASES={len(config['cases'])}",
        "-o", str(out),
    ] + [str(ROOT / s) for s in RTL_SOURCES + TESTBENCH_SOURCES]
    compiled = run(compile_cmd, ROOT, COMPILE_TIMEOUT_SECONDS)
    result = {
        "name": "iverilog",
        "compile_command": scrub(shlex.join(compile_cmd), work),
        "compile_returncode": compiled.returncode,
        "compile_log": scrub(
            (compiled.stdout + compiled.stderr).strip(), work
        ),
    }
    if compiled.returncode != 0:
        result["status"] = (
            "compile_timeout" if compiled.returncode == TIMEOUT_RETURN_CODE
            else "compile_failed"
        )
        return result
    run_cmd = [
        str(vvp), str(out),
        f"+META={vec_dir/'meta.hex'}",
        f"+CASE={vec_dir/'case.hex'}",
        f"+COMMUNICATION={vec_dir/'communication.hex'}",
        f"+NUMERIC={vec_dir/'numeric.hex'}",
        f"+CONTRIB={vec_dir/'contrib.hex'}",
        f"+EXPECT={vec_dir/'expect.hex'}",
    ]
    executed = run(run_cmd, ROOT, SIMULATION_TIMEOUT_SECONDS)
    log = (executed.stdout + executed.stderr).strip()
    result.update({
        "run_command": scrub(shlex.join(run_cmd), work),
        "run_returncode": executed.returncode,
        "run_log": scrub(log, work),
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
    })
    if executed.returncode == TIMEOUT_RETURN_CODE:
        result["status"] = "run_timeout"
    return result


def run_verilator(config: dict, vec_dir: Path, work: Path,
                  verilator: Path) -> dict[str, Any]:
    mdir = work / "vlt"
    compile_cmd = [
        str(verilator), "--binary", "-j", "4", "--top-module", "tb_a3_link",
        f"-GMESH_X={config['mesh_x']}",
        f"-GMESH_Y={config['mesh_y']}",
        f"-GVEC_LEN={config['vec_len']}",
        f"-GCREDITS={config['credits']}",
        f"-GRETRY_MAX={config['retry_max']}",
        f"-GTIMEOUT_CLASS={config['timeout_class']}",
        f"-GHOP_CYCLES={config['hop_cycles']}",
        f"-GMAX_CASES={len(config['cases'])}",
        "-Wno-fatal", "--Mdir", str(mdir), "-o", "vsim",
    ] + [str(ROOT / s) for s in RTL_SOURCES + TESTBENCH_SOURCES]
    compiled = run(compile_cmd, ROOT, COMPILE_TIMEOUT_SECONDS)
    result = {
        "name": "verilator",
        "compile_command": scrub(shlex.join(compile_cmd), work),
        "compile_returncode": compiled.returncode,
        "compile_log": scrub(
            (compiled.stdout + compiled.stderr).strip()[-4000:], work
        ),
    }
    if compiled.returncode != 0:
        result["status"] = (
            "compile_timeout" if compiled.returncode == TIMEOUT_RETURN_CODE
            else "compile_failed"
        )
        return result
    run_cmd = [
        str(mdir / "vsim"),
        f"+META={vec_dir/'meta.hex'}",
        f"+CASE={vec_dir/'case.hex'}",
        f"+COMMUNICATION={vec_dir/'communication.hex'}",
        f"+NUMERIC={vec_dir/'numeric.hex'}",
        f"+CONTRIB={vec_dir/'contrib.hex'}",
        f"+EXPECT={vec_dir/'expect.hex'}",
    ]
    executed = run(run_cmd, ROOT, SIMULATION_TIMEOUT_SECONDS)
    log = (executed.stdout + executed.stderr).strip()
    result.update({
        "run_command": scrub(shlex.join(run_cmd), work),
        "run_returncode": executed.returncode,
        "run_log": scrub(log, work),
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
    })
    if executed.returncode == TIMEOUT_RETURN_CODE:
        result["status"] = "run_timeout"
    return result


def hop_regression(configurations: list[dict]) -> dict[str, Any]:
    """Least squares of measured cycles against the declared hop occupancy.

    The analytical model charges a collective `traversals x hop_latency`.  With
    the same geometry evaluated at several declared hop occupancies, the slope
    of measured cycles against that occupancy IS the traversal count the RTL
    actually walks, and the intercept is the per-collective fixed cost the
    model has no term for at all.
    """
    families: dict[tuple, list[tuple[int, int]]] = {}
    labels: dict[tuple, str] = {}
    for cfg in configurations:
        if cfg.get("status") != "pass":
            continue
        key_base = (cfg["mesh_x"], cfg["mesh_y"], cfg["vec_len"], cfg["credits"])
        for case in cfg["cases"]:
            key = key_base + (case["label"],)
            families.setdefault(key, []).append(
                (cfg["hop_cycles"], case["measured"]["cycles"])
            )
            labels[key] = case["label"]
    report = []
    for key, points in sorted(families.items()):
        if len(points) < 2:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        n = len(points)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        if denom == 0:
            continue
        slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denom
        intercept = mean_y - slope * mean_x
        residual = max(abs(y - (slope * x + intercept)) for x, y in points)
        report.append({
            "mesh": f"{key[0]}x{key[1]}",
            "vec_len": key[2],
            "credits": key[3],
            "label": key[4],
            "points": sorted(points),
            "cycles_per_hop_cycle": slope,
            "fixed_cycles": intercept,
            "max_residual_cycles": residual,
        })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--only", default="", help="run one configuration by name")
    args = parser.parse_args()

    index = json.loads((VECTOR_DIR / "index.json").read_text())
    output = Path(args.output)
    canonical_output = output.resolve() == DEFAULT_OUTPUT.resolve()
    if canonical_output and args.only:
        raise SystemExit(
            "--only cannot write the canonical a3_link_campaign.json artifact"
        )
    if canonical_output:
        try:
            validate_canonical_index(index)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    selected = [
        entry for entry in index.get("configurations", [])
        if not args.only or entry.get("name") == args.only
    ]
    if not selected:
        raise SystemExit(
            f"configuration selection is empty (requested {args.only!r})"
        )

    iverilog = Path(shutil.which("iverilog") or "")
    vvp = Path(shutil.which("vvp") or "")
    if not iverilog.exists() or not vvp.exists():
        raise SystemExit("iverilog/vvp are not installed")
    verilator = resolve_verilator()
    cxx = Path(shutil.which("g++") or "")
    if not cxx.exists():
        raise SystemExit("g++ is not installed")
    cxx_version = run([str(cxx), "--version"], ROOT, TOOL_TIMEOUT_SECONDS)
    if cxx_version.returncode != 0:
        raise SystemExit("g++ version probe failed or timed out")

    tools = {
        "iverilog": tool_identity(iverilog, ["-V"], IVERILOG_VERSION_RE, (11, 0),
                                  "iverilog"),
        "vvp": tool_identity(vvp, ["-V"], VVP_VERSION_RE, (11, 0), "vvp"),
        "verilator": tool_identity(verilator, ["--version"],
                                   VERILATOR_VERSION_RE, (5, 50), "verilator"),
        "cxx": {
            "executable": scrub(str(cxx)),
            "executable_sha256": sha256(cxx),
            "version": cxx_version.stdout.splitlines()[0],
        },
    }

    configurations: list[dict[str, Any]] = []
    overall = "pass"
    for entry in selected:
        vec_dir = VECTOR_DIR / entry["name"]
        marker = entry["marker"]
        with tempfile.TemporaryDirectory(prefix="a3link-") as tmp:
            work = Path(tmp)
            simulators = [
                run_iverilog(entry, vec_dir, work, iverilog, vvp),
                run_verilator(entry, vec_dir, work, verilator),
            ]
        parsed = []
        for sim in simulators:
            parsed.append(
                evaluate_simulator_result(sim, marker, len(entry["cases"]))
            )

        agree = parsed[0] == parsed[1] and bool(parsed[0])
        status = "pass" if agree and all(s["status"] == "pass" for s in simulators) \
            else "fail"
        if status != "pass":
            overall = "fail"

        cases = []
        measured_by_index = {
            measured["index"]: measured for measured in parsed[0]
        }
        for case_index, spec in enumerate(entry["cases"]):
            measured = measured_by_index.get(case_index)
            cases.append({
                "label": spec["label"],
                "op": spec["op"],
                "engine_op": spec["engine_op"],
                "instruction_subopcode": spec["subopcode"],
                "alg": spec["alg"],
                "reduction_order": spec["order"],
                "numeric_descriptor_id": spec["numeric_descriptor_id"],
                "expect_trap": spec["expect_trap"],
                "expected_trap_class": spec["expected_trap_class"],
                "record_valid": spec["record_valid"],
                "numeric_record_valid": spec["numeric_record_valid"],
                "numeric_semantics_supported":
                    spec["numeric_semantics_supported"],
                "numeric_refusal_reason": spec["numeric_refusal_reason"],
                "command_admitted": spec["command_admitted"],
                "refusal_reason": spec["refusal_reason"],
                "source": spec["source"],
                "source_bundle": spec["source_bundle"],
                "source_descriptor_id": spec["source_descriptor_id"],
                "source_record_sha256": spec["source_record_sha256"],
                "record_sha256": spec["record_sha256"],
                "exact_source_record": spec["exact_source_record"],
                "mutations": spec["mutations"],
                "stale_crc": spec["stale_crc"],
                "numeric_source": spec["numeric_source"],
                "numeric_source_descriptor_id":
                    spec["numeric_source_descriptor_id"],
                "numeric_source_record_sha256":
                    spec["numeric_source_record_sha256"],
                "numeric_record_sha256": spec["numeric_record_sha256"],
                "numeric_exact_source_record":
                    spec["numeric_exact_source_record"],
                "numeric_mutations": spec["numeric_mutations"],
                "numeric_stale_crc": spec["numeric_stale_crc"],
                "execution_class": spec["execution_class"],
                "input_pattern": spec["input_pattern"],
                "expected": {
                    "serial_traversals": spec["expected_serial_traversals"],
                    "engine_flits": spec["expected_engine_flits"],
                    "wire_crossings": spec["expected_wire_crossings"],
                },
                "measured": measured,
                "functional_model_messages": spec["functional_model_messages"],
                "functional_model_payload_bytes":
                    spec["functional_model_payload_bytes"],
                "functional_oracle": spec["functional_oracle"],
            })

        configurations.append({
            "name": entry["name"],
            "mesh_x": entry["mesh_x"],
            "mesh_y": entry["mesh_y"],
            "vec_len": entry["vec_len"],
            "nodes": entry["nodes"],
            "credits": entry["credits"],
            "retry_max": entry["retry_max"],
            "timeout_class": entry["timeout_class"],
            "hop_cycles": entry["hop_cycles"],
            "diameter": entry["diameter"],
            "model_charged_traversals": entry["model_charged_traversals"],
            "sequential_vs_tree_differing_elements":
                entry["sequential_vs_tree_differing_elements"],
            "pairwise_tree_vs_halving_differing_elements":
                entry["pairwise_tree_vs_halving_differing_elements"],
            "blocked_ascending_vs_halving_differing_elements":
                entry["blocked_ascending_vs_halving_differing_elements"],
            "sequential_vs_tree_elements": entry["sequential_vs_tree_elements"],
            "required_marker": marker,
            "simulators": simulators,
            "simulators_agree": agree,
            "status": status,
            "cases": cases,
        })
        print(f"{entry['name']}: {status}")

    source_hashes = {}
    for rel in RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES:
        source_hashes[rel] = sha256(ROOT / rel)
    for entry in index["configurations"]:
        for name in (
            "meta.hex", "case.hex", "communication.hex", "contrib.hex",
            "numeric.hex", "expect.hex",
        ):
            rel = f"testdata/rtl/a3_link/{entry['name']}/{name}"
            source_hashes[rel] = sha256(ROOT / rel)
    source_hashes["testdata/rtl/a3_link/index.json"] = sha256(
        VECTOR_DIR / "index.json"
    )
    for source in index["certified_sources"]:
        source_hashes[source["certificate"]] = sha256(ROOT / source["certificate"])
        for name in ("deployment.json", "descriptors.bin", "program.bin"):
            rel = f"{source['bundle']}/{name}"
            source_hashes[rel] = sha256(ROOT / rel)

    artifact = {
        "schema": "opentallas.rtl.a3_link_campaign.v3",
        "campaign": "rtl3_a3_link_endpoint",
        "status": overall,
        "canonical_complete": canonical_output and not args.only and
            tuple(entry["name"] for entry in selected) == CANONICAL_CONFIGURATIONS,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "reference": (
            "runtime.sim.engines.reduction.ordered_sum for the reduced value; "
            "runtime.sim.engines.link.collective_traffic and barrier_messages "
            "for the functional model's own message and byte counts; "
            "src/opentallas/roofline.py MESH_ALLREDUCE_DIAMETER_FACTOR for the "
            "traversal charge the measurement is compared against"
        ),
        "compared": [
            "the reduced binary32 code at every participant and every element",
            "all common-header and COMMUNICATION payload fields at their frozen "
            "little-endian byte offsets",
            "all NUMERIC arithmetic controls, header/payload reserved bytes, "
            "permissions, registry fields and whole-record CRC32C",
            "descriptor magic, type/version, size, payload geometry, reserved "
            "bytes, permissions, registries and whole-record CRC32C admission",
            "exact descriptor records extracted from certificate-bound current "
            "DeepSeek deployments, plus mutations made only after extraction",
            "the trap class of an arithmetic collective whose declared reduction "
            "order the fabric cannot produce",
            "class-6 traps before writeback for binary32 overflow and nonfinite "
            "MAX/MIN operands, plus deterministic positive-zero MAX/MIN ties",
            "serial traversals walked by the collective's schedule",
            "flits the engine offered and link crossings the fabric performed",
            "CRC detection, bounded replay and bit-identical recovery",
            "cycle-for-cycle agreement between two independent simulators",
        ],
        "tools": tools,
        "configurations": configurations,
        "hop_latency_regression": hop_regression(configurations),
        "communication_field_boundary": {
            "command_admitted_semantics": (
                "all ABI command semantics present in the admitted record are "
                "implemented; unsupported integration semantics must be neutral"
            ),
            "production_fail_closed_admission": True,
            "not_shipped_deployment_sequencer_integration": True,
            "admitted_command_field_constraints": {
                "flags": "required zero",
                "primary_object_id": "data-buffer binding; NO_ID for barriers",
                "secondary_object_id": "data-buffer binding; NO_ID for barriers",
                "numeric_profile_id": "required NO_ID; reduction_numeric_id is separate",
                "schedule_id": "required NO_ID; algorithm is an explicit sideband",
                "permissions": "required zero after structural validation",
                "owner_scope_id": "required zero",
                "ordering": "required NONE; no memory-order sequencer is present",
                "virtual_channel": "required zero; the router has one buffer class",
                "destination_node": "required NO_NODE for supported collectives",
                "route_class": "required zero; routing is fixed dimension order",
                "local_object_id": "equals primary binding; NO_ID for barriers",
                "remote_object_id": "equals secondary binding; NO_ID for barriers",
                "local_offset": "required zero; no object address calculation",
                "remote_offset": "required zero; no object address calculation",
                "timeout_class": "must equal the elaboration parameter but does not translate ACK_TIMEOUT",
                "completion_event_id": "required NO_ID; no event signal is emitted",
                "reduction_numeric_id": "required NO_ID for barriers",
                "counter_class_id": "required NO_ID; no ABI counter object is updated",
                "chunk_bytes": "required zero for barriers and four for data probes",
            },
            "exact_hbm_barrier_2948": {
                "evidence_case": "certified_hbm_barrier_exact",
                "record_bytes": "certificate-exact and SHA-256 locked",
                "record_valid": True,
                "command_admitted": False,
                "refusal_reason": "COMM_REFUSE_CONTROL_METADATA (37)",
                "certified_functional_oracle": {
                    "source": "runtime.sim.engines.link.barrier_messages",
                    "topology_class": "CLUSTER_32",
                    "messages": 160,
                    "payload_bytes": 0,
                },
                "measured_engine_flits_crossings_traversals_and_cycles": 0,
            },
            "synthetic_neutral_barrier_probe": {
                "evidence_case": "synthetic_barrier",
                "record_bytes": "synthetic and CRC32C-resealed",
                "command_admitted": True,
                "all_barrier_timing_and_cycle_measurements_attributed_here": True,
            },
            "barrier_collective_op_semantics": (
                "don't-care for an otherwise admissible neutral barrier: the "
                "synthetic_barrier record carries POINT_TO_POINT while the "
                "LINK.BARRIER instruction subopcode selects barrier execution"
            ),
        },
        "claim_boundary": {
            "measures_wire_delay_seconds": False,
            "measures_reticle_boundary_delay": False,
            "measures_stitched_or_bonded_crossing": False,
            "establishes_hop_latency_s": False,
            "establishes_target_node_frequency": False,
            "contains_rom_or_sram_macro": False,
            "is_placed_or_routed": False,
            "implements_engine_arithmetic_other_than_binary32_add_max_min": False,
            "implements_virtual_channels_or_wormhole_routing": False,
            "implements_the_full_abi3_communication_descriptor_decode": True,
            "loads_or_decodes_referenced_numeric_descriptors": True,
            "executes_exact_hbm_sum_descriptor_1044": False,
            "executes_exact_hbm_barrier": False,
            "executes_only_synthetic_bounded_data_probes": True,
            "executes_only_synthetic_bounded_commands": True,
            "barrier_timing_uses_only_synthetic_neutral_probe": True,
            "command_admitted_means_full_abi_execution": True,
            "command_admitted_means_standalone_link_data_plane": False,
            "integrates_shipped_deployment_sequencer": False,
            "implements_completion_events_or_counter_updates": False,
            "implements_memory_ordering_or_object_access": False,
            "loads_or_validates_referenced_object_descriptors": False,
            "executes_point_to_point_or_remote_dma": False,
            "executes_concat_all_gather_or_reduce_scatter": False,
            "measures_traversal_counts_and_cycles": True,
            "measures_credit_and_retry_behaviour": True,
        },
        "limitations": [
            "This is a functional endpoint. It establishes how many traversals a "
            "collective walks and how many cycles this endpoint contract costs "
            "at a DECLARED hop occupancy. It does not measure wire delay across a "
            "stitched reticle boundary, and it does not establish what one hop "
            "costs in seconds. links.on_wafer's 125 ns remains derived from "
            "published geometry, not measured here.",
            "HOP_CYCLES is a parameter of the experiment, not an output of it. "
            "The regression's slope is a traversal count, not a latency.",
            "The mesh is built from single-flit packets under dimension-ordered "
            "routing with one buffer class. It has no virtual channels, no "
            "wormhole flow control, and no adaptive routing, so it says nothing "
            "about the congestion behaviour of a fabric that has them.",
            "The engine implements binary32 add, max and min. It does not "
            "implement the MXFP4 x FP8, FP8 x FP8 or BF16 arithmetic this "
            "program targets, and the reduction is the only arithmetic here.",
            "The RTL decodes the complete 192-byte COMMUNICATION record and the "
            "complete referenced 128-byte NUMERIC record. It does not load the "
            "referenced object, counter or TOPOLOGY descriptors. The collective "
            "algorithm is an explicit non-ABI sideband, cross-checked against "
            "the reduction order decoded from NUMERIC.",
            "Exact DeepSeek HBM COMMUNICATION descriptor 1044 and NUMERIC "
            "descriptor 1040 are decode evidence only. Descriptor 1044 is "
            "execution-refused: it declares 25,165,824 BF16 bytes in 65,536-byte "
            "chunks, while the bounded RTL consumes VEC_LEN binary32 words in "
            "4-byte flits. Its functional traffic oracle remains the certified "
            "1,984 messages and 1,560,281,088 payload bytes.",
            "Exact DeepSeek HBM barrier descriptor 2948 is byte-exact decode "
            "evidence and retains its independently calculated certified "
            "CLUSTER_32 oracle of 160 messages and zero payload bytes. It is not "
            "executed: its acquire-release ordering, permissions, route, object, "
            "completion-event and counter semantics are unsupported and produce "
            "COMM_REFUSE_CONTROL_METADATA. Consequently its measured engine "
            "flits, crossings, traversals and cycles are all zero.",
            "All admitted commands are CRC-resealed synthetic bounded probes. "
            "The synthetic neutral barrier alone supplies barrier traversal and "
            "cycle measurements. Unimplemented COMMUNICATION integration fields "
            "must be neutral: flags and permissions zero; numeric_profile_id, "
            "schedule_id, completion_event_id and counter_class_id NO_ID; "
            "owner_scope_id, ordering, virtual_channel and route_class zero; and "
            "destination_node NO_NODE. Barrier object and reduction references "
            "are NO_ID and its chunk size is zero. Data-probe object IDs bind to "
            "the explicit harness buffers; no shipped object descriptor lookup "
            "or deployment sequencer integration is claimed.",
            "LINK.BARRIER semantics use byte_extent, participant membership and "
            "an optional source; runtime.sim.engines.link.barrier does not inspect "
            "collective_op. The CRC-resealed synthetic neutral barrier carries "
            "POINT_TO_POINT in that field while LINK.BARRIER selects the barrier "
            "engine, proving it does not silently select a collective algorithm.",
            "Both certificate-bound Qwen deployments contain zero "
            "COMMUNICATION descriptors. They are source-locked and reported as "
            "the real zero-communication boundary, not represented by invented "
            "positive bytes.",
            "virtual_channel is range-checked, but the router has one buffering "
            "class; the decoded value does not establish virtual-channel "
            "isolation. timeout_class is required to equal the elaboration's "
            "declared class; this decoder does not translate that class into "
            "ACK_TIMEOUT cycles.",
            "The receive buffer is banked by step tag for correctness, at "
            "2 lg(P) x VEC_LEN words per node. That is a reference-model "
            "buffer, sized for clarity rather than minimised, and it is not an "
            "area claim.",
            "No block here has been synthesised, placed or routed as part of "
            "this campaign.",
        ],
        "certified_sources": index["certified_sources"],
        "source_sha256": source_hashes,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=1, sort_keys=True) + "\n")
    print(f"{overall}: {output}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
