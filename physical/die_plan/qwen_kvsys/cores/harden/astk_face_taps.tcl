# PATH-KV-ASTK4 10-25 (GEOM-REVIEW-2 [PATH-KV-ASTK3 14:36] ruling (a), CLOCK-RESET LC1 (a)): ASTK master regional taps.
# PRE_CTS.  CTS1 (one 'rest' tap for ctl + every face pin register, tap_0 at (108,49), ~125 um branches to the N row,
# pin regs TT 294 / FF 241 vs 250 / 202.5, group spread 53) -> the boundary pin registers get their OWN taps:
#   * face pin registers (RESULTS_DIR/ot_face_flops.txt, written by face_flops.tcl at GPL; any owner incl. zn_0's zl)
#     -> one tap per face chunk: each face's flops sorted along the face and cut into k equal-count chunks,
#     k = max(ceil(n / OT_FT_MAX_SINKS), ceil(span / OT_FT_MAX_SPAN_UM)) (N and S rows -> two half-row taps, E column
#     -> two taps); a face with < OT_FT_MIN_SINKS flops (W: the 2 false-path ID strap landings) joins the ctl tap;
#   * zone flops (OT_LANE_RE, zn_0..3) -> one tap per zone (as before), ctl / fault / rest -> one ctl tap.
# Every tap is one OT_LANE_TAP_CELL at its group centroid driving a new CLOCK net; TritonCTS builds one tree per tap
# net and the top tree from ck to the taps (-balance_levels).  Writes $RESULTS_DIR/ot_lane_taps.json.
uplevel #0 {
set lt_re [expr {[info exists ::env(OT_LANE_RE)] && $::env(OT_LANE_RE) ne "" ? $::env(OT_LANE_RE) : {^(u_u_strip_u_strip_g_zn_[0-9]_u_zn)[./]}}]
set lt_cell [expr {[info exists ::env(OT_LANE_TAP_CELL)] ? $::env(OT_LANE_TAP_CELL) : "BUFx12f_ASAP7_75t_R"}]
set lt_fmax [expr {[info exists ::env(OT_FT_MAX_SINKS)] ? $::env(OT_FT_MAX_SINKS) : 500}]
set lt_fspan [expr {[info exists ::env(OT_FT_MAX_SPAN_UM)] ? $::env(OT_FT_MAX_SPAN_UM) : 100.0}]
set lt_fmin [expr {[info exists ::env(OT_FT_MIN_SINKS)] ? $::env(OT_FT_MIN_SINKS) : 16}]
set lt_blk [ord::get_db_block]
set lt_u [[ord::get_db_tech] getDbUnitsPerMicron]
set lt_master [[ord::get_db] findMaster $lt_cell]
if {$lt_master eq "NULL" || $lt_master eq ""} { error "OT_FACE_TAPS: no master $lt_cell" }
set lt_in ""; set lt_out ""
foreach mt [$lt_master getMTerms] {
  if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
  if {[$mt getIoType] eq "INPUT"} { set lt_in [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set lt_out [$mt getName] }
}
# face pin registers: inst name -> face (N/E/S/W), from face_flops.tcl (fail closed: no table, no taps)
set lt_face [dict create]
set lt_ffile $::env(RESULTS_DIR)/ot_face_flops.txt
if {![file exists $lt_ffile]} { error "OT_FACE_TAPS: $lt_ffile missing (face_flops.tcl must run at GPL)" }
set fh [open $lt_ffile r]
foreach ln [split [read $fh] "\n"] {
  set f [split $ln "\t"]
  if {[llength $f] < 2} continue
  if {[lindex $f 1] in {N E S W}} { dict set lt_face [lindex $f 0] [lindex $f 1] }
}
close $fh
puts "OT_FACE_TAPS face pin registers listed: [dict size $lt_face]"
set lt_roots {}
foreach clk [all_clocks] {
  foreach src [get_property $clk sources] {
    set bt [$lt_blk findBTerm [get_full_name $src]]
    if {$bt ne "NULL" && $bt ne ""} { lappend lt_roots [$bt getNet] }
  }
}
set lt_js {}
set j 0
foreach root [lsort -unique $lt_roots] {
  set groups [dict create]
  set faces [dict create]
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set im [$inst getMaster]
    if {![$im isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL|ICG)} [$im getName]]} continue
    set nm [$inst getName]
    if {[dict exists $lt_face $nm]} { dict lappend faces [dict get $lt_face $nm] $it; continue }
    set k [expr {[regexp $lt_re $nm -> kk] ? $kk : "ctl"}]
    dict lappend groups $k $it
  }
  # face chunks
  dict for {fc its} $faces {
    set n [llength $its]
    if {$n < $lt_fmin} { foreach it $its { dict lappend groups ctl $it }; puts "OT_FACE_TAPS face $fc: $n sinks -> ctl tap"; continue }
    set ax [expr {$fc in {N S} ? 0 : 1}]
    set srt {}
    foreach it $its { set loc [[$it getInst] getLocation]; lappend srt [list [lindex $loc $ax] $it] }
    set srt [lsort -integer -index 0 $srt]
    set span [expr {double([lindex $srt end 0] - [lindex $srt 0 0]) / $lt_u}]
    set kk [expr {max(int(ceil(double($n) / $lt_fmax)), int(ceil($span / $lt_fspan)), 1)}]
    for {set c 0} {$c < $kk} {incr c} {
      set a [expr {($n * $c) / $kk}]; set b [expr {($n * ($c + 1)) / $kk - 1}]
      foreach e [lrange $srt $a $b] { dict lappend groups "face_${fc}$c" [lindex $e 1] }
    }
    puts [format "OT_FACE_TAPS face %s: %d sinks span %.1f um -> %d tap(s)" $fc $n $span $kk]
  }
  if {[dict size $groups] < 2} { puts "OT_FACE_TAPS [$root getName]: [dict size $groups] group(s), no taps"; continue }
  dict for {k its} $groups {
    set sx 0.0; set sy 0.0
    foreach it $its { lassign [[$it getInst] getLocation] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}] }
    set cx [expr {round($sx / [llength $its])}]; set cy [expr {round($sy / [llength $its])}]
    set nm "ot_lane_tap_$j"
    set b [odb::dbInst_create $lt_blk $lt_master $nm]
    $b setLocation $cx $cy
    $b setPlacementStatus PLACED
    set net [odb::dbNet_create $lt_blk "${nm}_ck"]
    $net setSigType CLOCK
    [$b findITerm $lt_in] connect $root
    [$b findITerm $lt_out] connect $net
    foreach it $its { $it disconnect; $it connect $net }
    puts [format "OT_FACE_TAPS %s %s sinks %d at %.1f %.1f" $nm $k [llength $its] [expr {double($cx) / $lt_u}] [expr {double($cy) / $lt_u}]]
    lappend lt_js "\"$nm\": {\"group\": \"[string map {\\ {}} $k]\", \"sinks\": [llength $its], \"x\": [format %.2f [expr {double($cx) / $lt_u}]], \"y\": [format %.2f [expr {double($cy) / $lt_u}]]}"
    incr j
  }
  puts "OT_FACE_TAPS [$root getName]: $j taps"
}
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_lane_taps.json w]; puts $fh "{[join $lt_js {, }]}"; close $fh
}
}
