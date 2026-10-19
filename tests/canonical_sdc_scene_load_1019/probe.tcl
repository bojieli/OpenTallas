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
set ::env(RESULTS_DIR) /src/out/$::env(CASE)
file mkdir $::env(RESULTS_DIR)
proc log_cmd {args} {uplevel 1 $args}
source /src/$::env(HELPER)
set sdc /src/test/matrix.sdc
if {$::env(CASE) eq "reference"} {
 set_mode ss
 define_scene TC -mode ss -liberty $libs(TT)
 read_sdc -mode ss $sdc
} else {
 ot_mm_read_sdc $sdc
}
foreach m [expr {$::env(CASE) eq "reference" ? "ss" : "ss ff"}] {
 set_mode $m
 write_sdc -no_timestamp /src/out/$::env(CASE)/before_$m.sdc
}
puts "READ_SCENES:[array get ::scene_count]"
puts "EVAL_COUNTS:[array get ::matrix_reads]|[array get ::include_reads]"
if {$::env(CASE) ne "reference"} {
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
 foreach m {ss ff} {
  set_mode $m
  write_sdc -no_timestamp /src/out/$::env(CASE)/after_sync_$m.sdc
 }
}
# Scene/library-sensitive expressions have a defined reference: evaluate
# after creating the same scene, rather than replaying side-effectful Tcl.
set_mode ss
set ns [llength [get_scenes -modes ss *]]
set_load [expr {50 + $ns}] [get_ports {y[7]}]
puts "SCENE_SENSITIVE:ss:$ns"
write_sdc -no_timestamp /src/out/$::env(CASE)/sensitive.sdc
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
