#!/usr/bin/env python3
"""Block I/O timing budgets derived from the top-level paths.

Method (the standard budgeting step of a hierarchical flow):

1. Every hardened block is characterised at its boundary
   (tools/chip_assembly/boundary.py): per port bus, the pre-layout internal
   delay -- ``in2reg`` for an input, ``reg2out`` for an output.
2. Each block becomes a *pre-layout timing model*: a Liberty cell whose
   input setup is its ``in2reg`` and whose output clock-to-q is its
   ``reg2out``, plus a LEF of its floorplan size.  The placeholder memories
   carry their own models (tools/chip_assembly/macros.py).
3. The parent (tile) is synthesised with those models as black boxes, and
   OpenSTA times the parent: for every macro pin, the worst path through it.
   Pre-layout, that path is ``internal`` (the block's own delay) plus
   ``external`` (the driver or receiver and the parent's glue logic).
4. The floorplan adds the wire: the Manhattan distance from the block's pin
   edge to the far end of the worst path (another macro's pin edge, or the
   glue logic's expected position), priced with the routed ASAP7 buffered
   wire model (floorplans.wire_delay_model()).
5. Path slack ``S = T - U - internal - external - wire``.  When S >= 0 it is
   divided in proportion to the delays on the path, so the block's budget is
   ``internal + S * internal / (internal + external + wire)``; when S < 0 the
   path does not fit the cycle at this floorplan and is reported as an
   architectural violation (a pipeline stage or a move), with the block
   budgeted at its pre-layout delay.  A port on a combinational path through
   the block (``feedthrough_ps``) gets the through-budget instead: the block
   keeps 1.5 x its through delay + 40 ps and the two outside halves share the
   rest equally.
6. The block's SDC then carries ``set_input_delay = T - U - budget`` and
   ``set_output_delay = T - U - budget`` per port bus: the time the rest of
   the chip consumes, which is what re-closing the block against its budget
   means (no I/O false paths).

    python3 tools/chip_assembly/budgets.py --arch qwen_rom --work /tmp/.../tile_budget
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chip_assembly import boundary, case as cs, floorplans as fp, macros as mc, orfs  # noqa: E402

RESULTS = orfs.ROOT / "results/physical_abi3/asap7/chip"
PERIOD_PS = fp.CLOCK_PERIOD_NS * 1000.0
UNCERTAINTY_PS = 30.0          # clock skew + jitter allowance at a block boundary
TILE_IO_FRACTION = 0.3         # the tile's own pins: 30% of the cycle outside the tile
HARDENED = ["ot_hdc_matvec", "ot_hdc_stream", "ot_hdc_kv_stream", "ot_chip_pkg_ctrl", "ot_chip_router"]
TILE_SOURCES = ["rtl/chip/ot_chip_hdc_tile.sv", "rtl/chip/ot_chip_mesh_link.sv"]
CORE_SOURCE = "rtl/hdc/ot_hdc_core.sv"


def load_boundary(block: str) -> dict[str, Any]:
    return json.loads((RESULTS / "boundary" / f"{block}.json").read_text(encoding="utf-8"))


def block_stub(block: fp.Block, char: dict[str, Any]) -> mc.MacroSpec:
    """The pre-layout timing model of a block: its boundary delays as a cell."""
    pins = []
    for name, p in sorted(char["ports"].items()):
        if name == "clk":
            continue
        if p["width"] == 1:
            edge: Any = fp.edge_of(block, name, None)
        else:
            ranges, start, cur = [], 0, fp.edge_of(block, name, 0)
            for bit in range(1, p["width"]):
                e = fp.edge_of(block, name, bit)
                if e != cur:
                    ranges.append((start, bit - 1, cur))
                    start, cur = bit, e
            ranges.append((start, p["width"] - 1, cur))
            edge = ranges[0][2] if len(ranges) == 1 else ranges
        key = "in2reg_ps" if p["direction"] == "input" else "reg2out_ps"
        d = p.get(key)
        delay = (d / 1000.0) if d is not None else (0.02 if p["direction"] == "input" else 0.05)
        pins.append(mc.Pin(name, p["direction"], p["width"], edge,
                           timed=name != "rst_n", delay_ns=delay))
    return mc.MacroSpec(block.name, block.width_um, block.height_um, pins, kind="block-stub",
                        obs_layers=("M1", "M2", "M3", "M4", "M5", "M6"),
                        basis="pre-layout timing model from the boundary characterisation")


def derived_core() -> tuple[str, list[str]]:
    text = (orfs.ROOT / CORE_SOURCE).read_text(encoding="utf-8")
    return cs.strip_param_overrides(text, ["ot_hdc_matvec", "ot_hdc_stream"])


def tile_io_sdc(uncertainty_ps: float) -> str:
    ext = PERIOD_PS * TILE_IO_FRACTION
    return "\n".join([
        f"set clk_period {PERIOD_PS:g}",
        "create_clock -name clk -period $clk_period [get_ports clk]",
        f"set_clock_uncertainty {uncertainty_ps:g} [get_clocks clk]",
        f"set_input_delay {ext:g} -clock clk [all_inputs -no_clocks]",
        f"set_output_delay {ext:g} -clock clk [all_outputs]",
        "set_false_path -from [get_ports rst_n]",
        "set_max_fanout 32 [current_design]",
        "",
    ])


def tile_views(arch: str, out: Path) -> dict[str, dict[str, Path]]:
    """Stub views of the hardened blocks and the placeholder memories."""
    views: dict[str, dict[str, Path]] = {}
    for name in HARDENED:
        spec = block_stub(fp.BLOCKS[name], load_boundary(name))
        views[name] = mc.write_views(spec, out)
    for name, spec in fp.tile_memories(arch).items():
        views[name] = mc.write_views(spec, out)
    return views


def synth_tile(arch: str, work: Path, views: dict[str, dict[str, Path]], timeout: int) -> Path:
    core_text, removed = derived_core()
    tile = fp.hdc_tile(arch)
    spec = cs.CaseSpec(
        nickname=f"chip_tile_{arch}_budget", top="ot_chip_hdc_tile", sources=TILE_SOURCES,
        die_um=(tile.width_um, tile.height_um), sdc=tile_io_sdc(UNCERTAINTY_PS),
        macros=[cs.MacroView(n, v["lef"], v["lib"]) for n, v in views.items()],
        derived_sources={"ot_hdc_core.sv": core_text},
        extra={"SYNTH_HIERARCHICAL": 0},
    )
    cs.write_case(work, spec)
    (work / "derived_edits.json").write_text(json.dumps({"ot_hdc_core.sv": removed}, indent=2))
    netlist = orfs.results_dir(work, spec.nickname) / "1_2_yosys.v"
    if not netlist.is_file():
        with orfs.slot(f"synth tile {arch}"):
            proc = orfs.docker_make(work, f"/work/results/asap7/{spec.nickname}/base/1_2_yosys.v",
                                    "synth.log", timeout)
        if proc.returncode != 0 or not netlist.is_file():
            raise orfs.FlowError(f"tile synthesis failed; see {work}/synth.log")
    orfs.normalise_netlist(netlist)
    return netlist


ANALYSE_TCL = r"""
foreach f {%(libs)s} { read_liberty $f }
read_verilog %(netlist)s
link_design %(top)s
read_sdc %(sdc)s
set macros {%(macros)s}
foreach c [get_cells *] {
  set ref [get_property $c ref_name]
  if {[lsearch -exact $macros $ref] < 0} continue
  set buses [dict create]
  foreach pin [get_pins -of_objects $c] {
    set pn [get_name $pin]
    if {$pn eq "clk"} continue
    set net [get_nets -quiet -of_objects $pin]
    set n 0
    if {[llength $net] > 0} { set n [llength [get_pins -quiet -of_objects $net]] ; if {[llength [get_ports -quiet [get_full_name $net]]] > 0} { incr n } }
    if {$n < 2} continue
    set s [get_property $pin slack_max]
    set a [get_property $pin arrival_max_rise]
    set a2 [get_property $pin arrival_max_fall]
    if {$a2 > $a} { set a $a2 }
    regsub {\[[0-9]+\]$} $pn "" b
    puts "OTM [get_full_name $c] $ref $b $pn [get_property $pin direction] $s $a"
    dict lappend buses $b $pin
  }
  foreach b [dict keys $buses] {
    set pe [find_timing_paths -through [dict get $buses $b] -path_delay max -group_path_count 1]
    foreach e $pe {
      set sp [get_property $e startpoint]
      set ep [get_property $e endpoint]
      puts "OTE [get_full_name $c] $b [get_full_name $sp] [get_full_name $ep] [get_property $e slack]"
    }
  }
}
exit
"""


def analyse(netlist: Path, work: Path, views: dict[str, dict[str, Path]], top: str,
            sdc: Path) -> dict[str, Any]:
    libs = [*boundary.STD_LIBS, *(v["lib"] for v in views.values())]
    script = work / "analyse.tcl"
    script.write_text(ANALYSE_TCL % {
        "libs": " ".join(str(p) for p in libs), "netlist": netlist, "top": top,
        "sdc": sdc, "macros": " ".join(views),
    }, encoding="utf-8")
    proc = subprocess.run([str(boundary.STA), "-no_init", "-exit", str(script)],
                          capture_output=True, text=True, check=False, timeout=14400)
    (work / "analyse.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    pins: dict[tuple[str, str], dict[str, Any]] = {}
    for line in proc.stdout.splitlines():
        if line.startswith("OTM "):
            _, inst, ref, bus, pin, direction, slack, arr = line.split()
            key = (inst, bus)
            e = pins.setdefault(key, {"inst": inst, "master": ref, "bus": bus,
                                      "direction": direction, "bits": 0,
                                      "slack_ps": None, "arrival_ps": None})
            e["bits"] += 1
            s, a = float(slack), float(arr)
            if abs(s) < 1e20 and (e["slack_ps"] is None or s < e["slack_ps"]):
                e["slack_ps"], e["arrival_ps"] = s, a
        elif line.startswith("OTE "):
            _, inst, bus, sp, ep, slack = line.split()
            e = pins.get((inst, bus))
            if e is not None:
                e["startpoint"], e["endpoint"] = sp, ep
    return {"pins": list(pins.values()), "log": str(work / "analyse.log")}


def _edge_point(x: float, y: float, w: float, h: float, edge: str) -> tuple[float, float]:
    return {"W": (x, y + h / 2), "E": (x + w, y + h / 2),
            "S": (x + w / 2, y), "N": (x + w / 2, y + h)}[edge]


def allocate(arch: str, analysis: dict[str, Any], views: dict[str, dict[str, Path]]) -> dict[str, Any]:
    tile = fp.hdc_tile(arch)
    wire = fp.wire_delay_model()
    mems = fp.tile_memories(arch)
    sizes = {n: (fp.BLOCKS[n].width_um, fp.BLOCKS[n].height_um) for n in HARDENED}
    sizes.update({n: (s.width_um, s.height_um) for n, s in mems.items()})
    place = {p.inst: p for p in tile.placements}
    chars = {n: load_boundary(n) for n in HARDENED}
    stubs = {n: block_stub(fp.BLOCKS[n], chars[n]) for n in HARDENED}
    specs = {**stubs, **mems}

    def inst_of(pin_path: str) -> tuple[str, str]:
        inst, _, pin = pin_path.rpartition("/")
        return inst, pin

    def pin_point(inst: str, pin: str) -> tuple[float, float] | None:
        p = place.get(inst)
        if p is None:
            return None
        spec = specs[p.master]
        bus = re.sub(r"\[\d+\]$", "", pin)
        bit = int(re.search(r"\[(\d+)\]$", pin).group(1)) if "[" in pin else 0
        for sp in spec.pins:
            if sp.name == bus:
                edge = sp.edge_of_bit(bit if sp.width > 1 else 0)
                break
        else:
            edge = "W"  # the clock pin
        w, h = sizes[p.master]
        return _edge_point(p.x, p.y, w, h, edge)

    blocks: dict[str, Any] = {n: {"instance": None, "ports": {}} for n in HARDENED}
    memories: dict[str, Any] = {}
    violations = []
    for e in analysis["pins"]:
        inst, master, bus = e["inst"], e["master"], e["bus"]
        spec = specs[master]
        sp = next((p for p in spec.pins if p.name == bus), None)
        if sp is None or e["slack_ps"] is None:
            continue
        internal = (sp.delay_ns if sp.delay_ns is not None else
                    (spec.setup_ns if e["direction"] == "input" else spec.clk_to_q_ns)) * 1000.0
        if e["direction"] == "input":
            external = PERIOD_PS - UNCERTAINTY_PS - internal - e["slack_ps"]
            far = e.get("startpoint", "")
        else:
            external = PERIOD_PS - UNCERTAINTY_PS - internal - e["slack_ps"]
            far = e.get("endpoint", "")
        here_edge = sp.edge_of_bit(0)
        p = place[inst]
        w, h = sizes[master]
        here = _edge_point(p.x, p.y, w, h, here_edge)
        far_inst, far_pin = inst_of(far)
        there = pin_point(far_inst, far_pin) if far_inst else None
        far_kind = "macro" if there else ("tile pin" if "/" not in far else "glue")
        if there is None and "/" not in far:
            # a tile port: its pin group's edge midpoint
            there = tile_pin_point(tile, far)
        if there is None:
            there = tile.glue_center
        dist = abs(here[0] - there[0]) + abs(here[1] - there[1])
        wire_ps = dist * wire["ps_per_um"]
        slack = PERIOD_PS - UNCERTAINTY_PS - internal - max(external, 0.0) - wire_ps
        total = internal + max(external, 0.0) + wire_ps
        if slack >= 0:
            budget = internal + slack * internal / total if total > 0 else internal
            status = "fits"
        else:
            budget = internal
            status = "violates"
        ext_sdc = PERIOD_PS - UNCERTAINTY_PS - budget
        ft = chars[master]["ports"].get(bus, {}).get("feedthrough_ps") if master in chars else None
        if ft:
            # A combinational path crosses the block (e.g. the KV window read
            # through KVS to ME).  The pre-layout stubs carry no through arcs,
            # so the through path gets the default through-budget: the block
            # keeps 1.5 x its pre-layout delay + 40 ps, and the two outside
            # halves split the rest equally; the registered path of the same
            # port must still fit.
            ft_budget = min(1.5 * ft + 40.0, PERIOD_PS - UNCERTAINTY_PS - 100.0)
            ext_sdc = min(ext_sdc, (PERIOD_PS - UNCERTAINTY_PS - ft_budget) / 2)
            budget = PERIOD_PS - UNCERTAINTY_PS - ext_sdc
        row = {
            "direction": e["direction"], "width": e["bits"],
            "internal_ps": round(internal, 1), "external_pre_ps": round(external, 1),
            "wire_um": round(dist, 1), "wire_ps": round(wire_ps, 1),
            "path_slack_ps": round(slack, 1), "internal_budget_ps": round(budget, 1),
            "external_ps": round(ext_sdc, 1),
            "far_end": far, "far_kind": far_kind, "status": status,
            **({"feedthrough_ps": ft, "feedthrough_budget_ps": round(ft_budget, 1)} if ft else {}),
        }
        if master in blocks:
            blocks[master]["instance"] = inst
            blocks[master]["ports"][bus] = row
        else:
            memories.setdefault(master, {"instance": inst, "ports": {}})["ports"][bus] = row
        if status == "violates":
            violations.append({"instance": inst, "bus": bus, **row})
    # Ports the parent does not time (unconnected, or reset) keep a default:
    # the conventional 20% outside the block.
    for name in HARDENED:
        for port, p in chars[name]["ports"].items():
            if port in ("clk",) or port in blocks[name]["ports"]:
                continue
            blocks[name]["ports"][port] = {
                "direction": p["direction"], "width": p["width"], "status": "untimed",
                "external_ps": round(PERIOD_PS * 0.2, 1),
                "internal_budget_ps": round(PERIOD_PS * 0.8 - UNCERTAINTY_PS, 1),
            }
    return {
        "name": f"hdc_tile_{arch}",
        "arch": arch,
        "period_ps": PERIOD_PS,
        "uncertainty_ps": UNCERTAINTY_PS,
        "wire_model": wire,
        "tile_io_fraction": TILE_IO_FRACTION,
        "method": __doc__.split("Method")[1].split("python3")[0].strip(),
        "blocks": blocks,
        "memories": memories,
        "violations": violations,
    }


def tile_pin_point(tile: fp.TileFloorplan, port_bit: str) -> tuple[float, float] | None:
    bus = re.sub(r"\[\d+\]$", "", port_bit)
    bit = int(re.search(r"\[(\d+)\]$", port_bit).group(1)) if "[" in port_bit else 0
    for g in tile.pin_groups:
        if re.search(g["regex"], bus):
            lo, hi = g.get("bits", (0, 1 << 30))
            if not (lo <= bit <= hi):
                continue
            a, b = g.get("range", (0, 0))
            mid = (a + b) / 2
            return {"W": (0.0, mid), "E": (tile.width_um, mid), "S": (mid, 0.0),
                    "N": (mid, tile.height_um)}[g["edge"]]
    return None


def markdown(budget: dict[str, Any]) -> str:
    lines = [f"# Budget table {budget['name']}", "",
             f"Period {budget['period_ps']:g} ps, uncertainty {budget['uncertainty_ps']:g} ps, "
             f"wire {budget['wire_model']['ps_per_um']} ps/um.", "",
             "| Block | Port | Dir | Bits | Internal ps | External ps | Wire um | Wire ps | "
             "Path slack ps | Block budget ps | SDC delay ps | Far end | Status |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for name, b in budget["blocks"].items():
        for port, r in sorted(b["ports"].items()):
            if r["status"] == "untimed":
                continue
            lines.append(
                f"| {name} | {port} | {r['direction'][:2]} | {r['width']} | {r['internal_ps']} | "
                f"{r['external_pre_ps']} | {r['wire_um']} | {r['wire_ps']} | {r['path_slack_ps']} | "
                f"{r['internal_budget_ps']} | {r['external_ps']} | {r['far_end']} | {r['status']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arch", required=True, choices=["qwen_rom", "hbm"])
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--timeout", type=int, default=14400)
    args = ap.parse_args(argv)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    views = tile_views(args.arch, work / "stub_views")
    netlist = synth_tile(args.arch, work, views, args.timeout)
    analysis = analyse(netlist, work, views, "ot_chip_hdc_tile", work / "constraint.sdc")
    (work / "analysis.json").write_text(json.dumps(analysis, indent=1))
    budget = allocate(args.arch, analysis, views)
    budget["tile_netlist"] = {"path": str(netlist), "sha256": orfs.sha256_file(netlist)}
    out = RESULTS / "budgets" / f"hdc_tile_{args.arch}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(budget, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out.with_suffix(".md")).write_text(markdown(budget), encoding="utf-8")
    print(json.dumps({"budget": str(out), "violations": len(budget["violations"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
