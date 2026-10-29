# DIE-QC-36 KITS BTAB QC-014 (A)/(B): PLANNED repeater fix for the long-net TT slew class (V1c routed 11 / V1d 12 TT
# violators = DFFHQNx1 QN / BUFx3 / AND3x1 drivers from the S IO band whose routes detour around g_btb[1]/[3]).
# Net set = nets of the pins in OT_PREP_PINS (V1c ROUTED TT slew >= 240 ps = 75 % of the 320 limit, 140 pins measured
# on V1c 6_final.spef with the V1c sign-off session, + the 6 extra V1d TT violators).  One BUFx6f per net, inserted
# between the driver and ALL its loads, at the 50 % point of the driver -> farthest-load L path (horizontal first),
# stepped back toward the driver until outside every macro body (+4.4 halo) and placement blockage; DPL legalizes.
# Clock nets, macro-pin nets, IO-port nets skipped.  Not a check: the existing slew gate judges the routed result.
# Env: OT_PREP_PINS (file), OT_PREP_CELL (BUFx6f_ASAP7_75t_R), OT_PREP_DRY (1 = report only).
proc ot_prep_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc ot_prep_blocked {x y rects} { foreach r $rects { lassign $r a b c d; if {$x >= $a && $x <= $c && $y >= $b && $y <= $d} { return 1 } }; return 0 }
proc ot_prep_run {} {
  set b [ord::get_db_block]; set u [expr double([[ord::get_db_tech] getDbUnitsPerMicron])]
  set cell [ot_prep_env OT_PREP_CELL BUFx6f_ASAP7_75t_R]; set dry [ot_prep_env OT_PREP_DRY 0]
  set master [[ord::get_db] findMaster $cell]; if {$master eq "NULL"} { error "OT_PREP: no master $cell" }
  set rects {}
  foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { set bb [$i getBBox]; lappend rects [list [expr [$bb xMin]/$u-4.4] [expr [$bb yMin]/$u-4.4] [expr [$bb xMax]/$u+4.4] [expr [$bb yMax]/$u+4.4]] } }
  foreach bl [$b getBlockages] { set bb [$bl getBBox]; lappend rects [list [expr [$bb xMin]/$u] [expr [$bb yMin]/$u] [expr [$bb xMax]/$u] [expr [$bb yMax]/$u]] }
  set byname [dict create]
  foreach i [$b getInsts] { dict set byname [string map {\\ {}} [$i getName]] $i }
  set f [open $::env(RESULTS_DIR)/planned_rep.txt w]; set nets [dict create]; set miss 0
  set pf [open [ot_prep_env OT_PREP_PINS /work/planned_rep_pins.txt]]
  foreach p [split [read $pf] "\n"] {
    set p [string trim $p]; if {$p eq ""} continue
    set k [string last / $p]; set in [string range $p 0 [expr $k-1]]; set mt [string range $p [expr $k+1] end]
    if {![dict exists $byname $in]} { puts $f "MISS $p"; incr miss; continue }
    set it [[dict get $byname $in] findITerm $mt]; if {$it eq "NULL"} { puts $f "MISS $p"; incr miss; continue }
    set n [$it getNet]; if {$n eq "NULL"} continue
    dict set nets [$n getName] $n
  }
  close $pf
  set k 0; set skip 0
  dict for {nn n} $nets {
    if {[$n isSpecial] || [$n getSigType] ne "SIGNAL" || [llength [$n getBTerms]] > 0} { puts $f "SKIP $nn special/io"; incr skip; continue }
    set drv ""; set loads {}; set bad ""
    foreach t [$n getITerms] { set i [$t getInst]
      if {[[$i getMaster] isBlock]} { set bad macro }; if {[string match mp_ck* [$i getName]]} { set bad clock }
      if {[$t isOutputSignal]} { set drv $t } else { lappend loads $t } }
    if {$bad ne "" || $drv eq "" || ![llength $loads]} { puts $f "SKIP $nn $bad"; incr skip; continue }
    set dl [$drv getAvgXY]; set dx [expr [lindex $dl 1]/$u]; set dy [expr [lindex $dl 2]/$u]
    set far -1
    foreach t $loads { set l [$t getAvgXY]; set d [expr abs([lindex $l 1]/$u-$dx)+abs([lindex $l 2]/$u-$dy)]; if {$d > $far} { set far $d; set sx [expr [lindex $l 1]/$u]; set sy [expr [lindex $l 2]/$u] } }
    set L $far; set ok 0
    for {set fr 0.5} {$fr >= 0.0} {set fr [expr $fr-0.025]} {
      set s [expr $fr*$L]; set h [expr abs($sx-$dx)]
      if {$s <= $h} { set px [expr $dx + ($sx>$dx?1:-1)*$s]; set py $dy } else { set px $sx; set py [expr $dy + ($sy>$dy?1:-1)*($s-$h)] }
      if {![ot_prep_blocked $px $py $rects]} { set ok 1; break }
    }
    if {!$ok} { puts $f [format "SKIP %s no free point L %.1f" $nn $L]; incr skip; continue }
    puts $f [format "PREP %s drv %s/%s(%s) @%.1f,%.1f loads %d far @%.1f,%.1f L %.1f buf @%.2f,%.2f fr %.3f" $nn [[$drv getInst] getName] [[$drv getMTerm] getName] [[[$drv getInst] getMaster] getName] $dx $dy [llength $loads] $sx $sy $L $px $py $fr]
    if {$dry} { incr k; continue }
    set bi [odb::dbInst_create $b $master ot_prep_$k]
    set nw [odb::dbNet_create $b ot_prep_n$k]; $nw setSigType SIGNAL
    foreach t $loads { $t disconnect; $t connect $nw }
    foreach mt [$master getMTerms] {
      if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq "INPUT"} { [$bi findITerm [$mt getName]] connect $n } else { [$bi findITerm [$mt getName]] connect $nw }
    }
    $bi setLocation [expr round($px*$u)] [expr round($py*$u)]; $bi setPlacementStatus PLACED
    incr k
  }
  close $f
  puts "OT_PLANNED_REP nets [dict size $nets] inserted $k $cell skipped $skip missing_pins $miss (dry $dry); list $::env(RESULTS_DIR)/planned_rep.txt"
}
ot_prep_run
