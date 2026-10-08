# Full-die r20c top-level GRT (owner 2026-10-06): signals on M4..M9 only (M1-M3 belong to the elements; every element
# signal pin is on M4/M5/M6/M8), coarse gcell grid (GRT tile = 15 x M2 track pitch in this build: M2/M3 carry no die
# signal, so their track grids are re-pitched to set the tile; OT_TILE_UM), r20c per-layer + corridor region capacity
# adjustments (M6-M9 0.146, corridor M8/M9 0.53 / 0.1033 as the r20c bundled GRT; M4/M5 0.30 kept for element pin escape).
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; regexp {VmHWM:\s+(\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name }
set_thread_count $::env(OT_THREADS)
step load { read_db /work/ckpt_grt.odb }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
step guides {
  set ng 0
  foreach net [[ord::get_db_block] getNets] { if {[llength [$net getGuides]]} { incr ng } }
  puts "OT_DB_GUIDES nets=$ng"
  if {$ng == 0} { read_guides /work/route.guide }
}
step drt { detailed_route -output_drc /work/drt_drc.rpt -verbose 1 -droute_end_iter $::env(OT_DRT_ITERS) }
step write_odb { write_db /work/routed.odb }
puts OT_DRT_DONE
