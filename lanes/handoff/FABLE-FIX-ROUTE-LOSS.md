# FABLE-FIX-ROUTE-LOSS handoff (2026-11-18)

Owner of the class "kits close at GRT and lose hold and setup through detail route". Lane dir: epyc9 `/srv/opentallas-scratch2/claude/fable-fix-route-loss` (lane clone `wt`, branch `claude/route-loss-eco-tt-1118`; private kit copy `hc0/kit` = QC sle_hc0__cl929603c0__cl38badc56 routed, the wave job itself was never touched).

## Root causes (measured, not estimated)

Method: the kit's own sign-off session (golden SDC, FF tap overlay, measured vclk) on the same DB three ways: routed 6_final + RCX SPEF (R), 5_1_grt.odb + GRT estimate on the kit clock table (G0), same on the signal table x1.25 the repairs use (G1). Per-endpoint dumps in `hc0/meas/{ff,tt}_{R,G0,G1}/ep_{min,max}.tsv`, clock arrival per register in `ckarr.tsv`; scripts `ana.py ana2.py ana3.py ana5.py` in the lane dir.

1. **FF hold: no RC bias, a clock-leaf tail.** 49,310 internal ends with routed slack < 30 ps: routed minus GRT median -0.9 ps (G0) / -2.2 (G1), p05 -2.6 / -6.5. The 152 routed failures lose 13.9 (G0) / 21.0 (G1) ps on average; +17.2 ps of it is clock skew (capture clock 18 ps later routed than estimated, launch +1), data +3. Per-sink clock arrival error routed minus G0 is -14..+47 ps. Detours are not the cause: DRT wire 4.45 M um, GRT 4.96 M um.
2. **The hold repair frame is the signal table x1.25** (hold_sdc_guard `ot_hsg_signal_ff`): every clock arrives 26-50 ps late there versus routed (kit table +8) and the failing ends read 7 ps better than on the kit table.
3. **A GRT margin cannot cover the tail.** Ends to lift at GRT for 0 routed failures: margin 10 -> 3,430 lifted, 142 of 152 still fail; 20 -> 9,528, 85 fail; 30 -> 46,487, 16 fail; 40 -> 54,563, 2 fail (G1 frame). The kit is at 102 % of the 400k cap. A post-route insert pads 152 ends, and routed TT setup at those capture pins is >= 144.9 ps (one end 84.2).
4. **TT setup: the routed failures are not the GRT worst ends.** asm_d[0][*] x6 and q[] x3 read +49..+57 at GRT (G1) and lose 59-75 ps: 23 ps because the signal table slows the capture clock more than the launch clock, 35-51 ps of real data-net delay above the x1.25 estimate (startpoint g_lv[1].g_c[10].f). Bulk TT is 6 ps pessimistic at x1.25.
5. **Corners.** GRT hold repair is an FF-only session (TT fell +18.44 -> -84.95 inside it); the TT repair after it is TT-only and recovered TT to +12.81 with 324 upsizes. It did NOT hurt internal hold: on the pre-TT-repair DB (`hc0/meas2/ff_P1`) internal FF hold is +6.16, the same after it, and 0 of 75,929 ends moved by more than 5 ps (the -5.68 the gate printed is 3 port-path ends). So the whole internal loss, +6.16 -> -21.57, is detail route. All 336 current wave kits read are single-mode (0 with OT_HOLD_MM).
6. **Post-route repair did not run.** The kit flow has no in-flow post-route step; the only one is the late ECO after sign-off (eco_loop). Since STAGE-CAP (600fb75237, 11-17) deleted 5_2_route.odb before sign-off, `prd_mk.sh` stopped in 1.5 s: 16 of 26 wave late ECOs on 11-17 / 11-18 ("pass dir not staged"), 0 signed off, each booked as a design near miss (hc0 x2, hd_ctl, col_h9_r2, slice_station t47). Fixed on main by LATE-ECO 8f3d167975 (found independently the same hour; verified here: staging on the capped hc0 copy passes with OT_PRD_FROM=final).

## On main / in flight

- Commit `ROUTE-LOSS: sign-off writes endpoint tables; late hold insert priced in the sign-off TT frame` (lane branch above): signoff.py writes ff/ep_ff.tsv and tt/ep_tt.tsv in every session; eco_loop plans the single-mode targeted hold insert from them (the FF-only b pass read TT room at the FF corner: sle_hc1 TT -59.5 -> -141); hold_eco_internal_run.py skips its two dump sessions when the tables exist; `OT_RC_SIGNAL_HOLD=0` knob (default unchanged). Tests `tools/die_plan/test_route_loss_eco.py`. On main: cd66ba221f (ot-push-main, tests of the touched files passed).
- Proof run 1 (QC): `hc0/kit/signoff_rl1` = sign-off of the private copy with the patched signoff.py, then `eco_loop.py run` on it. Log `hc0/signoff_rl1.log`.
- Proof run 2 (other die): not started; hd_ctl (HEAD, TT -34.49, FF internal -5.59 / 32 ends) is the right kit, its routed DB was not on disk any more.

## Open, in order

1. Read `hc0/kit/signoff_rl1/{ff/ep_ff.tsv,tt/ep_tt.tsv}` and `SO EP_DUMP` lines; run `python3 -I wt/tools/die_plan/eco_loop.py run --kit hc0/kit --out hc0/eco_rl1` through ot-run (mem 120); expect `OT_ECO_HOLD_PLAN sign-off priced`, DRC 0, TT >= -42, internal FF hold >= 0. Export what signs.
2. Second die: one HEAD or S81 kit with a routed hold-only miss through the same two steps.
3. Not done: a two-corner (TT guard) hold repair at GRT; per-class RC (clock nets on the clock table, signal nets on the signal table) in the GRT estimate. `OT_RC_SIGNAL_HOLD=0` needs a second kit before it becomes the default (sister kit cl4baa7c9c is the candidate).
4. `hc0/meas3` (net capacitance by class) was still running at this writing; `hc0/meas4/tt_R/ep_tt.tsv` = full routed TT endpoint table.
