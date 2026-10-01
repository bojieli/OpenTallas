# W18b: place the four hardened K-arb slices (ot_chip_v41x_karb_pslice macros) in their pseudo-channel windows,
# bottom edge on the die bottom (their PC pins face the PHY), window p at x = p * 265.584 um.  MACRO_PLACEMENT_TCL (replaces the macro placer).
set ot_block [ord::get_db_block]
set n 0
foreach inst [$ot_block getInsts] {
  if {[[$inst getMaster] getName] ne "ot_chip_v41x_karb_pslice"} continue
  regexp {g_s\\?\[(\d)\\?\]} [$inst getName] -> p
  place_inst -name [$inst getName] -location [list [expr {$p * 265.584}] 0] -orientation R0 -status FIRM
  incr n
}
puts "OT_HIER placed $n slices"
