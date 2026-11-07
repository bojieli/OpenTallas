# S81-ENGRR-B7 11-07: opt-in macro-aware form of regional_taps.tcl (PRE_CTS). Same macro skew groups, tap names for the
# macro taps, protection manifest and CTS -clk_nets contract as regional_taps.tcl; only the regions and the spine differ:
# rt_geo_plan.py clusters the placed registers and walks the spine through free channels. See rt_geo_plan.py.
uplevel #0 {
set rt_blk [ord::get_db_block]
set rt_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rt_bufm [[ord::get_db] findMaster [expr {[info exists ::env(OT_RT_BUF)] ? $::env(OT_RT_BUF) : "BUFx24_ASAP7_75t_R"}]]
set rt_portn [expr {[info exists ::env(OT_RT_PORT)] ? $::env(OT_RT_PORT) : "clk"}]
set rt_bt [$rt_blk findBTerm $rt_portn]
if {$rt_bt eq "NULL"} { set rt_bt [$rt_blk findBTerm "${rt_portn}\[0\]"] }
if {$rt_bt eq "NULL"} { error "OT_RTG: no clock port $rt_portn" }
set rt_root [$rt_bt getNet]
proc rt_ctr {i} { global rt_dbu; set b [$i getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2.0/$rt_dbu}] [expr {([$b yMin]+[$b yMax])/2.0/$rt_dbu}]] }
proc rt_is_macro {i} { return [expr {[[$i getMaster] getType] eq "BLOCK"}] }
proc rt_is_seq {i} { return [[$i getMaster] isSequential] }
proc rt_is_buf {i} { set m [[$i getMaster] getName]; return [expr {[string match BUF* $m] || [string match INV* $m] || [string match HB* $m]}] }
proc rt_out {i} { foreach t [$i getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT" && [$t getNet] ne "NULL"} { return [$t getNet] } }; return "NULL" }
proc rt_buf {name x y in} {
  global rt_blk rt_bufm rt_dbu
  set inst [odb::dbInst_create $rt_blk $rt_bufm $name]
  set out [odb::dbNet_create $rt_blk "${name}_n"]
  $out setSigType CLOCK
  foreach t [$inst getITerms] {
    set mt [$t getMTerm]
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $t connect $in } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $out }
  }
  $inst setLocation [expr {round(($x - 1.0) * $rt_dbu)}] [expr {round($y * $rt_dbu)}]
  $inst setPlacementStatus PLACED
  return $out
}
set regs {}; set macs {}
foreach it [$rt_root getITerms] {
  if {[[$it getMTerm] getIoType] ne "INPUT"} continue
  set i [$it getInst]
  if {[rt_is_macro $i]} { lappend macs $it } elseif {[rt_is_seq $i]} { lappend regs $it } else { error "OT_RTG: non register/macro sink [$i getName] on the root net" }
}
puts "OT_RTG sinks: [llength $regs] registers, [llength $macs] macro clock pins"
# macro skew groups, as regional_taps.tcl (interface registers through <= 1 buffer/inverter)
set grp {}
foreach mit $macs {
  set m [$mit getInst]; set g {}
  foreach t [$m getITerms] {
    set n [$t getNet]; if {$n eq "NULL" || [$n getSigType] in {POWER GROUND CLOCK}} continue
    if {$t eq $mit} continue
    if {[[$t getMTerm] getIoType] eq "INPUT"} {
      set d [$n getFirstOutput]; if {$d eq "NULL" || $d eq ""} continue
      set di [$d getInst]
      if {[rt_is_seq $di]} { lappend g [$di getName] } elseif {[rt_is_buf $di]} {
        foreach u [$di getITerms] { if {[[$u getMTerm] getIoType] eq "INPUT" && [$u getNet] ne "NULL"} { set dd [[$u getNet] getFirstOutput]
          if {$dd ne "NULL" && $dd ne "" && [rt_is_seq [$dd getInst]]} { lappend g [[$dd getInst] getName] } } } }
    } else {
      foreach s [$n getITerms] { if {[[$s getMTerm] getIoType] ne "INPUT"} continue; set si [$s getInst]
        if {[rt_is_seq $si]} { lappend g [$si getName] } elseif {[rt_is_buf $si] || [llength [$si getITerms]] <= 6} {
          set o [rt_out $si]; if {$o eq "NULL"} continue
          foreach s2 [$o getITerms] { if {[[$s2 getMTerm] getIoType] eq "INPUT" && [rt_is_seq [$s2 getInst]]} { lappend g [[$s2 getInst] getName] } } } }
    }
  }
  dict set grp [$m getName] [lsort -unique $g]
}
set ingrp {}
dict for {m g} $grp { foreach r $g { dict set ingrp $r $m } }
# macro tap sites: outside the macro at the W/E edge nearest the clock pin
set rt_mi 0; set mtapn {}; set mloc {}
foreach mit $macs {
  incr rt_mi
  set m [$mit getInst]
  set pbx [$mit getBBox]
  set mx [expr {([$pbx xMin]+[$pbx xMax])/2.0/$rt_dbu}]; set my [expr {([$pbx yMin]+[$pbx yMax])/2.0/$rt_dbu}]
  set mb [$m getBBox]
  if {abs($mx - [$mb xMin]/double($rt_dbu)) < abs($mx - [$mb xMax]/double($rt_dbu))} { set bx [expr {[$mb xMin]/double($rt_dbu) - 6.0}] } else { set bx [expr {[$mb xMax]/double($rt_dbu) + 6.0}] }
  dict set mtapn "ot_rt_mtap$rt_mi" $mit
  dict set mloc [$m getName] [list $bx $my "ot_rt_mtap$rt_mi"]
}
set rt_mgmax [expr {[info exists ::env(OT_RT_MGRP_MAXUM)] ? double($::env(OT_RT_MGRP_MAXUM)) : 60.0}]
set rt_in /work/ot_rtg_in.tsv; set rt_outf /work/ot_rtg_plan.tsv
set fh [open $rt_in w]
set core [$rt_blk getCoreArea]
puts $fh "CORE\t[expr {[$core xMin]/double($rt_dbu)}]\t[expr {[$core yMin]/double($rt_dbu)}]\t[expr {[$core xMax]/double($rt_dbu)}]\t[expr {[$core yMax]/double($rt_dbu)}]"
set pb [$rt_bt getBBox]
puts $fh "PORT\t[expr {([$pb xMin]+[$pb xMax])/2.0/$rt_dbu}]\t[expr {([$pb yMin]+[$pb yMax])/2.0/$rt_dbu}]"
foreach i [$rt_blk getInsts] { if {[rt_is_macro $i]} { set bb [$i getBBox]; puts $fh "MACRO\t[expr {[$bb xMin]/double($rt_dbu)}]\t[expr {[$bb yMin]/double($rt_dbu)}]\t[expr {[$bb xMax]/double($rt_dbu)}]\t[expr {[$bb yMax]/double($rt_dbu)}]" } }
dict for {m v} $mloc { lassign $v bx my tn; puts $fh "MTAP\t$tn\t$bx\t$my" }
set rt_stay {}; set rt_nfar 0
foreach it $regs {
  set i [$it getInst]; set nm [$i getName]
  lassign [rt_ctr $i] x y
  if {[dict exists $ingrp $nm]} {
    lassign [dict get $mloc [dict get $ingrp $nm]] mx2 my2 tn
    if {abs($x-$mx2)+abs($y-$my2) <= $rt_mgmax} { dict set rt_stay $nm $tn; continue }
    incr rt_nfar
  }
  puts $fh "REG\t$nm\t$x\t$y"
}
close $fh
puts "OT_RTG macro groups: [dict size $rt_stay] registers on macro taps, $rt_nfar far ones on region taps (OT_RT_MGRP_MAXUM $rt_mgmax)"
puts [exec python3 -I /work/rt_geo_plan.py $rt_in $rt_outf]
# build
set rt_net [dict create ROOT $rt_root]
set rt_tapnet {}; set rt_assign {}
set fh [open $rt_outf]
foreach line [split [string trim [read $fh]] "\n"] {
  set p [split $line "\t"]
  switch [lindex $p 0] {
    BUF { lassign $p k id x y par; dict set rt_net $id [rt_buf "ot_rt_s$id" $x $y [dict get $rt_net $par]] }
    TAP { lassign $p k nm x y par; dict set rt_tapnet $nm [rt_buf $nm $x $y [dict get $rt_net $par]] }
    ASSIGN { lassign $p k r t; dict set rt_assign $r $t }
  }
}
close $fh
dict for {nm mit} $mtapn { $mit disconnect; $mit connect [dict get $rt_tapnet $nm] }
foreach it $regs {
  set nm [[$it getInst] getName]
  if {[dict exists $rt_stay $nm]} { set t [dict get $rt_stay $nm] } else { set t [dict get $rt_assign $nm] }
  $it disconnect; $it connect [dict get $rt_tapnet $t]
}
set tl {}; set ti {}
dict for {nm n} $rt_tapnet { lappend tl [$n getName]; lappend ti $nm }
set fh [open /work/ot_rt_taps.txt w]; puts $fh [join $ti "\n"]; close $fh
set ::env(CTS_ARGS) "$::env(CTS_ARGS) -clk_nets {$tl}"
# planned spine protection, as regional_taps.tcl OT_RT_PROTECT_SPINE
set ::env(CTS_ARGS) [string map {"-repair_clock_nets" ""} $::env(CTS_ARGS)]
puts "OT_RTG CTS_ARGS $::env(CTS_ARGS)"
set rt_leafnets {}
dict for {nm n} $rt_tapnet { dict set rt_leafnets [$n getName] 1 }
set fp [open /work/ot_rt_spine.tsv w]
foreach i [$rt_blk getInsts] {
  if {![string match ot_rt_* [$i getName]]} continue
  set_dont_touch [get_cells -quiet [$i getName]]
  foreach t [$i getITerms] {
    set mt [$t getMTerm]
    if {[$mt getSigType] in {POWER GROUND} || [$t getNet] eq "NULL"} continue
    if {[$mt getIoType] eq "INPUT"} { puts $fp "[$i getName]\t[$mt getName]\t[[$t getNet] getName]" }
  }
}
foreach n [$rt_blk getNets] {
  set name [$n getName]
  if {![string match ot_rt_* $name] || [dict exists $rt_leafnets $name]} continue
  set_dont_touch [get_nets -quiet $name]
}
close $fp
set ::ot_rt_cts_roots $ti
if {[info commands ot_rt_cts_firm_orig] eq "" && [info commands clock_tree_synthesis] ne ""} {
  rename clock_tree_synthesis ot_rt_cts_firm_orig
  proc clock_tree_synthesis {args} {
    set blk [ord::get_db_block]; set held {}
    foreach nm $::ot_rt_cts_roots {
      set i [$blk findInst $nm]
      if {$i ne "NULL" && $i ne "" && [$i getPlacementStatus] eq "PLACED"} { $i setPlacementStatus FIRM; lappend held $i }
    }
    puts "OT_RTG: [llength $held] tap drivers FIRM during clock_tree_synthesis"
    set rc [catch {uplevel 1 [list ot_rt_cts_firm_orig {*}$args]} msg opts]
    foreach i $held { $i setPlacementStatus PLACED }
    return -options $opts $msg
  }
}
}
