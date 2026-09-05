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

Signal integrity.  ``--max-transition-ns`` and ``--max-fanout`` put explicit
``set_max_transition`` / ``set_max_fanout`` constraints in the SDC so ORFS's
repair_design buffers and sizes to them; ``--slew-margin-percent`` hands ORFS
its SLEW_MARGIN so the repair overfixes.  Bare ``--max-transition-ns`` takes
the corner's own liberty limit (asap7 RVT 0.32 ns, sky130hd 1.5 ns).  The
values used are recorded under ``place_and_route.signal_integrity_constraints``
and nothing is emitted or recorded when the options are absent.

Pinned sources.  ``--source-root DIR`` reads the RTL from another checkout
(a worktree pinned at the commit being characterised); the record's ``git``
block then describes that tree and ``runner.driver`` names the commit this
driver came from.
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

# DRIVER_ROOT is the tree this file lives in.  ROOT is the tree the RTL
# sources, their git identity, the container's /src mount and every relative
# path are taken from: the driver's own tree unless --source-root rebinds it
# to a worktree pinned at the commit being characterised.
DRIVER_ROOT = Path(__file__).resolve().parent.parent
ROOT = DRIVER_ROOT
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
    "matmul_bf16_sram_engine": {
        "top": "ot_ta_matmul_bf16_sram_engine",
        "sources": [
            "rtl/ot_fp32_rne_pkg.sv",
            "rtl/ot_ta_command_decoder.sv",
            "rtl/ot_ta_matmul_bf16_sram_engine.sv",
        ],
        "parameters": {},
        "clock_port": "clk",
        "false_path_from_ports": ["rst_n"],
        "description": (
            "MATMUL_BF16_TILE stream executor: command decode, exact BF16 "
            "widening multiply, binary32 RNE accumulate and BF16 conversion, "
            "with ordered 16-bit SRAM operand and accumulator traffic.  This "
            "is the block the cycle model's tensor engine actually is, and "
            "the one every tensor cycle in every study rests on; SRAM arrays "
            "are external, so it maps to standard cells only.  Its critical "
            "path is a whole FP32 multiply-add-convert chain in one cycle, so "
            "it closes far below the other blocks and needs a target period "
            "chosen for it -- 200 ns on sky130hd, 18 ns on asap7 -- rather "
            "than the period the smaller blocks use."
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
    """Commit and cleanliness of the tree the sources are read from.

    The flow writes its own records under ``results/`` inside the tree, so an
    earlier run's untracked output must not mark a later run dirty; those
    paths are listed separately.  Anything else -- a modified tracked file or
    an untracked file outside ``results/`` -- is dirt, because it could be
    source the record's commit does not describe.
    """
    head = run(["git", "rev-parse", "HEAD"])
    status = run(["git", "status", "--porcelain"])
    lines = [line for line in (status.stdout or "").splitlines() if line.strip()]

    def untracked_result(line: str) -> bool:
        return line.startswith("?? ") and line[3:].startswith("results/")

    dirt = [line for line in lines if not untracked_result(line)]
    return {
        "commit": (head.stdout or "").strip() or None,
        "worktree_dirty": bool(dirt),
        "worktree_status": dirt[:50],
        "untracked_results": [line[3:] for line in lines if untracked_result(line)][:50],
        "dirty_basis": (
            "a tracked file modified or an untracked file outside results/; "
            "untracked files under results/ (records the flow itself writes) "
            "are listed in untracked_results and do not count"
        ),
    }


def driver_identity() -> dict[str, Any]:
    """Which driver file ran, and the commit of the tree it came from.

    ``git`` in the record describes the tree the sources came from (``ROOT``).
    With ``--source-root`` that is a worktree pinned at the RTL's commit, whose
    own copy of this driver may be older; the driver that actually ran is
    identified here so the record names both commits.
    """
    path = Path(__file__).resolve()
    head = run(["git", "rev-parse", "HEAD"], cwd=DRIVER_ROOT)
    status = run(["git", "status", "--porcelain", "--", str(path)], cwd=DRIVER_ROOT)
    same_tree = DRIVER_ROOT.resolve() == ROOT.resolve()
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "tree": str(DRIVER_ROOT),
        "commit": (head.stdout or "").strip() or None,
        "file_modified_since_commit": bool((status.stdout or "").strip()),
        "same_tree_as_sources": same_tree,
        "note": (
            "the driver and the sources come from the same tree; git.commit describes both"
            if same_tree
            else (
                "the sources, their git identity (the record's git block) and the "
                "container's /src mount come from --source-root; the driver ran from "
                "a different checkout, so git.commit is the sources' commit and "
                "runner.driver.commit is the driver's"
            )
        ),
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
# SDC and signal-integrity constraints
# --------------------------------------------------------------------------
#
# Every SDC the driver writes carries ``set_max_fanout 32``; nothing else
# bounded slew, so the only max-transition limits ORFS saw were the liberty
# files' own (``default_max_transition`` and per-pin ``max_transition``:
# 320 ps in ASAP7 RVT, 1.5 ns in sky130hd).  repair_design buffers and sizes
# every net to the tightest limit on each of its pins -- SDC or liberty --
# under placement- and global-route-estimated parasitics; the finish report
# re-checks the same limits with extracted parasitics, and an LQ8 route came
# out with 292 pins over 320 ps.  ``--max-transition-ns`` puts an explicit
# design-wide limit in the SDC, ``--max-fanout`` replaces the fixed 32, and
# ``--slew-margin-percent`` hands ORFS its SLEW_MARGIN so repair_design
# overfixes by that fraction of the limit.  None of the three is emitted or
# recorded unless given: a record without
# ``place_and_route.signal_integrity_constraints`` was routed with exactly
# the SDC every earlier record had.

DEFAULT_MAX_FANOUT = 32
LIBRARY_LIMIT = "library"
DRIVER_DEFAULT = "default"

_DEFAULT_MAX_TRANSITION_RE = re.compile(
    r"^\s*default_max_transition\s*:\s*([0-9.eE+-]+)\s*;", re.M
)
_DEFAULT_MAX_FANOUT_RE = re.compile(r"^\s*default_max_fanout\s*:\s*([0-9.eE+-]+)\s*;", re.M)
_PIN_MAX_TRANSITION_RE = re.compile(r"^\s*max_transition\s*:", re.M)
_PIN_MAX_FANOUT_RE = re.compile(r"^\s*max_fanout\s*:", re.M)


def library_slew_limits(corner: dict[str, Any]) -> list[dict[str, Any]]:
    """What each liberty file of the corner declares as its slew limit.

    ``default_max_transition`` is in the library's own time unit (ps for
    ASAP7, ns for sky130); ``pin_max_transition_count`` is how many per-pin
    ``max_transition`` attributes the file carries, which override it.
    """
    found: list[dict[str, Any]] = []
    for path in corner["liberty"]:
        path = Path(path)
        text = path.read_text(errors="ignore")
        match = _DEFAULT_MAX_TRANSITION_RE.search(text)
        found.append(
            {
                "liberty": path.name,
                "default_max_transition": float(match.group(1)) if match else None,
                "pin_max_transition_count": len(_PIN_MAX_TRANSITION_RE.findall(text)),
            }
        )
    return found


def library_fanout_limits(corner: dict[str, Any]) -> list[dict[str, Any]]:
    """What each liberty file of the corner declares as its fanout limit, if anything."""
    found: list[dict[str, Any]] = []
    for path in corner["liberty"]:
        path = Path(path)
        text = path.read_text(errors="ignore")
        match = _DEFAULT_MAX_FANOUT_RE.search(text)
        found.append(
            {
                "liberty": path.name,
                "default_max_fanout": float(match.group(1)) if match else None,
                "pin_max_fanout_count": len(_PIN_MAX_FANOUT_RE.findall(text)),
            }
        )
    return found


def signal_integrity_sdc_lines(constraints: dict[str, Any] | None) -> list[str]:
    """The ``set_max_*`` lines of the SDC for these constraints (legacy 32 fanout when none)."""
    constraints = constraints or {}
    lines = [f"set_max_fanout {constraints.get('max_fanout', DEFAULT_MAX_FANOUT)} [current_design]"]
    if constraints.get("max_transition_library_units") is not None:
        lines.append(
            f"set_max_transition {constraints['max_transition_library_units']:g} [current_design]"
        )
    return lines


def resolve_signal_integrity_constraints(
    view: dict[str, Any],
    corner: dict[str, Any],
    max_transition_ns: float | str | None,
    max_fanout: int | str | None,
    slew_margin_percent: float | None,
) -> dict[str, Any] | None:
    """Turn the command-line options into the recorded constraint block.

    Returns ``None`` when no option was given, so the SDC and the record are
    exactly what they were before the options existed.
    """
    if max_transition_ns is None and max_fanout is None and slew_margin_percent is None:
        return None
    time_unit_ns = view["time_unit_ns"]
    out: dict[str, Any] = {}

    if max_transition_ns is not None:
        slew_limits = library_slew_limits(corner)
        declared = [e["default_max_transition"] for e in slew_limits if e["default_max_transition"] is not None]
        if max_transition_ns == LIBRARY_LIMIT:
            if not declared:
                raise FlowError(
                    "no liberty file of this corner declares default_max_transition; "
                    "give --max-transition-ns a value"
                )
            limit_lib = min(declared)
            ns = float(f"{limit_lib * time_unit_ns:.6g}")
            source = (
                "library: the smallest default_max_transition declared by the corner's "
                "liberty files, in the library time unit"
            )
        else:
            ns = float(max_transition_ns)
            if ns <= 0:
                raise FlowError(f"--max-transition-ns must be positive, got {ns}")
            limit_lib = float(f"{ns / time_unit_ns:.6g}")
            source = "command line"
        out["max_transition_ns"] = ns
        out["max_transition_library_units"] = limit_lib
        out["max_transition_source"] = source
        out["library_default_max_transition"] = slew_limits

    if max_fanout is not None:
        fanout_limits = library_fanout_limits(corner)
        declares_any = any(
            e["default_max_fanout"] is not None or e["pin_max_fanout_count"] for e in fanout_limits
        )
        if max_fanout == DRIVER_DEFAULT:
            n = DEFAULT_MAX_FANOUT
            source = "driver default: the set_max_fanout every earlier record's SDC carried"
        else:
            n = int(max_fanout)
            if n <= 0:
                raise FlowError(f"--max-fanout must be positive, got {n}")
            source = "command line"
        out["max_fanout"] = n
        out["max_fanout_source"] = source
        out["library_default_max_fanout"] = fanout_limits
        out["library_declares_fanout_limit"] = declares_any

    if slew_margin_percent is not None:
        margin = float(slew_margin_percent)
        if not 0.0 <= margin < 100.0:
            raise FlowError(f"--slew-margin-percent must be in [0, 100), got {margin}")
        out["slew_margin_percent"] = margin
        out["slew_margin_basis"] = (
            "ORFS SLEW_MARGIN, passed to repair_design -slew_margin at placement and "
            "after global routing: the repair targets (100 - margin)% of each pin's "
            "slew limit under estimated parasitics; the finish check keeps the full limit"
        )

    out["sdc_lines"] = signal_integrity_sdc_lines(out)
    out["basis"] = (
        "explicit SDC signal-integrity constraints this route was repaired against; "
        "absent from a record means the SDC carried only set_max_fanout 32 and the "
        "liberty files' own max_transition limits"
    )
    return out


def sdc_lines(
    view: dict[str, Any],
    block: dict[str, Any],
    clock_period_ns: float,
    constraints: dict[str, Any] | None = None,
) -> list[str]:
    """The SDC both the host OpenSTA stage and the ORFS flow are constrained by."""
    period_lib = clock_period_ns / view["time_unit_ns"]
    load_lib = view["output_load_ff"] / view["cap_unit_ff"]
    lines = [
        f"set clk_period {period_lib:g}",
        f"create_clock -name core_clk -period $clk_period [get_ports {block['clock_port']}]",
        "set non_clock_inputs [all_inputs -no_clocks]",
        "set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs",
        "set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]",
        f"set_load {load_lib:g} [all_outputs]",
        *signal_integrity_sdc_lines(constraints),
        *(f"set_false_path -from [get_ports {port}]" for port in block["false_path_from_ports"]),
    ]
    return lines


def sdc_text(
    view: dict[str, Any],
    block: dict[str, Any],
    clock_period_ns: float,
    constraints: dict[str, Any] | None = None,
) -> str:
    return "\n".join(sdc_lines(view, block, clock_period_ns, constraints)) + "\n"


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
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    time_unit_ns = view["time_unit_ns"]
    period_lib = clock_period_ns / time_unit_ns

    sdc = work / "constraint.sdc"
    sdc.write_text(sdc_text(view, block, clock_period_ns, constraints), encoding="utf-8")

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
    constraints: dict[str, Any] | None = None,
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
        result = run_sta(view, corner, block, stage, netlist, period_ns, constraints)
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

# Metrics whose metadata value is a time in the SDC/liberty time unit.
PNR_TIMING_METRICS_NS = {
    "setup_wns_ns",
    "setup_tns_ns",
    "hold_wns_ns",
    "hold_tns_ns",
}

PNR_METRIC_KEYS = {
    "setup_wns_ns": "finish__timing__setup__ws",
    "setup_tns_ns": "finish__timing__setup__tns",
    "setup_violations": "finish__timing__drv__setup_violation_count",
    "hold_wns_ns": "finish__timing__hold__ws",
    "hold_tns_ns": "finish__timing__hold__tns",
    "hold_violations": "finish__timing__drv__hold_violation_count",
    # Signal-integrity design-rule violations.  ORFS reports them beside the
    # timing ones and nothing read them, so an LQ8 route with 292 max-slew
    # violations was recorded closed=true (results/physical_abi3/asap7/
    # a3_lq8_array/pnr.json at 2f6b0a4).  A closed netlist has none.
    "max_slew_violations": "finish__timing__drv__max_slew",
    "max_cap_violations": "finish__timing__drv__max_cap",
    "max_fanout_violations": "finish__timing__drv__max_fanout",
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


def orfs_config_lines(
    nickname: str,
    block: dict[str, Any],
    platform_name: str,
    pnr: dict[str, Any],
    core_utilization: int,
    place_density: float,
    constraints: dict[str, Any] | None = None,
) -> list[str]:
    """The ORFS config.mk for one route; SLEW_MARGIN only when a margin was given."""
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
    if constraints and constraints.get("slew_margin_percent") is not None:
        config.append(f"export SLEW_MARGIN = {constraints['slew_margin_percent']:g}")
    return config


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
    artifact_dir: Path,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pnr = view["pnr"]
    platform_name = pnr["platform"]
    case = work / "orfs"
    case.mkdir(parents=True, exist_ok=True)

    time_unit_ns = view["time_unit_ns"]
    period_lib = clock_period_ns / time_unit_ns

    (case / "constraint.sdc").write_text(
        sdc_text(view, block, clock_period_ns, constraints), encoding="utf-8"
    )

    nickname = f"opentallas_{block_name}_{view_name}"
    config = orfs_config_lines(
        nickname, block, platform_name, pnr, core_utilization, place_density, constraints
    )
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

    # ORFS reports slack in the SDC's own time unit, which is the liberty time
    # unit: nanoseconds for sky130hd but PICOSECONDS for asap7.  Convert the
    # timing metrics into nanoseconds and keep the raw values alongside.
    metrics: dict[str, Any] = {}
    missing: list[str] = []
    raw_timing: dict[str, Any] = {}
    for name, key in sorted(PNR_METRIC_KEYS.items()):
        if key not in metadata:
            missing.append(key)
            continue
        value = metadata[key]
        if name in PNR_TIMING_METRICS_NS:
            raw_timing[name] = value
            metrics[name] = float(value) * time_unit_ns
        else:
            metrics[name] = value
    metrics["missing_metadata_keys"] = missing
    metrics["raw_timing_library_units"] = raw_timing
    metrics["library_time_unit_ns"] = time_unit_ns

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
    out_dir = artifact_dir
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
        **({"signal_integrity_constraints": constraints} if constraints else {}),
        "metrics": metrics,
        "artifacts": artifacts,
        "artifact_dir": str(out_dir.relative_to(ROOT)) if out_dir.is_relative_to(ROOT) else str(out_dir),
        "toolchain": orfs_identity(),
        "platform_file_sha256": platform_file_hashes(platform_name),
    }


# --------------------------------------------------------------------------
# Engineering verdict
# --------------------------------------------------------------------------
#
# ``status`` is the ENGINEERING result, not "the script finished".  Whether the
# flow ran to completion is reported separately as ``flow_completed``.  A run
# whose timing did not close must never be emitted as ``pass``: a downstream
# report generator reads ``status``, and a slow corner that fails to close at
# the target period would otherwise silently become a claim that the block
# closes at that period.

STATUS_PASS = "pass"
STATUS_NOT_MET = "not_met"
STATUS_NOT_EVALUATED = "not_evaluated"
STATUS_ERROR = "error"


def evaluate_verdict(record: dict[str, Any]) -> dict[str, Any]:
    """Derive the engineering verdict from whatever stages actually ran."""
    checks: list[dict[str, Any]] = []

    sta = record.get("static_timing")
    if sta:
        setup_ok = sta["setup_wns_ns"] >= 0.0 and sta["setup_violating_paths"] == 0
        hold_ok = sta["hold_wns_ns"] >= 0.0 and sta["hold_violating_paths"] == 0
        checks.append(
            {
                "stage": "static_timing",
                "scope": "pre-layout, ideal clock",
                "met": bool(setup_ok and hold_ok),
                "setup_met": bool(setup_ok),
                "hold_met": bool(hold_ok),
                "setup_wns_ns": sta["setup_wns_ns"],
                "setup_violating_paths": sta["setup_violating_paths"],
                "hold_wns_ns": sta["hold_wns_ns"],
                "hold_violating_paths": sta["hold_violating_paths"],
            }
        )

    pnr = record.get("place_and_route")
    if pnr:
        m = pnr["metrics"]

        def number(key: str) -> float | None:
            value = m.get(key)
            return None if value is None else float(value)

        setup_wns = number("setup_wns_ns")
        hold_wns = number("hold_wns_ns")
        setup_viol = number("setup_violations")
        hold_viol = number("hold_violations")
        drc = number("drc_errors")
        ant_nets = number("antenna_violating_nets")
        ant_pins = number("antenna_violating_pins")
        timing_ok = (
            setup_wns is not None
            and hold_wns is not None
            and setup_wns >= 0.0
            and hold_wns >= 0.0
            and setup_viol == 0
            and hold_viol == 0
        )
        clean_ok = drc == 0 and ant_nets == 0 and ant_pins == 0
        checks.append(
            {
                "stage": "place_and_route",
                "scope": "post-route, extracted parasitics",
                "met": bool(timing_ok and clean_ok),
                "timing_met": bool(timing_ok),
                "physically_clean": bool(clean_ok),
                "setup_wns_ns": setup_wns,
                "setup_violations": setup_viol,
                "hold_wns_ns": hold_wns,
                "hold_violations": hold_viol,
                "drc_errors": drc,
                "antenna_violating_nets": ant_nets,
                "antenna_violating_pins": ant_pins,
            }
        )

    if not checks:
        return {
            "status": STATUS_NOT_EVALUATED,
            "reason": "no timing-bearing stage ran; nothing to accept or reject",
            "checks": checks,
        }
    failed = [c["stage"] for c in checks if not c["met"]]
    if failed:
        return {
            "status": STATUS_NOT_MET,
            "reason": f"did not meet in: {', '.join(failed)}",
            "checks": checks,
        }
    return {"status": STATUS_PASS, "reason": "all evaluated stages met", "checks": checks}


# --------------------------------------------------------------------------
# Design summary: lanes, MAC rate and per-MAC figures (redesign gates D3, D4)
# --------------------------------------------------------------------------
#
# docs/OPENTALLAS_REDESIGN_PLAN.md gates D3 and D4 read a ``design`` block from
# each pnr.json: the declared lane count, the MAC (lane-op) rate the RTL
# campaign measured for the block, and the per-MAC area and period derived
# from the routed result with the same arithmetic as the recorded baseline
# (docs/CHIP_ARCHITECTURE_DESIGN.md section 8.4: standard-cell area / MAC per
# cycle = 48,274 um2; closed target period / MAC per cycle = 104.1 ns).  The
# MAC rate is never measured here -- it is cited from the results/rtl artifact
# named on the command line -- and the per-MAC period is meaningful only when
# the routed block closed at the target period (``closed`` says so).

_NETLIST_INSTANCE_RE = re.compile(r"^\s*(\w+)\s+(\\\S+|\w+)\s+\(", re.M)
_NETLIST_NET_RE = re.compile(
    r"^\s*(?:wire|reg|input|output|inout)\s+(?:\[[^\]]*\]\s*)?(\\\S+|\w+)\s*;", re.M
)


def count_lane_instances(netlist: Path, lane_regex: str) -> dict[str, Any]:
    """Count the distinct lane indices named in a flattened gate netlist.

    ORFS flattens the hierarchy (SYNTH_HIERARCHICAL = 0), but Yosys keeps the
    hierarchical prefix on every net it declares, so a generate-loop lane
    survives as a net-name prefix such as ``gen_lane[3].u_lane.``.  Whether
    the mapped registers keep that prefix as an instance name depends on the
    Yosys version (0.68 renames them ``_NNN_`` like ABC renames the
    combinational cells), so both instance names and net names are scanned
    and a lane counts as present when either carries its index.  The per-lane
    counts are over named objects only and are a lower bound on what each
    lane contributes.
    """
    pattern = re.compile(lane_regex)
    cells_per_lane: dict[str, int] = {}
    nets_per_lane: dict[str, int] = {}
    instances_total = 0
    nets_total = 0
    text = netlist.read_text(encoding="utf-8", errors="ignore")
    for match in _NETLIST_INSTANCE_RE.finditer(text):
        instances_total += 1
        found = pattern.search(match.group(2))
        if found:
            key = found.group(1)
            cells_per_lane[key] = cells_per_lane.get(key, 0) + 1
    for match in _NETLIST_NET_RE.finditer(text):
        nets_total += 1
        found = pattern.search(match.group(1))
        if found:
            key = found.group(1)
            nets_per_lane[key] = nets_per_lane.get(key, 0) + 1
    lanes_seen = set(cells_per_lane) | set(nets_per_lane)

    def ordered(counts: dict[str, int]) -> dict[str, int]:
        return {key: counts[key] for key in sorted(counts, key=lambda k: (len(k), k))}

    return {
        "netlist": netlist.name,
        "netlist_sha256": sha256_file(netlist),
        "instance_regex": lane_regex,
        "instances_total": instances_total,
        "nets_total": nets_total,
        "distinct_lanes": len(lanes_seen),
        "distinct_lanes_by_instance_name": len(cells_per_lane),
        "distinct_lanes_by_net_name": len(nets_per_lane),
        "named_cells_per_lane": ordered(cells_per_lane),
        "named_nets_per_lane": ordered(nets_per_lane),
        "note": (
            "distinct_lanes is the union of lane indices found on instance "
            "names and on declared net names; ABC renames combinational cells "
            "and Yosys 0.68 renames mapped registers, so instance names may "
            "carry no lane prefix while the nets keep it"
        ),
    }

def evidence_entry(spec: str) -> dict[str, Any]:
    """Resolve ``PATH`` or ``PATH:DOTTED.FIELD`` into a hashed citation."""
    path_str, _, field = spec.partition(":")
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT / path
    entry: dict[str, Any] = {"path": path_str}
    if not path.is_file():
        entry["error"] = "missing"
        return entry
    entry["sha256"] = sha256_file(path)
    if field:
        entry["field"] = field
        try:
            node: Any = json.loads(path.read_text(encoding="utf-8"))
            for part in field.split("."):
                node = node[part]
            entry["value"] = node
        except Exception as exc:  # noqa: BLE001 - recorded, not fatal
            entry["error"] = f"{type(exc).__name__}: {exc}"
    return entry


def augment_design(
    record: dict[str, Any],
    lanes: int | None,
    mac_per_cycle: float | None,
    evidence: list[str],
    lane_regex: str | None,
    netlists: list[Path | None],
) -> None:
    """Attach the gate-facing design summary to ``record['design']``.

    Every number here is copied from a stage this run executed; when a stage
    did not run (or the flow errored) the corresponding field is absent and
    ``closed`` is false, so a partial record can never read as a result.
    """
    # The closure verdict and the signal-integrity counts belong to EVERY
    # routed record.  This used to return early when no lane argument was
    # given, so five routed records -- the D4 baseline among them -- carried no
    # verdict at all.  Lane-specific fields stay conditional below.
    design = record.setdefault("design", {})
    pnr = record.get("place_and_route")
    synth = record.get("synthesis")
    sta = record.get("static_timing") or {}
    metrics = (pnr or {}).get("metrics", {})

    if lanes is not None:
        design["lanes"] = lanes
        design["lanes_basis"] = (
            "declared lane count of the block (its LANES parameter, or 1 for a "
            "single lane); lanes_in_netlist is the count recovered from the "
            "mapped netlist"
        )
    if lane_regex:
        counted: dict[str, Any] | None = None
        for candidate in netlists:
            if candidate is not None and candidate.is_file():
                counted = count_lane_instances(candidate, lane_regex)
                break
        if counted is None:
            counted = {"error": "no netlist available", "instance_regex": lane_regex}
        design["lanes_in_netlist"] = counted
        design["lanes_verified_in_netlist"] = bool(
            lanes is not None and counted.get("distinct_lanes") == lanes
        )

    if mac_per_cycle is not None:
        design["mac_per_cycle"] = mac_per_cycle
        design["mac_per_cycle_basis"] = (
            "lane-ops retired per cycle by the whole block in steady state, as "
            "measured by the RTL campaign cited in mac_rate_evidence (one "
            "product per lane-op at g = 1); not measured by this flow"
        )
        design["mac_rate_evidence"] = [evidence_entry(item) for item in evidence]

    if pnr:
        design["cells"] = metrics.get("standard_cell_count")
        design["cells_basis"] = (
            "place_and_route.metrics.standard_cell_count: routed netlist after "
            "timing repair and clock-tree synthesis, buffers included"
        )
        design["area_um2"] = metrics.get("standard_cell_area_um2")
        design["area_basis"] = "place_and_route.metrics.standard_cell_area_um2"
        design["core_area_um2"] = metrics.get("core_area_um2")
        design["utilization_fraction"] = metrics.get("utilization_fraction")
        design["fmax_hz"] = metrics.get("fmax_hz")
        design["fmax_basis"] = "place_and_route.metrics.fmax_hz (ORFS finish__timing__fmax)"
        design["clock_period_ns"] = pnr.get("clock_period_ns")
        design["setup_wns_ns"] = metrics.get("setup_wns_ns")
        design["hold_wns_ns"] = metrics.get("hold_wns_ns")
        design["drc"] = metrics.get("drc_errors")
        nets = metrics.get("antenna_violating_nets")
        pins = metrics.get("antenna_violating_pins")
        design["antenna_violating_nets"] = nets
        design["antenna_violating_pins"] = pins
        design["antenna"] = (
            int(nets) + int(pins) if nets is not None and pins is not None else None
        )
        drv = {k: metrics.get(k) for k in ("max_slew_violations", "max_cap_violations", "max_fanout_violations")}
        design["signal_integrity_violations"] = drv
        design["signal_integrity_clean"] = all(v is not None and int(v) == 0 for v in drv.values())
    elif synth:
        design["cells"] = synth.get("cell_count")
        design["cells_basis"] = "synthesis.cell_count (pre-layout, pinned host Yosys)"
        design["area_um2"] = synth.get("cell_area_um2")
        design["area_basis"] = "synthesis.cell_area_um2 (pre-layout)"
        design["fmax_hz"] = sta.get("fmax_hz")
        design["fmax_basis"] = "static_timing.fmax_hz (pre-layout)" if sta else None
        design["clock_period_ns"] = sta.get("clock_period_ns")
        design["drc"] = None
        design["antenna"] = None

    closed = bool(pnr) and record.get("status") == STATUS_PASS
    if closed and design.get("signal_integrity_clean") is False:
        closed = False
        design["closed_reason"] = (
            "signal-integrity violations in the routed netlist: "
            + ", ".join(f"{k} {v}" for k, v in design["signal_integrity_violations"].items() if v)
        )
    design["closed"] = closed
    design["closed_basis"] = (
        "true only when place-and-route ran, the routed netlist carries zero "
        "max-slew, max-cap and max-fanout violations, and the engineering verdict is "
        "pass: setup and hold met with zero violating paths, zero DRC, zero "
        "antenna violations at the target period"
    )

    if mac_per_cycle:
        area = design.get("area_um2")
        period = design.get("clock_period_ns")
        fmax = design.get("fmax_hz")
        if area is not None:
            design["per_mac_area_um2"] = float(area) / mac_per_cycle
        if period is not None:
            design["per_mac_period_ns"] = float(period) / mac_per_cycle
        if fmax:
            design["per_mac_period_ns_at_fmax"] = (1e9 / float(fmax)) / mac_per_cycle
        design["per_mac_basis"] = (
            "per_mac_area_um2 = standard-cell area / MAC per cycle; "
            "per_mac_period_ns = target clock period / MAC per cycle -- the "
            "arithmetic behind the baseline's 48,274 um2 and 104.1 ns "
            "(results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json: "
            "8,348.44 um2 / 0.17294 and 18 ns / 0.17294; "
            "docs/CHIP_ARCHITECTURE_DESIGN.md section 8.4).  The period figure "
            "is a result only when closed is true; per_mac_period_ns_at_fmax "
            "is the same quantity at the reported post-route fmax, for "
            "information.  Nothing is scaled across nodes."
        )


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def _max_transition_arg(text: str) -> float | str:
    if text == LIBRARY_LIMIT:
        return text
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a time in ns or '{LIBRARY_LIMIT}', got {text!r}") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError(f"max transition must be positive, got {text}")
    return value


def _max_fanout_arg(text: str) -> int | str:
    if text == DRIVER_DEFAULT:
        return text
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer or '{DRIVER_DEFAULT}', got {text!r}") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError(f"max fanout must be positive, got {text}")
    return value


def build_parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "--max-transition-ns",
        nargs="?",
        const=LIBRARY_LIMIT,
        default=None,
        type=_max_transition_arg,
        metavar="NS",
        help=(
            "emit set_max_transition NS [current_design] in the SDC so repair_design "
            "buffers and sizes every net to that slew; given bare (or as 'library') "
            "it is the smallest default_max_transition of the corner's liberty files "
            "(asap7 RVT 0.32 ns, sky130hd 1.5 ns).  Absent: no set_max_transition, "
            "the liberty limits alone, as every earlier record"
        ),
    )
    parser.add_argument(
        "--max-fanout",
        nargs="?",
        const=DRIVER_DEFAULT,
        default=None,
        type=_max_fanout_arg,
        metavar="N",
        help=(
            "emit set_max_fanout N [current_design] and record it; given bare (or as "
            "'default') it is the 32 every SDC carries anyway.  Absent: set_max_fanout "
            "32, unrecorded, as every earlier record"
        ),
    )
    parser.add_argument(
        "--slew-margin-percent",
        type=float,
        default=None,
        metavar="PCT",
        help=(
            "ORFS SLEW_MARGIN: repair_design overfixes max-slew to (100 - PCT)%% of "
            "each pin's limit under estimated parasitics.  Absent: ORFS default, no margin"
        ),
    )
    parser.add_argument(
        "--source-root",
        default=None,
        metavar="DIR",
        help=(
            "tree to read the RTL sources from (default: this driver's own checkout).  "
            "Its git identity becomes the record's git block, it is mounted as /src in "
            "the ORFS container, and relative --output, --keep-workdir and "
            "--mac-rate-evidence paths resolve under it; the commit this driver came "
            "from is recorded in runner.driver"
        ),
    )
    parser.add_argument(
        "--purpose",
        default="characterization",
        choices=["characterization", "signoff_target"],
        help=(
            "characterization: this target period is a probe, not a claim that "
            "the block must close at it.  signoff_target: this period is the "
            "intended operating point."
        ),
    )
    parser.add_argument(
        "--expected-not-met",
        action="store_true",
        help=(
            "record that this corner is deliberately expected not to close at "
            "the target period; does not change status, only documents intent"
        ),
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-workdir", default=None, help="directory to retain intermediate files in")
    parser.add_argument(
        "--lanes",
        type=int,
        default=None,
        help="declared lane count of the block; recorded as design.lanes (gate D3)",
    )
    parser.add_argument(
        "--mac-per-cycle",
        type=float,
        default=None,
        help=(
            "MAC (lane-ops) per cycle for the whole block as measured by the RTL "
            "campaign named in --mac-rate-evidence; recorded as design.mac_per_cycle "
            "and used for the per-MAC figures (gate D4)"
        ),
    )
    parser.add_argument(
        "--mac-rate-evidence",
        action="append",
        default=[],
        help="results/rtl artifact behind --mac-per-cycle, as PATH or PATH:DOTTED.FIELD (repeatable)",
    )
    parser.add_argument(
        "--lane-instance-regex",
        default=None,
        help=(
            "regex over instance names of the mapped netlist whose first group is "
            "the lane index; distinct indices are counted into design.lanes_in_netlist"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    global ROOT
    args = build_parser().parse_args(argv)

    if args.source_root:
        source_root = Path(args.source_root).resolve()
        if not (source_root / "rtl").is_dir():
            print(f"--source-root {source_root} has no rtl/ directory", file=sys.stderr)
            return 2
        ROOT = source_root
    else:
        ROOT = DRIVER_ROOT

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

    try:
        constraints = resolve_signal_integrity_constraints(
            view, corner, args.max_transition_ns, args.max_fanout, args.slew_margin_percent
        )
    except FlowError as exc:
        print(str(exc), file=sys.stderr)
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
            "source_root": str(ROOT),
            "driver": driver_identity(),
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
        "purpose": args.purpose,
        "expected_not_met": bool(args.expected_not_met),
        "target_semantics": (
            "the target clock period is a characterisation probe, not an "
            "operating-point requirement"
            if args.purpose == "characterization"
            else "the target clock period is the intended operating point"
        ),
        "stages_requested": stages,
        "stages_completed": [],
        "flow_completed": False,
        "status": STATUS_ERROR,
    }

    netlist: Path | None = None
    try:
        tools: dict[str, Any] = {}
        if "synth" in stages:
            tools["yosys"] = tool_identity(YOSYS, ["-V"])
            tools["abc"] = {"path": str(YOSYS_ABC), "sha256": sha256_file(YOSYS_ABC)}
        if "sta" in stages:
            tools["opensta"] = tool_identity(STA, ["-version"])
        record["tools"] = tools

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
                view, corner, block, work, netlist, args.clock_period_ns, constraints
            )
            if args.fmax_search:
                record["static_timing"]["fmax_search"] = search_fmax(
                    view, corner, block, work, netlist, args.clock_period_ns,
                    constraints=constraints,
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
                output.parent / f"{output.stem}_artifacts",
                constraints,
            )
            record["stages_completed"].append("pnr")

        record["flow_completed"] = True
    except Exception as exc:  # noqa: BLE001 - recorded, then reported as an error
        record["flow_completed"] = False
        record["status"] = STATUS_ERROR
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
        augment_design(
            record,
            args.lanes,
            args.mac_per_cycle,
            args.mac_rate_evidence,
            args.lane_instance_regex,
            [netlist],
        )
        canonical_dump(record, output)
        print(f"FAILED: {record['error']}", file=sys.stderr)
        print(f"partial record written to {output}", file=sys.stderr)
        if workdir_ctx is not None:
            workdir_ctx.cleanup()
        return 1

    verdict = evaluate_verdict(record)
    record["status"] = verdict["status"]
    record["acceptance"] = {
        "status": verdict["status"],
        "reason": verdict["reason"],
        "checks": verdict["checks"],
        "criterion": (
            "pass requires every timing-bearing stage that ran to meet setup "
            "and hold with zero violating paths; place-and-route additionally "
            "requires zero DRC and zero antenna violations"
        ),
        "note": (
            "status is the engineering result, not whether the script "
            "finished; see flow_completed for that"
        ),
    }
    record["completed_at"] = datetime.now(timezone.utc).isoformat()
    record["elapsed_seconds"] = round(
        (datetime.now(timezone.utc) - started).total_seconds(), 3
    )
    artifact_dir = output.parent / f"{output.stem}_artifacts"
    augment_design(
        record,
        args.lanes,
        args.mac_per_cycle,
        args.mac_rate_evidence,
        args.lane_instance_regex,
        [artifact_dir / "6_final.v", artifact_dir / "1_2_yosys.v", netlist],
    )
    canonical_dump(record, output)

    if workdir_ctx is not None:
        workdir_ctx.cleanup()

    synth = record.get("synthesis", {})
    sta = record.get("static_timing", {})
    pnr = record.get("place_and_route", {})
    print(
        f"view={args.view} corner={corner_name} block={block_name} "
        f"top={block['top']} purpose={args.purpose}"
    )
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
        print(
            f"  drv:   max_slew={m.get('max_slew_violations')} max_cap={m.get('max_cap_violations')} "
            f"max_fanout={m.get('max_fanout_violations')}"
        )
    if constraints:
        print(
            "  sdc:   " + "; ".join(constraints["sdc_lines"])
            + (
                f"; SLEW_MARGIN={constraints['slew_margin_percent']:g}"
                if constraints.get("slew_margin_percent") is not None
                else ""
            )
        )
    design = record["design"]
    if "per_mac_area_um2" in design or "lanes" in design:
        print(
            f"  design: lanes={design.get('lanes')} "
            f"lanes_in_netlist={(design.get('lanes_in_netlist') or {}).get('distinct_lanes')} "
            f"mac_per_cycle={design.get('mac_per_cycle')} cells={design.get('cells')} "
            f"per_mac_area={design.get('per_mac_area_um2')} um2 "
            f"per_mac_period={design.get('per_mac_period_ns')} ns closed={design.get('closed')}"
        )
    verdict_line = f"  STATUS: {record['status'].upper()} ({verdict['reason']})"
    if record["status"] != STATUS_PASS:
        verdict_line += "  <-- did NOT meet timing"
        if args.expected_not_met:
            verdict_line += " (expected for this corner)"
    print(verdict_line)
    print(f"  wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
