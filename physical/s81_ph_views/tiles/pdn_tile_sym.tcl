# CLAUDE S81-PH tiles (redesign pass 2026-10-06): PDN of the tiles placed both R0 and MY (dsfd_selt_q, dsfd_colt_lane).
# Same contract as pdn_view.tcl (M7 PG stripes 0.288 wide on a 10.8 pitch, die owns M8/M9) but with the M7 grid
# SYMMETRIC about the tile centre: VDD at x = 5.256 + k 10.8 and VSS at 10.656 + k 10.8 (2 x 5.256 + 0.288 = 10.8), on
# a tile width that is a multiple of 10.8, so an MY instance has VDD / VSS at the same x as an R0 one.  The die places
# both at x0 = 6.544 (mod 10.8): the tile stripes then sit on the die's VDD 1.0 / VSS 6.4 (mod 10.8) grid.  Pins of
# these tiles are on the W / E faces only (M4: y unchanged by MY).  SRAM macro grid as pdn_selector.tcl.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {5.256}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
# the line-memory / frame-FIFO SRAM macros (ot_sram_1r1w_256x256_m2_r2c2, PG pins on M4) get M5 straps over the
# macro connected down to their M4 PG pins and up to the M6 straps of the top grid (as the HBM-ABSTRACTS hfd_cmdproc view).
# ds-1010 2026-10-10: the grid covers EVERY ot_sram_* master instantiated (it named only ot_sram_1r1w_256x256_m2_r2c2, so
# the dsfd_selt_q2 FRPR line's six ot_sram_1r1w_128x256_m1_r2c2 macros got no strap: PSM-0069 VDD connectivity at
# 6_report after a full route, s81b-selt_q2-frprck2a-1dc5e37d5 / fill-6 frpr-sq12).  No SRAM master -> no macro grid.
set ot_sram_cells {}
foreach ot_m [[ord::get_db] getLibs] { foreach ot_c [$ot_m getMasters] {
  if {[$ot_c isBlock] && [string match ot_sram_* [$ot_c getName]]} { lappend ot_sram_cells [$ot_c getName] } } }
if {[llength $ot_sram_cells]} {
  puts "pdn_tile_sym: SRAM macro grid on [lsort -unique $ot_sram_cells]"
  define_pdn_grid -macro -cells [lsort -unique $ot_sram_cells] -halo {2 2 2 2} -voltage_domains {CORE} -name {sram}
  add_pdn_stripe -grid {sram} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
  add_pdn_connect -grid {sram} -layers {M4 M5}
  add_pdn_connect -grid {sram} -layers {M5 M6}
}
