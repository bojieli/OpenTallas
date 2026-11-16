# S81-BKSEL-O handoff (Opus successor of FABLE-FIX-S81-BKSEL)

Goal: sign off dsdv_bksel_q (last unsigned S81 core). Gates: DRC 0, TT setup >= -42, FF non-port hold >= 0, LEC.
Work dir: /srv/opentallas-scratch2/claude/fable-fix-bksel/ (epyc8 fx1; epyc2 fx3, fx5).

## State 2026-11-16 10:45 UTC
- fx1 epyc8 openroad PID 2767309 (kit fx1/bksel_vC9fx1): fx_repair.tcl post-GRT on calibrated RC (C x1.40 M2-M7).
  Setup -149.77 -> 0.00; FF hold repair iter 480, -116.5 -> -83.3 (7983 endpoints; pk2 c2_p + hf bank i_dg). Then pass 2, DRT, signoff.py.
- fx3 epyc2 PID 43933 (fx3/bksel_vC9fx3): same chain, hold iter 430 at -86.9.
- fx5 epyc2 PID 2269863 (fx5/bksel_vC9fx5): timing-driven GPL form, main GRT.
- b1q epyc8 PID 91496: reference only, no ECO.
- LEC: lec_async per kit (fx1 run klegacy-bksel_vC9fx1-2755310 on 1_2_yosys.v); earlier lec.json of same netlist line EQUIVALENT.
- ETM landing 140 ps already in all fx kits (etm_land.tcl via pin_post_cts.tcl, OT_ETM_EARLY_PS default 140).

## Verdict source
KIT/signoff/signoff.json + KIT/signoff.log (written by run_kit.sh after finish).

## Next
1. First form with SIGNED -> export_view.py -> AGIdock /archive/opentallas-signed-1114/s81/dsdv_bksel_q/ + rtx-pro
   /home/ubuntu/signed-export-1114/s81/dsdv_bksel_q/, INDEX.tsv, odb sha both sides; stop others by exact PID.
2. Routed setup miss -> launch OT_ETM_EARLY_PS=160 form and/or latch stage r1_d_l -> c1_p in parallel.
