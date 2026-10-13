# T_AQ (ot_dsrom_aq12t) variant a: deliberate SRAM placement (macro k = lanes 8k..8k+7; pins on the L/R M4 faces,
# >= 25 um channels to each other and to the core edge).  el1011-ds-misc/pqc 2026-10-11.
set loc {{25.92 97.2} {25.92 34.56} {159.84 97.2} {159.84 34.56}}
set b [ord::get_db_block]
set count 0
foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {
    if {![regexp {g_m\D*(\d+)} [$i getName] -> k]} { error "aq12t_place: unexpected macro [$i getName]" }
    place_macro -macro_name [$i getName] -location [lindex $loc $k] -orientation R0
    incr count
  }
}
if {$count != 4} { error "aq12t_place requires exactly four SRAMs: $count" }
