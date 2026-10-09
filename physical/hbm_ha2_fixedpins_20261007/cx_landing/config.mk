export DESIGN_NAME = ot_ha2_tu_owner_banked_half_cx_top
export DESIGN_NICKNAME = ha2_owner_banked_h2
export PLATFORM = asap7
export VERILOG_FILES = /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/rtl/hdc/ot_hdc_fp32_add_lat.sv /src/rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv /src/rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_banked.sv /src/rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_banked_half.sv /src/rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_banked_half_cx.sv /src/rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_banked_half_cx_top.sv /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v
export VERILOG_DEFINES = -DSYNTHESIS
export SYNTH_HDL_FRONTEND = slang
export SYNTH_HIERARCHICAL = 0
export ADDER_MAP_FILE =
export SDC_FILE = /src/physical/hbm_ha2_fixedpins_20261007/cx_landing/route_cx.sdc
export DIE_AREA = 0 0 840 480
export CORE_AREA = 10.8 10.8 829.2 469.2
export PLACE_DENSITY = 0.50
export NUM_CORES = 16
export MIN_ROUTING_LAYER = M2
export MAX_ROUTING_LAYER = M9
export MACRO_PLACEMENT_TCL = /src/physical/hbm_ha2_owner_banked_20261006/macro_placement.tcl
export MACRO_PLACE_HALO = 4 4
export CORNER = WC
export CORNERS = WC BC
export ADDITIONAL_LEFS = /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.lef
export ADDITIONAL_LIBS = /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ss.lib
export WC_LIB_FILES = $(WC_NLDM_LIB_FILES) /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ss.lib
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
export HOLD_SLACK_MARGIN = 10
export SETUP_SLACK_MARGIN = 0
export TNS_END_PERCENT = 100
export REPORT_CLOCK_SKEW = 1
export SKIP_LAST_GASP = 0
export SYNTH_MEMORY_MAX_BITS = 32768
export DESIGN_NICKNAME = ha2_owner_cx_landing
export PRE_IO_PLACEMENT_TCL = /src/physical/hbm_ha2_fixedpins_20261007/pins.tcl
export POST_IO_PLACEMENT_TCL = /src/physical/hbm_ha2_fixedpins_20261007/check_pins.tcl
# drive-1443 (2026-10-08): half-rate gater fix -- cg_pushdown clones u_icg per sink cluster, gclk re-generated on every
# clone, clk stopped at en_l (cg_gclk_pre_cts.tcl); route SDC route_h2_cg.sdc = make_sdc.py --half --h1 at 730 ps with the
# TT / FF insertion measured on the ca0d6a5a2-tt route (TT setup repair, BC/FF hold repair see their own IO reference).
export PRE_CTS_TCL = /src/physical/hbm_ha2_fixedpins_20261007/cx_landing/cx_pre_cts.tcl
export OT_CG_K ?= 48
export OT_CG_MIN ?= 64
# review-0400 R5 (drive-0212): TUhalf -cx = ot_ha2_tu_owner_banked_half_cx LANDING=1 (wrapper *_cx_top), route SDC
# cx_landing/route_cx.sdc (cg/route_h2_cg.sdc + generated headclk -edges {4 5 8} + clock-gating checks on both gates),
# PRE_CTS cx_pre_cts.tcl = the cg hook (gater pushdown, gclk on every clone) + headclk re-declared on every clone.
