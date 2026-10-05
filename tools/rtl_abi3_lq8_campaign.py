#!/usr/bin/env python3
"""Run and record the two-simulator campaign for the LQ8 lane block.

The artifact is ``results/rtl/abi3_lq8.json``: the D1 extension to eight
lanes (every block lane produces the same bits as an independent run of the
single qualified lane on the same weight elements), the block rate (eight
lane-ops per cycle in steady state, measured), and the fail-closed modes at
block level (every lane-level mode, on the shared side and on one lane's
column, plus the block's own refusals), all on Icarus Verilog 11 and the
pinned Verilator 5.050 through two independently written checkers that must
print the same marker, the same check count and the same rate lines.

Every number in the artifact is one a run produced.  Tool identity, source
digests and the git state (commit and whether the tree was dirty) are recorded
so the evidence is bound to what produced it.  An optional Yosys 0.68
elaboration of the block records that the netlist holds LANES lane instances;
it is orientation for gate D3, not a physical result.
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
MANIFEST_DIR = ROOT / "testdata/rtl/abi3_lq8"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_lq8.json"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools"))
LANES = 8

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/abi3/ot_a3_lane_pipelined.sv",
    "rtl/abi3/ot_a3_lq8.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_lq8_top.sv",
    "rtl/test/tb_a3_lq8.sv",
    "rtl/test/a3_lq8_harness.cpp",
)
CONTRACT_SOURCES = (
    "runtime/abi3/constants.py",
    "runtime/reference/formats.py",
    "runtime/sim/formats.py",
    "runtime/sim/backend.py",
    "runtime/sim/engines/tensor.py",
    "docs/CHIP_ARCHITECTURE_DESIGN.md",
)
TOOL_SOURCES = (
    "tools/am_e1_lane_reference.py",
    "tools/build_abi3_lane_vectors.py",
    "tools/build_abi3_lq8_vectors.py",
    "tools/rtl_abi3_lq8_campaign.py",
)
VECTOR_FILES = ("lq8_m0.hex", "lq8_m2.hex", "lq8_w.hex", "lq8_ws.hex", "lq8_m1.hex",
                "lq8_m3.hex", "lq8_case.hex", "lq8_expect.hex", "lq8_meta.hex")

CHECKS_RE = re.compile(r"checks=(\d+)")
MARKER_RE = re.compile(r"^PASS: ABI3 lq8 (.*)$", re.MULTILINE)
RATE_RE = re.compile(
    r"^RATE: case=(\d+) lane_ops=(\d+) products=(\d+) total_cycles=(\d+) "
    r"window_cycles=(\d+) first_retire=(-?\d+) last_retire=(-?\d+) lanes=(\d+)$", re.MULTILINE)
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
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
                            timeout=60)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "executable": canonical(str(executable), ROOT),
        "executable_sha256": sha256_file(executable),
        "version": lines[0] if lines else "no version text",
    }


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
    return {
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(status),
        "dirty_paths": sorted(line[3:] for line in status.splitlines()) if status else [],
    }


def run_stage(name: str, command: list[str], build: Path, timeout: int,
              env: dict[str, str] | None = None) -> dict[str, Any]:
    result = subprocess.run(command, cwd=build, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False, timeout=timeout, env=env)
    return {
        "name": name,
        "command": canonical(shlex.join(command), build),
        "returncode": result.returncode,
        "log": canonical(result.stdout, build),
    }


def parse_marker(log: str) -> dict[str, int] | None:
    match = MARKER_RE.search(log)
    if match is None:
        return None
    fields: dict[str, int] = {}
    for item in match.group(1).split():
        key, value = item.split("=")
        fields[key] = int(value)
    return fields


def parse_rates(log: str) -> list[dict[str, int]]:
    keys = ("case", "lane_ops", "products", "total_cycles", "window_cycles",
            "first_retire", "last_retire", "lanes")
    return [dict(zip(keys, (int(v) for v in match.groups())))
            for match in RATE_RE.finditer(log)]


def simulator_case(name: str, compile_command: list[str], run_command: list[str],
                   build: Path, marker_prefix: str) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=3600)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=6 * 3600)
    log = compiled["log"] + (executed["log"] if executed else "")
    run_log = executed["log"] if executed else ""
    marker = parse_marker(run_log)
    marker_present = marker is not None and run_log.find(marker_prefix) >= 0
    passed = (compiled["returncode"] == 0 and executed is not None
              and executed["returncode"] == 0 and marker_present)
    checks = CHECKS_RE.search(run_log) if executed else None
    tail = "\n".join(run_log.strip().splitlines()[-60:])
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log_sha256": hashlib.sha256(compiled["log"].encode("utf-8")).hexdigest(),
        "compile_log_tail": "\n".join(compiled["log"].strip().splitlines()[-40:]),
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log_sha256": hashlib.sha256(run_log.encode("utf-8")).hexdigest(),
        "run_log_tail": tail,
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "required_marker_prefix": marker_prefix,
        "marker_present": marker_present,
        "marker": marker,
        "checks": int(checks.group(1)) if checks else None,
        "rates": parse_rates(run_log),
        "first_failure": next((line.strip() for line in run_log.splitlines()
                               if line.strip().startswith(("FAIL:", "FAILURES:"))), None),
    }


def build_vectors(profile: str, adder_stages: int, out_dir: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    stage = run_stage(
        f"vectors.L{adder_stages}",
        [sys.executable, str(ROOT / "tools/build_abi3_lq8_vectors.py"),
         "--profile", profile, "--adder-stages", str(adder_stages), "--out-dir", str(out_dir)],
        ROOT, timeout=3 * 3600, env=env,
    )
    if stage["returncode"] != 0:
        raise SystemExit(f"vector build failed for L={adder_stages}:\n{stage['log'][-4000:]}")
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    for name in VECTOR_FILES:
        actual = sha256_file(out_dir / name)
        if actual != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    committed_path = MANIFEST_DIR / f"manifest_{profile}_L{adder_stages}.json"
    committed = json.loads(committed_path.read_text(encoding="utf-8")) if committed_path.exists() else None
    manifest["_committed_manifest"] = canonical(str(committed_path), ROOT)
    manifest["_committed_manifest_matches"] = (
        committed is not None and committed["image_sha256"] == manifest["image_sha256"]
    )
    manifest["_build_log"] = stage["log"][-2000:]
    return manifest


def run_one_depth(profile: str, adder_stages: int, build: Path,
                  executables: dict[str, Path]) -> dict[str, Any]:
    vectors_dir = build / f"vectors_L{adder_stages}"
    manifest = build_vectors(profile, adder_stages, vectors_dir)
    marker_prefix = manifest["required_marker_prefix"]
    rtl = [str(ROOT / path) for path in RTL_SOURCES]
    sim_dir = build / f"sim_L{adder_stages}"
    sim_dir.mkdir(parents=True, exist_ok=True)
    for name in VECTOR_FILES:
        shutil.copy2(vectors_dir / name, sim_dir / name)
    iverilog_compile = [
        str(executables["iverilog"]), "-g2012", "-s", "tb_a3_lq8",
        f"-Ptb_a3_lq8.ADDER_STAGES={adder_stages}", f"-Ptb_a3_lq8.LANES={LANES}",
        "-o", "lq8_sim.vvp", *rtl,
        str(ROOT / "rtl/test/a3_lq8_top.sv"),
        str(ROOT / "rtl/test/tb_a3_lq8.sv"),
    ]
    verilator_compile = [
        str(executables["verilator"]), "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
        "-Wno-DECLFILENAME", "--top-module", "ot_a3_lq8_top",
        f"-GADDER_STAGES={adder_stages}", f"-GLANES={LANES}", "--Mdir", "obj_lq8", *rtl,
        str(ROOT / "rtl/test/a3_lq8_top.sv"),
        str(ROOT / "rtl/test/a3_lq8_harness.cpp"),
        "-CFLAGS", "-std=c++17 -O2", "-j", "8",
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(simulator_case, "iverilog", iverilog_compile,
                        [str(executables["vvp"]), "lq8_sim.vvp"], sim_dir, marker_prefix),
            pool.submit(simulator_case, "verilator", verilator_compile,
                        ["./obj_lq8/Vot_a3_lq8_top"], sim_dir, marker_prefix),
        ]
        simulators = [future.result() for future in futures]
    agree = (
        all(s["status"] == "pass" for s in simulators)
        and len({json.dumps(s["marker"], sort_keys=True) for s in simulators}) == 1
        and len({s["checks"] for s in simulators}) == 1
        and len({json.dumps(s["rates"], sort_keys=True) for s in simulators}) == 1
    )
    return {
        "adder_stages": adder_stages,
        "status": "pass" if agree else "fail",
        "simulators_agree": agree,
        "vectors": {
            "manifest_sha256": sha256_file(vectors_dir / "manifest.json"),
            "committed_manifest": manifest["_committed_manifest"],
            "committed_manifest_matches": manifest["_committed_manifest_matches"],
            "image_sha256": manifest["image_sha256"],
            "geometry": manifest["geometry"],
            "totals": manifest["totals"],
            "case_count": len(manifest["cases"]),
            "sweep_products": manifest.get("sweep_products"),
            "column_assignment": manifest["column_assignment"],
            "stream_layout": manifest["stream_layout"],
            "scale_table_layout": manifest["scale_table_layout"],
            "reference": manifest["reference"],
            "failure_modes": manifest["failure_modes"],
            "rate_cases": manifest["rate_cases"],
            "cases": [
                {k: c[k] for k in ("id", "name", "note", "rows", "cols", "cols_per_lane", "depth",
                                   "dtype_a", "dtype_b", "group", "scaled_a", "scaled_b",
                                   "block_rows_b", "out_fp32", "run_reference", "rate",
                                   "block_refused", "products", "stream_words", "mode_name",
                                   "expected", "extras")}
                for c in manifest["cases"]
            ],
        },
        "simulators": simulators,
    }


def rate_from(depth_result: dict[str, Any], manifest_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {c["id"]: c for c in manifest_cases}
    rates: list[dict[str, Any]] = []
    for sim in depth_result["simulators"]:
        for entry in sim["rates"]:
            case = by_id.get(entry["case"], {})
            window = entry["window_cycles"]
            total = entry["total_cycles"]
            lanes = entry["lanes"]
            rates.append({
                "simulator": sim["name"],
                "case": entry["case"],
                "name": case.get("name"),
                "group": case.get("group"),
                "lanes": lanes,
                "lane_ops": entry["lane_ops"],
                "products": entry["products"],
                "window_cycles": window,
                "total_cycles": total,
                "first_retire_cycle": entry["first_retire"],
                "last_retire_cycle": entry["last_retire"],
                "lane_ops_per_window_cycle": (entry["lane_ops"] / window) if window else None,
                "lane_ops_per_lane_window_cycle": (entry["lane_ops"] / window / lanes) if window else None,
                "products_per_window_cycle": (entry["products"] / window) if window else None,
                "lane_ops_per_total_cycle": (entry["lane_ops"] / total) if total else None,
            })
    return rates


YOSYS_INSTANCE_RE = re.compile(r"^\s+(\d+)\s+(\S*ot_a3_lane_pipelined\S*)\s*$", re.MULTILINE)
YOSYS_CELLS_RE = re.compile(r"^\s+(\d+) cells\s*$", re.MULTILINE)


def yosys_elaboration(build: Path, yosys: Path) -> dict[str, Any]:
    """Elaborate the block under the synthesis front end; count lane instances."""
    script = build / "lq8_elab.ys"
    lines = [f"read_verilog -sv {ROOT / p}" for p in RTL_SOURCES]
    lines += [f"hierarchy -check -top ot_a3_lq8 -chparam LANES {LANES}", "proc",
              "tee -o lq8_stat.txt stat -top ot_a3_lq8"]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stage = run_stage("yosys.elaborate", [str(yosys), "-q", "-s", str(script)], build, timeout=3600)
    stat_path = build / "lq8_stat.txt"
    stat = stat_path.read_text(encoding="utf-8") if stat_path.exists() else ""
    # The top module's own section lists its submodule instances by type.
    top_section = stat.split("=== ot_a3_lq8 ===")[-1] if "=== ot_a3_lq8 ===" in stat else ""
    top_section = top_section.split("=== design hierarchy ===")[0]
    instances = sum(int(m.group(1)) for m in YOSYS_INSTANCE_RE.finditer(top_section))
    top_cells = YOSYS_CELLS_RE.search(top_section)
    return {
        "tool": "yosys",
        "returncode": stage["returncode"],
        "command": stage["command"],
        "script": canonical(script.read_text(encoding="utf-8"), build),
        "log_sha256": hashlib.sha256(stage["log"].encode("utf-8")).hexdigest(),
        "log_tail": "\n".join(stage["log"].strip().splitlines()[-30:]),
        "lane_instances_in_top": instances,
        "top_local_generic_cells_after_proc": int(top_cells.group(1)) if top_cells else None,
        "elaborated": stage["returncode"] == 0 and instances == LANES,
        "stat_tail": "\n".join(stat.strip().splitlines()[-40:]),
        "note": ("hierarchy + proc under the synthesis front end; this records that the block "
                 "elaborates and instantiates LANES lanes, not a cell count or a physical result"),
    }


def run(profile: str, depths: list[int], build_root: Path | None, with_yosys: bool) -> dict[str, Any]:
    executables = {
        "iverilog": resolve("iverilog", None),
        "vvp": resolve("vvp", None),
        "verilator": resolve("verilator", TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"),
        "cxx": resolve("g++", None),
        "python": Path(sys.executable),
    }
    version_flags = {"iverilog": ["-V"], "vvp": ["-V"], "verilator": ["--version"],
                     "cxx": ["--version"], "python": ["--version"]}
    if with_yosys:
        executables["yosys"] = resolve("yosys", TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys")
        version_flags["yosys"] = ["-V"]
    tools = {name: tool_record(path, version_flags[name]) for name, path in executables.items()}
    require_versions(tools)
    git = git_state()

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-lq8-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=max(1, len(depths)) + (1 if with_yosys else 0)) as pool:
            yosys_future = pool.submit(yosys_elaboration, build, executables["yosys"]) if with_yosys else None
            depth_results = list(pool.map(
                lambda depth: run_one_depth(profile, depth, build, executables), depths))
            elaboration = yosys_future.result() if yosys_future else None

    sources = {path: sha256_file(ROOT / path)
               for path in sorted(RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES)}
    for depth in depths:
        committed = MANIFEST_DIR / f"manifest_{profile}_L{depth}.json"
        if committed.exists():
            sources[canonical(str(committed), ROOT).replace("<ROOT>/", "")] = sha256_file(committed)

    all_pass = all(d["status"] == "pass" for d in depth_results)
    manifests_match = all(d["vectors"]["committed_manifest_matches"] for d in depth_results)

    # -- D1 extension: bit identity, block lane against the single lane ----------------------
    identity_counts = {}
    reference_counts = {}
    for d in depth_results:
        markers = [s["marker"] for s in d["simulators"] if s["marker"]]
        identity_counts[f"L{d['adder_stages']}"] = markers[0].get("identity") if markers else None
        reference_counts[f"L{d['adder_stages']}"] = markers[0].get("reference_cases") if markers else None
    identity_equal = (all_pass and manifests_match
                      and all(v and v > 0 for v in identity_counts.values())
                      and all(v and v > 0 for v in reference_counts.values()))

    # -- block rate ------------------------------------------------------------------------------
    rates_by_depth = {f"L{d['adder_stages']}": rate_from(d, d["vectors"]["cases"]) for d in depth_results}
    primary_depth = f"L{depths[0]}"
    primary_rates = [r for r in rates_by_depth[primary_depth] if r["simulator"] == "verilator"] or \
                    rates_by_depth[primary_depth]
    block_rate = None
    lane_rate = None
    for r in primary_rates:
        if r["lane_ops_per_window_cycle"] is not None:
            block_rate = r["lane_ops_per_window_cycle"] if block_rate is None else min(block_rate, r["lane_ops_per_window_cycle"])
            lane_rate = r["lane_ops_per_lane_window_cycle"] if lane_rate is None else min(lane_rate, r["lane_ops_per_lane_window_cycle"])
    products_by_group = {}
    for r in primary_rates:
        if r["products_per_window_cycle"] is not None:
            products_by_group[f"g{r['group']}"] = r["products_per_window_cycle"]
    if not all_pass:
        block_rate = 0.0 if block_rate is None else block_rate
        lane_rate = 0.0 if lane_rate is None else lane_rate

    # -- fail-closed modes at block level ---------------------------------------------------------
    mode_table = depth_results[0]["vectors"]["failure_modes"] if depth_results else {}
    observed = {}
    for name, entry in mode_table.items():
        observed[name] = {
            "case": entry["case"], "case_name": entry["name"],
            "error_code": entry["error_code"], "error_detail": entry["error_detail"],
            "error_lane": entry["error_lane"], "detail_name": entry["detail_name"],
            "per_lane_class_detail": entry["lanes"],
            "observed_on": ["iverilog", "verilator"] if all_pass else [],
        }
    detail_pairs = [(e["error_code"], e["error_detail"]) for e in mode_table.values()]
    preserved = ("nonfinite_bf16_operand_a", "nonfinite_bf16_operand_b",
                 "reserved_e4m3fn_operand_a", "reserved_e4m3fn_operand_b",
                 "reserved_e8m0_scale_a", "reserved_e8m0_scale_b",
                 "scale_application_range_a", "scale_application_range_b",
                 "product_range", "accumulate_range", "shape",
                 "block_columns", "block_stream_width")
    all_present = all(name in mode_table for name in preserved)
    all_distinct = (all_pass and all_present and len(set(detail_pairs)) == len(detail_pairs)
                    and all(e["error_code"] != 0 for e in mode_table.values()))

    status = "pass" if (all_pass and manifests_match and identity_equal
                        and block_rate is not None and block_rate >= float(LANES)
                        and all_distinct) else "fail"

    return {
        "schema": "opentallas.rtl.abi3_lq8.v1",
        "campaign": "rtl3_abi3_lq8",
        "profile": profile,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "design": {
            "module": "rtl/abi3/ot_a3_lq8.sv",
            "lanes": LANES,
            "lane_module": "rtl/abi3/ot_a3_lane_pipelined.sv (unchanged; qualified by results/rtl/abi3_pipelined_lane.json)",
            "sequential_reference": "rtl/abi3/ot_a3_mac_lane.sv (untouched; the lane's D1 reference)",
            "adder_stages_run": depths,
            "acc_slots": 8,
            "weight_stream_port": f"{2 * LANES} B per cycle: 2 B per lane per lane-op in every format, sequential from cfg_w_base",
            "weight_scale_port": f"{LANES} B per read, indexed by the lane's own A15 index for its lane-local column",
            "activation_ports": "one 64-bit operand port and one 32-bit E8M0 port, shared by every lane",
            "column_assignment": "lane i owns block columns c * LANES + i",
            "fault_policy": ("a faulting lane stops itself and writes nothing after its faulting pass; the "
                             "other lanes complete; the block reports the lowest-numbered faulting lane's "
                             "class and detail and every lane's beside them; cols not a multiple of LANES "
                             "and a group whose weight codes exceed 2 B are refused before any lane starts"),
        },
        "git": git,
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "all_depths_pass": all_pass,
        "vector_manifests_match_committed": manifests_match,
        "bit_identity": {
            "equal": identity_equal,
            "basis": (
                "every case is run once on the block and then LANES times on the single qualified lane, "
                "once per block lane on that lane's own column-major weight image and lane-local scale "
                "image built from the same weight elements; both checkers compare, element by element, "
                "the output word and the binary32 accumulator of each block lane against its reference "
                "run directly, both against the exact expectation, counters, error classes and details "
                "per lane, the unwritten sentinel on every element no lane was to write, and require the "
                "top's lockstep monitor to read zero; one differing bit fails the marker"),
            "reference": "rtl/abi3/ot_a3_lane_pipelined.sv",
            "identity_element_pairs_per_depth": identity_counts,
            "reference_cases_per_depth": reference_counts,
            "checks_per_depth": {f"L{d['adder_stages']}": {s["name"]: s["checks"] for s in d["simulators"]}
                                 for d in depth_results},
            "markers_per_depth": {f"L{d['adder_stages']}": {s["name"]: s["marker"] for s in d["simulators"]}
                                  for d in depth_results},
            "sweep_products": depth_results[0]["vectors"]["sweep_products"] if depth_results else None,
        },
        "measured": {
            "mac_per_block_cycle": block_rate,
            "mac_per_lane_cycle": lane_rate,
            "lanes": LANES,
            "definition": (
                "lane-ops retired by the block (the sum of the per-cycle retire count) divided by the "
                "clock cycles from the first to the last cycle with a retirement (inclusive) of the "
                f"steady-state case, as counted by both checkers on the L = {depths[0]} build; the "
                "minimum over the suite's rate cases is reported, and the per-lane figure is that "
                f"divided by {LANES}.  The same lane-ops divided by the whole run's cycles is beside it"),
            "products_per_block_cycle_by_group": products_by_group,
            "primary_adder_stages": depths[0],
            "rates_by_depth": rates_by_depth,
        },
        "failure_modes": {
            "all_distinct": all_distinct,
            "policy": (
                "every fault case is run on both simulators; the block must report the expected class, "
                "detail and faulting lane, every lane its own class and detail, each lane must write "
                "exactly the elements of the passes it completed before its fault and nothing after, and "
                "the (class, detail) pairs of the preserved modes must be pairwise distinct"),
            "preserved_modes": list(preserved),
            "modes": observed,
            "fault_cases_pass_on_both_simulators": all_pass,
        },
        "elaboration": elaboration,
        "tools": tools,
        "source_sha256": sources,
        "depths": depth_results,
        "claim_boundary": {
            "establishes": [
                (f"{LANES} lanes under one {2 * LANES}-byte weight stream port and shared activation ports "
                 "produce, on both simulators, exactly the bits that independent runs of the single "
                 "qualified lane produce on the same weight elements, over BF16 g = 1 and the FP8 g = 2 "
                 "and MXFP4 g = 4 group modes, scaled and unscaled"),
                f"the block retires {LANES} lane-ops per cycle in steady state (measured)",
                "every lane-level failure mode traps distinctly at block level, on the shared side and on one lane's column, and the block's own refusals are distinct from them",
                "the lanes stayed in lockstep on every cycle of every case (the top's monitor read zero)",
            ],
            "does_not_establish": {
                "physical_realisability": "simulation says nothing about area, timing or power; gates D3 and D4 need the physical flow",
                "scale_interleave": "section 4.4 interleaves E8M0 scale bytes into the weight stream under a ROM-plan rule it marks as not yet written; the block keeps the scales on a separate table port",
                "k_block_tree": "K_BLOCK = K here; the pairwise tree over K-blocks and the tile sequencer are outside the block",
                "integration": "the block is driven directly by the checkers with ideal one-cycle memories; no staging SRAM, ROM bank or H-tree is modelled",
                "exhaustive_arithmetic": "the sweep is seeded and directed, not exhaustive over the operand space",
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("quick", "full"), default="full")
    parser.add_argument("--adder-stages", default="3,2,1",
                        help="comma-separated adder depths to run; the first is the primary")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--yosys", action="store_true", help="also record a Yosys elaboration")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force to replace it", file=sys.stderr)
        return 2
    depths = [int(v) for v in args.adder_stages.split(",") if v.strip()]
    summary = run(args.profile, depths, args.build_dir, args.yosys)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for depth in summary["depths"]:
        for sim in depth["simulators"]:
            print(f"L={depth['adder_stages']} {sim['name']}: {sim['status'].upper()} checks={sim['checks']}"
                  + (f" first_failure={sim['first_failure']}" if sim["first_failure"] else ""))
    print(f"bit_identity.equal={summary['bit_identity']['equal']} "
          f"measured.mac_per_block_cycle={summary['measured']['mac_per_block_cycle']} "
          f"measured.mac_per_lane_cycle={summary['measured']['mac_per_lane_cycle']} "
          f"failure_modes.all_distinct={summary['failure_modes']['all_distinct']}")
    if summary["elaboration"]:
        print(f"yosys elaboration: lane instances={summary['elaboration']['lane_instances_in_top']} "
              f"elaborated={summary['elaboration']['elaborated']}")
    print(f"abi3 lq8 campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
