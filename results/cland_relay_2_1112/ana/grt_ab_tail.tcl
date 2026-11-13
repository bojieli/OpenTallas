# ---- CLAND-RELAY-2 GRT A/B tail: same post-GRT netlist (5_1_grt.odb), GRT-only re-route under a layer/RA mode ----
# env CR2_MAXL (M7|M8), CR2_RA (0|1); per-net wire RC of the cland slew nets + design slew count, GRT parasitics.
source /work/setRC_rcx.tcl
set maxl $::env(CR2_MAXL); set ra $::env(CR2_RA)
catch {grt::clear_route_guides}
set_global_routing_layer_adjustment M2-$maxl 0.5
set_routing_layers -clock M2-$maxl
set_routing_layers -signal M2-$maxl
set args {-congestion_iterations 30 -allow_congestion}
if {$ra} { lappend args -resistance_aware }
puts "CR2 GRT mode maxl $maxl ra $ra args $args"
global_route {*}$args
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
puts "CR2 SLEWCOUNT [sta::max_slew_violation_count]"
report_check_types -max_slew -violators > /out/slew.rpt
set fp [open /out/nets.tsv w]
puts $fp "net\tfanout\tpin_cap\twire_cap\ttotal_cap\twire_res_ohm\tworst_load_slew"
set c [open /out/netlist.txt]; set names [split [string trim [read $c]] "\n"]; close $c
foreach nn $names {
  set n [get_nets -quiet $nn]; if {$n eq ""} { puts $fp "$nn\tMISSING"; continue }
  report_net -digits 4 $nn > /out/net.tmp
  set c [open /out/net.tmp]; set r [read $c]; close $c
  set pc nan; set wc nan; set tc nan; set wr nan
  regexp {Pin capacitance:\s+[0-9.]+-([0-9.]+)} $r -> pc
  regexp {Wire capacitance:\s+[0-9.]+-([0-9.]+)} $r -> wc
  regexp {Total capacitance:\s+[0-9.]+-([0-9.]+)} $r -> tc
  set fo 0; set ws 0
  foreach p [get_pins -quiet -of_objects $n] {
    if {[get_property $p direction] ne "output"} { incr fo; set s [get_property $p slew_max]; if {$s ne "" && $s > $ws} { set ws $s } }
  }
  catch { set wr [format %.1f [expr {[rsz::sum_parasitic_network_resist $n]}]] }
  puts $fp "$nn\t$fo\t$pc\t$wc\t$tc\t$wr\t$ws"
}
close $fp
