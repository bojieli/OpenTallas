#!/usr/bin/env python3
"""Physical characterisation driver for OpenTallas ABI 3.0 RTL blocks.

Runs one named RTL top module through one named technology view:

  * ``synth``  -- pinned Yosys + pinned ABC map to the view's standard-cell
                  liberty and report cell count / cell area / sequential area /
                  macro count.
  * ``sta``    -- pinned OpenSTA pre-layout static timing on the mapped
                  netlist and report WNS / TNS / hold WNS / Fmax.
  * ``pnr``    -- full place-and-route through the pinned OpenROAD-flow-scripts
                  container, reporting routed wire length, via count, DRC and
                  antenna violation counts.  Only for views whose ``pnr``
                  platform is populated.

Every recorded number comes from a tool this script actually invoked.  Nothing
is estimated, scaled or interpolated.  Output is canonical JSON and the driver
fails closed if the output path already exists unless ``--force`` is given.

Reproduce, from the repository root::

    python3 tools/run_abi3_physical.py --view sky130hd --block reduction_s8_g2 \\
        --clock-period-ns 20 --stages synth,sta \\
        --output results/physical_abi3/sky130hd/reduction_s8_g2/physical.json
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN_ID = "opentallas-abi3-physical-v1"
SCHEMA_VERSION = 1

TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools"))
YOSYS = TOOLS_ROOT / "yosys-0.68/bin/yosys"
YOSYS_ABC = TOOLS_ROOT / "yosys-0.68/bin/yosys-abc"
STA = TOOLS_ROOT / "opensta-be771a0/bin/sta"

PDK_FULL_ROOT = Path(
    os.environ.get("OPENTALLAS_PDK_FULL_ROOT", Path.home() / ".local/opentallas-pdk-full")
)
PDK_ASAP7_ROOT = Path(
    os.environ.get("OPENTALLAS_PDK_ASAP7_ROOT", Path.home() / ".local/opentallas-pdk-asap7")
)

SKY130_HD = PDK_FULL_ROOT / "sky130A/libs.ref/sky130_fd_sc_hd"
ASAP7_NLDM = PDK_ASAP7_ROOT / "lib/NLDM"

ORFS_IMAGE = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest")
ORFS_EXPECTED_IMAGE_ID = (
    "sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34"
)


class FlowError(RuntimeError):
    """Raised when a stage cannot produce a trustworthy result."""


# --------------------------------------------------------------------------
# Technology views
# --------------------------------------------------------------------------
#
# ``liberty`` files are the exact library the local pinned Yosys/OpenSTA lane
# reads.  ``pnr`` describes the OpenROAD-flow-scripts platform used for the
# place-and-route lane; that lane reads the platform files baked into the
# container image, which are NOT the same files as ``liberty`` (see
# docs/ABI3_PHYSICAL_VIEWS.md).

VIEWS: dict[str, dict[str, Any]] = {
    "sky130hd": {
        "description": (
            "SkyWater SKY130 high-density standard cells; open manufacturable "
            "130 nm foundry PDK.  Mature implementation view."
        ),
        "evidence_class": "mature open foundry PDK (manufacturable)",
        "node_nm": 130,
        "predictive": False,
        "pdk_lock": "configs/pdk/sky130_full_physical_lock.json",
        "cell_library": "sky130_fd_sc_hd",
        "default_corner": "tt",
        # Liberty time unit is 1 ns and capacitance unit is 1 pF.
        "time_unit_ns": 1.0,
        "cap_unit_ff": 1000.0,
        "output_load_ff": 5.0,
        "corners": {
            "tt": {
                "liberty": [SKY130_HD / "lib/sky130_fd_sc_hd__tt_025C_1v80.lib"],
                "voltage_v": 1.80,
                "temperature_c": 25.0,
                "process": "typical",
            },
            "ss": {
                "liberty": [SKY130_HD / "lib/sky130_fd_sc_hd__ss_100C_1v60.lib"],
                "voltage_v": 1.60,
                "temperature_c": 100.0,
                "process": "slow",
            },
            "ss_lv": {
                "liberty": [SKY130_HD / "lib/sky130_fd_sc_hd__ss_n40C_1v28.lib"],
                "voltage_v": 1.28,
                "temperature_c": -40.0,
                "process": "slow, extreme low voltage",
            },
            "ff": {
                "liberty": [SKY130_HD / "lib/sky130_fd_sc_hd__ff_n40C_1v95.lib"],
                "voltage_v": 1.95,
                "temperature_c": -40.0,
                "process": "fast",
            },
        },
        "dff_liberty_corner_relative": "lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
        "dont_use": [
            "sky130_fd_sc_hd__probe_p_8",
            "sky130_fd_sc_hd__probec_p_8",
            "sky130_fd_sc_hd__lpflow_*",
        ],
        "pnr": {
            "platform": "sky130hd",
            "extra_config": {},
            # sky130hd ships a single tt liberty; ORFS has no corner switch.
            "corner_env": None,
        },
    },
    "asap7": {
        "description": (
            "ASAP7 7 nm predictive FinFET academic PDK (RVT), as distributed "
            "inside the pinned OpenROAD-flow-scripts image.  Predictive view."
        ),
        "evidence_class": "predictive academic PDK (not manufacturable)",
        "node_nm": 7,
        "predictive": True,
        "pdk_lock": "configs/pdk/asap7_local_liberty_lock.json",
        "cell_library": "asap7sc7p5t_RVT",
        "default_corner": "TT",
        # Liberty time unit is 1 ps and capacitance unit is 1 fF.
        "time_unit_ns": 0.001,
        "cap_unit_ff": 1.0,
        "output_load_ff": 3.898,
        "corners": {
            "TT": {
                "liberty": [
                    ASAP7_NLDM / "asap7sc7p5t_AO_RVT_TT_nldm_211120.lib",
                    ASAP7_NLDM / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib",
                    ASAP7_NLDM / "asap7sc7p5t_OA_RVT_TT_nldm_211120.lib",
                    ASAP7_NLDM / "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
                    ASAP7_NLDM / "asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib",
                ],
                "voltage_v": 0.70,
                "temperature_c": 0.0,
                "process": "typical",
            },
        },
        "dff_liberty_corner_relative": "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
        "dont_use": ["*x1p*_ASAP7*", "*xp*_ASAP7*", "SDF*", "ICG*"],
        "pnr": {
            "platform": "asap7",
            "extra_config": {"ASAP7_USE_VT": "RVT"},
            "corner_env": "TC",
        },
    },
}


# --------------------------------------------------------------------------
# Design blocks
# --------------------------------------------------------------------------

BLOCKS: dict[str, dict[str, Any]] = {
    "reduction_s8_g2": {
        "top": "ot_reduction_endpoint",
        "sources": ["rtl/ot_reduction_tree.sv"],
        "parameters": {"DATA_W": 32, "GROUPS": 2, "SOURCES": 8, "TAG_W": 16},
        "clock_port": "clk",
        "false_path_from_ports": ["rst_n"],
        "description": (
            "Eight-source, two-group tagged deterministic reduction endpoint."
        ),
    },
    "add_bf16_sram_engine": {
        "top": "ot_ta_add_bf16_sram_engine",
        "sources": [
            "rtl/ot_ta_add_bf16_sram_engine.sv",
            "rtl/ot_ta_command_decoder.sv",
            "rtl/ot_bf16_add_rne.sv",
            "rtl/ot_ta_add_bf16_executor.sv",
        ],
        "parameters": {},
        "clock_port": "clk",
        "false_path_from_ports": ["rst_n"],
        "description": (
            "Memory-bound ADD_BF16 stream executor: command decode, RNE bf16 "
            "adder and ordered SRAM read/write control.  SRAM arrays are "
            "external, so the block maps to standard cells only."
        ),
    },
}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 7200) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc


def require_success(proc: subprocess.CompletedProcess, what: str) -> None:
    if proc.returncode != 0:
        tail = (proc.stdout or "")[-3000:] + "\n" + (proc.stderr or "")[-3000:]
        raise FlowError(f"{what} failed with exit {proc.returncode}:\n{tail}")


def tool_identity(path: Path, version_args: list[str]) -> dict[str, Any]:
    if not path.is_file():
        raise FlowError(f"pinned tool missing: {path}")
    proc = run([str(path), *version_args], timeout=120)
    text = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
    version = ""
    for line in text:
        if line.strip():
            version = line.strip()
            break
    return {
        "path": str(path),
        "version": version,
        "sha256": sha256_file(path),
    }


def git_identity() -> dict[str, Any]:
    head = run(["git", "rev-parse", "HEAD"])
    status = run(["git", "status", "--porcelain"])
    return {
        "commit": (head.stdout or "").strip() or None,
        "worktree_dirty": bool((status.stdout or "").strip()),
    }


def canonical_dump(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Liberty scanning (cell area + sequential classification)
# --------------------------------------------------------------------------

_CELL_SPLIT = re.compile(r"\n\s*cell\s*\(\s*\"?([A-Za-z0-9_./\\\[\]-]+)\"?\s*\)\s*\{")
_AREA_RE = re.compile(r"\n\s*area\s*:\s*([0-9.eE+-]+)\s*;")
_SEQ_RE = re.compile(r"\n\s*(?:ff|ff_bank|latch|latch_bank)\s*\(")


def scan_liberty(paths: list[Path]) -> dict[str, dict[str, Any]]:
    """Return {cell_name: {"area": float, "sequential": bool}} for the library.

    Cells are top-level groups in every liberty file used here, so splitting on
    the ``cell (NAME) {`` header is sufficient to bound each cell's body.
    """
    cells: dict[str, dict[str, Any]] = {}
    for path in paths:
        text = path.read_text(errors="ignore")
        matches = list(_CELL_SPLIT.finditer(text))
        for index, match in enumerate(matches):
            name = match.group(1)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end(): end]
            area_match = _AREA_RE.search("\n" + body)
            cells[name] = {
                "area": float(area_match.group(1)) if area_match else 0.0,
                "sequential": bool(_SEQ_RE.search("\n" + body)),
            }
    return cells


def expand_dont_use(patterns: list[str], cells: dict[str, dict[str, Any]]) -> list[str]:
    matched = {
        name
        for name in cells
        if any(fnmatch.fnmatch(name, pattern) for pattern in patterns)
    }
    return sorted(matched)


# --------------------------------------------------------------------------
# Netlist normalisation
# --------------------------------------------------------------------------

_SIGNED_RE = re.compile(r"\b(input|output|inout|wire|reg)\s+signed\b")


def normalise_netlist(source: Path, target: Path) -> int:
    """Strip ``signed`` from declarations; OpenSTA's Verilog reader rejects it.

    This is a declaration-attribute-only edit on a structural gate netlist: it
    removes no cells, nets, ports or connectivity.
    """
    text = source.read_text(encoding="utf-8")
    normalised, count = _SIGNED_RE.subn(r"\1", text)
    target.write_text(normalised, encoding="utf-8")
    return count


# --------------------------------------------------------------------------
# Stage: synthesis
# --------------------------------------------------------------------------


# Summary rows emitted by ``stat`` that are not standard cells.
_STAT_SUMMARY_ROWS = {
    "wires",
    "wire",
    "bits",
    "ports",
    "cells",
    "memories",
    "processes",
}
_STAT_CELL_RE = re.compile(
    r"^\s+(\d+)\s+(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+(\S+)\s*$"
)


def parse_stat(text: str) -> dict[str, Any]:
    """Parse ``stat -liberty`` output into per-cell-type counts and areas.

    ``stat`` prints summary rows (``wires``, ``ports``, ``cells`` ...) whose
    area column is ``-``; those are skipped, as is the aggregate ``cells`` row.
    """
    per_cell: dict[str, dict[str, float]] = {}
    chip_area = None
    for line in text.splitlines():
        area_match = re.match(
            r"\s*Chip area for module '\\?(\S+)':\s*([0-9.eE+-]+)", line
        )
        if area_match:
            chip_area = float(area_match.group(2))
            continue
        cell_match = _STAT_CELL_RE.match(line)
        if cell_match:
            name = cell_match.group(3)
            if name in _STAT_SUMMARY_ROWS:
                continue
            per_cell[name] = {
                "count": int(cell_match.group(1)),
                "area": float(cell_match.group(2)),
            }
    return {"per_cell": per_cell, "chip_area_um2": chip_area}


def run_synthesis(
    view: dict[str, Any],
    corner: dict[str, Any],
    block: dict[str, Any],
    work: Path,
    clock_period_ns: float,
    dont_use: list[str],
) -> dict[str, Any]:
    liberty = [Path(p) for p in corner["liberty"]]
    for path in liberty:
        if not path.is_file():
            raise FlowError(f"liberty file missing: {path}")

    dff_lib = None
    relative = view["dff_liberty_corner_relative"]
    for path in liberty:
        if str(path).endswith(relative) or path.name == Path(relative).name:
            dff_lib = path
    if dff_lib is None:
        dff_lib = liberty[0]

    sources = [ROOT / s for s in block["sources"]]
    for path in sources:
        if not path.is_file():
            raise FlowError(f"RTL source missing: {path}")

    chparam = "".join(
        f" -chparam {name} {value}" for name, value in sorted(block["parameters"].items())
    )
    liberty_args = "".join(f" -liberty {path}" for path in liberty)
    dont_use_args = "".join(f" -dont_use {name}" for name in dont_use)
    # ABC's delay target is expressed in picoseconds regardless of the library.
    delay_target_ps = clock_period_ns * 1000.0

    raw_netlist = work / "mapped.raw.v"
    stat_path = work / "stat.txt"
    script = work / "synth.ys"
    script.write_text(
        "\n".join(
            [
                *(f"read_verilog -sv {path}" for path in sources),
                f"hierarchy -check -top {block['top']}{chparam}",
                f"synth -top {block['top']} -flatten",
                f"dfflibmap -liberty {dff_lib}",
                f"abc{liberty_args}{dont_use_args} -D {delay_target_ps:g}",
                "setundef -zero",
                "splitnets -ports",
                "opt_clean -purge",
                f"tee -o {stat_path} stat{liberty_args}",
                f"write_verilog -noattr {raw_netlist}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    proc = run([str(YOSYS), "-s", str(script)], timeout=7200)
    require_success(proc, "yosys synthesis")
    (work / "yosys.log").write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    if not raw_netlist.is_file():
        raise FlowError("yosys produced no mapped netlist")

    stat = parse_stat(stat_path.read_text(encoding="utf-8"))
    cells = scan_liberty(liberty)

    total_cells = 0
    total_area = 0.0
    seq_cells = 0
    seq_area = 0.0
    macro_cells = 0
    unknown: list[str] = []
    for name, info in sorted(stat["per_cell"].items()):
        total_cells += info["count"]
        total_area += info["area"]
        entry = cells.get(name)
        if entry is None:
            macro_cells += info["count"]
            unknown.append(name)
            continue
        if entry["sequential"]:
            seq_cells += info["count"]
            seq_area += info["area"]

    netlist = work / "mapped.v"
    stripped = normalise_netlist(raw_netlist, netlist)

    return {
        "netlist": netlist,
        "record": {
            "cell_count": total_cells,
            "cell_area_um2": round(total_area, 6),
            "chip_area_um2": stat["chip_area_um2"],
            "sequential_cell_count": seq_cells,
            "sequential_area_um2": round(seq_area, 6),
            "combinational_cell_count": total_cells - seq_cells - macro_cells,
            "macro_count": macro_cells,
            "unmapped_cell_types": unknown,
            "cell_types_used": len(stat["per_cell"]),
            "abc_delay_target_ps": delay_target_ps,
            "dont_use_cell_count": len(dont_use),
            "netlist_normalization": {
                "signed_declarations_stripped": stripped,
                "raw_netlist_sha256": sha256_file(raw_netlist),
                "normalized_netlist_sha256": sha256_file(netlist),
            },
        },
    }


# --------------------------------------------------------------------------
# Stage: static timing
# --------------------------------------------------------------------------


def run_sta(
    view: dict[str, Any],
    corner: dict[str, Any],
    block: dict[str, Any],
    work: Path,
    netlist: Path,
    clock_period_ns: float,
) -> dict[str, Any]:
    time_unit_ns = view["time_unit_ns"]
    period_lib = clock_period_ns / time_unit_ns
    load_lib = view["output_load_ff"] / view["cap_unit_ff"]

    false_paths = "\n".join(
        f"set_false_path -from [get_ports {port}]"
        for port in block["false_path_from_ports"]
    )
    sdc = work / "constraint.sdc"
    sdc.write_text(
        "\n".join(
            [
                f"set clk_period {period_lib:g}",
                f"create_clock -name core_clk -period $clk_period [get_ports {block['clock_port']}]",
                "set non_clock_inputs [all_inputs -no_clocks]",
                "set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs",
                "set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]",
                f"set_load {load_lib:g} [all_outputs]",
                "set_max_fanout 32 [current_design]",
                false_paths,
                "",
            ]
        ),
        encoding="utf-8",
    )

    script = work / "sta.tcl"
    script.write_text(
        "\n".join(
            [
                *(f"read_liberty {path}" for path in corner["liberty"]),
                f"read_verilog {netlist}",
                f"link_design {block['top']}",
                f"source {sdc}",
                'puts "OT_WNS [sta::worst_slack -max]"',
                'puts "OT_TNS [sta::total_negative_slack -max]"',
                'puts "OT_HOLD_WNS [sta::worst_slack -min]"',
                'puts "OT_SETUP_VIOL [llength [find_timing_paths -path_delay max -slack_max 0 -group_count 100000]]"',
                'puts "OT_HOLD_VIOL [llength [find_timing_paths -path_delay min -slack_max 0 -group_count 100000]]"',
                f"report_checks -path_delay max -digits 4 -group_count 1 > {work / 'setup_path.rpt'}",
                f"report_checks -path_delay min -digits 4 -group_count 1 > {work / 'hold_path.rpt'}",
                "exit",
                "",
            ]
        ),
        encoding="utf-8",
    )

    proc = run([str(STA), "-no_init", "-exit", str(script)], timeout=7200)
    require_success(proc, "OpenSTA")
    text = (proc.stdout or "") + (proc.stderr or "")
    (work / "sta.log").write_text(text, encoding="utf-8")

    def grab(tag: str) -> float:
        match = re.search(rf"^{tag}\s+(-?[0-9.eE+-]+)\s*$", text, re.M)
        if not match:
            raise FlowError(f"OpenSTA did not report {tag}")
        return float(match.group(1))

    wns_lib = grab("OT_WNS")
    tns_lib = grab("OT_TNS")
    hold_lib = grab("OT_HOLD_WNS")
    setup_viol = int(grab("OT_SETUP_VIOL"))
    hold_viol = int(grab("OT_HOLD_VIOL"))

    wns_ns = wns_lib * time_unit_ns
    critical_path_ns = clock_period_ns - wns_ns
    if critical_path_ns <= 0:
        raise FlowError("non-positive critical path; STA result is not usable")

    return {
        "clock_period_ns": clock_period_ns,
        "sdc_clock_period_library_units": period_lib,
        "library_time_unit_ns": time_unit_ns,
        "setup_wns_ns": wns_ns,
        "setup_tns_ns": tns_lib * time_unit_ns,
        "hold_wns_ns": hold_lib * time_unit_ns,
        "setup_violating_paths": setup_viol,
        "hold_violating_paths": hold_viol,
        "timing_met": wns_ns >= 0.0,
        "critical_path_ns": critical_path_ns,
        "fmax_hz": 1e9 / critical_path_ns,
        "fmax_definition": (
            "1 / (target clock period - setup WNS) at this target period.  Note "
            "the SDC derives input/output delay as 20% of the clock period, so "
            "for an I/O-bounded path this quantity varies with the target "
            "period; use fmax_search for a period-independent figure."
        ),
        "raw_library_units": {
            "setup_wns": wns_lib,
            "setup_tns": tns_lib,
            "hold_wns": hold_lib,
        },
    }


def search_fmax(
    view: dict[str, Any],
    corner: dict[str, Any],
    block: dict[str, Any],
    work: Path,
    netlist: Path,
    start_period_ns: float,
    tolerance: float = 0.001,
    max_iterations: int = 40,
) -> dict[str, Any]:
    """Bisect the clock period for the shortest period that still meets setup.

    The mapped netlist is held fixed; only the SDC period is varied.  This is
    period-independent, unlike ``1 / (period - WNS)``, because the SDC scales
    input and output delay with the clock period.
    """
    evaluations: list[dict[str, float]] = []

    def wns_at(period_ns: float) -> float:
        stage = work / f"fmax_{period_ns:.6f}"
        stage.mkdir(parents=True, exist_ok=True)
        result = run_sta(view, corner, block, stage, netlist, period_ns)
        evaluations.append(
            {"clock_period_ns": period_ns, "setup_wns_ns": result["setup_wns_ns"]}
        )
        return result["setup_wns_ns"]

    # Establish a period that meets timing (hi) and one that does not (lo).
    hi = start_period_ns
    iterations = 0
    while wns_at(hi) < 0.0:
        hi *= 1.5
        iterations += 1
        if iterations > 20:
            raise FlowError("could not find a clock period that meets setup timing")
    lo = hi / 1.5 if iterations else hi / 2.0
    while wns_at(lo) >= 0.0:
        hi = lo
        lo /= 2.0
        iterations += 1
        if iterations > 40 or lo < 1e-4:
            break

    for _ in range(max_iterations):
        if (hi - lo) / hi <= tolerance:
            break
        mid = 0.5 * (lo + hi)
        if wns_at(mid) >= 0.0:
            hi = mid
        else:
            lo = mid

    return {
        "min_clock_period_ns": hi,
        "fmax_hz": 1e9 / hi,
        "method": (
            "bisection on the SDC clock period with the mapped netlist held "
            "fixed; reported period is the smallest evaluated period with "
            "setup WNS >= 0"
        ),
        "relative_tolerance": tolerance,
        "evaluations": len(evaluations),
        "search_trace": sorted(evaluations, key=lambda item: item["clock_period_ns"]),
    }


# --------------------------------------------------------------------------
# Stage: place-and-route via OpenROAD-flow-scripts
# --------------------------------------------------------------------------

PNR_ARTIFACTS_LIGHT = [
    "config.mk",
    "constraint.sdc",
    "metadata.json",
    "1_2_yosys.v",
    "6_final.v",
    "6_finish.rpt",
    "5_route_drc.rpt",
]
PNR_ARTIFACTS_HEAVY = ["6_final.def", "6_final.gds", "6_final.odb", "6_final.spef"]

PNR_METRIC_KEYS = {
    "setup_wns_ns": "finish__timing__setup__ws",
    "setup_tns_ns": "finish__timing__setup__tns",
    "setup_violations": "finish__timing__drv__setup_violation_count",
    "hold_wns_ns": "finish__timing__hold__ws",
    "hold_tns_ns": "finish__timing__hold__tns",
    "hold_violations": "finish__timing__drv__hold_violation_count",
    "fmax_hz": "finish__timing__fmax",
    "core_area_um2": "finish__design__core__area",
    "die_area_um2": "finish__design__die__area",
    "standard_cell_area_um2": "finish__design__instance__area__stdcell",
    "macro_area_um2": "finish__design__instance__area__macros",
    "sequential_area_um2": "finish__design__instance__area__class__sequential_cell",
    "instance_count": "finish__design__instance__count",
    "standard_cell_count": "finish__design__instance__count__stdcell",
    "macro_count": "finish__design__instance__count__macros",
    "sequential_cell_count": "finish__design__instance__count__class__sequential_cell",
    "utilization_fraction": "finish__design__instance__utilization",
    "routed_wirelength_um": "detailedroute__route__wirelength",
    "vias": "detailedroute__route__vias",
    "drc_errors": "detailedroute__route__drc_errors",
    "antenna_violating_nets": "detailedroute__antenna__violating__nets",
    "antenna_violating_pins": "detailedroute__antenna__violating__pins",
    "routed_nets": "detailedroute__route__net",
    "clock_count": "constraints__clocks__count",
    "power_total_w": "finish__power__total",
}


def orfs_identity() -> dict[str, Any]:
    proc = run(["docker", "image", "inspect", ORFS_IMAGE, "--format", "{{.Id}}"], timeout=300)
    require_success(proc, "docker image inspect")
    image_id = (proc.stdout or "").strip()
    proc = run(
        ["docker", "image", "inspect", ORFS_IMAGE, "--format", "{{json .RepoDigests}}"],
        timeout=300,
    )
    require_success(proc, "docker image inspect digests")
    digests = json.loads((proc.stdout or "[]").strip() or "[]")

    probe = run(
        [
            "docker", "run", "--rm", ORFS_IMAGE, "bash", "-lc",
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
            "echo OPENROAD $(openroad -version 2>&1 | head -1); "
            "echo YOSYS $(yosys -V 2>&1 | head -1); "
            "sha256sum $(command -v openroad) $(command -v yosys)",
        ],
        timeout=900,
    )
    require_success(probe, "ORFS toolchain probe")
    text = probe.stdout or ""
    openroad_version = ""
    yosys_version = ""
    for line in text.splitlines():
        if line.startswith("OPENROAD "):
            openroad_version = line[len("OPENROAD "):].strip()
        elif line.startswith("YOSYS "):
            yosys_version = line[len("YOSYS "):].strip()
    binaries = {}
    for line in text.splitlines():
        match = re.match(r"^([0-9a-f]{64})\s+(\S+)\s*$", line)
        if match:
            binaries[match.group(2)] = match.group(1)

    return {
        "image_reference": ORFS_IMAGE,
        "image_id": image_id,
        "image_id_matches_archived_asap7_lock": image_id == ORFS_EXPECTED_IMAGE_ID,
        "repo_digests": digests,
        "openroad_version": openroad_version,
        "yosys_version": yosys_version,
        "binary_sha256": binaries,
    }


def platform_file_hashes(platform_name: str) -> dict[str, str]:
    proc = run(
        [
            "docker", "run", "--rm", ORFS_IMAGE, "bash", "-lc",
            f"cd /OpenROAD-flow-scripts/flow/platforms/{platform_name} && "
            "find . -type f \\( -name '*.lib' -o -name '*.lib.gz' -o -name '*.lef' "
            "-o -name '*.tlef' -o -name 'config.mk' \\) -print0 | sort -z | xargs -0 sha256sum",
        ],
        timeout=1800,
    )
    require_success(proc, "ORFS platform hash probe")
    hashes: dict[str, str] = {}
    for line in (proc.stdout or "").splitlines():
        match = re.match(r"^([0-9a-f]{64})\s+\./(\S+)\s*$", line)
        if match:
            hashes[match.group(2)] = match.group(1)
    return hashes


def run_pnr(
    view_name: str,
    view: dict[str, Any],
    block_name: str,
    block: dict[str, Any],
    work: Path,
    clock_period_ns: float,
    core_utilization: int,
    place_density: float,
    keep_heavy: bool,
) -> dict[str, Any]:
    pnr = view["pnr"]
    platform_name = pnr["platform"]
    case = work / "orfs"
    case.mkdir(parents=True, exist_ok=True)

    time_unit_ns = view["time_unit_ns"]
    period_lib = clock_period_ns / time_unit_ns
    load_lib = view["output_load_ff"] / view["cap_unit_ff"]

    (case / "constraint.sdc").write_text(
        "\n".join(
            [
                f"set clk_period {period_lib:g}",
                f"create_clock -name core_clk -period $clk_period [get_ports {block['clock_port']}]",
                "set non_clock_inputs [all_inputs -no_clocks]",
                "set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs",
                "set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]",
                f"set_load {load_lib:g} [all_outputs]",
                "set_max_fanout 32 [current_design]",
                *(
                    f"set_false_path -from [get_ports {port}]"
                    for port in block["false_path_from_ports"]
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    nickname = f"opentallas_{block_name}_{view_name}"
    params = " ".join(f"{k} {v}" for k, v in sorted(block["parameters"].items()))
    config = [
        f"export DESIGN_NICKNAME = {nickname}",
        f"export DESIGN_NAME = {block['top']}",
        f"export PLATFORM = {platform_name}",
        "export VERILOG_FILES = " + " ".join(f"/src/{s}" for s in block["sources"]),
        "export VERILOG_DEFINES = -DSYNTHESIS",
        "export SDC_FILE = /work/constraint.sdc",
        f"export CORE_UTILIZATION = {core_utilization}",
        "export CORE_ASPECT_RATIO = 1",
        "export CORE_MARGIN = 2",
        f"export PLACE_DENSITY = {place_density}",
        "export PLACE_DENSITY_LB_ADDON = 0.05",
        "export SYNTH_REPEATABLE_BUILD = 1",
        "export SYNTH_HIERARCHICAL = 0",
        "export LEC_CHECK = 0",
        "export TNS_END_PERCENT = 100",
        "export HOLD_SLACK_MARGIN = 0",
        "export SETUP_SLACK_MARGIN = 0",
        "export SKIP_REPORT_METRICS = 0",
        "export REPORT_CLOCK_SKEW = 1",
    ]
    if params:
        config.append(f"export VERILOG_TOP_PARAMS = {params}")
    if pnr["corner_env"]:
        config.append(f"export CORNER = {pnr['corner_env']}")
    for key, value in sorted(pnr["extra_config"].items()):
        config.append(f"export {key} = {value}")
    (case / "config.mk").write_text("\n".join(config) + "\n", encoding="utf-8")

    def orfs_make(goal: str, log_name: str, timeout: int) -> subprocess.CompletedProcess:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{ROOT}:/src:ro",
            "-v", f"{case}:/work",
            "-w", "/OpenROAD-flow-scripts/flow",
            ORFS_IMAGE, "bash", "-lc",
            "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; "
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
            "make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base "
            + goal,
        ]
        completed = run(cmd, timeout=timeout)
        (case / log_name).write_text(
            (completed.stdout or "") + (completed.stderr or ""), encoding="utf-8"
        )
        return completed

    results_dir = case / "results" / platform_name / nickname / "base"
    mapped_container = f"/work/results/{platform_name}/{nickname}/base/1_2_yosys.v"

    # Phase 1: ORFS synthesis only.  OpenROAD's Verilog reader rejects the
    # ``input signed`` declarations Yosys emits for signed RTL ports, so the
    # mapped netlist is normalised on the host before the flow resumes.
    proc = orfs_make(
        f"{mapped_container} && chmod a+w {mapped_container}",
        "orfs_synth.log",
        7200,
    )
    require_success(proc, "ORFS synthesis")
    mapped = results_dir / "1_2_yosys.v"
    if not mapped.is_file():
        raise FlowError(f"ORFS produced no mapped netlist at {mapped}")
    raw_mapped = case / "1_2_yosys.raw.v"
    shutil.copy2(mapped, raw_mapped)
    signed_stripped = normalise_netlist(mapped, mapped)

    # Phase 2: floorplan through routing and metadata.
    proc = orfs_make("finish metadata-generate", "orfs_flow.log", 21600)
    require_success(proc, "ORFS place-and-route")
    reports_dir = case / "reports" / platform_name / nickname / "base"
    logs_dir = case / "logs" / platform_name / nickname / "base"
    metadata_path = reports_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FlowError(f"ORFS produced no metadata.json at {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    metrics: dict[str, Any] = {}
    missing: list[str] = []
    for name, key in sorted(PNR_METRIC_KEYS.items()):
        if key in metadata:
            metrics[name] = metadata[key]
        else:
            missing.append(key)
    metrics["missing_metadata_keys"] = missing

    flow_errors = {
        key: metadata[key]
        for key in sorted(metadata)
        if key.endswith("__flow__errors__count")
    }
    metrics["flow_error_counts"] = flow_errors
    if any(int(v) != 0 for v in flow_errors.values()):
        raise FlowError(f"ORFS reported flow errors: {flow_errors}")

    # Collect artifacts.
    artifacts: dict[str, Any] = {}
    search_dirs = [results_dir, reports_dir, logs_dir, case]
    wanted = list(PNR_ARTIFACTS_LIGHT) + (PNR_ARTIFACTS_HEAVY if keep_heavy else [])
    out_dir = work / "pnr_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in wanted:
        for directory in search_dirs:
            candidate = directory / name
            if candidate.is_file():
                shutil.copy2(candidate, out_dir / name)
                artifacts[name] = {
                    "sha256": sha256_file(candidate),
                    "size_bytes": candidate.stat().st_size,
                    "retained": True,
                }
                break
    # Record identity of heavy artifacts even when they are not retained.
    if not keep_heavy:
        for name in PNR_ARTIFACTS_HEAVY:
            candidate = results_dir / name
            if candidate.is_file():
                artifacts[name] = {
                    "sha256": sha256_file(candidate),
                    "size_bytes": candidate.stat().st_size,
                    "retained": False,
                }

    return {
        "platform": platform_name,
        "design_nickname": nickname,
        "netlist_normalization": {
            "signed_declarations_stripped": signed_stripped,
            "raw_netlist_sha256": sha256_file(raw_mapped),
            "normalized_netlist_sha256": sha256_file(mapped),
            "note": (
                "declaration-attribute-only edit on the ORFS-synthesised gate "
                "netlist; no cell, net, port or connectivity change"
            ),
        },
        "core_utilization_percent": core_utilization,
        "place_density": place_density,
        "clock_period_ns": clock_period_ns,
        "sdc_clock_period_library_units": period_lib,
        "metrics": metrics,
        "artifacts": artifacts,
        "artifact_dir": str(out_dir.relative_to(ROOT)) if out_dir.is_relative_to(ROOT) else str(out_dir),
        "toolchain": orfs_identity(),
        "platform_file_sha256": platform_file_hashes(platform_name),
    }


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--view", required=True, choices=sorted(VIEWS))
    parser.add_argument("--block", choices=sorted(BLOCKS), help="named block from the built-in registry")
    parser.add_argument("--top", help="RTL top module (with --source, overrides --block)")
    parser.add_argument("--source", action="append", default=[], help="RTL source, repeatable")
    parser.add_argument("--param", action="append", default=[], help="NAME=VALUE top parameter, repeatable")
    parser.add_argument("--clock-port", default="clk")
    parser.add_argument("--false-path-from", action="append", default=None)
    parser.add_argument("--corner", default=None, help="corner name within the view")
    parser.add_argument("--clock-period-ns", type=float, required=True)
    parser.add_argument("--stages", default="synth,sta", help="comma list of synth,sta,pnr")
    parser.add_argument(
        "--fmax-search",
        action="store_true",
        help="bisect the clock period for the shortest period meeting setup timing",
    )
    parser.add_argument("--core-utilization", type=int, default=35)
    parser.add_argument("--place-density", type=float, default=0.60)
    parser.add_argument("--keep-heavy-artifacts", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-workdir", default=None, help="directory to retain intermediate files in")
    args = parser.parse_args(argv)

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    if output.exists() and not args.force:
        print(f"refusing to overwrite existing output: {output} (use --force)", file=sys.stderr)
        return 2

    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    for stage in stages:
        if stage not in {"synth", "sta", "pnr"}:
            print(f"unknown stage: {stage}", file=sys.stderr)
            return 2
    if "sta" in stages and "synth" not in stages:
        print("stage sta requires stage synth", file=sys.stderr)
        return 2

    view = VIEWS[args.view]

    if args.block:
        block = dict(BLOCKS[args.block])
        block_name = args.block
    elif args.top and args.source:
        parameters: dict[str, Any] = {}
        for item in args.param:
            name, _, value = item.partition("=")
            parameters[name] = int(value) if value.lstrip("-").isdigit() else value
        block = {
            "top": args.top,
            "sources": args.source,
            "parameters": parameters,
            "clock_port": args.clock_port,
            "false_path_from_ports": args.false_path_from or [],
            "description": "ad-hoc block supplied on the command line",
        }
        block_name = args.top
    else:
        print("either --block or (--top with at least one --source) is required", file=sys.stderr)
        return 2

    if args.false_path_from is not None:
        block["false_path_from_ports"] = args.false_path_from

    corner_name = args.corner or view["default_corner"]
    if corner_name not in view["corners"]:
        print(f"unknown corner {corner_name} for view {args.view}", file=sys.stderr)
        return 2
    corner = view["corners"][corner_name]

    if "pnr" in stages and not view.get("pnr"):
        print(f"view {args.view} does not support place-and-route", file=sys.stderr)
        return 2

    workdir_ctx = None
    if args.keep_workdir:
        work = Path(args.keep_workdir)
        if not work.is_absolute():
            work = ROOT / work
        work.mkdir(parents=True, exist_ok=True)
    else:
        workdir_ctx = tempfile.TemporaryDirectory(prefix="abi3-physical-")
        work = Path(workdir_ctx.name)

    started = datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": CAMPAIGN_ID,
        "generated_at": started.isoformat(),
        "git": git_identity(),
        "runner": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "argv": ["tools/run_abi3_physical.py", *(argv if argv is not None else sys.argv[1:])],
        },
        "view": {
            "name": args.view,
            "description": view["description"],
            "evidence_class": view["evidence_class"],
            "node_nm": view["node_nm"],
            "predictive": view["predictive"],
            "cell_library": view["cell_library"],
            "pdk_lock": view["pdk_lock"],
            "flows_supported": ["synth", "sta"] + (["pnr"] if view.get("pnr") else []),
        },
        "corner": {
            "name": corner_name,
            "process": corner["process"],
            "voltage_v": corner["voltage_v"],
            "temperature_c": corner["temperature_c"],
            "liberty": [
                {
                    "path": str(path),
                    "sha256": sha256_file(Path(path)),
                    "size_bytes": Path(path).stat().st_size,
                }
                for path in corner["liberty"]
            ],
        },
        "design": {
            "block": block_name,
            "top": block["top"],
            "description": block.get("description"),
            "parameters": block["parameters"],
            "clock_port": block["clock_port"],
            "false_path_from_ports": block["false_path_from_ports"],
            "sources": [
                {
                    "path": source,
                    "sha256": sha256_file(ROOT / source),
                    "size_bytes": (ROOT / source).stat().st_size,
                }
                for source in block["sources"]
            ],
        },
        "target_clock_period_ns": args.clock_period_ns,
        "stages_requested": stages,
        "stages_completed": [],
    }

    try:
        tools: dict[str, Any] = {}
        if "synth" in stages:
            tools["yosys"] = tool_identity(YOSYS, ["-V"])
            tools["abc"] = {"path": str(YOSYS_ABC), "sha256": sha256_file(YOSYS_ABC)}
        if "sta" in stages:
            tools["opensta"] = tool_identity(STA, ["-version"])
        record["tools"] = tools

        netlist = None
        if "synth" in stages:
            cells = scan_liberty([Path(p) for p in corner["liberty"]])
            dont_use = expand_dont_use(view["dont_use"], cells)
            result = run_synthesis(
                view, corner, block, work, args.clock_period_ns, dont_use
            )
            netlist = result["netlist"]
            record["synthesis"] = result["record"]
            record["synthesis"]["liberty_cell_count"] = len(cells)
            record["stages_completed"].append("synth")

        if "sta" in stages:
            assert netlist is not None
            record["static_timing"] = run_sta(
                view, corner, block, work, netlist, args.clock_period_ns
            )
            if args.fmax_search:
                record["static_timing"]["fmax_search"] = search_fmax(
                    view, corner, block, work, netlist, args.clock_period_ns
                )
            record["stages_completed"].append("sta")

        if "pnr" in stages:
            record["place_and_route"] = run_pnr(
                args.view,
                view,
                block_name,
                block,
                work,
                args.clock_period_ns,
                args.core_utilization,
                args.place_density,
                args.keep_heavy_artifacts,
            )
            record["stages_completed"].append("pnr")

        record["status"] = "pass"
    except Exception as exc:  # noqa: BLE001 - recorded, then re-raised as failure
        record["status"] = "fail"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
        canonical_dump(record, output)
        print(f"FAILED: {record['error']}", file=sys.stderr)
        print(f"partial record written to {output}", file=sys.stderr)
        if workdir_ctx is not None:
            workdir_ctx.cleanup()
        return 1

    record["completed_at"] = datetime.now(timezone.utc).isoformat()
    record["elapsed_seconds"] = round(
        (datetime.now(timezone.utc) - started).total_seconds(), 3
    )
    canonical_dump(record, output)

    if workdir_ctx is not None:
        workdir_ctx.cleanup()

    synth = record.get("synthesis", {})
    sta = record.get("static_timing", {})
    pnr = record.get("place_and_route", {})
    print(f"view={args.view} corner={corner_name} block={block_name} top={block['top']}")
    if synth:
        print(
            f"  synth: cells={synth['cell_count']} area={synth['cell_area_um2']:.3f} um2 "
            f"seq_area={synth['sequential_area_um2']:.3f} um2 macros={synth['macro_count']}"
        )
    if sta:
        print(
            f"  sta:   WNS={sta['setup_wns_ns']:.4f} ns TNS={sta['setup_tns_ns']:.4f} ns "
            f"Fmax={sta['fmax_hz'] / 1e6:.2f} MHz met={sta['timing_met']}"
        )
    if pnr:
        m = pnr["metrics"]
        print(
            f"  pnr:   wirelength={m.get('routed_wirelength_um')} um vias={m.get('vias')} "
            f"DRC={m.get('drc_errors')} antenna_nets={m.get('antenna_violating_nets')} "
            f"Fmax={float(m.get('fmax_hz', 0)) / 1e6:.2f} MHz"
        )
    print(f"  wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
