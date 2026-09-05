#!/usr/bin/env python3
"""The ORFS BLOCKS assembly pilot for the T64 tile at asap7.

docs/CHIP_ARCHITECTURE_DESIGN.md section 11.1: a flat T64 (about 1.4 M cells
pre-layout) exceeds the pinned flow's ceiling, so the tile is assembled from
hardened LQ8 blocks under the OpenROAD-flow-scripts BLOCKS / generate_abstract
mechanism.  This pilot runs that mechanism as it exists in the pinned
container (openroad/orfs image sha256:af971398d91e...; Makefile lines
100-109, 160-181, 674-682; scripts/generate_abstract.tcl) and records whether
it can do it and how long it takes -- or exactly where it stops.

Two legs, each bounded in wall time:

  ``--leg block``   ``make ... build_macros``: harden ONE ot_a3_lq8 (LANES 8,
                    ADDER_STAGES 3, ACC_SLOTS 8) through synthesis, place and
                    route, and write its abstract (.lef, _typ.lib, 6_final.gds)
                    with write_timing_model / write_abstract_lef.
  ``--leg parent``  ``make ...`` (the default goal): synthesise ot_a3_tile64
                    with ot_a3_lq8 blackboxed by the block's liberty (the
                    tile's LQ8_ABSTRACT = 1 branch instantiates the abstract
                    without parameter overrides, because a liberty cell has
                    none), place the eight abstracts as macros, and route.

The parent's configuration is written to /work/config.mk and the block's to
/work/ot_a3_lq8/config.mk, because ORFS derives the block's config path from
dirname(DESIGN_CONFIG)/<block>/config.mk and requires the block's
DESIGN_NICKNAME to be <parent nickname>_<block> for the parent to find the
abstract under results/<platform>/<nickname>_<block>/<variant>/.

The record is one JSON per pilot (both legs append to it) with every stage's
wall time from the flow's logs, the block's and the parent's metrics from
metadata.json where the flow produced them, the glue cell count and macro
count of the parent, DRC and antenna results, and, when a leg stops, the make
target and the last log lines.  Nothing here edits tools/run_abi3_physical.py.
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
import sys
import time
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORFS_IMAGE = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest")
ORFS_EXPECTED_IMAGE_ID = "sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34"
PLATFORM = "asap7"
PARENT_TOP = "ot_a3_tile64"
BLOCK_TOP = "ot_a3_lq8"
PARENT_NICKNAME = "opentallas_a3_tile64_asap7"
BLOCK_NICKNAME = f"{PARENT_NICKNAME}_{BLOCK_TOP}"
PACKAGES = ("rtl/ot_fp32_rne_pkg.sv", "rtl/abi3/ot_a3_lane_pkg.sv")
BLOCK_SOURCES = PACKAGES + ("rtl/abi3/ot_a3_lane_pipelined.sv", "rtl/abi3/ot_a3_lq8.sv")
PARENT_SOURCES = PACKAGES + ("rtl/abi3/ot_a3_tile64.sv",)
TIME_UNIT_NS = 0.001          # asap7 liberty time unit is 1 ps
OUTPUT_LOAD_FF = 3.898


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list[str], timeout: int) -> tuple[subprocess.CompletedProcess | None, bool]:
    try:
        return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout,
                              check=False), False
    except subprocess.TimeoutExpired as expired:
        stub = subprocess.CompletedProcess(cmd, -1, expired.stdout or "", expired.stderr or "")
        return stub, True


def git_identity() -> dict[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False)
    lines = [line for line in status.stdout.splitlines() if line.strip()]
    dirt = [line for line in lines if not (line.startswith("?? ") and line[3:].startswith("results/"))]
    return {"commit": head.stdout.strip() or None, "worktree_dirty": bool(dirt), "worktree_status": dirt[:50]}


def orfs_identity() -> dict[str, Any]:
    proc, _ = run(["docker", "image", "inspect", ORFS_IMAGE, "--format", "{{.Id}}"], 300)
    image_id = (proc.stdout or "").strip() if proc else None
    proc2, _ = run(["docker", "run", "--rm", ORFS_IMAGE, "bash", "-lc",
                    "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -version 2>/dev/null | head -1; "
                    "yosys -V 2>/dev/null | head -1"], 900)
    return {"image": ORFS_IMAGE, "image_id": image_id, "image_id_matches_pinned": image_id == ORFS_EXPECTED_IMAGE_ID,
            "tool_versions": (proc2.stdout or "").strip().splitlines() if proc2 else []}


def sdc_text(clock_period_ns: float) -> str:
    period_lib = clock_period_ns / TIME_UNIT_NS
    return "\n".join([
        f"set clk_period {period_lib:g}",
        "create_clock -name core_clk -period $clk_period [get_ports clk]",
        "set non_clock_inputs [all_inputs -no_clocks]",
        "set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs",
        "set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]",
        f"set_load {OUTPUT_LOAD_FF:g} [all_outputs]",
        "set_max_fanout 32 [current_design]",
        "set_false_path -from [get_ports rst_n]",
        "",
    ])


def macro_placement_tcl(work: Path, halo: str, lef: Path) -> str:
    """Place the eight abstracts on a regular grid: rows x columns of the block's own LEF size
    plus the halo, anchored at the core's lower-left corner.  ORFS sources this file
    (MACRO_PLACEMENT_TCL) instead of running RTL-MP."""
    size = re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", lef.read_text(encoding="utf-8", errors="ignore"))
    width, height = (float(size.group(1)), float(size.group(2))) if size else (280.0, 280.0)
    gap = float(halo.split()[0])
    lines = ["# eight ot_a3_lq8 abstracts on a 4 x 2 grid, generated by tools/run_abi3_tile64_blocks_pilot.py"]
    for index in range(8):
        col, row = index % 4, index // 4
        x = round(gap + col * (width + gap), 3)
        y = round(gap + row * (height + gap), 3)
        name = f"gen_lq8[{index}].gen_abstract.u_lq8"
        lines.append(f"place_macro -macro_name {{{name}}} -location {{{x} {y}}} -orientation R0")
    return "\n".join(lines) + "\n"


def write_configs(work: Path, clock_period_ns: float, core_utilization: int, place_density: float,
                  halo: str, macro_placement: str | None = None,
                  parent_exports: list[str] | None = None) -> dict[str, str]:
    block_dir = work / BLOCK_TOP
    block_dir.mkdir(parents=True, exist_ok=True)
    (work / "constraint.sdc").write_text(sdc_text(clock_period_ns), encoding="utf-8")
    (block_dir / "constraint.sdc").write_text(sdc_text(clock_period_ns), encoding="utf-8")
    parent = [
        f"export DESIGN_NICKNAME = {PARENT_NICKNAME}",
        f"export DESIGN_NAME = {PARENT_TOP}",
        f"export PLATFORM = {PLATFORM}",
        "export VERILOG_FILES = " + " ".join(f"/src/{s}" for s in PARENT_SOURCES),
        "export VERILOG_DEFINES = -DSYNTHESIS",
        "export SDC_FILE = /work/constraint.sdc",
        f"export BLOCKS = {BLOCK_TOP}",
        "export SYNTH_HIERARCHICAL = 1",
        "export VERILOG_TOP_PARAMS = ACC_SLOTS 8 ADDER_STAGES 3 LANES 8 LQ8S 8 STAGING_IN_TILE 0 LQ8_ABSTRACT 1",
        f"export CORE_UTILIZATION = {core_utilization}",
        "export CORE_ASPECT_RATIO = 1",
        "export CORE_MARGIN = 2",
        f"export PLACE_DENSITY = {place_density}",
        "export PLACE_DENSITY_LB_ADDON = 0.05",
        "export PLACE_PINS_ARGS = -annealing",
        f"export MACRO_PLACE_HALO = {halo}",
        "export GND_NETS_VOLTAGES =",
        "export PWR_NETS_VOLTAGES =",
        "export ASAP7_USE_VT = RVT",
        "export CORNER = TC",
        "export SYNTH_REPEATABLE_BUILD = 1",
        "export LEC_CHECK = 0",
        "export TNS_END_PERCENT = 100",
        "export SKIP_REPORT_METRICS = 0",
        "",
    ]
    block = [
        f"export DESIGN_NICKNAME = {BLOCK_NICKNAME}",
        f"export DESIGN_NAME = {BLOCK_TOP}",
        f"export PLATFORM = {PLATFORM}",
        "export VERILOG_FILES = " + " ".join(f"/src/{s}" for s in BLOCK_SOURCES),
        "export VERILOG_DEFINES = -DSYNTHESIS",
        f"export SDC_FILE = /work/{BLOCK_TOP}/constraint.sdc",
        "export VERILOG_TOP_PARAMS = ACC_SLOTS 8 ADDER_STAGES 3 LANES 8",
        f"export CORE_UTILIZATION = {core_utilization}",
        "export CORE_ASPECT_RATIO = 1",
        "export CORE_MARGIN = 2",
        f"export PLACE_DENSITY = {place_density}",
        "export PLACE_DENSITY_LB_ADDON = 0.05",
        "export PLACE_PINS_ARGS = -annealing",
        "export PDN_TCL = $(PLATFORM_DIR)/openRoad/pdn/BLOCK_grid_strategy.tcl",
        "export ASAP7_USE_VT = RVT",
        "export CORNER = TC",
        "export SYNTH_REPEATABLE_BUILD = 1",
        "export SYNTH_HIERARCHICAL = 0",
        "export LEC_CHECK = 0",
        "export TNS_END_PERCENT = 100",
        "export SKIP_REPORT_METRICS = 0",
        "",
    ]
    for extra in parent_exports or []:
        key, _, value = extra.partition("=")
        parent.insert(-1, f"export {key.strip()} = {value.strip()}")
    if macro_placement:
        lef = work / "results" / PLATFORM / BLOCK_NICKNAME / "base" / f"{BLOCK_TOP}.lef"
        if not lef.is_file():
            raise SystemExit(f"--macro-placement needs the block abstract: {lef} is missing (run --leg block first)")
        (work / "macro_placement.tcl").write_text(macro_placement_tcl(work, halo, lef), encoding="utf-8")
        parent.insert(-1, "export MACRO_PLACEMENT_TCL = /work/macro_placement.tcl")
    (work / "config.mk").write_text("\n".join(parent), encoding="utf-8")
    (block_dir / "config.mk").write_text("\n".join(block), encoding="utf-8")
    return {"parent": "\n".join(parent), "block": "\n".join(block)}


def make_in_container(work: Path, goal: str, log_path: Path, timeout: int) -> dict[str, Any]:
    # A unique container name: on a client-side timeout only THIS container is stopped.  Other
    # tracks run their own ORFS containers from the same image and must not be touched.
    container = f"opentallas-t64-blocks-{goal.split()[0]}-{os.getpid()}-{int(time.time())}"
    cmd = [
        "docker", "run", "--rm", "--name", container,
        "-v", f"{ROOT}:/src:ro",
        "-v", f"{work}:/work",
        "-w", "/OpenROAD-flow-scripts/flow",
        ORFS_IMAGE, "bash", "-lc",
        "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; "
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
        f"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base {goal}",
    ]
    started = time.monotonic()
    proc, timed_out = run(cmd, timeout)
    elapsed = round(time.monotonic() - started, 3)
    text = (proc.stdout or "") + (proc.stderr or "") if proc else ""
    log_path.write_text(text, encoding="utf-8")
    if timed_out:
        # the container keeps running after the client times out; stop this one by its own name
        subprocess.run(["docker", "stop", container], check=False, capture_output=True)
    return {"goal": goal, "container": container,
            "command": " ".join(cmd[:-1]) + " '" + cmd[-1] + "'", "returncode": proc.returncode if proc else None,
            "timed_out": timed_out, "wall_seconds": elapsed, "log": str(log_path),
            "log_sha256": sha256_file(log_path), "log_tail": "\n".join(text.strip().splitlines()[-40:])}


# ORFS prints "Elapsed time: 1:03:07[h:]min:sec" for stages over an hour and
# "Elapsed time: 23:44.10[h:]min:sec" (min:sec.cs) for shorter ones.
ELAPSED_RE = re.compile(r"Elapsed time: (?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\[h:\]min:sec")


def stage_times(logs_dir: Path) -> dict[str, Any]:
    """Per-stage wall time from the flow's logs (each ends with an 'Elapsed time' line)."""
    times: dict[str, float] = {}
    if not logs_dir.is_dir():
        return {}
    for log in sorted(logs_dir.glob("*.log")):
        text = log.read_text(encoding="utf-8", errors="ignore")
        match = None
        for match in ELAPSED_RE.finditer(text):
            pass
        if match:
            hours = int(match.group(1)) if match.group(1) else 0
            times[log.stem] = round(hours * 3600 + int(match.group(2)) * 60 + float(match.group(3)), 2)
    return times


def metrics_of(reports_dir: Path) -> dict[str, Any] | None:
    path = reports_dir / "metadata.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = {
        "synth_cells": "synth__design__instance__count__stdcell",
        "synth_area_um2": "synth__design__instance__area__stdcell",
        "macros": "synth__design__instance__count__macros",
        "placed_cells": "globalplace__design__instance__count__stdcell",
        "final_cells": "finish__design__instance__count__stdcell",
        "final_stdcell_area_um2": "finish__design__instance__area__stdcell",
        "final_macro_count": "finish__design__instance__count__macros",
        "final_macro_area_um2": "finish__design__instance__area__macros",
        "core_area_um2": "finish__design__core__area",
        "utilization": "finish__design__util",
        "setup_ws_lib": "finish__timing__setup__ws",
        "hold_ws_lib": "finish__timing__hold__ws",
        "setup_violations": "finish__timing__drv__setup_violation_count",
        "hold_violations": "finish__timing__drv__hold_violation_count",
        "fmax_hz": "finish__timing__fmax",
        "drc_errors": "detailedroute__route__drc_errors",
        "antenna_violating_nets": "finish__antenna_diodes_count",
        "wirelength_um": "detailedroute__route__wirelength",
    }
    out: dict[str, Any] = {k: data.get(v) for k, v in keys.items()}
    for name in ("setup_ws_lib", "hold_ws_lib"):
        if out.get(name) is not None:
            out[name.replace("_lib", "_ns")] = float(out[name]) * TIME_UNIT_NS
    out["flow_errors"] = {k: v for k, v in data.items() if k.endswith("__flow__errors__count")}
    out["available_keys"] = len(data)
    return out


def leg_record(work: Path, nickname: str) -> dict[str, Any]:
    results_dir = work / "results" / PLATFORM / nickname / "base"
    logs_dir = work / "logs" / PLATFORM / nickname / "base"
    reports_dir = work / "reports" / PLATFORM / nickname / "base"
    produced = {}
    for name in ("1_2_yosys.v", "1_synth.v", "2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_route.odb",
                 "6_final.odb", "6_final.def", "6_final.v", "6_final.gds", "6_final.sdc",
                 f"{BLOCK_TOP}.lef", f"{BLOCK_TOP}_typ.lib"):
        path = results_dir / name
        if path.is_file():
            produced[name] = {"size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
    logs = sorted(p.name for p in logs_dir.glob("*.log")) if logs_dir.is_dir() else []
    last_log = None
    if logs_dir.is_dir():
        candidates = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
        if candidates:
            last = candidates[-1]
            last_log = {"name": last.name, "tail": "\n".join(
                last.read_text(encoding="utf-8", errors="ignore").strip().splitlines()[-30:])}
    return {"results_dir": str(results_dir), "produced": produced, "logs": logs,
            "stage_wall_seconds": stage_times(logs_dir), "metrics": metrics_of(reports_dir), "last_log": last_log}


def abstract_summary(work: Path) -> dict[str, Any]:
    results_dir = work / "results" / PLATFORM / BLOCK_NICKNAME / "base"
    lef = results_dir / f"{BLOCK_TOP}.lef"
    lib = results_dir / f"{BLOCK_TOP}_typ.lib"
    out: dict[str, Any] = {"lef_present": lef.is_file(), "lib_present": lib.is_file()}
    if lef.is_file():
        text = lef.read_text(encoding="utf-8", errors="ignore")
        size = re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", text)
        out["lef_size_um"] = [float(size.group(1)), float(size.group(2))] if size else None
        out["lef_pins"] = len(re.findall(r"^\s*PIN\s+\S+", text, re.M))
        out["lef_obstruction_layers"] = sorted(set(re.findall(r"^\s*LAYER\s+(\S+)\s*;", text, re.M)))
    if lib.is_file():
        text = lib.read_text(encoding="utf-8", errors="ignore")
        out["lib_cells"] = re.findall(r"^\s*cell\s*\(\s*\"?(\w+)\"?\s*\)", text, re.M)
        out["lib_pins"] = len(re.findall(r"^\s*pin\s*\(", text, re.M))
        out["lib_timing_arcs"] = len(re.findall(r"^\s*timing\s*\(", text, re.M))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--view", default="asap7", choices=["asap7"])
    parser.add_argument("--leg", required=True, choices=["block", "parent"])
    parser.add_argument("--clock-period-ns", type=float, default=16.0)
    parser.add_argument("--core-utilization", type=int, default=35)
    parser.add_argument("--place-density", type=float, default=0.60)
    parser.add_argument("--macro-halo", default="5 5")
    parser.add_argument("--parent-export", action="append", default=[], metavar="KEY=VALUE",
                        help="an extra export in the parent config.mk (repeatable), e.g. RTLMP_MAX_LEVEL=1: "
                             "the knobs of the pinned flow's own macro placer, recorded with the attempt")
    parser.add_argument("--macro-placement", default=None,
                        help="place the eight abstracts explicitly instead of leaving them to the RTL-MP "
                             "macro placer: GRID places them on a regular grid inside the core with the "
                             "halo as the spacing (ORFS MACRO_PLACEMENT_TCL)")
    parser.add_argument("--timeout-seconds", type=int, default=3 * 3600)
    parser.add_argument("--record-only", action="store_true",
                        help="rebuild this leg's record from the kept work directory without running the "
                             "flow again; the make block (command, return code, wall time) of the recorded "
                             "run is preserved exactly as it was")
    parser.add_argument("--output", required=True)
    parser.add_argument("--keep-workdir", required=True)
    args = parser.parse_args(argv)

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    work = Path(args.keep_workdir)
    if not work.is_absolute():
        work = ROOT / work
    work.mkdir(parents=True, exist_ok=True)

    record: dict[str, Any] = {}
    if output.is_file():
        record = json.loads(output.read_text(encoding="utf-8"))
    record.setdefault("schema_version", 1)
    record.setdefault("campaign_id", "opentallas-abi3-tile64-blocks-pilot-v1")
    record.setdefault("purpose", "BLOCKS assembly pilot: can the pinned ORFS flow harden one LQ8 as an abstract "
                                 "and assemble a T64 from eight abstract instances, and how long does it take")
    record.setdefault("view", {"name": "asap7", "evidence_class": "predictive academic PDK (not manufacturable)",
                               "platform": PLATFORM, "cell_library": "asap7sc7p5t_RVT", "corner": "TC"})
    record.setdefault("git", git_identity())
    record.setdefault("orfs", orfs_identity())
    record.setdefault("mechanism", {
        "makefile": "ORFS flow/Makefile: BLOCKS -> BLOCK_LEFS / BLOCK_TYP_LIBS under results/<platform>/"
                    "<nickname>_<block>/<variant>/; GENERATE_ABSTRACT_RULE runs generate_abstract with "
                    "DESIGN_CONFIG=dirname(DESIGN_CONFIG)/<block>/config.mk; build_macros hardens the blocks; "
                    "the parent's synthesis reads the block liberty as ADDITIONAL_LIBS so the module is a "
                    "blackbox (read_liberty -lib) and its Verilog body is ignored",
        "abstract": "scripts/generate_abstract.tcl: write_timing_model <block>_typ.lib and write_abstract_lef "
                    "-bloat_occupied_layers <block>.lef from 6_final.odb with the extracted parasitics",
        "parameters": "a liberty blackbox has no parameters, so the parent instantiates ot_a3_lq8 through the "
                      "tile's LQ8_ABSTRACT = 1 generate branch (no overrides; the abstract is LANES 8, "
                      "ADDER_STAGES 3, ACC_SLOTS 8 by the block's own defaults)",
    })
    record.setdefault("sources", {s: {"sha256": sha256_file(ROOT / s)} for s in sorted(set(BLOCK_SOURCES + PARENT_SOURCES))})
    record.setdefault("target_clock_period_ns", args.clock_period_ns)
    record.setdefault("bound_seconds_per_leg", args.timeout_seconds)
    configs = write_configs(work, args.clock_period_ns, args.core_utilization, args.place_density,
                            args.macro_halo, args.macro_placement, args.parent_export)
    record["configs"] = configs
    record.setdefault("legs", {})

    started = datetime.now(timezone.utc)
    previous = record.get("legs", {}).get(args.leg, {})
    if args.record_only and not previous.get("make"):
        raise SystemExit(f"--record-only: no recorded {args.leg} leg to rebuild in {output}")
    if args.leg == "block":
        goal = "build_macros"
        make = (previous["make"] if args.record_only
                else make_in_container(work, goal, work / "orfs_block.log", args.timeout_seconds))
        leg = {"started_at": started.isoformat(), "make": make, "block": leg_record(work, BLOCK_NICKNAME),
               "abstract": abstract_summary(work)}
        leg["completed"] = bool(leg["abstract"]["lef_present"] and leg["abstract"]["lib_present"]
                                and make["returncode"] == 0)
        if not leg["completed"]:
            leg["stopped_at"] = {"make_target": goal, "timed_out": make["timed_out"],
                                 "last_log": leg["block"]["last_log"]}
        record["legs"]["block"] = leg
    else:
        goal = "finish metadata-generate"
        make = (previous["make"] if args.record_only
                else make_in_container(work, goal, work / "orfs_parent.log", args.timeout_seconds))
        leg = {"started_at": started.isoformat(), "make": make, "parent": leg_record(work, PARENT_NICKNAME),
               "block_abstract_used": abstract_summary(work)}
        metrics = leg["parent"]["metrics"] or {}
        leg["completed"] = bool(make["returncode"] == 0 and metrics.get("final_cells") is not None)
        if leg["completed"]:
            leg["assembly"] = {
                "macro_count": metrics.get("final_macro_count"),
                "macros_are": "eight ot_a3_lq8 abstracts (the vehicle's datapath array), NOT the memory system "
                              "gate G2's statement means; the staging and activation arrays are outside the tile "
                              "(STAGING_IN_TILE = 0) and no memory macro is placed",
                "glue_cells": metrics.get("final_cells"),
                "glue_stdcell_area_um2": metrics.get("final_stdcell_area_um2"),
                "macro_area_um2": metrics.get("final_macro_area_um2"),
                "drc_errors": metrics.get("drc_errors"),
                "antenna_violating_nets": metrics.get("antenna_violating_nets"),
                "setup_ws_ns": metrics.get("setup_ws_ns"), "hold_ws_ns": metrics.get("hold_ws_ns"),
                "fmax_hz": metrics.get("fmax_hz"),
            }
        else:
            leg["stopped_at"] = {"make_target": goal, "timed_out": make["timed_out"],
                                 "last_log": leg["parent"]["last_log"]}
        leg["knobs"] = {"core_utilization": args.core_utilization, "place_density": args.place_density,
                        "macro_halo": args.macro_halo, "clock_period_ns": args.clock_period_ns,
                        "macro_placement": args.macro_placement, "parent_exports": list(args.parent_export)}
        # Every parent attempt is kept: the assembly's floorplan knobs are exactly what a pilot
        # is for, and an attempt that stops is evidence, not a draft to be overwritten.
        attempts = record["legs"].setdefault("parent_attempts", [])
        if record["legs"].get("parent") is not None and not args.record_only:
            attempts.append(record["legs"]["parent"])
        record["legs"]["parent"] = leg
    if args.record_only:
        record["legs"][args.leg]["started_at"] = previous.get("started_at", leg["started_at"])
        record["legs"][args.leg]["completed_at"] = previous.get("completed_at")
        record["legs"][args.leg]["wall_seconds"] = previous.get("wall_seconds")
        record["legs"][args.leg]["record_rebuilt_at"] = datetime.now(timezone.utc).isoformat()
    else:
        record["legs"][args.leg]["completed_at"] = datetime.now(timezone.utc).isoformat()
        record["legs"][args.leg]["wall_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 3)

    block_done = record["legs"].get("block", {}).get("completed", False)
    parent_done = record["legs"].get("parent", {}).get("completed", False)
    record["status"] = ("assembled" if (block_done and parent_done) else
                        ("block_hardened" if block_done else "stopped"))
    record["claim_boundary"] = {
        "establishes": [
            "whether the pinned ORFS BLOCKS mechanism hardens ot_a3_lq8 as an abstract and assembles ot_a3_tile64 "
            "from eight abstract instances, with the wall time of every stage that ran",
        ],
        "does_not_establish": {
            "gate_g2": "the parent's macros are LQ8 abstracts, not the memory system; a G2 record needs the memory "
                       "abstracts and the microsequencer in one routed netlist",
            "timing": "the block's timing at 16 ns is the LQ8's own (previously 0.47 ns short); the parent's timing "
                      "through the abstract's liberty is reported as the flow reports it",
            "tile_rtl": "the assembled netlist is the tile's control and datapath glue around the abstracts; its "
                        "function is established by results/rtl/abi3_tile64.json, not by this pilot",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    leg = record["legs"][args.leg]
    print(f"leg={args.leg} completed={leg['completed']} wall={leg['wall_seconds']} s "
          f"returncode={leg['make']['returncode']} timed_out={leg['make']['timed_out']}")
    if not leg["completed"]:
        print(f"stopped at make target {leg['stopped_at']['make_target']}; last log: "
              f"{(leg['stopped_at']['last_log'] or {}).get('name')}")
    print(f"status={record['status']} -> {output}")
    return 0 if leg["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
