# DIE-QC-44 die GRT TRIAL1 (leaf rule) on Codex complete_pg/provider.odb (fixed clock + PG access, TRIAL0 source).
# Same as Codex grt_trial.tcl except the -clock layer range: every trunk/tree net is already a FIXED pre-routed wire,
# so the only CLOCK nets GRT routes are the 6,532 provider leaf-driver nets (CKINVDCx5p33/Y pair-internal, CKINVDCx16/Y
# leaf). Leaf rule: they stay on local layers (CLKLAYERS env, e.g. M4-M5) instead of the die trunk layers M8-M9.
# Then: arrivals (CORNER env TT or FF, one corner per session) (rise+fall, slew) at every clock sink: 22,365 provider FF CLK pins + 7,889 native core taps.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set O $::env(OUT)
set C $::env(CORNER)
foreach f [glob $P/lib/NLDM/*RVT_${C}_nldm*.lib*] { read_liberty $f }
read_db /s/codex-qc-2249/complete_pg/provider.odb
create_clock -name dck -period 833.000 [get_ports root]
set_propagated_clock [all_clocks]
source $P/setRC.tcl
set_routing_layers -signal M4-M9 -clock $::env(CLKLAYERS)
foreach L {M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.75 }
set_global_routing_layer_adjustment M8 0
set_global_routing_layer_adjustment M9 0
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file $O/congestion.rpt
write_guides $O/route.guide
write_db $O/routed.odb
puts QC44_GRT_DONE
estimate_parasitics -global_routing
set w 0
while {![file exists /s/die-qc-44/grt/clock.spef.done] && $w < 7200} { after 30000; incr w 30 }
if {[file exists /s/die-qc-44/grt/clock.spef.done]} { read_spef /s/die-qc-44/grt/clock.spef; puts QC44_SPEF_READ } else { puts QC44_SPEF_MISSING }
set fh [open $O/arrivals.txt w]
foreach c [list $C] {
  foreach p [get_pins -hierarchical */CLK] {
    puts $fh "$c F [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p slew_max_rise]"
  }
  set tf [open /s/die-qc-44/grt/taps.txt]
  while {[gets $tf l] >= 0} {
    lassign $l t inst pin x y
    set p [get_pins -quiet $inst/$pin]
    if {[llength $p]} { puts $fh "$c T $t [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p slew_max_rise] $x $y" } else { puts $fh "$c T $t NA" }
  }
  close $tf
}
close $fh
puts QC44_ARR_DONE
