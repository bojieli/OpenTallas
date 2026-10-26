# QC-A0 v8c (2026-10-24) PRE_GLOBAL_PLACE extras, sourced right after the kit's regions tcl (0 cycles, no RTL change):
#  * OT_A0C_BLOCK "x0 y0 x1 y1;..." (um): hard placement blockages over die whitespace that must stay empty (NL: the
#    node-less W slot and the die-top strip; GPL otherwise parks spread-out logic there, v8b NL review FAIL).
#  * OT_A0C_CONES "g1 g2 ..." + OT_A0C_CONE_DEPTH (default 6): every listed qrl_<g> INCLUSIVE group also owns the
#    EXCLUSIVE combinational fan-in cone of its registers (a comb cell joins only when every load of its outputs is
#    already a member), so GPL's per-region density sees the cone too.  Groups hold registers only otherwise and the
#    top-level cones were spread by a separate density field on top of them: v8b NK hub top band 0.95-0.99 bins.
set a0c_blk [ord::get_db_block]
set a0c_dbu [$a0c_blk getDbUnitsPerMicron]
if {[info exists ::env(OT_A0C_BLOCK)] && $::env(OT_A0C_BLOCK) ne ""} {
  foreach r [split $::env(OT_A0C_BLOCK) ";"] {
    if {[string trim $r] eq ""} continue
    lassign $r x0 y0 x1 y1
    odb::dbBlockage_create $a0c_blk [expr {round($x0*$a0c_dbu)}] [expr {round($y0*$a0c_dbu)}] [expr {round($x1*$a0c_dbu)}] [expr {round($y1*$a0c_dbu)}]
    puts "A0C_BLOCKAGE $x0 $y0 $x1 $y1"
  }
}
if {[info exists ::env(OT_A0C_CONES)] && $::env(OT_A0C_CONES) ne ""} {
  set a0c_depth [expr {[info exists ::env(OT_A0C_CONE_DEPTH)] ? $::env(OT_A0C_CONE_DEPTH) : 6}]
  foreach gname $::env(OT_A0C_CONES) {
    set grp [$a0c_blk findGroup qrl_$gname]
    if {$grp eq "NULL" || $grp eq ""} { error "A0C cone: no group qrl_$gname" }
    set mem [dict create]
    foreach i [$grp getInsts] { dict set mem [$i getName] 1 }
    set front [$grp getInsts]
    set added 0
    for {set d 0} {$d < $a0c_depth && [llength $front]} {incr d} {
      set next {}
      foreach inst $front {
        foreach it [$inst getITerms] {
          if {![$it isInputSignal]} continue
          set mt [$it getMTerm]
          if {[$mt getSigType] in {CLOCK POWER GROUND}} continue
          if {[$mt getName] in {CLK clk ck CK}} continue
          set net [$it getNet]
          if {$net eq "NULL" || $net eq ""} continue
          if {[$net getSigType] in {CLOCK POWER GROUND}} continue
          foreach dit [$net getITerms] {
            if {![$dit isOutputSignal]} continue
            set c [$dit getInst]
            set cn [$c getName]
            if {[dict exists $mem $cn]} continue
            set m [$c getMaster]
            if {[$m isBlock] || [$m isSequential]} continue
            if {[$c getPlacementStatus] in {FIRM LOCKED COVER}} continue
            set cg [$c getGroup]
            if {$cg ne "NULL" && $cg ne ""} continue
            set ok 1
            foreach oit [$c getITerms] {
              if {![$oit isOutputSignal]} continue
              set on [$oit getNet]
              if {$on eq "NULL" || $on eq ""} continue
              if {[llength [$on getBTerms]]} { set ok 0; break }
              foreach lit [$on getITerms] {
                if {[$lit isOutputSignal]} continue
                if {![dict exists $mem [[$lit getInst] getName]]} { set ok 0; break }
              }
              if {!$ok} break
            }
            if {!$ok} continue
            $grp addInst $c
            dict set mem $cn 1
            lappend next $c
            incr added
          }
        }
      }
      set front $next
    }
    puts "A0C_CONE qrl_$gname +$added comb cells (members now [llength [$grp getInsts]])"
  }
}
