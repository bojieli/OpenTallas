read_db /work/results/asap7/opentallas_qfd_tile_nk_banked_v1_asap7_ref_gate/base/1_synth.odb
set b [ord::get_db_block]
set n 0
set d 0
set h [dict create]
foreach i [$b getInsts] {
 incr n
 set m [[$i getMaster] getName]
 if {[string match DFF* $m]} {incr d; dict incr h $m}
}
puts "QCE_NATIVE_ODB_CENSUS insts=$n dff=$d histogram=$h"
exit
