# el1011-hbm-idx 2026-10-11 r6: macro floorplan of hgi_idx_topk_w8_hub (the 8-wide IDX.TOPK glue; heap tiles outside).
# Lane h owns a 311.04-um stripe (36 x 8.64 um; c = h % 4): lanes 0..3 face SOUTH (pin groups t0..t3 on the bottom edge),
# lanes 4..7 face NORTH (t4..t7 on the top edge), so each heap tile sits straight across its seam.  Each lane's reverse-
# buffer SRAM is centred in its stripe 103.7 um inside its pin edge (lane FIFO / run FIFO / seam flops between pins and
# SRAM); the central band between the two SRAM rows carries the front end, status tree, merge tree and result skid
# (command / scores on the west edge, results on the east edge).  Origins on the 8.64-um track/site common multiple.
set G 8.64
proc idx_of {name tag} { if {[regexp [format {%s\\?\[(\d+)\\?\]} $tag] $name -> i]} { return $i }; return -1 }
set block [ord::get_db_block]
set dh [ord::dbu_to_microns [[$block getDieArea] yMax]]
set yn [expr {floor(($dh - 12 * $G - 70.47) / $G) * $G}]
foreach inst [$block getInsts] {
  if {![string match "ot_sram_1r1w_1024x256*" [[$inst getMaster] getName]]} { continue }
  set n [$inst getName]
  set h [idx_of $n g_h]; set c [expr {$h % 4}]; set r [expr {$h / 4}]
  set x [expr {8 * $G + $c * 36 * $G}]; set y [expr {$r == 0 ? 12 * $G : $yn}]
  place_macro -macro_name $n -location [list $x $y] -orientation R0
}
