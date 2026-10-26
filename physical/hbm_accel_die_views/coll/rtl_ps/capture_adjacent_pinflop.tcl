# PRE_GLOBAL_PLACE (idleA-hcoll 2026-10-10, route_ps.sh PINFLOP=1 CAPTURE_ADJACENT=1): one hook slot, two placements.
#  1. capture_adjacent_place.tcl: every SRAM rd_out capture flop FIRM beside its macro pin (unchanged).
#  2. io_flop_at_pins.tcl: every output port's launching flop and every input port's capturing flop FIRM just inside
#     the core beside its own pin (design standard: pin flops anchored at their pins).  Why here: routes
#     hcoll-port-rfetch-c26cc6a77-f9a/-f9b left the ph_tx_flit / rb_d launch flops 150-250 ps of wire from the right
#     face (ph_tx_flit[11] TT -14.3, out_d -> rb_d -91.5 at 600x660) and the qp/qr/ph_rx capture flops beside the
#     macros, so 88 of the 229 max-slew violators were unbuffered port -> input-buffer nets over the macro field.
#     out_flop_release.tcl (PRE_DETAIL_PLACE) hands the pin flops back to DPL; the capture flops stay FIRM as before.
source /src/physical/hbm_accel_die_views/coll/rtl_ps/capture_adjacent_place.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
