# PATH-QC-SU 2026-10-25 btab_s6: structured clock spec (cf/mscts_core.tcl, QC-CQB2 recipe) for qfd_dv_s8x_btab 259.2 x 354.24 um.
# Replaces the s8bp struct_cts tree of btab_t2 (58 BUFx2 delay cells balancing short W feeds against long E wire feeds on the
# GRT estimate; same structure as prog_t2 whose routed review showed a W/E split ~70-90 ps after route, pair skew 119 ps).
# Macros 4x ot_sram_1r1w_128x256_m1_r2c2 (94.824 x 41.064) at x 86.4, y 86.4/155.52/224.64/293.76, halo 4.32; ck port S face
# (86.75, 0).  SRAM clk pins on the macro W edge.
set ot_ms_port ck
set ot_ms_root {86.75 6}
set ot_ms_taps {
  {SW  {86.75 6 86.6 6 86.6 25}        {{0 0 135 82}}}
  {SE  {86.75 6 184.6 6 184.6 29.7}    {{135 0 260 82}}}
  {Wlo {86.75 6 76 6 76 160.4}         {{0 82 134 205}}}
  {Whi {86.75 6 76 6 76 248.6}         {{0 205 134 360}}}
  {Elo {86.75 6 192 6 192 160.8}       {{134 82 260 205}}}
  {Ehi {86.75 6 237.1 6 237.1 233.2}   {{134 205 260 360}}}
}
set ot_ms_macros {
  {g_btb*0*.u_m Wlo {79.4 87.4}}
  {g_btb*1*.u_m Wlo {79.4 156.5}}
  {g_btb*2*.u_m Whi {79.4 225.6}}
  {g_btb*3*.u_m Whi {79.4 294.8}}
}
