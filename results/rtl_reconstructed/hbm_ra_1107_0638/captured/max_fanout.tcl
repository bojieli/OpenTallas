# HBM DRV basis (gen_core_kit_hbm.py --max-fanout): fanout cap at every repair_design
set_max_fanout 8 [current_design]
puts "HBMCORES max_fanout 8"
# HBM-CONS-2/HCOL vK (11-06, rb_vB form): every repair_design repeats signal wires at 80 um.
if {[info commands ot_rd_orig_mw] eq ""} {
  rename repair_design ot_rd_orig_mw
  proc repair_design {args} { puts "OT_MAXWIRE 80"; return [uplevel 1 [list ot_rd_orig_mw -max_wire_length 80 {*}$args]] }
}
