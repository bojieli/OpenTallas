Safe VMS vB, original source epyc4:/srv/opentallas-scratch2/claude/die-hbm-75/eco/kits/f512rp.
Copy original kit to your own directory without run/,signoff/,lec/ and lec_async* state. Keep rtl/ byte-identical.
Replace macro_placement.tcl with this copy; add safe_native_roots.tcl and post_cts_setup_vB.tcl. Append config.mk:
override export PLACE_DENSITY = 0.35
override export PRE_CTS_TCL = /work/safe_native_roots.tcl
override export POST_CTS_TCL = /work/post_cts_setup_vB.tcl
override export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -sink_clustering_max_diameter 30 -sink_clustering_size 20 -distance_between_buffers 40
Refresh orfs_hold_mm.py/tcl from build commit main before run. Current copies are be7b72fcce1.
Build ordinary run_kit_hbm.sh KIT finish 48 8 via ot-run. No source/pin/clock frequency/uncertainty/cycle change.
Do not treat this as closed: build job must finish and signoff+LEC decide.
