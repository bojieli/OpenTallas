# QW-ORPHANS2 10-20 (q6w, PRE_GLOBAL_PLACE before the pin flops; parallel fallback to q6): keep the generated native
# fp32 adder graph EXACT (every cell dont_touch, as generated). q5/q5w died in timing-driven GPL (ODB-1211 + RSZ-3006 on
# ...u_native.n1957: the resizer tried to buffer a net whose loads are all dont_touch). Mark every net whose driver and
# all loads are native dont_touch cells dont_touch as well, so the resizer skips it instead of aborting; the native
# graph's own fanout (census <= 32) and the route's sign-off timing decide.
set ot_nf_b [ord::get_db_block]
set ot_nf_n 0
foreach net [$ot_nf_b getNets] {
  if {[$net isDoNotTouch] || [$net getSigType] in {POWER GROUND CLOCK}} continue
  set its [$net getITerms]
  if {[llength $its] == 0 || [llength [$net getBTerms]] > 0} continue
  set all 1
  foreach it $its { set i [$it getInst]; if {![$i isDoNotTouch] || ![string match {*u_native*} [$i getName]]} { set all 0; break } }
  if {$all} { $net setDoNotTouch 1; incr ot_nf_n }
}
puts "OT_NATIVE_NET_FREEZE: $ot_nf_n all-native nets marked dont_touch"
