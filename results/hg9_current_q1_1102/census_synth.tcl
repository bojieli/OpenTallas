read_db /work/run/results/asap7/hc_qkd_ectlk_q1__243_648x172_8/base/1_synth.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set std 0;set mac 0;set seq 0;set sa 0.0;set ma 0.0;set placed 0;set ft 0
foreach i [$b getInsts] {
 set m [$i getMaster]
 set area [expr {double([$m getWidth])*[$m getHeight]/$u/$u}]
 if {[$m isBlock]} {incr mac;set ma [expr {$ma+$area}]} else {incr std;set sa [expr {$sa+$area}]}
 if {[regexp {(^|_)DFF|^DFF} [$m getName]]} {incr seq}
 if {[$i isPlaced]} {incr placed}
 if {[string match *mp_isl0_ck0* [$i getName]]} {incr ft}
}
set f [open /work/q1_synth_model_census.json w]
puts $f [format {{"status":"SYNTH ONLY; no physical/formalqualification","instances":%d,"std_instances":%d,"macro_instances":%d,"sequential_std":%d,"std_area_um2":%.9f,"macro_area_um2":%.9f,"placed_instances":%d,"FT_buffer_instances":%d}} [llength [$b getInsts]] $std $mac $seq $sa $ma $placed $ft]
close $f
