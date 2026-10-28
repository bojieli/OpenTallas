# TOK-ALL-15 GB composition (XS4 -> col_h10_l4_lp_asb_x u_f_0L01 -> capc5r_e6), Tue Oct 27 04:43:56 PM PDT 2026

Outcome: the mechanism was built and run. The POSITIVE FAILS: 0 returns, 0 captures, no fault. There are no measured per-layer cycles.
The controls report FAIL, but that means nothing while the positive fails.

- Fresh frame_schedule_asb.py on asbuilt_b178_gb_image_candidate_1450.json: all 4 masters PASS (asb_sched/).
  col_h10_l4_lp_asb_x: 171/171 validation, 38/38 plan, 12/12 GB stations, LK 0x492 (unit oth-ubuntu-1716138-1793142023).
- Vectors: u_f_0L01 (slice u_s_0S, rt_w W0), rows 224..227, 14 ret words, D=321, cycles 2905.
  gb_provider_under_test is set; Q advance = 1.
- CHECKED (run1, unit oth-ubuntu-1844553-1793142966): XS go at 452 (advance1) vs 453 (old Q).
  The frame cfifo cc go is at 457000 vs 458000.
- CHECKED (run2, unit oth-ubuntu-1982692-1793144021, with diag probes): cfg reaches every cfg7_seq lc (398-428 ns, lc=0002).
  Go also reaches every lc (460-490 ns, lc=0001).
  But no sequencer ever raises go_e, and the _gb element never sees go.
  In the RTL, go_e_c = go_x && act. act needs the loaded class-valid config word (c_v, NSEG<=c_a<2NSEG, c_d[0]).
  Still open: either the phase-0 seq config image for this layer does not set class-valid, or the PQ load is held on ef={bank_free,sh_free}.
- Bounds: one uniform phase on ck_r0/1/2 and on all CAP clocks.
  Not simulated: the 39-station return relay chain, the dsfd_dvland_70 landing and the other 5 frames.
- Bench admission uses OT_XS_GB_PROVIDER_UNDER_TEST=1. The default guard is unchanged and the provider is NOT qualified.
- Vectors are in intel1 /srv/opentallas-scratch2/claude/tok15-gb/vec_pos, vec_oldq and vec_swap (wrong-image = lower_xs --mutant swap); the binaries are in run1/obj and run2/obj.
