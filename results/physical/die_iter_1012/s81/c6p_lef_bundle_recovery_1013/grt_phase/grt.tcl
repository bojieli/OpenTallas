proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; regexp {VmHWM:\s+(\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout; return 0 }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name; flush stdout; return 1 }
set_thread_count 48
step load { read_db /work/placed.odb }
step coarse { set b [ord::get_db_block]; set p [expr {9.6/15.0}]
  foreach ln {M2 M3} { odb::dbTrackGrid_destroy [$b findTrackGrid [[ord::get_db_tech] findLayer $ln]]
    make_tracks $ln -x_offset 0.009 -x_pitch $p -y_offset 0.009 -y_pitch $p } }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_SS_nldm_*.lib*] { read_liberty $l }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
step grt { global_route -congestion_iterations 12 -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt }
step guides { write_guides /work/route.guide }
step ckpt_grt { write_db /work/ckpt_grt.odb }
step wl { report_wire_length -net * -global_route -file /work/wirelength_grt.csv }
step spef { estimate_parasitics -global_routing -spef_file /work/die_grt.spef }
step netlist { write_verilog /work/die_grt.v }
