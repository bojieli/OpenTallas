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
  # FABLE-FIX-HEAD-MESH 11-18 (OT_TAP_PAIR_CAP, opt-in): the receive capacity of the pair planner alone.  hd_mesh: 20 of 83 taps sat
  # exactly at the nearest-sink cap (1500), so no pair component could join them; the planner cap is the tree-size bound, the
  # nearest-sink cap only spreads the first assignment.  Unset = OT_TAP_MAX_SINKS as before.
  if {[info exists ::env(OT_TAP_PAIR_CAP)] && [string is integer -strict $::env(OT_TAP_PAIR_CAP)] && $::env(OT_TAP_PAIR_CAP) > $cap} { set cap $::env(OT_TAP_PAIR_CAP) }
  set rad_um [expr {[info exists ::env(OT_TAP_REASSIGN_UM)] && $::env(OT_TAP_REASSIGN_UM) ne "" ? $::env(OT_TAP_REASSIGN_UM) : 200.0}]
  if {[info exists ::env(OT_TAP_PAIR_RADIUS_UM)]} { set rad_um $::env(OT_TAP_PAIR_RADIUS_UM) }
  set pair [expr {$pair_um*$dbu}]; set rad [expr {$rad_um*$dbu}]
  # DIE-QC-97 11-11 CHAINS (OT_TAP_PAIR_CHAINS=1, plan clock.tap_pair_affinity.chains): chain-owned delay-pad flops join the pair graph
  set chains [expr {[info exists ::env(OT_TAP_PAIR_CHAINS)] && $::env(OT_TAP_PAIR_CHAINS) eq "1"}]
  set chainaff [expr {[info exists ::env(OT_TAP_CHAIN_AFFINITY)] && $::env(OT_TAP_CHAIN_AFFINITY) eq "1" && [llength [info commands ::ot_tap_chain::identity]]}]
  set idents {}
  # DIE-QC-97 11-12 RING (OT_TAP_PAIR_RING_DEPTH / OT_TAP_PAIR_RING_UM, plan clock.tap_pair_affinity.ring_depth /
  # ring_pair_um): inside ONE landing ring (ring_key) a pair also bonds up to the ring depth / distance.  Both unset = off.
  set ring [expr {[info exists ::env(OT_TAP_PAIR_RING_DEPTH)] || [info exists ::env(OT_TAP_PAIR_RING_UM)]}]
  set rdepth [expr {[info exists ::env(OT_TAP_PAIR_RING_DEPTH)] ? $::env(OT_TAP_PAIR_RING_DEPTH) : $depth}]
  set rpair [expr {([info exists ::env(OT_TAP_PAIR_RING_UM)] ? $::env(OT_TAP_PAIR_RING_UM) : $pair_um)*$dbu}]
  set nring 0
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
  set rkeys {}
  if {$ring} { dict for {iname row} $regs { dict set rkeys $iname [::ot_tap_pair::ring_key $iname] } }
  dict for {iname row} $regs {
   lassign $row it x y t
   set inst [$it getInst]
   set front {}
   foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend front [$o getNet] } }
   set seen {}
   set ka [expr {$ring ? [dict get $rkeys $iname] : {}}]
   set wdepth [::ot_tap_pair::walk_depth $depth $rdepth $ka]
   for {set d 0} {$d <= $wdepth && [llength $front]} {incr d} {
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
        set kb [expr {$ring ? [dict get $rkeys $sn] : {}}]
        set ok [::ot_tap_pair::pair_ok $d $dd $depth $pair $ka $kb $rdepth $rpair]
        if {$ok} { lappend pairs [list $dd $iname $sn] }
        if {$ok == 2} { incr nring }
       }
       continue
      }
      if {$d < $wdepth} { foreach o [$si getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend next [$o getNet] } } }
     }
    }
    set front $next
   }
  }
  if {$ring} {
   set nr 0; dict for {n k} $rkeys { if {$k ne {}} { incr nr } }
   puts "OT_TAP_PAIR ring: $nr ring registers, ring depth $rdepth ring pair_um [expr {$rpair/$dbu}], $nring ring-only pairs added"
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
  # FABLE-FIX-HEAD-MESH 11-18 (OT_TAP_PAIR_DUMP=<file>, diagnosis only): the planner input, one row per tap / register / pair
  if {[info exists ::env(OT_TAP_PAIR_DUMP)] && $::env(OT_TAP_PAIR_DUMP) ne ""} {
   set df [open $::env(OT_TAP_PAIR_DUMP) w]
   dict for {t xy} $tapxy { puts $df "T\t$t\t[lindex $xy 0]\t[lindex $xy 1]\t[dict get $load $t]" }
   dict for {n row} $regs { puts $df "R\t$n\t[lindex $row 1]\t[lindex $row 2]\t[lindex $row 3]" }
   foreach e $pairs { puts $df "P\t[lindex $e 1]\t[lindex $e 2]\t[lindex $e 0]" }
   close $df
  }
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
# FABLE-FIX-HEAD-MESH 11-18 MACRO FOLLOW (OT_TAP_PAIR_MACRO=1, default off).  The pair graph above holds flops only, so a
# zero-logic register -> hard-macro input pair (hd_mesh mesh_w2: wdata[i] -> SRAM wd_in[i], about 2,100 of the 10,130 cross-tap
# FF hold violators, the tap window 46-83 ps on a 45-ps data path) kept whatever boundary the nearest-PIN rule gave the macro.
# After the pair pass each macro clock pin moves to the tap that clocks most of the flops driving the inputs it captures
# (through at most OT_TAP_PAIR_DEPTH combinational cells), when that tap lies within the pair radius of the pin.  One clock
# pin per macro: all inputs; several (wclk / rclk): the inputs whose name starts with the first letter of the clock pin.
# Clock pins only; a macro is one sink, so no tap capacity changes materially.
namespace eval ::ot_tap_pair {
 proc macro_follow {} {
  global ct_taps
  set blk [ord::get_db_block]
  set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
  set depth [expr {[info exists ::env(OT_TAP_PAIR_DEPTH)] ? $::env(OT_TAP_PAIR_DEPTH) : 2}]
  set rad_um [expr {[info exists ::env(OT_TAP_REASSIGN_UM)] && $::env(OT_TAP_REASSIGN_UM) ne "" ? $::env(OT_TAP_REASSIGN_UM) : 200.0}]
  if {[info exists ::env(OT_TAP_PAIR_RADIUS_UM)]} { set rad_um $::env(OT_TAP_PAIR_RADIUS_UM) }
  set rad [expr {$rad_um*$dbu}]
  set tapxy {}; set ftap {}; set mpins {}
  foreach tp $ct_taps {
   set net [lindex $tp 1]; set nm [$net getName]
   dict set tapxy $nm [list [lindex $tp 2] [lindex $tp 3]]
   foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]
    if {[[$inst getMaster] isBlock]} { lappend mpins [list $it $nm] } else { dict set ftap [$inst getName] $nm }
   }
  }
  set seen 0; set moved 0; set far 0; set cross0 0; set cross1 0
  foreach row $mpins {
   lassign $row it old
   set inst [$it getInst]; set ck [[$it getMTerm] getName]
   set ncl 0
   foreach t [$inst getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL" && [dict exists $tapxy [[$t getNet] getName]]} { incr ncl } }
   set votes {}
   foreach t [$inst getITerms] {
    if {$t eq $it || ![$t isInputSignal] || [$t getNet] eq "NULL"} continue
    if {[dict exists $tapxy [[$t getNet] getName]]} continue
    if {$ncl > 1 && [string index [[$t getMTerm] getName] 0] ne [string index $ck 0]} continue
    set front [list [$t getNet]]; set vis {}
    for {set d 0} {$d <= $depth && [llength $front]} {incr d} {
     set next {}
     foreach net $front {
      if {[dict exists $vis [$net getName]]} continue
      dict set vis [$net getName] 1
      foreach s [$net getITerms] {
       if {![$s isOutputSignal]} continue
       set si [$s getInst]; set sm [$si getMaster]
       if {[$sm isBlock]} continue
       if {[$sm isSequential]} {
        if {[dict exists $ftap [$si getName]]} { dict incr votes [dict get $ftap [$si getName]] }
        continue
       }
       if {$d < $depth} { foreach o [$si getITerms] { if {[$o isInputSignal] && [$o getNet] ne "NULL" && [[$o getNet] getSigType] eq "SIGNAL"} { lappend next [$o getNet] } } }
      }
     }
     set front $next
    }
   }
   if {![dict size $votes]} continue
   incr seen
   if {[info exists ::env(OT_TAP_PAIR_DUMP)] && $::env(OT_TAP_PAIR_DUMP) ne ""} {
    set df [open $::env(OT_TAP_PAIR_DUMP) a]; set axy0 [$it getAvgXY]
    puts $df "M\t[$inst getName]/$ck\t[lindex $axy0 1]\t[lindex $axy0 2]\t$old\t$votes"; close $df
   }
   set tot 0; dict for {tap c} $votes { incr tot $c }
   set cur [expr {[dict exists $votes $old] ? [dict get $votes $old] : 0}]
   incr cross0 [expr {$tot - $cur}]
   set axy [$it getAvgXY]
   if {![lindex $axy 0]} { set loc [$inst getLocation]; set x [lindex $loc 0]; set y [lindex $loc 1] } else { set x [lindex $axy 1]; set y [lindex $axy 2] }
   set best $old; set bc $cur
   foreach tap [lsort [dict keys $votes]] {
    set c [dict get $votes $tap]
    if {$c <= $bc} continue
    lassign [dict get $tapxy $tap] tx ty
    if {abs($x-$tx)+abs($y-$ty) > $rad} { incr far; continue }
    set best $tap; set bc $c
   }
   incr cross1 [expr {$tot - $bc}]
   if {$best ne $old} { $it disconnect; $it connect [$blk findNet $best]; incr moved }
  }
  puts "OT_TAP_PAIR macro follow: macro clock pins with register-driven inputs $seen, moved $moved, cross-tap register->macro pairs $cross0 -> $cross1, better tap beyond radius $far"
  return $moved
 }
}
if {[info exists ::env(OT_TAP_PAIR_AFFINITY)] && $::env(OT_TAP_PAIR_AFFINITY) eq "1" && [info exists ct_taps] && [llength $ct_taps] >= 2} {
 ::ot_tap_pair::run
 if {[info exists ::env(OT_TAP_PAIR_MACRO)] && $::env(OT_TAP_PAIR_MACRO) eq "1"} { ::ot_tap_pair::macro_follow }
}
