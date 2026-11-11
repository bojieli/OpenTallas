# Default-off pre-CTS short-pair affinity, preserving initially coherent
# short-pair components atomically.  No data/reset/cell/timing changes.
# QC vPA showed why aggregate single-register label propagation is insufficient:
# it split the initially same-tap p_f[30] -> r_f[30] pair (1.404 um), worsening
# FF data hold from -60.75 to -66.39 ps.  The pure planner cannot make that cut.
source [file join [file dirname [info script]] tap_pair_plan.tcl]
namespace eval ::ot_tap_pair {
 proc run {} {
  global ct_taps
  set blk [ord::get_db_block]
  set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
  set pair_um [expr {[info exists ::env(OT_TAP_PAIR_UM)] ? $::env(OT_TAP_PAIR_UM) : 60.0}]
  set depth [expr {[info exists ::env(OT_TAP_PAIR_DEPTH)] ? $::env(OT_TAP_PAIR_DEPTH) : 2}]
  set gmax [expr {[info exists ::env(OT_TAP_PAIR_GROUP)] ? $::env(OT_TAP_PAIR_GROUP) : 64}]
  set cap [expr {[info exists ::env(OT_TAP_MAX_SINKS)] ? $::env(OT_TAP_MAX_SINKS) : 1200}]
  set rad_um [expr {[info exists ::env(OT_TAP_REASSIGN_UM)] && $::env(OT_TAP_REASSIGN_UM) ne "" ? $::env(OT_TAP_REASSIGN_UM) : 200.0}]
  if {[info exists ::env(OT_TAP_PAIR_RADIUS_UM)]} { set rad_um $::env(OT_TAP_PAIR_RADIUS_UM) }
  set pair [expr {$pair_um*$dbu}]; set rad [expr {$rad_um*$dbu}]
  # DIE-QC-97 11-11 CHAINS (OT_TAP_PAIR_CHAINS=1, plan clock.tap_pair_affinity.chains): chain-owned delay-pad flops join the pair graph
  set chains [expr {[info exists ::env(OT_TAP_PAIR_CHAINS)] && $::env(OT_TAP_PAIR_CHAINS) eq "1"}]
  set chainaff [expr {[info exists ::env(OT_TAP_CHAIN_AFFINITY)] && $::env(OT_TAP_CHAIN_AFFINITY) eq "1" && [llength [info commands ::ot_tap_chain::identity]]}]
  set idents {}
  # tap nets, their xy and load
  set tapxy {}; set load {}
  foreach tp $ct_taps {
   set net [lindex $tp 1]; set nm [$net getName]
   dict set tapxy $nm [list [lindex $tp 2] [lindex $tp 3]]
   set n 0; foreach it [$net getITerms] { if {[$it isInputSignal]} { incr n } }
   dict set load $nm $n
  }
  # registers on a tap net: clock iterm, xy, tap
  set regs {}
  dict for {nm xy} $tapxy {
   set net [$blk findNet $nm]
   foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]; set m [$inst getMaster]
    if {[$m isBlock] || ![string match {DFF*} [$m getName]] || [[$it getMTerm] getName] ni {CLK CLKN}} continue
    # reset relays / synchronisers belong to their tap (reset_taps.tcl): never move them
    if {[regexp {(^|[/.])(u_rsync_t[0-9]+|u_rst_root|u_rst_in|u_run_root|u_run_in|u_[rs]rl_[0-9]+(_[rgb])?)[/.]} [$inst getName]]} continue
    # A named-chain form owns those clocks, including long coherent runs that
    # this short-pair graph does not enumerate.  Never tear its separate cohort.
    set ident {}
    if {$chainaff} {set ident [::ot_tap_chain::identity [$inst getName]]}
    if {[::ot_tap_pair::skip_chain_owned $chains $chainaff $ident]} continue
    if {$chains && $ident ne {}} {dict set idents [$inst getName] $ident}
    set bb [$inst getBBox]
    dict set regs [$inst getName] [list $it [expr {([$bb xMin]+[$bb xMax])/2}] [expr {([$bb yMin]+[$bb yMax])/2}] $nm]
   }
  }
  puts "OT_TAP_PAIR registers on taps [dict size $regs], taps [dict size $tapxy], pair_um $pair_um depth $depth group $gmax"
  # short direct pairs: Q net -> up to depth combinational cells -> D of a register on a tap
  set pairs {}
  dict for {iname row} $regs {
   lassign $row it x y t
   set inst [$it getInst]
   set front {}
   foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [$o getNet] } }
   set seen {}
   for {set d 0} {$d <= $depth && [llength $front]} {incr d} {
    set next {}
    foreach net $front {
     if {[dict exists $seen [$net getName]]} continue
     dict set seen [$net getName] 1
     if {[llength [$net getITerms]] > 64} continue
     foreach s [$net getITerms] {
      if {![$s isInputSignal]} continue
      set si [$s getInst]; set sm [$si getMaster]
      if {[$sm isBlock]} continue
      if {[$sm isSequential]} {
       set sn [$si getName]
       if {$sn ne $iname && [dict exists $regs $sn]} {
        lassign [dict get $regs $sn] sit sx sy st
        set dd [expr {abs($sx-$x)+abs($sy-$y)}]
        if {$dd <= $pair} { lappend pairs [list $dd $iname $sn] }
       }
       continue
      }
      if {$d < $depth} { foreach o [$si getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend next [$o getNet] } } }
     }
    }
    set front $next
   }
  }
  if {$chains && [dict size $idents]} {
   set seen {}
   foreach e $pairs {lassign $e d a b;dict set seen "$a $b" 1;dict set seen "$b $a" 1}
   set nb 0
   foreach e [::ot_tap_pair::chain_bonds $idents] {
    lassign $e d a b
    if {![dict exists $regs $a] || ![dict exists $regs $b] || [dict exists $seen "$a $b"]} continue
    lappend pairs $e;incr nb
   }
   puts "OT_TAP_PAIR chains: [dict size $idents] chain registers in the pair graph, $nb chain bonds added"
  }
  set maxp [expr {[info exists ::env(OT_TAP_PAIR_PASSES)] ? $::env(OT_TAP_PAIR_PASSES) : 20}]
  set mlim [expr {[info exists ::env(OT_TAP_PAIR_MERGE)] ? $::env(OT_TAP_PAIR_MERGE) : 128}]
  set shp [expr {[info exists ::env(OT_TAP_PAIR_SHIFT)] ? $::env(OT_TAP_PAIR_SHIFT) : 10}]
  set grow [expr {[info exists ::env(OT_TAP_PAIR_OVERFULL_GROW)] ? $::env(OT_TAP_PAIR_OVERFULL_GROW) : 0}]
  set result [plan $regs $pairs $tapxy $load $cap $rad $gmax $maxp $mlim $shp $grow]
  puts "OT_TAP_PAIR coherent components [dict get $result components], largest [dict get $result largest], frozen oversized [dict get $result frozen], taps above cap $cap at start [dict get $result overfull] (donate only unless overfull grow $grow)"
  foreach row [dict get $result passes] {
   lassign $row pass groups pins cross
   puts "OT_TAP_PAIR pass $pass: groups moved $groups clock pins moved $pins cross-tap short pairs $cross"
  }
  if {$chains && [dict size $idents]} {
   lassign [::ot_tap_pair::chain_tap_report $idents $regs [dict get $result regs]] cn csb csa cbroken
   puts "OT_TAP_PAIR chains $cn single-tap before $csb after $csa broken $cbroken"
   if {$cbroken} {error "OT_TAP_PAIR a delay-pad chain left its tap"}
  }
  set changed 0
  dict for {name row} [dict get $result regs] {
   lassign $row it x y target
   if {$target eq [lindex [dict get $regs $name] 3]} continue
   $it disconnect; $it connect [$blk findNet $target];incr changed
  }
  puts "OT_TAP_PAIR done: unique clock pins changed $changed, coherent-pair cuts 0, converged [dict get $result converged]"
  return $changed
 }
}
if {[info exists ::env(OT_TAP_PAIR_AFFINITY)] && $::env(OT_TAP_PAIR_AFFINITY) eq "1" && [info exists ct_taps] && [llength $ct_taps] >= 2} {
 ::ot_tap_pair::run
}
