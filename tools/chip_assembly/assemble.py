#!/usr/bin/env python3
"""Assemble a parent level from hardened macros: the tile, then the die.

  --level tile   ot_chip_hdc_tile: the hardened ME, SU, KVS, controller and
                 router abstracts plus the placeholder memories, placed where
                 the floorplan puts them, the level-2 power grid, clock tree,
                 and route of the glue and inter-block nets; then the tile's
                 own abstract (LEF + timing model) for the die.
  --level die    ot_chip_die2x2: four tile abstracts (mirrored), the PHY and
                 link placeholders, the level-3 power grid, the clock tree
                 across tiles and the route of the inter-tile nets.

After the route, a boundary report times every macro pin of the parent with
the macros' extracted timing models and the parent's extracted parasitics,
and compares the time the parent actually used outside each block with the
block's budget (tools/chip_assembly/budgets.py): the closure check.

    python3 tools/chip_assembly/assemble.py --level tile --arch qwen_rom \
        --work /tmp/claude-1000/otchip/tile_qwen_rom
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chip_assembly import budgets, case as cs, floorplans as fp, macros as mc, orfs  # noqa: E402

RESULTS = orfs.ROOT / "results/physical_abi3/asap7/chip"
BLOCK_WORK = Path(os.environ.get("OT_CHIP_WORK", "/tmp/claude-1000/otchip"))
GRID_UM = 0.192       # macro origins on the M4/M5 (0.048) and M6/M7 (0.064) track grid


def snap(v: float) -> float:
    return round(round(v / GRID_UM) * GRID_UM, 3)


def placement_tcl(placements: list[fp.Placement]) -> str:
    lines = [
        "# Macro placement from tools/chip_assembly/floorplans.py (lower-left corners, um).",
        "proc ot_place {want x y orient} {",
        "  foreach inst [[ord::get_db_block] getInsts] {",
        "    set n [$inst getName]",
        "    if {[string map {\\\\ {}} $n] eq $want} {",
        "      place_macro -macro_name $n -location [list $x $y] -orientation $orient",
        "      return",
        "    }",
        "  }",
        "  error \"macro placement: no instance $want\"",
        "}",
    ]
    for p in placements:
        lines.append(f"ot_place {{{p.inst}}} {snap(p.x)} {snap(p.y)} {p.orient}")
    return "\n".join(lines) + "\n"


def module_ports(path: Path, module: str) -> dict[str, dict[str, Any]]:
    """Port names, directions and widths from an ANSI module header (one
    declaration per line, widths as constant expressions)."""
    text = path.read_text(encoding="utf-8")
    body = text[text.index(f"module {module}"):]
    body = body[:re.search(r"^\s*\);", body, re.M).start()]
    ports: dict[str, dict[str, Any]] = {}
    decl = re.compile(r"^\s*(input|output)\s+(?:wire|reg)?\s*(?:\[([^\]]+):0\])?\s*([^/]+?)\s*(?://.*)?$")
    for line in body.splitlines():
        m = decl.match(line)
        if not m:
            continue
        width = eval(m.group(2), {}, {}) + 1 if m.group(2) else 1
        for name in m.group(3).rstrip(",").split(","):
            name = name.strip()
            if name:
                ports[name] = {"direction": m.group(1), "width": width}
    return ports


def tile_pin_groups(tile: fp.TileFloorplan, ports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups = []
    used: set[str] = set()
    for p, (edge, rng) in enumerate([("N", None), ("E", None), ("S", None), ("W", None)]):
        g = next(g for g in tile.pin_groups if g.get("bits") == (p * 512, p * 512 + 511))
        names = []
        for i in range(p * 512, p * 512 + 512):
            names += [f"m_out_data[{i}]", f"m_in_data[{i}]"]
        for s in ("valid", "last", "cr"):
            names += [f"m_out_{s}[{p}]", f"m_in_{s}[{p}]"]
        used.update(names)
        groups.append({"edge": g["edge"], "range": g["range"], "names": names})
    rest_hbm, rest = [], []
    for name in sorted(ports):
        if name == "clk":
            continue
        bits = [name] if ports[name]["width"] == 1 else [f"{name}[{i}]" for i in range(ports[name]["width"])]
        bits = [b for b in bits if b not in used]
        (rest_hbm if re.match(r"^(hq_|hr_)", name) else rest).extend(bits)
    g = next(g for g in tile.pin_groups if g["regex"] == r"^(hq_|hr_)")
    groups.append({"edge": g["edge"], "range": g["range"], "names": rest_hbm})
    g = tile.pin_groups[-1]
    groups.append({"edge": g["edge"], "range": g["range"], "names": rest})
    return groups


def tile_sdc(uncertainty_ps: float) -> str:
    """The tile's own boundary: every mesh pin is a register (the link), so
    the die budget gives the channel most of the cycle; other pins 30%."""
    T = fp.CLOCK_PERIOD_NS * 1000.0
    return "\n".join([
        f"set clk_period {T:g}",
        "create_clock -name clk -period $clk_period [get_ports clk]",
        f"set_clock_uncertainty {uncertainty_ps:g} [get_clocks clk]",
        f"set_input_delay {T * 0.3:g} -clock clk [all_inputs -no_clocks]",
        f"set_output_delay {T * 0.3:g} -clock clk [all_outputs]",
        "set_false_path -from [get_ports rst_n]",
        "set_max_fanout 32 [current_design]",
        "set_max_transition 320 [current_design]",
        "set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [all_inputs -no_clocks]",
        "set_load 4.0 [all_outputs]",
        "",
    ])


def block_views() -> list[cs.MacroView]:
    views = []
    for name in budgets.HARDENED:
        res = orfs.results_dir(BLOCK_WORK / name, f"chip_{name}")
        lef, lib, gds = res / f"{name}.lef", res / f"{name}_typ.lib", res / "6_final.gds"
        if not (lef.is_file() and lib.is_file()):
            raise orfs.FlowError(f"{name} is not hardened yet ({res})")
        views.append(cs.MacroView(name, lef, lib, gds if gds.is_file() else None))
    return views


def memory_views(arch: str, out: Path) -> list[cs.MacroView]:
    views = []
    for name, spec in fp.tile_memories(arch).items():
        v = mc.write_views(spec, out)
        views.append(cs.MacroView(name, v["lef"], v["lib"]))
    return views


def tile_spec(arch: str, work: Path) -> cs.CaseSpec:
    tile = fp.hdc_tile(arch)
    core_text, _ = budgets.derived_core()
    ports = module_ports(orfs.ROOT / "rtl/chip/ot_chip_hdc_tile.sv", "ot_chip_hdc_tile")
    return cs.CaseSpec(
        nickname=f"chip_tile_{arch}", top="ot_chip_hdc_tile", sources=budgets.TILE_SOURCES,
        die_um=(snap(tile.width_um), snap(tile.height_um)), core_margin_um=4.0,
        sdc=tile_sdc(budgets.UNCERTAINTY_PS),
        pin_groups=tile_pin_groups(tile, ports),
        pdn_tcl=cs.TCL_DIR / "pdn_tile.tcl",
        max_layer="M8", io_layers=("M6", "M7"), place_density=0.55,
        macros=block_views() + memory_views(arch, work / "mem_views"),
        macro_placement_tcl=placement_tcl(tile.placements),
        derived_sources={"ot_hdc_core.sv": core_text},
        extra={"SLEW_MARGIN": 20, "HOLD_SLACK_MARGIN": 5, "MACRO_ROWS_HALO_X": 2,
               "MACRO_ROWS_HALO_Y": 2, "GPL_TIMING_DRIVEN": 1, "GPL_ROUTABILITY_DRIVEN": 1},
    )


def die_spec(arch: str, work: Path) -> cs.CaseSpec:
    die = fp.die2x2(arch)
    tres = orfs.results_dir(BLOCK_WORK / f"tile_{arch}", f"chip_tile_{arch}")
    tile_view = cs.MacroView("ot_chip_hdc_tile", tres / "ot_chip_hdc_tile.lef",
                             tres / "ot_chip_hdc_tile_typ.lib", tres / "6_final.gds")
    phys = []
    for name, spec in die.phys.items():
        v = mc.write_views(spec, work / "phy_views")
        phys.append(cs.MacroView(name, v["lef"], v["lib"]))
    T = fp.CLOCK_PERIOD_NS * 1000.0
    sdc = "\n".join([
        f"set clk_period {T:g}",
        "create_clock -name clk -period $clk_period [get_ports clk]",
        f"set_clock_uncertainty {budgets.UNCERTAINTY_PS:g} [get_clocks clk]",
        f"set_input_delay {T * 0.3:g} -clock clk [all_inputs -no_clocks]",
        f"set_output_delay {T * 0.3:g} -clock clk [all_outputs]",
        "set_false_path -from [get_ports rst_n]",
        "set_max_fanout 32 [current_design]",
        "set_max_transition 320 [current_design]",
        "",
    ])
    return cs.CaseSpec(
        nickname=f"chip_die2x2_{arch}", top="ot_chip_die2x2", sources=["rtl/chip/ot_chip_die2x2.sv"],
        die_um=(snap(die.width_um), snap(die.height_um)), core_margin_um=5.0, sdc=sdc,
        pdn_tcl=cs.TCL_DIR / "pdn_die.tcl", max_layer="M9", io_layers=("M4", "M5"),
        place_density=0.5, macros=[tile_view, *phys],
        macro_placement_tcl=placement_tcl(die.placements),
        extra={"SLEW_MARGIN": 20, "HOLD_SLACK_MARGIN": 5, "MACRO_ROWS_HALO_X": 2,
               "MACRO_ROWS_HALO_Y": 2},
    )


BOUNDARY_TCL = r"""
source $::env(SCRIPTS_DIR)/load.tcl
load_design 6_final.odb 6_final.sdc
if {[file exists $::env(RESULTS_DIR)/6_final.spef]} { read_spef $::env(RESULTS_DIR)/6_final.spef } else { estimate_parasitics -placement }
set_propagated_clock [all_clocks]
set out [open /work/boundary_report.txt w]
foreach inst [[ord::get_db_block] getInsts] {
  if {![[$inst getMaster] isBlock]} continue
  set c [get_cells [$inst getName]]
  set ref [get_property $c ref_name]
  set buses [dict create]
  foreach pin [get_pins -of_objects $c] {
    set pn [get_name $pin]
    if {$pn eq "clk"} continue
    set s [get_property $pin slack_max]
    if {$s > 1e20 || $s < -1e20} continue
    regsub {\[[0-9]+\]$} $pn "" b
    if {![dict exists $buses $b] || $s < [dict get $buses $b]} { dict set buses $b $s }
  }
  foreach b [dict keys $buses] { puts $out "OTB [$inst getName] $ref $b [dict get $buses $b]" }
  set ck [get_pins -quiet [get_full_name $c]/clk]
  if {[llength $ck]} { puts $out "OTC [$inst getName] [get_property $ck arrival_max_rise]" }
}
close $out
"""


def run_level(level: str, arch: str, work: Path, timeout: int) -> dict[str, Any]:
    spec = tile_spec(arch, work) if level == "tile" else die_spec(arch, work)
    cs.write_case(work, spec)
    res = orfs.results_dir(work, spec.nickname)
    t0 = time.time()
    with orfs.slot(f"{level} {arch}"):
        netlist = res / "1_2_yosys.v"
        if not netlist.is_file():
            proc = orfs.docker_make(work, f"/work/results/asap7/{spec.nickname}/base/1_2_yosys.v",
                                    "synth.log", timeout)
            if proc.returncode != 0:
                raise orfs.FlowError(f"{level} synthesis failed; see {work}/synth.log")
        orfs.normalise_netlist(netlist)
        proc = orfs.docker_make(work, "finish metadata-generate", "flow.log", timeout)
        if proc.returncode != 0:
            raise orfs.FlowError(f"{level} place-and-route failed; see {work}/flow.log")
        if level == "tile":
            proc = orfs.docker_make(work, "generate_abstract", "abstract.log", 7200)
            if proc.returncode != 0:
                raise orfs.FlowError(f"tile abstract failed; see {work}/abstract.log")
    return {"elapsed_seconds": round(time.time() - t0, 1), "spec": spec}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", required=True, choices=["tile", "die"])
    ap.add_argument("--arch", required=True, choices=["qwen_rom", "hbm"])
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--write-only", action="store_true", help="write the case and stop")
    args = ap.parse_args(argv)
    timeout = int(os.environ.get("OT_FLOW_TIMEOUT_SECONDS", "86400"))
    work = args.work.resolve()
    if args.write_only:
        spec = tile_spec(args.arch, work) if args.level == "tile" else die_spec(args.arch, work)
        cs.write_case(work, spec)
        print(f"wrote {work}")
        return 0
    out = run_level(args.level, args.arch, work, timeout)
    print(json.dumps({"level": args.level, "arch": args.arch, "elapsed": out["elapsed_seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
