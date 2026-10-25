S81-CORES3/RT 2026-10-25 review records
vq (ot_s81sl_vq):
- Census of the PASS-COND kit vq_bfq (epyc3:/srv/opentallas-scratch2/claude/s81-cores3/vq_census/kit, FF-only GRT, RCX-calibrated RC):
  postcts_gate TT pinreg mean 222.01 vs bound 234.89 (dev 12.9) PASS, FF 179.76 vs 188.76 PASS; macro pin slacks setup >= 395 ps,
  hold >= 41 ps (FF). BUT TT setup estimate -219.9 ps: yv_c -> si_ decode -> 1024 blk load enables (bf broadcast class), and F6 FAIL:
  rd_out -> xr regs 69-80 um (227/256 > 20 um), wd_in regs up to 184 um (255/256 > 20 um) (if_dist.py on 5_1_grt.odb).
- Fix (claude/s81-cores3-rt-1025, 0 cycles): blk staged write (4 per-quarter enables + blk_d) with forward blk_x; rd_q capture
  register at the macro, read one row earlier; F6 macro_if_flops.tcl (claude/s81-cores2-sw-1025) in pre_gpl.tcl.
  Bench tools/s81_slice/vq_pinreg_eq.sh vs closed b6d9d4515: base PASS 400 vectors / 2152 fragments / 0 mismatches;
  mutblkf FAIL 213, mutrdq FAIL 540, mutbfq FAIL 1072, mutwreg FAIL 540. (OT_VQ_MUT_XPTR is blind: the ref RTL reads the same define.)
- Kit epyc3:/srv/opentallas-scratch2/claude/s81-cores3-rt/kits/ot_s81sl_vq_f6 post-CTS: face_guard PASS (synth + odb), CTS FF hold
  -40.26/365 (pre-repair), OT_MACRO_IF 520 IF regs FIRM p50 9.0 / p90 11.1 / max 11.2 um; CK (TT, placement RC) 147-159 (spread 12.0),
  macro clk 151.2, pin-reg max 8.5 um. vq_f6_postcts.png.
rxsf (dsfd_su_t_rxsf): re-pin inputs/core_pins/dsfd_su_t_rxsf_c.json + cores/rx/lef (repin.py): W 96 pins spread 5.0-135.4
  (was 3 clusters at 10.5/um), E 34 pins 6.3-134.1, ck at W 70.19 (was E 92.89). Measured on the old ftz kit post-CTS (placement RC):
  CK spread 7.7 ps, W band 200.7-204.3 vs E 198.5-203.7, pin-reg max 10.7 um -> the E clock entry caused no band skew; the remaining
  cause is pin density. Kit epyc2:/srv/opentallas-scratch2/claude/s81-cores3-rt/kits/dsfd_su_t_rxsf_w (CTS running).
