read_db /work/results/asap7/sf7_census/base/1_synth.odb
source /src/results/arch/qw_d2d_safe7_1019/native_dump.tcl
set b [ord::get_db_block]
set area 0; set softarea 0; set nff 0;set nmacro 0
set u [$b getDbUnitsPerMicron]
foreach i [$b getInsts] {
set m [$i getMaster]
set a [expr {double([$m getWidth])*[$m getHeight]/$u/$u}]
set area [expr {$area+$a}]
if {[$m isBlock]} {incr nmacro} else {set softarea [expr {$softarea+$a}]}
if {[regexp -nocase {DFF|SDFF} [$m getName]]} {incr nff}
}
puts "SF7_NATIVE_COST cells=[llength [$b getInsts]] ff=$nff macros=$nmacro area_um2=$area soft_um2=$softarea"
