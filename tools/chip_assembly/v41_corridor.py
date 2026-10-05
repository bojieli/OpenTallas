#!/usr/bin/env python3
"""Real-technology check of a die-level registered channel (companion of tools/chip_assembly/v41_die.py).

The die-level route (v41_die.py) is bundled and prices every crossing with the routed ASAP7 wire model
(ps/um + flop overhead fitted on the express-link routes).  This tool checks that price where it matters:
a CORRIDOR -- one inter-cluster channel of the die, at its real width and carrying the bus population the
die route put through it -- is built in the real ASAP7 technology with register stations at a chosen
spacing, buffered by repair_design, globally routed and timed with global-route parasitics at the die
clock (0.92 ns, 60 ps uncertainty; ideal regional clock: the die clock plan is regional trees with
mesochronous crossings, results/arch/v41_die_assembly.json clock.verdict).

Groups of chains with different station spacings share the corridor, so one run brackets the reach.

    python3 tools/chip_assembly/v41_corridor.py write --work W --length-mm 3.4 --width-um 140 \
        --wires 1200 --spacings-mm 0.9,1.118,1.4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PERIOD_PS = 920.0   # ASAP7 liberty time unit is ps
UNC_PS = 60.0
FLOP = "DFFHQNx2_ASAP7_75t_R"
ROW_UM = 0.270
SITE_UM = 0.054


def write(work: Path, length_mm: float, width_um: float, wires: int, spacings: list[float],
          adjust: float, min_layer: str = "M2", rc_layer: str | None = None) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    L = length_mm * 1000.0
    groups = []
    per = wires // len(spacings)
    v = ["// Registered channel corridor (tools/chip_assembly/v41_corridor.py)", "module corridor (input clk,"]
    ports, body, place = [], [], []
    n = 0
    y_rows = int(width_um / ROW_UM) - 4
    for gi, sp in enumerate(spacings):
        stations = max(1, int((L - 2.0) / (sp * 1000.0) + 1e-9))
        seg = sp * 1000.0
        groups.append({"spacing_mm": round(seg / 1000, 4), "stations": stations, "chains": per})
        for c in range(per):
            ports += [f"input d{n}", f"output q{n}"]
            prev = f"d{n}"
            row = 2 + (n * 7919) % y_rows
            col_off = (n // y_rows) * 1.62  # chains beyond one per row stack in adjacent flop columns
            for s in range(stations + 1):
                inst = f"r{n}_{s}"
                out = f"q{n}" if s == stations else f"w{n}_{s}"
                body.append(f"  {FLOP} {inst} (.CLK(clk), .D({prev}), .QN({out}));")
                x = (min(s * seg, L - 2.0) if s else 1.0) + col_off
                place.append(f"place_inst -name {inst} -location {{{round(round(x / SITE_UM) * SITE_UM, 3)} "
                             f"{round(row * ROW_UM, 3)}}} -status FIRM")
                prev = out
            n += 1
    v.append(",\n".join(ports) + ");")
    v += body
    v.append("endmodule")
    (work / "corridor.v").write_text("\n".join(v) + "\n")
    (work / "place.tcl").write_text("\n".join(place) + "\n")
    W, H = L + 4.0, round(math.ceil(width_um / ROW_UM) * ROW_UM, 3)
    sdc = [f"create_clock -name clk -period {PERIOD_PS} [get_ports clk]",
           f"set_clock_uncertainty {UNC_PS} [get_clocks clk]",
           "set_input_delay 0 -clock clk [delete_from_list [all_inputs] [get_ports clk]]",
           "set_output_delay 0 -clock clk [all_outputs]",
           "set_max_transition 320 [current_design]", "set_max_fanout 32 [current_design]"]
    (work / "corridor.sdc").write_text("\n".join(sdc) + "\n")
    adj = "\n".join(f"set_global_routing_layer_adjustment M{i} {adjust}" for i in range(2, 10))
    tcl = f"""set P /OpenROAD-flow-scripts/flow/platforms/asap7
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $P/lib/NLDM/*RVT_TT*] {{ read_liberty $f }}
read_verilog /work/corridor.v
link_design corridor
read_sdc /work/corridor.sdc
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
source $P/setRC.tcl
{f"set_wire_rc -signal -layer {rc_layer}" if rc_layer else ""}
set_dont_use {{*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}}
place_pins -hor_layers M4 -ver_layers M5 -min_distance 1 -min_distance_in_tracks
source /work/place.tcl
mem placed
estimate_parasitics -placement
repair_design -max_wire_length 0
mem repaired
detailed_placement
{adj}
set_routing_layers -signal {min_layer}-M9
global_route -allow_congestion -congestion_iterations 30 -verbose
estimate_parasitics -global_routing
repair_timing -setup -skip_pin_swap
detailed_placement
global_route -start_incremental
global_route -end_incremental
estimate_parasitics -global_routing
mem routed
report_worst_slack -max
report_worst_slack -min
report_tns
report_checks -path_delay max -group_path_count 3 -format full_clock_expanded -fields {{slew cap fanout}}
report_design_area
set out [open /work/chains.txt w]
foreach g {{{' '.join(str(i) for i in range(len(spacings)))}}} {{ }}
foreach pin [get_pins -hierarchical r*/D] {{
  puts $out "[get_full_name $pin] [get_property $pin slack_max] [get_property $pin slack_min]"
}}
close $out
report_wire_length -net * -global_route -file /work/wirelength.csv
mem done
"""
    (work / "run.tcl").write_text(tcl)
    man = {"length_mm": length_mm, "width_um": width_um, "wires": per * len(spacings), "groups": groups,
           "layer_adjustment": adjust, "die_um": [W, H], "flop": FLOP, "period_ps": PERIOD_PS,
           "uncertainty_ps": UNC_PS, "signal_layers": f"{min_layer}-M9",
           "placement_rc_layer": rc_layer or "platform setRC default"}
    (work / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


def record(work: Path) -> dict[str, Any]:
    man = json.loads((work / "manifest.json").read_text())
    log = (work / "run.log").read_text() if (work / "run.log").is_file() else ""
    slack = {}
    for line in (work / "chains.txt").read_text().splitlines() if (work / "chains.txt").is_file() else []:
        name, smax, smin = line.split()
        m = re.match(r"r(\d+)_(\d+)/D", name)
        if not m:
            continue
        chain, st = int(m.group(1)), int(m.group(2))
        slack[(chain, st)] = (float(smax), float(smin))
    per_group = []
    start = 0
    for g in man["groups"]:
        chains = range(start, start + g["chains"])
        # station 0 is fed from the input port (not a channel segment)
        seg = [slack[(c, s)] for c in chains for s in range(1, g["stations"] + 1) if (c, s) in slack]
        worst = min((x[0] for x in seg), default=None)
        per_group.append({**g, "segments": len(seg),
                          "worst_setup_slack_ps": worst,
                          "failing_segments": sum(1 for x in seg if x[0] < 0),
                          "worst_hold_slack_ps": min((x[1] for x in seg), default=None)})
        start += g["chains"]
    m = re.search(r"GRT-0096\] Final congestion report:.*?Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)",
                  log, re.S)
    buf = re.findall(r"Inserted (\d+) buffers", log)
    rec = {"schema": "opentallas.v41.die_corridor.v1", **man, "groups": per_group,
           "grt_overflow": int(m.group(6)) if m else None, "grt_usage_pct": float(m.group(3)) if m else None,
           "repair_buffers_inserted": [int(b) for b in buf],
           "errors": re.findall(r"\[ERROR [^\]]+\].*", log)[:5],
           "peak_rss_mb": max((int(x) for x in re.findall(r"OTMEM \S+ (\d+) MB", log)), default=None),
           "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["write", "record"])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--length-mm", type=float, default=3.4)
    ap.add_argument("--width-um", type=float, default=140.0)
    ap.add_argument("--wires", type=int, default=1200)
    ap.add_argument("--spacings-mm", default="0.9,1.118,1.4")
    ap.add_argument("--adjust", type=float, default=0.25)
    ap.add_argument("--min-layer", default="M2")
    ap.add_argument("--rc-layer")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.mode == "write":
        print(json.dumps(write(a.work.resolve(), a.length_mm, a.width_um, a.wires,
                               [float(x) for x in a.spacings_mm.split(",")], a.adjust, a.min_layer, a.rc_layer)))
        return 0
    rec = record(a.work.resolve())
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rec[k] for k in ("groups", "grt_overflow", "errors", "peak_rss_mb")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
