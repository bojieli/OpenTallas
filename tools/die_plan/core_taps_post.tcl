# QC-RP1 10-25 F5 post-CTS: measure every regional tap (mean / range of its register clock-pin arrivals) and every
# macro leaf, then (1) delay early taps at the TAP INPUT (one chain per tap, structured, not per leaf) so all tap means
# sit within OT_CTAP_WIN (default 20 ps) of the latest; (2) latency-match each macro clock pin to the mean launch
# arrival of its interface registers (the regs driving its wd_in / w_addr_in pins) with a chain at its own leaf input.
# Measured on the parasitics the caller loaded (OT_CTAP_EST=grt -> estimate_parasitics -global_routing, netlist edits
# wrapped in incremental GRT).  Report-only with OT_CTAP_REPORT_ONLY=1.
uplevel #0 {
set cp_blk [ord::get_db_block]
proc cp_env {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
set cp_win [cp_env OT_CTAP_WIN 20.0]
set cp_grt [expr {[cp_env OT_CTAP_EST place] eq "grt"}]
set cp_ronly [cp_env OT_CTAP_REPORT_ONLY 0]
set cp_tag [cp_env OT_CTAP_TAG ctp]
set cp_master [[ord::get_db] findMaster [cp_env OT_CTAP_DELAY_CELL BUFx4_ASAP7_75t_R]]
# QC-PHYS f57 pass-2 (CQB2 OT_MSCTS_CORR mechanism): OT_CTAP_CORR = Tcl file with the measured RCX - estimate offsets of
# the previous routed pass (same estimator / RC table), applied to the GRT-mode balance only:
#   set ot_ctap_corr     { TAP {tt_ps ff_ps} ... }        ;# tap-mean register clock arrival
#   set ot_ctap_corr_mac { INST_GLOB {tt_ps ff_ps} ... }  ;# macro clock pin
set ot_ctap_corr {}; set ot_ctap_corr_mac {}
set cp_corr_on [expr {$cp_grt && [cp_env OT_CTAP_CORR ""] ne ""}]
if {$cp_corr_on} { source [cp_env OT_CTAP_CORR ""]; puts "OT_CTAP_CORR [cp_env OT_CTAP_CORR {}] taps $ot_ctap_corr macros $ot_ctap_corr_mac" }
proc cp_ctap {r} { global cp_corr_on ot_ctap_corr; if {$cp_corr_on && [dict exists $ot_ctap_corr $r]} { return [lindex [dict get $ot_ctap_corr $r] 0] }; return 0.0 }
proc cp_cmac {n} { global cp_corr_on ot_ctap_corr_mac; if {$cp_corr_on} { foreach {g v} $ot_ctap_corr_mac { if {[string match $g [string map {\\ {}} $n]]} { return [lindex $v 0] } } }; return 0.0 }
# OT_CTAP_EST=loaded (QC 10-25, post-route report): use the parasitics the caller read (routed SPEF / RCX), never estimate
set cp_loaded [expr {[cp_env OT_CTAP_EST place] eq "loaded"}]
if {$cp_loaded && !$cp_ronly} { error "OT_CTAP_EST=loaded is report-only (OT_CTAP_REPORT_ONLY=1)" }
proc cp_est {} { global cp_grt cp_loaded; set_propagated_clock [all_clocks]; if {$cp_loaded} return; if {$cp_grt} { estimate_parasitics -global_routing } else { estimate_parasitics -placement } }
proc cp_arr {it} {
  set p [get_pins -quiet [string map {\\ \\\\} "[[$it getInst] getName]/[[$it getMTerm] getName]"]]
  if {![llength $p]} { set p [get_pins -quiet "[[$it getInst] getName]/[[$it getMTerm] getName]"] }
  set a ""; catch {set a [get_property $p arrival_max_rise]}
  return $a
}
# register clock pins below a net (through clock buffers/inverters), not crossing into another tap / leaf
proc cp_regs {net acc} {
  upvar $acc out
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set i [$it getInst]; set m [$i getMaster]
    if {[$m isBlock] || [string match "*DFF*" [$m getName]]} { lappend out $it; continue }
    if {[string match "ot_ctap_*" [$i getName]] || [string match "ot_cleaf_*" [$i getName]]} continue
    foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { cp_regs [$o getNet] out } }
  }
}
proc cp_stats {its} {
  set n 0; set s 0.0; set lo 1e9; set hi -1e9
  foreach it $its { set a [cp_arr $it]; if {$a eq ""} continue; incr n; set s [expr {$s+$a}]; set lo [expr {min($lo,$a)}]; set hi [expr {max($hi,$a)}] }
  if {!$n} { return {0 0 0 0} }
  return [list $n [expr {$s/$n}] $lo $hi]
}
# insert n delay buffers in front of instance input iterm `it`
set cp_k 0
proc cp_hang {it n} {
  global cp_blk cp_master cp_k cp_tag
  set inst [$it getInst]; set prev [$it getNet]; set b [$inst getBBox]
  $it disconnect
  for {set i 0} {$i < $n} {incr i} {
    incr cp_k
    set net [odb::dbNet_create $cp_blk "ot_${cp_tag}_n$cp_k"]; $net setSigType CLOCK
    set buf [odb::dbInst_create $cp_blk $cp_master "ot_${cp_tag}_b$cp_k"]
    foreach t [$buf getITerms] {
      set mt [$t getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq "INPUT"} { $t connect $prev } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $net }
    }
    $buf setLocation [expr {[$b xMin] - ($i+1) * 2 * [$cp_master getWidth]}] [$b yMin]; $buf setPlacementStatus PLACED
    set prev $net
  }
  $it connect $prev
}
proc cp_in {inst} { foreach t [$inst getITerms] { if {[[$t getMTerm] getIoType] eq "INPUT" && [$t getSigType] ne "POWER" && [$t getSigType] ne "GROUND"} { return $t } } }
proc cp_out {inst} { foreach t [$inst getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT"} { return $t } } }
# interface launch registers of a macro: flops whose output reaches its wd_in / w_addr_in through <= 2 buf/inv
proc cp_ifregs {m} {
  set r {}
  foreach it [$m getITerms] {
    if {![regexp {^(wd_in|w_addr_in)} [[$it getMTerm] getName]]} continue
    set net [$it getNet]
    for {set d 0} {$d < 3 && $net ne "NULL"} {incr d} {
      set drv ""; foreach x [$net getITerms] { if {[[$x getMTerm] getIoType] eq "OUTPUT"} { set drv [$x getInst] } }
      if {$drv eq ""} break
      if {[string match "*DFF*" [[$drv getMaster] getName]]} { foreach t [$drv getITerms] { if {[$t isClocked]} { lappend r $t } }; break }
      set net [[cp_in $drv] getNet]
    }
  }
  return $r
}
# per-buffer delay step (BUFx4 + its local wire, measured ~21-23 ps at TT placement RC)
set cp_step [cp_env OT_CTAP_STEP_PS 22.0]
proc cp_taps {it} {
  global cp_blk
  set taps {}
  foreach i [$cp_blk getInsts] {
    if {![regexp {^ot_ctap_([A-Z0-9]+)$} [$i getName] -> r]} continue
    set its {}; cp_regs [[cp_out $i] getNet] its
    lassign [cp_stats $its] n mean lo hi
    set k [cp_ctap $r]; set mean [expr {$mean + $k}]; set lo [expr {$lo + $k}]; set hi [expr {$hi + $k}]
    dict set taps $r [list $i $n $mean $lo $hi]
    puts [format "OT_CTAP_M it%s tap %s n %d mean %.1f min %.1f max %.1f%s" $it $r $n $mean $lo $hi [expr {$k != 0.0 ? [format " (RCX-corrected %+.1f)" $k] : ""}]]
  }
  return $taps
}
# region tap of a register clock iterm (walk the clock net drivers up to an ot_ctap_* instance)
proc cp_regtap {it} {
  set net [$it getNet]
  for {set d 0} {$d < 30 && $net ne "NULL"} {incr d} {
    set drv ""; foreach x [$net getITerms] { if {[[$x getMTerm] getIoType] eq "OUTPUT"} { set drv [$x getInst] } }
    if {$drv eq ""} { return "" }
    if {[regexp {^ot_ctap_([A-Z0-9]+)$} [$drv getName] -> r]} { return $r }
    set net [[cp_in $drv] getNet]
  }
  return ""
}
proc cp_macros {it} {
  global cp_blk
  set out {}
  foreach m [$cp_blk getInsts] {
    if {![[$m getMaster] isBlock]} continue
    set ck ""; foreach t [$m getITerms] { if {[[$t getMTerm] getName] eq "clk"} { set ck $t } }
    # QC 2026-10-25 (GEOM-REVIEW-3 [QC-PHYS-RP1-F57] cond a): ONE set for every statistic. Each interface reg arrival
    # carries the correction of the tap that clocks it (0 when OT_CTAP_CORR is off), the macro pin its own entry;
    # n / mean / min / max and the W-side / E-side split all come from that set (before: mean corrected, min/max raw).
    set a [cp_arr $ck]; if {$a eq ""} { set a 0.0 }; set a [expr {$a + [cp_cmac [$m getName]]}]
    set all {}; set side [dict create W {} E {}]
    foreach t [cp_ifregs $m] {
      set aa [cp_arr $t]; if {$aa eq ""} continue
      set r [cp_regtap $t]; set v [expr {$aa + [cp_ctap $r]}]
      lappend all $v; dict lappend side [expr {[string match {E*} $r] || [string match {SE*} $r] ? "E" : "W"}] $v
    }
    lassign [cp_lstats $all] n mean lo hi
    set sd ""
    foreach s {W E} {
      lassign [cp_lstats [dict get $side $s]] sn smean slo shi
      append sd [format " %s n %d mean %.1f min %.1f (clk - min %.1f)" $s $sn $smean $slo [expr {$sn ? $a-$slo : 0.0}]]
    }
    puts [format "OT_CTAP_M it%s macro %s clk %.1f ifregs n %d mean %.1f min %.1f max %.1f (clk - mean %.1f) |%s" $it [$m getName] $a $n $mean $lo $hi [expr {$a-$mean}] $sd]
    lappend out [list $m $a $mean]
  }
  return $out
}
proc cp_lstats {vs} {
  if {![llength $vs]} { return {0 0.0 0.0 0.0} }
  set s 0.0; set lo 1e9; set hi -1e9
  foreach v $vs { set s [expr {$s+$v}]; set lo [expr {min($lo,$v)}]; set hi [expr {max($hi,$v)}] }
  return [list [llength $vs] [expr {$s/[llength $vs]}] $lo $hi]
}
proc cp_apply {todo} {
  global cp_grt
  if {$cp_grt} { global_route -start_incremental }
  foreach t $todo { lassign $t it n why; puts "OT_CTAP_FIX $why -> $n delay buffers"; cp_hang $it $n }
  detailed_placement
  if {$cp_grt} { global_route -end_incremental }
}
# (1) taps: one fixed target = the latest tap mean at the first measurement; only early taps get delay, never removed
set cp_target ""
for {set cp_it 0} {$cp_it < [cp_env OT_CTAP_ITERS 3]} {incr cp_it} {
  cp_est
  set taps [cp_taps $cp_it]
  if {$cp_target eq ""} { set cp_target -1e9; dict for {r v} $taps { set cp_target [expr {max($cp_target,[lindex $v 2])}] } }
  set todo {}; set lo 1e9; set hi -1e9
  dict for {r v} $taps { lassign $v i n mean; set lo [expr {min($lo,$mean)}]; set hi [expr {max($hi,$mean)}]
    set d [expr {$cp_target - $mean}]; set k [expr {int(round($d / $cp_step))}]
    if {$d > $cp_win / 2.0 && $k >= 1} { lappend todo [list [cp_in $i] $k "it$cp_it tap:$r:[format %.1f $d]"] } }
  puts [format "OT_CTAP_SPREAD it%d taps %.1f..%.1f (%.1f ps, window %.1f) target %.1f" $cp_it $lo $hi [expr {$hi-$lo}] $cp_win $cp_target]
  if {$cp_ronly || ![llength $todo]} break
  cp_apply $todo
}
# OT_CTAP_MACRO_EARLY (ps, default 0): the SRAM clock pin targets (interface launch mean - EARLY): useful skew that gives
# every zero-logic register -> SRAM input path structural hold margin (the SRAM read side has > 150 ps setup slack)
set cp_early [cp_env OT_CTAP_MACRO_EARLY 0.0]
# (2) each macro clock pin latency-matched to the mean launch arrival of its interface registers (own leaf only)
for {set cp_it 0} {!$cp_ronly && $cp_it < 2} {incr cp_it} {
  cp_est
  set todo {}
  foreach row [cp_macros m$cp_it] {
    lassign $row m a mean
    set leaf [$cp_blk findInst "ot_cleaf_[regsub -all {[^A-Za-z0-9]} [$m getName] _]"]
    set tgt [expr {$mean - $cp_early}]
    set k [expr {int(round(($tgt - $a) / $cp_step))}]
    if {$leaf ne "NULL" && $tgt - $a > $cp_step / 2.0 && $k >= 1} { lappend todo [list [cp_in $leaf] $k "m$cp_it macro:[$m getName]:[format %.1f [expr {$tgt-$a}]]"] }
    if {$a - $tgt > $cp_win / 2.0} { puts "OT_CTAP_WARN macro [$m getName] clock pin LATE by [format %.1f [expr {$a-$mean}]] ps vs its interface regs" }
  }
  if {![llength $todo]} break
  cp_apply $todo
}
# GRT mode: after incremental-GRT netlist edits, reset the estimator through placement RC before the GRT estimate
# (else the following repair_design inside global_route -start_incremental fails EST-0104 inconsistent parasitics state)
if {$cp_grt} { estimate_parasitics -placement }
cp_est
cp_taps final
cp_macros final
}
