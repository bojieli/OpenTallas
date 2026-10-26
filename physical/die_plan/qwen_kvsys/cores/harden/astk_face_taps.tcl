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
# PATH-KV-ASTK8 10-26 (COORD 01:13 ruling (1), STRUCTURAL: face taps on their own sub-root, contract 250 / 202.5 kept).
# ASTK7 measured face landing insertion TT 256-273 / FF 206-221: (i) TritonCTS latency balancing ("Balancing latency
# for clock clk", delaybuf_*) padded the shallow face-chunk trees up to the deepest 5.4k-sink zone tree, and
# (ii) leaf_affinity.tcl (POST_CTS) re-hung face registers onto zone leaves because their zero-logic partner
# (zl -> zq, pin register <-> stage 2) sat on a zone leaf.  Structure (industry practice: interface registers on their
# own sub-tree, rooted early and balanced to the boundary target):
#   * OT_FACE_SUBROOT=1: the face chunk taps hang on ONE face sub-root buffer (OT_FACE_SUBROOT_CELL, at the centroid of
#     the face sinks) driving net ot_face_root_ck; the zone / ctl taps stay on the port net.  The face network is a
#     separate CTS tree (port -> sub-root -> face taps -> face leaves) and shares only the port with the core trees.
#   * OT_FACE_PARTNER_DEPTH=N (>0): every register joined to a face register by a zero-logic transfer (Q -> D through
#     <= N buf/inv cells, either direction) and within OT_FACE_PARTNER_UM (30) of it joins that face register's chunk,
#     so the pair shares the face tree (no face <-> zone skew on a zero-logic path).
#   * every sink on the face network is listed in $RESULTS_DIR/ot_face_tree_sinks.txt (leaf_affinity.tcl
#     OT_LEAF_AFF_ANCHORS: a group containing these sinks may only be re-hung onto a face-tree leaf).
uplevel #0 {
set lt_sub [expr {[info exists ::env(OT_FACE_SUBROOT)] && $::env(OT_FACE_SUBROOT) eq "1"}]
set lt_subcell [expr {[info exists ::env(OT_FACE_SUBROOT_CELL)] ? $::env(OT_FACE_SUBROOT_CELL) : "BUFx24_ASAP7_75t_R"}]
set lt_pdep [expr {[info exists ::env(OT_FACE_PARTNER_DEPTH)] ? $::env(OT_FACE_PARTNER_DEPTH) : 0}]
set lt_pum [expr {[info exists ::env(OT_FACE_PARTNER_UM)] ? $::env(OT_FACE_PARTNER_UM) : 30.0}]
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
proc lt_isreg {inst} { regexp {^(DFF|ASYNC|SDF)} [[$inst getMaster] getName] }
proc lt_isbi {inst} { regexp {^(BUF|INV|HB|CKINV|CKBUF)} [[$inst getMaster] getName] }
# zero-logic successors: registers whose D is reached from inst's outputs through <= depth buf/inv cells
proc lt_succ {inst depth} {
  set r {}
  foreach o [$inst getITerms] {
    if {![$o isOutputSignal] || [$o getNet] eq "NULL"} continue
    if {[[$o getNet] getSigType] in {POWER GROUND CLOCK}} continue
    foreach it [[$o getNet] getITerms] {
      if {![$it isInputSignal]} continue
      set si [$it getInst]
      if {[lt_isreg $si] && [[$it getMTerm] getName] eq "D"} { lappend r $si } elseif {$depth > 0 && [lt_isbi $si]} { lappend r {*}[lt_succ $si [expr {$depth - 1}]] }
    }
  }
  return $r
}
# zero-logic predecessors: registers whose Q reaches inst's D through <= depth buf/inv cells
proc lt_pred {inst depth} {
  set r {}
  foreach it [$inst getITerms] {
    if {![$it isInputSignal] || [$it getNet] eq "NULL"} continue
    if {[lt_isreg $inst] && [[$it getMTerm] getName] ne "D"} continue
    if {[[$it getNet] getSigType] in {POWER GROUND CLOCK}} continue
    foreach d [[$it getNet] getITerms] {
      if {![$d isOutputSignal]} continue
      set di [$d getInst]
      if {[lt_isreg $di]} { lappend r $di } elseif {$depth > 0 && [lt_isbi $di]} { lappend r {*}[lt_pred $di [expr {$depth - 1}]] }
    }
  }
  return $r
}
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
  set lt_chunk [dict create]
  set lt_root_it [dict create]
  foreach it [$root getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    set im [$inst getMaster]
    if {![$im isBlock] && ![regexp {^(DFF|ASYNC|SDF|DHL|DLL|ICG)} [$im getName]]} continue
    set nm [$inst getName]
    dict set lt_root_it $nm $it
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
      foreach e [lrange $srt $a $b] { dict lappend groups "face_${fc}$c" [lindex $e 1]; dict set lt_chunk [[[lindex $e 1] getInst] getName] "face_${fc}$c" }
    }
    puts [format "OT_FACE_TAPS face %s: %d sinks span %.1f um -> %d tap(s)" $fc $n $span $kk]
  }
  # zero-logic partners of face registers join the face register's chunk (moved out of their zone / ctl group)
  set lt_np 0; set lt_nfar 0
  if {$lt_pdep > 0} {
    set lt_take [dict create]
    dict for {fnm ch} $lt_chunk {
      set fi [$lt_blk findInst $fnm]
      lassign [$fi getLocation] fx fy
      foreach pi [concat [lt_succ $fi $lt_pdep] [lt_pred $fi $lt_pdep]] {
        set pn [$pi getName]
        if {[dict exists $lt_chunk $pn] || [dict exists $lt_take $pn] || ![dict exists $lt_root_it $pn]} continue
        lassign [$pi getLocation] px py
        if {(abs($px - $fx) + abs($py - $fy)) > $lt_pum * $lt_u} { incr lt_nfar; continue }
        dict set lt_take $pn $ch
      }
    }
    set g2 [dict create]
    dict for {k its} $groups {
      foreach it $its {
        set pn [[$it getInst] getName]
        if {[dict exists $lt_take $pn]} { dict lappend g2 [dict get $lt_take $pn] $it; incr lt_np } else { dict lappend g2 $k $it }
      }
    }
    set groups $g2
    puts "OT_FACE_TAPS face partners (zero-logic, depth $lt_pdep, <= $lt_pum um) adopted $lt_np, too far $lt_nfar"
  }
  if {[dict size $groups] < 2} { puts "OT_FACE_TAPS [$root getName]: [dict size $groups] group(s), no taps"; continue }
  set lt_fnet $root
  if {$lt_sub} {
    # face sub-root at the centroid of the face sinks (one buffer on the port net)
    set fx 0.0; set fy 0.0; set fn 0
    dict for {k its} $groups {
      if {![string match face_* $k]} continue
      foreach it $its { lassign [[$it getInst] getLocation] x y; set fx [expr {$fx + $x}]; set fy [expr {$fy + $y}]; incr fn }
    }
    if {$fn == 0} { error "OT_FACE_SUBROOT: no face sinks" }
    set sm [[ord::get_db] findMaster $lt_subcell]
    if {$sm eq "NULL" || $sm eq ""} { error "OT_FACE_SUBROOT: no master $lt_subcell" }
    set sb [odb::dbInst_create $lt_blk $sm ot_face_root]
    set sx0 [expr {round($fx / $fn)}]; set sy0 [expr {round($fy / $fn)}]
    # OT_FACE_SUBROOT_AT=port: root the face network EARLY, at the clock port (2 um inside the core edge)
    if {[info exists ::env(OT_FACE_SUBROOT_AT)] && $::env(OT_FACE_SUBROOT_AT) eq "port"} {
      foreach bt [$root getBTerms] { foreach bp [$bt getBPins] { set bb [$bp getBBox]; set sx0 [$bb xMin]; set sy0 [$bb yMin] } }
      set ca [$lt_blk getCoreArea]
      set sx0 [expr {min(max($sx0, [$ca xMin] + 2 * $lt_u), [$ca xMax] - 2 * $lt_u)}]
      set sy0 [expr {min(max($sy0, [$ca yMin] + 2 * $lt_u), [$ca yMax] - 2 * $lt_u)}]
    }
    $sb setLocation $sx0 $sy0
    $sb setPlacementStatus PLACED
    set lt_fnet [odb::dbNet_create $lt_blk ot_face_root_ck]
    $lt_fnet setSigType CLOCK
    foreach mt [$sm getMTerms] {
      if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
      if {[$mt getIoType] eq "INPUT"} { [$sb findITerm [$mt getName]] connect $root } elseif {[$mt getIoType] eq "OUTPUT"} { [$sb findITerm [$mt getName]] connect $lt_fnet }
    }
    puts [format "OT_FACE_SUBROOT ot_face_root (%s) at %.1f %.1f drives the face taps" $lt_subcell [expr {double($sx0) / $lt_u}] [expr {double($sy0) / $lt_u}]]
    lappend lt_js "\"ot_face_root\": {\"group\": \"face_subroot\", \"sinks\": 0, \"x\": [format %.2f [expr {double($sx0) / $lt_u}]], \"y\": [format %.2f [expr {double($sy0) / $lt_u}]]}"
  }
  set lt_fsinks {}
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
    [$b findITerm $lt_in] connect [expr {[string match face_* $k] ? $lt_fnet : $root}]
    [$b findITerm $lt_out] connect $net
    foreach it $its { $it disconnect; $it connect $net; if {[string match face_* $k]} { lappend lt_fsinks [[$it getInst] getName] } }
    puts [format "OT_FACE_TAPS %s %s sinks %d at %.1f %.1f" $nm $k [llength $its] [expr {double($cx) / $lt_u}] [expr {double($cy) / $lt_u}]]
    lappend lt_js "\"$nm\": {\"group\": \"[string map {\\ {}} $k]\", \"sinks\": [llength $its], \"x\": [format %.2f [expr {double($cx) / $lt_u}]], \"y\": [format %.2f [expr {double($cy) / $lt_u}]]}"
    incr j
  }
  puts "OT_FACE_TAPS [$root getName]: $j taps"
}
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_lane_taps.json w]; puts $fh "{[join $lt_js {, }]}"; close $fh
  if {[info exists lt_fsinks]} { set fh [open $::env(RESULTS_DIR)/ot_face_tree_sinks.txt w]; puts $fh [join $lt_fsinks "\n"]; close $fh }
}
}
