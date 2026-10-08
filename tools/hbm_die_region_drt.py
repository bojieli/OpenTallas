#!/usr/bin/env python3
"""HBM die: detail route of one REPRESENTATIVE REGION of the full-die global-routed database (OWNER STEER 2026-10-07 (6):
no flat full-die DRT; regions with DRT convergence, DRC and the GRT-vs-DRT correlation as the error bar).

The region is cut from the die's ckpt_grt.odb (tools/hbm_die_relay_sta.py run_grt_sta.tcl):
  * the window edges are moved outward into the nearest channel so no hard block straddles an edge;
  * instances inside the window stay (fixed), the rest are deleted;
  * a net with terminals on both sides keeps its inside terminals and gets a boundary pin where its outside terminals'
    centroid projects onto the window edge (horizontal-routing layers M4/M6/M8 on W/E edges, vertical M5/M7/M9 on S/N,
    round robin), so the region routes every wire it would carry in the die, to the edge;
  * the die area becomes the window; GRT (same layer adjustments as the die GRT) -> SS STA on GRT parasitics ->
    DRT -> RCX -> SS STA on extracted parasitics, both over the same endpoint set -> per-net GRT vs DRT wire length.

    python3 tools/hbm_die_region_drt.py --case <relay case dir with run_grt_sta.tcl> --name hub --window x0 y0 x1 y1
writes <case>/region_<name>.tcl (run in the case dir, /work = case, /out = case/region_<name>/)
"""
import argparse
import re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--window', nargs=4, type=float, required=True)
    ap.add_argument('--iters', type=int, default=20)
    ap.add_argument('--endpoints', type=int, default=3000)
    a = ap.parse_args()
    case = Path(a.case)
    full = (case / 'run_grt_sta.tcl').read_text()
    libs = '\n'.join(l for l in full.splitlines() if l.startswith(('define_corners', 'read_liberty')))
    i0 = full.index('set_cmd_units -time ns')
    i1 = full.index('puts "OT_WNS corner=ss')
    cons_ss = full[i0:i1]
    x0, y0, x1, y1 = a.window
    tcl = f'''# region {a.name}: window {x0} {y0} {x1} {y1} um of the die GRT checkpoint
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag rss_mb=[expr {{$r/1024}}] t=[clock seconds]"; flush stdout }}
{libs}
read_db /work/ckpt_grt.odb
set b [ord::get_db_block]; set dbu [$b getDbUnitsPerMicron]
set tech [ord::get_db_tech]
# grow each edge outward until no hard block straddles it
set wx0 [expr {{round({x0}*$dbu)}}]; set wy0 [expr {{round({y0}*$dbu)}}]; set wx1 [expr {{round({x1}*$dbu)}}]; set wy1 [expr {{round({y1}*$dbu)}}]
for {{set it 0}} {{$it < 20}} {{incr it}} {{
  set moved 0
  foreach i [$b getInsts] {{
    set bb [$i getBBox]; set a0 [$bb xMin]; set b0 [$bb yMin]; set a1 [$bb xMax]; set b1 [$bb yMax]
    if {{$a1 <= $wx0 || $a0 >= $wx1 || $b1 <= $wy0 || $b0 >= $wy1}} continue
    if {{$a0 < $wx0}} {{ set wx0 [expr {{$a0 - 2160}}]; set moved 1 }}
    if {{$a1 > $wx1}} {{ set wx1 [expr {{$a1 + 2160}}]; set moved 1 }}
    if {{$b0 < $wy0}} {{ set wy0 [expr {{$b0 - 2160}}]; set moved 1 }}
    if {{$b1 > $wy1}} {{ set wy1 [expr {{$b1 + 2160}}]; set moved 1 }}
  }}
  if {{!$moved}} break
}}
set die [$b getDieArea]
set wx0 [expr {{max($wx0, [$die xMin])}}]; set wy0 [expr {{max($wy0, [$die yMin])}}]
set wx1 [expr {{min($wx1, [$die xMax])}}]; set wy1 [expr {{min($wy1, [$die yMax])}}]
set wx0 [expr {{$wx0 - $wx0 % 432}}]; set wy0 [expr {{$wy0 - $wy0 % 540}}]
puts "OT_REGION name={a.name} window_um=[expr {{$wx0/double($dbu)}}] [expr {{$wy0/double($dbu)}}] [expr {{$wx1/double($dbu)}}] [expr {{$wy1/double($dbu)}}]"
set keep [dict create]; set del {{}}
foreach i [$b getInsts] {{
  set bb [$i getBBox]
  if {{[$bb xMin] >= $wx0 && [$bb xMax] <= $wx1 && [$bb yMin] >= $wy0 && [$bb yMax] <= $wy1}} {{ dict set keep [$i getName] 1 }} else {{ lappend del $i }}
}}
set hl {{M4 M6 M8}}; set vl {{M5 M7 M9}}; set rr 0
set n_in 0; set n_cut 0; set n_del 0; set n_pins 0
foreach n [$b getNets] {{
  if {{[$n getSigType] in {{POWER GROUND}}}} continue
  set ins {{}}; set outs {{}}
  foreach it [$n getITerms] {{ if {{[dict exists $keep [[$it getInst] getName]]}} {{ lappend ins $it }} else {{ lappend outs $it }} }}
  if {{![llength $ins]}} {{ odb::dbNet_destroy $n; incr n_del; continue }}
  if {{![llength $outs]}} {{ incr n_in; continue }}
  # boundary pin: centroid of the outside terminals projected onto the window edge
  set sx 0; set sy 0
  foreach it $outs {{ set ib [[$it getInst] getBBox]; set sx [expr {{$sx + ([$ib xMin]+[$ib xMax])/2}}]; set sy [expr {{$sy + ([$ib yMin]+[$ib yMax])/2}}] }}
  set cx [expr {{$sx/[llength $outs]}}]; set cy [expr {{$sy/[llength $outs]}}]
  foreach it $outs {{ $it disconnect }}
  set dl [expr {{$wx0 - $cx}}]; set dr [expr {{$cx - $wx1}}]; set dd [expr {{$wy0 - $cy}}]; set du [expr {{$cy - $wy1}}]
  set m [lindex [lsort -real -decreasing [list $dl $dr $dd $du]] 0]
  set px [expr {{min(max($cx, $wx0 + 200), $wx1 - 200)}}]; set py [expr {{min(max($cy, $wy0 + 200), $wy1 - 200)}}]
  if {{$m == $dl || $m == $dr}} {{ set ly [lindex $hl [expr {{$rr % 3}}]]; set px [expr {{$m == $dl ? $wx0 : $wx1 - 100}}] }} else {{ set ly [lindex $vl [expr {{$rr % 3}}]]; set py [expr {{$m == $dd ? $wy0 : $wy1 - 100}}] }}
  incr rr
  set bt [odb::dbBTerm_create $n "rp_[$n getName]"]
  $bt setIoType [expr {{[llength $ins] && [[[lindex $ins 0] getMTerm] getIoType] eq "OUTPUT" ? "OUTPUT" : "INPUT"}}]
  set bp [odb::dbBPin_create $bt]
  odb::dbBox_create $bp [$tech findLayer $ly] [expr {{int($px)}}] [expr {{int($py)}}] [expr {{int($px)+100}}] [expr {{int($py)+100}}]
  $bp setPlacementStatus FIRM
  incr n_cut; incr n_pins
}}
foreach i $del {{ odb::dbInst_destroy $i }}
$b setDieArea [odb::new_Rect $wx0 $wy0 $wx1 $wy1]
puts "OT_CROP insts=[dict size $keep] nets_inside=$n_in nets_cut=$n_cut nets_deleted=$n_del boundary_pins=$n_pins"
mem crop
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -congestion_report_file /out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
report_wire_length -net * -global_route -file /out/wl_grt.csv
estimate_parasitics -global_routing
{cons_ss}
set eps {{}}
set f [open /out/slack_grt.txt w]
foreach pe [find_timing_paths -path_delay max -corner ss -group_path_count {a.endpoints} -endpoint_path_count 1] {{
  set e [get_full_name [get_property $pe endpoint]]
  lappend eps $e
  puts $f "$e [get_property $pe slack]"
}}
close $f
puts "OT_STA_GRT wns_ns=[sta::worst_slack -max] endpoints=[llength $eps]"
mem sta_grt
set t0 [clock seconds]
detailed_route -output_drc /out/drc.rpt -droute_end_iter {a.iters} -verbose 1
puts "OT_DRT_S [expr {{[clock seconds]-$t0}}]"
mem drt
write_db /out/region_drt.odb
report_wire_length -net * -detailed_route -file /out/wl_drt.csv
puts "OT_ANTENNA [check_antennas -report_file /out/antenna.rpt]"
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules
set f [open /out/slack_rcx.txt w]
foreach e $eps {{
  set pe [find_timing_paths -path_delay max -corner ss -to [get_pins -quiet $e] -group_path_count 1]
  if {{[llength $pe]}} {{ puts $f "$e [get_property [lindex $pe 0] slack]" }}
}}
close $f
puts "OT_STA_RCX wns_ns=[sta::worst_slack -max]"
puts OT_REGION_DONE
'''
    out = case / f'region_{a.name}.tcl'
    out.write_text(tcl)
    print(out)


if __name__ == '__main__':
    main()
