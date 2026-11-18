# SERDES-H-FORM corridor correction (S81-SERDES-GEN 11-17): H_correct_corridor_r2.tcl of the H17 hand kit as a generated step, run at
# PRE_DETAIL_PLACE (the hand step ran on 3_4_place_resized.odb and DPL was resumed after it).  BOOT0 is aligned to the FIRM authority
# anchor and every exclusive BUF/INV leg of the boot/authority reset trees is spread on macro-free sites within the 405 um hop budget
# (serdes_boot_transport_local.tcl: fail closed).  The anchor is added to ot_reset_pair_fixed.txt so reset-pair legalisation keeps it.
set ot_sc_save_boot [expr {[info exists ::env(OT_SERDES_BOOT_RELEASE_LOCAL)] ? $::env(OT_SERDES_BOOT_RELEASE_LOCAL) : ""}]
set ::env(OT_SERDES_BOOT_RELEASE_LOCAL) 0
source /work/serdes_boot_release_local.tcl
set ::env(OT_SERDES_AUTH_INPUT_LOCAL) 0
source /work/authority_input_local.tcl
source /work/serdes_boot_transport_local.tcl
set ot_sc_p $::env(RESULTS_DIR)/ot_reset_pair_fixed.txt;set ot_sc_names {}
if {[file exists $ot_sc_p]} {set ot_sc_f [open $ot_sc_p];set ot_sc_names [split [read $ot_sc_f] "\n"];close $ot_sc_f}
if {[lsearch -exact $ot_sc_names $::hboot_anchor_name]<0} {set ot_sc_f [open $ot_sc_p a];puts $ot_sc_f $::hboot_anchor_name;close $ot_sc_f}
set ::env(OT_SERDES_BOOT_RELEASE_LOCAL) $ot_sc_save_boot
puts "SERDES_CORRIDOR done anchor $::hboot_anchor_name"
