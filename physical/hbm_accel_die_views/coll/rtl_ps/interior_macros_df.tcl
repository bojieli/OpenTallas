# POST_MACRO_PLACE (el1011-hbm-coll 2026-10-11, route_ps.sh INTERIOR=2): DATAFLOW-ORDERED interior floorplan.
# Why: interior_macros.tcl stacked the six 3-macro rows in lsort order of the instance names (bottom -> top: qp, qr,
# rb0, rb1, wrx, wtx), so the RX bus ran from the bottom ph_rx pins up to the wrx row (~350 um) and back down to rb,
# and the TX bus from the qp/qr rows (bottom) up to the wtx row (~280 um) and over to the right face.  Route
# hcoll-port-rbsel-7dba707a7-a: GRT wirelength 2.04 m, 447 slew violations after GRT repair, 226 left after DRT
# (76 port buffers, ~60 u_wtx / u_rb / u_wrx wire buffers, 9 u_rb wd_in, pin-flop D pins).
# Here every 545-bit hop is one row pitch (65 um) vertically, rows in dataflow order (bottom -> top):
#   r0 u_wrx  (just above the bottom ph_rx pins)      r3 u_wtx  (tx wire line; feeds u_txq -> ph_tx pins, right)
#   r1 u_rb bank 0 (rb_d pins on the right beside)    r4 u_qp   (qp pins on the left beside)
#   r2 u_rb bank 1                                     r5 u_qr   (qr pins on the left beside)
# Inside a row g_m[0] (bits 0..255) is the RIGHTMOST macro and g_m[2] (bits 512..544) the leftmost, in every row, so a
# bit's macro sits in the same column in every row (row-to-row hops are vertical) and the 256-bit slice is the one
# nearest the right face, where both outputs (rb_d, ph_tx_flit) leave.  Same 24 um channels and >= 48 um pin corridors
# as interior_macros.tcl; the matching pin plan is interior_pins_df.tcl.
set block [ord::get_db_block]
set units [$block getDbUnitsPerMicron]
set macros {}
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getType] eq "BLOCK"} { lappend macros [$inst getName] }
}
if {[llength $macros] != 18} { error "hcoll interior_df requires exactly 18 SRAMs; found [llength $macros]" }
set die [$block getDieArea]
set dw [expr {double([$die dx])/$units}]
set dh [expr {double([$die dy])/$units}]
set mw 94.824
set mh 41.040
# textbook audit 10-11 (class 6: 31% util at 480x540): compact outlines (< 460 um wide) use 20 um channels
set gap [expr {[info exists ::env(OT_HCOLL_GAP)] ? double($::env(OT_HCOLL_GAP)) : ($dw < 460.0 ? 20.0 : 24.0)}]
# M4 pin access (tools/check_macro_track_alignment.py: this SRAM in R0 needs origin y = 0 mod 48 nm; its M4 pin
# centres sit at 12 mod 48 nm, on the M4 tracks only then).  Tiles g/g3/g4a-c used gap 20 and y0 19.88:
# every row off track -> DRT-0419 on all pins and DRT-0255 on the dense (every-track) right-edge wd_in/w_mask_in
# pins.  Snap the row gap and y0 to the 48 nm grid (gap 24 / y0 86.88 of df-a were already on it).
set gap [expr {round($gap/0.048)*0.048}]
# column channel (x) can differ from the row channel: INTERIOR=4 tiles g / g3 died in DRT-0255 (u_wtx/rd[542] pin access at
# the col1|col2 channel: one macro's 119 right-edge wd_in + the next one's 256 rd_out + 137 wd_in pins and the capture flops
# in 20 um) -> OT_HCOLL_GAPX (env) or ::ot_hcoll_gapx (hook wrapper) widens only the column channels
set gapx [expr {[info exists ::env(OT_HCOLL_GAPX)] ? double($::env(OT_HCOLL_GAPX)) : ([info exists ::ot_hcoll_gapx] ? $::ot_hcoll_gapx : $gap)}]
set array_w [expr {3*$mw+2*$gapx}]
set array_h [expr {6*$mh+5*$gap}]
set x0 [expr {($dw-$array_w)/2}]
# INTERIOR=4 die tile (10-11, g2ck-r2 GPL-0305 / routability 1.13 top-2%): the LEFT (core) face carries 1,640 pins + their
# FIRM pin flops, the right (link) face 1,092 -> a 20 um link corridor and every other um on the core side (384 wide: 40 um)
if {[info exists ::ot_hcoll_m0_left]} { set x0 [expr {$dw - 20.0 - $array_w}] }
set y0 [expr {floor(($dh-$array_h)/2/0.048)*0.048}]
# compact slice (< 400 um wide, the hierarchical hfd_coll tile: 364 x 386 = ~57% util): 20 um pin corridors suffice for
# one face of pin flops (qp/qr 1,092 flops on the 364 um top face = 4 rows of DFFs)
set cmin [expr {$dw < 460.0 ? 18.0 : 48.0}]
if {$x0 < $cmin || $y0 < $cmin} { error "hcoll interior_df outline too small for ${cmin}um pin corridors" }
set seen 0
foreach name $macros {
    # odb names keep the escaped identifier, e.g. u_rb/g_bk\[1\].u_m.g_m\[2\].u_sram
    set row -1
    if {[regexp {^u_wrx/} $name]} { set row 0 }
    if {[regexp {^u_rb/g_bk\\?\[([01])\\?\]} $name -> bk]} { set row [expr {1 + $bk}] }
    if {[regexp {^u_wtx/} $name]} { set row 3 }
    if {[regexp {^u_qp/} $name]} { set row 4 }
    if {[regexp {^u_qr/} $name]} { set row 5 }
    if {![regexp {g_m\\?\[([0-2])\\?\]} $name -> m]} { error "hcoll interior_df: no g_m index in $name" }
    if {$row < 0} { error "hcoll interior_df: unknown macro $name" }
    set inst [$block findInst $name]
    set master [$inst getMaster]
    if {abs(double([$master getWidth])/$units-$mw)>0.01 || abs(double([$master getHeight])/$units-$mh)>0.01} {
        error "hcoll unexpected macro dimensions for $name"
    }
    # INTERIOR=4 (die tile, interior_macros_df4.tcl sets ot_hcoll_m0_left): core-side pins on the LEFT face, so g_m[0] leftmost
    set col [expr {[info exists ::ot_hcoll_m0_left] ? $m : 2 - $m}]
    set x [expr {$x0+$col*($mw+$gapx)}]
    set y [expr {$y0+$row*($mh+$gap)}]
    set ydbu [expr {int(round($y*$units))}]
    if {$ydbu % int(round(0.048*$units)) != 0} { error "hcoll interior_df: $name origin y $y off the 48 nm M4 grid" }
    $inst setPlacementStatus PLACED
    $inst setOrient R0
    $inst setLocation [expr {int(round($x*$units))}] [expr {int(round($y*$units))}]
    $inst setPlacementStatus FIRM
    puts "HCOLL_INTERIOR_DF $name row=$row col=$col $x $y R0"
    incr seen
}
if {$seen != 18} { error "hcoll interior_df placed $seen of 18" }
