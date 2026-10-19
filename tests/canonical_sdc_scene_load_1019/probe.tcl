set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach corner {TT FF} {
 set libs($corner) {}
 foreach name [list asap7sc7p5t_AO_RVT_${corner}_nldm_211120.lib.gz asap7sc7p5t_OA_RVT_${corner}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${corner}_nldm_220122.lib.gz asap7sc7p5t_SEQ_RVT_${corner}_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_${corner}_nldm_211120.lib.gz] {
  lappend libs($corner) $plat/lib/NLDM/$name
  read_liberty $plat/lib/NLDM/$name
 }
}
read_db /src/1_synth.odb
set ::env(TC_LIB_FILES) $libs(TT)
set ::env(BC_LIB_FILES) $libs(FF)
set ::env(OT_MM_SETUP_CORNER) TC
set ::env(RESULTS_DIR) /src/out_verified/$::env(CASE)
file mkdir $::env(RESULTS_DIR)
proc log_cmd {args} {uplevel 1 $args}
source /src/$::env(HELPER)
proc dump_caps {label modes} {
 foreach m $modes {
  set_mode $m
  foreach i {0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15} {
   set p [lindex [get_ports "y\[$i\]"] 0]
   foreach mm {min max} {
    set pc [sta::port_ext_pin_cap $p $mm]
    set wc [sta::port_ext_wire_cap $p $mm]
    set fo [sta::port_ext_fanout $p $mm]
    puts "CAP_TABLE:$label:$m:$i:$mm:$pc:$wc:$fo"
   }
  }
  set scenes [get_scenes -modes $m *]
  if {[llength $scenes]} {
   set scene [lindex $scenes 0]
   foreach name {y[5] a[5]} {
    set net [lindex [get_nets $name] 0]
    foreach mm {min max} {
     puts "NET_TABLE:$label:$m:$name:$mm:[$net pin_capacitance $scene $mm]:[$net wire_capacitance $scene $mm]:[$net capacitance $scene $mm]"
    }
   }
  }
 }
}
set sdc /src/test/matrix.sdc
set basecase $::env(CASE)
if {[string match coupon_* $basecase]} {
 set sdc /src/test/coupon.sdc
 set basecase [string range $basecase 7 end]
}
if {$basecase in {reference reference_ff}} {
 if {$basecase eq "reference_ff"} {
  set_mode ff
  define_scene BC -mode ff -liberty $libs(FF)
  read_sdc -mode ff $sdc
 } else {
  set_mode ss
  define_scene TC -mode ss -liberty $libs(TT)
  read_sdc -mode ss $sdc
 }
} else {
 rename define_scene native_define_scene
 proc define_scene {args} {
  set modes [list ss ff]
  dump_caps before_scene $modes
  set rc [native_define_scene {*}$args]
  dump_caps after_scene $modes
  return $rc
 }
 ot_mm_read_sdc $sdc
}
set modes [expr {$basecase eq "reference" ? "ss" : ($basecase eq "reference_ff" ? "ff" : "ss ff")}]
dump_caps after_read $modes
foreach m $modes {
 set_mode $m
 write_sdc -no_timestamp /src/out_verified/$::env(CASE)/before_$m.sdc
}
if {[array exists ::scene_count]} {puts "READ_SCENES:[array get ::scene_count]"}
if {[array exists ::matrix_reads]} {puts "EVAL_COUNTS:[array get ::matrix_reads]|[array get ::include_reads]"}
if {$basecase ni {reference reference_ff}} {
 # Exercise real sync's write/read, scene/mode and exception handling. This
 # synthesis-only ODB has no placement RC: these two diagnostic seams skip
 # timing/RC computation, and no timing qualification is claimed.
 rename estimate_parasitics native_estimate_parasitics
 proc estimate_parasitics {args} {puts "DIAGNOSTIC_NO_PLACEMENT_RC:$args"}
 rename ot_mm_ws native_ot_mm_ws
 proc ot_mm_ws {args} {return 0}
 set ::ot_mm_stage 3_place.sdc
 ot_mm_sync
 ot_mm_unsync
 dump_caps after_sync {ss ff}
 foreach m {ss ff} {
  set_mode $m
  write_sdc -no_timestamp /src/out_verified/$::env(CASE)/after_sync_$m.sdc
 }
}
if {$basecase eq "candidate" && $sdc eq "/src/test/matrix.sdc"} {
 set_mode ss
 foreach {rf mm value} {rise min 71 fall min 72 rise max 73 fall max 74} {
  set_load -pin_load -$rf -$mm $value [get_ports {y[1]}]
 }
 ot_mm_sync
 ot_mm_unsync
 dump_caps after_changed_asym_sync {ss ff}
}
# Scene/library-sensitive expressions have a defined reference: evaluate
# after creating the same scene, rather than replaying side-effectful Tcl.
set_mode [lindex $modes 0]
set ns [llength [get_scenes -modes [sta::cmd_mode_name] *]]
set_load [expr {50 + $ns}] [get_ports {y[7]}]
puts "SCENE_SENSITIVE:ss:$ns"
write_sdc -no_timestamp /src/out_verified/$::env(CASE)/sensitive.sdc
# Native unsupported warnings/errors intentionally remain unchanged.
foreach cmd {
 {set_load -subtract_pin_load 1 [get_ports {y[8]}]}
 {set_load -pin_load 1 [get_nets {y[9]}]}
 {set_load -wire_load 1 [get_nets {y[10]}]}
 {set_load -rise 1 [get_nets {y[11]}]}
 {set_load -bogus 1 [get_ports {y[12]}]}
 {set_load -1 [get_ports {y[13]}]}
} {
 set rc [catch {eval $cmd} msg]
 puts "NATIVE_INVALID:[list $cmd $rc $msg]"
}
exit
