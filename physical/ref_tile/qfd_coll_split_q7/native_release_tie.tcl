# QW-ORPHANS2/QW-COLLQ6 10-20 (q7/q7w, PRE_GLOBAL_PLACE before the pin flops).
# q6 r2 (q6 geometry, native cells released): GRT FAIL overflow 605 (M4 549), hotspot = the std-cell channel x~120-140
#   between the macro stacks (E stack at 129.6) -> q7 takes the q6w geometry (E stack at 172.8: GRT overflow 0).
# q6w r2 (all-native nets frozen dont_touch): GRT overflow 0 but post-GRT FF hold -274 -> -200 ps after repair, residue
#   ~1000 endpoints on native flop D pins (u_native.c2802/D) whose nets were frozen, so hold repair could not buffer
#   them; then DRT-9419 (inst not found) in the parasitic update. -> q7 does NOT freeze nets: native cells released
#   (as q6), so hold/setup repair may buffer native short paths (function unchanged; standard equivalence on the netlist).
# Both r2 runs also carried an UNSPLIT TIELO net g_pf_fan32.u_pf/_409_ with 1345 loads (floorplan repair_tie_fanout
#   inserted 1014 TIEHI copies but no TIELO copies: the loads were dont_touch native cells at floorplan time); one
#   1345-pin net across the tile is pure routing demand. -> after the release, re-run repair_tie_fanout (separation 0).
set ot_nr_b [ord::get_db_block]
set ot_nr_n 0
foreach inst [$ot_nr_b getInsts] {
  if {![$inst isDoNotTouch]} continue
  set nm [$inst getName]
  set mt [[$inst getMaster] getName]
  if {[string match {*u_native*} $nm] || [string match {TIE*} $mt]} { $inst setDoNotTouch 0; incr ot_nr_n }
}
set ot_nr_t 0
foreach inst [$ot_nr_b getInsts] {
  if {![string match {TIE*} [[$inst getMaster] getName]]} continue
  foreach it [$inst getITerms] {
    set n [$it getNet]
    if {$n ne "NULL" && [$n isDoNotTouch]} { $n setDoNotTouch 0; incr ot_nr_t }
  }
}
puts "OT_NATIVE_RELEASE: released $ot_nr_n native/tie cells, $ot_nr_t tie nets"
foreach {ot_tc ot_tp} {TIELOx1_ASAP7_75t_R L TIEHIx1_ASAP7_75t_R H} {
  if {[catch {
    set ot_tl [get_name [get_property [lindex [get_lib_cell $ot_tc] 0] library]]
    repair_tie_fanout -separation 0 $ot_tl/$ot_tc/$ot_tp
  } ot_err]} { puts "OT_NATIVE_RELEASE: repair_tie_fanout $ot_tc failed: $ot_err" }
}
set ot_nr_max 0; set ot_nr_maxn ""
foreach net [$ot_nr_b getNets] {
  if {[$net getSigType] in {POWER GROUND CLOCK}} continue
  set k [llength [$net getITerms]]
  if {$k > $ot_nr_max} { set ot_nr_max $k; set ot_nr_maxn [$net getName] }
}
puts "OT_NATIVE_RELEASE: largest non-clock net after tie repair: $ot_nr_maxn $ot_nr_max iterms"
