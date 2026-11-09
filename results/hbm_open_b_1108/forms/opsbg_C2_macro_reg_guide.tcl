# HBM-HARD-6 C1 11-08 (opsb_group): bank guides (macro bbox +6.48/+6.0, the R2g/P2 form) + ONE hub region holding ALL
# remaining logic (registers AND combinational cells: the GP crossbar/decode/read network, IREG), two boxes at the E strip.
# Why: G1 guided only the hub REGISTERS into its box, so ~5.8k um2 of hub combinational logic was excluded from the box and
# spilled into the 4x4 macro array (top-level util 32.6%, GPL overflowed tiles 20-31%); R2g/P1b had no hub guide and the
# crossbar balled up at the E pins (local density 3.2) -> GPL-0307.  Excluded from the hub (left top-level, free): pure
# BUF/INV cells on a port net or touching a FIRM face flop (W-face rd outputs must not be dragged 700 um east).
# Sourced at PRE_GLOBAL_PLACE (end of face_flops.tcl); macro_reg_guide_release.tcl removes every ot_mrg_* region before DPL.
set ::ot_mrg_spec [concat {bk0 {{u_fcore.u_g.g_bank[0].} {u_fcore.u_g.b_q[0][}} 7.56 4.32 113.184 59.46} {bk1 {{u_fcore.u_g.g_bank[1].} {u_fcore.u_g.b_q[1][}} 114.12 4.32 219.744 59.46} {bk2 {{u_fcore.u_g.g_bank[2].} {u_fcore.u_g.b_q[2][}} 220.68 4.32 326.304 59.46} {bk3 {{u_fcore.u_g.g_bank[3].} {u_fcore.u_g.b_q[3][}} 327.24 4.32 432.864 59.46} {bk4 {{u_fcore.u_g.g_bank[4].} {u_fcore.u_g.b_q[4][}} 433.8 4.32 539.424 59.46} {bk5 {{u_fcore.u_g.g_bank[5].} {u_fcore.u_g.b_q[5][}} 540.36 4.32 645.984 59.46} {bk6 {{u_fcore.u_g.g_bank[6].} {u_fcore.u_g.b_q[6][}} 646.92 4.32 752.544 59.46} {bk7 {{u_fcore.u_g.g_bank[7].} {u_fcore.u_g.b_q[7][}} 540.36 173.82 645.984 228.96} {bk8 {{u_fcore.u_g.g_bank[8].} {u_fcore.u_g.b_q[8][}} 433.8 173.82 539.424 228.96} {bk9 {{u_fcore.u_g.g_bank[9].} {u_fcore.u_g.b_q[9][}} 327.24 173.82 432.864 228.96} {bk10 {{u_fcore.u_g.g_bank[10].} {u_fcore.u_g.b_q[10][}} 220.68 173.82 326.304 228.96} {bk11 {{u_fcore.u_g.g_bank[11].} {u_fcore.u_g.b_q[11][}} 114.12 173.82 219.744 228.96} {bk12 {{u_fcore.u_g.g_bank[12].} {u_fcore.u_g.b_q[12][}} 7.56 173.82 113.184 228.96} {bk13 {{u_fcore.u_g.g_bank[13].} {u_fcore.u_g.b_q[13][}} 7.56 117.612 113.184 173.364} {bk14 {{u_fcore.u_g.g_bank[14].} {u_fcore.u_g.b_q[14][}} 7.56 60.012 113.184 115.764} {bk15 {{u_fcore.u_g.g_bank[15].} {u_fcore.u_g.b_q[15][}} 114.12 88.764 219.744 144.516}]
set ::ot_mrg_hub {hub {{225.0 59.5 756.0 173.8} {646.0 173.8 756.0 228.96}}}
uplevel #0 {
set mrg_blk [ord::get_db_block]
set mrg_u [[ord::get_db_tech] getDbUnitsPerMicron]
set mrg_free {}
foreach i [$mrg_blk getInsts] {
  if {![[$i getMaster] isCore]} continue
  if {[$i getPlacementStatus] in {FIRM FIXED LOCKED COVER}} continue
  lappend mrg_free [string map {"\\" ""} [$i getName]] $i
}
proc mrg_fixed_in {boxes} {
  global mrg_blk mrg_u
  set a 0.0
  foreach fi [$mrg_blk getInsts] {
    if {[$fi getPlacementStatus] ni {FIRM FIXED LOCKED COVER}} continue
    set bb [$fi getBBox]
    foreach z $boxes {
      lassign $z zx0 zy0 zx1 zy1
      set ix0 [expr {max($zx0, double([$bb xMin])/$mrg_u)}]; set iy0 [expr {max($zy0, double([$bb yMin])/$mrg_u)}]
      set ix1 [expr {min($zx1, double([$bb xMax])/$mrg_u)}]; set iy1 [expr {min($zy1, double([$bb yMax])/$mrg_u)}]
      if {$ix1 > $ix0 && $iy1 > $iy0} { set a [expr {$a + ($ix1-$ix0)*($iy1-$iy0)}] }
    }
  }
  return $a
}
proc mrg_make {nm boxes insts} {
  global mrg_blk mrg_u
  set area 0.0
  foreach i $insts { set area [expr {$area + double([[$i getMaster] getWidth]) * [[$i getMaster] getHeight] / $mrg_u / $mrg_u}] }
  set barea 0.0
  foreach z $boxes { lassign $z zx0 zy0 zx1 zy1; set barea [expr {$barea + ($zx1-$zx0)*($zy1-$zy0)}] }
  set fixed [mrg_fixed_in $boxes]
  set fill [expr {($area + $fixed) / $barea}]
  if {$fill >= 0.80} { error "OT_MACRO_REG_GUIDE_CAPACITY $nm: movable+fixed fill $fill >= 0.80" }
  set reg [odb::dbRegion_create $mrg_blk "ot_mrg_$nm"]
  $reg setRegionType INCLUSIVE
  foreach z $boxes {
    lassign $z zx0 zy0 zx1 zy1
    odb::dbBox_create $reg [expr {round($zx0*$mrg_u)}] [expr {round($zy0*$mrg_u)}] [expr {round($zx1*$mrg_u)}] [expr {round($zy1*$mrg_u)}]
  }
  set g [odb::dbGroup_create $reg "ot_mrg_$nm"]
  $g setType VOLTAGE_DOMAIN
  foreach i $insts { $g addInst $i }
  puts [format "OT_MACRO_REG_GUIDE %s cells %d area %.1f um2 boxes {%s} box_area %.0f fixed %.0f fill %.3f free_density %.3f" \
        $nm [llength $insts] $area $boxes $barea $fixed $fill [expr {$area / max(1.0, $barea - $fixed)}]]
}
set mrg_taken [dict create]
set mrg_n 0; set mrg_cells 0
foreach {mrg_nm mrg_pf zx0 zy0 zx1 zy1} $ot_mrg_spec {
  set insts {}
  foreach {nm i} $mrg_free {
    foreach pf $mrg_pf {
      if {[string equal -length [string length $pf] $nm $pf]} { lappend insts $i; dict set mrg_taken $nm 1; break }
    }
  }
  if {[llength $insts] == 0} { error "OT_MACRO_REG_GUIDE $mrg_nm: no instance under $mrg_pf" }
  mrg_make $mrg_nm [list [list $zx0 $zy0 $zx1 $zy1]] $insts
  incr mrg_n; incr mrg_cells [llength $insts]
}
# hub = every remaining free core cell except face-chain BUF/INV (port net, or a net shared with a FIRM face flop)
set hub {}; set mrg_face 0
foreach {nm i} $mrg_free {
  if {[dict exists $mrg_taken $nm]} continue
  set mn [[$i getMaster] getName]
  if {[regexp {^(INV|BUF|HB)} $mn]} {
    set face 0
    foreach it [$i getITerms] {
      set n [$it getNet]
      if {$n eq "NULL" || [$n getSigType] ne "SIGNAL"} continue
      if {[llength [$n getBTerms]] > 0} { set face 1; break }
      foreach o [$n getITerms] {
        set oi [$o getInst]
        if {$oi ne $i && [$oi getPlacementStatus] eq "FIRM"} { set face 1; break }
      }
      if {$face} break
    }
    if {$face} { incr mrg_face; continue }
  }
  lappend hub $i
}
lassign $ot_mrg_hub hub_nm hub_boxes
mrg_make $hub_nm $hub_boxes $hub
incr mrg_n; incr mrg_cells [llength $hub]
puts "OT_MACRO_REG_GUIDE $mrg_n guides $mrg_cells cells; $mrg_face face-chain BUF/INV left free (GPL guide, released before DPL)"
}
