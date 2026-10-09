export DESIGN_NAME = ot_ha2_relay_tx_internal
export DESIGN_NICKNAME = ha2_relay_tx_internal
export PLATFORM = asap7
export VERILOG_FILES = /src/rtl/hbm_accel/ha2_ar/ot_ha2_parent_quiet_prims.sv /src/rtl/hbm_accel/ha2_ar/ot_ha2_hub_launch_single.sv /src/rtl/hbm_accel/ha2_ar/ot_ha2_truecredit_sender_capture.sv /src/physical/ha2_relay_tx_internal_20261008/wrapper.sv
export VERILOG_DEFINES = -DSYNTHESIS
export SYNTH_HDL_FRONTEND = slang
export SYNTH_HIERARCHICAL = 0
export ADDER_MAP_FILE =
export SDC_FILE = /src/physical/ha2_relay_tx_internal_20261008/internal.sdc
export DIE_AREA = 0 0 840.024 40.176
export CORE_AREA = 1.08 1.08 838.944 39.096
export PLACE_DENSITY = 0.55
export NUM_CORES = 8
export MIN_ROUTING_LAYER = M2
export MAX_ROUTING_LAYER = M9
# gaps-design 2026-10-08: OPTION B route at TC (setup repair at TT), MCMM hold repair at BC (FF), hold margin 50 ps
export CORNER = TC
export CORNERS = TC BC
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES)
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)
export HOLD_SLACK_MARGIN = 50
export SETUP_SLACK_MARGIN = 0
export TNS_END_PERCENT = 100
export REPORT_CLOCK_SKEW = 1
export PRE_IO_PLACEMENT_TCL = /src/physical/ha2_relay_tx_internal_20261008/pins.tcl
export POST_IO_PLACEMENT_TCL = /src/physical/ha2_relay_tx_internal_20261008/check_pins.tcl
export POST_PDN_TCL = /src/physical/ha2_relay_tx_internal_20261008/regions.tcl
# drive-1013 2026-10-08: 1,088-bit flop-to-flop hold needs ~5.7k hold buffers, over repair_timing's default 20% cap
# (RSZ-0060); raise it in CTS and GRT repair. LEC_CHECK 0 as in every other block flow: kepler-formal dies with
# SIGILL on hosts without AVX-512 (PVE1 Xeon E5-2680 v4), which killed CTS as "child killed: illegal instruction".
export PRE_CTS_TCL = /src/physical/ha2_relay_tx_internal_20261008/rsz_buffer_cap.tcl
export PRE_GLOBAL_ROUTE_TCL = /src/physical/ha2_relay_tx_internal_20261008/rsz_buffer_cap.tcl
export LEC_CHECK = 0
