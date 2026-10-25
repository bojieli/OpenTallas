# ELEM-QK warm FF-hold ECO on KV head_eighth e1..e7 (old 285.12 routes), 2026-10-24
Recipe: tools/elem_qk/hold_eco (POST_GLOBAL_ROUTE warm ECO from the completed 5_2_route.odb + its SPEF, re-DRT, finish,
then main 410d3d1712 signoff.py --corners tt,ff; safe SDC of the Codex corner recovery; no RTL/cycle/clock/SDC change).
  a = FF-only, hold margin 0, FF setup may break   b = FF-only, hold margin 3   c = MCMM tc+bc, margin 0, setup-guarded
Best = b: FF hold residual -1.6..+0.09 ps on <= 5 endpoints (from -7.9..-11.8 / ~470 endpoints), TT setup kept +4.6..+27.
e2/b FF hold +0.09 PASS (TT +27.10). ALL 21 NOT SIGNED: every run also fails drv (TT slew viol 86..331), clock (TT
pin-flop insertion 320..363 ps vs 250 +- 40) and face_guard (old kit: shared/dropped/feedthrough). Those are structural
(CTS insertion, slew, kit face registers) -> the 216x216 head re-kits (KVG3-CORES, plan v3.8x) must fix them; carry
recipe b (margin >= 3 ps; c's setup-guarded MCMM is the weakest) into their post-route hold step.
Per run: <head>_<v>_signoff.json; table hold_summary.json.
