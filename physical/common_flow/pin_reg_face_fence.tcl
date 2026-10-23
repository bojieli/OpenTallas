# PRE_GLOBAL_PLACE hook (TILE-FLOW 2026-10-23, ref_tile recipe 5 / spec "tile_plan"): pin-register FACE FENCES.
#
# Why: the 10-23 tile review measured pin registers 300-630 um from their pins (qhub p90 423, bankq 329, hidx_s3 534,
# s81sl_lep 501) and thousands of unregistered boundary pins.  io_flop_at_pins.tcl FIRMs ONE launch/capture flop per
# port at its pin and releases it to PLACED before detailed placement; ports it cannot trace (several captures, deeper
# cones, kits without the hook) float, and nothing keeps any of them at the face afterwards.
#
# What: every flop whose D comes from a top-level input pin, or whose Q/QN drives a top-level output pin (through at
# most OT_FENCE_HOPS buffers / inverters), joins an EXCLUSIVE placement region (OpenDB dbRegion + VOLTAGE_DOMAIN group,
# the native GPL/DPL fence of physical/dscoll_cx/native_cell_fence.tcl) that is a band along THAT pin's face, at most
# OT_FENCE_MAX_UM (default 14.04 um, inside the 20 um macro keep-off of a pin face) deep.  The band depth per face is
# the face's register area at OT_FENCE_FILL (0.5), in whole rows, at least OT_FENCE_MIN_UM (4.32).  N / S bands span
# the core width; W / E bands sit between them (regions never overlap).  The fence holds through GPL, repair, CTS and
# every DPL; nothing else may enter the band (EXCLUSIVE), so it stays a clean register column.
#
# Pin classes (written to $RESULTS_DIR/ot_face_fence.tsv: port bit, face, class, flops):
#   reg       exactly one register per input bit / the output's driver is a register        -> fenced
#   multi     an input bit captured by 2..OT_FENCE_MULTI_MAX (4) registers                  -> all fenced (RTL should
#                                                                                              register once; reported)
#   macro     the bit connects straight to a hard macro pin (SRAM/ROM port at the boundary)  -> not a pin register;
#                                                                                              unregistered unless ok
#   none      logic between the pin and every register (or > MULTI_MAX captures)            -> UNREGISTERED
# Unregistered bits whose port name does not match OT_FENCE_UNREG_OK (a regexp of the spec "unregistered_ok" keys) are
# a hard error when OT_FENCE_STRICT=1 (default): registers come from the RTL, never from the flow.  Clock nets (sig
# type CLOCK or OT_FENCE_CLOCKS) and power are skipped; reset inputs count like data (the reset landing flops are the
# pin registers of a reset port).
#
# Env: OT_FENCE_HOPS (4) OT_FENCE_MAX_UM (14.04) OT_FENCE_MIN_UM (4.32) OT_FENCE_FILL (0.5) OT_FENCE_MULTI_MAX (4)
#      OT_FENCE_STRICT (1) OT_FENCE_UNREG_OK (regexp on the port base name, "" = none) OT_FENCE_CLOCKS (comma list)
set ot_ff_blk [ord::get_db_block]
set ot_ff_u [[ord::get_db_tech] getDbUnitsPerMicron]
proc ot_ff_env {k d} { if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) }; return $d }
set ot_ff_hops [ot_ff_env OT_FENCE_HOPS 4]
set ot_ff_max [ot_ff_env OT_FENCE_MAX_UM 14.04]
set ot_ff_min [ot_ff_env OT_FENCE_MIN_UM 4.32]
set ot_ff_fill [ot_ff_env OT_FENCE_FILL 0.5]
set ot_ff_mmax [ot_ff_env OT_FENCE_MULTI_MAX 4]
set ot_ff_strict [ot_ff_env OT_FENCE_STRICT 1]
set ot_ff_ok [ot_ff_env OT_FENCE_UNREG_OK ""]
set ot_ff_clocks [split [ot_ff_env OT_FENCE_CLOCKS ""] ","]
set ot_ff_row 0.27
set ot_ff_core [$ot_ff_blk getCoreArea]
set ot_ff_cx0 [expr {double([$ot_ff_core xMin]) / $ot_ff_u}]; set ot_ff_cx1 [expr {double([$ot_ff_core xMax]) / $ot_ff_u}]
set ot_ff_cy0 [expr {double([$ot_ff_core yMin]) / $ot_ff_u}]; set ot_ff_cy1 [expr {double([$ot_ff_core yMax]) / $ot_ff_u}]
set ot_ff_die [$ot_ff_blk getDieArea]
set ot_ff_dx0 [expr {double([$ot_ff_die xMin]) / $ot_ff_u}]; set ot_ff_dx1 [expr {double([$ot_ff_die xMax]) / $ot_ff_u}]
set ot_ff_dy0 [expr {double([$ot_ff_die yMin]) / $ot_ff_u}]; set ot_ff_dy1 [expr {double([$ot_ff_die yMax]) / $ot_ff_u}]

# ORFS sources hooks inside a proc: publish what ot_ff_face reads as true globals
foreach ot_ff_v {ot_ff_u ot_ff_dx0 ot_ff_dx1 ot_ff_dy0 ot_ff_dy1} { set ::$ot_ff_v [set $ot_ff_v] }
proc ot_ff_isff {inst} { return [regexp {^(DFF|ASYNC_DFF|SDF|DHL|DLL)} [[$inst getMaster] getName]] }
proc ot_ff_isbuf {inst} { return [regexp {^(INV|BUF|HB|CKINV|CKBUF)} [[$inst getMaster] getName]] }
# input bit: data captures through buffer / inverter branches (D pin only); {regs macro other}
proc ot_ff_fwd {net hops} {
  set regs {}; set mac 0; set oth 0
  set front [list $net]; set seen [dict create]
  for {set d 0} {$d <= $hops && [llength $front]} {incr d} {
    set nf {}
    foreach n $front {
      if {[dict exists $seen [$n getName]]} continue
      dict set seen [$n getName] 1
      foreach it [$n getITerms] {
        if {![$it isInputSignal]} continue
        set i [$it getInst]
        if {[[$i getMaster] isBlock]} { incr mac; continue }
        if {[ot_ff_isff $i]} {
          if {[[$it getMTerm] getName] eq "D"} { lappend regs $i } else { incr oth }
          continue
        }
        if {[ot_ff_isbuf $i] && $d < $hops} {
          foreach ot [$i getITerms] { if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { lappend nf [$ot getNet] } }
          continue
        }
        incr oth
      }
    }
    set front $nf
  }
  return [list [lsort -unique $regs] $mac $oth]
}
# output bit: walk back through buffers / inverters to the driver; {reg macro}
proc ot_ff_bwd {net hops} {
  for {set d 0} {$d <= $hops} {incr d} {
    set drv ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv $it; break } }
    if {$drv eq ""} { return [list "" 0] }
    set i [$drv getInst]
    if {[[$i getMaster] isBlock]} { return [list "" 1] }
    if {[ot_ff_isff $i]} { return [list $i 0] }
    if {![ot_ff_isbuf $i]} { return [list "" 0] }
    set in ""
    foreach it [$i getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { set in [$it getNet] } }
    if {$in eq ""} { return [list "" 0] }
    set net $in
  }
  return [list "" 0]
}
proc ot_ff_face {bt} {
  global ot_ff_u ot_ff_dx0 ot_ff_dx1 ot_ff_dy0 ot_ff_dy1
  set bb [$bt getBBox]
  set x [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $ot_ff_u}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $ot_ff_u}]
  set d [dict create W [expr {$x - $ot_ff_dx0}] E [expr {$ot_ff_dx1 - $x}] S [expr {$y - $ot_ff_dy0}] N [expr {$ot_ff_dy1 - $y}]]
  set best ""; set bd 1e30
  foreach f {W E S N} { if {[dict get $d $f] < $bd} { set bd [dict get $d $f]; set best $f } }
  return $best
}

set ot_ff_tsv [open $::env(RESULTS_DIR)/ot_face_fence.tsv w]
puts $ot_ff_tsv "port\tface\tclass\tflops"
set ot_ff_of [dict create]           ;# flop name -> face (first face wins; a conflict is reported)
set ot_ff_conf 0
set ot_ff_cls [dict create reg 0 multi 0 macro 0 none 0]
set ot_ff_bad {}
foreach bt [$ot_ff_blk getBTerms] {
  set net [$bt getNet]
  if {$net eq "NULL"} continue
  if {[$net getSigType] in {POWER GROUND CLOCK}} continue
  set pn [$bt getName]
  regsub {\[.*$} $pn {} base
  if {[lsearch -exact $ot_ff_clocks $base] >= 0 || [lsearch -exact $ot_ff_clocks $pn] >= 0} continue
  if {[llength [$bt getBPins]] == 0} continue
  set face [ot_ff_face $bt]
  set io [$bt getIoType]
  set regs {}
  if {$io eq "INPUT"} {
    lassign [ot_ff_fwd $net $ot_ff_hops] regs mac oth
    if {[llength $regs] == 1 && $oth == 0 && $mac == 0} { set cls reg
    } elseif {[llength $regs] >= 2 && [llength $regs] <= $ot_ff_mmax && $oth == 0 && $mac == 0} { set cls multi
    } elseif {$mac > 0 && [llength $regs] == 0 && $oth == 0} { set cls macro; set regs {}
    } else { set cls none; set regs {} }
  } elseif {$io eq "OUTPUT"} {
    lassign [ot_ff_bwd $net $ot_ff_hops] r mac
    if {$r ne ""} { set cls reg; set regs [list $r] } elseif {$mac} { set cls macro } else { set cls none }
  } else {
    continue
  }
  dict incr ot_ff_cls $cls
  if {$cls in {macro none}} {
    if {$ot_ff_ok eq "" || ![regexp -- "^(?:$ot_ff_ok)\$" $base]} { lappend ot_ff_bad "$pn:$cls" }
  }
  set names {}
  foreach r $regs {
    set rn [$r getName]
    lappend names $rn
    if {[dict exists $ot_ff_of $rn] && [dict get $ot_ff_of $rn] ne $face} { incr ot_ff_conf; continue }
    dict set ot_ff_of $rn $face
  }
  puts $ot_ff_tsv "$pn\t$face\t$cls\t[join $names ,]"
}
close $ot_ff_tsv

# band depth per face from the register area it holds
set ot_ff_area [dict create N 0.0 S 0.0 E 0.0 W 0.0]
set ot_ff_stolen [dict create]
set ot_ff_list [dict create N {} S {} E {} W {}]
dict for {rn f} $ot_ff_of {
  set i [$ot_ff_blk findInst $rn]
  if {$i eq "NULL"} continue
  set og [$i getGroup]
  if {$og ne "NULL"} {
    # a pin register inside a kit's own GPL region (e.g. the HC hub's central std-cell band) is taken out of it: pin
    # registers belong at their face (owner rule), the kit region keeps the rest of its logic
    if {[string match ot_face_fence_* [$og getName]]} continue
    $og removeInst $i
    dict incr ot_ff_stolen [$og getName]
  }
  set m [$i getMaster]
  dict set ot_ff_area $f [expr {[dict get $ot_ff_area $f] + double([$m getWidth]) * [$m getHeight] / $ot_ff_u / $ot_ff_u}]
  dict lappend ot_ff_list $f $rn
}
set ot_ff_dep [dict create]
foreach f {N S E W} {
  set len [expr {$f in {N S} ? $ot_ff_cx1 - $ot_ff_cx0 : $ot_ff_cy1 - $ot_ff_cy0}]
  set a [dict get $ot_ff_area $f]
  if {$a <= 0} { dict set ot_ff_dep $f 0.0; continue }
  set d [expr {$a / ($ot_ff_fill * $len)}]
  set d [expr {ceil($d / $ot_ff_row - 1e-9) * $ot_ff_row}]
  if {$d < $ot_ff_min} { set d $ot_ff_min }
  if {$d > $ot_ff_max} {
    puts "FACE_FENCE WARN face $f needs [format %.2f $d] um of band for [format %.0f $a] um2 of registers; capped at $ot_ff_max (band fill [format %.2f [expr {$a / ($ot_ff_max * $len)}]])"
    set d $ot_ff_max
  }
  dict set ot_ff_dep $f $d
}
set dN [dict get $ot_ff_dep N]; set dS [dict get $ot_ff_dep S]
set ot_ff_boxes [dict create \
  N [list $ot_ff_cx0 [expr {$ot_ff_cy1 - $dN}] $ot_ff_cx1 $ot_ff_cy1] \
  S [list $ot_ff_cx0 $ot_ff_cy0 $ot_ff_cx1 [expr {$ot_ff_cy0 + $dS}]] \
  W [list $ot_ff_cx0 [expr {$ot_ff_cy0 + $dS}] [expr {$ot_ff_cx0 + [dict get $ot_ff_dep W]}] [expr {$ot_ff_cy1 - $dN}]] \
  E [list [expr {$ot_ff_cx1 - [dict get $ot_ff_dep E]}] [expr {$ot_ff_cy0 + $dS}] $ot_ff_cx1 [expr {$ot_ff_cy1 - $dN}]]]
set ot_ff_n 0
foreach f {N S E W} {
  set names [dict get $ot_ff_list $f]
  if {![llength $names] || [dict get $ot_ff_dep $f] <= 0} continue
  lassign [dict get $ot_ff_boxes $f] x0 y0 x1 y1
  set nm "ot_face_fence_$f"
  set r [odb::dbRegion_create $ot_ff_blk $nm]
  $r setRegionType EXCLUSIVE
  odb::dbBox_create $r [expr {round($x0 * $ot_ff_u)}] [expr {round($y0 * $ot_ff_u)}] [expr {round($x1 * $ot_ff_u)}] [expr {round($y1 * $ot_ff_u)}]
  set g [odb::dbGroup_create $r $nm]
  $g setType VOLTAGE_DOMAIN
  # a FIRM pin flop (io_flop_at_pins) sits AT its pin already and stays FIRM (releasing it lets GPL slide it along the
  # band, measured p90 7.7 -> 127 um); every other pin register (several captures, untraced, no io_flop_at_pins) is
  # fenced.  A face with no movable register gets no region (GPL-0304 -nan on a region without a movable instance).
  set mov {}
  foreach rn $names {
    set i [$ot_ff_blk findInst $rn]
    if {[$i getPlacementStatus] ni {FIRM LOCKED}} { lappend mov $i }
  }
  if {![llength $mov]} {
    odb::dbGroup_destroy $g
    odb::dbRegion_destroy $r
    puts "FACE_FENCE face $f: all [llength $names] pin registers FIRM at their pins (io_flop_at_pins), no fence needed"
    incr ot_ff_n [llength $names]
    continue
  }
  foreach i $mov { $g addInst $i }
  dict set ot_ff_list $f [lmap i $mov {$i getName}]
  incr ot_ff_n [llength $names]
  puts "FACE_FENCE region $nm box [format {%.2f %.2f %.2f %.2f} $x0 $y0 $x1 $y1] depth [format %.2f [dict get $ot_ff_dep $f]] um flops [llength $names] area [format %.0f [dict get $ot_ff_area $f]] um2"
}
dict for {gn c} $ot_ff_stolen { puts "FACE_FENCE took $c pin registers out of the kit region $gn (pin registers sit at their face)" }
puts "FACE_FENCE fenced $ot_ff_n flops; pin bits reg [dict get $ot_ff_cls reg] multi [dict get $ot_ff_cls multi] macro [dict get $ot_ff_cls macro] unregistered [dict get $ot_ff_cls none]; face conflicts $ot_ff_conf; not-ok [llength $ot_ff_bad] (table $::env(RESULTS_DIR)/ot_face_fence.tsv)"
if {[llength $ot_ff_bad] && $ot_ff_strict} {
  error "FACE_FENCE: [llength $ot_ff_bad] boundary pin bits have no register of their own and are not in spec unregistered_ok ([lrange $ot_ff_bad 0 7] ...): add the register in the RTL (registers come from RTL, never from the flow), or list the port in unregistered_ok with a reason"
}
