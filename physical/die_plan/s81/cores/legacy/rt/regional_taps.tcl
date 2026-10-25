# COPY for gen_core_kit_legacy.py regional_taps (KITS-SPARE/S81C 10-25) of physical/die_plan/s81/cores/split_clock/regional_taps.tcl
# @ codex/s81-physical-0719 6e336af2ba (S81-CORES/SPLIT + Codex planned-spine protection / guard).
# S81-CORES/SPLIT structured regional clock taps (PRE_CTS hook), owner clock rule 10-23 / decision 5 / COORD F3+F5.
# Replaces the single 24-30k-sink TritonCTS tree from the face-middle clk pin (7 H-levels + an 85 ps unbuffered root
# run to the sink centroid + 100-120 ps leaf runs over the SRAM, I 345-480 ps RCX) with:
#   clk port -> buffered trunk (<= OT_RT_REP_UM between repeaters) -> symmetric binary H-tree (equal Manhattan length per
#   level by construction) -> one regional tap per NX x NY region (geometric region centre, moved off macros);
#   one macro skew group per SRAM: its clk pin + its interface registers (wd/addr/ctl launch regs, rd capture regs, through
#   <= 1 buffer/inverter) on their own tap at the macro clk pin, hung from the H-tree leaf node of its region.
# TritonCTS then builds one local tree per tap net (it treats the pre-placed spine buffers as tree boundaries) and the
# POST_CTS hook (regional_taps_balance.tcl) pads early taps so every tap mean sits within OT_RT_WIN_PS (20) of the latest.
# env: OT_RT_NX OT_RT_NY (powers of 2), OT_RT_BUF (BUFx24_ASAP7_75t_R), OT_RT_REP_UM (60), OT_RT_PORT (clk)
uplevel #0 {
set rt_blk [ord::get_db_block]
set rt_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rt_nx [expr {[info exists ::env(OT_RT_NX)] ? $::env(OT_RT_NX) : 4}]
set rt_ny [expr {[info exists ::env(OT_RT_NY)] ? $::env(OT_RT_NY) : 2}]
set rt_bufm [[ord::get_db] findMaster [expr {[info exists ::env(OT_RT_BUF)] ? $::env(OT_RT_BUF) : "BUFx24_ASAP7_75t_R"}]]
set rt_rep [expr {[info exists ::env(OT_RT_REP_UM)] ? $::env(OT_RT_REP_UM) : ([info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE) ? 60.0 : 250.0)}]
set rt_portn [expr {[info exists ::env(OT_RT_PORT)] ? $::env(OT_RT_PORT) : "clk"}]
set rt_bt [$rt_blk findBTerm $rt_portn]
if {$rt_bt eq "NULL"} { error "OT_RT: no clock port $rt_portn" }
set rt_root [$rt_bt getNet]
set core [$rt_blk getCoreArea]
set cx0 [expr {[$core xMin]/double($rt_dbu)}]; set cy0 [expr {[$core yMin]/double($rt_dbu)}]
set cx1 [expr {[$core xMax]/double($rt_dbu)}]; set cy1 [expr {[$core yMax]/double($rt_dbu)}]
proc rt_ctr {i} { global rt_dbu; set b [$i getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2.0/$rt_dbu}] [expr {([$b yMin]+[$b yMax])/2.0/$rt_dbu}]] }
proc rt_is_macro {i} { return [expr {[[$i getMaster] getType] eq "BLOCK"}] }
proc rt_is_seq {i} { return [[$i getMaster] isSequential] }
proc rt_is_buf {i} { set m [[$i getMaster] getName]; return [expr {[string match BUF* $m] || [string match INV* $m] || [string match HB* $m]}] }
proc rt_out {i} { foreach t [$i getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT" && [$t getNet] ne "NULL"} { return [$t getNet] } }; return "NULL" }
set rt_n 0
proc rt_buf {tag x y in} {
  global rt_blk rt_bufm rt_dbu rt_n
  incr rt_n
  set inst [odb::dbInst_create $rt_blk $rt_bufm "ot_rt_${tag}"]
  set out [odb::dbNet_create $rt_blk "ot_rt_${tag}_n"]
  $out setSigType CLOCK
  foreach t [$inst getITerms] {
    set mt [$t getMTerm]
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $t connect $in } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $out }
  }
  # Keep all planned repeaters out of macro halos. The clock wire may cross a
  # macro on its granted layers; a standard cell cannot occupy that macro.
  if {[info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE)} {
    set halo 4.32
    set w [expr {[$rt_bufm getWidth]/double($rt_dbu)}]
    set h [expr {[$rt_bufm getHeight]/double($rt_dbu)}]
    set core [$rt_blk getCoreArea]
    set x [expr {min(max($x,[$core xMin]/double($rt_dbu)+$w),[$core xMax]/double($rt_dbu)-$w)}]
    set y [expr {min(max($y,[$core yMin]/double($rt_dbu)+$h),[$core yMax]/double($rt_dbu)-$h)}]
    set boxes {}
    foreach m [$rt_blk getInsts] {
      if {[[$m getMaster] getType] ne "BLOCK"} continue
      set b [$m getBBox]
      lappend boxes [list [expr {[$b xMin]/double($rt_dbu)-$halo-$w}] [expr {[$b xMax]/double($rt_dbu)+$halo+$w}] [expr {[$b yMin]/double($rt_dbu)-$halo-$h}] [expr {[$b yMax]/double($rt_dbu)+$halo+$h}]]
    }
    for {set pass 0} {$pass < 16} {incr pass} {
      set blocked 0
      foreach b $boxes {
        lassign $b x0 x1 y0 y1
        if {$x <= $x0 || $x >= $x1 || $y <= $y0 || $y >= $y1} continue
        set opts [list [list [expr {$x-$x0}] $x0 $y] [list [expr {$x1-$x}] $x1 $y] [list [expr {$y-$y0}] $x $y0] [list [expr {$y1-$y}] $x $y1]]
        set found 0
        foreach opt [lsort -real -index 0 $opts] {
          lassign $opt d xx yy
          if {$xx-$w < [$core xMin]/double($rt_dbu) || $xx+$w > [$core xMax]/double($rt_dbu) || $yy < [$core yMin]/double($rt_dbu) || $yy+$h > [$core yMax]/double($rt_dbu)} continue
          set legal 1
          foreach bb $boxes { lassign $bb a b c d; if {$xx>$a && $xx<$b && $yy>$c && $yy<$d} { set legal 0; break } }
          if {$legal} {set x $xx;set y $yy;set found 1;break}
        }
        if {!$found} { error "OT_RT no legal repeater site for $tag" }
        set blocked 1;break
      }
      if {!$blocked} break
    }
  }
  $inst setLocation [expr {round(($x - 1.0) * $rt_dbu)}] [expr {round($y * $rt_dbu)}]
  $inst setPlacementStatus PLACED
  return $out
}
# repeated straight (L) run from (x0,y0) on net n to (x1,y1): returns the net at the end
proc rt_run {tag x0 y0 x1 y1 n} {
  global rt_rep
  set L [expr {abs($x1-$x0) + abs($y1-$y0)}]
  set k [expr {int(ceil($L / $rt_rep)) - 1}]
  for {set j 1} {$j <= $k} {incr j} {
    set f [expr {double($j) / ($k + 1)}]
    # x first, then y (L shape), position at fraction f of the length
    set d [expr {$f * $L}]
    if {$d <= abs($x1-$x0)} { set x [expr {$x0 + ($x1>$x0?1:-1)*$d}]; set y $y0 } else { set x $x1; set y [expr {$y0 + ($y1>$y0?1:-1)*($d-abs($x1-$x0))}] }
    set n [rt_buf "${tag}_r$j" $x $y $n]
  }
  return $n
}
# ---- sinks on the root net
set regs {}; set macs {}; set other 0
foreach it [$rt_root getITerms] {
  if {[[$it getMTerm] getIoType] ne "INPUT"} continue
  set i [$it getInst]
  if {[rt_is_macro $i]} { lappend macs $it } elseif {[rt_is_seq $i]} { lappend regs $it } else { incr other }
}
puts "OT_RT sinks: [llength $regs] registers, [llength $macs] macro clock pins, $other other (kept on the root)"
# ---- macro skew groups (F3): interface registers through <= 1 buffer/inverter
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
dict for {m g} $grp { foreach r $g { dict set ingrp $r $m } ; puts "OT_RT macro group $m: [llength $g] interface registers" }
# ---- regions + H-tree
# OT_RT_SPLIT=count (S81-CORES3/SW 10-25, GEOM-REVIEW-3 05:47 vn_a/vn_b: regions cut to equal sink count instead of
# padding the light taps): every binary cut goes at the median coordinate of the non-macro-group registers inside the
# node's box (clamped to the middle half of the span, no sliver regions); tap buffer at the child box centre as before.
# The spine arms are then unequal by construction; regional_taps_balance.tcl brings the taps inside OT_RT_WIN_PS.
# Default (geom) = geometric halves, unchanged.
set rt_split [expr {[info exists ::env(OT_RT_SPLIT)] ? $::env(OT_RT_SPLIT) : "geom"}]
set rt_pts {}
foreach it $regs { if {[dict exists $ingrp [[$it getInst] getName]]} continue; lappend rt_pts [rt_ctr [$it getInst]] }
proc rt_cut {a b c d byx} {
  global rt_pts rt_split
  set lo [expr {$byx ? $a : $c}]; set hi [expr {$byx ? $b : $d}]
  set g [expr {($lo + $hi) / 2.0}]
  if {$rt_split ne "count"} { return $g }
  set v {}
  foreach p $rt_pts { lassign $p x y; if {$x >= $a && $x <= $b && $y >= $c && $y <= $d} { lappend v [expr {$byx ? $x : $y}] } }
  if {[llength $v] < 2} { return $g }
  set v [lsort -real $v]; set m [lindex $v [expr {[llength $v] / 2}]]
  set q [expr {($hi - $lo) / 4.0}]
  return [expr {min(max($m, $lo + $q), $hi - $q)}]
}
set W [expr {$cx1-$cx0}]; set H [expr {$cy1-$cy0}]
set rw [expr {$W/$rt_nx}]; set rh [expr {$H/$rt_ny}]
# port -> centre trunk
set pb [$rt_bt getBBox]
set px [expr {([$pb xMin]+[$pb xMax])/2.0/$rt_dbu}]; set py [expr {([$pb yMin]+[$pb yMax])/2.0/$rt_dbu}]
set CX [expr {$cx0 + $W/2.0}]; set CY [expr {$cy0 + $H/2.0}]
# the trunk drives from the port; all register / macro sinks are moved off the root
set n0 [rt_buf trunk0 [expr {max($px, $cx0+1.0)}] [expr {min(max($py,$cy0+1.0),$cy1-2.0)}] $rt_root]
set nC [rt_run trunk [expr {max($px, $cx0+1.0)}] $py $CX $CY $n0]
# recursive binary split: x first while columns > 1 then y; node list {x y net x0 x1 y0 y1}
set nodes [list [list $CX $CY $nC $cx0 $cx1 $cy0 $cy1]]
set lvl 0; set cols $rt_nx; set rows $rt_ny
while {$cols > 1 || $rows > 1} {
  set nn {}
  incr lvl
  set byx [expr {$cols >= $rows && $cols > 1}]
  foreach nd $nodes {
    lassign $nd x y n a b c d
    if {$byx} {
      set m [rt_cut $a $b $c $d 1]
      foreach {xa xb} [list $a $m $m $b] { set xc [expr {($xa+$xb)/2.0}]
        set e [rt_run "h${lvl}_[llength $nn]" $x $y $xc $y $n]
        lappend nn [list $xc $y [rt_buf "h${lvl}_[llength $nn]" $xc $y $e] $xa $xb $c $d $e] }
    } else {
      set m [rt_cut $a $b $c $d 0]
      foreach {ya yb} [list $c $m $m $d] { set yc [expr {($ya+$yb)/2.0}]
        set e [rt_run "h${lvl}_[llength $nn]" $x $y $x $yc $n]
        lappend nn [list $x $yc [rt_buf "h${lvl}_[llength $nn]" $x $yc $e] $a $b $ya $yb $e] }
    }
  }
  if {$byx} { set cols [expr {$cols/2}] } else { set rows [expr {$rows/2}] }
  set nodes $nn
}
puts "OT_RT H-tree ($rt_split split): $lvl levels, [llength $nodes] leaf nodes (taps), region [format %.1f $rw] x [format %.1f $rh] um, $rt_n spine buffers"
# taps: the leaf node buffer output net is the regional tap net
set k 0; set tapnet {}
foreach nd $nodes { lassign $nd x y n a b c d; dict set tapnet $k $nd; incr k }
proc rt_region {x y} {
  global tapnet
  dict for {k nd} $tapnet { lassign $nd nx ny n a b c d; if {$x >= $a-0.01 && $x <= $b+0.01 && $y >= $c-0.01 && $y <= $d+0.01} { return $k } }
  return 0
}
# macro taps hang off their region's leaf node: buffer at the macro clk pin (outside the macro, W/E edge nearest the pin)
set mtap {}
foreach mit $macs {
  set m [$mit getInst]
  # KITS-SPARE/L5 10-25 (F3): a macro with two clock pins (ot_sram_1r1w2c: wclk + rclk) gets ONE macro tap; the second
  # pin joins the first pin's tap net, so both clock pins and the interface registers are one skew group.
  if {[dict exists $mtap [$m getName]]} { $mit disconnect; $mit connect [dict get $mtap [$m getName]]; puts "OT_RT macro tap [$m getName]: 2nd clock pin [[$mit getMTerm] getName] on the same tap"; continue }
  set pbx [$mit getBBox]
  set mx [expr {([$pbx xMin]+[$pbx xMax])/2.0/$rt_dbu}]; set my [expr {([$pbx yMin]+[$pbx yMax])/2.0/$rt_dbu}]
  set mb [$m getBBox]
  if {abs($mx - [$mb xMin]/double($rt_dbu)) < abs($mx - [$mb xMax]/double($rt_dbu))} { set bx [expr {[$mb xMin]/double($rt_dbu) - 6.0}] } else { set bx [expr {[$mb xMax]/double($rt_dbu) + 6.0}] }
  # OT_MPF_SIDE "X0 X1 L|R ..." (same variable as physical/common_flow/macro_pin_flops.tcl): the macro tap sits on the
  # edge where its interface registers were anchored (pins with shapes on both edges otherwise default to xMax).
  if {[info exists ::env(OT_MPF_SIDE)]} { foreach {x0 x1 s} $::env(OT_MPF_SIDE) { set mlx [expr {[$mb xMin]/double($rt_dbu)}]
    if {$mlx >= $x0 && $mlx < $x1 && $s in {L R}} { set bx [expr {$s eq "L" ? $mlx - 6.0 : [$mb xMax]/double($rt_dbu) + 6.0}]; break } } }
  set r [rt_region $bx $my]
  # sibling of the region's leaf tap buffer (same stage count): hang from the leaf buffer's INPUT net
  lassign [dict get $tapnet $r] nx ny nn a b c d nin
  set e [rt_run "m[llength $mtap]" $nx $ny $bx $my $nin]
  set tn [rt_buf "mtap[dict size $mtap]" $bx $my $e]
  $mit disconnect; $mit connect $tn
  dict set mtap [$m getName] $tn
  puts "OT_RT macro tap [$m getName] at ([format %.1f $bx],[format %.1f $my]) from region $r node ([format %.1f $nx],[format %.1f $ny])"
}
set cnt {}
foreach it $regs {
  set i [$it getInst]; set nm [$i getName]
  if {[dict exists $ingrp $nm]} { set tn [dict get $mtap [dict get $ingrp $nm]] } else {
    lassign [rt_ctr $i] x y; set r [rt_region $x $y]; set tn [lindex [dict get $tapnet $r] 2]; dict incr cnt $r }
  $it disconnect; $it connect $tn
}
puts "OT_RT tap loads: $cnt; macro groups [dict size $mtap]"
# TritonCTS builds local trees ONLY on the tap nets (the spine is fixed, balanced by construction): -clk_nets
set tl {}; set ti {}
dict for {k nd} $tapnet { set n [lindex $nd 2]; lappend tl [$n getName]; lappend ti [[[$n getFirstOutput] getInst] getName] }
dict for {m n} $mtap { lappend tl [$n getName]; lappend ti [[[$n getFirstOutput] getInst] getName] }
set fh [open /work/ot_rt_taps.txt w]; puts $fh [join $ti "\n"]; close $fh
set ::env(CTS_ARGS) "$::env(CTS_ARGS) -clk_nets {$tl}"
puts "OT_RT CTS_ARGS $::env(CTS_ARGS)"

# Optional hardened clock spine: CTS may build local trees after a tap, but cannot
# add an asymmetric wire buffer on a planned trunk/arm. Save the exact input nets
# before CTS so the post-CTS gate detects tools that disregard dont_touch.
if {[info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE)} {
  # TritonCTS repairs ALL clock roots despite dont_touch; use selected -clk_nets
  # local trees and keep its global repair_clock_nets sweep off the planned spine.
  set ::env(CTS_ARGS) [string map {"-repair_clock_nets" ""} $::env(CTS_ARGS)]
  puts "OT_RT_PROTECT CTS_ARGS $::env(CTS_ARGS)"
  set rt_leafnets {}
  dict for {k nd} $tapnet { dict set rt_leafnets [[lindex $nd 2] getName] 1 }
  dict for {m n} $mtap { dict set rt_leafnets [$n getName] 1 }
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
  puts "OT_RT_PROTECT: planned spine protected; local tap nets remain CTS-enabled"
}

}
