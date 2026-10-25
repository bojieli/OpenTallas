# PATH-QC-SU 2026-10-25 prog_s6: structured clock spec (cf/mscts_core.tcl, QC-CQB2 recipe) for qfd_dv_s8x_prog 259.2 x 354.24 um.
# Replaces the s8bp struct_cts tree of prog_t2 (routed review: W/E tap split ~70-90 ps after route because 68 BUFx2 delay
# cells balanced short W feeds against long E wire feeds on the GRT estimate; est->RCX error differs for cell- vs wire-
# dominated feeds -> pair skew TT 119 / FF 86.5, input hold -91.8).  Here: equal stage count + identical cells on every tap
# path (common-mode estimate error), tap pad on GRT RC only.
# Macros (4x ot_sram_1r1w_256x256_m2_r2c2, R0, 172.824 x 41.064) at x 43.2, y 86.4/155.52/224.64/293.76, halo 4.32;
# ck port S face (35.3, 0); sink groups: S-face pin regs SW x 0-65 / SE x 195-235 (y 0-40), W column x 0-39 + W gaps,
# E column x 220-259 + E gaps.  SRAM clk pins on the macro W edge (y + 0.78).
set ot_ms_port ck
set ot_ms_root {35.3 6}
set ot_ms_taps {
  {SW  {35.3 6 37.8 6 37.8 26.8}        {{0 0 120 82}}}
  {SE  {35.3 6 213.2 6 213.2 28.5}      {{120 0 260 82}}}
  {Wlo {35.3 6 30 6 30 155.6}           {{0 82 130 210}}}
  {Whi {35.3 6 30 6 30 262.1}           {{0 210 130 360}}}
  {Elo {35.3 6 238.7 6 238.7 156.4}     {{130 82 260 210}}}
  {Ehi {35.3 6 238.7 6 238.7 247.2}     {{130 210 260 360}}}
}
set ot_ms_macros {
  {g_prog*0*.u_hi Wlo {37.0 87.2}}
  {g_prog*0*.u_lo Wlo {37.0 156.3}}
  {g_prog*1*.u_hi Whi {37.0 225.4}}
  {g_prog*1*.u_lo Whi {37.0 294.6}}
}
