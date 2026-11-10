# PRE_DETAIL_PLACE hook (S81-SVCRS-3 11-10): the pin-flop release of out_flop_release.tcl, then every output port's
# BUF / INV driver placed on its pin face (port_buf_at_pin.tcl).  Placement only, 0 cycles, no new cells.
# Selected by tools/ref_tile/ref_tile.py for io_flop_at_pins kits with port_buf_at_pin (default on for s81svc_* kits).
source /src/physical/qwen_die_masters/out_flop_release.tcl
source /src/physical/common_flow/port_buf_at_pin.tcl
