read_db /work/synth/results/asap7/opentallas_qkd_kvs_attn_fl_ba5_asap7_ref_gate/base/1_synth.odb
set db [ord::get_db]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set f [open /work/candidate/master_areas.json w]
puts $f "\{"
set sep ""
foreach lib [$db getLibs] {
 foreach master [$lib getMasters] {
  set area [expr {double([$master getWidth])*[$master getHeight]/$dbu/$dbu}]
  puts $f "$sep\"[$master getName]\": $area"
  set sep ","
 }
}
puts $f "\}"
close $f
exit
