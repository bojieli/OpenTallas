# HBM DRV basis (gen_core_kit_hbm.py --max-fanout): fanout cap at every repair_design
set_max_fanout 16 [current_design]  ;# DIE-HBM-89 lanec_vM2: 64 -> 16 (vM1 slew: BUFx3/x6f place buffers driving 26-54 loads over 30-55 um)
puts "HBMCORES max_fanout 16"
# HBM-FORM-TIMING maxwire (11-05, lcmw = hnx_fused_lane_c RE-FORM after lanecde/lanecde2): every repair_design in this kit
# (3_4 + GRT) repeats signal wires at 80 um. Measured on lanecde i2: 79 slew nets, fanout <=2, 90-170 um, SRAM / INVx1 drivers -> faces.
if {[info commands ot_rd_orig_mw] eq ""} {
  rename repair_design ot_rd_orig_mw
  proc repair_design {args} { puts "OT_MAXWIRE 80"; return [uplevel 1 [list ot_rd_orig_mw -max_wire_length 80 {*}$args]] }
}
