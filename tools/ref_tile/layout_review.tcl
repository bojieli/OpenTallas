# layout_review.tcl (TILE-REVIEW 2026-10-23), sourced by layout_dump.tcl: pin registers, clock root buffers, macro pin
# facing and macro OBS layers for tools/ref_tile/layout_review.py.  Needs layout_dump.tcl's ot_ld_block / ot_ld_dbu /
# ot_ld_q / ot_ld_um.  Sets pin_regs, clock_roots, macro_faces, macro_obs (lists of JSON fragments).
#   pin_regs    [pin kind px py fx fy depth]: kind R = nearest flop whose D/Q/QN net reaches the pin through <= 4
#               buffers / inverters, M = a hard macro pin instead, N = neither (depth -1)
#   clock_roots [inst master x0 y0 x1 y1 level]: level 1 = std cells on a clock port net, 2 = buffers they drive
#   macro_faces [inst cx cy pin_cx pin_cy logic_cx logic_cy]: centroid of the macro's signal pins vs its connected cells
#   macro_obs   {master: [OBS layers]}
# OT_LAYOUT_PINREGS=0 skips it.
set pin_regs {}; set clock_roots {}; set macro_faces {}; set macro_obs {}
if {![info exists ::env(OT_LAYOUT_PINREGS)] || $::env(OT_LAYOUT_PINREGS) ne "0"} {
  proc ot_lr_seq {m} { return [regexp {^(DFF|DHL|DLL|SDF|ASYNC|ICG)} $m] }
  proc ot_lr_buf {m} { return [regexp {^(BUF|INV|HB|CKINV|CKBUF)} $m] }
  proc ot_lr_c {bb} { return [list [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $::ot_ld_dbu}] [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $::ot_ld_dbu}]] }
  proc ot_lr_pg {n} { return [expr {[$n getSigType] eq "POWER" || [$n getSigType] eq "GROUND"}] }
  array set ot_lr_cr {}
  set ot_lr_ck {}
  if {[info exists ::env(OT_LAYOUT_CLOCKS)]} { set ot_lr_ck [split $::env(OT_LAYOUT_CLOCKS) ","] }
  foreach bt [$ot_ld_block getBTerms] {
    set n [$bt getNet]
    if {$n eq "NULL" || [ot_lr_pg $n]} { continue }
    if {[$n getSigType] eq "CLOCK" || [lsearch -exact $ot_lr_ck [$bt getName]] >= 0} {
      foreach it [$n getITerms] {
        set i [$it getInst]; set m [$i getMaster]
        if {![$m isBlock] && ![ot_lr_seq [$m getName]]} { set ot_lr_cr([$i getName]) 1 }
      }
      continue
    }
    lassign [ot_lr_c [$bt getBBox]] px py
    set front [list $n]; set seen [dict create [$n getName] 1]; set hits {}; set mac {}; set depth 0
    while {[llength $front] && $depth < 5} {
      set nf {}
      foreach nn $front {
        foreach it [$nn getITerms] {
          set i [$it getInst]; set m [$i getMaster]; set mn [$m getName]
          if {[$m isBlock]} { lappend mac [concat [ot_lr_c [$it getBBox]] $depth]; continue }
          if {[ot_lr_seq $mn]} {
            if {[regexp {^(D|Q|QN)$} [[$it getMTerm] getName]]} { lappend hits [concat [ot_lr_c [$i getBBox]] $depth] }
            continue
          }
          if {[ot_lr_buf $mn]} {
            foreach jt [$i getITerms] {
              set on [$jt getNet]
              if {$on eq "NULL" || [ot_lr_pg $on]} { continue }
              if {![dict exists $seen [$on getName]]} { dict set seen [$on getName] 1; lappend nf $on }
            }
          }
        }
      }
      if {[llength $hits] || [llength $mac]} { break }
      set front $nf; incr depth
    }
    set kind N; set best [list $px $py -1]
    foreach {k lst} [list R $hits M $mac] {
      if {[llength $lst] == 0} { continue }
      set bd 1e30
      foreach h $lst {
        set dd [expr {abs([lindex $h 0] - $px) + abs([lindex $h 1] - $py)}]
        if {$dd < $bd} { set bd $dd; set best $h }
      }
      set kind $k; break
    }
    lappend pin_regs "\[[ot_ld_q [$bt getName]], \"$kind\", [format %.3f $px], [format %.3f $py], [format %.3f [lindex $best 0]], [format %.3f [lindex $best 1]], [lindex $best 2]\]"
  }
  array set ot_lr_cr2 {}
  foreach r [array names ot_lr_cr] {
    set i [$ot_ld_block findInst $r]
    foreach it [$i getITerms] {
      if {![$it isOutputSignal]} { continue }
      set n [$it getNet]; if {$n eq "NULL"} { continue }
      foreach jt [$n getITerms] {
        set j [$jt getInst]; set jm [$j getMaster]
        if {![$jm isBlock] && [ot_lr_buf [$jm getName]] && ![info exists ot_lr_cr([$j getName])]} { set ot_lr_cr2([$j getName]) 1 }
      }
    }
  }
  foreach {arr lvl} {ot_lr_cr 1 ot_lr_cr2 2} {
    foreach r [array names $arr] {
      set i [$ot_ld_block findInst $r]; set bb [$i getBBox]
      lappend clock_roots "\[[ot_ld_q $r], [ot_ld_q [[$i getMaster] getName]], [ot_ld_um [$bb xMin]], [ot_ld_um [$bb yMin]], [ot_ld_um [$bb xMax]], [ot_ld_um [$bb yMax]], $lvl\]"
    }
  }
  array set ot_lr_mo {}
  foreach i [$ot_ld_block getInsts] {
    set m [$i getMaster]; if {![$m isBlock]} { continue }
    if {![info exists ot_lr_mo([$m getName])]} {
      set ls {}
      foreach o [$m getObstructions] { set L [$o getTechLayer]; if {$L ne "NULL"} { lappend ls [ot_ld_q [$L getName]] } }
      set ot_lr_mo([$m getName]) 1
      lappend macro_obs "[ot_ld_q [$m getName]]: \[[join [lsort -unique $ls] ", "]\]"
    }
    set sx 0; set sy 0; set np 0; set lx 0; set ly 0; set nl 0
    foreach it [$i getITerms] {
      set n [$it getNet]
      if {$n eq "NULL" || [ot_lr_pg $n]} { continue }
      lassign [ot_lr_c [$it getBBox]] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]; incr np
      if {[llength [$n getITerms]] > 64} { continue }
      foreach jt [$n getITerms] {
        set j [$jt getInst]
        if {$j eq $i || [[$j getMaster] isBlock]} { continue }
        lassign [ot_lr_c [$j getBBox]] x y; set lx [expr {$lx + $x}]; set ly [expr {$ly + $y}]; incr nl
      }
    }
    if {$np && $nl} {
      lassign [ot_lr_c [$i getBBox]] cx cy
      lappend macro_faces "\[[ot_ld_q [$i getName]], [format %.3f $cx], [format %.3f $cy], [format %.3f [expr {$sx / $np}]], [format %.3f [expr {$sy / $np}]], [format %.3f [expr {$lx / $nl}]], [format %.3f [expr {$ly / $nl}]]\]"
    }
  }
}
