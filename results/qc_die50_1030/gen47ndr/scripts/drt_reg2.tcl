# DIE-QC-50/gen47ndr stage 2b (PARTIAL DRT): whole-die clock-only DRT is infeasible here (probe: 120 GB OOM at 32 threads
# in the first DR batch; ~36 s CPU per non-empty 75.6-um worker at native ASAP7 tracks -> ~700 thread-hours for the
# 5.4 m clock).  So DETAILED ROUTE + RCX of the clock nets lying wholly inside the worst-region windows (region tap bbox
# + 200 um; boxes_$G.txt), same clk_grt.odb (full-die NDR GRT guides), same NDR CLK2W2S, then OpenRCX (rcx_ndr008).
set O $::env(OUT)
read_db $::env(RUN)/grt_TT/clk_grt.odb
source $::env(RUN)/obsfix.tcl
set b [ord::get_db_block]
set bxs {}
set fh [open $::env(BOXES)]; while {[gets $fh l] >= 0} { if {[llength $l] == 4} { lappend bxs $l } }; close $fh
proc inbox {bb} { global bxs; foreach x $bxs { lassign $x x0 y0 x1 y1; if {[$bb xMin] >= $x0 && [$bb xMax] <= $x1 && [$bb yMin] >= $y0 && [$bb yMax] <= $y1} { return 1 } }; return 0 }
set keep 0; set del 0
set kf [open $O/kept_nets.txt w]
foreach n [$b getNets] {
  set ok [expr {[llength [$n getITerms]] > 0}]
  foreach it [$n getITerms] { if {![inbox [[$it getInst] getBBox]]} { set ok 0; break } }
  if {$ok} { foreach bt [$n getBTerms] { if {![inbox [$bt getBBox]]} { set ok 0; break } } }
  if {$ok} { incr keep; puts $kf [$n getName] } else { odb::dbNet_destroy $n; incr del }
}
close $kf
puts "REG keep $keep del $del boxes [llength $bxs]"
set_routing_layers -signal M1-M9 -clock M1-M9
detailed_route -output_drc $O/drc.rpt -droute_end_iter $::env(ITERS) -verbose 1
puts DRT_DONE
write_db $O/clk_drt.odb
set ot_tech [ord::get_db_tech]
[$ot_tech findLayer M1] setResistance 0.563166
[$ot_tech findLayer M2] setResistance 0.534825
[$ot_tech findLayer M3] setResistance 0.563166
[$ot_tech findLayer M4] setResistance 0.432876
[$ot_tech findLayer M5] setResistance 0.455842
[$ot_tech findLayer M6] setResistance 0.380144
[$ot_tech findLayer M7] setResistance 0.400304
[$ot_tech findLayer M8] setResistance 0.337862
[$ot_tech findLayer M9] setResistance 0.355786
extract_parasitics -ext_model_file $::env(RUN)/rcx_ndr008.rules -lef_res
write_spef $O/clk_rcx.spef
puts RCX_DONE
