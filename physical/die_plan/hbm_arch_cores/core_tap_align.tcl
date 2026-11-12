# core_tap_align.tcl -- POST_CTS hook (HBM-CLKSTRUCT 2026-10-25), runs before the kit's tap_balance.tcl report.
# Balances the density-tap trees of core_density_taps.tcl: measures every tap's mean sink insertion (propagated clock,
# placement RC, CTS corner) and hangs a delay chain in front of each EARLY tap buffer (trunk -> delay cells -> tap)
# until all tap means sit within OT_DTAP_TOL_PS (default 8) of the latest tap -- the owner 10-23 rule "taps balanced
# to <= 20 ps" made explicit instead of trusting TritonCTS level balancing (measured 476..519 / 528..608 ps).
# env: OT_DTAP_TOL_PS, OT_DTAP_DELAY_CELL (default BUFx4_ASAP7_75t_R), OT_DTAP_ROUNDS (default 4), OT_DTAP_NEXT
# (script sourced at the end, default /work/tap_balance.tcl).
# OT_DTAP_ALIGN_LEAD (HBM-TAPS 11-11, optional, CLKLOC 0-cycle clock form): a reviewed file of Tcl records
# {lead_ps {exact_member_instance ...}}, read as data, never eval.  Every tap that drives a listed member aligns to
# (target - lead_ps) instead of the target, i.e. its registers launch lead_ps EARLY on purpose (useful skew for a launch
# group that core_density_taps OT_DTAP_ATOMIC_GROUPS put on its own branch); lead taps do not set the target.  All
# sinks of a lead tap must be listed members of ONE record (an atomic branch), else the script stops.  The final lines
# OT_DTAP_LEAD tap/requested/achieved are the receipt; a lead tap already later than its own target at r0 is a MISS line.
if {![llength [info commands ot_cf_wire]]} { source [file join [file dirname [info script]] clock_family.tcl] }
uplevel #0 {
set ta_blk [ord::get_db_block]
set ta_tol [expr {[info exists ::env(OT_DTAP_TOL_PS)] ? $::env(OT_DTAP_TOL_PS) : 8.0}]
set ta_cell [expr {[info exists ::env(OT_DTAP_DELAY_CELL)] ? $::env(OT_DTAP_DELAY_CELL) : "BUFx4_ASAP7_75t_R"}]
set ta_rounds [expr {[info exists ::env(OT_DTAP_ROUNDS)] ? $::env(OT_DTAP_ROUNDS) : 4}]
set ta_master [[ord::get_db] findMaster $ta_cell]
proc ta_isbuf {i} { return [regexp {^(BUF|INV|CKINV|HB)} [[$i getMaster] getName]] }
proc ta_sinks {net} {
  set out {}; set todo [list $net]; set seen [dict create]
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]
      if {[ta_isbuf $i]} {
        foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
      } else { lappend out "[$i getName]/[[$it getMTerm] getName]" }
    }
  }
  return $out
}
# DIE-HBM-97 11-11 (tapalign-stale-measure): ot_cf_wire reads stored vertex arrivals and never forces a search, so
# after delay cells are inserted a tap could read its pre-edit mean (vecd4ae v512b ot_dtap_700011: 617 -> 617 after 1
# and after 12 cells, final 1067 vs target 860).  Every measurement now forces a full arrival search first, and the
# first sink of every tap is cross-checked against a direct arrival query.  COORD 11-11: a mismatch WARNs by default
# (OT_DTAP_XCHECK_MODE=warn); OT_DTAP_XCHECK_MODE=fail stops the flow (promote after 24 h of real kits with 0 STALE).
set ta_xcheck_ps [expr {[info exists ::env(OT_DTAP_XCHECK_PS)] ? $::env(OT_DTAP_XCHECK_PS) : 1.0}]
set ta_xcheck_mode [expr {[info exists ::env(OT_DTAP_XCHECK_MODE)] ? $::env(OT_DTAP_XCHECK_MODE) : "warn"}]
if {$ta_xcheck_mode ni {warn fail}} { error "OT_DTAP_XCHECK_MODE must be warn or fail, got $ta_xcheck_mode" }
proc ta_fresh_check {tap pin cf ref tol {mode warn}} {
  set msg ""
  if {$ref eq "" || $ref eq "INF" || ![string is double -strict $ref]} {
    set msg "OT_DTAP_ALIGN STALE $tap: no direct arrival for $pin (cross-check impossible)"
  } elseif {abs($cf - $ref) > $tol} {
    set msg "OT_DTAP_ALIGN STALE $tap: $pin measured [format %.2f $cf] ps, direct arrival [format %.2f $ref] ps (tol $tol)"
  }
  if {$msg eq ""} { return 1 }
  if {$mode eq "fail"} { error $msg }
  puts "WARN $msg"
  return 0
}
proc ta_measure {} {
  global ta_blk ta_xcheck_ps ta_xcheck_mode
  set_propagated_clock [all_clocks]
  estimate_parasitics -placement
  ot_cf_refresh
  sta::find_timing 1
  set clk [lindex [all_clocks] 0]
  set res [dict create]
  foreach i [$ta_blk getInsts] {
    set n [$i getName]
    if {![regexp {^ot_dtap_[0-9]+$} $n]} continue
    set y [$i findITerm Y]; set net [$y getNet]
    set s 0.0; set k 0; set mn 1e9; set mx 0.0; set xc 0
    foreach p [ta_sinks $net] {
      set pin [get_pins -quiet $p]; if {$pin eq ""} continue
      # clock_family tagged arrival; a pin it cannot resolve uniquely falls back to the rise arrival property (the
      # core clk port carries no input delay, so a CK pin holds clock arrivals only)
      if {[catch {set a [ot_cf_wire $pin $clk]}] || $a eq ""} {
        if {[catch {set a [get_property $pin arrival_max_rise]}] || $a eq "" || $a eq "INF"} continue
      } elseif {!$xc} {
        # ot_cf_wire reports the arrival relative to the active edge of the waveform (fall edge for a negative-edge
        # register); the direct query is absolute, so take the same edge off it before comparing
        set tr [ot_cf_active $pin]
        set wf {}; foreach t [$clk waveform] {lappend wf [sta::time_sta_ui $t]}
        set ref [get_property $pin [expr {$tr eq "fall" ? "arrival_max_fall" : "arrival_max_rise"}]]
        if {[string is double -strict $ref]} {set ref [expr {$ref - [lindex $wf [expr {$tr eq "fall" ? 1 : 0}]]}]}
        ta_fresh_check $n $p $a $ref $ta_xcheck_ps $ta_xcheck_mode
        set xc 1
      }
      set s [expr {$s + $a}]; incr k; set mn [expr {min($mn, $a)}]; set mx [expr {max($mx, $a)}]
    }
    if {$k} { dict set res $n [list [expr {$s / $k}] $mn $mx $k] }
  }
  return $res
}
proc ta_line {tag m} {
  set l $tag; set lo 1e9; set hi 0
  dict for {n v} $m { set lo [expr {min($lo, [lindex $v 0])}]; set hi [expr {max($hi, [lindex $v 0])}]; append l " [string range $n 8 end]=[format %.0f [lindex $v 0]]([format %.0f [lindex $v 1]]-[format %.0f [lindex $v 2]])" }
  return "$l | tap means [format %.1f $lo]..[format %.1f $hi] spread [format %.1f [expr {$hi - $lo}]] ps"
}
# one delay cell in front of tap inst (between its current input net and its A pin), placed at the tap
proc ta_add {tap r b} {
  global ta_blk ta_master
  set a [$tap findITerm A]; set src [$a getNet]
  set inst [odb::dbInst_create $ta_blk $ta_master "[$tap getName]_al${r}_$b"]
  set nn [odb::dbNet_create $ta_blk "[$tap getName]_al${r}_${b}_n"]; $nn setSigType CLOCK
  foreach t [$inst getITerms] {
    set mt [$t getMTerm]; if {[$mt getSigType] ne "SIGNAL"} continue
    if {[$mt getIoType] eq "INPUT"} { $t connect $src } else { $t connect $nn }
  }
  lassign [$tap getLocation] x y
  $inst setLocation $x $y; $inst setPlacementStatus PLACED
  $a disconnect; $a connect $nn
}
# target = latest tap mean at r0 (fixed, so the target never chases the trunk-load drift); each tap keeps its own
# measured ps/cell (an inserted cell also unloads the trunk, so the first cell can even speed the tap up): clamped to
# 12..30 ps, default 20.  At most ceil(deficit/step) cells per round, never past the target.
# isolation (f790 v3d: the first delay cell in front of a BUFx24 tap took the tap's input load off the trunk and made
# the tap EARLIER, so alignment never converged): every tap first gets one identical isolation cell, so the trunk sees
# a uniform small load per tap and every later cell is pure delay.
if {![info exists ::env(OT_DTAP_ISO)] || $::env(OT_DTAP_ISO)} {
  set ta_iso 0
  foreach i [$ta_blk getInsts] { if {[regexp {^ot_dtap_[0-9]+$} [$i getName]]} { ta_add $i 0 iso; incr ta_iso } }
  detailed_placement
  puts "OT_DTAP_ALIGN iso: $ta_iso taps behind one [$ta_master getName] each"
}
set m [ta_measure]
puts [ta_line "OT_DTAP_ALIGN r0" $m]
set ta_lead [dict create]
if {[info exists ::env(OT_DTAP_ALIGN_LEAD)] && $::env(OT_DTAP_ALIGN_LEAD) ne ""} {
  set fh [open $::env(OT_DTAP_ALIGN_LEAD) r]; set ta_lrec [read $fh]; close $fh
  set ta_mlead [dict create]; set ta_mrec [dict create]; set ri 0
  foreach rec $ta_lrec {
    if {[llength $rec] != 2 || ![string is double -strict [lindex $rec 0]] || [lindex $rec 0] < 0 || [lindex $rec 0] > 200} {error "OT_DTAP_ALIGN_LEAD malformed record (need {lead_ps 0..200 {members}})"}
    foreach nm [lindex $rec 1] {
      set k [string map {\\ {}} $nm]
      if {[dict exists $ta_mlead $k]} {error "OT_DTAP_ALIGN_LEAD member in two records: $nm"}
      dict set ta_mlead $k [lindex $rec 0]; dict set ta_mrec $k $ri
    }
    incr ri
  }
  set ta_seen [dict create]
  foreach i [$ta_blk getInsts] {
    set n [$i getName]
    if {![regexp {^ot_dtap_[0-9]+$} $n]} continue
    set hit {}; set miss 0
    foreach p [ta_sinks [[$i findITerm Y] getNet]] {
      set k [string map {\\ {}} [string range $p 0 [expr {[string last / $p] - 1}]]]
      if {[dict exists $ta_mlead $k]} { lappend hit $k } else { incr miss }
    }
    if {![llength $hit]} continue
    set recs [lsort -unique [lmap k $hit {dict get $ta_mrec $k}]]
    if {$miss || [llength $recs] != 1} {error "OT_DTAP_ALIGN_LEAD tap $n mixes lead members with [expr {$miss}] other sinks / [llength $recs] records: not an atomic lead branch"}
    dict set ta_lead $n [dict get $ta_mlead [lindex $hit 0]]
    foreach k $hit { dict set ta_seen $k 1 }
  }
  dict for {k v} $ta_mlead { if {![dict exists $ta_seen $k]} {error "OT_DTAP_ALIGN_LEAD member $k is on no density tap"} }
  puts "OT_DTAP_ALIGN lead taps [dict size $ta_lead] members [dict size $ta_seen]"
}
# ---- OT_DTAP_ALIGN_ROBUST (HBM-CORES-B 11-12, default off; class hbm-dtap-pad-depth) ----------------------------------------
# The default target is the r0 MAXIMUM tap mean over every tap of every root, so ONE late tap (v32e0 ot_dtap_700028 937 ps,
# 210 ps over the next) sets the padding of all other taps (~14 BUFx12 each).  With OT_DTAP_ALIGN_ROBUST=1 the target is
# the OT_DTAP_ALIGN_PCT percentile (default 90, nearest rank) of the tap means of the MAIN root (the root with the most
# sinks) taps that are not lead taps and carry >= OT_DTAP_ALIGN_MINSINK (default 2) sinks; every other root still aligns to
# that one target.  A tap later than target + OT_DTAP_OUTLIER_PS (default 40) is an OUTLIER: it is never padded to and gets
# no cells.  OT_DTAP_ALIGN_OUTLIER=rehome additionally re-connects the outlier's isolation-cell input to the trunk net of the
# nearest same-root non-outlier tap and keeps the move only if the tap mean drops by >= OT_DTAP_REHOME_MIN_PS (default 20),
# else it is put back (receipt line OT_DTAP_OUTLIER).  Pure procs below (no odb) are replayed offline by test_dtap_robust.py.
proc ta_root_of {n} {
  if {![regexp {^ot_dtap_([0-9]+)$} $n -> id]} { return -1 }
  scan $id %d idn
  return [expr {int($idn / 100000)}]
}
proc ta_main_root {m} {
  set sk [dict create]
  dict for {n v} $m { set r [ta_root_of $n]; dict set sk $r [expr {([dict exists $sk $r] ? [dict get $sk $r] : 0) + [lindex $v 3]}] }
  set best -1; set bs -1
  dict for {r s} $sk { if {$s > $bs || ($s == $bs && $r > $best)} { set best $r; set bs $s } }
  return $best
}
proc ta_robust_target {m lead pct minsink} {
  set mr [ta_main_root $m]; set xs {}; set all {}
  dict for {n v} $m {
    if {[dict exists $lead $n]} continue
    lappend all [lindex $v 0]
    if {[ta_root_of $n] == $mr && [lindex $v 3] >= $minsink} { lappend xs [lindex $v 0] }
  }
  if {![llength $xs]} { set xs $all }
  if {![llength $xs]} { return 0.0 }
  set xs [lsort -real $xs]
  set i [expr {int(ceil($pct / 100.0 * [llength $xs])) - 1}]
  if {$i < 0} { set i 0 }
  return [lindex $xs $i]
}
proc ta_outliers {m lead tgt outps} {
  set out {}
  dict for {n v} $m { if {![dict exists $lead $n] && [lindex $v 0] > $tgt + $outps} { lappend out $n } }
  return $out
}
# predicted padding per root for target tgt: cells = ceil(deficit / step) per tap, deficit = max(0, goal - mean)
proc ta_predict {m lead tgt step skip} {
  set res [dict create]
  dict for {n v} $m {
    set r [ta_root_of $n]
    set g [expr {$tgt - ([dict exists $lead $n] ? [dict get $lead $n] : 0.0)}]
    set d [expr {$g - [lindex $v 0]}]
    if {[lsearch -exact $skip $n] >= 0 || $d <= 0} { set d 0.0; set c 0 } else { set c [expr {int(ceil($d / $step))}] }
    if {![dict exists $res $r]} { dict set res $r [list 0 0 0.0 0.0] }
    lassign [dict get $res $r] nt cells sum mx
    dict set res $r [list [expr {$nt + 1}] [expr {$cells + $c}] [expr {$sum + $d}] [expr {max($mx, $d)}]]
  }
  return $res
}
proc ta_goal {n} { global ta_tgt ta_lead; return [expr {$ta_tgt - ([dict exists $ta_lead $n] ? [dict get $ta_lead $n] : 0.0)}] }
set ta_tgt 0.0; dict for {n v} $m { if {![dict exists $ta_lead $n]} { set ta_tgt [expr {max($ta_tgt, [lindex $v 0])}] } }
set ta_rob [expr {[info exists ::env(OT_DTAP_ALIGN_ROBUST)] && $::env(OT_DTAP_ALIGN_ROBUST)}]
if {$ta_rob} {
  set ta_pct [expr {[info exists ::env(OT_DTAP_ALIGN_PCT)] ? $::env(OT_DTAP_ALIGN_PCT) : 90.0}]
  set ta_minsink [expr {[info exists ::env(OT_DTAP_ALIGN_MINSINK)] ? $::env(OT_DTAP_ALIGN_MINSINK) : 2}]
  set ta_outps [expr {[info exists ::env(OT_DTAP_OUTLIER_PS)] ? $::env(OT_DTAP_OUTLIER_PS) : 40.0}]
  set ta_max_tgt $ta_tgt
  set ta_tgt [ta_robust_target $m $ta_lead $ta_pct $ta_minsink]
  set ta_out [ta_outliers $m $ta_lead $ta_tgt $ta_outps]
  puts "OT_DTAP_ALIGN robust: main root [ta_main_root $m] p$ta_pct target [format %.1f $ta_tgt] (r0 max would be [format %.1f $ta_max_tgt]) outliers [llength $ta_out]"
  foreach {tag tg sk} [list max $ta_max_tgt {} robust $ta_tgt $ta_out] {
    dict for {r v} [ta_predict $m $ta_lead $tg 15.3 $sk] { lassign $v nt cells sum mx; puts "OT_DTAP_PRED $tag root $r taps $nt cells $cells pad_sum_ps [format %.0f $sum] pad_max_ps [format %.0f $mx]" }
  }
  set ta_rehome [expr {[info exists ::env(OT_DTAP_ALIGN_OUTLIER)] && $::env(OT_DTAP_ALIGN_OUTLIER) eq "rehome"}]
  set ta_rmin [expr {[info exists ::env(OT_DTAP_REHOME_MIN_PS)] ? $::env(OT_DTAP_REHOME_MIN_PS) : 20.0}]
  foreach n $ta_out {
    set a0 [lindex [dict get $m $n] 0]
    if {!$ta_rehome} { puts "OT_DTAP_OUTLIER $n mean [format %.1f $a0] target [format %.1f $ta_tgt] kept-unpadded"; continue }
    set tapi [$ta_blk findInst $n]; set iso [$ta_blk findInst "${n}_al0_iso"]
    if {$iso eq "NULL" || $iso eq ""} { puts "OT_DTAP_OUTLIER $n mean [format %.1f $a0] no isolation cell: kept-unpadded"; continue }
    set isoA [$iso findITerm A]; set oldnet [$isoA getNet]
    lassign [$tapi getLocation] tx ty; set best ""; set bd 1e18
    dict for {c v} $m {
      if {$c eq $n || [ta_root_of $c] != [ta_root_of $n] || [lsearch -exact $ta_out $c] >= 0 || [dict exists $ta_lead $c]} continue
      if {[lindex $v 0] > $ta_tgt} continue
      set ci [$ta_blk findInst "${c}_al0_iso"]; if {$ci eq "NULL" || $ci eq ""} continue
      lassign [$ci getLocation] cx cy; set dd [expr {abs($cx - $tx) + abs($cy - $ty)}]
      if {$dd < $bd} { set bd $dd; set best $c }
    }
    if {$best eq ""} { puts "OT_DTAP_OUTLIER $n mean [format %.1f $a0] no candidate trunk: kept-unpadded"; continue }
    set newnet [[[$ta_blk findInst "${best}_al0_iso"] findITerm A] getNet]
    $isoA disconnect; $isoA connect $newnet
    set m2 [ta_measure]; set a1 [lindex [dict get $m2 $n] 0]
    if {$a0 - $a1 >= $ta_rmin} {
      puts "OT_DTAP_OUTLIER $n rehomed onto trunk of $best: mean [format %.1f $a0] -> [format %.1f $a1] ps (dist [format %.0f [expr {$bd / 1000.0}]] um)"
      set m $m2
    } else {
      $isoA disconnect; $isoA connect $oldnet
      puts "OT_DTAP_OUTLIER $n rehome onto $best gave [format %.1f $a0] -> [format %.1f $a1] ps (< $ta_rmin): put back, kept-unpadded"
    }
  }
  if {$ta_rehome && [llength $ta_out]} { set m [ta_measure]; puts [ta_line "OT_DTAP_ALIGN r0b" $m] }
}
dict for {n v} $ta_lead { if {[lindex [dict get $m $n] 0] > [ta_goal $n] + $ta_tol} { puts "OT_DTAP_LEAD MISS $n r0 [format %.1f [lindex [dict get $m $n] 0]] already later than lead goal [format %.1f [ta_goal $n]]" } }
set ta_stp [dict create]
# safety: a tap never takes more than ceil(r0 deficit / 12 ps) + 1 cells in total, and a round whose measurement does
# not move (stale timing) stops the loop -- f790 v3c: a stale measure re-added the same deficit 4x -> 1.1 ns tree.
set ta_cap [dict create]; set ta_used [dict create]
dict for {n v} $m { dict set ta_cap $n [expr {max(0, int(ceil(([ta_goal $n] - [lindex $v 0]) / 12.0)) + 1)}]; dict set ta_used $n 0 }
for {set r 1} {$r <= $ta_rounds} {incr r} {
  set added {}
  dict for {n v} $m {
    set d [expr {[ta_goal $n] - [lindex $v 0]}]
    if {$d <= $ta_tol} continue
    set st [expr {[dict exists $ta_stp $n] ? [dict get $ta_stp $n] : 20.0}]
    # Native multi-root inputs can differ by hundreds of ps (macro-only roots
    # versus large logic trees). Measure one real delay cell before a large
    # fill; the historical 20 ps guess can otherwise overshoot by >50 ps.
    # Without uniform isolation the first cell also unloads the trunk. Warm
    # that transition, then measure a second cell before predicting bulk delay.
    set calibration_rounds 1
    if {[info exists ::env(OT_DTAP_ISO)] && !$::env(OT_DTAP_ISO)} {set calibration_rounds 2}
    if {[info exists ::env(OT_DTAP_CALIBRATE)] && $::env(OT_DTAP_CALIBRATE) && $r <= $calibration_rounds && $d > 30.0} {
      set nb 1
    } else {
      set nb [expr {int(floor($d / $st + 0.5))}]
    }
    set nb [expr {min($nb, [dict get $ta_cap $n] - [dict get $ta_used $n])}]
    if {$nb < 1} continue
    dict incr ta_used $n $nb
    for {set b 0} {$b < $nb} {incr b} { ta_add [$ta_blk findInst $n] $r $b }
    lappend added $n $nb [lindex $v 0]
  }
  if {![llength $added]} break
  detailed_placement
  set m [ta_measure]
  set moved 0
  foreach {n nb a0} $added { if {abs([lindex [dict get $m $n] 0] - $a0) > 1.0} { set moved 1 } }
  if {!$moved} { puts "OT_DTAP_ALIGN WARN r$r: tap means did not move after [expr {[llength $added] / 3}] taps got delay cells (stale timing?) -- stop"; break }
  foreach {n nb a0} $added {
    set st [expr {([lindex [dict get $m $n] 0] - $a0) / double($nb)}]
    dict set ta_stp $n [expr {$st < 12.0 ? 12.0 : ($st > 30.0 ? 30.0 : $st)}]
  }
  puts "[ta_line "OT_DTAP_ALIGN r$r" $m] (target [format %.1f $ta_tgt])"
}
puts [ta_line "OT_DTAP_ALIGN final" $m]
dict for {n l} $ta_lead { puts "OT_DTAP_LEAD $n requested [format %.1f $l] achieved [format %.1f [expr {$ta_tgt - [lindex [dict get $m $n] 0]}]] ps (target [format %.1f $ta_tgt])" }
}
set ta_next [expr {[info exists ::env(OT_DTAP_NEXT)] ? $::env(OT_DTAP_NEXT) : "/work/tap_balance.tcl"}]
if {$ta_next ne "" && [file exists $ta_next]} { source $ta_next }
