#!/usr/bin/env python3
"""Run and record the two-simulator campaign for the T64 tile.

The artifact is ``results/rtl/abi3_tile64.json``: the tile
``rtl/abi3/ot_a3_tile64.sv`` (eight unmodified LQ8s, the tile stream sequencer,
the staging ring, the activation FIFO, the partial port) run over the contract
shapes -- decode (rows = 1) at (cols, K) = (192, 4,096) in BF16 g = 1, FP8 g = 2
and MXFP4 g = 4, (64, 1,024) in each, (192, 12,288) in BF16, a short final
block, batch rows, the prefill shape (16, 192, 1,024) in FP8 g = 2, the
qualification schedule (op_kblock = K), the tile's own refusals and run-time
faults, and LQ8 / lane faults propagated through the tile -- with every
partial checked against the exact AM-E1 reference per lane per K-block and
every tree root checked by feeding the captured partials through the RE8
endpoint beside the tile in the chained shapes of the K-block tree, on Icarus
Verilog 11 and the pinned Verilator 5.050 through two independently written
checkers that must print the same marker, the same check count and the same
rate lines.  The rate lines measure lane-ops per tile cycle and the cycles
per K-block.

Builds: the vehicle (WEIGHT_SOURCE = 0, STAGING_IN_TILE = 1) is the primary
evidence; the physical build's view (STAGING_IN_TILE = 0: ring and FIFO in the
top) and the ROM sense stream (WEIGHT_SOURCE = 1) are run on the quick profile
so every generate branch of the tile is simulated.

Every number in the artifact is one a run produced.  Tool identity, source
digests and the git state (commit and whether the tree was dirty) are recorded
so the evidence is bound to what produced it.  An optional Yosys 0.68
elaboration records that the netlist holds LQ8S LQ8 instances; it is
orientation for gate D3, not a physical result.
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
MANIFEST_DIR = ROOT / "testdata/rtl/abi3_tile64"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_tile64.json"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools"))
LQ8S = 8
LANES = 8
TILE_LANES = LQ8S * LANES

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_lane_pipelined.sv",
    "rtl/abi3/ot_a3_lq8.sv",
    "rtl/abi3/ot_a3_tile64.sv",
    "rtl/abi3/ot_a3_tree_endpoint_fp32.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_tile64_top.sv",
    "rtl/test/tb_a3_tile64.sv",
    "rtl/test/a3_tile64_harness.cpp",
)
CONTRACT_SOURCES = (
    "runtime/abi3/constants.py",
    "runtime/reference/formats.py",
    "runtime/sim/formats.py",
    "runtime/sim/engines/tensor.py",
    "runtime/sim/engines/reduction.py",
    "docs/CHIP_ARCHITECTURE_DESIGN.md",
)
TOOL_SOURCES = (
    "tools/am_e1_lane_reference.py",
    "tools/build_abi3_lane_vectors.py",
    "tools/build_abi3_tile64_vectors.py",
    "tools/rtl_abi3_tile64_campaign.py",
)
VECTOR_FILES = ("t64_stream.hex", "t64_ws.hex", "t64_act.hex", "t64_act_scale.hex", "t64_case.hex",
                "t64_expect.hex", "t64_meta.hex")

CHECKS_RE = re.compile(r"checks=(\d+)")
MARKER_RE = re.compile(r"^PASS: ABI3 tile64 (.*)$", re.MULTILINE)
RATE_RE = re.compile(
    r"^RATE: case=(\d+) lane_ops=(\d+) products=(\d+) total_cycles=(\d+) window_cycles=(\d+) "
    r"first_retire=(-?\d+) last_retire=(-?\d+) lanes=(\d+) kblocks=(\d+) kblock_cycles_min=(-?\d+) "
    r"kblock_cycles_max=(\d+) kblock_cycles_sum=(\d+)$", re.MULTILINE)
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")
IVERILOG_VERSION_RE = re.compile(r"Icarus Verilog version (\d+)\.(\d+)")
YOSYS_VERSION_RE = re.compile(r"Yosys (\d+)\.(\d+)")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(text: str, build: Path) -> str:
    return (text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>")
            .replace(str(Path.home()), "<HOME>"))


def resolve(name: str, pinned: Path | None) -> Path:
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
    result = subprocess.run([str(executable), *version_args], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {"executable": canonical(str(executable), ROOT), "executable_sha256": sha256_file(executable),
            "version": lines[0] if lines else "no version text"}


def require_versions(tools: dict[str, dict[str, Any]]) -> None:
    match = VERILATOR_VERSION_RE.search(tools["verilator"]["version"])
    if match is None or (int(match.group(1)), int(match.group(2))) < (5, 50):
        raise SystemExit(f"Verilator {PINNED_VERILATOR_VERSION} or newer is required, found "
                         f"{tools['verilator']['version']!r}")
    match = IVERILOG_VERSION_RE.search(tools["iverilog"]["version"])
    if match is None or (int(match.group(1)), int(match.group(2))) < (11, 0):
        raise SystemExit(f"Icarus Verilog {PINNED_IVERILOG_VERSION} or newer is required, found "
                         f"{tools['iverilog']['version']!r}")


def git_state() -> dict[str, Any]:
    def run(*argv: str) -> str:
        return subprocess.run(["git", *argv], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=False).stdout.strip()
    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(status),
            "dirty_paths": sorted(line[3:] for line in status.splitlines()) if status else []}


def run_stage(name: str, command: list[str], build: Path, timeout: int,
              env: dict[str, str] | None = None) -> dict[str, Any]:
    result = subprocess.run(command, cwd=build, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, timeout=timeout, env=env)
    return {"name": name, "command": canonical(shlex.join(command), build),
            "returncode": result.returncode, "log": canonical(result.stdout, build)}


def parse_marker(log: str) -> dict[str, int] | None:
    match = MARKER_RE.search(log)
    if match is None:
        return None
    return {k: int(v) for k, v in (item.split("=") for item in match.group(1).split())}


def parse_rates(log: str) -> list[dict[str, int]]:
    keys = ("case", "lane_ops", "products", "total_cycles", "window_cycles", "first_retire", "last_retire",
            "lanes", "kblocks", "kblock_cycles_min", "kblock_cycles_max", "kblock_cycles_sum")
    return [dict(zip(keys, (int(v) for v in match.groups()))) for match in RATE_RE.finditer(log)]


def simulator_case(name: str, compile_command: list[str], run_command: list[str], build: Path,
                   marker_prefix: str, run_timeout: int) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=4 * 3600)
    executed = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=run_timeout)
    log = compiled["log"] + (executed["log"] if executed else "")
    run_log = executed["log"] if executed else ""
    marker = parse_marker(run_log)
    marker_present = marker is not None and run_log.find(marker_prefix) >= 0
    passed = (compiled["returncode"] == 0 and executed is not None and executed["returncode"] == 0
              and marker_present)
    checks = CHECKS_RE.search(run_log) if executed else None
    return {
        "name": name, "status": "pass" if passed else "fail",
        "compile_command": compiled["command"], "compile_returncode": compiled["returncode"],
        "compile_log_sha256": hashlib.sha256(compiled["log"].encode("utf-8")).hexdigest(),
        "compile_log_tail": "\n".join(compiled["log"].strip().splitlines()[-40:]),
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log_sha256": hashlib.sha256(run_log.encode("utf-8")).hexdigest(),
        "run_log_tail": "\n".join(run_log.strip().splitlines()[-60:]),
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "required_marker_prefix": marker_prefix, "marker_present": marker_present, "marker": marker,
        "checks": int(checks.group(1)) if checks else None, "rates": parse_rates(run_log),
        "first_failure": next((line.strip() for line in run_log.splitlines()
                               if line.strip().startswith(("FAIL:", "FAILURES:"))), None),
    }


def build_vectors(profile: str, adder_stages: int, weight_source: int, out_dir: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    stage = run_stage(f"vectors.{profile}.L{adder_stages}.W{weight_source}",
                      [sys.executable, str(ROOT / "tools/build_abi3_tile64_vectors.py"), "--profile", profile,
                       "--adder-stages", str(adder_stages), "--weight-source", str(weight_source),
                       "--out-dir", str(out_dir)], ROOT, timeout=6 * 3600, env=env)
    if stage["returncode"] != 0:
        raise SystemExit(f"vector build failed ({profile}, L={adder_stages}, W={weight_source}):\n"
                         f"{stage['log'][-4000:]}")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    for name in VECTOR_FILES:
        if sha256_file(out_dir / name) != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    committed_path = MANIFEST_DIR / f"manifest_{profile}_L{adder_stages}_W{weight_source}.json"
    committed = json.loads(committed_path.read_text(encoding="utf-8")) if committed_path.exists() else None
    manifest["_committed_manifest"] = canonical(str(committed_path), ROOT)
    manifest["_committed_manifest_matches"] = (committed is not None
                                               and committed["image_sha256"] == manifest["image_sha256"])
    return manifest


def run_one_build(label: str, profile: str, adder_stages: int, weight_source: int, staging_in_tile: int,
                  build: Path, executables: dict[str, Path]) -> dict[str, Any]:
    vectors_dir = build / f"vectors_{label}"
    manifest = build_vectors(profile, adder_stages, weight_source, vectors_dir)
    marker_prefix = manifest["required_marker_prefix"]
    rtl = [str(ROOT / path) for path in RTL_SOURCES]
    sim_dir = build / f"sim_{label}"
    sim_dir.mkdir(parents=True, exist_ok=True)
    for name in VECTOR_FILES:
        shutil.copy2(vectors_dir / name, sim_dir / name)
    iverilog_compile = [str(executables["iverilog"]), "-g2012", "-s", "tb_a3_tile64",
                        f"-Ptb_a3_tile64.ADDER_STAGES={adder_stages}",
                        f"-Ptb_a3_tile64.WEIGHT_SOURCE={weight_source}",
                        f"-Ptb_a3_tile64.STAGING_IN_TILE={staging_in_tile}",
                        "-o", "t64_sim.vvp", *rtl, str(ROOT / "rtl/test/a3_tile64_top.sv"),
                        str(ROOT / "rtl/test/tb_a3_tile64.sv")]
    verilator_compile = [str(executables["verilator"]), "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
                         "-Wno-DECLFILENAME", "--top-module", "ot_a3_tile64_top",
                         f"-GADDER_STAGES={adder_stages}", f"-GWEIGHT_SOURCE={weight_source}",
                         f"-GSTAGING_IN_TILE={staging_in_tile}", "--Mdir", "obj_t64", *rtl,
                         str(ROOT / "rtl/test/a3_tile64_top.sv"), str(ROOT / "rtl/test/a3_tile64_harness.cpp"),
                         "-CFLAGS", "-std=c++17 -O2", "-j", "8"]
    run_timeout = 12 * 3600 if profile == "full" else 4 * 3600
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(simulator_case, "iverilog", iverilog_compile,
                               [str(executables["vvp"]), "t64_sim.vvp"], sim_dir, marker_prefix, run_timeout),
                   pool.submit(simulator_case, "verilator", verilator_compile,
                               ["./obj_t64/Vot_a3_tile64_top"], sim_dir, marker_prefix, run_timeout)]
        simulators = [future.result() for future in futures]
    agree = (all(s["status"] == "pass" for s in simulators)
             and len({json.dumps(s["marker"], sort_keys=True) for s in simulators}) == 1
             and len({s["checks"] for s in simulators}) == 1
             and len({json.dumps(s["rates"], sort_keys=True) for s in simulators}) == 1)
    return {
        "label": label, "profile": profile, "adder_stages": adder_stages, "weight_source": weight_source,
        "staging_in_tile": staging_in_tile,
        "status": "pass" if agree else "fail", "simulators_agree": agree,
        "vectors": {
            "manifest_sha256": sha256_file(vectors_dir / "manifest.json"),
            "committed_manifest": manifest["_committed_manifest"],
            "committed_manifest_matches": manifest["_committed_manifest_matches"],
            "image_sha256": manifest["image_sha256"], "geometry": manifest["geometry"],
            "totals": manifest["totals"], "case_count": len(manifest["cases"]),
            "column_assignment": manifest["column_assignment"], "stream_layout": manifest["stream_layout"],
            "scale_table_layout": manifest["scale_table_layout"],
            "activation_layout": manifest["activation_layout"], "reference": manifest["reference"],
            "failure_modes": manifest["failure_modes"], "rate_cases": manifest["rate_cases"],
            "cases": [{k: c[k] for k in ("id", "name", "note", "shape", "rows", "cols", "cols_per_lane", "depth",
                                         "kblock", "blocks", "dtype_a", "dtype_b", "group", "scaled_a", "scaled_b",
                                         "block_a", "block_b", "block_rows_b", "out_fp32", "rate", "refused",
                                         "mode_name", "stream_words", "products", "tree_checked", "tree_vectors",
                                         "expected", "output_stage", "extras")}
                      for c in manifest["cases"]],
        },
        "simulators": simulators,
    }


def rates_of(result: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {c["id"]: c for c in result["vectors"]["cases"]}
    rate_cases = {r["case"]: r for r in result["vectors"]["rate_cases"]}
    rows = []
    for sim in result["simulators"]:
        for entry in sim["rates"]:
            case = by_id.get(entry["case"], {})
            rate = rate_cases.get(entry["case"], {})
            window = entry["window_cycles"]
            total = entry["total_cycles"]
            blocks = entry["kblocks"]
            ideal = rate.get("issue_cycles_per_block_ideal")
            rows.append({
                "simulator": sim["name"], "case": entry["case"], "name": case.get("name"),
                "shape": case.get("shape"), "group": case.get("group"), "rows": case.get("rows"),
                "cols_per_lane": case.get("cols_per_lane"), "kblocks": blocks,
                "lane_ops": entry["lane_ops"], "products": entry["products"],
                "window_cycles": window, "total_cycles": total,
                "first_retire_cycle": entry["first_retire"], "last_retire_cycle": entry["last_retire"],
                "lane_ops_per_window_cycle": (entry["lane_ops"] / window) if window else None,
                "lane_ops_per_lane_window_cycle": (entry["lane_ops"] / window / TILE_LANES) if window else None,
                "products_per_window_cycle": (entry["products"] / window) if window else None,
                "lane_ops_per_total_cycle": (entry["lane_ops"] / total) if total else None,
                "kblock_cycles_min": entry["kblock_cycles_min"], "kblock_cycles_max": entry["kblock_cycles_max"],
                "kblock_cycles_mean": (entry["kblock_cycles_sum"] / blocks) if blocks else None,
                "issue_cycles_per_block_ideal": ideal,
                "overhead_cycles_per_block": ((entry["kblock_cycles_sum"] / blocks) - ideal) if (blocks and ideal) else None,
            })
    return rows


YOSYS_INSTANCE_RE = re.compile(r"^\s+(\d+)\s+(\S*ot_a3_lq8\S*)\s*$", re.MULTILINE)
YOSYS_CELLS_RE = re.compile(r"^\s+(\d+) cells\s*$", re.MULTILINE)


def yosys_elaboration(build: Path, yosys: Path) -> dict[str, Any]:
    """Elaborate the tile under the synthesis front end; count the LQ8 instances."""
    script = build / "t64_elab.ys"
    lines = [f"read_verilog -sv {ROOT / p}" for p in RTL_SOURCES]
    lines += ["hierarchy -check -top ot_a3_tile64 -chparam STAGING_IN_TILE 0", "proc",
              "tee -o t64_stat.txt stat -top ot_a3_tile64"]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stage = run_stage("yosys.elaborate", [str(yosys), "-q", "-s", str(script)], build, timeout=3600)
    stat_path = build / "t64_stat.txt"
    stat = stat_path.read_text(encoding="utf-8") if stat_path.exists() else ""
    top_section = stat.split("=== ot_a3_tile64 ===")[-1] if "=== ot_a3_tile64 ===" in stat else ""
    top_section = top_section.split("=== design hierarchy ===")[0]
    instances = sum(int(m.group(1)) for m in YOSYS_INSTANCE_RE.finditer(top_section))
    top_cells = YOSYS_CELLS_RE.search(top_section)
    return {
        "tool": "yosys", "returncode": stage["returncode"], "command": stage["command"],
        "script": canonical(script.read_text(encoding="utf-8"), build),
        "log_sha256": hashlib.sha256(stage["log"].encode("utf-8")).hexdigest(),
        "log_tail": "\n".join(stage["log"].strip().splitlines()[-30:]),
        "lq8_instances_in_top": instances,
        "top_local_generic_cells_after_proc": int(top_cells.group(1)) if top_cells else None,
        "elaborated": stage["returncode"] == 0 and instances == LQ8S,
        "stat_tail": "\n".join(stat.strip().splitlines()[-40:]),
        "note": ("hierarchy + proc under the synthesis front end at STAGING_IN_TILE = 0; this records that the "
                 "tile elaborates and instantiates LQ8S LQ8s, not a cell count or a physical result"),
    }


def run(profile: str, adder_stages: int, build_root: Path | None, with_yosys: bool,
        secondary: bool) -> dict[str, Any]:
    executables = {
        "iverilog": resolve("iverilog", None), "vvp": resolve("vvp", None),
        "verilator": resolve("verilator", TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"),
        "cxx": resolve("g++", None), "python": Path(sys.executable),
    }
    version_flags = {"iverilog": ["-V"], "vvp": ["-V"], "verilator": ["--version"], "cxx": ["--version"],
                     "python": ["--version"]}
    if with_yosys:
        executables["yosys"] = resolve("yosys", TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys")
        version_flags["yosys"] = ["-V"]
    tools = {name: tool_record(path, version_flags[name]) for name, path in executables.items()}
    require_versions(tools)
    git = git_state()

    builds = [("vehicle", profile, adder_stages, 0, 1)]
    if secondary:
        builds += [("arrays_in_top", "quick", adder_stages, 0, 0), ("rom_stream", "quick", adder_stages, 1, 1)]

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-tile64-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=len(builds) + (1 if with_yosys else 0)) as pool:
            yosys_future = pool.submit(yosys_elaboration, build, executables["yosys"]) if with_yosys else None
            build_results = list(pool.map(
                lambda spec: run_one_build(spec[0], spec[1], spec[2], spec[3], spec[4], build, executables), builds))
            elaboration = yosys_future.result() if yosys_future else None

    sources = {path: sha256_file(ROOT / path)
               for path in sorted(RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES)}
    for spec in builds:
        committed = MANIFEST_DIR / f"manifest_{spec[1]}_L{spec[2]}_W{spec[3]}.json"
        if committed.exists():
            sources[canonical(str(committed), ROOT).replace("<ROOT>/", "")] = sha256_file(committed)

    all_pass = all(b["status"] == "pass" for b in build_results)
    manifests_match = all(b["vectors"]["committed_manifest_matches"] for b in build_results)
    primary = build_results[0]

    # -- the measured tile rate and the cycles per K-block ------------------------------------------
    rates_by_build = {b["label"]: rates_of(b) for b in build_results}
    primary_rates = [r for r in rates_by_build["vehicle"] if r["simulator"] == "verilator"] or rates_by_build["vehicle"]
    tile_rate = None
    per_group: dict[str, dict[str, Any]] = {}
    for r in primary_rates:
        if r["lane_ops_per_window_cycle"] is not None:
            tile_rate = r["lane_ops_per_window_cycle"] if tile_rate is None else min(tile_rate, r["lane_ops_per_window_cycle"])
            per_group.setdefault(f"g{r['group']}_{r['shape']}", {
                "case": r["name"], "lane_ops_per_window_cycle": r["lane_ops_per_window_cycle"],
                "products_per_window_cycle": r["products_per_window_cycle"],
                "kblock_cycles_mean": r["kblock_cycles_mean"], "kblock_cycles_min": r["kblock_cycles_min"],
                "kblock_cycles_max": r["kblock_cycles_max"],
                "issue_cycles_per_block_ideal": r["issue_cycles_per_block_ideal"],
                "overhead_cycles_per_block": r["overhead_cycles_per_block"],
            })
    if not all_pass:
        tile_rate = 0.0 if tile_rate is None else tile_rate

    # -- fail-closed modes -----------------------------------------------------------------------------
    mode_table = primary["vectors"]["failure_modes"]
    observed = {name: dict(entry, observed_on=["iverilog", "verilator"] if primary["status"] == "pass" else [])
                for name, entry in mode_table.items()}
    preserved = ("tile_columns", "tile_kblock_value", "tile_kblock_scaled_short_tail",
                 "tile_kblock_block_not_dividing", "tile_out_format", "tile_staging_underrun",
                 "tile_staging_overrun", "tile_act_range", "lane_operand_a_nonfinite", "lane_operand_b_nonfinite",
                 "lane_accumulate_range", "lane_scale_b_reserved", "lq8_stream_width")
    all_present = all(name in mode_table for name in preserved)
    tile_details = {e["error_detail"] for n, e in mode_table.items() if n.startswith("tile_")}
    all_distinct = (all_pass and all_present and tile_details == {18, 19, 20, 21, 22, 23}
                    and all(e["error_code"] != 0 for e in mode_table.values()))

    status = "pass" if (all_pass and manifests_match and tile_rate is not None and tile_rate > 0.0
                        and all_distinct) else "fail"

    return {
        "schema": "opentallas.rtl.abi3_tile64.v1",
        "campaign": "rtl3_abi3_tile64",
        "profile": profile,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "design": {
            "module": "rtl/abi3/ot_a3_tile64.sv",
            "lq8s": LQ8S, "lanes_per_lq8": LANES, "lanes": TILE_LANES,
            "lq8_module": "rtl/abi3/ot_a3_lq8.sv (unchanged; cited by digest in source_sha256)",
            "lane_module": "rtl/abi3/ot_a3_lane_pipelined.sv (unchanged, 7a01ce5; cited by digest in source_sha256)",
            "tree_endpoint": "rtl/abi3/ot_a3_tree_endpoint_fp32.sv, instantiated beside the tile in the top (never inside)",
            "adder_stages": adder_stages, "acc_slots": 8,
            "weight_port": "128 B per cycle: one 1024-bit stream word per tile lane-op cycle in every format",
            "staging": "vehicle ring 2 x 2 KB = 32 stream words (design 2 x 16 KB), SDN write port with credit",
            "activation_fifo": "two slices of rows x 128 / g words plus E8M0 slices, H-tree write port, act_ready_kblocks",
            "partial_port": "64 x binary32 per pass at the lane-local address op_out_base + b x stride + row x cols_per_lane + c",
            "column_assignment": "lane (j, i) owns global column 64 c + 8 j + i",
            "quotient_decision": ("the per-pass quotients stay in the lane's multi-cycle admission unit (7a01ce5); "
                                  "the sequencer owns pass geometry only -- recorded in the tile header and "
                                  "docs/CHIP_ARCHITECTURE_DESIGN.md section 13 item 13"),
            "fault_policy": ("tile refusals (details 18..20) before K-block 0 with zero counters; run-time tile faults "
                             "(21..23) and LQ8 / lane faults evaluated when the K-block completes, the lowest-numbered "
                             "faulting LQ8 and lane reported, no later K-block started"),
            "builds": [{"label": b["label"], "profile": b["profile"], "weight_source": b["weight_source"],
                        "staging_in_tile": b["staging_in_tile"]} for b in build_results],
        },
        "git": git,
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "all_builds_pass": all_pass,
        "vector_manifests_match_committed": manifests_match,
        "bit_identity": {
            "equal": all_pass and manifests_match,
            "basis": ("every partial the tile writes is compared, per lane, per K-block, per element, with the exact "
                      "AM-E1 reference run on that lane's columns restricted to that K-block; every tree root is the "
                      "RE8 endpoint's output over the captured partials in the chained shapes, compared with "
                      "re8_chain (asserted equal to reduction.ordered_sum PAIRWISE_TREE); counters, error class / "
                      "detail / K-block / LQ8 / lane, every LQ8's and lane's class and detail, the unwritten sentinel "
                      "and the lockstep monitor are checked; both checkers must print the same marker and count"),
            "reference": "tools/am_e1_lane_reference.py (element_chain per K-block, re8_chain, tile_output)",
            "checks_per_build": {b["label"]: {s["name"]: s["checks"] for s in b["simulators"]} for b in build_results},
            "markers_per_build": {b["label"]: {s["name"]: s["marker"] for s in b["simulators"]} for b in build_results},
        },
        "measured": {
            "mac_per_tile_cycle": tile_rate,
            "mac_per_lane_cycle": (tile_rate / TILE_LANES) if tile_rate else tile_rate,
            "lanes": TILE_LANES,
            "definition": (
                "lane-ops retired by the tile (the sum of the per-cycle retire count over the 64 lanes) divided by "
                "the clock cycles from the first to the last cycle with a retirement (inclusive) of each rate case, "
                f"as counted by both checkers on the vehicle build at L = {adder_stages}; the minimum over the rate "
                "cases is reported.  This window INCLUDES the per-K-block overhead (admission, drain, handshake), so "
                "it is the tile's rate, not the lane's.  kblock_cycles_*: cycles the sequencer's kblock_active was "
                "high per K-block (from the start pulse to the AND of the eight done pulses), measured; "
                "issue_cycles_per_block_ideal = rows x cols_per_lane x ceil(128 / g) from the geometry; "
                "overhead_cycles_per_block = measured mean minus ideal"),
            "by_case": per_group,
            "rates_by_build": rates_by_build,
        },
        "failure_modes": {
            "all_distinct": all_distinct,
            "policy": ("every fault case is run on both simulators; the tile must report the expected class, detail, "
                       "K-block, LQ8 and lane, every LQ8 and lane its own class and detail, every lane must have "
                       "written exactly the elements the reference predicts for the K-blocks it completed and nothing "
                       "after, and the six tile-level details 18..23 must be pairwise distinct"),
            "preserved_modes": list(preserved),
            "modes": observed,
            "fault_cases_pass_on_both_simulators": all_pass,
        },
        "elaboration": elaboration,
        "tools": tools,
        "source_sha256": sources,
        "builds": build_results,
        "claim_boundary": {
            "establishes": [
                "eight unmodified LQ8s under the tile stream sequencer produce, on both simulators, exactly the "
                "K-block partials the exact AM-E1 reference produces per lane per K-block, over BF16 g = 1, FP8 g = 2 "
                "and MXFP4 g = 4, scaled and unscaled, for the decode, batch, prefill and qualification shapes run",
                "the RE8 endpoint chained over the captured partials produces exactly reduction.py's PAIRWISE_TREE "
                "root for every column of every clean case (K = 4,096: 32 leaves; K = 12,288: 96 leaves)",
                "the tile's rate and its cycles per K-block are measured (see measured)",
                "every tile-level refusal and run-time fault, and every LQ8 / lane fault, traps distinctly and fails closed",
                "the eight LQ8s stayed in lockstep on every cycle of every case (the top's monitor read zero)",
            ],
            "does_not_establish": {
                "physical_realisability": "simulation says nothing about area or timing; results/physical_abi3/asap7/a3_tile64/physical.json is synthesis + STA only and the BLOCKS pilot is results/physical_abi3/asap7/a3_tile64_blocks/pilot.json",
                "output_stage": "no output-stage RTL exists; tile_output (one RNE to BF16 / FP32 pass-through) is recorded per root in the manifest, not checked against RTL",
                "golden_model": "runtime/sim/backend.py's blocked path has not adopted AM-E1; the expectation is the exact reference and reduction.py's ordered_sum on block partials, not the functional simulator's contraction; the gold tokens are not re-established",
                "prefill_schedule": "the lane is row-serial; section 4.5's activation-block-stationary schedule is not in the lane, so the prefill shape streams each K-block's weights once per row",
                "stream_layout": "the ROM plan's pass-granule rule (section 5.1) and the E8M0 scale interleave (section 4.4) are unwritten; the tile assumes the LQ8 issue-order word rule and a separate scale table port",
                "sdn_and_htree": "the bench's SDN and H-tree models sustain 128 B/cycle and one slice per K-block; this is not evidence that the real networks can",
                "tree_span": "one RE8 inside the top combines one tile's partials; the design's tree spans tiles and its hop latency is not modelled",
                "quotients": "the per-pass quotients stay in the lane's admission unit; the per-K-block overhead measured here is what the later lane change (stride interface + configuration double-buffer) would remove",
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("quick", "full"), default="full")
    parser.add_argument("--adder-stages", type=int, default=3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--yosys", action="store_true", help="also record a Yosys elaboration")
    parser.add_argument("--no-secondary", action="store_true",
                        help="skip the STAGING_IN_TILE = 0 and WEIGHT_SOURCE = 1 quick builds")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force to replace it", file=sys.stderr)
        return 2
    summary = run(args.profile, args.adder_stages, args.build_dir, args.yosys, not args.no_secondary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for build in summary["builds"]:
        for sim in build["simulators"]:
            print(f"{build['label']} {sim['name']}: {sim['status'].upper()} checks={sim['checks']}"
                  + (f" first_failure={sim['first_failure']}" if sim["first_failure"] else ""))
    print(f"measured.mac_per_tile_cycle={summary['measured']['mac_per_tile_cycle']} "
          f"failure_modes.all_distinct={summary['failure_modes']['all_distinct']}")
    for key, entry in summary["measured"]["by_case"].items():
        print(f"  {key}: {entry['lane_ops_per_window_cycle']} lane-ops/cycle, K-block cycles mean "
              f"{entry['kblock_cycles_mean']} (ideal issue {entry['issue_cycles_per_block_ideal']}, "
              f"overhead {entry['overhead_cycles_per_block']})")
    if summary["elaboration"]:
        print(f"yosys elaboration: LQ8 instances={summary['elaboration']['lq8_instances_in_top']} "
              f"elaborated={summary['elaboration']['elaborated']}")
    print(f"abi3 tile64 campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
