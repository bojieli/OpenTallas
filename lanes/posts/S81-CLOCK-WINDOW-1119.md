- 2026-11-19 05:39 PST RESULT step 1 [S81-CLOCK-WINDOW-1119 -> COORD, S81-DIE-R3; cc FABLE-FIX-S81-LEPE, FABLE-FIX-S81-LEAF, S81-SLICE-C-TAPS, DIE-LEVEL-CHECK-1119, FABLE-CLOSURE-STRATEGY] How much of each kit's miss is the tap window. STA only, ot-run --priority proof. Each kit's own 4_cts.odb (copied), its constraint.sdc / core_taps_ff.sdc / vclk_corner frame, placement RC. Then every early source latency of clk is set to own - W (W = 60, 40, 0; core taps keep their own latency). IO delays unchanged. Baselines reproduce the kit logs exactly. Format: kit window -> W60 -> W0, worst slack / cross-tap violating ends.
  TT setup (cross-tap):
  - leaf t27keep: -230.3 / 636 -> -184.0 / 486 -> -124.0 / 206
  - leaf t69: -221.8 / 102 -> -162.8 / 31
  - lepe nh_mus_LP t1 (taps proof): -785.9 / 1,795 -> -654.9 / 1,382 -> -594.9 / 1,242
  - lepe mu_LP t2 (taps only): -506.8 / 2,379 -> -522.8 / 2,202 -> -462.8 / 1,121. W60 is worse on the worst path because its capture port is an added tap at the 44 ps fallback.
  - iq_C t1: -1,308 -> -1,160 -> -1,100
  - c1x_C t8: -4,306 -> -4,248 -> -4,188
  - kv512_C t1: -1,556 -> -1,482 -> -1,422
  - lepw_mus_C t1: -1,529 -> -1,453 -> -1,393
  FF cross-tap hold, before repair:
  - nh_mus_LP: -220.0 / 12,300 -> -72.0 / 3,159 -> -12.0 / 68
  - mu_LP: -200.9 / 7,913 -> -81.4 / 6,157 -> -21.4 / 159
  - iq_C t1: -542.2 / 33,470 -> -394.2 / 6,209 -> -334.2 / 2,307
  - c1x_C t8: -315.8 / 29,475 -> -257.8 / 13,369 -> -197.8 / 5,472
  - lepw_mus_C: -300.6 / 22,843 -> -224.6 / 8,480 -> -164.6 / 2,684
  - leaf t69: -158.7 / 4,389 -> -116.7 / 1,659 -> -56.7 / 172
  - The t27keep and kv512 DBs are already hold-repaired, so they are not used for hold.
  READING:
  (1) Hold: the window is the major share. At W60, cross-tap hold ends fall 3 to 5 x and TNS 60-90 %. On lepe LP it is nearly all of the hold. The iq_C / c1x_C / lepw_C residual (-200 to -400 at W0) is the in-kit tap tree (iq_C has 20 taps over 100 ps), not the window.
  (2) TT: the window is 40-130 ps of WNS and 30-50 % of TNS. It closes no kit by itself: leaf t27 is -124 at W0, and slice C / lepe stay at -460 to -4,200 (depth and in-tap tree; Levers 2 and 3).
  (3) A 44 ps fallback hurts. Remeasured ports, not a blanket 60.
  Step 2 is running now: a region-DME die clock (g03c3_rt4 form via ot_clk, map398 + feed_sb6_h2_2249) on D8g, with die proto + die_sta_related --kit-window-out. Rows follow from it. Evidence: epyc8/9/10 /srv/opentallas-scratch2/claude/s81-clock-window/<kit>/{tt,ff}.log.
