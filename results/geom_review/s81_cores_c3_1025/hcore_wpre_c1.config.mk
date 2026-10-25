# S81-HCORE r3 (10-24; r2 + GRT margins after the r2 signoff: TT -1.30 / FF hold -2.95 / 10-12 slew nets): ot_s81c_attn_hcore 157.68x259.2 on the kits_repin recipe of the SIGNED VQ r12 kit (codex-s81/cores-r12):
# current SDC (-max/-min IO, seam-hold padding), keep pin regs, MCMM tc+bc repair, DRV fanout cap + post-GRT DRV/hold repair,
# SKIP_LAST_GASP 0, signoff.py as the final step.  RTL = base (WPRE 0): WPRE decodes the ld_* pins before the R0 register,
# which face_guard rejects (pin -> logic -> flop; 9 shared pin nets in the wpre route gate).
export DESIGN_NICKNAME = hc_ot_s81c_attn_hcore_wpre_c1
export DESIGN_NAME = ot_s81c_attn_hcore
export PLATFORM = asap7
export VERILOG_FILES = /work/rtl/ot_s81c_attn_hcore.sv /work/rtl/ot_hdc_v41x_attn_tile_s.sv /work/rtl/ot_hdc_v41x_kreg.sv /work/rtl/ot_hdc_v41x_attn_tile.sv /work/rtl/ot_hdc_v41x_attn_tile_lat.sv /work/rtl/ot_hdc_fp32_f12.sv /work/rtl/ot_hdc_fp32_add_lat.sv /work/rtl/ot_hdc_prefix.sv /work/rtl/ot_hdc_fastfp.sv /work/rtl/ot_dsrom_su_add6.sv
export VERILOG_INCLUDE_DIRS = /work/rtl
export VERILOG_DEFINES = -DSYNTHESIS -DOT_S81C_HCORE_WPRE
export SDC_FILE = /work/constraint.sdc
export DIE_AREA = 0 0 157.68 259.2
export CORE_AREA = 4.32 4.32 153.36 254.88
export IO_CONSTRAINTS = /work/io.tcl
export PDN_TCL = /work/pdn.tcl
override export MAKE_TRACKS = /work/make_tracks.tcl
export MIN_ROUTING_LAYER = M2
export MAX_ROUTING_LAYER = M5
export PLACE_DENSITY = 0.6
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export LEC_CHECK = 0
export HOLD_SLACK_MARGIN = 15
export SETUP_SLACK_MARGIN = 15
export SKIP_LAST_GASP = 0
export TNS_END_PERCENT = 100
export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl
export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl
export CORNER = TC
export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl
export OT_KEEP_PIN_REGS = 1
export CORNERS = tc bc
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES)
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)
export SLEW_MARGIN = 20
export CAP_MARGIN = 20
export PRE_RESIZE_TCL = /work/drv.tcl
export PRE_GLOBAL_ROUTE_TCL = /work/drv.tcl
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5
export SYNTH_HDL_FRONTEND = slang
export POST_GLOBAL_ROUTE_TCL = /work/post_grt_drv.tcl
# CP1-R10 face_keep (main 0ce45ab03c): boundary cells dont_touch through ORFS eliminate_dead_logic, released after synth
export PRE_SYNTH_TCL = /work/face_keep.tcl
export POST_SYNTH_TCL = /work/face_keep_release.tcl
