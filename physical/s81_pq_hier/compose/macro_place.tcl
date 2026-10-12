# ot_v41_pqc_spine_screen v15 HIER composition (R 16), el1011-ds-misc/pqc 2026-10-11: deliberate tile placement,
# computed from the tile views' sizes (whichever variant is adopted).  Data flow (physical spec, el1011-ds-misc.log):
#   N edge: T_XIN0/1 (the x_q pin registers) over their halves; band 2: T_AQ0 | T_AQ1; band 3: T_IX0 T_IX2 | T_IX1
#     T_IX3 next to the die centre.  x_q[0:1023] (words 0-31) feeds T_AQ0, T_IX0, T_IX2 (left half), x_q[1024:2047]
#     T_AQ1, T_IX1, T_IX3 (right half): each T_XIN output is <= ~300 um from its three consumers;
#   middle band, centred under the T_IX block: T_CTL | T_QB | T_BC0..3 -> o_bus pins (E face).  T_QB takes aq_q from
#     both T_AQ bottoms (<= ~470 um Manhattan), T_BC0 takes bt_d (T_IX, <= ~250 um), hq (T_QB), bc_hr (T_CTL);
#   bottom band: T_RET0/1 centred on the region-root pins (S face: r_* / o_w_*), mdr from T_CTL (<= ~250 um); the ROM
#     stand-ins SW by the rw_* pins (W face), <= ~350 um from T_CTL's ROM ports.
# Channels >= 25 um between tiles and to the core edge; x on 0.432, y on 2.16 (the tiles' M4 / M5 pins stay on grid).
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set die [$b getDieArea]
set W [expr {double([$die xMax]) / $dbu}]
set H [expr {double([$die yMax]) / $dbu}]
set G 25.0
set E 25.0
proc snapx {v} { return [expr {round($v / 0.432) * 0.432}] }
proc snapy {v} { return [expr {round($v / 2.16) * 2.16}] }
array set inst {}
foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} { continue }
  set n [$i getName]
  set m [[$i getMaster] getName]
  set k 0
  if {[regexp {g_(?:aq|ix|ret|bc)\\?\[(\d+)\\?\]} $n -> k]} {}
  if {[regexp {u_prom1} $n]} { set k 1 }
  if {[regexp {u_obus} $n]} { set k 4 }
  if {[regexp {u_xin(\d)} $n -> xk]} { set k $xk }
  set inst($m,$k) $i
}
proc dim {i} {
  global dbu
  set mm [$i getMaster]
  return [list [expr {double([$mm getWidth]) / $dbu}] [expr {double([$mm getHeight]) / $dbu}]]
}
proc put {i x y} {
  place_macro -macro_name [$i getName] -location [list [snapx $x] [snapy $y]] -orientation R0 -exact
}
foreach need {ot_dsrom_aq12t,0 ot_dsrom_aq12t,1 ot_pqc_t_ix,0 ot_pqc_t_ix,1 ot_pqc_t_ix,2 ot_pqc_t_ix,3 ot_pqc_t_qb,0
              ot_pqc_t_ctl16,0 ot_pqc_t_ret,0 ot_pqc_t_ret,1 ot_pqc_t_bc,0 ot_pqc_t_bc,1 ot_pqc_t_bc,2 ot_pqc_t_bc,3
              ot_pqc_t_srom,0 ot_pqc_t_prom,0 ot_pqc_t_prom,1 ot_pqc_t_bc,4 ot_pqc_t_xin,0 ot_pqc_t_xin,1} {
  if {![info exists inst($need)]} { error "pqc macro_place: no tile $need" }
}
# x_q pin-register tiles at the N edge (no top-level soft flops), each over its half
lassign [dim $inst(ot_pqc_t_xin,0)] xw xh
set ybase [expr {$H - $E - $xh}]
# band 2: the quantisers side by side (x_q[0:1023] -> T_AQ0 left, x_q[1024:2047] -> T_AQ1 right)
lassign [dim $inst(ot_dsrom_aq12t,0)] aw ah
set ya [expr {$ybase - $G - $ah}]
put $inst(ot_dsrom_aq12t,0) $E $ya
put $inst(ot_dsrom_aq12t,1) [expr {$E + $aw + $G}] $ya
if {$E + 2 * $aw + 2 * $G > $W + 0.01} { error "pqc macro_place: quantiser band needs [expr {$E + 2 * $aw + 2 * $G}] um > die $W" }
set c0 [expr {$E + $aw / 2.0}]
set c1 [expr {$E + $aw + $G + $aw / 2.0}]
put $inst(ot_pqc_t_xin,0) [expr {$c0 - $xw / 2.0}] $ybase
put $inst(ot_pqc_t_xin,1) [expr {$c1 - $xw / 2.0}] $ybase
# band 3: the BF16 x-buffer tiles, IX0 IX2 under T_AQ0 (words 0-31), IX1 IX3 under T_AQ1 (words 32-63), each pair
# centred on its half and pulled to the die centre (their bt_d lanes go to T_BC0 under the middle)
lassign [dim $inst(ot_pqc_t_ix,0)] iw ih
set yi [expr {$ya - $G - $ih}]
put $inst(ot_pqc_t_ix,0) [expr {$c0 + $aw / 2.0 - 2 * $iw - $G}] $yi
put $inst(ot_pqc_t_ix,2) [expr {$c0 + $aw / 2.0 - $iw}] $yi
put $inst(ot_pqc_t_ix,1) [expr {$c1 - $aw / 2.0}] $yi
put $inst(ot_pqc_t_ix,3) [expr {$c1 - $aw / 2.0 + $iw + $G}] $yi
set ytop $yi
# middle band, centred on the die
lassign [dim $inst(ot_pqc_t_qb,0)] qw qh
set qx [expr {$W / 2.0 - $qw / 2.0}]
put $inst(ot_pqc_t_qb,0) $qx [expr {$ytop - $G - $qh}]
lassign [dim $inst(ot_pqc_t_ctl16,0)] cw ch
set cx [expr {$qx - $G - $cw}]
put $inst(ot_pqc_t_ctl16,0) $cx [expr {$ytop - $G - $ch}]
set x [expr {$qx + $qw + $G}]
set bhm 0
foreach k {0 1 2 3} {
  lassign [dim $inst(ot_pqc_t_bc,$k)] bw bh
  put $inst(ot_pqc_t_bc,$k) $x [expr {$ytop - $G - $bh}]
  set x [expr {$x + $bw + 20.0}]
  set bhm [expr {max($bhm, $bh)}]
}
lassign [dim $inst(ot_pqc_t_bc,4)] bw bh
if {$x + $bw + $E > $W - $E + 0.01} { error "pqc macro_place: relay row runs past the E edge" }
# the screen's o_bus register (fifth relay) at the E edge, by the o_bus pins
put $inst(ot_pqc_t_bc,4) [expr {$W - $E - $bw}] [expr {$ytop - $G - $bh}]
# bottom band
lassign [dim $inst(ot_pqc_t_ret,0)] rw rh
set rx [expr {$W / 2.0 - $rw - $G / 2.0}]
put $inst(ot_pqc_t_ret,0) $rx $E
put $inst(ot_pqc_t_ret,1) [expr {$rx + $rw + $G}] $E
lassign [dim $inst(ot_pqc_t_srom,0)] sw sh
put $inst(ot_pqc_t_srom,0) $E $E
lassign [dim $inst(ot_pqc_t_prom,0)] pw ph
put $inst(ot_pqc_t_prom,0) [expr {$E + $sw + $G}] $E
put $inst(ot_pqc_t_prom,1) [expr {$E + $sw + $G}] [expr {$E + $ph + $G}]
if {$E + $sw + $G + $pw + $G > $rx + 0.01} { error "pqc macro_place: ROM tiles run into T_RET0" }
set lowtop [expr {max($E + $rh, $E + 2 * $ph + $G, $E + $sh)}]
set midbot [expr {$ytop - $G - max($qh, $ch, $bhm)}]
if {$lowtop + $G > $midbot + 0.01} { error "pqc macro_place: bands overlap (die H $H too small)" }
puts "pqc macro_place: 20 tiles placed (die $W x $H, top band y >= $ytop)"
