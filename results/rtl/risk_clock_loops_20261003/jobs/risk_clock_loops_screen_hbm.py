#!/usr/bin/env python3
"""Control-loop clock screen at the sign-off setup corner (SS, ASAP7 RVT), pre-layout.

Disaster-class risk check of 2026-10-03: can each design's loop-carried CONTROL (sequencer
issue/next-PC, ready = !active && !pend handshakes, credit/arbiter loops, collective sequencers,
HBM scheduler, accept/commit) run at its domain clock?  Datapaths pipeline; a control loop cannot
without adding a cycle per iteration, so its single-cycle register-to-register closure is the
question.

For one block this script:
  1. synthesises it with the pinned driver's Yosys script (tools/run_abi3_physical.py run_synthesis:
     Yosys 0.68 + ABC mapped to ASAP7 RVT TT at the target period), plus defines/includes and
     ``rename -wire`` so the timed path reads in RTL register names;
  2. times the mapped netlist in the pinned ORFS image with OpenROAD/OpenSTA on the SS liberty
     (asap7 WC: 0.63 V, 100 C), 60 ps setup uncertainty, ideal clock, no wires:
       * ``raw``      -- the netlist as synthesised (no buffering: a fan-out-limited block reads
                         pessimistic here, see repo memory high-fanout-not-logic-depth);
       * ``repaired`` -- after placement, ``repair_design`` (max slew 320 ps / max fanout) and
                         ``repair_timing -setup`` (sizing, buffering, cloning);
     each reported register-to-register (the loop) and in total (with 20 %-of-period I/O delays).
     ``repaired`` places the block (global + detailed, platform setRC wire parasitics) before the
     repair, so buffer trees are real; it is still pre-CTS and pre-route;
  3. the worst register-to-register path of each phase (start/end, cells, per-cell delay, the
     largest-fanout net on it).

Neither phase is sign-off: the routed SS/FF record (run_abi3_physical --stages synth,pnr
--orfs-corner WC --hold-corners WC,BC + tools/w18/corner_sta.py) is the authority.  ``fmax`` here
is 1 / (period - WNS) with the 60 ps uncertainty inside the WNS, i.e. the clock at which the path
would just meet including the uncertainty.

    python3 tools/risk_clock_loops_screen.py --top T --source F [--source F ...] [--param K=V ...] \
        --period-ns 0.833 --work DIR --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# HBM-screen copy of tools/risk_clock_loops_screen.py (2026-10-03): adds --macro (hard-macro LEF + SS liberty,
# macros FIRM-placed in columns from the core origin) and an IO-perimeter-aware utilisation; otherwise identical.
ROOT = Path.home() / "rcl-20261003/src"
MACRO_DIRS = ["physical/asap7_memory_macros", "physical/asap7_memory_macros_v2"]
IMAGE = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TT_LIBS = ["asap7sc7p5t_AO_RVT_TT_nldm_211120.lib", "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib",
           "asap7sc7p5t_OA_RVT_TT_nldm_211120.lib", "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
           "asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib"]
DONT_USE = ["*x1p*_ASAP7*", "*xp*_ASAP7*", "SDF*", "ICG*"]   # the pinned driver's asap7 view
SS_LIBS = ["asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz",
           "asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib",
           "asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tcl(top: str, period_ps: float, clock_port: str, false_from: list[str], max_fanout: int, util: int,
        focus: list[str] | None = None, macros: list[str] | None = None) -> str:
    libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{lib}" for lib in SS_LIBS)
    libs += "".join(f"\nread_liberty /w/{m}_ss.lib" for m in macros or [])
    mlefs = "".join(f"\nread_lef /w/{m}.lef" for m in macros or [])
    io = 0.2 * period_ps
    pairs = []
    for f in focus or []:
        name, rx = f.split("=", 1)
        pairs.append(f"{name} {{{rx}}}")
    focus_tcl = "set ::ot_focus [list " + " ".join(pairs) + "]"
    ff = " ".join(false_from)
    return f"""
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef{mlefs}
{libs}
read_verilog /w/mapped.v
link_design {top}
create_clock -name clk -period {period_ps} [get_ports {clock_port}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ins [delete_from_list [all_inputs] [get_ports {clock_port}]]
set_input_delay {io} -clock clk $ins
set_output_delay {io} -clock clk [all_outputs]
foreach p {{{ff}}} {{ if {{[llength [get_ports -quiet $p]]}} {{ set_false_path -from [get_ports $p] }} }}
set_max_transition 320 [current_design]
set_max_fanout {max_fanout} [current_design]
{focus_tcl}
proc ot_phase {{tag}} {{
  set r2r [find_timing_paths -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay max -group_path_count 1]
  if {{[llength $r2r]}} {{ puts "OT_${{tag}}_R2R_WS [get_property [lindex $r2r 0] slack]" }} else {{ puts "OT_${{tag}}_R2R_WS NONE" }}
  puts "OT_${{tag}}_ALL_WS [sta::worst_slack_cmd max]"
  puts "OT_${{tag}}_TNS [sta::total_negative_slack_cmd max]"
  puts "OT_${{tag}}_CELLS [llength [get_cells *]]"
  puts "OT_${{tag}}_PATH_BEGIN"
  report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -fields {{fanout cap slew}} -digits 1
  puts "OT_${{tag}}_PATH_END"
  foreach {{fname fre}} $::ot_focus {{
    set pins {{}}
    foreach c [concat [all_registers -cells] [get_cells -quiet -filter "ref_name=~ICG*" *]] {{ if {{[regexp -- $fre [get_full_name $c]]}} {{ foreach pn [get_pins -of_objects $c -filter "direction==input"] {{ set nm [get_property $pn lib_pin_name]; if {{$nm eq "D" || $nm eq "ENA" || $nm eq "SE"}} {{ lappend pins $pn }} }} }} }}
    puts "OT_${{tag}}_FOCUS_N_${{fname}} [llength $pins]"
    if {{[llength $pins]}} {{
      set fp [find_timing_paths -to $pins -path_delay max -group_path_count 1]
      if {{[llength $fp]}} {{ puts "OT_${{tag}}_FOCUS_WS_${{fname}} [get_property [lindex $fp 0] slack]" }}
      puts "OT_${{tag}}_FPATH_${{fname}}_BEGIN"
      report_checks -to $pins -path_delay max -group_path_count 1 -fields {{fanout cap slew}} -digits 1
      puts "OT_${{tag}}_FPATH_${{fname}}_END"
    }}
  }}
  puts "OT_${{tag}}_IOPATH_BEGIN"
  report_checks -path_delay max -group_path_count 1 -fields {{fanout}} -digits 1
  puts "OT_${{tag}}_IOPATH_END"
}}
ot_phase RAW
source {PLAT}/setRC.tcl
initialize_floorplan -utilization {util} -aspect_ratio 1 -core_space 2 -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set blk [ord::get_db_block]; set core [$blk getCoreArea]; set mx [$core xMin]; set my [$core yMin]; set colw 0
foreach inst [$blk getInsts] {{ set ms [$inst getMaster]; if {{[$ms isBlock]}} {{
  if {{$my + [$ms getHeight] > [$core yMax]}} {{ set mx [expr {{$mx + $colw + 4000}}]; set my [$core yMin]; set colw 0 }}
  $inst setOrigin $mx $my; $inst setPlacementStatus FIRM
  set my [expr {{$my + [$ms getHeight] + 4000}}]; if {{[$ms getWidth] > $colw}} {{ set colw [$ms getWidth] }} }} }}
place_pins -hor_layers M4 -ver_layers M5
global_placement -density 0.6
estimate_parasitics -placement
repair_design -slew_margin 0 -cap_margin 0
detailed_placement
estimate_parasitics -placement
repair_timing -setup -setup_margin 0
detailed_placement
estimate_parasitics -placement
ot_phase REP
exit
"""


MOD_DEF = re.compile(r"^\s*module\s+(\w+)", re.M)
INST = re.compile(r"^\s*(\w+)\s*(?:#\s*\(|\w+\s*\()", re.M)
KEYWORDS = {"module", "always", "always_ff", "always_comb", "assign", "if", "else", "for", "case", "begin",
            "end", "function", "task", "wire", "reg", "logic", "input", "output", "inout", "parameter",
            "localparam", "generate", "genvar", "initial", "return", "integer", "while", "repeat"}


def resolve(top: str, extra: list[str], listfile: str, incs: list[str], blackboxes: list[str]) -> list[str]:
    """Closure of ``top`` over the module definitions in a runtime source list (+ explicit sources)."""
    files = [l.strip() for l in (ROOT / listfile).read_text().splitlines() if l.strip() and not l.startswith("#")]
    files = list(dict.fromkeys(extra + files))
    defs: dict[str, str] = {}
    for f in files:
        for m in MOD_DEF.finditer((ROOT / f).read_text(errors="replace")):
            defs.setdefault(m.group(1), f)
    need, todo, seen = [], [top], set()
    while todo:
        mod = todo.pop()
        if mod in seen or mod not in defs:
            continue
        seen.add(mod)
        f = defs[mod]
        if f not in need:
            need.append(f)
        if mod in blackboxes:          # its definition is read (for its ports), its body is not descended
            continue
        text = (ROOT / f).read_text(errors="replace")
        text = re.sub(r"//.*", "", text)
        for m in INST.finditer(text):
            name = m.group(1)
            if name not in KEYWORDS and name in defs:
                todo.append(name)
    for f in extra:
        if f not in need:
            need.append(f)
    return need


def parse_path(text: str) -> dict:
    out = {"startpoint": None, "endpoint": None, "cells": [], "max_fanout_on_path": 0}
    m = re.search(r"Startpoint: (\S+)", text)
    out["startpoint"] = m.group(1) if m else None
    m = re.search(r"Endpoint: (\S+)", text)
    out["endpoint"] = m.group(1) if m else None
    # rows: Fanout Cap Slew Delay Time Description  (net rows carry fanout + cap)
    for line in text.splitlines():
        cell = re.match(r"\s*((?:[\d.\-]+\s+)+)[\^v]\s+(\S+)\s+\((\S+)\)", line)
        if cell:
            nums = [float(x) for x in cell.group(1).split()]
            # columns: [fanout cap] slew delay time
            if len(nums) >= 3:
                row = {"slew_ps": nums[-3], "delay_ps": nums[-2], "pin": cell.group(2), "cell": cell.group(3)}
                if len(nums) == 5:
                    row["fanout"] = int(nums[0])
                    out["max_fanout_on_path"] = max(out["max_fanout_on_path"], int(nums[0]))
                out["cells"].append(row)
    m = re.search(r"([\-\d.]+)\s+data arrival time", text)
    out["arrival_ps"] = float(m.group(1)) if m else None
    out["logic_cells"] = len(out["cells"])
    out["worst_cell"] = max(out["cells"], key=lambda c: c["delay_ps"]) if out["cells"] else None
    return out


def block(text: str, tag: str) -> str:
    m = re.search(rf"OT_{tag}_BEGIN\n(.*?)OT_{tag}_END", text, re.S)
    return m.group(1) if m else ""


def num(text: str, key: str):
    m = re.search(rf"^OT_{key} (\S+)", text, re.M)
    if not m or m.group(1) in ("NONE", "INF"):
        return None
    return float(m.group(1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", required=True)
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--clock-port", default="clk")
    ap.add_argument("--false-path-from", action="append", default=["rst_n", "rst", "reset", "rstn"])
    ap.add_argument("--period-ns", type=float, default=0.833)
    ap.add_argument("--max-fanout", type=int, default=24)
    ap.add_argument("--utilization", type=float, default=30)
    ap.add_argument("--macro", action="append", default=[], help="hard macro with LEF + _ss.lib under physical/")
    ap.add_argument("--work", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--label", default=None)
    ap.add_argument("--include", action="append", default=[], help="include directory (repo-relative)")
    ap.add_argument("--define", action="append", default=[], help="Verilog define NAME or NAME=VAL")
    ap.add_argument("--resolve-from", default=None, help="runtime source list; add the closure of --top from it")
    ap.add_argument("--blackbox", action="append", default=[], help="module to leave as a black box")
    ap.add_argument("--domain", default=None, help="intended clock domain of the block (label only)")
    ap.add_argument("--focus", action="append", default=[], metavar="NAME=REGEX",
                    help="also report the worst path into registers whose full name matches REGEX (the loop state)")
    args = ap.parse_args()

    work = Path(args.work).resolve()
    (work / "named").mkdir(parents=True, exist_ok=True)
    sources = list(args.source)
    if args.resolve_from:
        sources = resolve(args.top, sources, args.resolve_from, args.include, args.blackbox)
    tt = Path(os.environ.get("OPENTALLAS_PDK_ASAP7_ROOT", Path.home() / ".local/opentallas-pdk-asap7")) / "lib/NLDM"
    libs = [tt / n for n in TT_LIBS]
    seq = tt / TT_LIBS[3]
    incs = "".join(f" -I{ROOT / i}" for i in args.include)
    defs = "".join(f" -D{d}" for d in args.define)
    chparam = "".join(f" -chparam {k} {v}" for k, v in sorted(dict(p.split("=", 1) for p in args.param).items()))
    icg = any("ICGx" in (ROOT / f).read_text(errors="replace") for f in sources)
    ys = [*( [f"read_liberty -lib {seq}"] if icg else []),
          *(f"read_verilog -sv{defs}{incs} {ROOT / f}" for f in sources),
          *(f"blackbox {b}" for b in args.blackbox),
          f"hierarchy -check -top {args.top}{chparam}",
          f"synth -top {args.top} -flatten",
          # non-macro black boxes (no LEF/liberty): remove the instance, expose its undriven outputs as top inputs
          *(f"delete t:{b}" for b in args.blackbox if b not in args.macro),
          *(["setundef -undriven -expose"] if any(b not in args.macro for b in args.blackbox) else []),
          # cells named after the wire they drive, so the timed path reads in RTL names
          "rename -wire",
          f"dfflibmap -liberty {seq}",
          "abc" + "".join(f" -liberty {l}" for l in libs) + "".join(f" -dont_use {d}" for d in DONT_USE)
          + f" -D {args.period_ns * 1000.0:g}",
          "setundef -zero", "splitnets -ports", "opt_clean",
          f"tee -o {work / 'named/stat.txt'} stat" + "".join(f" -liberty {l}" for l in libs),
          f"write_verilog -noattr {work / 'named/mapped.v'}", ""]
    (work / "named/synth.ys").write_text("\n".join(ys))
    yosys = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "yosys-0.68/bin/yosys"
    proc = subprocess.run([str(yosys), "-q", "-s", str(work / "named/synth.ys")], capture_output=True, text=True)
    (work / "named/yosys.log").write_text(proc.stdout + proc.stderr)
    if not (work / "named/mapped.v").is_file():
        print(proc.stdout[-2000:], proc.stderr[-3000:], file=sys.stderr)
        return 2
    stat = (work / "named/stat.txt").read_text()
    m = re.search(r"Chip area for (?:top )?module .*?:\s*([\d.]+)", stat)
    mc = re.findall(r"^\s+(\d+)\s+(?:[\d.E+\-]+\s+)?cells\s*$", stat, re.M) or re.findall(r"Number of cells:\s+(\d+)", stat)
    synth = {"design": {"area_um2": float(m.group(1)) if m else None, "cells": int(mc[-1]) if mc else None}}
    import shutil, math
    marea = 0.0
    mapped = (work / "named/mapped.v").read_text()
    for mname in args.macro:
        d = next(ROOT / md / mname for md in MACRO_DIRS if (ROOT / md / mname / f"{mname}.lef").is_file())
        shutil.copy(d / f"{mname}.lef", work / "named" / f"{mname}.lef")
        shutil.copy(d / f"{mname}_ss.lib", work / "named" / f"{mname}_ss.lib")
        sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", (d / f"{mname}.lef").read_text())
        n = len(re.findall(rf"^\s*{mname}\s", mapped, re.M))
        marea += n * float(sz.group(1)) * float(sz.group(2)) * 1.25
    # port bits of the top (after splitnets -ports): place_pins needs ~9.4 positions/um of core perimeter
    ports = 0
    mt = re.search(rf"module\s+{re.escape(args.top)}\s*\((.*?)\);", mapped, re.S)
    for decl in re.finditer(r"^\s*(input|output|inout)\s+(?:wire\s+)?(\[(\d+):(\d+)\]\s+)?([^;]+);", mapped, re.M):
        w = abs(int(decl.group(3)) - int(decl.group(4))) + 1 if decl.group(2) else 1
        ports += w * len(decl.group(5).split(","))
    cell_area = synth.get("design", {}).get("area_um2") or 0.0
    total = cell_area + marea
    side_io = ports / (4 * 9.4) * 1.5 + 4
    side_util = math.sqrt(total / (args.utilization / 100.0)) + 4 if total else 0
    util = args.utilization
    if side_io > side_util and total:
        util = max(0.01, 100.0 * total / (side_io - 4) ** 2)
    rec_util = {"requested": args.utilization, "used": util, "port_bits": ports, "macro_area_um2": marea}
    script = tcl(args.top, args.period_ns * 1000.0, args.clock_port, args.false_path_from, args.max_fanout, util,
                 args.focus, args.macro)
    (work / "screen.tcl").write_text(script)
    dock = ["docker", "run", "--rm", "-v", f"{work / 'named'}:/w:ro", "-v", f"{work}:/o", IMAGE, "bash", "-lc",
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /o/screen.tcl"]
    proc = subprocess.run(dock, capture_output=True, text=True)
    log = proc.stdout + proc.stderr
    (work / "screen.log").write_text(log)
    period_ps = args.period_ns * 1000.0
    phases = {}
    for tag in ("RAW", "REP"):
        r2r = num(log, f"{tag}_R2R_WS")
        allws = num(log, f"{tag}_ALL_WS")
        phases[tag.lower()] = {
            "r2r_setup_wns_ps": r2r,
            "r2r_required_period_ps": None if r2r is None else period_ps - r2r,
            "r2r_fmax_mhz": None if r2r is None else 1e6 / (period_ps - r2r),
            "all_setup_wns_ps": allws,
            "all_fmax_mhz": None if allws is None else 1e6 / (period_ps - allws),
            "tns_ps": num(log, f"{tag}_TNS"),
            "cells": num(log, f"{tag}_CELLS"),
            "r2r_path": parse_path(block(log, f"{tag}_PATH")),
            "io_path": {k: v for k, v in parse_path(block(log, f"{tag}_IOPATH")).items() if k != "cells"},
            "focus": {},
        }
        for f in args.focus:
            name = f.split("=", 1)[0]
            ws = num(log, f"{tag}_FOCUS_WS_{name}")
            phases[tag.lower()]["focus"][name] = {
                "regex": f.split("=", 1)[1], "endpoints": num(log, f"{tag}_FOCUS_N_{name}"),
                "setup_wns_ps": ws, "fmax_mhz": None if ws is None else 1e6 / (period_ps - ws),
                "path": parse_path(block(log, f"{tag}_FPATH_{name}")),
            }
    src_commit = None
    for cand in (ROOT / "SOURCE_COMMIT",):
        if cand.is_file():
            src_commit = cand.read_text().strip()
    if src_commit is None:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        src_commit = r.stdout.strip() or None
    rec = {
        "schema": "opentallas-risk-clock-loops-screen-v1",
        "label": args.label or args.top,
        "top": args.top,
        "sources": {f: sha(ROOT / f) for f in sources},
        "defines": args.define, "includes": args.include, "blackboxes": args.blackbox, "domain": args.domain,
        "parameters": dict(p.split("=", 1) for p in args.param),
        "source_commit": src_commit,
        "corner": "ASAP7 RVT SS (ORFS asap7 WC liberty: 0.63 V, 100 C)",
        "mapping": ("Yosys 0.68 + ABC on the TT RVT liberty at the target period, the pinned driver's synth.ys "
                    "(tools/run_abi3_physical.py run_synthesis) plus defines/includes, rename -wire before mapping "
                    "and opt_clean without -purge so paths read in RTL names; timed on SS"),
        "period_ns": args.period_ns,
        "setup_uncertainty_ps": 60,
        "io_delay_fraction": 0.2,
        "wires": "raw: none (ideal clock, zero wire load); repaired: global+detailed placement, placement parasitics (asap7 setRC), ideal clock, no route",
        "floorplan": rec_util, "macros": args.macro,
        "screen_tool": "jobs/risk_clock_loops_screen_hbm.py (copy of tools/risk_clock_loops_screen.py + --macro + IO-aware utilisation + non-macro black boxes cut to top inputs)",
        "repair": f"global_placement, repair_design (max_transition 320 ps, max_fanout {args.max_fanout}), repair_timing -setup, legalised; utilisation {util:g}%",
        "synth": {"cells": synth.get("design", {}).get("cells"), "area_um2": synth.get("design", {}).get("area_um2")},
        "phases": phases,
        "image": IMAGE,
        "openroad_rc": proc.returncode,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    Path(args.output).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    rp = phases["rep"]
    for name, fo in rp["focus"].items():
        print(f"  focus {name}: repaired wns {fo['setup_wns_ps']} ps, fmax {fo['fmax_mhz']} MHz, "
              f"{fo['path']['startpoint']} -> {fo['path']['endpoint']}")
    print(f"{rec['label']}: raw r2r {phases['raw']['r2r_fmax_mhz']} MHz, repaired r2r {rp['r2r_fmax_mhz']} MHz "
          f"(wns {rp['r2r_setup_wns_ps']} ps), all {rp['all_fmax_mhz']} MHz")
    return 0 if proc.returncode == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
