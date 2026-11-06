# S81-BKSEL-RF vB 11-05: delta applied to the rfh6 kit config.mk (epyc2 scratch2 form-bksel/dsdv_bksel_q_rfh6, nickname
# kl_dsdv_bksel_q_rfh2) to make kit dsdv_bksel_q_vB.  Base kit RTL = the rfh6 kit rtl/ (RF-H form); only
# rtl/ot_s81ph_hq_tile.sv changes (this directory).  macros/ot_s81ph_native_sel_hist_bank.lef = the rfh6 hist_inset.lef
# (clk pin bottom 0.108, FORM-S81-2 rfh6).  Kit also carries physical/common_flow/ot_rst_copies.{tcl,py} (main).
export DESIGN_NICKNAME = kl_dsdv_bksel_q_vB
# VERILOG_DEFINES: rfh6 list + -DOT_BKQ_RCP=16
export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_vB.tcl
export PRE_DETAIL_PLACE_TCL = /work/bank_regs_release.tcl
export OT_RST_COPIES_MAX = 256
export OT_RST_COPIES_RE = (^|\.)u_q\.rst_c_[st]$$
