# PATH-S81/ELEMB 10-25 (elemB_if2e): STRUCTURAL clock (GEOM-REVIEW 12:03 elemB_if2d FAIL). Cause (routed RCX ancestry dump):
# the single-root TritonCTS H-tree first branch clkbuf_1_0_0 runs (139,171)->(139,99) across rom0 and its level-2
# branch points sit on the rom0 halo edge (y 99.2), so the lower half (15200 sinks: rom0 cap0/addr0, S + E faces)
# is 52 ps TT / 47 FF later than the upper half (rom1 side); the ROM clocks ride a separate 10-delaybuf macro tree
# (231 TT). Fix = HBM-CLKSTRUCT structured clock: density taps (<= 1250 sinks / 80 um, never on a ROM), each ROM clk
# pin on the tap of its own IF registers, F4 zero-logic chains on one leaf, taps aligned (core_tap_align), RCX-
# calibrated RC basis.  Same 3_place.odb (GEOM placement PASS 08:19), no RTL/netlist change, no hold repair.
export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl
export SET_RC_TCL = /work/setRC_rcx.tcl
export PRE_CTS_TCL = /work/prects_dtap.tcl
export OT_DTAP_TARGET = 1250
export OT_DTAP_DMAX_UM = 80
export OT_DTAP_OUT = /work/dtap.txt
export POST_CTS_TCL = /work/f4_chain_leaf.tcl
export OT_F4_NEXT_TCL = /work/core_tap_align.tcl
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -sink_clustering_max_diameter 30 -sink_clustering_size 20 -distance_between_buffers 40 -balance_levels
export OT_VCLK_TT = 250
export OT_VCLK_FF = 170
