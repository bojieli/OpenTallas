# DIE-KV-33 KV-006 clock check on the KV-006 die GRT0 (die-kv-32 src_phy/grt): same GRT settings as grt_loaded.tcl (re-run in-session
# so estimate_parasitics -global_routing sees the routes), then the DIE-KV-26 combo readout (vclk on root, 3 fF tap loads, rise+fall per tap,
# per clock cell arrivals) + provider/start FF CLK pin arrivals + slew/cap violators.
set t0 [clock seconds]
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_db /n/access/access.odb
# WHAT-IF B (estimate only, not a build): every die clock net that drives provider FF CLK pins gets a local leaf driver
# (CKINVDCx5p33 pair (B3: x5p33 trunk-side, x16 leaf-side) at the FF-group centroid, overlap not legalized), so the trunk leg stays a non-leaf clock net (M8/M9).
set block [ord::get_db_block]
set m [[ord::get_db] findMaster CKINVDCx5p33_ASAP7_75t_R]; set m2 [[ord::get_db] findMaster CKINVDCx16_ASAP7_75t_R]
set todo {}
foreach n [$block getNets] {
  set ffs {}
  foreach it [$n getITerms] { if {[[$it getMTerm] getName] eq "CLK"} { lappend ffs $it } }
  if {[llength $ffs]} { lappend todo [list $n $ffs] }
}
set k 0
foreach e $todo {
  lassign $e n ffs
  set sx 0; set sy 0
  foreach it $ffs { set loc [[$it getInst] getLocation]; incr sx [lindex $loc 0]; incr sy [lindex $loc 1] }
  set cx [expr {$sx/[llength $ffs]}]; set cy [expr {$sy/[llength $ffs]}]
  set mid [odb::dbNet_create $block "lf_m$k"]; set leaf [odb::dbNet_create $block "lf_l$k"]
  set a [odb::dbInst_create $block $m "lf_a$k"]; set b [odb::dbInst_create $block $m2 "lf_b$k"]
  foreach i [list $a $b] { $i setLocation $cx $cy; $i setPlacementStatus PLACED }
  [$a findITerm A] connect $n; [$a findITerm Y] connect $mid; [$b findITerm A] connect $mid; [$b findITerm Y] connect $leaf
  foreach it $ffs { $it disconnect; $it connect $leaf }
  incr k
}
puts "OT_WHATIF_B leaf drivers $k"
create_clock -name dck -period 833.333 [get_ports root]
set_routing_layers -signal M4-M7 -clock M8-M9
set_global_routing_layer_adjustment M4 0.75
set_global_routing_layer_adjustment M5 0.75
set_global_routing_layer_adjustment M6 0.75
set_global_routing_layer_adjustment M7 0
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose
puts "OT_T grt [expr {[clock seconds]-$t0}]"
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
create_clock -name vclk -period 833.333
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
set fh [open /out/arr_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "T [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [get_property $p slack_min_rise] [get_property $p slew_max_rise]" }
foreach i [get_cells ck_*] { set q [get_pins [get_full_name $i]/Y]; set a [get_pins [get_full_name $i]/A]; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise] [get_property $a slew_max_rise] [get_property $q slew_max_rise]" }
foreach p [get_pins -hierarchical */CLK] { puts $fh "F [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p slew_max_rise]" }
close $fh
set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "D [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slew_max_rise] [get_property $p slew_max_fall]" }
close $fh
report_check_types -max_slew -max_capacitance -violators > /out/drv_$::env(CORNER).rpt
puts "OT_T done [expr {[clock seconds]-$t0}]"
puts OT_DONE
