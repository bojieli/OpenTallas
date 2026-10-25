# PATH-S81/HCORE 10-25 (swr): hcore_eh1 kit (EH 8775dd9be source: hcore 7a00f9ed, tile_s 780e8010, CTLA+RSTE, WPRE2) unchanged in
# outline / pins / SDC / clock recipe, plus the STRUCTURAL fix for the 13 TT setup violators (-29.15 ps, all = the f12 LAT-4
# adder's stage-1 swap select fanning out to 61 swap muxes through 3 serial BUFx2 at fanout cap 24): -DOT_F12_SWAP_REP builds
# the select 4x in keep_hierarchy leaves ot_hdc_f12_swsel (one per mux group, <= 17 loads), 0 cycles, function unchanged
# (miter/: f12 l4/l5x/l5 3 seeds x 2M PASS + mutant CAUGHT; hcore vs EH source 3 seeds PASS + mutant CAUGHT).
# Runner run_swr.sh: synth -> LEC (lec.py, fail-closed) -> face_guard -> CTS -> ISOLATED FF hold repair (repair_ff.tcl, one FF
# scene, FF vclk 213.14, placement RC) -> independent TT setup check -> GRT with SKIP_INCREMENTAL_REPAIR=1 and a DRV-only
# post-GRT hook (no 2-scene hold session) -> post-CTS gate -> route/finish/pin_audit/corners -> signoff.py, exit = signoff's.
# S81-HCORE r3 (10-24; r2 + GRT margins after the r2 signoff: TT -1.30 / FF hold -2.95 / 10-12 slew nets): ot_s81c_attn_hcore 157.68x259.2 on the kits_repin recipe of the SIGNED VQ r12 kit (codex-s81/cores-r12):
# current SDC (-max/-min IO, seam-hold padding), keep pin regs, MCMM tc+bc repair, DRV fanout cap + post-GRT DRV/hold repair,
# SKIP_LAST_GASP 0, signoff.py as the final step.  RTL = base (WPRE 0): WPRE decodes the ld_* pins before the R0 register,
# which face_guard rejects (pin -> logic -> flop; 9 shared pin nets in the wpre route gate).
export DESIGN_NICKNAME = hc_ot_s81c_attn_hcore_swr
export DESIGN_NAME = ot_s81c_attn_hcore
export PLATFORM = asap7
export VERILOG_FILES = /work/rtl/ot_s81c_attn_hcore.sv /work/rtl/ot_hdc_v41x_attn_tile_s.sv /work/rtl/ot_hdc_v41x_kreg.sv /work/rtl/ot_hdc_v41x_attn_tile.sv /work/rtl/ot_hdc_v41x_attn_tile_lat.sv /work/rtl/ot_hdc_fp32_f12.sv /work/rtl/ot_hdc_fp32_add_lat.sv /work/rtl/ot_hdc_prefix.sv /work/rtl/ot_hdc_fastfp.sv /work/rtl/ot_dsrom_su_add6.sv
export VERILOG_INCLUDE_DIRS = /work/rtl
export VERILOG_DEFINES = -DSYNTHESIS -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RSTE -DOT_F12_SWAP_REP
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
export HOLD_SLACK_MARGIN = 5
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
export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre_flow.tcl
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5
export SYNTH_HDL_FRONTEND = slang
export POST_GLOBAL_ROUTE_TCL = /work/grt_post_flow.tcl
# CP1-R10 face_keep (main 0ce45ab03c): boundary cells dont_touch through ORFS eliminate_dead_logic, released after synth
export PRE_SYNTH_TCL = /work/face_keep.tcl
export POST_SYNTH_TCL = /work/face_keep_release.tcl
# S81-CORES2/EH 10-25: FLOW F1 (per-corner bound vclk = r3 routed RCX pin-reg means TT 258.53 / FF 213.14), F2 calibrated RC,
# F4 leaf affinity + tap_balance to the bound TT insertion; no CTS-stage repair (hold repaired at FF GRT on the FF vclk)
export PRE_CTS_TCL = /work/hold_budget.tcl
export OT_TAP_TARGET_PS = 258.53
export OT_TAP_WINDOW_PS = 40
export OT_TAP_PITCH_UM = 600
export SKIP_CTS_REPAIR_TIMING = 1
export POST_CTS_TCL = /work/cts_post.tcl
export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl
export SET_RC_TCL = /work/setRC_rcx.tcl
export OT_VCLK_TT = 258.53
export OT_VCLK_FF = 213.14
# PATH-S81/HCORE swr additions
export SYNTH_KEEP_MODULES = ot_hdc_f12_swsel
export SKIP_INCREMENTAL_REPAIR = 1
