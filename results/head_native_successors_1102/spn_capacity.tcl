# PREP ONLY: one raw capacity diagnostic, never normal GRT hooks/CTS/repair.
foreach v {IN SDC OUT GUIDE OUTDIR PG_HELPER} {if {![info exists ::env($v)]} {error "missing $v"}}
if {[file exists $::env(OUT)] || [file exists $::env(GUIDE)]} {error "refuse output reuse/old guides"}
source [file join [file dirname [info script]] frozen_geometry.tcl]
set libs [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT_nldm*.lib*]]
if {[llength $libs] != 5} {error "exact ASAP7 TT library set differs; restage/review, do not infer cells"}
foreach f $libs {puts "SPN_NATIVE_TT_LIB $f"; read_liberty $f}
read_db $::env(IN)
read_sdc $::env(SDC)
set block [ord::get_db_block]
source $::env(PG_HELPER)
ot_pg_require_bound SPN_CAPACITY_INPUT
# No global_connect or PG repair: native source must already be eligible.
foreach n [$block getNets] {if {[$n getSigType] in {POWER GROUND}} {
 check_power_grid -net [$n getName] -error_file [file join $::env(OUTDIR) pg_[$n getName].rpt]
}}
set clocks [all_clocks]
if {[llength $clocks] == 0} {error "native SDC has no clocks"}
set roots 0
foreach c $clocks {foreach p [get_property $c sources] {
 set ns [get_nets -of_objects $p]
 if {[llength $ns] != 1} {error "native clock source must resolve to exactly one physical net"}
 foreach n $ns {
  set name [get_full_name $n]; set dn [$block findNet $name]
  if {$dn eq "NULL" || [$dn getSigType] ne "CLOCK"} {error "SDC root is not originally CLOCK: $name"}
  puts "SPN_ACTUAL_SDC_ROOT [get_full_name $c] [get_full_name $p] $name"; incr roots
 }
}}
if {$roots == 0} {error "only virtual clocks found; physical clock occupancy absent"}
set before [hg_state]; hg_write [file join $::env(OUTDIR) frozen.before] $before
set f [open [file join $::env(OUTDIR) native_census.tsv] w]
puts $f "class\tnet\tdegree\tspecial\tspecial_wires\tguides"
set nc 0; set ns 0
foreach n [$block getNets] {
 set ty [$n getSigType]; set degree [expr {[llength [$n getITerms]]+[llength [$n getBTerms]]}]
 puts $f "$ty\t[$n getName]\t$degree\t[$n isSpecial]\t[llength [$n getSWires]]\t[llength [$n getGuides]]"
 if {$ty ni {CLOCK SIGNAL} || $degree <= 1} continue
 set wire [$n getWire]
 if {[$n isSpecial] || [llength [$n getSWires]] || [llength [$n getGuides]] || ($wire ne "NULL" && $wire ne "")} {error "SPN input excluded or already routed class $ty:[$n getName]; no flag changes allowed"}
 if {$ty eq "CLOCK"} {incr nc} else {incr ns}
}
close $f
if {$nc == 0 || $ns == 0} {error "SPN omitted CLOCK or SIGNAL class"}
puts "SPN_CAPACITY_CLASSES native_CLOCK=$nc native_SIGNAL=$ns, all originally non-special"
set_routing_layers -signal M2-M7 -clock M2-M7
set_global_routing_layer_adjustment M2-M7 0.25
puts "SPN_CAPACITY_RAW native M2-M7 adjustment0.25 iterations50; no repair/birth/CTS/STA; source nearest-tap load1993 remains held"
global_route -congestion_iterations 50 -congestion_report_file [file join $::env(OUTDIR) congestion.rpt] -allow_congestion -verbose
set missing {}; set gc 0; set gs 0
foreach n [$block getNets] {
 set ty [$n getSigType]; set degree [expr {[llength [$n getITerms]]+[llength [$n getBTerms]]}]
 if {$ty ni {CLOCK SIGNAL} || $degree <= 1} continue
 if {[llength [$n getGuides]] == 0} {lappend missing "$ty:[$n getName]"}
 if {$ty eq "CLOCK"} {incr gc} else {incr gs}
}
if {[llength $missing] || $gc != $nc || $gs != $ns} {error "SPN missing actual guide coverage: $missing"}
ot_pg_require_bound SPN_CAPACITY_OUTPUT
set after [hg_state]; hg_require_same $before $after; hg_write [file join $::env(OUTDIR) frozen.after] $after
write_guides $::env(GUIDE)
write_db $::env(OUT)
puts "SPN_CAPACITY_PROBE_DONE CLOCK=$gc SIGNAL=$gs: raw capacity only, no CTS/source/clock-load/timing/route-signoff release"
