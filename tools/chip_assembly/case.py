"""One ORFS design case: config.mk, SDC, pin constraints, PDN, macro views.

Used for every level: a hardened block (level 1), the tile (level 2) and the
die (level 3).  Hierarchy is explicit rather than ORFS's BLOCKS make feature:
each parent case receives its children's abstracts (LEF, Liberty timing
model, GDS) as ``ADDITIONAL_*`` views and places them with
``MACRO_PLACEMENT_TCL``, so each block's constraints, pin placement and power
grid are this flow's own.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import orfs

TCL_DIR = Path(__file__).resolve().parent / "tcl"
EDGE_REGION = {"W": "left", "E": "right", "N": "top", "S": "bottom"}


@dataclass
class MacroView:
    name: str
    lef: Path
    lib: Path
    gds: Path | None = None


@dataclass
class CaseSpec:
    nickname: str
    top: str
    sources: list[str]                       # repository-relative, or absolute derived files
    die_um: tuple[float, float]
    sdc: str
    core_margin_um: float = 2.0
    params: dict[str, Any] = field(default_factory=dict)
    pin_groups: list[dict[str, Any]] = field(default_factory=list)   # {edge, names, range?}
    pdn_tcl: Path | None = None
    min_layer: str = "M2"
    max_layer: str = "M6"
    io_layers: tuple[str, str] = ("M4", "M5")   # (horizontal, vertical)
    place_density: float = 0.60
    macros: list[MacroView] = field(default_factory=list)
    blackboxes: list[str] = field(default_factory=list)
    macro_placement_tcl: str | None = None
    macro_halo_um: tuple[float, float] = (2.0, 2.0)
    extra: dict[str, Any] = field(default_factory=dict)
    derived_sources: dict[str, str] = field(default_factory=dict)   # file name -> text
    include_dirs: list[str] = field(default_factory=list)          # repository-relative


def io_constraints_tcl(groups: list[dict[str, Any]]) -> str:
    lines = ["# Pin placement from the parent floorplan (tools/chip_assembly)."]
    for g in groups:
        if not g["names"]:
            continue
        region = EDGE_REGION[g["edge"]]
        span = g.get("range")
        where = f"{region}:{span[0]:g}-{span[1]:g}" if span else f"{region}:*"
        names = " ".join(g["names"])
        lines.append(f"set_io_pin_constraint -group -order -region {where} -pin_names {{{names}}}")
    return "\n".join(lines) + "\n"


def write_case(case: Path, spec: CaseSpec) -> None:
    case.mkdir(parents=True, exist_ok=True)
    views = case / "views"
    views.mkdir(exist_ok=True)
    w, h = spec.die_um
    m = spec.core_margin_um
    sources = []
    for src in spec.sources:
        sources.append(f"/src/{src}")
    if spec.derived_sources:
        derived = case / "derived"
        derived.mkdir(exist_ok=True)
        for name, text in spec.derived_sources.items():
            (derived / name).write_text(text, encoding="utf-8")
            sources.append(f"/work/derived/{name}")
    lefs, libs, gdss = [], [], []
    for mv in spec.macros:
        for attr in ("lef", "lib", "gds"):
            src = getattr(mv, attr)
            if src is None:
                continue
            dst = views / Path(src).name
            if Path(src).resolve() != dst.resolve():
                shutil.copy2(src, dst)
            {"lef": lefs, "lib": libs, "gds": gdss}[attr].append(f"/work/views/{dst.name}")
    cfg = [
        f"export DESIGN_NICKNAME = {spec.nickname}",
        f"export DESIGN_NAME = {spec.top}",
        "export PLATFORM = asap7",
        "export VERILOG_FILES = " + " ".join(sources),
        "export VERILOG_DEFINES = -DSYNTHESIS",
        "export SDC_FILE = /work/constraint.sdc",
        f"export DIE_AREA = 0 0 {w:g} {h:g}",
        f"export CORE_AREA = {m:g} {m:g} {w - m:g} {h - m:g}",
        f"export PLACE_DENSITY = {spec.place_density:g}",
        "export PLACE_DENSITY_LB_ADDON = 0.05",
        "export SYNTH_REPEATABLE_BUILD = 1",
        "export SYNTH_HIERARCHICAL = 0",
        "export SYNTH_MEMORY_MAX_BITS = 65536",
        "export LEC_CHECK = 0",
        "export TNS_END_PERCENT = 100",
        "export SKIP_REPORT_METRICS = 0",
        "export REPORT_CLOCK_SKEW = 1",
        "export ASAP7_USE_VT = RVT",
        "export CORNER = TC",
        f"export MIN_ROUTING_LAYER = {spec.min_layer}",
        f"export MAX_ROUTING_LAYER = {spec.max_layer}",
        f"export IO_PLACER_H = {spec.io_layers[0]}",
        f"export IO_PLACER_V = {spec.io_layers[1]}",
        "export PLACE_PINS_ARGS = -min_distance 1 -min_distance_in_tracks",
    ]
    if spec.include_dirs:
        cfg.append("export VERILOG_INCLUDE_DIRS = " + " ".join(f"/src/{d}" for d in spec.include_dirs))
    if spec.params:
        cfg.append("export VERILOG_TOP_PARAMS = " + " ".join(f"{k} {v}" for k, v in spec.params.items()))
    if spec.pdn_tcl:
        shutil.copy2(spec.pdn_tcl, case / "pdn.tcl")
        cfg.append("export PDN_TCL = /work/pdn.tcl")
    if spec.pin_groups:
        (case / "io_constraints.tcl").write_text(io_constraints_tcl(spec.pin_groups), encoding="utf-8")
        cfg.append("export IO_CONSTRAINTS = /work/io_constraints.tcl")
    if lefs:
        cfg.append("export ADDITIONAL_LEFS = " + " ".join(lefs))
        cfg.append("export ADDITIONAL_LIBS = " + " ".join(libs))
    if gdss:
        cfg.append("export ADDITIONAL_GDS = " + " ".join(gdss))
    no_gds = [mv.name for mv in spec.macros if mv.gds is None]
    if no_gds:
        cfg.append("export GDS_ALLOW_EMPTY = " + "|".join(["fakeram.*", *no_gds]))
    if spec.blackboxes:
        cfg.append("export SYNTH_BLACKBOXES = " + " ".join(spec.blackboxes))
    if spec.macro_placement_tcl:
        (case / "macro_placement.tcl").write_text(spec.macro_placement_tcl, encoding="utf-8")
        cfg.append("export MACRO_PLACEMENT_TCL = /work/macro_placement.tcl")
        cfg.append(f"export MACRO_PLACE_HALO = {spec.macro_halo_um[0]:g} {spec.macro_halo_um[1]:g}")
    for key, value in spec.extra.items():
        cfg.append(f"export {key} = {value}")
    (case / "config.mk").write_text("\n".join(cfg) + "\n", encoding="utf-8")
    sdc = case / "constraint.sdc"
    if sdc.exists():
        # A later phase rewrites the constraints; keep the synthesis products
        # (they depend on the SDC's mtime) by preserving it.
        stat = sdc.stat()
        sdc.write_text(spec.sdc, encoding="utf-8")
        os.utime(sdc, (stat.st_atime, stat.st_mtime))
    else:
        sdc.write_text(spec.sdc, encoding="utf-8")


def strip_param_overrides(text: str, modules: list[str]) -> tuple[str, list[str]]:
    """Remove ``#(...)`` parameter overrides from instances of hardened modules.

    A hardened block is a liberty cell and has no parameters, so an instance
    that passes any cannot elaborate.  The caller asserts every override equals
    the block's hardened value (they are the same localparams); the edit is
    recorded in the case record.
    """
    removed = []
    for mod in modules:
        pattern = re.compile(r"\b(" + re.escape(mod) + r")\s*#\s*\(")
        while True:
            mt = pattern.search(text)
            if not mt:
                break
            depth, i = 1, mt.end()
            while depth:
                depth += {"(": 1, ")": -1}.get(text[i], 0)
                i += 1
            removed.append(text[mt.start():i])
            text = text[:mt.start()] + mod + text[i:]
    return text, removed


def metrics(case: Path, nickname: str) -> dict[str, Any]:
    """The finish metrics ORFS reports (metadata.json, else the stage JSONs)."""
    rep = orfs.reports_dir(case, nickname)
    meta = orfs.read_json(rep / "metadata.json") or {}
    if not meta:
        for js in sorted(orfs.logs_dir(case, nickname).glob("*.json")):
            meta.update(orfs.read_json(js) or {})
    keys = {
        "setup_wns_ps": "finish__timing__setup__ws",
        "setup_tns_ps": "finish__timing__setup__tns",
        "setup_violations": "finish__timing__drv__setup_violation_count",
        "hold_wns_ps": "finish__timing__hold__ws",
        "hold_tns_ps": "finish__timing__hold__tns",
        "hold_violations": "finish__timing__drv__hold_violation_count",
        "max_slew_violations": "finish__timing__drv__max_slew",
        "max_cap_violations": "finish__timing__drv__max_cap",
        "max_fanout_violations": "finish__timing__drv__max_fanout",
        "fmax_hz": "finish__timing__fmax",
        "clock_skew_ps": "finish__clock__skew__setup",
        "core_area_um2": "finish__design__core__area",
        "die_area_um2": "finish__design__die__area",
        "stdcell_area_um2": "finish__design__instance__area__stdcell",
        "macro_area_um2": "finish__design__instance__area__macros",
        "stdcell_count": "finish__design__instance__count__stdcell",
        "macro_count": "finish__design__instance__count__macros",
        "utilization": "finish__design__instance__utilization",
        "wirelength_um": "detailedroute__route__wirelength",
        "vias": "detailedroute__route__vias",
        "drc_errors": "detailedroute__route__drc_errors",
        "antenna_violating_nets": "detailedroute__antenna__violating__nets",
        "power_total_w": "finish__power__total",
    }
    out = {k: meta.get(v) for k, v in keys.items()}
    out["flow_errors"] = {k: v for k, v in meta.items() if k.endswith("__flow__errors__count") and v}
    return out


KEEP_AFTER_SYNTH = {"1_1_yosys_canonicalize.rtlil", "1_2_yosys.v", "mem.json", "clock_period.txt"}


def purge_after_synthesis(case: Path, nickname: str) -> list[str]:
    """Remove every flow product downstream of the synthesised netlist.

    ORFS reads the SDC into 1_2_yosys.sdc / 1_synth.sdc once; a new budget
    must restart the flow from the netlist, not resume on the old constraints.
    """
    import shutil as _sh
    removed = []
    for sub in ("results", "logs", "reports", "objects"):
        d = case / sub / "asap7" / nickname / "base"
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if sub == "results" and f.name in KEEP_AFTER_SYNTH:
                continue
            if sub == "objects":
                continue
            if sub == "logs" and f.name.startswith("1_1") or f.name.startswith("1_2_yosys.log"):
                continue
            (_sh.rmtree if f.is_dir() else Path.unlink)(f)
            removed.append(f"{sub}/{f.name}")
    return removed


def ensure_constraints(case: Path, nickname: str, sdc_text: str) -> bool:
    """Purge downstream products when the constraints changed since the last run."""
    import hashlib
    digest = hashlib.sha256(sdc_text.encode()).hexdigest()
    marker = case / "flow_sdc.sha256"
    if marker.is_file() and marker.read_text().strip() == digest:
        return False
    purge_after_synthesis(case, nickname)
    marker.write_text(digest + "\n")
    return True

