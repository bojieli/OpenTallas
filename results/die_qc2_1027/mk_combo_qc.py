#!/usr/bin/env python3
"""DIE-QC (10-27): combined die GRT with the clock ROUTED = die_trial signal kit (abstracts) + die_trial clock tree
(ctree.v / ctree.tcl placements) in ONE global_route, 50 congestion iterations, -critical_nets_percentage 0.
Derived from results/fallback_head_1026/scripts/mk_combo_dcm.py (LAND-HEAD-1/3 recipe) with three QC changes:
  * the kit's clock RESERVATION obstructions (die_trial reserve_rects, kit.json clock_reserve_rects) are dropped: the
    clock is now a routed occupant of those tracks; PG stripe obstructions (written first in obs.tcl) are kept;
  * signal layers stay as the QC kit (12.1c: M4-M9, leftover M8/M9) and the clock routes on M8-M9;
  * -critical_nets_percentage 0 (congestion-only, as the kit GRT).
Arrivals (T = tap ports, N = clock cells, late/early, slews) on estimate_parasitics -global_routing, same file format
as mk_combo_dcm (consumed by tools/s81_head/landed_phase_ocv.py).
usage: CORNER=TT mk_combo_qc.py KIT_DIR CLK_DIR OUT_DIR"""
import json
import os
import re
import sys

K, C, O = sys.argv[1:4]
os.makedirs(O, exist_ok=True)
kit = json.load(open(K + "/kit.json"))
g = kit["grt"]
nres, npg = g["clock_reserve_rects"], g["pg_stripes"]
band = g["die_ft_bands"]["share_obstructions"]
obs = open(K + "/grt/obs.tcl").read().splitlines()
assert len(obs) == npg + nres + band and band == 0, (len(obs), npg, nres, band)   # order: pg, reserve, band
open(O + "/obs_pg.tcl", "w").write("\n".join(obs[:npg]) + "\n")
rv = open(K + "/grt/route.v").read(); cv = open(C + "/ctree.v").read()
mh = re.match(r"\s*module\s+(\w+)\s*\(([^)]*)\);", rv); rports = [p.strip() for p in mh.group(2).split(",") if p.strip()]
rbody = rv[mh.end():rv.rindex("endmodule")]
mc = re.search(r"module\s+ctree\s*\(([^)]*)\);", cv, re.S); cports = [p.strip() for p in mc.group(1).split(",") if p.strip()]
assert not set(rports) & set(cports)
Pset = set(cports)


def f(n):
    return n if n in Pset else "ck_" + n


out = []
for line in cv[mc.end():cv.rindex("endmodule")].split("\n"):
    s = line.strip()
    if not s or s.startswith(("input", "output")):
        continue
    m = re.match(r"wire\s+(\w+)\s*;", s)
    if m:
        out.append(f"  wire {f(m.group(1))};"); continue
    m = re.match(r"(\w+)\s+(\w+)\s*\((.*)\);", s)
    if m:
        conns = re.sub(r"\.(\w+)\((\w+)\)", lambda q: f".{q.group(1)}({f(q.group(2))})", m.group(3))
        out.append(f"  {m.group(1)} ck_{m.group(2)} ({conns});"); continue
    m = re.match(r"assign\s+(\w+)\s*=\s*(\w+)\s*;", s)
    if m:
        out.append(f"  assign {f(m.group(1))} = {f(m.group(2))};"); continue
    raise SystemExit("unparsed: " + s)
decl = [l for l in cv[mc.end():].split("\n") if l.strip().startswith(("input", "output"))]
open(O + "/combo.v", "w").write(f"module die_combo ({', '.join(rports + cports)});\n" + "\n".join(decl) + "\n" + rbody
                                 + "\n".join(out) + "\nendmodule\n")
t = open(K + "/grt/grt.tcl").read()
ct = open(C + "/ctree.tcl").read()
pins = [l for l in ct.split("\n") if l.startswith("place_pin")]
insts = [re.sub(r"-name (\S+)", r"-name ck_\1", l) for l in ct.split("\n") if l.startswith("place_inst")]
pre = t.split("source /work/grt/obs.tcl")[0]
pre = pre.replace("read_verilog /work/grt/route.v",
                  "foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\nread_verilog /out/combo.v")
pre = pre.replace(re.search(r"link_design \S+", pre).group(0), "link_design die_combo")
adj = re.findall(r"set_global_routing_layer_adjustment (M\d) ([\d.]+)", t)
assert adj, "kit grt.tcl has no layer adjustments"
tail = f"""source /out/obs_pg.tcl
puts "OT_T obs [expr {{[clock seconds]-$t0}}]"
{chr(10).join(pins)}
{chr(10).join(insts)}
puts "OT_T clockplaced [expr {{[clock seconds]-$t0}}]"
create_clock -name dck -period 833.333 [get_ports root]
set_routing_layers -signal M4-M9 -clock M8-M9
{chr(10).join(f"set_global_routing_layer_adjustment {L} {a}" for L, a in adj)}
source /out/ndr.tcl
puts "OT_NDR [llength [get_nets ck_*]]"
if {{[catch {{global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file /out/congestion_$::env(CORNER).rpt}} e]}} {{ puts "OT_GRT_ERROR $e" }}
puts "OT_T grt [expr {{[clock seconds]-$t0}}]"
if {{[catch {{grt::report_layer_wire_lengths}} e]}} {{ puts "OT_NO_LAYER_WL $e" }}
write_guides /out/route_$::env(CORNER).guide
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
create_clock -name vclk -period 833.333
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
set fh [open /out/arr_$::env(CORNER).txt w]
foreach p [get_ports t_*] {{ puts $fh "T [get_full_name $p] [expr {{833.333 - [get_property $p slack_max_rise]}}] [get_property $p slack_min_rise] [get_property $p slew_max_rise]" }}
foreach i [get_cells ck_*] {{ set q [get_pins [get_full_name $i]/Y]; set a [get_pins [get_full_name $i]/A]; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise] [get_property $a slew_max_rise] [get_property $q slew_max_rise]" }}
close $fh
report_check_types -max_slew -max_capacitance -violators
puts OT_DONE
"""
open(O + "/combo.tcl", "w").write(pre + tail)
print("ports", len(rports), len(cports), "ck insts", len(insts), "pins", len(pins), "obs pg", npg, "dropped clock reserve", nres)
