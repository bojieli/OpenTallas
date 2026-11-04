# DIE-QC-66/CLK 11-03 NL conservative clock form: balanced multi-entry ck_de register clock.
# ot_rr_split (OT_RR_SPLIT=1, PRE_CTS) cuts the ck_de register sinks into <=5000-sink regions, each behind one BUFx24
# root; TritonCTS then builds one tree per region.  Free CTS per root lands the roots at different insertion delays
# (5-root probe: hold -209.6 ps), so OT_RR_BALANCE=1 equalizes them right after CTS (before the FF hold gate / repair):
# every region's mean register CK arrival and the ck_de macro (romleaf / rawleaf) CK arrival are measured, the common
# target T = max(all) (the macro anchor, ~700 ps), and each region root gets a BUFx24 delay chain in front of it sized
# to T - mean (2 passes: insert, re-measure, trim).  Data paths are unchanged; only clock insertion moves.
set ::ot_rr_sinks [dict create]
proc ot_rr_split {} {
  set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]
  set net [$blk findNet ck_de]
  if {$net eq "NULL"} { error "OT_RR: net ck_de not found" }
  set master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  array set R {}
  foreach it [$net getITerms] {
    set inst [$it getInst]
    if {[[$inst getMaster] isBlock]} continue
    if {[$it getIoType] ne "INPUT"} continue
    lassign [$inst getLocation] x y
    set xu [expr {double($x) / $dbu}]; set yu [expr {double($y) / $dbu}]
    if {$yu < 660.0} { set r [expr {$xu < 232.0 ? "romW" : "romE"}] } else {
      set r [expr {$xu < 136.5 ? "rawW" : ($xu < 262.5 ? "rawM" : "rawE")}] }
    lappend R($r) [list $it $x $y]
  }
  set regs {}
  foreach r [lsort [array names R]] {
    set L $R($r)
    set k [expr {int(ceil([llength $L] / 5000.0))}]
    if {$k > 1} {
      set L [lsort -integer -index 2 $L]; set sz [expr {int(ceil([llength $L] / double($k)))}]
      for {set i 0} {$i < $k} {incr i} { lappend regs [list ${r}$i [lrange $L [expr {$i * $sz}] [expr {($i + 1) * $sz - 1}]]] }
    } else { lappend regs [list $r $L] }
  }
  foreach rg $regs {
    lassign $rg r L
    set sx 0; set sy 0; foreach e $L { incr sx [lindex $e 1]; incr sy [lindex $e 2] }
    set n [llength $L]; set cx [expr {$sx / $n}]; set cy [expr {$sy / $n}]
    set b [odb::dbInst_create $blk $master "ot_rr_root_$r"]
    $b setLocation $cx $cy; $b setPlacementStatus PLACED
    set nn [odb::dbNet_create $blk "ck_de_rr_$r"]; $nn setSigType CLOCK
    [$b findITerm A] connect $net
    [$b findITerm Y] connect $nn
    set names {}
    foreach e $L { set it [lindex $e 0]; $it disconnect; $it connect $nn
      lappend names "[[$it getInst] getName]/[[$it getMTerm] getName]" }
    dict set ::ot_rr_sinks $r $names
    puts [format "OT_RR region %-6s sinks %5d root at (%.1f, %.1f) um" $r $n [expr {double($cx)/$dbu}] [expr {double($cy)/$dbu}]]
  }
}
proc ot_rr_arr {pinname} {
  if {[catch {set p [get_pins $pinname]}] || $p eq ""} { return "" }
  foreach prop {arrival_max_rise max_rise_arrival} {
    if {![catch {get_property $p $prop} v] && $v ne "" && ![string match *INF* $v]} {
      set v [expr {double($v)}]; return [expr {abs($v) < 1e-6 ? $v * 1e12 : $v}] } }
  return ""
}
proc ot_rr_mean {names} {
  set s 0.0; set n 0; set step [expr {max(1, [llength $names] / 400)}]
  for {set i 0} {$i < [llength $names]} {incr i $step} {
    set a [ot_rr_arr [lindex $names $i]]; if {$a ne ""} { set s [expr {$s + $a}]; incr n } }
  return [expr {$n ? $s / $n : ""}]
}
proc ot_rr_macro_mean {} {
  set blk [ord::get_db_block]; set names {}
  foreach inst [$blk getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    foreach it [$inst getITerms] { set n [$it getNet]
      if {$n ne "NULL" && [$n getSigType] eq "CLOCK"} { lappend names "[$inst getName]/[[$it getMTerm] getName]" } } }
  return [ot_rr_mean $names]
}
proc ot_rr_chain {r nbuf} {
  set blk [ord::get_db_block]; set master [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set root [$blk findInst "ot_rr_root_$r"]; set a [$root findITerm A]; set n0 [$a getNet]
  lassign [$root getLocation] x y
  $a disconnect
  set prev $n0
  for {set i 0} {$i < $nbuf} {incr i} {
    set b [odb::dbInst_create $blk $master "ot_rr_dly_${r}_[clock clicks]_$i"]
    $b setLocation $x $y; $b setPlacementStatus PLACED
    set nn [odb::dbNet_create $blk "ot_rr_dlynet_${r}_[clock clicks]_$i"]; $nn setSigType CLOCK
    [$b findITerm A] connect $prev; [$b findITerm Y] connect $nn; set prev $nn
  }
  $a connect $prev
}
proc ot_rr_balance {} {
  if {[dict size $::ot_rr_sinks] == 0} { puts "OT_RR_BALANCE: no regions"; return }
  set dps [expr {[info exists ::env(OT_RR_BUF_PS)] ? $::env(OT_RR_BUF_PS) : 18.0}]
  for {set pass 1} {$pass <= 2} {incr pass} {
    catch {estimate_parasitics -placement}
    set m [ot_rr_macro_mean]; set T [expr {$m eq "" ? 0.0 : $m}]
    set L [dict create]
    dict for {r names} $::ot_rr_sinks { set v [ot_rr_mean $names]; if {$v ne ""} { dict set L $r $v; if {$v > $T} { set T $v } } }
    set line [format "OT_RR_BALANCE pass %d target %.1f ps (macro %s)" $pass $T [expr {$m eq "" ? "NA" : [format %.1f $m]}]]
    set tot 0
    dict for {r v} $L {
      set d [expr {$T - $v}]; set nb [expr {int(round($d / $dps))}]
      append line [format " %s %.1f(+%d)" $r $v $nb]
      if {$nb > 0} { ot_rr_chain $r $nb; incr tot $nb }
    }
    puts "$line; inserted $tot"
    if {$tot == 0} break
  }
  catch {detailed_placement}
  catch {estimate_parasitics -placement}
  dict for {r names} $::ot_rr_sinks { set v [ot_rr_mean $names]
    if {$v ne ""} { puts [format "OT_RR_BALANCE final %s %.1f ps" $r $v] } }
  set m [ot_rr_macro_mean]; if {$m ne ""} { puts [format "OT_RR_BALANCE final macro %.1f ps" $m] }
}
if {[info exists ::env(OT_RR_SPLIT)] && $::env(OT_RR_SPLIT) eq "1"} {
  ot_rr_split; catch {detailed_placement}
  if {[info exists ::env(OT_RR_BALANCE)] && $::env(OT_RR_BALANCE) eq "1" && [info commands ot_rr_hsg_orig] eq ""} {
    rename ot_hold_structural_gate ot_rr_hsg_orig
    set ::ot_rr_balanced 0
    proc ot_hold_structural_gate {} {
      if {!$::ot_rr_balanced} { set ::ot_rr_balanced 1; ot_rr_balance }
      return [ot_rr_hsg_orig]
    }
  }
}
