# QC-CQB2 s5 structured clock spec (physical/common_flow/mscts_core.tcl), qfd_dv_s8x_vmr 259.2 x 276.48 um.
# Placement (vmr_s5 3_place, F6): S strip y 0-40 x 40-220 (~2050 regs), W strip x 0-40 y 80-230 (~1400 regs incl. the
# W-face pin registers and both SRAM left-edge bands), E bands x 222-245 at both SRAM right edges (~130 regs each).
# ck port on the S face at x 92.9.  Macros + 4.32 halo: x 38.9-222.3, y 82.1-161.2 / 177.1-256.3 (no cells there).
# PATH-QC-PROGVMR vmr_s6j (2026-10-25): SE tap SPLIT into SEa (x 110-160, 424 sinks, the vm_wdata/w16 W cluster x 110-140)
# and SEb (x 160-260, 775 sinks: S strip x 165-230 + E SRAM-edge band). The s6i single SE tap (1210 sinks, bimodal region with a
# 25-um empty gap, tap between the clusters) gave a TritonCTS H-tree with a 47-55 ps internal FF spread (leaves 234..289):
# every s6i hold residual (w16_data->pw16_data, pw16_data->l_w16d <=17.5 um, l_w16d->g_wr.u_d) sat on that tail. Same
# lesson as btab Whi (GEOM-REVIEW-2 10:30 cond. 1): split the tap so each local tree covers one compact cluster.
set ot_ms_port ck
set ot_ms_root {93 6}
set ot_ms_taps {
  {SW {93 6 72 6 72 14}             {{40 0 110 80}}}
  {SEa {93 6 125 6 125 12}          {{110 0 160 80}}}
  {SEb {93 6 195 6 195 14}          {{160 0 260 80}}}
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
