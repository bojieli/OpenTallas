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
import sys
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
    r"trap=(?P<trap>\d+)$"
)
CHECKS_RE = re.compile(r"checks=(\d+)")
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")
IVERILOG_VERSION_RE = re.compile(r"Icarus Verilog version (\d+)\.(\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub(text: str) -> str:
    return text.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, cwd=str(cwd), capture_output=True, text=True, check=False
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
    proc = subprocess.run(
        [str(path)] + version_args, capture_output=True, text=True, check=False
    )
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


def parse_cases(log: str) -> list[dict[str, int]]:
    cases = []
    for line in log.splitlines():
        match = CASE_RE.match(line.strip())
        if match:
            cases.append({k: int(v) for k, v in match.groupdict().items()})
    return cases


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
        f"-Ptb_a3_link.HOP_CYCLES={config['hop_cycles']}",
        f"-Ptb_a3_link.MAX_CASES={len(config['cases'])}",
        "-o", str(out),
    ] + [str(ROOT / s) for s in RTL_SOURCES + TESTBENCH_SOURCES]
    compiled = run(compile_cmd, ROOT)
    result = {
        "name": "iverilog",
        "compile_command": scrub(shlex.join(compile_cmd)),
        "compile_returncode": compiled.returncode,
        "compile_log": scrub((compiled.stdout + compiled.stderr).strip()),
    }
    if compiled.returncode != 0:
        result["status"] = "compile_failed"
        return result
    run_cmd = [
        str(vvp), str(out),
        f"+META={vec_dir/'meta.hex'}",
        f"+CASE={vec_dir/'case.hex'}",
        f"+CONTRIB={vec_dir/'contrib.hex'}",
        f"+EXPECT={vec_dir/'expect.hex'}",
    ]
    executed = run(run_cmd, ROOT)
    log = (executed.stdout + executed.stderr).strip()
    result.update({
        "run_command": scrub(shlex.join(run_cmd)),
        "run_returncode": executed.returncode,
        "run_log": scrub(log),
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
    })
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
        f"-GHOP_CYCLES={config['hop_cycles']}",
        f"-GMAX_CASES={len(config['cases'])}",
        "-Wno-fatal", "--Mdir", str(mdir), "-o", "vsim",
    ] + [str(ROOT / s) for s in RTL_SOURCES + TESTBENCH_SOURCES]
    compiled = run(compile_cmd, ROOT)
    result = {
        "name": "verilator",
        "compile_command": scrub(shlex.join(compile_cmd)),
        "compile_returncode": compiled.returncode,
        "compile_log": scrub((compiled.stdout + compiled.stderr).strip()[-4000:]),
    }
    if compiled.returncode != 0:
        result["status"] = "compile_failed"
        return result
    run_cmd = [
        str(mdir / "vsim"),
        f"+META={vec_dir/'meta.hex'}",
        f"+CASE={vec_dir/'case.hex'}",
        f"+CONTRIB={vec_dir/'contrib.hex'}",
        f"+EXPECT={vec_dir/'expect.hex'}",
    ]
    executed = run(run_cmd, ROOT)
    log = (executed.stdout + executed.stderr).strip()
    result.update({
        "run_command": scrub(shlex.join(run_cmd)),
        "run_returncode": executed.returncode,
        "run_log": scrub(log),
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
    })
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

    iverilog = Path(shutil.which("iverilog") or "")
    vvp = Path(shutil.which("vvp") or "")
    if not iverilog.exists() or not vvp.exists():
        raise SystemExit("iverilog/vvp are not installed")
    verilator = resolve_verilator()
    cxx = Path(shutil.which("g++") or "")

    tools = {
        "iverilog": tool_identity(iverilog, ["-V"], IVERILOG_VERSION_RE, (11, 0),
                                  "iverilog"),
        "verilator": tool_identity(verilator, ["--version"],
                                   VERILATOR_VERSION_RE, (5, 50), "verilator"),
        "cxx": {
            "executable": scrub(str(cxx)),
            "executable_sha256": sha256(cxx),
            "version": subprocess.run([str(cxx), "--version"], capture_output=True,
                                      text=True, check=False).stdout.splitlines()[0],
        },
    }

    configurations: list[dict[str, Any]] = []
    overall = "pass"
    for entry in index["configurations"]:
        if args.only and entry["name"] != args.only:
            continue
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
            log = sim.get("run_log", "")
            sim["marker_present"] = marker in log
            checks = CHECKS_RE.search(log)
            sim["checks"] = int(checks.group(1)) if checks else 0
            sim["status"] = "pass" if sim["marker_present"] else "fail"
            parsed.append(parse_cases(log))

        agree = parsed[0] == parsed[1] and bool(parsed[0])
        status = "pass" if agree and all(s["status"] == "pass" for s in simulators) \
            else "fail"
        if status != "pass":
            overall = "fail"

        cases = []
        for spec, measured in zip(entry["cases"], parsed[0] if parsed[0] else []):
            cases.append({
                "label": spec["label"],
                "op": spec["op"],
                "alg": spec["alg"],
                "reduction_order": spec["order"],
                "expect_trap": spec["expect_trap"],
                "expected": {
                    "serial_traversals": spec["expected_serial_traversals"],
                    "engine_flits": spec["expected_engine_flits"],
                    "wire_crossings": spec["expected_wire_crossings"],
                },
                "measured": measured,
                "functional_model_messages": spec["functional_model_messages"],
                "functional_model_payload_bytes":
                    spec["functional_model_payload_bytes"],
            })

        configurations.append({
            "name": entry["name"],
            "mesh_x": entry["mesh_x"],
            "mesh_y": entry["mesh_y"],
            "vec_len": entry["vec_len"],
            "nodes": entry["nodes"],
            "credits": entry["credits"],
            "retry_max": entry["retry_max"],
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
        for name in ("meta.hex", "case.hex", "contrib.hex", "expect.hex"):
            rel = f"testdata/rtl/a3_link/{entry['name']}/{name}"
            source_hashes[rel] = sha256(ROOT / rel)
    source_hashes["testdata/rtl/a3_link/index.json"] = sha256(
        VECTOR_DIR / "index.json"
    )

    artifact = {
        "schema": "opentallas.rtl.a3_link_campaign.v1",
        "campaign": "rtl3_a3_link_endpoint",
        "status": overall,
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
            "the trap class of an arithmetic collective whose declared reduction "
            "order the fabric cannot produce",
            "serial traversals walked by the collective's schedule",
            "flits the engine offered and link crossings the fabric performed",
            "CRC detection, bounded replay and bit-identical recovery",
            "cycle-for-cycle agreement between two independent simulators",
        ],
        "tools": tools,
        "configurations": configurations,
        "hop_latency_regression": hop_regression(configurations),
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
            "implements_the_full_abi3_communication_descriptor_decode": False,
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
            "The COMMUNICATION descriptor is not decoded in RTL. The engine "
            "takes op, algorithm, reduction order and root as ports; the "
            "descriptor's memory objects, offsets, permissions, group and route "
            "class are outside this block.",
            "The receive buffer is banked by step tag for correctness, at "
            "2 lg(P) x VEC_LEN words per node. That is a reference-model "
            "buffer, sized for clarity rather than minimised, and it is not an "
            "area claim.",
            "No block here has been synthesised, placed or routed as part of "
            "this campaign.",
        ],
        "source_sha256": source_hashes,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=1, sort_keys=True) + "\n")
    print(f"{overall}: {output}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
