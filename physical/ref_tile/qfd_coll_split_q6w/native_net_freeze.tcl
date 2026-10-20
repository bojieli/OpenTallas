# QW-ORPHANS2 10-20 (q6w, PRE_GLOBAL_PLACE before the pin flops; parallel fallback to q6): keep the generated native
# fp32 adder graph EXACT (every cell dont_touch, as generated). q5/q5w died in timing-driven GPL (ODB-1211 + RSZ-3006 on
# ...u_native.n1957: the resizer tried to buffer a net whose loads are all dont_touch). Mark every net whose driver and
# all loads are native dont_touch cells dont_touch as well, so the resizer skips it instead of aborting; the native
# graph's own fanout (census <= 32) and the route's sign-off timing decide.
# r2 (q6w r1 gate: CTS ODB-0370, a dont_touch native flop's CLK cannot be connected to the clock tree): native cells
# are released from dont_touch (CTS and placement may touch them); the native COMBINATIONAL graph stays exact because
# every net whose driver and loads are all native cells (no port) is marked dont_touch: the resizer neither buffers
# nor resizes across it.
set ot_nf_b [ord::get_db_block]
set ot_nf_n 0
set ot_nf_r 0
foreach inst [$ot_nf_b getInsts] {
  if {[$inst isDoNotTouch] && [string match {*u_native*} [$inst getName]]} { $inst setDoNotTouch 0; incr ot_nf_r }
}
foreach net [$ot_nf_b getNets] {
  if {[$net isDoNotTouch] || [$net getSigType] in {POWER GROUND CLOCK}} continue
  set its [$net getITerms]
  if {[llength $its] == 0 || [llength [$net getBTerms]] > 0} continue
  set all 1
  foreach it $its { set i [$it getInst]; if {![string match {*u_native*} [$i getName]]} { set all 0; break } }
  if {$all} { $net setDoNotTouch 1; incr ot_nf_n }
}
puts "OT_NATIVE_NET_FREEZE: released $ot_nf_r native cells; $ot_nf_n all-native nets marked dont_touch"
