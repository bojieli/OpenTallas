#!/usr/bin/env python3
"""W18: a top-level registered channel of the V4.1 ROM die, placed, clock-tree'd, globally AND detail
routed in real ASAP7, and timed with extracted parasitics for setup (60 ps) and hold (25 ps).

The die route (tools/w18/die_route.py) is bundled; this is its real-technology check on the channel that
sets the longest crossing: the horizontal SPINE between two bands of ROM-array clusters.  The spine is
32.4 um of open channel (W1 pack SPINE_H) between two cluster rows whose abstracts obstruct M1-M7 (the W10
pair's bloated OBS); over the clusters only M8/M9 are free.  The case is:

  * a die of length L x (flank + spine + flank); the flanks carry hard placement blockages and M1-M7
    routing obstructions (the neighbouring clusters), the spine is open; 60 um end caps at each end are
    open too (the hub edge and the far cluster's pins);
  * ``wires`` register chains (the spine population: 549-bit x broadcast + 256-bit result + control =
    832), each with a station flop every ``spacing`` um, the station flops FIRM in the spine;
  * ORFS flow through tools/run_abi3_physical.py (pnr: floorplan, PDN, placement, CTS, global route,
    detailed route, RCX), clock 0.92 ns, uncertainty 60 ps setup / 25 ps hold (project SDC policy).

    python3 tools/w18/channel.py --work W --length-um 4300 --spacing-um 1060 --wires 832 --run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FLOP, FLOP_W = "DFFHQNx2_ASAP7_75t_R", 1.296   # 1.134 um cell on a 24-site column pitch
ROW = 0.27
END_CAP = 60.0


def build(work: Path, length_um: float, spacing_um: float, wires: int, spine_um: float, flank_um: float,
          tag: str) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    n_st = int((length_um - 2 * END_CAP) // spacing_um)
    L = round(2 * END_CAP + n_st * spacing_um, 3)
    H = round(round((2 * flank_um + spine_um) / (8 * ROW)) * 8 * ROW, 3)
    y0 = round(round(flank_um / ROW) * ROW, 3)              # spine rows start here
    y1 = round(y0 + spine_um, 3)
    rows = int((y1 - y0 - 2 * ROW) / ROW)
    top = f"w18_chan{tag}"
    sv = [f"// W18 spine channel: {wires} chains x {n_st + 1} stations at {spacing_um} um (tools/w18/channel.py)",
          f"module {top} (input clk, input [{wires - 1}:0] d, output [{wires - 1}:0] q);"]
    for i in range(wires):
        prev = f"d[{i}]"
        for s in range(n_st + 1):
            out = f"w{i}_{s}"
            sv.append(f"  wire w{i}_{s};")
            # QN output: the chain inverts at every station; the function is irrelevant to the channel's timing
            sv.append(f"  {FLOP} r{i}_{s} (.CLK(clk), .D({prev}), .QN({out}));")
            prev = out
        # a movable output buffer per chain (global placement needs movable cells; all stations are FIRM)
        sv.append(f"  BUFx2_ASAP7_75t_R ob{i} (.A({prev}), .Y(q[{i}]));")
    sv.append("endmodule")
    gen = ROOT / "physical/w18"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / f"{top}.sv").write_text("\n".join(sv) + "\n")
    # POST_MACRO_PLACE hook: flank blockages + obstructions, FIRM station flops in the spine rows
    hook = [f"# W18 channel hook ({top}): flanks = neighbouring ROM clusters (M1-M7 obstructed, no cells)",
            "set block [ord::get_db_block]", "set tech [ord::get_db_tech]",
            "set ::ot_dbu [$tech getDbUnitsPerMicron]",
            "proc um {v} { return [expr {round($v * $::ot_dbu)}] }"]
    for (a, b) in ((0.0, y0 - 1.08), (y1 + 1.08, H)):
        hook.append(f"set bl [odb::dbBlockage_create $block [um {END_CAP}] [um {a}] [um {L - END_CAP}] [um {b}]]")
        for lay in range(1, 8):
            hook.append(f"odb::dbObstruction_create $block [$tech findLayer M{lay}] [um {END_CAP}] [um {a}] "
                        f"[um {L - END_CAP}] [um {b}]")
    flops = ["# W18 channel station flops, placed FIRM after tapcell/PDN, skipping tap cells in their row",
             "set block [ord::get_db_block]", "set ::ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
             "proc um {v} { return [expr {round($v * $::ot_dbu)}] }",
             "set ::ot_rows [dict create]",
             "foreach r [$block getRows] { dict set ::ot_rows [lindex [$r getOrigin] 1] [$r getOrient] }",
             "set ::ot_taps [dict create]",
             "foreach i [$block getInsts] { if {[string match TAP* [[$i getMaster] getName]]} { set bb [$i getBBox]; "
             "dict lappend ::ot_taps [$bb yMin] [list [$bb xMin] [$bb xMax]] } }",
             "set ::ot_used [dict create]",
             f"set ::ot_w [um {FLOP_W}]",
             "proc ot_put {name x y} {",
             "  set yy [um $y]; set xx [um $x]",
             "  set busy {}",
             "  if {[dict exists $::ot_taps $yy]} { set busy [dict get $::ot_taps $yy] }",
             "  if {[dict exists $::ot_used $yy]} { set busy [concat $busy [dict get $::ot_used $yy]] }",
             "  set moved 1",
             "  while {$moved} { set moved 0",
             "    foreach iv $busy { lassign $iv a b; if {$xx < $b && $a < $xx + $::ot_w} { set xx $b; set moved 1 } } }",
             "  set site 54; set xx [expr {(($xx + $site - 1) / $site) * $site}]",
             "  dict lappend ::ot_used $yy [list $xx [expr {$xx + $::ot_w}]]",
             "  set o R0; if {[dict exists $::ot_rows $yy]} { set o [dict get $::ot_rows $yy] }",
             "  place_inst -name $name -location [list [expr {$xx / double($::ot_dbu)}] $y] -orientation $o -status FIRM",
             "}"]
    for s in range(n_st + 1):
        xs = END_CAP / 2 if s == 0 else (L - END_CAP / 2 - (wires // rows + 2) * FLOP_W if s == n_st
                                          else END_CAP + s * spacing_um - (wires // rows + 2) * FLOP_W / 2)
        for i in range(wires):
            r, c = i % rows, i // rows
            flops.append(f"ot_put r{i}_{s} {round(xs + c * FLOP_W, 3)} {round(y0 + ROW * (1 + r), 3)}")
    (gen / f"{top}_flops.tcl").write_text("\n".join(flops) + "\n")
    (gen / f"{top}_place.tcl").write_text("\n".join(hook) + "\n")
    pin_y = f"{y0 + 2:g}-{y1 - 2:g}"
    argv = [sys.executable, str(ROOT / "tools/run_abi3_physical.py"), "--view", "asap7", "--top", top,
            "--source", f"physical/w18/{top}.sv", "--clock-period-ns", "0.92", "--clock-uncertainty-ns", "0.06",
            "--clock-uncertainty-hold-ns", "0.025", "--io-delay-fraction", "0.2", "--stages", "pnr",
            "--die-area", "0", "0", f"{L:g}", f"{H:g}", "--core-area", "1.08", "1.08", f"{L - 1.08:g}", f"{H - 1.08:g}",
            "--place-density", "0.5", "--orfs-var", "PLACE_DENSITY_LB_ADDON=", "--pin-region", r"^d\[\d+\]$=left", "--pin-region", r"^q\[\d+\]$=right",
            "--pin-region", r"^clk$=left", "--step-tcl", f"POST_MACRO_PLACE=physical/w18/{top}_place.tcl",
            "--step-tcl", f"POST_PDN=physical/w18/{top}_flops.tcl",
            "--nickname-tag", f"w18_chan{tag}", "--keep-workdir", str(work / "run"), "--force",
            "--output", str(work / "physical.json")]
    man = dict(top=top, length_um=L, spacing_um=spacing_um, stations=n_st + 1, segments=n_st, wires=wires,
               die_um=[L, H], spine_um=[y0, y1], flank_um=flank_um, end_cap_um=END_CAP, flop=FLOP,
               flops=wires * (n_st + 1), rows_in_spine=rows, argv=argv[1:])
    (work / "manifest.json").write_text(json.dumps(man, indent=1))
    return man


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--length-um", type=float, default=4300)
    ap.add_argument("--spacing-um", type=float, default=1060)
    ap.add_argument("--wires", type=int, default=832)
    ap.add_argument("--spine-um", type=float, default=32.4)
    ap.add_argument("--flank-um", type=float, default=150.0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args(argv)
    m = build(a.work.resolve(), a.length_um, a.spacing_um, a.wires, a.spine_um, a.flank_um, a.tag)
    print(json.dumps({k: v for k, v in m.items() if k != "argv"}, indent=1))
    if a.run:
        return subprocess.run(m["argv"] and [sys.executable, *m["argv"]], cwd=ROOT).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
