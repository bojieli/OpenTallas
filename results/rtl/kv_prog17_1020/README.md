# KV-PROG17 10-20 bench witnesses (claude/kv-prog17-1020 @4d1545457, Verilator 5.050, ot-epyc7 units oth-ubuntu-1697244-1792566213 / -1711394-1792566273)
EW=595_r16 (the ATTN_R16 pair image d2d_cal_image_mu_ew595_r16.svh, DUT qkd_d2d_cal_seq_bc4_ew595_r16.sv):
- r16_dcal_bc4_production_m*.log: boot target 11 (r16 image) -> bc4_ew595_r16 -> real cal pair vs the MU pin tile on the r16 image:
  m0 PASS; m1-m5 FAIL (as bc4); m7 target 11 from the base 272 image FAIL; m8 target 11 from the non-r16 595 image FAIL.
- r16_dcal_bc4_miter_m*.log: 600k-edge miter vs the frozen bc2 wrapper on the r16 image: m0 PASS (53 bits, 80 resets, 116 starts);
  m1-m3 FAIL; m7 / m8 reference on the base / non-r16 image FAIL (mismatch edge 8134 / 8457).
