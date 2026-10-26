read_db /prior/run/results/asap7/hc_kv3_pv_pair__380_16x190_08/base/4_cts.odb
set R /prior/run/results/asap7/hc_kv3_pv_pair__380_16x190_08/base
source /new/pv_pair_taps_key.tcl
set groups {}
foreach inst [$pt_blk getInsts] {
  set m [$inst getMaster]
  if {![$m isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL)} [$m getName]]} continue
  dict incr groups [ot_pv_key [$inst getName]]
}
puts "PV_ACTUAL_CLOCK_GROUPS $groups"
