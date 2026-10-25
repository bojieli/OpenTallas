# QC-CQB2 s5 structured clock spec (physical/common_flow/mscts_core.tcl), qfd_dv_s8x_vmr 259.2 x 276.48 um.
# Placement (vmr_s5 3_place, F6): S strip y 0-40 x 40-220 (~2050 regs), W strip x 0-40 y 80-230 (~1400 regs incl. the
# W-face pin registers and both SRAM left-edge bands), E bands x 222-245 at both SRAM right edges (~130 regs each).
# ck port on the S face at x 92.9.  Macros + 4.32 halo: x 38.9-222.3, y 82.1-161.2 / 177.1-256.3 (no cells there).
set ot_ms_port ck
set ot_ms_root {93 6}
set ot_ms_taps {
  {SW {93 6 72 6 72 14}             {{40 0 110 80}}}
  {SE {93 6 165 6 165 14}           {{110 0 260 80}}}
  {W0 {93 6 25 6 25 110}            {{0 0 40 150}}}
  {W1 {93 6 33 6 33 185 20 185}     {{0 150 40 280}}}
  {E  {93 6 232 6 232 150}          {{222 80 260 280}}}
}
# SRAM clock leaves: own leaf driver just outside the halo at the clk pin (left edge, y+0.78), hung on the trunk end of
# the nearest west tap, latency-matched to the bank's interface registers (wd/mask/addr/ce launch, rd capture)
set ot_ms_macros {
  {g_bank*0*.u_m W0 {37.0 87.2}}
  {g_bank*1*.u_m W1 {37.0 182.2}}
}
