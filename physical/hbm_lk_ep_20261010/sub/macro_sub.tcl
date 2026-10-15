# MACRO_PLACEMENT_TCL for ot_lkep_sub (el1011-hbm-coll 2026-10-11): the one retry macro (690 x 460, pins on its W / S / N
# edges) centred with a logic ring: x 86.4 (W ring: TX pin buffer + TX bank beside in_data / tx_data on the W edge),
# y 91.2 (S ring: seam pin flops + control beside the S-edge pins), N ring 92 um (RX pin buffer / out capture beside
# rx_data / out_data on the N edge x 345..490), E ring 87.6 um (RX / out relay path to the S face).  Origin on the
# 48 nm grid (tools/check_macro_track_alignment.py: R0 needs x, y = 0 mod 48 nm).
set n 0
foreach inst [[ord::get_db_block] getInsts] {
  if {[[$inst getMaster] getName] ne "ot_hbm_link_retry_pipeline"} continue
  place_macro -macro_name [$inst getName] -location {86.4 91.2} -orientation R0
  incr n
}
if {$n != 1} { error "ot_lkep_sub: expected 1 retry macro, found $n" }
puts "OT_LKEP_SUB macro placed at 86.4 91.2 R0"
